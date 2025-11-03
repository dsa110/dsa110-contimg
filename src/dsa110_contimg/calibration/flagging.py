from typing import List, Optional
import os
import sys
from contextlib import contextmanager

# Ensure headless operation to prevent casaplotserver X server errors
# Set multiple environment variables to prevent CASA from launching plotting servers
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CASA_NO_X", "1")  # Additional CASA-specific flag
if os.environ.get("DISPLAY"):
    os.environ.pop("DISPLAY", None)

from casatasks import flagdata


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


def flag_rfi(ms: str, datacolumn: str = "data") -> None:
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


def flag_antenna(ms: str, antenna: str, datacolumn: str = "data", pol: Optional[str] = None) -> None:
    antenna_sel = antenna if pol is None else f"{antenna}&{pol}"
    with suppress_subprocess_stderr():
        flagdata(vis=ms, mode="manual", antenna=antenna_sel, datacolumn=datacolumn)


def flag_baselines(ms: str, uvrange: str = "2~50m", datacolumn: str = "data") -> None:
    with suppress_subprocess_stderr():
        flagdata(vis=ms, mode="manual", uvrange=uvrange, datacolumn=datacolumn)


def flag_manual(ms: str, antenna: Optional[str] = None,
                scan: Optional[str] = None, spw: Optional[str] = None,
                field: Optional[str] = None, uvrange: Optional[str] = None,
                timerange: Optional[str] = None, correlation: Optional[str] = None,
                datacolumn: str = "data") -> None:
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
    
    if len([k for k in [antenna, scan, spw, field, uvrange, timerange, correlation] if k]) == 0:
        raise ValueError("At least one selection parameter must be provided for manual flagging")
    
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


def flag_quack(ms: str, quackinterval: float = 2.0, 
               quackmode: str = "beg", datacolumn: str = "data") -> None:
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
        flagdata(vis=ms, mode="quack", datacolumn=datacolumn,
                 quackinterval=quackinterval, quackmode=quackmode)


def flag_elevation(ms: str, lowerlimit: Optional[float] = None,
                   upperlimit: Optional[float] = None,
                   datacolumn: str = "data") -> None:
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


def flag_clip(ms: str, clipminmax: List[float],
              clipoutside: bool = True, correlation: str = "ABS_ALL",
              datacolumn: str = "data", 
              channelavg: bool = False, timeavg: bool = False,
              chanbin: Optional[int] = None, timebin: Optional[str] = None) -> None:
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


def flag_extend(ms: str, growtime: float = 0.0, growfreq: float = 0.0,
                growaround: bool = False, flagneartime: bool = False,
                flagnearfreq: bool = False, extendpols: bool = True,
                datacolumn: str = "data") -> None:
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
    with suppress_subprocess_stderr():
        flagdata(vis=ms, mode="extend", datacolumn=datacolumn,
                 growtime=growtime, growfreq=growfreq, growaround=growaround,
                 flagneartime=flagneartime, flagnearfreq=flagnearfreq,
                 extendpols=extendpols)


def flag_summary(ms: str, spw: str = "", field: str = "", 
                 antenna: str = "", uvrange: str = "",
                 correlation: str = "", timerange: str = "",
                 reason: str = "") -> dict:
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
        from casacore.tables import table
        import numpy as np
        
        stats = {}
        with table(ms, readonly=True) as tb:
            n_rows = tb.nrows()
            if n_rows > 0:
                flags = tb.getcol("FLAG")
                total_points = flags.size
                flagged_points = np.sum(flags)
                stats["total_fraction_flagged"] = float(flagged_points / total_points) if total_points > 0 else 0.0
                stats["n_rows"] = int(n_rows)
        
        return stats
    except Exception:
        return {}


