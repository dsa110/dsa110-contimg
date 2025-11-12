"""Unified Pipeline Orchestrator

Single orchestrator that consolidates the logic from multiple orchestrator
implementations into a clean, maintainable interface.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from ..data.ms_creation import MSCreator
from ..utils.config import ConfigManager
from ..utils.data_manager import DataManager

logger = logging.getLogger(__name__)

class Pipeline:
    """Main pipeline orchestrator for DSA-110 processing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize pipeline with configuration.
        
        Args:
            config: Configuration dictionary or path to config file
        """
        self.config_manager = ConfigManager(config)
        self.config = self.config_manager.get_config()
        self.data_manager = DataManager(self.config)
        
        # Initialize processing components
        self.ms_creator = MSCreator(self.config.get('ms_creation', {}))
        
    async def process_directory(self, hdf5_dir: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Process all HDF5 files in a directory.
        
        Args:
            hdf5_dir: Directory containing HDF5 files
            output_dir: Output directory (optional)
            
        Returns:
            dict: Processing results
        """
        hdf5_path = Path(hdf5_dir)
        if not hdf5_path.exists():
            raise FileNotFoundError(f"HDF5 directory not found: {hdf5_dir}")
            
        # Find HDF5 files
        hdf5_files = list(hdf5_path.glob("*.h5")) + list(hdf5_path.glob("*.hdf5"))
        if not hdf5_files:
            raise ValueError(f"No HDF5 files found in: {hdf5_dir}")
            
        logger.info(f"Found {len(hdf5_files)} HDF5 files to process")
        
        # Set output directory
        if output_dir:
            self.data_manager.set_output_dir(output_dir)
            
        results = {
            'input_files': [str(f) for f in hdf5_files],
            'ms_files': [],
            'calibration_tables': [],
            'images': [],
            'success': False
        }
        
        try:
            # Stage 1: Create Measurement Sets
            logger.info("Stage 1: Creating Measurement Sets")
            ms_files = await self._create_measurement_sets(hdf5_files)
            results['ms_files'] = ms_files
            
            if not ms_files:
                logger.error("No MS files created, stopping pipeline")
                return results
                
            # Stage 2: Calibration (placeholder for now)
            logger.info("Stage 2: Calibration (using existing implementation)")
            # TODO: Integrate existing calibration pipeline
            
            # Stage 3: Imaging (placeholder for now)  
            logger.info("Stage 3: Imaging (using existing implementation)")
            # TODO: Integrate existing imaging pipeline
            
            results['success'] = True
            logger.info("Pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            results['error'] = str(e)
            
        return results
        
    async def _create_measurement_sets(self, hdf5_files: List[Path]) -> List[str]:
        """Create measurement sets from HDF5 files.
        
        Args:
            hdf5_files: List of HDF5 file paths
            
        Returns:
            list: Created MS file paths
        """
        ms_files = []
        
        for hdf5_file in hdf5_files:
            ms_path = self.data_manager.get_ms_path(hdf5_file.stem)
            
            success = await self.ms_creator.create_ms_from_hdf5(
                [str(hdf5_file)], str(ms_path)
            )
            
            if success:
                ms_files.append(str(ms_path))
                logger.info(f"Created MS: {ms_path}")
            else:
                logger.error(f"Failed to create MS from: {hdf5_file}")
                
        return ms_files