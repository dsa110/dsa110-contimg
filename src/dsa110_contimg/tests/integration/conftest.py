"""Integration test configuration."""

import sys
from pathlib import Path

# Ensure src directory is in Python path for test imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
