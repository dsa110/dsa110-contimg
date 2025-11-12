import os
import glob
import multiprocessing
from functools import partial
import argparse
import subprocess

def run_conversion(hdf5_file, output_dir):
    """
    Runs the HDF5 to MS conversion for a single file.

    Parameters
    ----------
    hdf5_file : str
        Path to the input HDF5 file.
    output_dir : str
        Directory to save the output MS file.
    """
    ms_file = os.path.join(output_dir, os.path.basename(hdf5_file).replace('.hdf5', '.ms'))
    
    # Path to the conversion script
    conversion_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'convert_hdf5_to_ms.py')

    # Construct the command to run the conversion script with CASA's Python
    # This ensures that the script is run within the CASA environment
    command = [
        'casa', '--nologger', '--nogui', '-c',
        conversion_script,
        hdf5_file,
        ms_file
    ]
    
    try:
        print(f"Executing command: {' '.join(command)}")
        subprocess.run(command, check=True)
        print(f"Successfully converted {hdf5_file} to {ms_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting {hdf5_file}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during conversion of {hdf5_file}: {e}")

def imaging_pipeline(input_dir, output_dir, imagename, use_mms=False, num_cores=None):
    """
    CASA imaging pipeline for DSA-110 data.

    This pipeline automates the conversion of HDF5 files to Measurement Sets (MS),
    concatenates them, and creates a continuum image using tclean. It supports
    parallel processing for the conversion and imaging steps.

    Parameters
    ----------
    input_dir : str
        Directory containing the HDF5 files.
    output_dir : str
        Directory to save the intermediate MS files and the final image.
    imagename : str
        The root name for the output image products.
    use_mms : bool, optional
        If True, create and image a Multi-MS for parallel tclean. 
        Default is False.
    num_cores : int, optional
        The number of cores to use for parallel processing. Defaults to the 
        number of available CPUs.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Find all HDF5 files in the input directory
    hdf5_files = sorted(glob.glob(os.path.join(input_dir, '*.hdf5')))
    if not hdf5_files:
        print("No HDF5 files found in the specified directory.")
        return

    # Determine the number of cores to use
    if num_cores is None:
        num_cores = multiprocessing.cpu_count()
    
    # --- 1. Parallel Conversion from HDF5 to MS ---
    print(f"Starting parallel conversion of {len(hdf5_files)} HDF5 files using {num_cores} cores...")
    
    # Create a partial function with the fixed output directory
    conversion_func = partial(run_conversion, output_dir=output_dir)
    
    with multiprocessing.Pool(processes=num_cores) as pool:
        pool.map(conversion_func, hdf5_files)
    
    print("All HDF5 files have been converted to MS.")

    # List of created MS files
    ms_files = sorted([os.path.join(output_dir, os.path.basename(f).replace('.hdf5', '.ms')) for f in hdf5_files])

    # --- 2. Concatenate the Measurement Sets ---
    concat_ms = os.path.join(output_dir, 'concatenated.ms')
    print(f"Concatenating {len(ms_files)} MS files into {concat_ms}...")
    
    # This part needs to be run within CASA's environment.
    # We'll create a small Python script to be executed by CASA.
    concat_script_content = f"""
from casatasks import concat
concat(vis={ms_files}, concatvis='{concat_ms}')
"""
    concat_script_file = os.path.join(output_dir, 'concat_script.py')
    with open(concat_script_file, 'w') as f:
        f.write(concat_script_content)
    
    # Execute the concat script with CASA
    subprocess.run(['casa', '--nologger', '--nogui', '-c', concat_script_file], check=True)
    print("Concatenation complete.")

    # --- 3. Imaging ---
    vis_to_image = concat_ms
    image_output_path = os.path.join(output_dir, imagename)

    if use_mms:
        print("Creating a Multi-MS for parallel imaging...")
        mms_file = os.path.join(output_dir, 'concatenated.mms')
        
        # Create a partition script for CASA
        partition_script_content = f"""
from casatasks import partition
partition(vis='{concat_ms}', outputvis='{mms_file}', numsubms={num_cores}, flagbackup=False)
"""
        partition_script_file = os.path.join(output_dir, 'partition_script.py')
        with open(partition_script_file, 'w') as f:
            f.write(partition_script_content)

        subprocess.run(['casa', '--nologger', '--nogui', '-c', partition_script_file], check=True)
        vis_to_image = mms_file
        print("Multi-MS created.")

    print(f"Starting imaging with tclean on {vis_to_image}...")
    
    # Create the tclean script for CASA
    tclean_script_content = f"""
from casatasks import tclean
tclean(
    vis='{vis_to_image}',
    imagename='{image_output_path}',
    imsize=[1024, 1024],  # Adjust as needed
    cell=['1.0arcsec'],   # Adjust as needed
    stokes='I',
    specmode='mfs',
    deconvolver='hogbom',
    gridder='standard',
    weighting='natural',
    niter=1000,
    threshold='0.1mJy',
    interactive=False
)
"""
    tclean_script_file = os.path.join(output_dir, 'tclean_script.py')
    with open(tclean_script_file, 'w') as f:
        f.write(tclean_script_content)

    # Execute tclean
    subprocess.run(['casa', '--nologger', '--nogui', '-c', tclean_script_file], check=True)
    print(f"Imaging complete. Output image is located at {image_output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CASA Imaging Pipeline for DSA-110 Data.')
    parser.add_argument('input_dir', type=str, help='Directory containing HDF5 files.')
    parser.add_argument('output_dir', type=str, help='Directory for output files.')
    parser.add_argument('imagename', type=str, help='Root name for the output image.')
    parser.add_argument('--use_mms', action='store_true', help='Use Multi-MS for parallel imaging.')
    parser.add_argument('--num_cores', type=int, default=None, help='Number of cores for parallel processing.')
    
    args = parser.parse_args()
    
    imaging_pipeline(args.input_dir, args.output_dir, args.imagename, args.use_mms, args.num_cores)
