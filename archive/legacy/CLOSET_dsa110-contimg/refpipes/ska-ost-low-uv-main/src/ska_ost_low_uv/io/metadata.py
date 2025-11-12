"""metadata.py - I/O for metadata YAML in ska_ost_low_uv."""

import os

import h5py
from loguru import logger

from ska_ost_low_uv import __version__ as ska_ost_low_uv_version
from ska_ost_low_uv.utils import load_config, load_yaml


def get_hdf5_metadata(filename: str) -> dict:
    """Extract metadata from HDF5 and perform checks."""
    with h5py.File(filename, mode='r') as datafile:
        expected_keys = [
            'n_antennas',
            'ts_end',
            'n_pols',
            'n_beams',
            'tile_id',
            'n_chans',
            'n_samples',
            'type',
            'data_type',
            'data_mode',
            'ts_start',
            'n_baselines',
            'n_stokes',
            'channel_id',
            'timestamp',
            'date_time',
            'n_blocks',
        ]

        # Check that keys are present
        if set(expected_keys) - set(datafile.get('root').attrs.keys()) != set():  # pragma: no cover
            raise Exception('Missing metadata in file')

        # All good, get metadata
        metadata = {k: v for (k, v) in datafile.get('root').attrs.items()}
        metadata['n_integrations'] = metadata['n_blocks'] * metadata['n_samples']
        metadata['data_shape'] = datafile['correlation_matrix']['data'].shape

        # Overwrite ts_start with value from sample_timestamps/data
        # This is a WAR as h['root'].attrs['ts_start'] does not update
        # if a long observation spans multiple HDF5 files
        # (see https://github.com/ska-sci-ops/aa_uv/issues/48)
        metadata['ts_start'] = datafile['sample_timestamps/data'][0][0]
    return metadata


def load_observation_metadata(filename: str, yaml_config: str = None, use_config: str = None) -> dict:
    """Load observation metadata from correlator output HDF5.

    Args:
        filename (str): Path to HDF5 file
        yaml_config (str): Path to YAML station configuration file
        use_config (str): Name of config to load from ska_ost_low_uv package

    Notes:
        One of either `yaml_config` or `use_config` should be set. If `yaml_config`
        is set, it will take precedence over internal config
    """
    # Load metadata from config and HDF5 file
    md = get_hdf5_metadata(filename)

    if yaml_config is None:
        logger.info(f'Using internal config {use_config}')
        md_yaml = load_config(use_config)

    else:
        md_yaml = load_yaml(yaml_config)

    md.update(md_yaml)

    if not os.path.exists(md['antenna_locations_file']):
        logger.info('antenna locations not found by relative path, joining path to yaml file.')
        # Update path to antenna location files to use absolute path
        config_abspath = os.path.dirname(os.path.abspath(yaml_config))

        md['antenna_locations_file'] = os.path.join(config_abspath, md['antenna_locations_file'])
        md['baseline_order_file'] = os.path.join(config_abspath, md['baseline_order_file'])
        md['station_config_file'] = os.path.abspath(yaml_config)

    md['history'] = f'Created with ska_ost_low_uv {ska_ost_low_uv_version}'
    return md
