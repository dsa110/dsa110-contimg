"""
Calibration table discovery utilities.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Dict, Optional


def discover_caltables(ms_path: str) -> Dict[str, Optional[str]]:
    """
    Discover calibration tables associated with an MS.

    Args:
        ms_path: Path to the Measurement Set

    Returns:
        Dictionary with keys 'k', 'bp', 'g' mapping to table paths (or None if not found)
    """
    if not os.path.exists(ms_path):
        return {"k": None, "bp": None, "g": None}

    # Get MS directory and base name
    ms_dir = os.path.dirname(ms_path)
    ms_base = os.path.basename(ms_path).replace(".ms", "")

    # Search patterns for cal tables
    k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
    bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
    g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")  # Matches gpcal and gacal

    # Find latest tables (if multiple exist)
    k_tables = sorted(glob.glob(k_pattern), key=os.path.getmtime, reverse=True)
    bp_tables = sorted(glob.glob(bp_pattern), key=os.path.getmtime, reverse=True)
    g_tables = sorted(glob.glob(g_pattern), key=os.path.getmtime, reverse=True)

    return {
        "k": k_tables[0] if k_tables else None,
        "bp": bp_tables[0] if bp_tables else None,
        "g": g_tables[0] if g_tables else None,
    }
