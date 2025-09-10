"""DSA-110 Continuum Imaging Pipeline

A unified pipeline for processing DSA-110 radio astronomy data from HDF5 files
to calibrated images and photometry products.
"""

__version__ = "2.0.0"

from .pipeline.orchestrator import Pipeline
from .data.ms_creation import MSCreator
from .calibration.bandpass import BandpassCalibrator
from .imaging.clean import Imager

def process_observation(hdf5_dir, output_dir=None, config=None):
    """Process complete observation from HDF5 to final products.
    
    Args:
        hdf5_dir: Directory containing HDF5 files
        output_dir: Output directory (default: data_new/output)
        config: Configuration dict or path to config file
        
    Returns:
        dict: Processing results and output paths
    """
    pipeline = Pipeline(config)
    return pipeline.process_directory(hdf5_dir, output_dir)

def create_measurement_sets(hdf5_files, output_dir=None):
    """Convert HDF5 files to Measurement Sets.
    
    Args:
        hdf5_files: List of HDF5 file paths
        output_dir: Output directory for MS files
        
    Returns:
        list: Paths to created MS files
    """
    creator = MSCreator()
    return creator.batch_convert(hdf5_files, output_dir)