# core/data_manager.py
"""
Data Manager for DSA-110 Pipeline

Centralized data management system that handles data lifecycle,
storage coordination, and data flow between pipeline stages.
"""

import os
import shutil
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

from .utils.logging import get_logger
from .utils.config_loader import ConfigLoader

logger = get_logger(__name__)


class DataManager:
    """
    Centralized data manager for pipeline data lifecycle.
    
    Handles:
    - Data staging and cleanup
    - Storage coordination between stages
    - Data retention policies
    - Disk space monitoring
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.paths = config.get('paths', {})
        self.retention = config.get('data_retention', {})
        
    async def stage_hdf5_data(self, source_dir: str, timestamp: str) -> str:
        """Stage HDF5 data for processing."""
        staging_dir = self.paths.get('hdf5_staging_dir', 'data/hdf5_staging')
        target_dir = os.path.join(staging_dir, timestamp)
        os.makedirs(target_dir, exist_ok=True)
        
        # Copy HDF5 files
        for file in os.listdir(source_dir):
            if file.endswith('.hdf5'):
                shutil.copy2(os.path.join(source_dir, file), target_dir)
        
        logger.info(f"Staged HDF5 data to {target_dir}")
        return target_dir
    
    async def cleanup_old_data(self) -> Dict[str, int]:
        """Clean up old data based on retention policies."""
        cleaned = {'hdf5': 0, 'ms': 0, 'images': 0, 'cal_tables': 0}
        
        # Clean HDF5 staging
        hdf5_retention_days = self.retention.get('hdf5_staging_days', 7)
        cleaned['hdf5'] = await self._cleanup_directory(
            self.paths.get('hdf5_staging_dir'), hdf5_retention_days
        )
        
        # Clean old MS files
        ms_retention_days = self.retention.get('ms_files_days', 30)
        cleaned['ms'] = await self._cleanup_directory(
            self.paths.get('ms_stage1_dir'), ms_retention_days
        )
        
        # Clean old images
        image_retention_days = self.retention.get('images_days', 90)
        cleaned['images'] = await self._cleanup_directory(
            self.paths.get('images_dir'), image_retention_days
        )
        
        return cleaned
    
    async def _cleanup_directory(self, directory: str, retention_days: int) -> int:
        """Clean up files older than retention period."""
        if not directory or not os.path.exists(directory):
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        cleaned_count = 0
        
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.getmtime(item_path) < cutoff_time.timestamp():
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to clean {item_path}: {e}")
        
        return cleaned_count
    
    def get_disk_usage(self) -> Dict[str, Dict[str, float]]:
        """Get disk usage for all data directories."""
        usage = {}
        
        for name, path in self.paths.items():
            if path and os.path.exists(path):
                total, used, free = shutil.disk_usage(path)
                usage[name] = {
                    'total_gb': total / (1024**3),
                    'used_gb': used / (1024**3),
                    'free_gb': free / (1024**3),
                    'usage_percent': (used / total) * 100
                }
        
        return usage