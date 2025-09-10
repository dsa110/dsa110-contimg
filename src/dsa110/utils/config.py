"""Configuration Management

Unified configuration system that consolidates all the various config
approaches into a single, clear interface.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Centralized configuration management."""
    
    def __init__(self, config: Optional[Union[str, Dict[str, Any]]] = None):
        """Initialize configuration manager.
        
        Args:
            config: Configuration dict or path to config file
        """
        self.config = self._load_config(config)
        
    def _load_config(self, config: Optional[Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """Load configuration from various sources.
        
        Args:
            config: Configuration dict or path to config file
            
        Returns:
            dict: Loaded configuration
        """
        # Default configuration
        default_config = {
            'pipeline': {
                'name': 'DSA-110 Continuum Imaging',
                'version': '2.0.0'
            },
            'paths': {
                'input_dir': 'data_new/input',
                'output_dir': 'data_new/output',
                'cache_dir': 'data_new/cache'
            },
            'ms_creation': {
                'antenna_selection': None,
                'time_tolerance': 120.0,
                'coordinate_validation': True
            },
            'calibration': {
                'bandpass_interval_hours': 8.0,
                'gain_interval_hours': 1.0,
                'reference_antennas': ['pad103', 'pad001']
            },
            'imaging': {
                'cell_size': '3arcsec',
                'image_size': [4800, 4800],
                'weighting': 'briggs',
                'robust': 0.5
            }
        }
        
        if config is None:
            # Try to load default config file
            config_path = Path('config/default.yaml')
            if config_path.exists():
                return self._load_yaml_config(config_path, default_config)
            else:
                return default_config
                
        elif isinstance(config, str):
            # Load from file path
            config_path = Path(config)
            if config_path.exists():
                return self._load_yaml_config(config_path, default_config)
            else:
                logger.warning(f"Config file not found: {config}, using defaults")
                return default_config
                
        elif isinstance(config, dict):
            # Merge with defaults
            return self._merge_configs(default_config, config)
            
        else:
            logger.warning(f"Invalid config type: {type(config)}, using defaults")
            return default_config
            
    def _load_yaml_config(self, config_path: Path, default_config: Dict[str, Any]) -> Dict[str, Any]:
        """Load YAML configuration file.
        
        Args:
            config_path: Path to YAML config file
            default_config: Default configuration to merge with
            
        Returns:
            dict: Merged configuration
        """
        try:
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                
            return self._merge_configs(default_config, file_config)
            
        except Exception as e:
            logger.error(f"Failed to load config file {config_path}: {e}")
            return default_config
            
    def _merge_configs(self, default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries.
        
        Args:
            default: Default configuration
            override: Override configuration
            
        Returns:
            dict: Merged configuration
        """
        result = default.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
        
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration.
        
        Returns:
            dict: Current configuration
        """
        return self.config
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value