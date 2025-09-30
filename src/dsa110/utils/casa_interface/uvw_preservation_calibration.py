"""
UVW Coordinate Preservation Calibration Pipeline

This module provides a calibration pipeline that preserves UVW coordinates
during calibration operations to prevent the issues observed with applymode='calflag'.
"""

import os
import logging
import asyncio
import shutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import numpy as np
from casatools import table
from casatasks import applycal

from core.utils.logging import get_logger

logger = get_logger(__name__)


class UVWPreservationCalibrationPipeline:
    """
    Calibration pipeline that preserves UVW coordinates during calibration.
    
    This pipeline ensures that UVW coordinates are not modified during
    calibration operations by using safe applycal parameters and
    implementing UVW coordinate backup/restore functionality.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the UVW preservation calibration pipeline.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.cal_config = config.get('calibration', {})
        self.paths_config = config.get('paths', {})
        
    async def apply_calibration_with_uvw_preservation(self, ms_path: str, 
                                                    calibration_tables: List[str]) -> Dict[str, Any]:
        """
        Apply calibration while preserving UVW coordinates.
        
        This method:
        1. Backs up original UVW coordinates
        2. Applies calibration with safe parameters
        3. Restores UVW coordinates if they were modified
        4. Validates the result
        
        Args:
            ms_path: Path to the MS file
            calibration_tables: List of calibration tables to apply
            
        Returns:
            Dictionary with application results
        """
        logger.info(f"Applying calibration with UVW preservation to {os.path.basename(ms_path)}")
        
        results = {
            'ms_path': ms_path,
            'success': False,
            'uvw_preserved': False,
            'uvw_restored': False,
            'errors': []
        }
        
        try:
            # Step 1: Backup original UVW coordinates
            logger.info("Step 1: Backing up original UVW coordinates")
            original_uvw = await self._backup_uvw_coordinates(ms_path)
            if original_uvw is None:
                results['errors'].append("Failed to backup UVW coordinates")
                return results
            
            # Step 2: Apply calibration with safe parameters
            logger.info("Step 2: Applying calibration with safe parameters")
            apply_result = await self._apply_safe_calibration(ms_path, calibration_tables)
            if not apply_result['success']:
                results['errors'].extend(apply_result.get('errors', []))
                return results
            
            # Step 3: Check if UVW coordinates were modified
            logger.info("Step 3: Checking UVW coordinate integrity")
            uvw_check = await self._check_uvw_integrity(ms_path, original_uvw)
            
            if uvw_check['modified']:
                logger.warning("UVW coordinates were modified during calibration - restoring")
                # Step 4: Restore UVW coordinates
                restore_result = await self._restore_uvw_coordinates(ms_path, original_uvw)
                if restore_result['success']:
                    results['uvw_restored'] = True
                    logger.info("Successfully restored UVW coordinates")
                else:
                    results['errors'].append("Failed to restore UVW coordinates")
                    return results
            else:
                results['uvw_preserved'] = True
                logger.info("UVW coordinates were preserved during calibration")
            
            # Step 5: Validate final result
            logger.info("Step 5: Validating final calibration result")
            validation_result = await self._validate_calibration_result(ms_path, original_uvw)
            results['validation'] = validation_result
            
            if validation_result['valid']:
                results['success'] = True
                logger.info("Calibration with UVW preservation completed successfully")
            else:
                results['errors'].append("Calibration validation failed")
                
        except Exception as e:
            logger.error(f"UVW preservation calibration failed: {e}")
            results['errors'].append(str(e))
            
        return results
    
    async def _backup_uvw_coordinates(self, ms_path: str) -> Optional[np.ndarray]:
        """
        Backup UVW coordinates from MS file.
        
        Args:
            ms_path: Path to the MS file
            
        Returns:
            Original UVW coordinates array, or None if failed
        """
        try:
            table_tool = table()
            table_tool.open(ms_path)
            
            uvw_data = table_tool.getcol('UVW')
            logger.info(f"Backed up UVW coordinates with shape: {uvw_data.shape}")
            
            table_tool.close()
            return uvw_data
            
        except Exception as e:
            logger.error(f"Failed to backup UVW coordinates: {e}")
            return None
    
    async def _apply_safe_calibration(self, ms_path: str, calibration_tables: List[str]) -> Dict[str, Any]:
        """
        Apply calibration using safe parameters that don't modify UVW coordinates.
        
        Args:
            ms_path: Path to the MS file
            calibration_tables: List of calibration tables to apply
            
        Returns:
            Dictionary with application results
        """
        try:
            if not calibration_tables:
                logger.warning("No calibration tables to apply")
                return {'success': True, 'message': 'No calibration tables to apply'}
            
            # Use safe applycal parameters
            apply_params = {
                'vis': ms_path,
                'gaintable': calibration_tables,
                'gainfield': [],
                'interp': ['nearest', 'linear'],
                'spwmap': [],
                'calwt': False,
                'flagbackup': False,
                'applymode': 'calonly'  # This prevents UVW coordinate modification
            }
            
            # Apply calibration
            applycal(**apply_params)
            
            logger.info(f"Applied {len(calibration_tables)} calibration tables safely")
            
            return {
                'success': True,
                'message': f'Applied {len(calibration_tables)} calibration tables safely',
                'applied_tables': calibration_tables
            }
            
        except Exception as e:
            logger.error(f"Safe calibration application failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _check_uvw_integrity(self, ms_path: str, original_uvw: np.ndarray) -> Dict[str, Any]:
        """
        Check if UVW coordinates were modified during calibration.
        
        Args:
            ms_path: Path to the MS file
            original_uvw: Original UVW coordinates
            
        Returns:
            Dictionary with integrity check results
        """
        try:
            table_tool = table()
            table_tool.open(ms_path)
            
            current_uvw = table_tool.getcol('UVW')
            
            # Check if UVW coordinates are identical
            uvw_diff = np.abs(original_uvw - current_uvw)
            max_diff = np.max(uvw_diff)
            mean_diff = np.mean(uvw_diff)
            
            # Consider modified if difference is > 1e-10 (numerical precision)
            modified = max_diff > 1e-10
            
            logger.info(f"UVW integrity check: max_diff={max_diff:.6f}m, mean_diff={mean_diff:.6f}m, modified={modified}")
            
            table_tool.close()
            
            return {
                'modified': modified,
                'max_difference': max_diff,
                'mean_difference': mean_diff,
                'current_uvw': current_uvw
            }
            
        except Exception as e:
            logger.error(f"UVW integrity check failed: {e}")
            return {'modified': True, 'error': str(e)}
    
    async def _restore_uvw_coordinates(self, ms_path: str, original_uvw: np.ndarray) -> Dict[str, Any]:
        """
        Restore original UVW coordinates to MS file.
        
        Args:
            ms_path: Path to the MS file
            original_uvw: Original UVW coordinates to restore
            
        Returns:
            Dictionary with restoration results
        """
        try:
            table_tool = table()
            table_tool.open(ms_path, nomodify=False)
            
            # Restore UVW coordinates
            table_tool.putcol('UVW', original_uvw)
            
            # Verify restoration
            restored_uvw = table_tool.getcol('UVW')
            uvw_diff = np.abs(original_uvw - restored_uvw)
            max_diff = np.max(uvw_diff)
            
            if max_diff < 1e-10:
                logger.info("UVW coordinates successfully restored")
                success = True
            else:
                logger.warning(f"UVW restoration may have failed - max_diff: {max_diff:.6f}m")
                success = False
            
            table_tool.close()
            
            return {
                'success': success,
                'max_difference': max_diff,
                'message': 'UVW coordinates restored' if success else 'UVW restoration may have failed'
            }
            
        except Exception as e:
            logger.error(f"UVW coordinate restoration failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _validate_calibration_result(self, ms_path: str, original_uvw: np.ndarray) -> Dict[str, Any]:
        """
        Validate the final calibration result.
        
        Args:
            ms_path: Path to the MS file
            original_uvw: Original UVW coordinates for comparison
            
        Returns:
            Dictionary with validation results
        """
        try:
            table_tool = table()
            table_tool.open(ms_path)
            
            current_uvw = table_tool.getcol('UVW')
            
            # Check UVW coordinate integrity
            uvw_diff = np.abs(original_uvw - current_uvw)
            max_diff = np.max(uvw_diff)
            
            # Calculate baseline lengths
            if current_uvw.shape[0] == 3:
                baseline_lengths = np.sqrt(current_uvw[0]**2 + current_uvw[1]**2 + current_uvw[2]**2)
            else:
                baseline_lengths = np.sqrt(current_uvw[:, 0]**2 + current_uvw[:, 1]**2 + current_uvw[:, 2]**2)
            
            mean_baseline = np.mean(baseline_lengths)
            max_baseline = np.max(baseline_lengths)
            
            # Validation criteria
            uvw_preserved = max_diff < 1e-10
            baseline_reasonable = mean_baseline > 100 and max_baseline > 1000  # DSA-110 criteria
            
            valid = uvw_preserved and baseline_reasonable
            
            logger.info(f"Calibration validation: uvw_preserved={uvw_preserved}, baseline_reasonable={baseline_reasonable}, valid={valid}")
            
            table_tool.close()
            
            return {
                'valid': valid,
                'uvw_preserved': uvw_preserved,
                'baseline_reasonable': baseline_reasonable,
                'max_uvw_difference': max_diff,
                'mean_baseline': mean_baseline,
                'max_baseline': max_baseline
            }
            
        except Exception as e:
            logger.error(f"Calibration validation failed: {e}")
            return {'valid': False, 'error': str(e)}
