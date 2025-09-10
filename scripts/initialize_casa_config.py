#!/usr/bin/env python3
"""
Initialize CASA Configuration for DSA-110 Pipeline

This script sets up comprehensive CASA configuration including:
- Measures data configuration
- Casarundata configuration  
- Auto-update settings
- Lock file handling

Based on CASA documentation:
https://casadocs.readthedocs.io/en/stable/api/casaconfig.html
"""

import sys
import os
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.utils.casa_config_manager import CASAConfigManager


def main():
    """Initialize CASA configuration for the pipeline."""
    
    print("DSA-110 Pipeline CASA Configuration Initializer")
    print("=" * 50)
    
    # Load pipeline configuration
    config_path = project_root / "config" / "pipeline_config.yaml"
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        return 1
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✅ Loaded configuration from: {config_path}")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return 1
    
    # Initialize CASA configuration manager
    try:
        casa_manager = CASAConfigManager(config)
        print("✅ CASA configuration manager initialized")
    except Exception as e:
        print(f"❌ Failed to initialize CASA configuration manager: {e}")
        return 1
    
    # Set up CASA configuration
    print("\nSetting up CASA configuration...")
    if casa_manager.setup_casa_configuration():
        print("✅ CASA configuration setup completed successfully")
    else:
        print("❌ CASA configuration setup failed")
        return 1
    
    # Validate configuration
    print("\nValidating CASA configuration...")
    if casa_manager.validate_casa_configuration():
        print("✅ CASA configuration validation successful")
    else:
        print("❌ CASA configuration validation failed")
        return 1
    
    # Show configuration summary
    print("\nCASA Configuration Summary:")
    print("-" * 30)
    summary = casa_manager.get_casa_config_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n✅ CASA configuration initialization completed successfully!")
    print("\nNext steps:")
    print("1. Run your pipeline - CASA should now work correctly")
    print("2. Check casalogs/ directory for CASA log files")
    print("3. Monitor ~/.casa/data/ for measures data updates")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
