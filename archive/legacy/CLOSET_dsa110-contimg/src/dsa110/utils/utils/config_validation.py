"""Configuration validation utilities."""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Simple configuration validator."""
    
    @staticmethod
    def validate_mosaicking_config(config: Dict[str, Any]) -> List[str]:
        """Validate mosaicking configuration."""
        errors = []
        
        mosaic_config = config.get('mosaicking', {})
        
        # Required fields
        if 'mosaic_nx' not in mosaic_config or not isinstance(mosaic_config['mosaic_nx'], int):
            errors.append("mosaicking.mosaic_nx must be an integer")
        if 'mosaic_ny' not in mosaic_config or not isinstance(mosaic_config['mosaic_ny'], int):
            errors.append("mosaicking.mosaic_ny must be an integer")
            
        # Optional fields with defaults
        if 'mosaic_cell' in mosaic_config and not isinstance(mosaic_config['mosaic_cell'], str):
            errors.append("mosaicking.mosaic_cell must be a string")
            
        return errors
    
    @staticmethod
    def validate_photometry_config(config: Dict[str, Any]) -> List[str]:
        """Validate photometry configuration."""
        errors = []
        
        phot_config = config.get('photometry', {})
        detection_config = phot_config.get('detection', {})
        
        # Validate detection parameters
        if 'fwhm_pixels' in detection_config:
            if not isinstance(detection_config['fwhm_pixels'], (int, float)) or detection_config['fwhm_pixels'] <= 0:
                errors.append("photometry.detection.fwhm_pixels must be positive number")
                
        if 'threshold_sigma' in detection_config:
            if not isinstance(detection_config['threshold_sigma'], (int, float)) or detection_config['threshold_sigma'] <= 0:
                errors.append("photometry.detection.threshold_sigma must be positive number")
                
        return errors
    
    @staticmethod
    def validate_paths_config(config: Dict[str, Any]) -> List[str]:
        """Validate paths configuration."""
        errors = []
        
        paths_config = config.get('paths', {})
        required_paths = ['mosaics_dir', 'photometry_dir']
        
        for path_key in required_paths:
            if path_key not in paths_config:
                errors.append(f"paths.{path_key} is required")
                
        return errors