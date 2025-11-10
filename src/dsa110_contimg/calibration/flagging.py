import logging
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

from casatasks import flagdata

from dsa110_contimg.utils.error_context import format_ms_error_with_suggestions

# Ensure headless operation to prevent casaplotserver X server errors
# Set multiple environment variables to prevent CASA from launching plotting servers
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CASA_NO_X", "1")  # Additional CASA-specific flag
if os.environ.get("DISPLAY"):
    os.environ.pop("DISPLAY", None)


@contextmanager
def suppress_subprocess_stderr():
    """Context manager to suppress stderr from subprocesses (like casaplotserver).

    Redirects stderr at the file descriptor level to suppress casaplotserver errors.
    Note: This only suppresses output to stderr; CASA operations still complete normally.
    """
    devnull_fd = None
    old_stderr = None
    old_stderr_fd = None
    try:
        old_stderr_fd = sys.stderr.fileno()
        # Save original stderr
        old_stderr = os.dup(old_stderr_fd)
        # Open devnull and redirect stderr to it
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, old_stderr_fd)
        yield
    except (AttributeError, OSError):
        # Fallback if fd manipulation fails (e.g., in tests or non-standard environments)
        yield
    finally:
        # Restore original stderr
        if old_stderr is not None and old_stderr_fd is not None:
            try:
                os.dup2(old_stderr, old_stderr_fd)
                os.close(old_stderr)
            except OSError:
                pass
        if devnull_fd is not None:
            try:
                os.close(devnull_fd)
            except OSError:
                pass


def reset_flags(ms: str) -> None:
    with suppress_subprocess_stderr():
        flagdata(vis=ms, mode="unflag")


def flag_zeros(ms: str, datacolumn: str = "data") -> None:
    with suppress_subprocess_stderr():
        flagdata(vis=ms, mode="clip", datacolumn=datacolumn, clipzeros=True)


def flag_rfi(
    ms: str,
    datacolumn: str = "data",
    backend: str = "aoflagger",
    aoflagger_path: Optional[str] = None,
    strategy: Optional[str] = None,
    extend_flags: bool = True,
) -> None:
    """Flag RFI using CASA or AOFlagger.

    Args:
        ms: Path to Measurement Set
        datacolumn: Data column to use (default: "data")
        backend: Backend to use - "aoflagger" (default) or "casa"
        aoflagger_path: Path to aoflagger executable or "docker" (for AOFlagger backend)
        strategy: Optional path to custom Lua strategy file (for AOFlagger backend)
        extend_flags: If True, extend flags to adjacent channels/times after flagging (default: True)
    """
    if backend == "aoflagger":
        flag_rfi_aoflagger(
            ms, datacolumn=datacolumn, aoflagger_path=aoflagger_path, strategy=strategy
        )
        # Extend flags after AOFlagger (if enabled)
        # Note: Flag extension may fail when using Docker due to permission issues
        # (AOFlagger writes as root, making subsequent writes fail). This is non-fatal.
        if extend_flags:
            time.sleep(2)  # Allow file locks to clear
            try:
                flag_extend(
                    ms,
                    flagnearfreq=True,
                    flagneartime=True,
                    extendpols=True,
                    datacolumn=datacolumn,
                )
                logger = logging.getLogger(__name__)
                logger.debug("Flag extension completed successfully")
            except (RuntimeError, PermissionError, OSError) as e:
                # If file lock or permission issue, log warning but don't fail
                logger = logging.getLogger(__name__)
                error_str = str(e).lower()
                if any(
                    term in error_str
                    for term in [
                        "cannot be opened",
                        "not writable",
                        "permission denied",
                        "permission",
                    ]
                ):
                    logger.warning(
                        f"Flag extension skipped due to file permission/lock issue (common when using Docker AOFlagger). "
                        f"RFI flags from AOFlagger are still applied. Error: {e}"
                    )
                else:
                    logger.warning(
                        f"Flag extension failed: {e}. RFI flags from AOFlagger are still applied."
                    )
    else:
        # Two-stage RFI flagging using flagdata modes (tfcrop then rflag)
        with suppress_subprocess_stderr():
            flagdata(
                vis=ms,
                mode="tfcrop",
                datacolumn=datacolumn,
                timecutoff=4.0,
                freqcutoff=4.0,
                timefit="line",
                freqfit="poly",
                maxnpieces=5,
                winsize=3,
                extendflags=False,
            )
            flagdata(
                vis=ms,
                mode="rflag",
                datacolumn=datacolumn,
                timedevscale=4.0,
                freqdevscale=4.0,
                extendflags=False,
            )
        # Extend flags to adjacent channels/times after flagging (if enabled)
        if extend_flags:
            try:
                flag_extend(
                    ms,
                    flagnearfreq=True,
                    flagneartime=True,
                    extendpols=True,
                    datacolumn=datacolumn,
                )
            except RuntimeError as e:
                # If file lock or permission issue, log warning but don't fail
                logger = logging.getLogger(__name__)
                if "cannot be opened" in str(e) or "not writable" in str(e):
                    logger.warning(
                        f"Could not extend flags due to file lock/permission: {e}. Flags from tfcrop+rflag are still applied."
                    )
                else:
                    raise


def _get_default_aoflagger_strategy() -> Optional[str]:
    """Get the default DSA-110 AOFlagger strategy file path.

    Returns:
        Path to dsa110-default.lua if it exists, None otherwise
    """
    # Try multiple possible locations for the strategy file
    possible_paths = [
        Path("/data/dsa110-contimg/config/dsa110-default.lua"),
        Path(__file__).parent.parent.parent.parent / "config" / "dsa110-default.lua",
        Path(os.getcwd()) / "config" / "dsa110-default.lua",
    ]

    for strategy_path in possible_paths:
        if strategy_path.exists():
            return str(strategy_path.resolve())

    return None


def flag_rfi_aoflagger(
    ms: str,
    datacolumn: str = "data",
    aoflagger_path: Optional[str] = None,
    strategy: Optional[str] = None,
) -> None:
    """Flag RFI using AOFlagger (faster alternative to CASA tfcrop).

    AOFlagger uses the SumThreshold algorithm which is typically 2-5x faster
    than CASA's tfcrop+rflag combination for large datasets.

    **Note:** On Ubuntu 18.x systems, Docker is required due to CMake/pybind11
    compatibility issues. The default behavior is to use Docker if available.

    Args:
        ms: Path to Measurement Set
        datacolumn: Data column to use (default: "data")
        aoflagger_path: Path to aoflagger executable, "docker" to force Docker, or None to auto-detect
        strategy: Optional path to custom Lua strategy file. If None, uses DSA-110 default strategy
                 from config/dsa110-default.lua if available, otherwise uses AOFlagger auto-detection.

    Raises:
        RuntimeError: If AOFlagger is not available
        subprocess.CalledProcessError: If AOFlagger execution fails
    """
    logger = logging.getLogger(__name__)

    # Determine AOFlagger command
    # Default to Docker since AOFlagger was built for Docker on Ubuntu 18.x
    use_docker = False
    if aoflagger_path:
        if aoflagger_path == "docker":
            # Force Docker usage
            docker_cmd = shutil.which("docker")
            if not docker_cmd:
                suggestions = [
                    "Install Docker",
                    "Verify Docker is in PATH",
                    "Check Docker service is running",
                    "Use --aoflagger-path to specify native AOFlagger location",
                ]
                error_msg = format_ms_error_with_suggestions(
                    RuntimeError(
                        "Docker not found but --aoflagger-path=docker was specified"
                    ),
                    ms,
                    "AOFlagger setup",
                    suggestions,
                )
                raise RuntimeError(error_msg)
            use_docker = True
            # Use current user ID to avoid permission issues
            user_id = os.getuid()
            group_id = os.getgid()
            aoflagger_cmd = [
                docker_cmd,
                "run",
                "--rm",
                "--user",
                f"{user_id}:{group_id}",
                "-v",
                "/scratch:/scratch",
                "-v",
                "/data:/data",
                "-v",
                "/stage:/stage",
                "aoflagger:latest",
                "aoflagger",
            ]
        else:
            # Explicit path provided - use it directly
            aoflagger_cmd = [aoflagger_path]
            logger.info(f"Using AOFlagger from explicit path: {aoflagger_path}")
    else:
        # Auto-detect: prefer Docker (since that's what we built) but check for native
        docker_cmd = shutil.which("docker")
        native_aoflagger = shutil.which("aoflagger")

        if docker_cmd:
            # Docker is available - use it by default (works on Ubuntu 18.x)
            use_docker = True
            # Use current user ID to avoid permission issues
            user_id = os.getuid()
            group_id = os.getgid()
            aoflagger_cmd = [
                docker_cmd,
                "run",
                "--rm",
                "--user",
                f"{user_id}:{group_id}",
                "-v",
                "/scratch:/scratch",
                "-v",
                "/data:/data",
                "-v",
                "/stage:/stage",
                "aoflagger:latest",
                "aoflagger",
            ]
            if native_aoflagger:
                logger.debug(
                    "Both Docker and native AOFlagger available; using Docker (Ubuntu 18.x compatible)"
                )
            else:
                logger.debug("Using Docker for AOFlagger (native not found)")
        elif native_aoflagger:
            # Fall back to native if Docker not available
            aoflagger_cmd = [native_aoflagger]
            logger.info("Using native AOFlagger (Docker not available)")
        else:
            suggestions = [
                "Install Docker and build aoflagger:latest image",
                "Install native AOFlagger and ensure it's in PATH",
                "Use --aoflagger-path to specify AOFlagger location",
                "Check AOFlagger installation documentation",
            ]
            error_msg = format_ms_error_with_suggestions(
                RuntimeError(
                    "AOFlagger not found. Docker is required on Ubuntu 18.x systems."
                ),
                ms,
                "AOFlagger setup",
                suggestions,
            )
            raise RuntimeError(error_msg)

    # Build command
    cmd = aoflagger_cmd.copy()

    # Determine strategy to use
    strategy_to_use = strategy
    if strategy_to_use is None:
        # Try to use DSA-110 default strategy
        default_strategy = _get_default_aoflagger_strategy()
        if default_strategy:
            strategy_to_use = default_strategy
            logger.info(f"Using DSA-110 default AOFlagger strategy: {strategy_to_use}")
        else:
            logger.debug(
                "No default strategy found; AOFlagger will auto-detect strategy"
            )

    # Add strategy if we have one
    if strategy_to_use:
        # When using Docker, ensure the strategy path is accessible inside the container
        if use_docker:
            # Strategy file must be under /data or /stage (mounted volumes)
            strategy_path = Path(strategy_to_use)
            if not str(strategy_path).startswith(("/data", "/stage")):
                # Try to find it under /data
                strategy_name = strategy_path.name
                docker_strategy_path = f"/data/dsa110-contimg/config/{strategy_name}"
                if Path("/data/dsa110-contimg/config/dsa110-default.lua").exists():
                    strategy_to_use = docker_strategy_path
                    logger.debug(
                        f"Using Docker-accessible strategy path: {strategy_to_use}"
                    )
                else:
                    logger.warning(
                        f"Strategy file {strategy_to_use} may not be accessible in Docker container. "
                        f"Ensure it's under /data or /stage, or mount it explicitly."
                    )
        cmd.extend(["-strategy", strategy_to_use])

    # Add MS path (required - AOFlagger will auto-detect strategy if not specified)
    cmd.append(ms)

    # Execute AOFlagger
    logger.info(f"Running AOFlagger: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, capture_output=False)
        logger.info("✓ AOFlagger RFI flagging complete")
    except subprocess.CalledProcessError as e:
        logger.error(f"AOFlagger failed with exit code {e.returncode}")
        raise
    except FileNotFoundError:
        suggestions = [
            "Check AOFlagger installation",
            "Verify AOFlagger is in PATH",
            "Use --aoflagger-path to specify AOFlagger location",
            "Check Docker image is available (if using Docker)",
        ]
        error_msg = format_ms_error_with_suggestions(
            FileNotFoundError(f"AOFlagger executable not found: {aoflagger_cmd[0]}"),
            ms,
            "AOFlagger execution",
            suggestions,
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def flag_antenna(
    ms: str, antenna: str, datacolumn: str = "data", pol: Optional[str] = None
) -> None:
    antenna_sel = antenna if pol is None else f"{antenna}&{pol}"
    with suppress_subprocess_stderr():
        flagdata(vis=ms, mode="manual", antenna=antenna_sel, datacolumn=datacolumn)


def flag_baselines(ms: str, uvrange: str = "2~50m", datacolumn: str = "data") -> None:
    with suppress_subprocess_stderr():
        flagdata(vis=ms, mode="manual", uvrange=uvrange, datacolumn=datacolumn)


def flag_manual(
    ms: str,
    antenna: Optional[str] = None,
    scan: Optional[str] = None,
    spw: Optional[str] = None,
    field: Optional[str] = None,
    uvrange: Optional[str] = None,
    timerange: Optional[str] = None,
    correlation: Optional[str] = None,
    datacolumn: str = "data",
) -> None:
    """Manual flagging with selection parameters.

    Flags data matching the specified selection criteria using CASA's
    standard selection syntax. All parameters are optional - specify any
    combination to flag matching data.

    Args:
        ms: Path to Measurement Set
        antenna: Antenna selection (e.g., '0,1,2' or 'ANT01,ANT02')
        scan: Scan selection (e.g., '1~5' or '1,3,5')
        spw: Spectral window selection (e.g., '0:10~20')
        field: Field selection (field IDs or names)
        uvrange: UV range selection (e.g., '>100m' or '10~50m')
        timerange: Time range selection (e.g., '2025/01/01/10:00:00~10:05:00')
        correlation: Correlation product selection (e.g., 'RR,LL')
        datacolumn: Data column to use (default: 'data')

    Note: At least one selection parameter must be provided.
    """
    kwargs = {"vis": ms, "mode": "manual", "datacolumn": datacolumn}
    if antenna:
        kwargs["antenna"] = antenna
    if scan:
        kwargs["scan"] = scan
    if spw:
        kwargs["spw"] = spw
    if field:
        kwargs["field"] = field
    if uvrange:
        kwargs["uvrange"] = uvrange
    if timerange:
        kwargs["timerange"] = timerange
    if correlation:
        kwargs["correlation"] = correlation

    if (
        len(
            [
                k
                for k in [antenna, scan, spw, field, uvrange, timerange, correlation]
                if k
            ]
        )
        == 0
    ):
        suggestions = [
            "Provide at least one selection parameter (antenna, time, baseline, etc.)",
            "Check manual flagging command syntax",
            "Review flagging documentation for parameter requirements",
        ]
        error_msg = format_ms_error_with_suggestions(
            ValueError(
                "At least one selection parameter must be provided for manual flagging"
            ),
            ms,
            "manual flagging",
            suggestions,
        )
        raise ValueError(error_msg)

    with suppress_subprocess_stderr():
        flagdata(**kwargs)


def flag_shadow(ms: str, tolerance: float = 0.0) -> None:
    """Flag geometrically shadowed baselines.

    Flags data where one antenna physically blocks the line of sight
    between another antenna and the source. This is particularly important
    for low-elevation observations and compact array configurations.

    Args:
        ms: Path to Measurement Set
        tolerance: Shadowing tolerance in degrees (default: 0.0)
    """
    with suppress_subprocess_stderr():
        flagdata(vis=ms, mode="shadow", tolerance=tolerance)


def flag_quack(
    ms: str,
    quackinterval: float = 2.0,
    quackmode: str = "beg",
    datacolumn: str = "data",
) -> None:
    """Flag beginning/end of scans to remove antenna settling transients.

    After slewing to a new source, antennas require time to stabilize
    thermally and mechanically. This function flags the specified duration
    from the beginning or end of each scan.

    Args:
        ms: Path to Measurement Set
        quackinterval: Duration in seconds to flag (default: 2.0)
        quackmode: 'beg' (beginning), 'end', 'tail', or 'endb' (default: 'beg')
        datacolumn: Data column to use (default: 'data')
    """
    with suppress_subprocess_stderr():
        flagdata(
            vis=ms,
            mode="quack",
            datacolumn=datacolumn,
            quackinterval=quackinterval,
            quackmode=quackmode,
        )


def flag_elevation(
    ms: str,
    lowerlimit: Optional[float] = None,
    upperlimit: Optional[float] = None,
    datacolumn: str = "data",
) -> None:
    """Flag observations below/above specified elevation limits.

    Low-elevation observations suffer from increased atmospheric opacity,
    phase instability, and reduced sensitivity. High-elevation observations
    may have other issues. This function flags data outside specified limits.

    Args:
        ms: Path to Measurement Set
        lowerlimit: Minimum elevation in degrees (flag data below this)
        upperlimit: Maximum elevation in degrees (flag data above this)
        datacolumn: Data column to use (default: 'data')
    """
    kwargs = {"vis": ms, "mode": "elevation", "datacolumn": datacolumn}
    if lowerlimit is not None:
        kwargs["lowerlimit"] = lowerlimit
    if upperlimit is not None:
        kwargs["upperlimit"] = upperlimit
    with suppress_subprocess_stderr():
        flagdata(**kwargs)


def flag_clip(
    ms: str,
    clipminmax: List[float],
    clipoutside: bool = True,
    correlation: str = "ABS_ALL",
    datacolumn: str = "data",
    channelavg: bool = False,
    timeavg: bool = False,
    chanbin: Optional[int] = None,
    timebin: Optional[str] = None,
) -> None:
    """Flag data outside specified amplitude thresholds.

    Flags visibility amplitudes that fall outside acceptable ranges.
    Useful for identifying extreme outliers, strong RFI, or systematic problems.

    Args:
        ms: Path to Measurement Set
        clipminmax: [min, max] amplitude range in Jy
        clipoutside: If True, flag outside range; if False, flag inside range
        correlation: Correlation product ('ABS_ALL', 'RR', 'LL', etc.)
        datacolumn: Data column to use (default: 'data')
        channelavg: Average channels before clipping
        timeavg: Average time before clipping
        chanbin: Channel binning factor
        timebin: Time binning (e.g., '30s')
    """
    kwargs = {
        "vis": ms,
        "mode": "clip",
        "datacolumn": datacolumn,
        "clipminmax": clipminmax,
        "clipoutside": clipoutside,
        "correlation": correlation,
    }
    if channelavg or chanbin:
        kwargs["channelavg"] = channelavg
        if chanbin:
            kwargs["chanbin"] = chanbin
    if timeavg or timebin:
        kwargs["timeavg"] = timeavg
        if timebin:
            kwargs["timebin"] = timebin
    with suppress_subprocess_stderr():
        flagdata(**kwargs)


def flag_extend(
    ms: str,
    growtime: float = 0.0,
    growfreq: float = 0.0,
    growaround: bool = False,
    flagneartime: bool = False,
    flagnearfreq: bool = False,
    extendpols: bool = True,
    datacolumn: str = "data",
) -> None:
    """Extend existing flags to neighboring data points.

    RFI often affects neighboring channels, times, or correlations through
    hardware responses, cross-talk, or physical proximity. This function
    grows flagged regions appropriately.

    Args:
        ms: Path to Measurement Set
        growtime: Fraction of time already flagged to flag entire time slot (0-1)
        growfreq: Fraction of frequency already flagged to flag entire channel (0-1)
        growaround: Flag points if most neighbors are flagged
        flagneartime: Flag points immediately before/after flagged regions
        flagnearfreq: Flag points immediately adjacent to flagged channels
        extendpols: Extend flags across polarization products
        datacolumn: Data column to use (default: 'data')
    """
    # Try using CASA flagdata first
    try:
        with suppress_subprocess_stderr():
            flagdata(
                vis=ms,
                mode="extend",
                datacolumn=datacolumn,
                growtime=growtime,
                growfreq=growfreq,
                growaround=growaround,
                flagneartime=flagneartime,
                flagnearfreq=flagnearfreq,
                extendpols=extendpols,
                flagbackup=False,
            )
    except RuntimeError as e:
        # If CASA fails due to file lock, try direct casacore approach for simple extension
        if ("cannot be opened" in str(e) or "not writable" in str(e)) and (
            flagneartime or flagnearfreq
        ):
            logger = logging.getLogger(__name__)
            logger.debug("CASA flagdata failed, trying direct casacore flag extension")
            try:
                _extend_flags_direct(
                    ms,
                    flagneartime=flagneartime,
                    flagnearfreq=flagnearfreq,
                    extendpols=extendpols,
                )
            except Exception as e2:
                logger.warning(
                    f"Direct flag extension also failed: {e2}. Flag extension skipped."
                )
                raise RuntimeError(f"Flag extension failed: {e}") from e
        else:
            raise


def _extend_flags_direct(
    ms: str,
    flagneartime: bool = False,
    flagnearfreq: bool = False,
    extendpols: bool = True,
) -> None:
    """Extend flags directly using casacore.tables (fallback when CASA flagdata fails).

    This is a simpler implementation that only handles adjacent channel/time extension.
    For more complex extension (growaround, growtime, etc.), use CASA flagdata.
    """
    try:
        import numpy as np
        from casacore.tables import table

        with table(ms, readonly=False, ack=False) as tb:
            flags = tb.getcol("FLAG")

            if flags.size == 0:
                return

            # Create extended flags
            extended_flags = flags.copy()

            # Extend in frequency direction (adjacent channels)
            if flagnearfreq:
                # Shape: (nrows, nchans, npols)
                nrows, nchans, npols = flags.shape
                for row in range(nrows):
                    for pol in range(npols):
                        row_flags = flags[row, :, pol]
                        # Flag channels adjacent to flagged channels
                        flagged_chans = np.where(row_flags)[0]
                        for chan in flagged_chans:
                            if chan > 0:
                                extended_flags[row, chan - 1, pol] = True
                            if chan < nchans - 1:
                                extended_flags[row, chan + 1, pol] = True

            # Extend in time direction (adjacent time samples)
            if flagneartime:
                # Flag time samples adjacent to flagged samples
                nrows, nchans, npols = flags.shape
                for row in range(nrows):
                    if np.any(flags[row]):
                        # Flag adjacent rows (time samples)
                        if row > 0:
                            extended_flags[row - 1] = (
                                extended_flags[row - 1] | flags[row]
                            )
                        if row < nrows - 1:
                            extended_flags[row + 1] = (
                                extended_flags[row + 1] | flags[row]
                            )

            # Extend across polarizations
            if extendpols:
                # If any pol is flagged, flag all pols
                nrows, nchans, npols = flags.shape
                for row in range(nrows):
                    for chan in range(nchans):
                        if np.any(flags[row, chan]):
                            extended_flags[row, chan, :] = True

            # Write extended flags back
            tb.putcol("FLAG", extended_flags)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.debug(f"Direct flag extension failed: {e}")
        raise


def analyze_channel_flagging_stats(
    ms_path: str, threshold: float = 0.5
) -> Dict[int, List[int]]:
    """Analyze flagging statistics per channel across all SPWs.

    After RFI flagging, this function identifies channels that have high flagging
    rates and should be flagged entirely before calibration. This is more precise
    than SPW-level flagging since SPWs are arbitrary subdivisions for data processing.

    Args:
        ms_path: Path to Measurement Set
        threshold: Fraction of flagged data to consider channel problematic (default: 0.5)

    Returns:
        Dict mapping SPW ID -> list of problematic channel indices

    Example:
        >>> problematic = analyze_channel_flagging_stats('data.ms', threshold=0.5)
        >>> # Returns: {1: [5, 10, 15, 20], 12: [3, 7, 11]}
    """
    import numpy as np
    from casacore.tables import table

    logger = logging.getLogger(__name__)
    problematic_channels = {}

    try:
        with table(ms_path, readonly=True) as tb:
            flags = tb.getcol("FLAG")  # Shape: (nrows, nchannels, npol)
            data_desc_id = tb.getcol("DATA_DESC_ID")

            # Get SPW mapping from DATA_DESCRIPTION table
            with table(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as dd:
                spw_ids = dd.getcol("SPECTRAL_WINDOW_ID")

            # Get unique SPWs present in data
            unique_ddids = np.unique(data_desc_id)
            unique_spws = np.unique([spw_ids[ddid] for ddid in unique_ddids])

            logger.debug(f"Analyzing channel flagging for {len(unique_spws)} SPW(s)")

            for spw in unique_spws:
                # Get rows for this SPW
                spw_mask = np.array([spw_ids[ddid] == spw for ddid in data_desc_id])
                spw_flags = flags[spw_mask]

                if len(spw_flags) == 0:
                    continue

                # Calculate flagging fraction per channel
                # flags shape: (nrows, nchannels, npol)
                # Average across rows and polarizations
                channel_flagging = np.mean(spw_flags, axis=(0, 2))

                # Find channels above threshold
                problematic = np.where(channel_flagging > threshold)[0].tolist()

                if problematic:
                    problematic_channels[int(spw)] = problematic
                    logger.debug(
                        f"SPW {spw}: {len(problematic)}/{len(channel_flagging)} channels "
                        f"above {threshold*100:.1f}% flagging threshold"
                    )

    except Exception as e:
        logger.warning(f"Failed to analyze channel flagging statistics: {e}")
        logger.warning("Skipping channel-level flagging analysis")

    return problematic_channels


def flag_problematic_channels(
    ms_path: str, problematic_channels: Dict[int, List[int]], datacolumn: str = "data"
) -> None:
    """Flag problematic channels using CASA flagdata.

    Args:
        ms_path: Path to Measurement Set
        problematic_channels: Dict mapping SPW ID -> list of channel indices
        datacolumn: Data column to flag (default: "data")

    Raises:
        RuntimeError: If flagdata fails
    """
    from casatasks import flagdata

    logger = logging.getLogger(__name__)

    if not problematic_channels:
        logger.debug("No problematic channels to flag")
        return

    # Build SPW selection string for CASA flagdata
    # Format: "spw:chan1,chan2,chan3;spw:chan1,chan2"
    spw_selections = []
    total_channels = 0

    for spw, channels in sorted(problematic_channels.items()):
        # Sort channels for cleaner output
        channels_sorted = sorted(channels)
        chan_str = ",".join(map(str, channels_sorted))
        spw_selections.append(f"{spw}:{chan_str}")
        total_channels += len(channels_sorted)
        logger.info(
            f"  SPW {spw}: {len(channels_sorted)} problematic channels "
            f"({channels_sorted[:5]}{'...' if len(channels_sorted) > 5 else ''})"
        )

    spw_sel = ";".join(spw_selections)

    logger.info(
        f"Flagging {total_channels} problematic channel(s) across "
        f"{len(problematic_channels)} SPW(s) before calibration"
    )

    try:
        flagdata(
            vis=ms_path,
            spw=spw_sel,
            mode="manual",
            datacolumn=datacolumn,
            flagbackup=False,
        )
        logger.info(
            f"✓ Flagged {total_channels} problematic channel(s) before calibration"
        )
    except Exception as e:
        logger.error(f"Failed to flag problematic channels: {e}")
        raise RuntimeError(f"Channel flagging failed: {e}") from e


def flag_summary(
    ms: str,
    spw: str = "",
    field: str = "",
    antenna: str = "",
    uvrange: str = "",
    correlation: str = "",
    timerange: str = "",
    reason: str = "",
) -> dict:
    """Report flagging statistics without flagging data.

    Provides comprehensive statistics about existing flags, including
    total flagged fraction, breakdowns by antenna, spectral window,
    polarization, and other dimensions. Useful for understanding data quality
    and identifying problematic subsets.

    Args:
        ms: Path to Measurement Set
        spw: Spectral window selection
        field: Field selection
        antenna: Antenna selection
        uvrange: UV range selection
        correlation: Correlation product selection
        timerange: Time range selection
        reason: Flag reason to query

    Returns:
        Dictionary with flagging statistics
    """
    kwargs = {"vis": ms, "mode": "summary", "display": "report"}
    if spw:
        kwargs["spw"] = spw
    if field:
        kwargs["field"] = field
    if antenna:
        kwargs["antenna"] = antenna
    if uvrange:
        kwargs["uvrange"] = uvrange
    if correlation:
        kwargs["correlation"] = correlation
    if timerange:
        kwargs["timerange"] = timerange
    if reason:
        kwargs["reason"] = reason

    # Skip calling flagdata in summary mode - it triggers casaplotserver which hangs
    # Instead, directly read flags from the MS using casacore.tables
    # This is faster and avoids subprocess issues
    # with suppress_subprocess_stderr():
    #     flagdata(**kwargs)

    # Parse summary statistics directly from MS (faster and avoids casaplotserver)
    try:
        import numpy as np
        from casacore.tables import table

        stats = {}
        with table(ms, readonly=True) as tb:
            n_rows = tb.nrows()
            if n_rows > 0:
                flags = tb.getcol("FLAG")
                total_points = flags.size
                flagged_points = np.sum(flags)
                stats["total_fraction_flagged"] = (
                    float(flagged_points / total_points) if total_points > 0 else 0.0
                )
                stats["n_rows"] = int(n_rows)

        return stats
    except Exception:
        return {}
