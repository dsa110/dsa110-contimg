"""
CASA Calibration Pipeline for DSA-110

This module provides comprehensive CASA-based calibration functionality
for the DSA-110 continuum imaging pipeline, including bandpass calibration,
gain calibration, and RFI flagging.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u

from casatools import ms, calanalysis
from casatasks import listobs, flagdata, bandpass, gaincal, applycal, gencal

from dsa110.utils.logging import get_logger
from dsa110.telescope.dsa110 import get_telescope_location, get_valid_antennas
from dsa110.data_ingestion.skymodel import SkyModelManager

logger = get_logger(__name__)


class CASACalibrationPipeline:
    """
    Comprehensive CASA calibration pipeline for DSA-110.
    
    This class provides a complete calibration workflow using CASA tools,
    including RFI flagging, bandpass calibration, and gain calibration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the CASA calibration pipeline.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.cal_config = config.get('calibration', {})
        self.paths_config = config.get('paths', {})
        self.telescope_config = config.get('telescope', {})
        
        # Initialize CASA tools with proper cleanup tracking
        self.ms_tool = None
        self.cal_tool = None
        self._initialize_tools()
        
        # Set up paths
        self.cal_tables_dir = Path(self.paths_config.get('cal_tables_dir', 'cal_tables'))
        self.cal_tables_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize sky model manager
        self.skymodel_manager = SkyModelManager(config)
        
        # Calibration parameters
        self.rfi_config = self.cal_config.get('rfi_flagging', {})
        self.bandpass_config = self.cal_config.get('bandpass', {})
        self.gain_config = self.cal_config.get('gain', {})
        
    async def run_complete_calibration(self, ms_path: str, 
                                     calibrator_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Run complete calibration pipeline on a measurement set.
        
        Args:
            ms_path: Path to the measurement set
            calibrator_source: Optional calibrator source name
            
        Returns:
            Dictionary with calibration results and table paths
        """
        logger.info(f"Starting complete calibration for {os.path.basename(ms_path)}")
        
        results = {
            'ms_path': ms_path,
            'success': False,
            'rfi_table': None,
            'bandpass_table': None,
            'gain_table': None,
            'errors': []
        }
        
        try:
            # Step 1: Initial data inspection
            logger.info("Step 1: Initial data inspection")
            inspection_result = await self._inspect_data(ms_path)
            if not inspection_result['success']:
                results['errors'].append("Data inspection failed")
                return results
            
            # Step 2: RFI flagging
            logger.info("Step 2: RFI flagging")
            rfi_result = await self._run_rfi_flagging(ms_path)
            results['rfi_table'] = rfi_result.get('table_path')
            
            # Step 3: Bandpass calibration
            logger.info("Step 3: Bandpass calibration")
            if calibrator_source:
                bp_result = await self._run_bandpass_calibration(ms_path, calibrator_source)
                results['bandpass_table'] = bp_result.get('table_path')
            else:
                logger.warning("No calibrator source specified, skipping bandpass calibration")
            
            # Step 4: Gain calibration
            logger.info("Step 4: Gain calibration")
            gain_result = await self._run_gain_calibration(ms_path, calibrator_source)
            results['gain_table'] = gain_result.get('table_path')
            
            # Step 5: Apply calibration
            logger.info("Step 5: Apply calibration")
            apply_result = await self._apply_calibration(ms_path, results)
            
            if apply_result['success']:
                results['success'] = True
                logger.info("Complete calibration pipeline finished successfully")
            else:
                results['errors'].extend(apply_result.get('errors', []))
                
        except Exception as e:
            logger.error(f"Calibration pipeline failed: {e}")
            results['errors'].append(str(e))
        finally:
            self.cleanup_tools()
            
        return results
    
    def _initialize_tools(self):
        """Initialize CASA tools with proper error handling."""
        try:
            self.ms_tool = ms()
            self.cal_tool = calanalysis()
        except Exception as e:
            logger.error(f"Failed to initialize CASA tools: {e}")
            self.cleanup_tools()
            raise
    
    async def _inspect_data(self, ms_path: str) -> Dict[str, Any]:
        """
        Inspect measurement set data quality and structure.
        
        Args:
            ms_path: Path to the measurement set
            
        Returns:
            Dictionary with inspection results
        """
        try:
            # Open MS with proper cleanup
            self.ms_tool.open(ms_path)
            
            try:
                # Get basic information
                n_rows = self.ms_tool.nrow()
                summary = self.ms_tool.summary()
                
                # Get antenna information
                antenna_info = summary.get('antenna', {})
                n_antennas = len(antenna_info) if antenna_info else 0
                
                # Get spectral window information
                spw_info = summary.get('spectralWindow', {})
                n_spws = len(spw_info) if spw_info else 0
                
                # Get field information
                field_info = summary.get('field', {})
                n_fields = len(field_info) if field_info else 0
                
                logger.info(f"Data inspection: {n_rows:,} rows, {n_antennas} antennas, {n_spws} SPWs, {n_fields} fields")
                
                return {
                    'success': True,
                    'n_rows': n_rows,
                    'n_antennas': n_antennas,
                    'n_spws': n_spws,
                    'n_fields': n_fields,
                    'summary': summary
                }
            finally:
                # Always close MS
                try:
                    self.ms_tool.close()
                except Exception as close_e:
                    logger.warning(f"Failed to close MS tool: {close_e}")
            
        except Exception as e:
            logger.error(f"Data inspection failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_rfi_flagging(self, ms_path: str) -> Dict[str, Any]:
        """
        Run RFI flagging on the measurement set.
        
        Args:
            ms_path: Path to the measurement set
            
        Returns:
            Dictionary with RFI flagging results
        """
        try:
            # RFI flagging parameters - simplified for DSA-110
            rfi_params = {
                'vis': ms_path,
                'mode': 'rflag',
                'datacolumn': 'DATA',
                'timecutoff': self.rfi_config.get('timecutoff', 3.0),  # More conservative
                'freqcutoff': self.rfi_config.get('freqcutoff', 3.0),  # More conservative
                'timefit': 'line',
                'freqfit': 'line',
                'flagdimension': 'freqtime',
                'extendflags': True,
                'extendpols': True,
                'growaround': False,  # Disable to avoid over-flagging
                'flagnearfreq': False,  # Disable to avoid over-flagging
                'flagneartime': False,  # Disable to avoid over-flagging
                'display': 'none',
                'flagbackup': True
            }
            
            # Run RFI flagging
            flagdata(**rfi_params)
            
            logger.info("RFI flagging completed successfully")
            
            return {
                'success': True,
                'table_path': None,  # RFI flagging modifies the MS directly
                'message': 'RFI flagging applied to measurement set'
            }
            
        except Exception as e:
            logger.error(f"RFI flagging failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_bandpass_calibration(self, ms_path: str, 
                                      calibrator_source: str) -> Dict[str, Any]:
        """
        Run bandpass calibration.
        
        Args:
            ms_path: Path to the measurement set
            calibrator_source: Calibrator source name
            
        Returns:
            Dictionary with bandpass calibration results
        """
        try:
            # Generate bandpass table path
            bp_table = self.cal_tables_dir / f"{Path(ms_path).stem}_bandpass.table"
            
            # Bandpass calibration parameters - optimized for DSA-110
            bp_params = {
                'vis': ms_path,
                'caltable': str(bp_table),
                'field': calibrator_source,
                'refant': self.bandpass_config.get('refant', '0'),
                'solint': self.bandpass_config.get('solint', 'inf'),
                'combine': self.bandpass_config.get('combine', 'scan'),
                'minsnr': self.bandpass_config.get('minsnr', 0.5),  # Much lower SNR threshold
                'solnorm': True,
                'bandtype': 'B',
                'fillgaps': 0,
                'gaintable': '',
                'gainfield': '',
                'interp': '',
                'spwmap': [],
                'append': False
            }
            
            # Run bandpass calibration
            bandpass(**bp_params)
            
            logger.info(f"Bandpass calibration completed: {bp_table}")
            
            return {
                'success': True,
                'table_path': str(bp_table),
                'message': f'Bandpass calibration table created: {bp_table.name}'
            }
            
        except Exception as e:
            logger.error(f"Bandpass calibration failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_gain_calibration(self, ms_path: str, 
                                  calibrator_source: str) -> Dict[str, Any]:
        """
        Run gain calibration.
        
        Args:
            ms_path: Path to the measurement set
            calibrator_source: Calibrator source name
            
        Returns:
            Dictionary with gain calibration results
        """
        try:
            # Generate gain table path
            gain_table = self.cal_tables_dir / f"{Path(ms_path).stem}_gain.table"
            
            # Gain calibration parameters - optimized for DSA-110
            gain_params = {
                'vis': ms_path,
                'caltable': str(gain_table),
                'field': calibrator_source,
                'refant': self.gain_config.get('refant', '0'),
                'solint': self.gain_config.get('solint', 'inf'),
                'combine': self.gain_config.get('combine', 'scan'),
                'minsnr': self.gain_config.get('minsnr', 0.3),  # Much lower SNR threshold
                'solnorm': True,
                'calmode': 'p',
                'gaintable': '',
                'gainfield': '',
                'interp': '',
                'spwmap': [],
                'append': False
            }
            
            # Run gain calibration
            gaincal(**gain_params)
            
            logger.info(f"Gain calibration completed: {gain_table}")
            
            return {
                'success': True,
                'table_path': str(gain_table),
                'message': f'Gain calibration table created: {gain_table.name}'
            }
            
        except Exception as e:
            logger.error(f"Gain calibration failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _apply_calibration(self, ms_path: str, 
                               calibration_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply calibration tables to the measurement set.
        
        Args:
            ms_path: Path to the measurement set
            calibration_results: Results from calibration steps
            
        Returns:
            Dictionary with application results
        """
        try:
            # Collect calibration tables
            gaintables = []
            
            if calibration_results.get('bandpass_table'):
                gaintables.append(calibration_results['bandpass_table'])
            
            if calibration_results.get('gain_table'):
                gaintables.append(calibration_results['gain_table'])
            
            if not gaintables:
                logger.warning("No calibration tables to apply")
                return {'success': True, 'message': 'No calibration tables to apply'}
            
            # Apply calibration parameters
            apply_params = {
                'vis': ms_path,
                'gaintable': gaintables,
                'gainfield': '',
                'interp': '',
                'spwmap': [],
                'calwt': True,
                'flagbackup': True,
                'applymode': 'calonly'  # Prevents UVW coordinate modification
            }
            
            # Apply calibration
            applycal(**apply_params)
            
            logger.info(f"Applied {len(gaintables)} calibration tables to {os.path.basename(ms_path)}")
            
            return {
                'success': True,
                'message': f'Applied {len(gaintables)} calibration tables',
                'applied_tables': gaintables
            }
            
        except Exception as e:
            logger.error(f"Calibration application failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def create_calibration_plots(self, ms_path: str, 
                                     output_dir: str) -> Dict[str, Any]:
        """
        Create calibration diagnostic plots.
        
        Note: plotms is not available in this CASA version, so we'll use
        alternative plotting methods or skip plotting for now.
        
        Args:
            ms_path: Path to the measurement set
            output_dir: Directory for output plots
            
        Returns:
            Dictionary with plot creation results
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # For now, we'll skip plotting since plotms is not available
            # In a production environment, you would implement alternative
            # plotting methods or use external plotting tools
            
            logger.info(f"Plotting skipped - plotms not available in this CASA version")
            
            return {
                'success': True,
                'plots_created': [],
                'output_dir': str(output_path),
                'message': 'Plotting skipped - plotms not available'
            }
            
        except Exception as e:
            logger.error(f"Plot creation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup_calibration_tables(self, keep_recent: int = 5):
        """
        Clean up old calibration tables, keeping only the most recent ones.
        
        Args:
            keep_recent: Number of recent tables to keep
        """
        try:
            # Find all calibration tables
            bp_tables = list(self.cal_tables_dir.glob("*_bandpass.table"))
            gain_tables = list(self.cal_tables_dir.glob("*_gain.table"))
            
            # Sort by modification time (newest first)
            all_tables = sorted(bp_tables + gain_tables, 
                              key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove old tables
            tables_to_remove = all_tables[keep_recent:]
            for table in tables_to_remove:
                table.unlink()
                logger.info(f"Removed old calibration table: {table.name}")
            
            logger.info(f"Cleaned up {len(tables_to_remove)} old calibration tables")
            
        except Exception as e:
            logger.error(f"Calibration table cleanup failed: {e}")
    
    def cleanup_tools(self):
        """Clean up CASA tools explicitly."""
        if hasattr(self, 'ms_tool') and self.ms_tool:
            try:
                self.ms_tool.done()
            except Exception as e:
                logger.error(f"Failed to cleanup ms_tool: {e}")
            finally:
                self.ms_tool = None
        
        if hasattr(self, 'cal_tool') and self.cal_tool:
            try:
                self.cal_tool.done()
            except Exception as e:
                logger.error(f"Failed to cleanup cal_tool: {e}")
            finally:
                self.cal_tool = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup_tools()
    
    def __del__(self):
        """Clean up CASA tools."""
        self.cleanup_tools()
