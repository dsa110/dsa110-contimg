# core/utils/config_loader.py
"""
Configuration loading utilities for DSA-110 pipeline.

This module provides utilities for loading and merging configuration
files from different environments.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from .logging import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """
    Handles configuration loading and merging for the pipeline.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.environments_dir = self.config_dir / "environments"
    
    def load_config(self, environment: str = "development", 
                   config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration for a specific environment.
        
        Args:
            environment: Environment name (development, production, testing)
            config_file: Optional specific config file to load
            
        Returns:
            Merged configuration dictionary
        """
        try:
            if config_file:
                # Load specific config file
                config_path = Path(config_file)
                if not config_path.exists():
                    raise FileNotFoundError(f"Config file not found: {config_file}")
                
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                logger.info(f"Loaded configuration from {config_file}")
                return config
            
            else:
                # Load environment-specific config
                env_config_path = self.environments_dir / f"{environment}.yaml"
                if not env_config_path.exists():
                    raise FileNotFoundError(f"Environment config not found: {env_config_path}")
                
                with open(env_config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Extract environment-specific configuration
                if environment in config:
                    env_config = config[environment]
                else:
                    env_config = config
                
                logger.info(f"Loaded {environment} environment configuration")
                return env_config
                
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def load_base_config(self) -> Dict[str, Any]:
        """
        Load the base configuration file.
        
        Returns:
            Base configuration dictionary
        """
        base_config_path = self.config_dir / "pipeline_config.yaml"
        if not base_config_path.exists():
            raise FileNotFoundError(f"Base config not found: {base_config_path}")
        
        with open(base_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        logger.info("Loaded base configuration")
        return config
    
    def merge_configs(self, base_config: Dict[str, Any], 
                     env_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge base configuration with environment-specific configuration.
        
        Args:
            base_config: Base configuration dictionary
            env_config: Environment-specific configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        try:
            # Deep merge configurations
            merged_config = self._deep_merge(base_config, env_config)
            logger.info("Merged base and environment configurations")
            return merged_config
            
        except Exception as e:
            logger.error(f"Failed to merge configurations: {e}")
            raise
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate a configuration dictionary.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required sections
            required_sections = ['paths', 'services', 'calibration', 'imaging']
            for section in required_sections:
                if section not in config:
                    logger.error(f"Missing required configuration section: {section}")
                    return False
            
            # Check required paths
            paths = config.get('paths', {})
            required_paths = ['ms_stage1_dir', 'cal_tables_dir', 'images_dir', 'mosaics_dir']
            for path_key in required_paths:
                if path_key not in paths:
                    logger.error(f"Missing required path configuration: {path_key}")
                    return False
            
            # Check required services
            services = config.get('services', {})
            required_services = ['mosaic_duration_min', 'mosaic_overlap_min', 'ms_chunk_duration_min']
            for service_key in required_services:
                if service_key not in services:
                    logger.error(f"Missing required service configuration: {service_key}")
                    return False
            
            logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_environment_config(self, environment: str) -> Dict[str, Any]:
        """
        Get configuration for a specific environment with validation.
        
        Args:
            environment: Environment name
            
        Returns:
            Validated configuration dictionary
        """
        try:
            # Load base config
            base_config = self.load_base_config()
            
            # Load environment config
            env_config = self.load_config(environment)
            
            # Merge configurations
            merged_config = self.merge_configs(base_config, env_config)
            
            # Validate configuration
            if not self.validate_config(merged_config):
                raise ValueError(f"Configuration validation failed for environment: {environment}")
            
            return merged_config
            
        except Exception as e:
            logger.error(f"Failed to get environment config: {e}")
            raise


def load_pipeline_config(environment: str = "development", 
                        config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to load pipeline configuration.
    
    Args:
        environment: Environment name (development, production, testing)
        config_file: Optional specific config file to load
        
    Returns:
        Configuration dictionary
    """
    loader = ConfigLoader()
    
    if config_file:
        return loader.load_config(config_file=config_file)
    else:
        return loader.get_environment_config(environment)
