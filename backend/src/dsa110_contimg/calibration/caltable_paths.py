"""
Calibration table path construction and validation.

Functions for constructing expected calibration table paths based on MS path
and calibration parameters, and validating that all expected tables exist.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Provide a patchable casacore table symbol for unit tests
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()
import casacore.tables as casatables  # type: ignore

table = casatables.table  # noqa: N816


def get_expected_caltables(
    ms_path: str,
    caltable_dir: Optional[str] = None,
    caltype: str = "all",  # "all", "K", "B", "G"
    spwmap: Optional[Dict[int, int]] = None,
) -> Dict[str, List[str]]:
    """
    Construct expected calibration table paths for a Measurement Set.

    Expected naming convention (based on CASA standards):
    - Delay calibration: {ms_basename}.K
    - Bandpass calibration: {ms_basename}.B{spw_index}
    - Gain calibration: {ms_basename}.G

    Args:
        ms_path: Path to Measurement Set
        caltable_dir: Directory containing caltables (default: same as MS)
        caltype: Type of caltables to return ("all", "K", "B", "G")
        spwmap: Optional SPW mapping dict {spw_index: bptable_index}

    Returns:
        Dict with keys:
        - "K": List of delay caltable paths (typically 1)
        - "B": List of bandpass caltable paths (one per SPW or per mapped SPW)
        - "G": List of gain caltable paths (typically 1)
        - "all": List of all expected caltable paths

    Example:
        ms_path = "/data/obs123.ms"
        Returns:
        {
            "K": ["/data/obs123.K"],
            "B": ["/data/obs123.B0", "/data/obs123.B1"],
            "G": ["/data/obs123.G"],
            "all": ["/data/obs123.K", "/data/obs123.B0", "/data/obs123.B1", "/data/obs123.G"]
        }
    """
    ms_path_obj = Path(ms_path)
    ms_basename = ms_path_obj.stem  # "obs123" from "/data/obs123.ms"

    if caltable_dir is None:
        caltable_dir = ms_path_obj.parent
    else:
        caltable_dir = Path(caltable_dir)

    expected = {"K": [], "B": [], "G": [], "all": []}

    # Delay calibration (K)
    if caltype in ("all", "K"):
        k_table = caltable_dir / f"{ms_basename}.K"
        expected["K"].append(str(k_table))

    # Bandpass calibration (B)
    if caltype in ("all", "B"):
        # Need to determine number of SPWs from MS
        n_spws = _get_n_spws_from_ms(ms_path)
        if spwmap:
            # Use mapped SPW indices
            unique_bp_indices = set(spwmap.values())
            for bp_idx in unique_bp_indices:
                b_table = caltable_dir / f"{ms_basename}.B{bp_idx}"
                expected["B"].append(str(b_table))
        else:
            # One BP table per SPW
            for spw_idx in range(n_spws):
                b_table = caltable_dir / f"{ms_basename}.B{spw_idx}"
                expected["B"].append(str(b_table))

    # Gain calibration (G)
    if caltype in ("all", "G"):
        g_table = caltable_dir / f"{ms_basename}.G"
        expected["G"].append(str(g_table))

    # Collect all
    expected["all"] = expected["K"] + expected["B"] + expected["G"]

    return expected


def validate_caltables_exist(
    ms_path: str,
    caltable_dir: Optional[str] = None,
    caltype: str = "all",
    spwmap: Optional[Dict[int, int]] = None,
    raise_on_missing: bool = False,
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Validate that expected calibration tables exist.

    Supports both naming conventions:
    - Standard CASA: {ms_basename}.K, {ms_basename}.B0, {ms_basename}.G
    - DSA-110 convention: {ms_basename}_kcal, {ms_basename}_bpcal, {ms_basename}_gpcal, {ms_basename}_2gcal

    Args:
        ms_path: Path to Measurement Set
        caltable_dir: Directory containing caltables
        caltype: Type of caltables to validate
        spwmap: Optional SPW mapping
        raise_on_missing: If True, raise exception if any tables missing

    Returns:
        Tuple of (existing_tables, missing_tables) dicts
        Each dict has keys: "K", "B", "G", "all"

    Raises:
        FileNotFoundError: If raise_on_missing=True and tables are missing
    """
    import glob

    ms_path_obj = Path(ms_path)
    ms_basename = ms_path_obj.stem

    if caltable_dir is None:
        caltable_dir = ms_path_obj.parent
    else:
        caltable_dir = Path(caltable_dir)

    existing = {"K": [], "B": [], "G": [], "all": []}
    missing = {"K": [], "B": [], "G": [], "all": []}

    # Check for standard CASA naming convention first
    expected_standard = get_expected_caltables(ms_path, caltable_dir, caltype, spwmap)

    # Also check for DSA-110 naming convention (combined tables)
    # Pattern: {ms_basename}_*_kcal, {ms_basename}_*_bpcal, {ms_basename}_*_gpcal, {ms_basename}_*_2gcal
    expected_dsa110 = {"K": [], "B": [], "G": [], "all": []}

    if caltype in ("all", "K"):
        # Look for _kcal tables
        kcal_pattern = str(caltable_dir / f"{ms_basename}_*_kcal")
        kcal_tables = glob.glob(kcal_pattern)
        expected_dsa110["K"].extend(kcal_tables)

    if caltype in ("all", "B"):
        # Look for _bpcal tables
        bpcal_pattern = str(caltable_dir / f"{ms_basename}_*_bpcal")
        bpcal_tables = glob.glob(bpcal_pattern)
        expected_dsa110["B"].extend(bpcal_tables)

    if caltype in ("all", "G"):
        # Look for _gpcal and _2gcal tables
        gpcal_pattern = str(caltable_dir / f"{ms_basename}_*_gpcal")
        gpcal_tables = glob.glob(gpcal_pattern)
        expected_dsa110["G"].extend(gpcal_tables)

        # Also check for _2gcal (second-order gain calibration)
        g2cal_pattern = str(caltable_dir / f"{ms_basename}_*_2gcal")
        g2cal_tables = glob.glob(g2cal_pattern)
        expected_dsa110["G"].extend(g2cal_tables)

    # Combine both naming conventions
    all_expected = {
        "K": expected_standard["K"] + expected_dsa110["K"],
        "B": expected_standard["B"] + expected_dsa110["B"],
        "G": expected_standard["G"] + expected_dsa110["G"],
        "all": expected_standard["all"] + expected_dsa110["all"],
    }

    # Check which tables actually exist
    for caltype_key in ["K", "B", "G"]:
        for table_path in all_expected[caltype_key]:
            if Path(table_path).exists():
                existing[caltype_key].append(table_path)
                existing["all"].append(table_path)
            else:
                # Only report as missing if it's from the standard convention
                # (DSA-110 convention tables may not exist if using standard naming)
                if table_path in expected_standard[caltype_key]:
                    missing[caltype_key].append(table_path)
                    missing["all"].append(table_path)

    # Check if we found DSA-110 convention tables
    dsa110_tables_found = any(
        path in existing[caltype_key]
        for caltype_key in ["K", "B", "G"]
        for path in expected_dsa110[caltype_key]
    )

    # If we found tables using DSA-110 convention (and not standard), don't report standard convention as missing
    # This is because DSA-110 uses a different naming scheme and the standard tables won't exist
    if dsa110_tables_found:
        missing = {"K": [], "B": [], "G": [], "all": []}

    if raise_on_missing and missing["all"]:
        raise FileNotFoundError(
            f"Missing calibration tables for {ms_path}:\n"
            f"  K tables: {missing['K']}\n"
            f"  B tables: {missing['B']}\n"
            f"  G tables: {missing['G']}\n"
            f"  Found tables: {existing['all']}"
        )

    return existing, missing


def _get_n_spws_from_ms(ms_path: str) -> int:
    """Get number of spectral windows from MS."""
    try:
        spw_table_path = str(ms_path) + "/SPECTRAL_WINDOW"
        with table(spw_table_path, ack=False) as spw_table:
            return len(spw_table)
    except Exception as e:
        logger.warning(f"Could not determine SPW count from MS {ms_path}: {e}")
        return 1  # Default to 1 SPW
