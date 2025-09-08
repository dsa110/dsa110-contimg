#!/usr/bin/env python3
"""
Setup CASA environment to force log files to casalogs directory.

This script sets up environment variables and creates a CASA configuration
that forces all CASA log files to go to the casalogs directory.
"""

import os
import sys
from pathlib import Path

def setup_casa_environment():
    """Set up CASA environment to use casalogs directory."""
    
    # Get project root
    project_root = Path(__file__).parent.parent
    casalogs_dir = project_root / "casalogs"
    
    # Ensure casalogs directory exists
    casalogs_dir.mkdir(exist_ok=True)
    
    # Set CASA environment variables
    os.environ['CASA_LOG_DIR'] = str(casalogs_dir.absolute())
    os.environ['CASA_LOG_FILE'] = str(casalogs_dir / "casa.log")
    
    # Set CASA configuration directory
    casa_config_dir = project_root / ".casa"
    casa_config_dir.mkdir(exist_ok=True)
    
    # Create CASA configuration file
    casa_config_file = casa_config_dir / "rc"
    with open(casa_config_file, 'w') as f:
        f.write(f"# CASA configuration for DSA-110 pipeline\n")
        f.write(f"# Log directory: {casalogs_dir}\n")
        f.write(f"logfile = '{casalogs_dir}/casa.log'\n")
        f.write(f"logdir = '{casalogs_dir}'\n")
    
    print(f"CASA environment configured:")
    print(f"  Log directory: {casalogs_dir}")
    print(f"  Config file: {casa_config_file}")
    print(f"  Environment variables set")

def create_casa_wrapper():
    """Create a wrapper script that sets up CASA environment."""
    
    project_root = Path(__file__).parent.parent
    wrapper_script = project_root / "scripts" / "casa_wrapper.py"
    
    wrapper_content = f'''#!/usr/bin/env python3
"""
CASA wrapper that forces logging to casalogs directory.
"""

import os
import sys
from pathlib import Path

# Set up CASA environment before importing CASA
project_root = Path(__file__).parent.parent
casalogs_dir = project_root / "casalogs"
casalogs_dir.mkdir(exist_ok=True)

os.environ['CASA_LOG_DIR'] = str(casalogs_dir.absolute())
os.environ['CASA_LOG_FILE'] = str(casalogs_dir / "casa.log")

# Now import and run the original script
if __name__ == "__main__":
    # Import the original script
    original_script = sys.argv[1] if len(sys.argv) > 1 else None
    if original_script:
        exec(open(original_script).read())
    else:
        print("Usage: python casa_wrapper.py <script.py>")
'''
    
    with open(wrapper_script, 'w') as f:
        f.write(wrapper_content)
    
    # Make it executable
    os.chmod(wrapper_script, 0o755)
    
    print(f"CASA wrapper created: {wrapper_script}")

if __name__ == "__main__":
    setup_casa_environment()
    create_casa_wrapper()
