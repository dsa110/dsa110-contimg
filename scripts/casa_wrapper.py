#!/usr/bin/env python3
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
