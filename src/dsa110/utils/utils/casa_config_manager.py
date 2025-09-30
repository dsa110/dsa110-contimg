"""
CASA Configuration Manager for DSA-110 Pipeline

This module provides comprehensive CASA configuration management including
measures data, casarundata, and auto-update settings as specified in the
CASA documentation.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CASAConfig:
    """CASA configuration parameters."""
    # Data paths
    datapath: list = None
    measurespath: str = "~/.casa/data"
    
    # Auto-update settings
    measures_auto_update: bool = True
    data_auto_update: bool = True
    
    # Logging
    logfile: str = None
    logdir: str = None
    
    # Performance
    startupfile: str = None
    cachedir: str = None
    
    def __post_init__(self):
        if self.datapath is None:
            self.datapath = [self.measurespath]


class CASAConfigManager:
    """
    Manages CASA configuration for the DSA-110 pipeline.
    
    This class handles:
    - CASA configuration file creation
    - Measures data management
    - Auto-update configuration
    - Lock file handling
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize CASA configuration manager.
        
        Args:
            config: Pipeline configuration dictionary
        """
        self.config = config
        self.casa_config_dir = Path.home() / ".casa"
        self.casa_config_file = self.casa_config_dir / "config.py"
        self.casa_rc_file = self.casa_config_dir / "rc"
        
        # Get CASA configuration from pipeline config
        self.casa_config = self._load_casa_config()
        
    def _load_casa_config(self) -> CASAConfig:
        """Load CASA configuration from pipeline config."""
        casa_config = self.config.get('casa', {})
        
        return CASAConfig(
            datapath=casa_config.get('datapath', [self.config.get('paths', {}).get('casa_log_dir', '~/.casa/data')]),
            measurespath=casa_config.get('measurespath', '~/.casa/data'),
            measures_auto_update=casa_config.get('measures_auto_update', True),
            data_auto_update=casa_config.get('data_auto_update', True),
            logfile=casa_config.get('logfile', str(Path(self.config.get('paths', {}).get('casa_log_dir', 'casalogs')) / 'casa.log')),
            logdir=casa_config.get('logdir', str(Path(self.config.get('paths', {}).get('casa_log_dir', 'casalogs')))),
            startupfile=casa_config.get('startupfile'),
            cachedir=casa_config.get('cachedir')
        )
    
    def setup_casa_configuration(self) -> bool:
        """
        Set up comprehensive CASA configuration.
        
        Returns:
            True if configuration was successful
        """
        try:
            # Ensure CASA config directory exists
            self.casa_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Create CASA configuration file
            self._create_casa_config_file()
            
            # Create CASA rc file
            self._create_casa_rc_file()
            
            # Ensure measures data is available
            self._ensure_measures_data()
            
            # Clear any stale lock files
            self._clear_casa_locks()
            
            logger.info("CASA configuration setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup CASA configuration: {e}")
            return False
    
    def _create_casa_config_file(self):
        """Create CASA config.py file."""
        config_content = f'''# CASA Configuration for DSA-110 Pipeline
# Generated automatically by CASAConfigManager

# Data paths
datapath = {self.casa_config.datapath}
measurespath = '{self.casa_config.measurespath}'

# Auto-update settings
measures_auto_update = {str(self.casa_config.measures_auto_update).lower()}
data_auto_update = {str(self.casa_config.data_auto_update).lower()}

# Logging
logfile = '{self.casa_config.logfile}'
logdir = '{self.casa_config.logdir}'

# Performance settings
{('startupfile = "' + self.casa_config.startupfile + '"') if self.casa_config.startupfile else ''}
{('cachedir = "' + self.casa_config.cachedir + '"') if self.casa_config.cachedir else ''}

# Additional CASA settings
log2term = True
nologger = False
nologfile = False
'''
        
        with open(self.casa_config_file, 'w') as f:
            f.write(config_content)
        
        logger.info(f"CASA config.py created: {self.casa_config_file}")
    
    def _create_casa_rc_file(self):
        """Create CASA rc file."""
        rc_content = f'''# CASA RC Configuration for DSA-110 Pipeline
# Generated automatically by CASAConfigManager

logfile = '{self.casa_config.logfile}'
logdir = '{self.casa_config.logdir}'
'''
        
        with open(self.casa_rc_file, 'w') as f:
            f.write(rc_content)
        
        logger.info(f"CASA rc file created: {self.casa_rc_file}")
    
    def _ensure_measures_data(self):
        """Ensure CASA measures data is available and up-to-date."""
        try:
            # Import CASA tools
            from casatools import measures
            
            # Test measures access
            me = measures()
            me.done()
            
            logger.info("CASA measures data is accessible")
            
            # If auto-update is enabled, trigger updates
            if self.casa_config.measures_auto_update or self.casa_config.data_auto_update:
                self._trigger_casa_updates()
                
        except Exception as e:
            logger.warning(f"CASA measures data check failed: {e}")
            logger.info("Attempting to initialize CASA data...")
            self._initialize_casa_data()
    
    def _trigger_casa_updates(self):
        """Trigger CASA data updates if needed."""
        try:
            import casaconfig
            
            # Update measures data if needed
            if self.casa_config.measures_auto_update:
                logger.info("Checking for measures data updates...")
                casaconfig.measures_update(force=False)
            
            # Update casarundata if needed
            if self.casa_config.data_auto_update:
                logger.info("Checking for casarundata updates...")
                casaconfig.data_update(force=False)
                
        except Exception as e:
            logger.warning(f"CASA data update failed: {e}")
    
    def _initialize_casa_data(self):
        """Initialize CASA data if not available."""
        try:
            import casaconfig
            
            logger.info("Initializing CASA data...")
            
            # Pull initial data
            casaconfig.pull_data(force=True)
            
            # Update measures data
            casaconfig.measures_update(force=True)
            
            logger.info("CASA data initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize CASA data: {e}")
            raise
    
    def _clear_casa_locks(self):
        """Clear any stale CASA lock files."""
        casa_data_dir = Path(self.casa_config.measurespath).expanduser()
        lock_file = casa_data_dir / "data_update.lock"
        
        if lock_file.exists():
            logger.warning(f"Removing stale CASA lock file: {lock_file}")
            try:
                lock_file.unlink()
                logger.info("CASA lock file removed successfully")
            except Exception as e:
                logger.error(f"Failed to remove CASA lock file: {e}")
    
    def get_casa_config_summary(self) -> Dict[str, Any]:
        """Get summary of current CASA configuration."""
        return {
            'config_file': str(self.casa_config_file),
            'rc_file': str(self.casa_rc_file),
            'measurespath': self.casa_config.measurespath,
            'datapath': self.casa_config.datapath,
            'measures_auto_update': self.casa_config.measures_auto_update,
            'data_auto_update': self.casa_config.data_auto_update,
            'logfile': self.casa_config.logfile,
            'logdir': self.casa_config.logdir
        }
    
    def validate_casa_configuration(self) -> bool:
        """Validate that CASA configuration is working correctly."""
        try:
            # Test CASA tools import
            from casatools import measures, ms
            
            # Test measures object creation
            me = measures()
            me.done()
            
            # Test MS tool creation
            ms_tool = ms()
            ms_tool.done()
            
            logger.info("CASA configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"CASA configuration validation failed: {e}")
            return False


def setup_casa_for_pipeline(config: Dict[str, Any]) -> bool:
    """
    Set up CASA configuration for the DSA-110 pipeline.
    
    Args:
        config: Pipeline configuration dictionary
        
    Returns:
        True if setup was successful
    """
    try:
        casa_manager = CASAConfigManager(config)
        return casa_manager.setup_casa_configuration()
    except Exception as e:
        logger.error(f"Failed to setup CASA for pipeline: {e}")
        return False
