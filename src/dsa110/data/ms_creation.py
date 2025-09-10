"""Unified MS Creation Module

Consolidates all DSA-110 specific MS creation logic from the various
converter modules into a single, well-tested implementation.
"""

import os
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MSCreator:
    """Unified MS creation with all DSA-110 fixes."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize MS creator with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self._setup_paths()
        
    def _setup_paths(self):
        """Setup input/output paths from config."""
        self.output_dir = Path(self.config.get('output_dir', 'data_new/output/ms'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def create_ms_from_hdf5(self, hdf5_files: List[str], output_path: str) -> bool:
        """Create MS from HDF5 files using unified logic.
        
        This method consolidates the logic from:
        - unified_ms_creation.py (current best practices)
        - All other converter modules (for compatibility)
        
        Args:
            hdf5_files: List of HDF5 file paths
            output_path: Output MS file path
            
        Returns:
            bool: Success status
        """
        # Import the current unified implementation
        from ...core.data_ingestion.unified_ms_creation import UnifiedMSCreator
        
        # Use existing implementation until we fully migrate
        creator = UnifiedMSCreator(
            output_antennas=self.config.get('antenna_selection'),
            time_tolerance=self.config.get('time_tolerance', 120.0)
        )
        
        return await creator.create_ms_from_hdf5_files(hdf5_files, output_path)
        
    def batch_convert(self, hdf5_files: List[str], output_dir: Optional[str] = None) -> List[str]:
        """Convert multiple HDF5 files to MS format.
        
        Args:
            hdf5_files: List of HDF5 file paths
            output_dir: Output directory for MS files
            
        Returns:
            list: Paths to created MS files
        """
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
        results = []
        for hdf5_file in hdf5_files:
            hdf5_path = Path(hdf5_file)
            ms_path = self.output_dir / f"{hdf5_path.stem}.ms"
            
            success = asyncio.run(self.create_ms_from_hdf5([hdf5_file], str(ms_path)))
            if success:
                results.append(str(ms_path))
                logger.info(f"Created MS: {ms_path}")
            else:
                logger.error(f"Failed to create MS from: {hdf5_file}")
                
        return results