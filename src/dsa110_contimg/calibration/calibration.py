import fnmatch
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from casatasks import gaincal as casa_gaincal  # type: ignore[import]

from dsa110_contimg.calibration.validate import (
    validate_caltable_compatibility,
    validate_caltable_exists,
    validate_caltables_for_use,
)
from dsa110_contimg.conversion.merge_spws import get_spw_count
from dsa110_contimg.utils.casa_init import ensure_casa_path

# Initialize CASA environment before importing CASA modules
ensure_casa_path()

# setjy imported elsewhere; avoid unused import here

logger = logging.getLogger(__name__)

# Provide a single casacore tables symbol for the module
import casacore.tables as _casatables  # type: ignore

table = _casatables.table  # noqa: N816


def _get_caltable_spw_count(caltable_path: str) -> Optional[int]:
    """Get the number of unique spectral windows in a calibration table.

    Args:
        caltable_path: Path to calibration table

    Returns:
        Number of unique SPWs, or None if unable to read
    """
    import numpy as np  # type: ignore[import]

    # use module-level table

    try:
        with table(caltable_path, readonly=True) as tb:
            if "SPECTRAL_WINDOW_ID" not in tb.colnames():
                return None
            spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
            return len(np.unique(spw_ids))
    except Exception:
        return None


def _get_casa_version() -> Optional[str]:
    """Get CASA version string.
    
    Returns:
        CASA version string (e.g., "6.7.2"), or None if unavailable
    """
    try:
        import casatools  # type: ignore[import]
        
        # Try to get version from casatools
        if hasattr(casatools, "version"):
            version = casatools.version()
            # Handle both string and list/tuple formats
            if isinstance(version, str):
                return version
            elif isinstance(version, (list, tuple)):
                # Convert list/tuple to string (e.g., [6, 7, 2] -> "6.7.2")
                return ".".join(str(v) for v in version)
            else:
                return str(version)
        
        # Fallback: try casatasks
        try:
            import casatasks  # type: ignore[import]
            if hasattr(casatasks, "version"):
                version = casatasks.version()
                if isinstance(version, str):
                    return version
                elif isinstance(version, (list, tuple)):
                    return ".".join(str(v) for v in version)
                else:
                    return str(version)
        except Exception:
            pass
        
        # Fallback: try environment variable
        casa_version = os.environ.get("CASA_VERSION")
        if casa_version:
            return casa_version
            
        return None
    except Exception:
        return None


def _build_command_string(
    task_name: str, kwargs: Dict[str, Any]
) -> str:
    """Build a human-readable command string from task name and kwargs.
    
    Args:
        task_name: CASA task name (e.g., "gaincal", "bandpass")
        kwargs: Dictionary of task parameters
        
    Returns:
        Formatted command string
    """
    # Filter out None values and format
    filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    # Format parameters
    params = []
    for key, value in sorted(filtered_kwargs.items()):
        if isinstance(value, str):
            params.append(f"{key}='{value}'")
        elif isinstance(value, (list, tuple)):
            params.append(f"{key}={list(value)}")
        else:
            params.append(f"{key}={value}")
    
    return f"{task_name}({', '.join(params)})"


def _extract_quality_metrics(
    caltable_path: str,
) -> Optional[Dict[str, Any]]:
    """Extract quality metrics from a calibration table.
    
    Args:
        caltable_path: Path to calibration table
        
    Returns:
        Dictionary with quality metrics (SNR, flagged_fraction, etc.), or None
    """
    import numpy as np  # type: ignore[import]

    try:
        with table(caltable_path, readonly=True) as tb:
            metrics: Dict[str, Any] = {}
            
            # Number of solutions
            nrows = tb.nrows()
            metrics["n_solutions"] = nrows
            
            if nrows == 0:
                return metrics
            
            # Check for FLAG column
            if "FLAG" in tb.colnames():
                flags = tb.getcol("FLAG")
                if flags.size > 0:
                    flagged_count = np.sum(flags)
                    total_count = flags.size
                    metrics["flagged_fraction"] = float(flagged_count / total_count)
            
            # Check for SNR column
            if "SNR" in tb.colnames():
                snr = tb.getcol("SNR")
                if snr.size > 0:
                    snr_flat = snr.flatten()
                    snr_valid = snr_flat[~np.isnan(snr_flat)]
                    if len(snr_valid) > 0:
                        metrics["snr_mean"] = float(np.mean(snr_valid))
                        metrics["snr_median"] = float(np.median(snr_valid))
                        metrics["snr_min"] = float(np.min(snr_valid))
                        metrics["snr_max"] = float(np.max(snr_valid))
            
            # Number of antennas
            if "ANTENNA1" in tb.colnames():
                ant1 = tb.getcol("ANTENNA1")
                unique_ants = np.unique(ant1)
                metrics["n_antennas"] = len(unique_ants)
            
            # Number of spectral windows
            if "SPECTRAL_WINDOW_ID" in tb.colnames():
                spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
                unique_spws = np.unique(spw_ids)
                metrics["n_spws"] = len(unique_spws)
            
            return metrics if metrics else None
            
    except Exception as e:
        logger.warning(
            f"Failed to extract quality metrics from {caltable_path}: {e}"
        )
        return None


def _track_calibration_provenance(
    ms_path: str,
    caltable_path: str,
    task_name: str,
    params: Dict[str, Any],
    registry_db: Optional[str] = None,
) -> None:
    """Track calibration provenance after successful solve.
    
    This function captures and stores provenance information (source MS,
    solver command, version, parameters, quality metrics) for a calibration table.
    
    Args:
        ms_path: Path to the input MS that generated this caltable
        caltable_path: Path to the calibration table
        task_name: CASA task name used (e.g., "gaincal", "bandpass")
        params: Dictionary of all calibration parameters used
        registry_db: Optional path to registry database (if None, uses default)
    """
    try:
        from pathlib import Path as PathLib
        
        from dsa110_contimg.database.provenance import track_calibration_provenance
        
        # Get CASA version
        casa_version = _get_casa_version()
        
        # Build command string
        command_str = _build_command_string(task_name, params)
        
        # Extract quality metrics
        quality_metrics = _extract_quality_metrics(caltable_path)
        
        # Determine registry DB path
        if registry_db is None:
            # Use default registry path logic
            registry_db_path = PathLib(
                os.environ.get(
                    "CAL_REGISTRY_DB",
                    os.path.join(
                        os.environ.get("PIPELINE_STATE_DIR", "/data/dsa110-contimg/state"),
                        "cal_registry.sqlite3",
                    ),
                )
            )
        else:
            registry_db_path = PathLib(registry_db)
        
        # Track provenance
        track_calibration_provenance(
            registry_db=registry_db_path,
            ms_path=ms_path,
            caltable_path=caltable_path,
            params=params,
            metrics=quality_metrics,
            solver_command=command_str,
            solver_version=casa_version,
        )
        
        logger.debug(
            f"Tracked provenance for {caltable_path} "
            f"(source: {ms_path}, version: {casa_version})"
        )
        
    except Exception as e:
        # Don't fail calibration if provenance tracking fails
        logger.warning(
            f"Failed to track provenance for {caltable_path}: {e}. "
            f"Calibration succeeded but provenance not recorded."
        )


def _determine_spwmap_for_bptables(
    bptables: List[str],
    ms_path: str,
) -> Optional[List[int]]:
    """Determine spwmap parameter for bandpass tables when combine_spw was used.

    When a bandpass table is created with combine_spw=True, it contains solutions
    only for SPW=0 (the aggregate SPW). When applying this table during gain
    calibration, we need to map all MS SPWs to SPW 0 in the bandpass table.

    Args:
        bptables: List of bandpass table paths
        ms_path: Path to Measurement Set

    Returns:
        List of SPW mappings [0, 0, 0, ...] if needed, or None if not needed.
        The length of the list equals the number of SPWs in the MS.
    """
    if not bptables:
        return None

    # Get number of SPWs in MS
    n_ms_spw = get_spw_count(ms_path)
    if n_ms_spw is None or n_ms_spw <= 1:
        return None

    # Check if any bandpass table has only 1 SPW (indicating combine_spw was used)
    for bptable in bptables:
        n_bp_spw = _get_caltable_spw_count(bptable)
        logger.debug(
            f"Checking table {os.path.basename(bptable)}: {n_bp_spw} SPW(s), MS has {n_ms_spw} SPWs"
        )
        if n_bp_spw == 1:
            # This bandpass table was created with combine_spw=True
            # Map all MS SPWs to SPW 0 in the bandpass table
            logger.info(
                f"Detected calibration table {os.path.basename(bptable)} has only 1 SPW (from combine_spw), "
                f"while MS has {n_ms_spw} SPWs. Setting spwmap to map all MS SPWs to SPW 0."
            )
            return [0] * n_ms_spw

    return None


def _validate_solve_success(
    caltable_path: str, refant: Optional[Union[int, str]] = None
) -> None:
    """Validate that a calibration solve completed successfully.

    This ensures we follow "measure twice, cut once" - verify solutions exist
    immediately after each solve completes, before proceeding to the next step.

    Args:
        caltable_path: Path to calibration table
        refant: Optional reference antenna ID to verify has solutions

    Raises:
        RuntimeError: If table doesn't exist, has no solutions, or refant missing
    """
    # use module-level table

    # Verify table exists
    if not os.path.exists(caltable_path):
        raise RuntimeError(
            f"Calibration solve failed: table was not created: {caltable_path}"
        )

    # Verify table has solutions
    try:
        with table(caltable_path, readonly=True) as tb:
            if tb.nrows() == 0:
                raise RuntimeError(
                    f"Calibration solve failed: table has no solutions: {caltable_path}"
                )

            # Verify refant has solutions if provided
            if refant is not None:
                # Handle comma-separated refant string (e.g., "103,111,113,115,104")
                # Use the first antenna in the chain for validation
                if isinstance(refant, str):
                    if "," in refant:
                        # Comma-separated list: use first antenna
                        refant_str = refant.split(",")[0].strip()
                        refant_int = int(refant_str)
                    else:
                        # Single antenna ID as string
                        refant_int = int(refant)
                else:
                    refant_int = refant

                antennas = tb.getcol("ANTENNA1")

                # For antenna-based calibration, check ANTENNA1
                # For baseline-based calibration, check both ANTENNA1 and ANTENNA2
                if "ANTENNA2" in tb.colnames():
                    ant2 = tb.getcol("ANTENNA2")
                    # Filter out -1 values (baseline-based calibration uses -1 for antenna-based entries)
                    ant2_valid = ant2[ant2 != -1]
                    all_antennas = set(antennas) | set(ant2_valid)
                else:
                    all_antennas = set(antennas)

                if refant_int not in all_antennas:
                    raise RuntimeError(
                        f"Calibration solve failed: reference antenna {refant} has no solutions "
                        f"in table: {caltable_path}. Available antennas: {sorted(all_antennas)}"
                    )
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(
            f"Calibration solve validation failed: unable to read table {caltable_path}. "
            f"Error: {e}"
        ) from e


logger = logging.getLogger(__name__)


def _resolve_field_ids(ms: str, field_sel: str) -> List[int]:
    """Resolve CASA-like field selection into a list of FIELD_ID integers.

    Supports numeric indices, comma lists, numeric ranges ("A~B"), and
    name/glob matching against FIELD::NAME.
    """
    # use module-level table

    sel = str(field_sel).strip()
    # Try numeric selections first: comma-separated tokens and A~B ranges
    ids: List[int] = []
    numeric_tokens = [
        tok.strip() for tok in sel.replace(";", ",").split(",") if tok.strip()
    ]

    def _add_numeric(tok: str) -> bool:
        if "~" in tok:
            a, b = tok.split("~", 1)
            if a.strip().isdigit() and b.strip().isdigit():
                ai, bi = int(a), int(b)
                lo, hi = (ai, bi) if ai <= bi else (bi, ai)
                ids.extend(list(range(lo, hi + 1)))
                return True
            return False
        if tok.isdigit():
            ids.append(int(tok))
            return True
        return False

    any_numeric = False
    for tok in numeric_tokens:
        if _add_numeric(tok):
            any_numeric = True

    if any_numeric:
        # Deduplicate and return
        return sorted(set(ids))

    # Fall back to FIELD::NAME glob matching
    patterns = [p for p in numeric_tokens if p]
    # If no separators were present, still try the full selector as a single
    # pattern
    if not patterns:
        patterns = [sel]

    try:
        with table(f"{ms}::FIELD") as tf:
            names = list(tf.getcol("NAME"))
            out = []
            for i, name in enumerate(names):
                for pat in patterns:
                    if fnmatch.fnmatchcase(str(name), pat):
                        out.append(int(i))
                        break
            return sorted(set(out))
    except Exception:
        return []


def solve_delay(
    ms: str,
    cal_field: str,
    refant: str,
    table_prefix: Optional[str] = None,
    combine_spw: bool = False,
    t_slow: str = "inf",
    t_fast: Optional[str] = "60s",
    uvrange: str = "",
    minsnr: float = 5.0,
    skip_slow: bool = False,
) -> List[str]:
    """
    Solve delay (K) on slow and optional fast timescales using CASA gaincal.

    Uses casatasks.gaincal with gaintype='K' to avoid explicit casatools
    calibrater usage, which can be unstable in some notebook environments.

    **PRECONDITION**: MODEL_DATA must be populated before calling this function.
    This ensures consistent, reliable calibration results across all calibrators
    (bright or faint). The calling code should verify MODEL_DATA exists and is
    populated before invoking solve_delay().
    """
    import numpy as np  # type: ignore[import]

    # use module-level table

    # Validate data availability before attempting calibration
    logger.info(f"Validating data for delay solve on field(s) {cal_field}...")

    # PRECONDITION CHECK: Verify MODEL_DATA exists and is populated
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators (bright or faint).
    with table(ms) as tb:
        if "MODEL_DATA" not in tb.colnames():
            raise ValueError(
                f"MODEL_DATA column does not exist in MS. "
                f"This is a required precondition for K-calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_delay()."
            )

        # Check if MODEL_DATA is populated (not all zeros)
        model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
        if np.all(np.abs(model_sample) < 1e-10):
            raise ValueError(
                f"MODEL_DATA column exists but is all zeros (unpopulated). "
                f"This is a required precondition for K-calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_delay()."
            )

        field_ids = tb.getcol("FIELD_ID")
        # Resolve selector (names, ranges, lists) to numeric FIELD_IDs
        target_ids = _resolve_field_ids(ms, str(cal_field))
        if not target_ids:
            raise ValueError(f"Unable to resolve field selection: {cal_field}")
        field_mask = np.isin(field_ids, np.asarray(target_ids, dtype=field_ids.dtype))
        if not np.any(field_mask):
            raise ValueError(f"No data found for field selection {cal_field}")

        # Check if reference antenna exists in this field
        row_idx = np.nonzero(field_mask)[0]
        if row_idx.size == 0:
            raise ValueError(f"No data found for field selection {cal_field}")
        start_row = int(row_idx[0])
        nrow_sel = int(row_idx[-1] - start_row + 1)

        ant1_slice = tb.getcol("ANTENNA1", startrow=start_row, nrow=nrow_sel)
        ant2_slice = tb.getcol("ANTENNA2", startrow=start_row, nrow=nrow_sel)
        rel_idx = row_idx - start_row
        field_ant1 = ant1_slice[rel_idx]
        field_ant2 = ant2_slice[rel_idx]
        ref_present = np.any((field_ant1 == int(refant)) | (field_ant2 == int(refant)))
        if not ref_present:
            raise ValueError(
                f"Reference antenna {refant} not found in field {cal_field}"
            )

        # Check for unflagged data (optimized: use getcol instead of per-row getcell)
        # This is much faster for large MS files
        field_flags = tb.getcol("FLAG", startrow=start_row, nrow=nrow_sel)
        unflagged_count = int(np.sum(~field_flags))
        if unflagged_count == 0:
            raise ValueError(f"All data in field {cal_field} is flagged")

        logger.debug(
            f"Field {cal_field}: {np.sum(field_mask)} rows, "
            f"{unflagged_count} unflagged points"
        )

    # Use more conservative combination settings to avoid empty arrays
    # For field-per-integration MS, avoid combining across scans/obs
    combine = "spw" if combine_spw else ""
    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"

    tables: List[str] = []

    # Slow (infinite) delay solve with error handling
    # OPTIMIZATION: Allow skipping slow solve in fast mode for speed
    if not skip_slow:
        try:
            logger.info(
                f"Running delay solve (K) on field {cal_field} "
                f"with refant {refant}..."
            )
            kwargs = dict(
                vis=ms,
                caltable=f"{table_prefix}_kcal",
                field=cal_field,
                solint=t_slow,
                refant=refant,
                gaintype="K",
                combine=combine,
                minsnr=minsnr,
                selectdata=True,
            )
            if uvrange:
                kwargs["uvrange"] = uvrange
                logger.debug(f"Using uvrange filter: {uvrange}")
            casa_gaincal(**kwargs)
            # PRECONDITION CHECK: Verify K-calibration solve completed successfully
            # This ensures we follow "measure twice, cut once" - verify solutions exist
            # immediately after solve completes, before proceeding.
            _validate_solve_success(f"{table_prefix}_kcal", refant=refant)
            # Track provenance after successful solve
            _track_calibration_provenance(
                ms_path=ms,
                caltable_path=f"{table_prefix}_kcal",
                task_name="gaincal",
                params=kwargs,
            )
            tables.append(f"{table_prefix}_kcal")
            logger.info(f"✓ Delay solve completed: {table_prefix}_kcal")
        except Exception as e:
            logger.error(f"Delay solve failed: {e}")
            # Try with even more conservative settings
            try:
                logger.info("Retrying with no combination...")
                kwargs = dict(
                    vis=ms,
                    caltable=f"{table_prefix}_kcal",
                    field=cal_field,
                    solint=t_slow,
                    refant=refant,
                    gaintype="K",
                    combine="",
                    minsnr=minsnr,
                    selectdata=True,
                )
                if uvrange:
                    kwargs["uvrange"] = uvrange
                casa_gaincal(**kwargs)
                # PRECONDITION CHECK: Verify K-calibration solve completed successfully
                # This ensures we follow "measure twice, cut once" - verify solutions exist
                # immediately after solve completes, before proceeding.
                _validate_solve_success(f"{table_prefix}_kcal", refant=refant)
                # Track provenance after successful solve
                _track_calibration_provenance(
                    ms_path=ms,
                    caltable_path=f"{table_prefix}_kcal",
                    task_name="gaincal",
                    params=kwargs,
                )
                tables.append(f"{table_prefix}_kcal")
                logger.info(f"✓ Delay solve completed (retry): {table_prefix}_kcal")
            except Exception as e2:
                raise RuntimeError(
                    f"Delay solve failed even with conservative settings: {e2}"
                )
    else:
        logger.debug("Skipping slow delay solve (fast mode optimization)")

    # Optional fast (short) delay solve
    # In skip_slow mode, fast solve is required (not optional)
    if t_fast or skip_slow:
        if skip_slow and not t_fast:
            # If skip_slow but no t_fast specified, use default
            t_fast = "60s"
            logger.debug(f"Using default fast solution interval: {t_fast}")
        try:
            logger.info(f"Running fast delay solve (K) on field {cal_field}...")
            kwargs = dict(
                vis=ms,
                caltable=f"{table_prefix}_2kcal",
                field=cal_field,
                solint=t_fast,
                refant=refant,
                gaintype="K",
                combine=combine,
                minsnr=minsnr,
                selectdata=True,
            )
            if uvrange:
                kwargs["uvrange"] = uvrange
            casa_gaincal(**kwargs)
            # PRECONDITION CHECK: Verify fast K-calibration solve completed successfully
            # This ensures we follow "measure twice, cut once" - verify solutions exist
            # immediately after solve completes, before proceeding.
            _validate_solve_success(f"{table_prefix}_2kcal", refant=refant)
            # Track provenance after successful solve
            _track_calibration_provenance(
                ms_path=ms,
                caltable_path=f"{table_prefix}_2kcal",
                task_name="gaincal",
                params=kwargs,
            )
            tables.append(f"{table_prefix}_2kcal")
            logger.info(f"✓ Fast delay solve completed: {table_prefix}_2kcal")
        except Exception as e:
            logger.error(f"Fast delay solve failed: {e}")
            logger.info("Skipping fast delay solve...")

    # QA validation of delay calibration tables (non-blocking: errors are warnings)
    # OPTIMIZATION: Only run QA validation if not in fast mode to avoid performance overhead
    # QA validation reads calibration tables which can be slow for large datasets
    # In fast mode, skip detailed QA to prioritize speed
    # Note: This is a trade-off - fast mode prioritizes speed over comprehensive QA
    if not uvrange or not uvrange.startswith(">"):
        # Only run QA if not in fast mode (no uvrange filter indicates normal mode)
        try:
            from dsa110_contimg.qa.pipeline_quality import check_calibration_quality

            check_calibration_quality(tables, ms_path=ms, alert_on_issues=True)
        except Exception as e:
            logger.warning(f"QA validation failed: {e}")
    else:
        logger.debug("Skipping QA validation (fast mode)")

    return tables


def solve_prebandpass_phase(
    ms: str,
    cal_field: str,
    refant: str,
    table_prefix: Optional[str] = None,
    combine_fields: bool = False,
    combine_spw: bool = False,
    uvrange: str = "",
    # Default to 'inf' to match test expectation and allow long integration when appropriate
    solint: str = "inf",
    # Default to 5.0 to match test expectations and conservative SNR threshold
    minsnr: float = 5.0,
    peak_field_idx: Optional[int] = None,
    minblperant: Optional[int] = None,  # Minimum baselines per antenna
    # SPW selection (e.g., "4~11" for central 8 SPWs)
    spw: Optional[str] = None,
    # Custom table name (e.g., ".bpphase.gcal")
    table_name: Optional[str] = None,
) -> str:
    """Solve phase-only calibration before bandpass to correct phase drifts in raw data.

    This phase-only calibration step is critical for uncalibrated raw data. It corrects
    for time-dependent phase variations that cause decorrelation and low SNR in bandpass
    calibration. This should be run BEFORE bandpass calibration.

    **PRECONDITION**: MODEL_DATA must be populated before calling this function.

    Returns:
        Path to phase-only calibration table (to be passed to bandpass via gaintable)
    """
    import numpy as np  # type: ignore[import]

    # use module-level table

    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"

    # PRECONDITION CHECK: Verify MODEL_DATA exists and is populated
    logger.info(
        f"Validating MODEL_DATA for pre-bandpass phase solve on field(s) {cal_field}..."
    )
    with table(ms) as tb:
        if "MODEL_DATA" not in tb.colnames():
            raise ValueError(
                f"MODEL_DATA column does not exist in MS. "
                f"This is a required precondition for phase-only calibration. "
                f"Populate MODEL_DATA before calling solve_prebandpass_phase()."
            )

        model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
        if np.all(np.abs(model_sample) < 1e-10):
            raise ValueError(
                f"MODEL_DATA column exists but is all zeros (unpopulated). "
                f"This is a required precondition for phase-only calibration. "
                f"Populate MODEL_DATA before calling solve_prebandpass_phase()."
            )

    # Determine field selector based on combine_fields setting
    # - If combining across fields: use the full selection string to maximize SNR
    # - Otherwise: use the peak field (closest to calibrator) if provided, otherwise parse from range
    #   The peak field is the one with maximum PB-weighted flux (closest to calibrator position)
    if combine_fields:
        field_selector = str(cal_field)
    else:
        if peak_field_idx is not None:
            field_selector = str(peak_field_idx)
        elif "~" in str(cal_field):
            # Fallback: use first field in range (should be peak when peak_idx=0)
            field_selector = str(cal_field).split("~")[0]
        else:
            field_selector = str(cal_field)
    logger.debug(
        f"Using field selector '{field_selector}' for pre-bandpass phase solve"
        + (
            f" (combined from range {cal_field})"
            if combine_fields
            else f" (peak field: {field_selector})"
        )
    )

    # Combine across scans, fields, and SPWs when requested
    # Combining SPWs improves SNR by using all 16 subbands simultaneously
    comb_parts = ["scan"]
    if combine_fields:
        comb_parts.append("field")
    if combine_spw:
        comb_parts.append("spw")
    comb = ",".join(comb_parts) if comb_parts else ""

    # VERIFICATION: Check which SPWs are available and will be used
    logger.info("\n" + "=" * 70)
    logger.info("SPW SELECTION VERIFICATION")
    logger.info("=" * 70)
    with table(f"{ms}::SPECTRAL_WINDOW", ack=False) as tspw:
        n_spws = tspw.nrows()
        spw_ids = list(range(n_spws))
        ref_freqs = tspw.getcol("REF_FREQUENCY")
        num_chan = tspw.getcol("NUM_CHAN")
        logger.info(
            f"MS contains {n_spws} spectral windows: SPW {spw_ids[0]} to SPW {spw_ids[-1]}"
        )
        logger.info(
            f"  Frequency range: {ref_freqs[0]/1e9:.4f} - {ref_freqs[-1]/1e9:.4f} GHz"
        )
        logger.info(f"  Total channels across all SPWs: {np.sum(num_chan)}")

    # Check data selection for the specified field
    with table(ms, ack=False) as tb:
        # Get unique SPW IDs in data for the selected field
        # We need to query the actual data to see which SPWs have data
        field_ids = tb.getcol("FIELD_ID")
        spw_ids_in_data = tb.getcol("DATA_DESC_ID")

        # Get unique SPW IDs (need to map DATA_DESC_ID to SPW)
        with table(f"{ms}::DATA_DESCRIPTION", ack=False) as tdd:
            data_desc_to_spw = tdd.getcol("SPECTRAL_WINDOW_ID")

        # Filter by field if field_selector is a single number
        if "~" not in str(field_selector):
            try:
                field_idx = int(field_selector)
                field_mask = field_ids == field_idx
                spw_ids_with_data = np.unique(
                    data_desc_to_spw[spw_ids_in_data[field_mask]]
                )
            except ValueError:
                # Field selector might be a name, use all data
                spw_ids_with_data = np.unique(data_desc_to_spw[spw_ids_in_data])
        else:
            # Range of fields, use all data
            spw_ids_with_data = np.unique(data_desc_to_spw[spw_ids_in_data])

        spw_ids_with_data = sorted(
            [int(x) for x in spw_ids_with_data]
        )  # Convert to plain ints for cleaner output
        logger.info(
            f"\nSPWs with data for field(s) '{field_selector}': {spw_ids_with_data}"
        )
        logger.info(f"  Total SPWs to be processed: {len(spw_ids_with_data)}")

        if combine_spw:
            logger.info(f"\n  COMBINE='spw' is ENABLED:")
            logger.info(
                f"    → All {len(spw_ids_with_data)} SPWs will be used together in a single solve"
            )
            logger.info(f"    → Solution will be stored in SPW ID 0 (aggregate SPW)")
            logger.info(
                f"    → This improves SNR by using all {len(spw_ids_with_data)} subbands simultaneously"
            )
        else:
            logger.info(f"\n  COMBINE='spw' is DISABLED:")
            logger.info(
                f"    → Each of the {len(spw_ids_with_data)} SPWs will be solved separately"
            )
            logger.info(
                f"    → Solutions will be stored in SPW IDs {spw_ids_with_data}"
            )

    logger.info("=" * 70 + "\n")

    # Determine table name
    if table_name:
        caltable_name = table_name
    else:
        caltable_name = f"{table_prefix}_prebp_phase"

    # Solve phase-only calibration (no previous calibrations applied)
    combine_desc = f" (combining across {comb})" if comb else ""
    spw_desc = f" (SPW: {spw})" if spw else ""
    logger.info(
        f"Running pre-bandpass phase-only solve on field {field_selector}{combine_desc}{spw_desc}..."
    )
    kwargs = dict(
        vis=ms,
        caltable=caltable_name,
        field=field_selector,
        spw=spw if spw else "",  # Use provided SPW selection or all SPWs
        solint=solint,
        refant=refant,
        calmode="p",  # Phase-only mode
        combine=comb,
        minsnr=minsnr,
        selectdata=True,
    )
    if uvrange:
        kwargs["uvrange"] = uvrange
    if minblperant is not None:
        kwargs["minblperant"] = minblperant

    casa_gaincal(**kwargs)
    _validate_solve_success(caltable_name, refant=refant)
    # Track provenance after successful solve
    _track_calibration_provenance(
        ms_path=ms,
        caltable_path=caltable_name,
        task_name="gaincal",
        params=kwargs,
    )
    logger.info(f"✓ Pre-bandpass phase-only solve completed: {caltable_name}")

    return caltable_name


def solve_bandpass(
    ms: str,
    cal_field: str,
    refant: str,
    ktable: Optional[str],
    table_prefix: Optional[str] = None,
    set_model: bool = True,
    model_standard: str = "Perley-Butler 2017",
    combine_fields: bool = False,
    combine_spw: bool = False,
    minsnr: float = 5.0,
    uvrange: str = "",  # No implicit UV cut; caller/CLI may provide
    prebandpass_phase_table: Optional[str] = None,
    bp_smooth_type: Optional[str] = None,
    bp_smooth_window: Optional[int] = None,
    peak_field_idx: Optional[int] = None,
    # Custom combine string (e.g., "scan,obs,field")
    combine: Optional[str] = None,
) -> List[str]:
    """Solve bandpass using CASA bandpass task with bandtype='B'.

    This solves for frequency-dependent bandpass correction using the dedicated
    bandpass task, which properly handles per-channel solutions. The bandpass task
    requires a source model (smodel) which is provided via MODEL_DATA column.

    **PRECONDITION**: MODEL_DATA must be populated before calling this function.
    This ensures consistent, reliable calibration results across all calibrators
    (bright or faint). The calling code should verify MODEL_DATA exists and is
    populated before invoking solve_bandpass().

    **NOTE**: `ktable` parameter is kept for API compatibility but is NOT used
    (K-calibration is not used for DSA-110 connected-element array).
    """
    import numpy as np  # type: ignore[import]

    # use module-level table
    from casatasks import bandpass as casa_bandpass  # type: ignore[import]

    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"

    # PRECONDITION CHECK: Verify MODEL_DATA exists and is populated
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators (bright or faint).
    logger.info(f"Validating MODEL_DATA for bandpass solve on field(s) {cal_field}...")
    with table(ms) as tb:
        if "MODEL_DATA" not in tb.colnames():
            raise ValueError(
                f"MODEL_DATA column does not exist in MS. "
                f"This is a required precondition for bandpass calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_bandpass()."
            )

        # Check if MODEL_DATA is populated (not all zeros)
        model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
        if np.all(np.abs(model_sample) < 1e-10):
            raise ValueError(
                f"MODEL_DATA column exists but is all zeros (unpopulated). "
                f"This is a required precondition for bandpass calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_bandpass()."
            )

    # NOTE: K-table is NOT used for bandpass solve (K-calibration is applied in gain step, not before bandpass)
    # K-table parameter is kept for API compatibility but is not applied to bandpass solve

    # Determine CASA field selector based on combine_fields setting
    # - If combining across fields: use the full selection string to maximize SNR
    # - Otherwise: use the peak field (closest to calibrator) if provided, otherwise parse from range
    #   The peak field is the one with maximum PB-weighted flux (closest to calibrator position)
    if combine_fields:
        field_selector = str(cal_field)
    else:
        if peak_field_idx is not None:
            field_selector = str(peak_field_idx)
        elif "~" in str(cal_field):
            # Fallback: use first field in range (should be peak when peak_idx=0)
            field_selector = str(cal_field).split("~")[0]
        else:
            field_selector = str(cal_field)
    logger.debug(
        f"Using field selector '{field_selector}' for bandpass calibration"
        + (
            f" (combined from range {cal_field})"
            if combine_fields
            else f" (peak field: {field_selector})"
        )
    )

    # Avoid setjy here; CLI will write a calibrator MODEL_DATA when available.
    # Note: set_model and model_standard are kept for API compatibility but not used
    # (bandpass task uses MODEL_DATA column directly, not setjy)

    # Combine across scans by default to improve SNR; optionally across fields, SPWs, and obs
    # Only include 'spw' when explicitly requested and scientifically justified
    # (i.e., similar bandpass behavior across SPWs and appropriate spwmap on apply)
    # Note: 'obs' is unusual but can be specified if needed
    # If custom combine string is provided, use it directly
    if combine:
        comb = combine
        logger.debug(f"Using custom combine string: {comb}")
    else:
        comb_parts = ["scan"]
        if combine_fields:
            comb_parts.append("field")
        if combine_spw:
            comb_parts.append("spw")
        comb = ",".join(comb_parts)

    # VERIFICATION: Check which SPWs are available and will be used
    logger.info("\n" + "=" * 70)
    logger.info("SPW SELECTION VERIFICATION")
    logger.info("=" * 70)
    with table(f"{ms}::SPECTRAL_WINDOW", ack=False) as tspw:
        n_spws = tspw.nrows()
        spw_ids = list(range(n_spws))
        ref_freqs = tspw.getcol("REF_FREQUENCY")
        num_chan = tspw.getcol("NUM_CHAN")
        logger.info(
            f"MS contains {n_spws} spectral windows: SPW {spw_ids[0]} to SPW {spw_ids[-1]}"
        )
        logger.info(
            f"  Frequency range: {ref_freqs[0]/1e9:.4f} - {ref_freqs[-1]/1e9:.4f} GHz"
        )
        logger.info(f"  Total channels across all SPWs: {np.sum(num_chan)}")

    # Check data selection for the specified field
    with table(ms, ack=False) as tb:
        field_ids = tb.getcol("FIELD_ID")
        spw_ids_in_data = tb.getcol("DATA_DESC_ID")

        with table(f"{ms}::DATA_DESCRIPTION", ack=False) as tdd:
            data_desc_to_spw = tdd.getcol("SPECTRAL_WINDOW_ID")

        if "~" not in str(field_selector):
            try:
                field_idx = int(field_selector)
                field_mask = field_ids == field_idx
                spw_ids_with_data = np.unique(
                    data_desc_to_spw[spw_ids_in_data[field_mask]]
                )
            except ValueError:
                spw_ids_with_data = np.unique(data_desc_to_spw[spw_ids_in_data])
        else:
            spw_ids_with_data = np.unique(data_desc_to_spw[spw_ids_in_data])

        spw_ids_with_data = sorted(spw_ids_with_data)
        logger.info(
            f"\nSPWs with data for field(s) '{field_selector}': {spw_ids_with_data}"
        )
        logger.info(f"  Total SPWs to be processed: {len(spw_ids_with_data)}")

        if combine_spw:
            logger.info(f"\n  COMBINE='spw' is ENABLED:")
            logger.info(
                f"    → All {len(spw_ids_with_data)} SPWs will be used together in a single solve"
            )
            logger.info(f"    → Solution will be stored in SPW ID 0 (aggregate SPW)")
            logger.info(
                f"    → This improves SNR by using all {len(spw_ids_with_data)} subbands simultaneously"
            )
        else:
            logger.info(f"\n  COMBINE='spw' is DISABLED:")
            logger.info(
                f"    → Each of the {len(spw_ids_with_data)} SPWs will be solved separately"
            )
            logger.info(
                f"    → Solutions will be stored in SPW IDs {spw_ids_with_data}"
            )

    logger.info("=" * 70 + "\n")

    # Use bandpass task with bandtype='B' for proper bandpass calibration
    # The bandpass task requires MODEL_DATA to be populated (smodel source model)
    # uvrange='>1klambda' is the default to avoid short baselines
    # NOTE: Do NOT apply K-table to bandpass solve. K-calibration (delay correction)
    # should be applied AFTER bandpass, not before. Applying K-table before bandpass
    # can corrupt the frequency structure and cause low SNR/flagging.
    # CRITICAL: Apply pre-bandpass phase-only calibration if provided. This corrects
    # phase drifts in raw uncalibrated data that cause decorrelation and low SNR.
    combine_desc = f" (combining across {comb})" if comb else ""
    phase_desc = (
        f" with pre-bandpass phase correction" if prebandpass_phase_table else ""
    )
    logger.info(
        f"Running bandpass solve using bandpass task (bandtype='B') on field {field_selector}{combine_desc}{phase_desc}..."
    )
    kwargs = dict(
        vis=ms,
        caltable=f"{table_prefix}_bpcal",
        field=field_selector,
        solint="inf",  # Per-channel solution (bandpass)
        refant=refant,
        combine=comb,
        solnorm=True,
        bandtype="B",  # Bandpass type B (per-channel)
        selectdata=True,  # Required to use uvrange parameter
        minsnr=minsnr,  # Minimum SNR threshold for solutions
    )
    # Set uvrange (default: '>1klambda' to avoid short baselines)
    if uvrange:
        kwargs["uvrange"] = uvrange
    # Apply pre-bandpass phase-only calibration if provided
    # This corrects phase drifts that cause decorrelation in raw uncalibrated data
    if prebandpass_phase_table:
        kwargs["gaintable"] = [prebandpass_phase_table]
        logger.debug(
            f"  Applying pre-bandpass phase-only calibration: {prebandpass_phase_table}"
        )

        # CRITICAL FIX: Determine spwmap if pre-bandpass phase table was created with combine_spw=True
        # When combine_spw is used, the pre-bandpass phase table has solutions only for SPW=0 (aggregate).
        # We need to map all MS SPWs to SPW 0 in the pre-bandpass phase table.
        spwmap = _determine_spwmap_for_bptables([prebandpass_phase_table], ms)
        if spwmap:
            # spwmap is a list of lists (one per gaintable)
            kwargs["spwmap"] = [spwmap]
            # For phase-only calibration, use linear interpolation (frequency-independent phase)
            kwargs["interp"] = ["linear"]  # One interpolation string per gaintable
            logger.debug(
                f"  Setting spwmap={spwmap} and interp=['linear'] to map all MS SPWs to SPW 0"
            )
    # Do NOT apply K-table to bandpass solve (K-table is applied in gain calibration step)
    casa_bandpass(**kwargs)
    # PRECONDITION CHECK: Verify bandpass solve completed successfully
    # This ensures we follow "measure twice, cut once" - verify solutions exist
    # immediately after solve completes, before proceeding.
    _validate_solve_success(f"{table_prefix}_bpcal", refant=refant)
    # Track provenance after successful solve
    _track_calibration_provenance(
        ms_path=ms,
        caltable_path=f"{table_prefix}_bpcal",
        task_name="bandpass",
        params=kwargs,
    )
    logger.info(f"✓ Bandpass solve completed: {table_prefix}_bpcal")

    # Optional smoothing of bandpass table (post-solve), off by default
    try:
        if (
            bp_smooth_type
            and str(bp_smooth_type).lower() != "none"
            and bp_smooth_window
            and int(bp_smooth_window) > 1
        ):
            try:
                # Prefer CASA smoothcal if available
                from casatasks import (
                    smoothcal as casa_smoothcal,  # type: ignore[import]
                )

                logger.info(
                    f"Smoothing bandpass table '{table_prefix}_bpcal' with {bp_smooth_type} (window={bp_smooth_window})..."
                )
                # Best-effort: in-place smoothing using same output table
                casa_smoothcal(
                    vis=ms,
                    tablein=f"{table_prefix}_bpcal",
                    tableout=f"{table_prefix}_bpcal",
                    smoothtype=str(bp_smooth_type).lower(),
                    smoothwindow=int(bp_smooth_window),
                )
                logger.info("✓ Bandpass table smoothing complete")
            except Exception as e:
                logger.warning(
                    f"Could not smooth bandpass table via CASA smoothcal: {e}"
                )
    except Exception:
        # Do not fail calibration if smoothing parameters are malformed
        pass

    out = [f"{table_prefix}_bpcal"]

    # QA validation of bandpass calibration tables
    try:
        from dsa110_contimg.qa.pipeline_quality import check_calibration_quality

        check_calibration_quality(out, ms_path=ms, alert_on_issues=True)
    except Exception as e:
        logger.warning(f"QA validation failed: {e}")

    return out


def solve_gains(
    ms: str,
    cal_field: str,
    refant: str,
    ktable: Optional[str],
    bptables: List[str],
    table_prefix: Optional[str] = None,
    t_short: str = "60s",
    combine_fields: bool = False,
    *,
    phase_only: bool = False,
    uvrange: str = "",
    solint: str = "inf",
    minsnr: float = 5.0,
    peak_field_idx: Optional[int] = None,
) -> List[str]:
    """Solve gain amplitude and phase; optionally short-timescale.

    **PRECONDITION**: MODEL_DATA must be populated before calling this function.
    This ensures consistent, reliable calibration results across all calibrators
    (bright or faint). The calling code should verify MODEL_DATA exists and is
    populated before invoking solve_gains().

    **PRECONDITION**: If `bptables` are provided, they must exist and be
    compatible with the MS. This ensures consistent, reliable calibration results.

    **NOTE**: `ktable` parameter is kept for API compatibility but is NOT used
    (K-calibration is not used for DSA-110 connected-element array).
    """
    import numpy as np  # type: ignore[import]

    # use module-level table

    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"

    # PRECONDITION CHECK: Verify MODEL_DATA exists and is populated
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators (bright or faint).
    logger.info(f"Validating MODEL_DATA for gain solve on field(s) {cal_field}...")
    with table(ms) as tb:
        if "MODEL_DATA" not in tb.colnames():
            raise ValueError(
                f"MODEL_DATA column does not exist in MS. "
                f"This is a required precondition for gain calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_gains()."
            )

        # Check if MODEL_DATA is populated (not all zeros)
        model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
        if np.all(np.abs(model_sample) < 1e-10):
            raise ValueError(
                f"MODEL_DATA column exists but is all zeros (unpopulated). "
                f"This is a required precondition for gain calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_gains()."
            )

    # PRECONDITION CHECK: Validate all required calibration tables
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators.
    # NOTE: K-table is NOT used for gain calibration (K-calibration not used for DSA-110)
    if bptables:
        logger.info(
            f"Validating {len(bptables)} bandpass table(s) before gain calibration..."
        )
        try:
            # Convert refant string to int for validation
            # Handle comma-separated refant string (e.g., "113,114,103,106,112")
            # Use the first antenna in the chain for validation
            if isinstance(refant, str):
                if "," in refant:
                    # Comma-separated list: use first antenna
                    refant_str = refant.split(",")[0].strip()
                    refant_int = int(refant_str)
                else:
                    # Single antenna ID as string
                    refant_int = int(refant)
            else:
                refant_int = refant
            validate_caltables_for_use(
                bptables, ms, require_all=True, refant=refant_int
            )
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(
                f"Calibration table validation failed. This is a required precondition for "
                f"gain calibration. Error: {e}"
            ) from e

    # Determine CASA field selector based on combine_fields setting
    # - If combining across fields: use the full selection string to maximize SNR
    # - Otherwise: use the peak field (closest to calibrator) if provided, otherwise parse from range
    #   The peak field is the one with maximum PB-weighted flux (closest to calibrator position)
    if combine_fields:
        field_selector = str(cal_field)
    else:
        if peak_field_idx is not None:
            field_selector = str(peak_field_idx)
        elif "~" in str(cal_field):
            # Fallback: use first field in range (should be peak when peak_idx=0)
            field_selector = str(cal_field).split("~")[0]
        else:
            field_selector = str(cal_field)
    logger.debug(
        f"Using field selector '{field_selector}' for gain calibration"
        + (
            f" (combined from range {cal_field})"
            if combine_fields
            else f" (peak field: {field_selector})"
        )
    )

    # NOTE: K-table is NOT used for gain calibration (K-calibration not used for DSA-110)
    # Only apply bandpass tables to gain solve
    gaintable = bptables
    # Combine across scans and fields when requested; otherwise do not combine
    comb = "scan,field" if combine_fields else ""

    # CRITICAL FIX: Determine spwmap if bandpass table was created with combine_spw=True
    # When combine_spw is used, the bandpass table has solutions only for SPW=0 (aggregate).
    # We need to map all MS SPWs to SPW 0 in the bandpass table.
    spwmap = _determine_spwmap_for_bptables(bptables, ms)

    # Always run phase-only gains (calmode='p') after bandpass
    # This corrects for time-dependent phase variations
    logger.info(
        f"Running phase-only gain solve on field {field_selector}"
        + (" (combining across fields)..." if combine_fields else "...")
    )
    kwargs = dict(
        vis=ms,
        caltable=f"{table_prefix}_gpcal",
        field=field_selector,
        solint=solint,
        refant=refant,
        gaintype="G",
        calmode="p",  # Phase-only mode
        gaintable=gaintable,
        combine=comb,
        minsnr=minsnr,
        selectdata=True,
    )
    if uvrange:
        kwargs["uvrange"] = uvrange
    if spwmap:
        kwargs["spwmap"] = spwmap
    casa_gaincal(**kwargs)
    # PRECONDITION CHECK: Verify phase-only gain solve completed successfully
    # This ensures we follow "measure twice, cut once" - verify solutions exist
    # immediately after solve completes, before proceeding.
    _validate_solve_success(f"{table_prefix}_gpcal", refant=refant)
    # Track provenance after successful solve
    _track_calibration_provenance(
        ms_path=ms,
        caltable_path=f"{table_prefix}_gpcal",
        task_name="gaincal",
        params=kwargs,
    )
    logger.info(f"✓ Phase-only gain solve completed: {table_prefix}_gpcal")

    out = [f"{table_prefix}_gpcal"]
    gaintable2 = gaintable + [f"{table_prefix}_gpcal"]

    if t_short:
        logger.info(
            f"Running short-timescale phase-only gain solve on field {field_selector}"
            + (" (combining across fields)..." if combine_fields else "...")
        )
        kwargs = dict(
            vis=ms,
            caltable=f"{table_prefix}_2gcal",
            field=field_selector,
            solint=t_short,
            refant=refant,
            gaintype="G",
            calmode="p",  # Phase-only mode
            gaintable=gaintable2,
            combine=comb,
            minsnr=minsnr,
            selectdata=True,
        )
        if uvrange:
            kwargs["uvrange"] = uvrange
        # CRITICAL FIX: Apply spwmap to second gaincal call as well
        # Note: spwmap applies to bandpass tables in gaintable2; the gain table doesn't need it
        if spwmap:
            kwargs["spwmap"] = spwmap
        casa_gaincal(**kwargs)
        # PRECONDITION CHECK: Verify short-timescale phase-only gain solve completed successfully
        # This ensures we follow "measure twice, cut once" - verify solutions exist
        # immediately after solve completes, before proceeding.
        _validate_solve_success(f"{table_prefix}_2gcal", refant=refant)
        # Track provenance after successful solve
        _track_calibration_provenance(
            ms_path=ms,
            caltable_path=f"{table_prefix}_2gcal",
            task_name="gaincal",
            params=kwargs,
        )
        logger.info(
            f"✓ Short-timescale phase-only gain solve completed: {table_prefix}_2gcal"
        )
        out.append(f"{table_prefix}_2gcal")

    # QA validation of gain calibration tables
    try:
        from dsa110_contimg.qa.pipeline_quality import check_calibration_quality

        check_calibration_quality(out, ms_path=ms, alert_on_issues=True)
    except Exception as e:
        logger.warning(f"QA validation failed: {e}")

    return out
