# core/pipeline/stages/calibration_stage.py
"""
Calibration stage for DSA-110 pipeline.

This module handles all calibration-related operations including
bandpass calibration, gain calibration, and calibration application.
"""

import os
import glob
import logging
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord

from ...utils.logging import get_logger
from ...telescope.dsa110 import get_telescope_location
from ..exceptions import CalibrationError
from ...data_ingestion.skymodel import SkyModelManager

# New imports for calibrator finder and sky model builder
from ...calibration.calibrator_finder import CalibratorFinder
from ...calibration.skymodel_builder import SkyModelBuilder

logger = get_logger(__name__)


class CalibrationStage:
    """
    Handles calibration operations for the pipeline.
    
    This class consolidates calibration logic from the original
    calibration.py module and provides a cleaner interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the calibration stage.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.cal_config = config.get('calibration', {})
        self.paths_config = config.get('paths', {})
        self.skymodel_manager = SkyModelManager(config)
        
        # Ensure calibration tables directory exists
        cal_tables_dir = self.paths_config.get('cal_tables_dir')
        if cal_tables_dir:
            os.makedirs(cal_tables_dir, exist_ok=True)

    # ---- Parameter builders (config-driven) ----
    def _build_bandpass_params(self, vis, caltable: str) -> Dict[str, Any]:
        bp = self.cal_config.get('bandpass', {})
        params: Dict[str, Any] = {
            'vis': vis,
            'caltable': caltable,
            'field': bp.get('field', ''),
            'refant': bp.get('refant', self.cal_config.get('bcal_refant', '')),
            'solint': bp.get('solint', 'inf'),
            'combine': bp.get('combine', 'scan'),
            'minsnr': bp.get('minsnr', 3.0),
            'solnorm': bp.get('solnorm', True),
            'bandtype': bp.get('bandtype', 'B'),
            'fillgaps': bp.get('fillgaps', 0),
            'gaintable': bp.get('gaintable', ''),
            'gainfield': bp.get('gainfield', ''),
            'interp': bp.get('interp', ''),
            'spwmap': bp.get('spwmap', []),
            'append': bp.get('append', False),
        }
        return params

    def _build_gain_params(self, vis, caltable: str) -> Dict[str, Any]:
        g = self.cal_config.get('gain', {})
        params: Dict[str, Any] = {
            'vis': vis,
            'caltable': caltable,
            'field': g.get('field', ''),
            'refant': g.get('refant', self.cal_config.get('gcal_refant', '')),
            'solint': g.get('solint', self.cal_config.get('gcal_solint', '30min')),
            'combine': g.get('combine', 'scan'),
            'minsnr': g.get('minsnr', self.cal_config.get('gcal_minsnr', 3.0)),
            'solnorm': g.get('solnorm', True),
            'calmode': g.get('calmode', self.cal_config.get('gcal_mode', 'ap')),
            'gaintable': g.get('gaintable', ''),
            'gainfield': g.get('gainfield', ''),
            'interp': g.get('interp', ''),
            'spwmap': g.get('spwmap', []),
            'append': g.get('append', False),
        }
        if 'uvrange' in g or 'gcal_uvrange' in self.cal_config:
            params['uvrange'] = g.get('uvrange', self.cal_config.get('gcal_uvrange', ''))
        return params

    def _build_apply_params(self, vis, gaintable: List[str]) -> Dict[str, Any]:
        ap = self.cal_config.get('apply', {})
        interp_val = ap.get('interp', ['nearest', 'linear'])
        if not isinstance(interp_val, list):
            interp_val = interp_val or ''
        params: Dict[str, Any] = {
            'vis': vis,
            'gaintable': gaintable,
            'gainfield': ap.get('gainfield', []),
            'interp': interp_val,
            'spwmap': ap.get('spwmap', []),
            'calwt': ap.get('calwt', False),
            'flagbackup': ap.get('flagbackup', False),
            'applymode': ap.get('applymode', 'calonly'),
        }
        return params
    
    async def setup_calibration(self, block, max_retries: int = 3) -> Dict[str, Any]:
        """
        Set up calibration for a processing block with retry logic.
        
        This includes finding the appropriate bandpass calibration table
        and generating gain calibration solutions.
        
        Args:
            block: ProcessingBlock object
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary containing calibration setup results
        """
        logger.info(f"Setting up calibration for block {block.block_id}")
        
        for attempt in range(max_retries + 1):
            try:
                # Find latest bandpass calibration table
                bcal_table = self._find_latest_bcal_table(block.end_time)
                if not bcal_table:
                    raise CalibrationError("No suitable bandpass calibration table found")
                
                # Calculate block center coordinates
                center_coord = self._calculate_block_center(block)
                
                # Prefer calibrator-based sky model (cache-first; online fallback)
                cl_path = await self._prepare_calibrator_model(block, center_coord)
                
                # Fallback to field sky model if calibrator model not available
                if not cl_path:
                    logger.warning("Falling back to field sky model generation")
                    cl_path = await self._generate_sky_model(block, center_coord)
                if not cl_path:
                    raise CalibrationError("Failed to generate any sky model")
                
                # Perform gain calibration
                gcal_table = await self._perform_gain_calibration(block, cl_path)
                if not gcal_table:
                    raise CalibrationError("Failed to perform gain calibration")
                
                # Validate calibration quality
                validation_results = await self.validate_calibration_quality(bcal_table, gcal_table)
                
                # Prepare mask path if needed
                mask_path = None
                if self.config.get('imaging', {}).get('use_clean_mask', False):
                    mask_path = self._prepare_mask_path(block)
                
                result = {
                    'success': True,
                    'bcal_table': bcal_table,
                    'gcal_table': gcal_table,
                    'cl_path': cl_path,
                    'mask_path': mask_path,
                    'center_coord': center_coord,
                    'validation_results': validation_results
                }
                
                logger.info(f"Calibration setup completed for block {block.block_id}")
                logger.info(f"Calibration quality score: {validation_results['overall_quality_score']:.2f}/10.0")
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Calibration setup failed for block {block.block_id} "
                                 f"(attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                 f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Calibration setup failed for block {block.block_id} after "
                               f"{max_retries + 1} attempts: {e}")
                    return {
                        'success': False,
                        'error': str(e),
                        'bcal_table': None,
                        'gcal_table': None,
                        'cl_path': None,
                        'mask_path': None,
                        'validation_results': None
                    }
    
    async def _prepare_calibrator_model(self, block, center_coord: SkyCoord,
                                        search_radius_deg: float = 10.0,
                                        min_flux_jy: float = 0.1) -> Optional[str]:
        """
        Find nearest calibrator (cache-first), build CASA component list, and
        inject the model into MODEL_DATA via setjy or ft/clearcal.
        
        Returns path to the .cl file, or None on failure.
        """
        try:
            # 0) Establish reference frequency and PB FWHM (Gaussian approx)
            ref_freq_hz = float(self.cal_config.get('ref_freq_hz', 1.4e9))
            c = 299792458.0
            wavelength_m = c / ref_freq_hz
            dish_d_m = float(self.cal_config.get('dish_diameter_m', 4.65))
            # FWHM ~ 1.02 * lambda/D (radians) -> convert to deg
            pb_fwhm_deg = (1.02 * wavelength_m / dish_d_m) * (180.0/np.pi)
            half_fwhm_deg = 0.5 * pb_fwhm_deg

            # 1) Find calibrator candidates near center (cache-first)
            finder = CalibratorFinder()
            cands = finder.find_nearby(center_coord.ra.deg, center_coord.dec.deg,
                                       radius_deg=search_radius_deg,
                                       min_flux_jy=min_flux_jy)
            if not cands:
                logger.warning("No calibrator candidates found near field center")
                return None

            # 2) Rank by expected attenuated flux under Gaussian PB: R=exp(-4 ln2 * (theta/FWHM)^2)
            def pb_response(theta_deg: float) -> float:
                return float(np.exp(-4.0*np.log(2.0) * (theta_deg / max(pb_fwhm_deg, 1e-6))**2))

            ranked = []
            for s in cands:
                flux0 = s.flux_jy_ref if s.flux_jy_ref is not None else 1.0
                att = pb_response(s.separation_deg)
                ranked.append((flux0 * att, att, s))
            ranked.sort(key=lambda x: (-x[0], x[2].separation_deg))

            best_att_flux, best_att, cal = ranked[0]
            logger.info(f"Top candidate: {cal.name} sep={cal.separation_deg:.2f} deg, PBresp={best_att:.3f}, att_flux={best_att_flux:.3f} Jy")

            # 3) Adaptive choice: bright in-beam single-source vs multi-source .cl
            bright_thresh_jy = float(self.cal_config.get('bright_att_flux_threshold_jy', 0.7))
            near_center_limit_deg = float(self.cal_config.get('near_center_limit_deg', half_fwhm_deg))
            use_single = (cal.separation_deg <= near_center_limit_deg) and (best_att_flux >= bright_thresh_jy)

            if use_single:
                # Single-source manual setjy or ft
                try:
                    from casatasks import setjy, clearcal
                    for ms_path in block.ms_files:
                        if not os.path.exists(ms_path):
                            logger.warning(f"MS file not found for setjy: {ms_path}")
                            continue
                        clearcal(vis=ms_path, addmodel=True)
                        # If flux unknown, assume 1 Jy; set at ref frequency
                        flux_jy = cal.flux_jy_ref if cal.flux_jy_ref is not None else 1.0
                        setjy(vis=ms_path,
                              field='',
                              standard='manual',
                              usescratch=True,
                              scalebychan=True,
                              fluxdensity=[flux_jy, 0.0, 0.0, 0.0],
                              reffreq=f"{ref_freq_hz}Hz",
                              # dir param not available in setjy; MS should be phased; else fallback to ft
                              )
                    logger.info(f"Injected single-source model via setjy(manual): {cal.name}")
                    return f"single_source:{cal.name}"
                except Exception as e:
                    logger.warning(f"setjy(manual) failed ({e}); falling back to ft with .cl")

            # Multi-source (or fallback) path: build .cl with top N within ~1.5 PB FWHM
            builder = SkyModelBuilder(output_dir=self.paths_config.get('skymodels_dir', 'data/sky_models'))
            # Select components
            max_components = int(self.cal_config.get('max_components', 50))
            include_radius_deg = float(self.cal_config.get('include_radius_deg', 1.5 * pb_fwhm_deg))
            names, ras, decs, fluxes = [], [], [], []
            for att_flux, att, s in ranked:
                if s.separation_deg > include_radius_deg:
                    continue
                names.append(s.name)
                ras.append(s.ra_deg)
                decs.append(s.dec_deg)
                fluxes.append(s.flux_jy_ref if s.flux_jy_ref is not None else 0.5)
                if len(names) >= max_components:
                    break
            if not names:
                # As a last resort, use the single candidate with assumed flux and ft
                try:
                    from casatasks import ft, clearcal
                    for ms_path in block.ms_files:
                        if not os.path.exists(ms_path):
                            continue
                        clearcal(vis=ms_path, addmodel=True)
                        # Build a temp one-source .cl
                        sm = builder.build_point_sources(
                            names=[cal.name], ras_deg=[cal.ra_deg], decs_deg=[cal.dec_deg],
                            fluxes_jy=[cal.flux_jy_ref or 1.0], ref_freq_hz=ref_freq_hz)
                        cl_tmp = builder.write_casa_component_list(sm, out_name=f"cal_{cal.name}")
                        ft(vis=ms_path, complist=cl_tmp, usescratch=True)
                    logger.info(f"Injected single-source model via ft(): {cal.name}")
                    return f"single_source:{cal.name}"
                except Exception as e2:
                    logger.error(f"Failed to inject any model: {e2}")
                    return None

            sm = builder.build_point_sources(names=names, ras_deg=ras, decs_deg=decs,
                                             fluxes_jy=fluxes, ref_freq_hz=ref_freq_hz)
            cl_path = builder.write_casa_component_list(sm, out_name="cal_multisrc")
            
            # 3) Inject model into MS
            try:
                from casatasks import setjy, clearcal
                # Apply to all MS files in block
                for ms_path in block.ms_files:
                    if not os.path.exists(ms_path):
                        logger.warning(f"MS file not found for setjy: {ms_path}")
                        continue
                    clearcal(vis=ms_path, addmodel=True)
                    setjy(vis=ms_path,
                          standard='manual',
                          usescratch=True,
                          scalebychan=True,
                          listmodels=[cl_path])
                logger.info(f"Injected calibrator model via setjy: {os.path.basename(cl_path)}")
            except Exception as e:
                # Fallback to ft/clearcal path
                logger.warning(f"setjy unavailable/failed ({e}); falling back to ft/clearcal")
                try:
                    from casatasks import ft, clearcal
                    for ms_path in block.ms_files:
                        if not os.path.exists(ms_path):
                            logger.warning(f"MS file not found for ft: {ms_path}")
                            continue
                        clearcal(vis=ms_path, addmodel=True)
                        ft(vis=ms_path, complist=cl_path, usescratch=True)
                    logger.info(f"Injected calibrator model via ft: {os.path.basename(cl_path)}")
                except Exception as e2:
                    logger.error(f"Failed to inject calibrator model: {e2}")
                    return None
            
            return cl_path
        except Exception as e:
            logger.error(f"Calibrator model preparation failed: {e}")
            return None
    
    def _find_latest_bcal_table(self, block_end_time: Time) -> Optional[str]:
        """
        Find the latest bandpass calibration table created before the block end time.
        
        Args:
            block_end_time: End time of the processing block
            
        Returns:
            Path to the bandpass calibration table, or None if not found
        """
        cal_tables_dir = self.paths_config.get('cal_tables_dir')
        if not cal_tables_dir:
            raise CalibrationError("Calibration tables directory not configured")
        
        bcal_files = sorted(glob.glob(os.path.join(cal_tables_dir, "*.bcal")))
        if not bcal_files:
            raise CalibrationError(f"No bandpass calibration tables found in {cal_tables_dir}")
        
        # Find the most recent table created before the block end time
        valid_bcals = []
        for bcal_file in bcal_files:
            try:
                file_mtime = os.path.getmtime(bcal_file)
                file_time = Time(file_mtime, format='unix', scale='utc')
                if file_time <= block_end_time:
                    valid_bcals.append((file_time, bcal_file))
            except Exception as e:
                logger.warning(f"Could not get modification time for {bcal_file}: {e}")
                continue
        
        if not valid_bcals:
            logger.warning("No bandpass calibration table found created before block end time")
            # Use the newest overall table as fallback
            return bcal_files[-1]
        
        # Return the most recent valid table
        valid_bcals.sort(key=lambda x: x[0])
        latest_bcal = valid_bcals[-1][1]
        logger.info(f"Using bandpass calibration table: {os.path.basename(latest_bcal)}")
        return latest_bcal
    
    def _calculate_block_center(self, block) -> SkyCoord:
        """
        Calculate the center coordinates for a processing block.
        
        Args:
            block: ProcessingBlock object
            
        Returns:
            SkyCoord object representing the block center
        """
        # Calculate block center time
        block_center_time = block.start_time + (block.end_time - block.start_time) / 2.0
        
        # Get telescope location
        telescope_loc = get_telescope_location()
        
        # Calculate center RA = LST at center time
        center_lst = block_center_time.sidereal_time('apparent', longitude=telescope_loc.lon)
        center_ra = center_lst.to(u.deg)
        
        # Get fixed declination from config
        fixed_dec_deg = self.cal_config.get('fixed_declination_deg')
        if fixed_dec_deg is None:
            raise CalibrationError("Fixed declination not configured")
        
        center_dec = fixed_dec_deg * u.deg
        center_coord = SkyCoord(ra=center_ra, dec=center_dec, frame='icrs')
        
        logger.info(f"Calculated block center coordinate: {center_coord.to_string('hmsdms')}")
        return center_coord
    
    async def _generate_sky_model(self, block, center_coord: SkyCoord) -> Optional[str]:
        """
        Generate a sky model component list for the block.
        
        Args:
            block: ProcessingBlock object
            center_coord: Center coordinates for the block
            
        Returns:
            Path to the component list file, or None if failed
        """
        try:
            skymodels_dir = self.paths_config.get('skymodels_dir')
            if not skymodels_dir:
                raise CalibrationError("Sky models directory not configured")
            
            os.makedirs(skymodels_dir, exist_ok=True)
            
            # Generate component list filename
            cl_filename = f"sky_field_{block.start_time.strftime('%Y%m%dT%H%M%S')}.cl"
            cl_output_path = os.path.join(skymodels_dir, cl_filename)
            
            # Create the sky model
            cl_path = await self.skymodel_manager.create_field_component_list(
                center_coord, cl_output_path
            )
            
            if cl_path:
                logger.info(f"Generated sky model: {os.path.basename(cl_path)}")
            else:
                logger.error("Failed to generate sky model")
            
            return cl_path
            
        except Exception as e:
            logger.error(f"Sky model generation failed: {e}")
            return None
    
    async def _perform_gain_calibration(self, block, cl_path: str, max_retries: int = 3) -> Optional[str]:
        """
        Perform gain calibration for the block with retry logic.
        
        Args:
            block: ProcessingBlock object
            cl_path: Path to the component list file
            max_retries: Maximum number of retry attempts
            
        Returns:
            Path to the gain calibration table, or None if failed
        """
        for attempt in range(max_retries + 1):
            try:
                cal_tables_dir = self.paths_config.get('cal_tables_dir')
                if not cal_tables_dir:
                    raise CalibrationError("Calibration tables directory not configured")
                
                os.makedirs(cal_tables_dir, exist_ok=True)
                
                # Generate gain calibration table filename
                time_segment_str = f"{block.start_time.strftime('%Y%m%dT%H%M%S')}_{block.end_time.strftime('%Y%m%dT%H%M%S')}"
                gcal_table_name = f"gain_{time_segment_str}.gcal"
                gcal_table_path = os.path.join(cal_tables_dir, gcal_table_name)
                
                # Import CASA tasks
                try:
                    from casatasks import gaincal, ft, clearcal
                    casa_available = True
                except ImportError:
                    logger.error("CASA tasks not available for gain calibration")
                    return None
                
                # Apply sky model to MS files and perform gain calibration
                for ms_path in block.ms_files:
                    if not os.path.exists(ms_path):
                        logger.error(f"MS file not found: {ms_path}")
                        continue
                    
                    try:
                        # Clear any existing model
                        clearcal(vis=ms_path, addmodel=True)
                        
                        # Apply sky model
                        ft(vis=ms_path, complist=cl_path, usescratch=True)
                        
                    except Exception as e:
                        logger.error(f"Failed to apply sky model to {ms_path}: {e}")
                        continue
                
                # Perform gain calibration
                try:
                    params = self._build_gain_params(block.ms_files, gcal_table_path)
                    gaincal(**params)
                    
                    logger.info(f"Gain calibration completed: {os.path.basename(gcal_table_path)}")
                    return gcal_table_path
                    
                except Exception as e:
                    if attempt < max_retries:
                        retry_delay = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Gain calibration failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                     f"Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"Gain calibration failed after {max_retries + 1} attempts: {e}")
                        return None
                        
            except Exception as e:
                if attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Gain calibration setup failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                 f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Gain calibration setup failed after {max_retries + 1} attempts: {e}")
                    return None
        
        return None
    
    def _prepare_mask_path(self, block) -> str:
        """
        Prepare the path for a clean mask file.
        
        Args:
            block: ProcessingBlock object
            
        Returns:
            Path for the mask file
        """
        skymodels_dir = self.paths_config.get('skymodels_dir')
        mask_filename = f"mask_{block.start_time.strftime('%Y%m%dT%H%M%S')}.mask"
        return os.path.join(skymodels_dir, mask_filename)
    
    async def apply_calibration(self, ms_path: str, bcal_table: str, 
                              gcal_tables: List[str]) -> bool:
        """
        Apply calibration tables to an MS file.
        
        Args:
            ms_path: Path to the MS file
            bcal_table: Path to the bandpass calibration table
            gcal_tables: List of paths to gain calibration tables
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from casatasks import applycal
            casa_available = True
        except ImportError:
            logger.error("CASA tasks not available for calibration application")
            return False
        
        if not os.path.exists(ms_path):
            logger.error(f"MS file not found: {ms_path}")
            return False
        
        if not os.path.exists(bcal_table):
            logger.error(f"Bandpass calibration table not found: {bcal_table}")
            return False
        
        for gcal_table in gcal_tables:
            if not os.path.exists(gcal_table):
                logger.error(f"Gain calibration table not found: {gcal_table}")
                return False
        
        try:
            # Build list of tables for applycal
            gaintables = [bcal_table] + gcal_tables
            
            params = self._build_apply_params(ms_path, gaintables)
            applycal(**params)
            
            logger.info(f"Successfully applied calibration to {os.path.basename(ms_path)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply calibration to {ms_path}: {e}")
            return False
    
    async def validate_calibration_quality(self, bcal_table: str, gcal_table: str) -> Dict[str, Any]:
        """
        Validate the quality of calibration tables.
        
        Args:
            bcal_table: Path to bandpass calibration table
            gcal_table: Path to gain calibration table
            
        Returns:
            Dictionary with validation results and quality metrics
        """
        logger.info("Validating calibration quality")
        
        validation_results = {
            'bcal_valid': False,
            'gcal_valid': False,
            'overall_quality_score': 0.0,
            'warnings': [],
            'errors': [],
            'quality_metrics': {
                'bcal_solutions': 0,
                'gcal_solutions': 0,
                'bcal_snr_median': 0.0,
                'gcal_snr_median': 0.0,
                'bcal_phase_rms': 0.0,
                'gcal_phase_rms': 0.0
            }
        }
        
        try:
            # Validate bandpass calibration table
            bcal_metrics = await self._validate_bcal_table(bcal_table)
            validation_results['bcal_valid'] = bcal_metrics['valid']
            validation_results['quality_metrics'].update(bcal_metrics['metrics'])
            validation_results['warnings'].extend(bcal_metrics.get('warnings', []))
            validation_results['errors'].extend(bcal_metrics.get('errors', []))
            
            # Validate gain calibration table
            gcal_metrics = await self._validate_gcal_table(gcal_table)
            validation_results['gcal_valid'] = gcal_metrics['valid']
            validation_results['quality_metrics'].update(gcal_metrics['metrics'])
            validation_results['warnings'].extend(gcal_metrics.get('warnings', []))
            validation_results['errors'].extend(gcal_metrics.get('errors', []))
            
            # Calculate overall quality score
            validation_results['overall_quality_score'] = self._calculate_calibration_quality_score(
                validation_results['quality_metrics']
            )
            
            logger.info(f"Calibration validation complete. Quality score: {validation_results['overall_quality_score']:.2f}/10.0")
            
        except Exception as e:
            logger.error(f"Calibration validation failed: {e}")
            validation_results['errors'].append(f"Validation error: {e}")
        
        return validation_results
    
    async def _validate_bcal_table(self, bcal_table: str) -> Dict[str, Any]:
        """
        Validate bandpass calibration table quality.
        
        Args:
            bcal_table: Path to bandpass calibration table
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'metrics': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            import casacore.tables as pt
            
            with pt.table(bcal_table) as table:
                nrows = table.nrows()
                if nrows == 0:
                    result['errors'].append("Bandpass calibration table is empty")
                    return result
                
                # Get solution statistics
                result['metrics']['bcal_solutions'] = nrows
                
                # Check for amplitude and phase columns
                if 'CPARAM' in table.colnames():
                    cparam_data = table.getcol('CPARAM')
                    if len(cparam_data) > 0:
                        # Calculate amplitude and phase statistics
                        amplitude = np.abs(cparam_data)
                        phase = np.angle(cparam_data)
                        
                        result['metrics']['bcal_amplitude_median'] = float(np.median(amplitude))
                        result['metrics']['bcal_phase_rms'] = float(np.std(phase))
                        
                        # Check for reasonable values
                        if np.any(amplitude < 0.1) or np.any(amplitude > 10.0):
                            result['warnings'].append("Bandpass amplitudes have unusual values")
                        
                        if np.std(phase) > 1.0:  # More than 1 radian RMS
                            result['warnings'].append("Bandpass phases have high RMS")
                
                # Check for SNR column
                if 'SNR' in table.colnames():
                    snr_data = table.getcol('SNR')
                    if len(snr_data) > 0:
                        result['metrics']['bcal_snr_median'] = float(np.median(snr_data))
                        if np.median(snr_data) < 3.0:
                            result['warnings'].append("Bandpass calibration has low SNR")
                
                result['valid'] = True
                
        except ImportError:
            result['warnings'].append("casacore not available for detailed validation")
            result['valid'] = True  # Basic file check passed
        except Exception as e:
            result['errors'].append(f"Bandpass validation error: {e}")
        
        return result
    
    async def _validate_gcal_table(self, gcal_table: str) -> Dict[str, Any]:
        """
        Validate gain calibration table quality.
        
        Args:
            gcal_table: Path to gain calibration table
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'metrics': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            import casacore.tables as pt
            
            with pt.table(gcal_table) as table:
                nrows = table.nrows()
                if nrows == 0:
                    result['errors'].append("Gain calibration table is empty")
                    return result
                
                # Get solution statistics
                result['metrics']['gcal_solutions'] = nrows
                
                # Check for amplitude and phase columns
                if 'CPARAM' in table.colnames():
                    cparam_data = table.getcol('CPARAM')
                    if len(cparam_data) > 0:
                        # Calculate amplitude and phase statistics
                        amplitude = np.abs(cparam_data)
                        phase = np.angle(cparam_data)
                        
                        result['metrics']['gcal_amplitude_median'] = float(np.median(amplitude))
                        result['metrics']['gcal_phase_rms'] = float(np.std(phase))
                        
                        # Check for reasonable values
                        if np.any(amplitude < 0.1) or np.any(amplitude > 10.0):
                            result['warnings'].append("Gain amplitudes have unusual values")
                        
                        if np.std(phase) > 1.0:  # More than 1 radian RMS
                            result['warnings'].append("Gain phases have high RMS")
                
                # Check for SNR column
                if 'SNR' in table.colnames():
                    snr_data = table.getcol('SNR')
                    if len(snr_data) > 0:
                        result['metrics']['gcal_snr_median'] = float(np.median(snr_data))
                        if np.median(snr_data) < 3.0:
                            result['warnings'].append("Gain calibration has low SNR")
                
                result['valid'] = True
                
        except ImportError:
            result['warnings'].append("casacore not available for detailed validation")
            result['valid'] = True  # Basic file check passed
        except Exception as e:
            result['errors'].append(f"Gain validation error: {e}")
        
        return result
    
    def _calculate_calibration_quality_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate overall calibration quality score.
        
        Args:
            metrics: Dictionary of calibration metrics
            
        Returns:
            Quality score from 0.0 to 10.0
        """
        score = 10.0
        
        # Check bandpass calibration quality
        if metrics.get('bcal_solutions', 0) == 0:
            score -= 3.0
        elif metrics.get('bcal_snr_median', 0) < 3.0:
            score -= 1.5
        elif metrics.get('bcal_phase_rms', 0) > 1.0:
            score -= 1.0
        
        # Check gain calibration quality
        if metrics.get('gcal_solutions', 0) == 0:
            score -= 3.0
        elif metrics.get('gcal_snr_median', 0) < 3.0:
            score -= 1.5
        elif metrics.get('gcal_phase_rms', 0) > 1.0:
            score -= 1.0
        
        return max(0.0, round(score, 2))
    
    async def create_bandpass_calibration(self, ms_files: List[str], 
                                        output_bcal_path: str,
                                        max_retries: int = 3) -> Optional[str]:
        """
        Create bandpass calibration table from MS files.
        
        Args:
            ms_files: List of MS file paths
            output_bcal_path: Path for the output bandpass calibration table
            max_retries: Maximum number of retry attempts
            
        Returns:
            Path to the created bandpass calibration table, or None if failed
        """
        logger.info(f"Creating bandpass calibration from {len(ms_files)} MS files")
        
        for attempt in range(max_retries + 1):
            try:
                # Import CASA tasks
                try:
                    from casatasks import bandpass, flagdata
                    casa_available = True
                except ImportError:
                    logger.error("CASA tasks not available for bandpass calibration")
                    return None
                
                # Check if all MS files exist
                for ms_path in ms_files:
                    if not os.path.exists(ms_path):
                        logger.error(f"MS file not found: {ms_path}")
                        return None
                
                # Apply initial flagging
                for ms_path in ms_files:
                    try:
                        flagdata(
                            vis=ms_path,
                            mode='tfcrop',
                            timecutoff=self.cal_config.get('flagging', {}).get('tfcrop_timecutoff', 4.0),
                            freqcutoff=self.cal_config.get('flagging', {}).get('tfcrop_freqcutoff', 4.0),
                            action='apply',
                            flagbackup=True
                        )
                    except Exception as e:
                        logger.warning(f"Initial flagging failed for {ms_path}: {e}")
                
                # Perform bandpass calibration
                try:
                    params = self._build_bandpass_params(ms_files, output_bcal_path)
                    bandpass(**params)
                    
                    logger.info(f"Bandpass calibration completed: {os.path.basename(output_bcal_path)}")
                    return output_bcal_path
                    
                except Exception as e:
                    if attempt < max_retries:
                        retry_delay = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Bandpass calibration failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                     f"Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"Bandpass calibration failed after {max_retries + 1} attempts: {e}")
                        return None
                        
            except Exception as e:
                if attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Bandpass calibration setup failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                 f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Bandpass calibration setup failed after {max_retries + 1} attempts: {e}")
                    return None
        
        return None
    
    async def apply_calibration_with_retry(self, ms_path: str, bcal_table: str, 
                                         gcal_tables: List[str], max_retries: int = 3) -> bool:
        """
        Apply calibration tables to an MS file with retry logic.
        
        Args:
            ms_path: Path to the MS file
            bcal_table: Path to the bandpass calibration table
            gcal_tables: List of paths to gain calibration tables
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(max_retries + 1):
            try:
                success = await self.apply_calibration(ms_path, bcal_table, gcal_tables)
                if success:
                    return True
                elif attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Calibration application failed (attempt {attempt + 1}/{max_retries + 1}). "
                                 f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Calibration application failed after {max_retries + 1} attempts")
                    return False
                    
            except Exception as e:
                if attempt < max_retries:
                    retry_delay = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Calibration application failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                                 f"Retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Calibration application failed after {max_retries + 1} attempts: {e}")
                    return False
        
        return False

    # ---- Provenance and table lifecycle helpers ----
    def _persist_calibration_provenance(self,
                                        output_dir: str,
                                        ms_path: str,
                                        center_coord: SkyCoord,
                                        calibrator_info: Dict[str, Any],
                                        cl_path: str,
                                        refant: str,
                                        solints: Dict[str, Any],
                                        combine: str,
                                        tables: Dict[str, str]) -> Optional[str]:
        """
        Persist a structured JSON provenance document for calibration artifacts.
        Returns the written path or None on failure.
        """
        try:
            from ...calibration.provenance import write_provenance
            payload = {
                'ms': ms_path,
                'field_center': {
                    'ra_deg': float(center_coord.ra.deg),
                    'dec_deg': float(center_coord.dec.deg),
                },
                'calibrator': calibrator_info,
                'component_list': cl_path,
                'refant': refant,
                'solints': solints,
                'combine': combine,
                'tables': tables,
            }
            return write_provenance(payload, output_dir=output_dir, basename='calibration_provenance')
        except Exception as e:
            logger.warning(f"Failed to write calibration provenance: {e}")
            return None

    def _update_table_symlinks(self, cal_tables_dir: str, bcal_path: Optional[str], gcal_path: Optional[str]) -> None:
        """Create/refresh convenient latest symlinks for .bcal and .gcal tables."""
        os.makedirs(cal_tables_dir, exist_ok=True)
        def _symlink(target: Optional[str], linkname: str):
            try:
                link_path = os.path.join(cal_tables_dir, linkname)
                if target:
                    if os.path.islink(link_path) or os.path.exists(link_path):
                        os.remove(link_path)
                    os.symlink(os.path.basename(target), link_path)
            except Exception as e:
                logger.debug(f"Symlink update skipped for {linkname}: {e}")
        _symlink(bcal_path, 'latest.bcal')
        _symlink(gcal_path, 'latest.gcal')
