"""converter: Command-line utility for file conversion."""

import argparse
import glob
import os
import sys
import time
import warnings

from astropy.time import Time, TimeDelta
from loguru import logger

from ska_ost_low_uv import __version__
from ska_ost_low_uv.io import (
    hdf5_to_pyuvdata,
    hdf5_to_uvx,
    phase_to_sun,
    write_ms,
    write_uvfits,
    write_uvx,
)
from ska_ost_low_uv.utils import get_aa_config, load_yaml

from .parallelize import run_in_parallel, task
from .utils import reset_logger, zipit

# fmt: off
EXT_LUT = {
    'ms':     '.ms',
    'uvfits': '.uvfits',
    'miriad': '.uv',
    'mir':    '.uv',

    'uvx':    '.uvx5',
    'uvh5':   '.uvh5',
}
# fmt: on

PYUVDATA_FORMATS = ('uvfits', 'miriad', 'mir', 'ms', 'uvh5')


def parse_args(args):
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description='AAVS UV file conversion utility')
    p.add_argument('infile', help='Input filename')
    p.add_argument('outfile', help='Output filename')
    p.add_argument(
        '-o',
        '--output_format',
        help='Output file format (uvx, uvfits, miriad, ms, uvh5). Can be comma separated for multiple formats.',
        required=True,
    )
    p.add_argument(
        '-c',
        '--array_config',
        help='Array configuration YAML file. If supplied, will override ska_ost_low_uv internal array configs.',
        required=False,
    )
    p.add_argument(
        '-n',
        '--telescope_name',
        help="Telescope name, e.g. 'aavs3'. If supplied, will attempt to use ska_ost_low_uv internal array config.",
        required=False,
    )
    p.add_argument(
        '-s',
        '--phase-to-sun',
        help='Re-phase to point toward Sun (the sun must be visible!). If flag not set, data will be phased toward zenith.',
        required=False,
        action='store_true',
        default=False,
    )
    p.add_argument(
        '-b',
        '--batch',
        help='Batch mode. Input and output are treated as directories, and all subfiles are converted.',
        required=False,
        action='store_true',
        default=False,
    )
    p.add_argument(
        '-B',
        '--megabatch',
        help='MEGA batch mode. Runs on subdirectories too, e.g. eb-aavs3/2023_12_12/*.hdf5.',
        required=False,
        action='store_true',
        default=False,
    )
    p.add_argument(
        '-x',
        '--file_ext',
        help='File extension to search for in batch mode ',
        required=False,
        default='hdf5',
    )
    p.add_argument(
        '-i',
        '--context_yaml',
        help='Path to observation context YAML (for UVX format)',
        required=False,
        default=None,
    )
    p.add_argument(
        '-w',
        '--num-workers',
        help='Number of parallel processors (i.e. number of files to read in parallel).',
        required=False,
        default=1,
        type=int,
    )
    p.add_argument(
        '-v',
        '--verbose',
        help='Run with verbose output.',
        action='store_true',
        default=False,
    )
    p.add_argument(
        '-p',
        '--parallel_backend',
        help="Joblib backend to use: 'loky' (default) or 'dask' ",
        required=False,
        default='loky',
    )
    p.add_argument(
        '-N',
        '--n_int_per_file',
        help='Set number of integrations to write per file. Only valid for MS, Miriad, UVFITS, uvh5 output.',
        required=False,
        default=None,
        type=int,
    )
    p.add_argument(
        '-z',
        '--zipit',
        help='Zip up a MS or Miriad file after conversion (flag ignored for other files)',
        required=False,
        action='store_true',
        default=False,
    )
    args = p.parse_args(args)
    return args


def convert_file(
    args: argparse.Namespace,
    fn_in: str,
    fn_out: str,
    array_config: str,
    output_format: str,
    context: dict,
):
    """Convert a file.

    Args:
        args (argparse.Namespace): Namespace (output of argparse's parse_args() )
        fn_in (str): Input filename
        fn_out (str): Output filename
        array_config (str): Path to array config directory
        output_format (str): Output format, one of uvfits, miriad, mir, ms, uvh5, uvx
        context (dict): Dictionary of additional metadata. Only supported by UVX format.
    """
    # Create subdirectories as needed
    if args.batch or args.megabatch:
        subdir = os.path.dirname(fn_out)
        if not os.path.exists(subdir):
            logger.info(f'Creating sub-directory {subdir}')
            os.mkdir(subdir)

    # Load file and read basic metadata
    vis = hdf5_to_uvx(
        fn_in, yaml_config=array_config, load_data=False
    )  # load_data=False flag so data is not read into memory

    # Print basic info to screen (skip if in batch mode)
    if not args.batch and not args.megabatch:
        logger.info(f'Loading {fn_in}')
        logger.info(f'Data shape:     {vis.data.shape}')
        logger.info(f'Data dims:      {vis.data.dims}')
        logger.info(f'UTC start:      {vis.timestamps[0].iso}')
        logger.info(f'MJD start:      {vis.timestamps[0].mjd}')
        logger.info(f'LST start:      {vis.data.time.data[0][1]:.5f}')
        logger.info(f'Frequency 0:    {vis.data.frequency.data[0]} {vis.data.frequency.units}')
        logger.info(f'Polarization:   {vis.data.polarization.data}\n')

    if output_format in PYUVDATA_FORMATS:
        if args.n_int_per_file is not None:
            N_cycles = len(vis.timestamps) // args.n_int_per_file
            logger.info(f'Number of file reads: {N_cycles}')
        else:
            N_cycles = 1

        tr0 = time.time()
        for start_int in range(N_cycles):
            uv = hdf5_to_pyuvdata(
                fn_in,
                yaml_config=array_config,
                max_int=args.n_int_per_file,
                start_int=start_int,
            )

            if args.phase_to_sun:
                logger.info('Phasing to sun')
                ts0 = Time(uv.time_array[0], format='jd') + TimeDelta(uv.integration_time[0] / 2, format='sec')
                uv = phase_to_sun(uv, ts0)
            tr = time.time() - tr0

            tw0 = time.time()

            # fmt: off
            _writers = {
                'uvfits': write_uvfits,
                'miriad': uv.write_miriad,
                'mir': uv.write_miriad,
                'ms': write_ms,
                'uvh5': uv.write_uvh5,
            }
            # fmt: on

            writer = _writers[output_format]

            if N_cycles > 1:
                # Update filename if we are iterating over the file
                new_fn_out = os.path.splitext(fn_out)[0] + f'.{start_int:05d}' + EXT_LUT[output_format]
            else:
                new_fn_out = fn_out

            logger.info(f'Creating {args.output_format} file: {new_fn_out}')
            if os.path.exists(new_fn_out):
                logger.warning(f'File exists, skipping: {new_fn_out}')
            else:
                # Write the desired output format
                # Add special kwargs as needed -- currently just for UVFITS
                kwargs = {}
                if output_format == 'uvfits':
                    kwargs['use_miriad_convention'] = True
                    writer(uv, new_fn_out, **kwargs)
                elif output_format == 'ms':
                    writer(uv, new_fn_out, **kwargs)
                else:
                    writer(new_fn_out, **kwargs)
                # and if MS or Miriad, check if it should be zipped
                if args.zipit and output_format in ('ms', 'miriad'):
                    zipit(new_fn_out, rm_dir=True)
            tw = time.time() - tw0
            del uv

    elif output_format == 'uvx':
        tr0 = time.time()
        vis = hdf5_to_uvx(fn_in, yaml_config=array_config, context=context)
        tr = time.time() - tr0
        tw0 = time.time()
        logger.info(f'Creating {args.output_format} file: {fn_out}')
        write_uvx(vis, fn_out)
        tw = time.time() - tw0
        del vis

    return (fn_in, tr, tw)


@task
def convert_file_task(
    args: argparse.Namespace,
    fn_in: str,
    fn_out: str,
    array_config: str,
    output_format: str,
    context: dict,
    verbose: bool,
):
    """Parallelizable task for file conversion.

    Args:
        args (argparse.Namespace): Namespace (output of argparse's parse_args() )
        fn_in (str): Input filename
        fn_out (str): Output filename
        array_config (str): Path to array config directory
        output_format (str): Output format, one of uvfits, miriad, mir, ms, uvh5, uvx
        context (dict): Dictionary of additional metadata. Only supported by UVX format.
        verbose (bool): Turn on verbose mode
    """
    if not verbose:
        # Silence warnings from other packages (e.g. pyuvdata)
        warnings.simplefilter('ignore')
        reset_logger(use_tqdm=True, disable=True)
    convert_file(args, fn_in, fn_out, array_config, output_format, context)


def run(args=None):
    """Command-line utility for file conversion.

    Args:
        args (list): List of command line arguments to pass to convert_file().
    """
    args = parse_args(args)
    config_error_found = False

    # Reset logger
    reset_logger()
    logger.info(f'ska_ost_low_uv {__version__}')

    # Load array configuration
    array_config = args.array_config

    if args.telescope_name:
        logger.info(f'Telescope name: {args.telescope_name}')
        array_config = get_aa_config(args.telescope_name)

    if array_config is None:
        logger.error('No telescope name or array config file passed. Please re-run with -n or -c flag set')
        config_error_found = True
    else:
        if not os.path.exists(array_config):
            logger.error(f'Cannot find array config: {array_config}')
            config_error_found = True

    output_formats = args.output_format.lower().split(',')

    # Check input file exists
    if not os.path.exists(args.infile):
        logger.error(f'Cannot find input file: {args.infile}')
        config_error_found = True

    # Check path points to a directory for batch mode, or a file for regular mode
    if args.batch or args.megabatch:
        if not os.path.isdir(args.infile):
            logger.error('Input path must be a directory when using batch mode.')
            config_error_found = True
    else:
        if os.path.isdir(args.infile):
            logger.error(
                'Input path point to a directory, but batch mode flag not set. Please pass -b (batch) or -B (megabatch) flags.'
            )
            config_error_found = True

    # Check output format
    for output_format in output_formats:
        if output_format not in ('uvfits', 'miriad', 'mir', 'ms', 'uvh5', 'uvx'):
            logger.error(f'Output format not valid: {output_format}')
            config_error_found = True

    # Raise error and quit if config issues exist
    if config_error_found:
        logger.error('Errors found. Please check arguments.')
        return

    logger.info(f'Input path:       {args.infile}')
    logger.info(f'Array config:     {array_config}')
    logger.info(f'Output path:      {args.outfile}')
    logger.info(f'Output formats:   {output_formats} \n')

    # Check if we need to zip data
    if args.zipit:
        logger.info('Zip output:      Yes')
        if output_format not in ('miriad', 'ms'):
            logger.warning(f'Output format {output_format} is not MS or Miriad, so will not be zipped')

    # Check if context yaml was included
    context = load_yaml(args.context_yaml) if args.context_yaml is not None else None

    ######
    # Start outer main conversion loop -- (output formats)
    for output_format in output_formats:
        # Setup filelist, globbing for files if in batch mode
        if args.batch or args.megabatch:
            if not os.path.exists(args.outfile):
                logger.info(f'Creating directory {args.outfile}')
                os.mkdir(args.outfile)

            if args.batch:
                filelist = sorted(glob.glob(os.path.join(args.infile, f'*.{args.file_ext}')))
            else:
                filelist = sorted(
                    glob.glob(
                        os.path.join(args.infile, f'*/*.{args.file_ext}'),
                        recursive=True,
                    )
                )

            filelist_out = []

            for fn in filelist:
                bn = os.path.basename(fn)
                bn_out = os.path.splitext(bn)[0] + EXT_LUT[output_format]
                if args.megabatch:
                    subdir = os.path.join(args.outfile, os.path.basename(os.path.dirname(fn)))
                    filelist_out.append(os.path.join(subdir, bn_out))
                else:
                    filelist_out.append(os.path.join(args.outfile, bn_out))
        else:
            filelist = [args.infile]
            filelist_out = [args.outfile]

        ######
        # Start inner main conversion loop -- (run on each file)
        with warnings.catch_warnings():
            if not args.verbose:
                warnings.simplefilter('ignore')
                logger.remove()

            logger.info(f'Starting conversion on {len(filelist)} files with {args.num_workers} workers')

            if args.num_workers > 1:
                # Create a list of tasks to run
                task_list = []
                for fn_in, fn_out in zip(filelist, filelist_out, strict=False):
                    task_list.append(
                        convert_file_task(
                            args,
                            fn_in,
                            fn_out,
                            array_config,
                            output_format,
                            context,
                            args.verbose,
                        )
                    )

                # Run the task list
                run_in_parallel(
                    task_list,
                    n_workers=args.num_workers,
                    backend=args.parallel_backend,
                    verbose=args.verbose,
                )
            else:
                for fn_in, fn_out in zip(filelist, filelist_out, strict=False):
                    convert_file(args, fn_in, fn_out, array_config, output_format, context)


if __name__ == '__main__':  # pragma: no cover
    print(sys.argv[1:])
    args = parse_args(sys.argv[1:])
    run(args)
