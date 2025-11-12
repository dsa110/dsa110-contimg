#!/usr/bin/env python3
"""
Practical Antenna Position Swap Example

This script shows how to integrate antenna position swapping into your
existing DSA110 continuum imaging pipeline.
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
import warnings

# Add pipeline path
pipeline_parent_dir = '/data/jfaber/dsa110-contimg/'
if pipeline_parent_dir not in sys.path:
    sys.path.insert(0, pipeline_parent_dir)

from pyuvdata import UVData
from astropy.coordinates import EarthLocation
import astropy.units as u

# Import your existing utilities
from dsa110.telescope.antenna_positions import DSA110AntennaPositions
from dsa110.utils.logging import get_logger

logger = get_logger(__name__)


class AntennaPositionSwapper:
    """
    Practical antenna position swapper for DSA110 pipeline integration.
    """
    
    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize with CSV file path.
        
        Args:
            csv_path: Path to antenna positions CSV file
        """
        self.csv_path = csv_path or self._get_default_csv_path()
        self.antenna_manager = DSA110AntennaPositions(self.csv_path)
        
    def _get_default_csv_path(self) -> str:
        """Get default CSV path from your existing setup."""
        return str(Path(__file__).parent.parent.parent / "archive" / "reference_pipelines" / 
                  "dsa110_hi-main" / "dsa110hi" / "resources" / "DSA110_Station_Coordinates.csv")
    
    def swap_uvdata_positions(self, uv_data: UVData, use_survey_grade: bool = True) -> UVData:
        """
        Swap antenna positions in UVData object using your existing infrastructure.
        
        Args:
            uv_data: UVData object to modify
            use_survey_grade: If True, use survey-grade positions from CSV
            
        Returns:
            Modified UVData object
        """
        try:
            if use_survey_grade:
                # Use your existing antenna position manager
                antenna_positions, antenna_names = self.antenna_manager.get_antenna_positions_for_uvdata()
                antenna_numbers = np.arange(len(antenna_names))
                
                logger.info(f"Using survey-grade positions for {len(antenna_names)} antennas")
            else:
                # Use positions from HDF5 file (original)
                antenna_positions = uv_data.antenna_positions
                antenna_names = uv_data.antenna_names
                antenna_numbers = uv_data.antenna_numbers
                
                logger.info(f"Using original HDF5 positions for {len(antenna_names)} antennas")
            
            # Update UVData object
            uv_data.antenna_positions = antenna_positions
            uv_data.antenna_names = antenna_names
            uv_data.antenna_numbers = antenna_numbers
            
            # Log position statistics
            self._log_position_stats(antenna_positions, antenna_names)
            
            return uv_data
            
        except Exception as e:
            logger.error(f"Failed to swap antenna positions: {e}")
            raise
    
    def _log_position_stats(self, positions: np.ndarray, names: List[str]) -> None:
        """Log antenna position statistics."""
        if len(positions) > 0:
            logger.info(f"Antenna position range: X={np.min(positions[:, 0]):.3f} to {np.max(positions[:, 0]):.3f}m")
            logger.info(f"Antenna position range: Y={np.min(positions[:, 1]):.3f} to {np.max(positions[:, 1]):.3f}m")
            logger.info(f"Antenna position range: Z={np.min(positions[:, 2]):.3f} to {np.max(positions[:, 2]):.3f}m")
            
            # Calculate baseline lengths
            baselines = []
            for i in range(len(positions)):
                for j in range(i+1, len(positions)):
                    baseline_length = np.linalg.norm(positions[i] - positions[j])
                    baselines.append(baseline_length)
            
            if baselines:
                baselines = np.array(baselines)
                logger.info(f"Baseline range: {np.min(baselines):.1f} to {np.max(baselines):.1f}m")
                logger.info(f"Mean baseline: {np.mean(baselines):.1f}m")
    
    def compare_positions(self, uv_data: UVData) -> Dict[str, Any]:
        """
        Compare current UVData positions with CSV positions.
        
        Args:
            uv_data: UVData object to compare
            
        Returns:
            Dictionary with comparison results
        """
        try:
            # Get current positions
            current_positions = uv_data.antenna_positions
            current_names = uv_data.antenna_names
            
            # Get CSV positions
            csv_positions, csv_names = self.antenna_manager.get_antenna_positions_for_uvdata()
            
            # Compare
            n_current = len(current_positions)
            n_csv = len(csv_positions)
            
            comparison = {
                'current_antennas': n_current,
                'csv_antennas': n_csv,
                'current_names': current_names,
                'csv_names': csv_names,
                'position_differences': None
            }
            
            if n_current == n_csv:
                # Calculate differences
                pos_diff = np.abs(current_positions - csv_positions)
                comparison['position_differences'] = {
                    'max_diff': np.max(pos_diff),
                    'mean_diff': np.mean(pos_diff),
                    'rms_diff': np.sqrt(np.mean(pos_diff**2))
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to compare positions: {e}")
            return {'error': str(e)}


def demonstrate_integration():
    """
    Demonstrate how to integrate antenna position swapping into your pipeline.
    """
    print("=== PRACTICAL ANTENNA POSITION SWAPPING INTEGRATION ===\n")
    
    # Initialize swapper
    swapper = AntennaPositionSwapper()
    
    # Example HDF5 file path
    hdf5_file = "data/hdf5/example.hdf5"  # Replace with actual file
    
    if os.path.exists(hdf5_file):
        try:
            # Read HDF5 file with Pyuvdata
            print("1. Reading HDF5 file with Pyuvdata...")
            uv_data = UVData()
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                uv_data.read(hdf5_file, file_type='uvh5', run_check=False)
            
            print(f"   Loaded {len(uv_data.antenna_names)} antennas from HDF5")
            
            # Compare positions
            print("\n2. Comparing positions...")
            comparison = swapper.compare_positions(uv_data)
            if 'error' not in comparison:
                print(f"   HDF5 antennas: {comparison['current_antennas']}")
                print(f"   CSV antennas: {comparison['csv_antennas']}")
                if comparison['position_differences']:
                    diff = comparison['position_differences']
                    print(f"   Max difference: {diff['max_diff']:.3f} m")
                    print(f"   Mean difference: {diff['mean_diff']:.3f} m")
            
            # Swap to survey-grade positions
            print("\n3. Swapping to survey-grade positions...")
            uv_data_swapped = swapper.swap_uvdata_positions(uv_data, use_survey_grade=True)
            
            print("   Antenna position swap completed successfully!")
            
            # Show how to write the result
            print("\n4. Writing result...")
            print("   # Write to MS format:")
            print("   uv_data_swapped.write_ms('output.ms', clobber=True)")
            print("   # or write back to HDF5:")
            print("   uv_data_swapped.write_uvh5('output.uvh5', clobber=True)")
            
        except Exception as e:
            print(f"Error in demonstration: {e}")
    else:
        print("Example HDF5 file not found - showing integration code only")
        print("\nINTEGRATION CODE:")
        print("=" * 20)
        print("""
# In your existing pipeline code:

# 1. Initialize swapper
swapper = AntennaPositionSwapper()

# 2. Read HDF5 file
uv_data = UVData()
uv_data.read(hdf5_file, file_type='uvh5')

# 3. Swap positions (use survey-grade from CSV)
uv_data = swapper.swap_uvdata_positions(uv_data, use_survey_grade=True)

# 4. Continue with your pipeline
# ... rest of your processing ...

# 5. Write result
uv_data.write_ms(output_ms_file, clobber=True)
        """)


def show_integration_examples():
    """
    Show specific integration examples for different scenarios.
    """
    print("\n=== INTEGRATION EXAMPLES ===\n")
    
    print("EXAMPLE 1: INTEGRATE INTO UNIFIED MS CREATION")
    print("-" * 45)
    print("""
# In your UnifiedMSCreationManager class:

async def _set_antenna_positions(self, uv_data: UVData) -> None:
    \"\"\"Set antenna positions with option to use CSV or HDF5 positions.\"\"\"
    try:
        # Initialize swapper
        swapper = AntennaPositionSwapper()
        
        # Choose source based on configuration
        use_survey_grade = self.config.get('use_survey_grade_positions', True)
        
        # Swap positions
        uv_data = swapper.swap_uvdata_positions(uv_data, use_survey_grade=use_survey_grade)
        
        logger.info(f"Set antenna positions for {len(uv_data.antenna_names)} antennas")
        
    except Exception as e:
        logger.error(f"Failed to set antenna positions: {e}")
        raise
    """)
    
    print("\nEXAMPLE 2: BATCH PROCESSING WITH POSITION SWAPPING")
    print("-" * 50)
    print("""
# Process multiple HDF5 files with position swapping:

def process_hdf5_files_with_swapping(hdf5_files: List[str], output_dir: str):
    \"\"\"Process multiple HDF5 files with antenna position swapping.\"\"\"
    swapper = AntennaPositionSwapper()
    
    for hdf5_file in hdf5_files:
        try:
            # Read HDF5 file
            uv_data = UVData()
            uv_data.read(hdf5_file, file_type='uvh5')
            
            # Swap to survey-grade positions
            uv_data = swapper.swap_uvdata_positions(uv_data, use_survey_grade=True)
            
            # Write to MS format
            output_file = os.path.join(output_dir, f"{Path(hdf5_file).stem}.ms")
            uv_data.write_ms(output_file, clobber=True)
            
            print(f"Processed: {hdf5_file} -> {output_file}")
            
        except Exception as e:
            print(f"Error processing {hdf5_file}: {e}")
    """)
    
    print("\nEXAMPLE 3: VALIDATION AND COMPARISON")
    print("-" * 35)
    print("""
# Validate antenna positions before processing:

def validate_antenna_positions(hdf5_file: str) -> bool:
    \"\"\"Validate antenna positions and log differences.\"\"\"
    try:
        # Read HDF5 file
        uv_data = UVData()
        uv_data.read(hdf5_file, file_type='uvh5')
        
        # Initialize swapper
        swapper = AntennaPositionSwapper()
        
        # Compare positions
        comparison = swapper.compare_positions(uv_data)
        
        if 'error' in comparison:
            logger.error(f"Position comparison failed: {comparison['error']}")
            return False
        
        # Log differences
        if comparison['position_differences']:
            diff = comparison['position_differences']
            logger.info(f"Position differences - Max: {diff['max_diff']:.3f}m, "
                       f"Mean: {diff['mean_diff']:.3f}m, RMS: {diff['rms_diff']:.3f}m")
        
        return True
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False
    """)


if __name__ == "__main__":
    demonstrate_integration()
    show_integration_examples()
