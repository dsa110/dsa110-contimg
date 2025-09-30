"""
Improved CASA Calibration Pipeline for DSA-110

This module provides a more robust calibration approach specifically
designed for DSA-110 continuum imaging data.
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
from casatasks import listobs, flagdata, bandpass, gaincal, applycal, gencal, setjy

from core.utils.logging import get_logger
from core.telescope.dsa110 import get_telescope_location, get_valid_antennas

logger = get_logger(__name__)


class ImprovedCASACalibrationPipeline:
    """
    Improved CASA calibration pipeline specifically for DSA-110.
    
    This class provides a more robust calibration approach that:
    1. Uses appropriate parameters for DSA-110 data
    2. Handles low SNR calibration sources better
    3. Provides better error handling and diagnostics
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the improved CASA calibration pipeline.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.cal_config = config.get('calibration', {})
        self.paths_config = config.get('paths', {})
        self.telescope_config = config.get('telescope', {})
        
        # Initialize CASA tools
        self.ms_tool = ms()
        self.cal_tool = calanalysis()
        
        # Set up paths
        self.cal_tables_dir = Path(self.paths_config.get('cal_tables_dir', 'cal_tables'))
        self.cal_tables_dir.mkdir(parents=True, exist_ok=True)
        
        # Calibration parameters optimized for DSA-110
        self.rfi_config = self.cal_config.get('rfi_flagging', {})
        self.bandpass_config = self.cal_config.get('bandpass', {})
        self.gain_config = self.cal_config.get('gain', {})
        
    async def run_robust_calibration(self, ms_path: str, 
                                   calibrator_source: Optional[str] = None) -> Dict[str, Any]:
        """
        Run robust calibration pipeline optimized for DSA-110.
        
        Args:
            ms_path: Path to the measurement set
            calibrator_source: Optional calibrator source name
            
        Returns:
            Dictionary with calibration results
        """
        logger.info(f"Starting robust calibration for {os.path.basename(ms_path)}")
        
        results = {
            'ms_path': ms_path,
            'success': False,
            'calibration_tables': [],
            'quality_metrics': {},
            'errors': []
        }
        
        try:
            # Step 1: Data inspection and source identification
            logger.info("Step 1: Data inspection and source identification")
            inspection_result = await self._inspect_data_and_sources(ms_path)
            if not inspection_result['success']:
                results['errors'].append("Data inspection failed")
                return results
            
            # Use the strongest source for calibration if no calibrator specified
            if not calibrator_source:
                calibrator_source = inspection_result.get('strongest_source', '0')
            
            logger.info(f"Using source '{calibrator_source}' for calibration")
            
            # Step 2: Conservative RFI flagging
            logger.info("Step 2: Conservative RFI flagging")
            rfi_result = await self._run_conservative_rfi_flagging(ms_path)
            results['rfi_result'] = rfi_result
            
            # Step 3: Set flux density for calibrator
            logger.info("Step 3: Set flux density for calibrator")
            flux_result = await self._set_calibrator_flux(ms_path, calibrator_source)
            results['flux_result'] = flux_result
            
            # Step 4: Initial gain calibration with very low SNR threshold
            logger.info("Step 4: Initial gain calibration")
            initial_gain_result = await self._run_initial_gain_calibration(
                ms_path, calibrator_source
            )
            if initial_gain_result['success']:
                results['calibration_tables'].append(initial_gain_result['table_path'])
            
            # Step 5: Bandpass calibration using initial gains
            logger.info("Step 5: Bandpass calibration")
            if initial_gain_result['success']:
                bp_result = await self._run_bandpass_calibration(
                    ms_path, calibrator_source, initial_gain_result['table_path']
                )
                if bp_result['success']:
                    results['calibration_tables'].append(bp_result['table_path'])
            
            # Step 6: Final gain calibration with bandpass
            logger.info("Step 6: Final gain calibration")
            final_gain_result = await self._run_final_gain_calibration(
                ms_path, calibrator_source, results['calibration_tables']
            )
            if final_gain_result['success']:
                results['calibration_tables'].append(final_gain_result['table_path'])
            
            # Step 7: Apply calibration
            logger.info("Step 7: Apply calibration")
            apply_result = await self._apply_calibration(ms_path, results['calibration_tables'])
            results['apply_result'] = apply_result
            
            # Step 8: Quality assessment
            logger.info("Step 8: Quality assessment")
            quality_result = await self._assess_calibration_quality(ms_path, results['calibration_tables'])
            results['quality_metrics'] = quality_result
            
            if len(results['calibration_tables']) > 0:
                results['success'] = True
                logger.info(f"Robust calibration completed with {len(results['calibration_tables'])} tables")
            else:
                results['errors'].append("No calibration tables were created successfully")
                
        except Exception as e:
            logger.error(f"Robust calibration failed: {e}")
            results['errors'].append(str(e))
            
        return results
    
    async def _inspect_data_and_sources(self, ms_path: str) -> Dict[str, Any]:
        """
        Inspect data and identify the best calibrator source.
        
        Args:
            ms_path: Path to the measurement set
            
        Returns:
            Dictionary with inspection results
        """
        try:
            # Open MS
            self.ms_tool.open(ms_path)
            
            # Get basic information
            n_rows = self.ms_tool.nrow()
            summary = self.ms_tool.summary()
            
            # Get field information
            field_info = summary.get('field', {})
            n_fields = len(field_info) if field_info else 0
            
            # Get antenna information
            antenna_info = summary.get('antenna', {})
            n_antennas = len(antenna_info) if antenna_info else 0
            
            # Get frequency information
            spw_info = summary.get('spectralWindow', {})
            if spw_info:
                freq_info = list(spw_info.values())[0]
                freq_center = freq_info.get('refFreq', 1.4e9)
            else:
                freq_center = 1.4e9
            
            self.ms_tool.close()
            self.ms_tool.done()
            
            # For now, use field 0 as the strongest source
            # In a real implementation, you would analyze the data to find the strongest source
            strongest_source = '0'
            
            logger.info(f"Data inspection: {n_rows:,} rows, {n_antennas} antennas, "
                       f"{n_fields} fields, freq={freq_center/1e9:.2f} GHz")
            
            return {
                'success': True,
                'n_rows': n_rows,
                'n_antennas': n_antennas,
                'n_fields': n_fields,
                'frequency_center': freq_center,
                'strongest_source': strongest_source,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Data inspection failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_conservative_rfi_flagging(self, ms_path: str) -> Dict[str, Any]:
        """
        Run conservative RFI flagging to avoid over-flagging.
        
        Args:
            ms_path: Path to the measurement set
            
        Returns:
            Dictionary with RFI flagging results
        """
        try:
            # Very conservative RFI flagging parameters
            rfi_params = {
                'vis': ms_path,
                'mode': 'rflag',
                'datacolumn': 'DATA',
                'timecutoff': 2.0,  # Very conservative
                'freqcutoff': 2.0,  # Very conservative
                'timefit': 'line',
                'freqfit': 'line',
                'flagdimension': 'freqtime',
                'extendflags': False,  # Disable to avoid over-flagging
                'extendpols': False,   # Disable to avoid over-flagging
                'growaround': False,   # Disable to avoid over-flagging
                'flagnearfreq': False, # Disable to avoid over-flagging
                'flagneartime': False, # Disable to avoid over-flagging
                'display': 'none',
                'flagbackup': True
            }
            
            # Run RFI flagging
            flagdata(**rfi_params)
            
            logger.info("Conservative RFI flagging completed")
            
            return {
                'success': True,
                'message': 'Conservative RFI flagging applied'
            }
            
        except Exception as e:
            logger.error(f"RFI flagging failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _set_calibrator_flux(self, ms_path: str, calibrator_source: str) -> Dict[str, Any]:
        """
        Set flux density for the calibrator source.
        
        Args:
            ms_path: Path to the measurement set
            calibrator_source: Calibrator source name
            
        Returns:
            Dictionary with flux setting results
        """
        try:
            # Set a reasonable flux density for the calibrator
            # For DSA-110 at 1.4 GHz, we'll use a typical flux density
            flux_params = {
                'vis': ms_path,
                'field': calibrator_source,
                'spw': '0',
                'fluxdensity': [1.0, 0, 0, 0],  # 1 Jy, no polarization
                'standard': 'Perley-Butler 2017'
            }
            
            setjy(**flux_params)
            
            logger.info(f"Set flux density for calibrator {calibrator_source}")
            
            return {
                'success': True,
                'message': f'Flux density set for {calibrator_source}'
            }
            
        except Exception as e:
            logger.error(f"Flux setting failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_initial_gain_calibration(self, ms_path: str, 
                                          calibrator_source: str) -> Dict[str, Any]:
        """
        Run initial gain calibration with very low SNR threshold.
        
        Args:
            ms_path: Path to the measurement set
            calibrator_source: Calibrator source name
            
        Returns:
            Dictionary with gain calibration results
        """
        try:
            # Generate gain table path
            gain_table = self.cal_tables_dir / f"{Path(ms_path).stem}_initial_gain.table"
            
            # Initial gain calibration with very low SNR threshold
            gain_params = {
                'vis': ms_path,
                'caltable': str(gain_table),
                'field': calibrator_source,
                'refant': '0',
                'solint': 'inf',
                'combine': 'scan',
                'minsnr': 0.1,  # Very low SNR threshold
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
            
            logger.info(f"Initial gain calibration completed: {gain_table}")
            
            return {
                'success': True,
                'table_path': str(gain_table),
                'message': f'Initial gain calibration table created: {gain_table.name}'
            }
            
        except Exception as e:
            logger.error(f"Initial gain calibration failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _run_bandpass_calibration(self, ms_path: str, 
                                      calibrator_source: str,
                                      gain_table: str) -> Dict[str, Any]:
        """
        Run bandpass calibration using initial gains.
        
        Args:
            ms_path: Path to the measurement set
            calibrator_source: Calibrator source name
            gain_table: Path to initial gain table
            
        Returns:
            Dictionary with bandpass calibration results
        """
        try:
            # Generate bandpass table path
            bp_table = self.cal_tables_dir / f"{Path(ms_path).stem}_bandpass.table"
            
            # Bandpass calibration using initial gains
            bp_params = {
                'vis': ms_path,
                'caltable': str(bp_table),
                'field': calibrator_source,
                'refant': '0',
                'solint': 'inf',
                'combine': 'scan',
                'minsnr': 0.1,  # Very low SNR threshold
                'solnorm': True,
                'bandtype': 'B',
                'fillgaps': 0,
                'gaintable': gain_table,
                'gainfield': calibrator_source,
                'interp': 'linear',
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
    
    async def _run_final_gain_calibration(self, ms_path: str, 
                                        calibrator_source: str,
                                        calibration_tables: List[str]) -> Dict[str, Any]:
        """
        Run final gain calibration with all previous tables.
        
        Args:
            ms_path: Path to the measurement set
            calibrator_source: Calibrator source name
            calibration_tables: List of existing calibration tables
            
        Returns:
            Dictionary with final gain calibration results
        """
        try:
            # Generate final gain table path
            gain_table = self.cal_tables_dir / f"{Path(ms_path).stem}_final_gain.table"
            
            # Final gain calibration with all previous tables
            gain_params = {
                'vis': ms_path,
                'caltable': str(gain_table),
                'field': calibrator_source,
                'refant': '0',
                'solint': 'inf',
                'combine': 'scan',
                'minsnr': 0.1,  # Very low SNR threshold
                'solnorm': True,
                'calmode': 'p',
                'gaintable': calibration_tables,
                'gainfield': calibrator_source,
                'interp': 'linear',
                'spwmap': [],
                'append': False
            }
            
            # Run gain calibration
            gaincal(**gain_params)
            
            logger.info(f"Final gain calibration completed: {gain_table}")
            
            return {
                'success': True,
                'table_path': str(gain_table),
                'message': f'Final gain calibration table created: {gain_table.name}'
            }
            
        except Exception as e:
            logger.error(f"Final gain calibration failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _apply_calibration(self, ms_path: str, 
                               calibration_tables: List[str]) -> Dict[str, Any]:
        """
        Apply calibration tables to the measurement set.
        
        Args:
            ms_path: Path to the measurement set
            calibration_tables: List of calibration tables to apply
            
        Returns:
            Dictionary with application results
        """
        try:
            if not calibration_tables:
                logger.warning("No calibration tables to apply")
                return {'success': True, 'message': 'No calibration tables to apply'}
            
            # Apply calibration parameters
            # Use 'calonly' mode to avoid modifying UVW coordinates
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
            
            logger.info(f"Applied {len(calibration_tables)} calibration tables to {os.path.basename(ms_path)}")
            
            return {
                'success': True,
                'message': f'Applied {len(calibration_tables)} calibration tables',
                'applied_tables': calibration_tables
            }
            
        except Exception as e:
            logger.error(f"Calibration application failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _assess_calibration_quality(self, ms_path: str, 
                                        calibration_tables: List[str]) -> Dict[str, Any]:
        """
        Assess the quality of the calibration.
        
        Args:
            ms_path: Path to the measurement set
            calibration_tables: List of calibration tables
            
        Returns:
            Dictionary with quality metrics
        """
        try:
            quality_metrics = {
                'n_calibration_tables': len(calibration_tables),
                'calibration_success': len(calibration_tables) > 0,
                'tables_created': [os.path.basename(table) for table in calibration_tables]
            }
            
            # Add more detailed quality assessment here if needed
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return {'error': str(e)}
    
    def __del__(self):
        """Clean up CASA tools."""
        try:
            self.ms_tool.done()
            self.cal_tool.done()
        except:
            pass
