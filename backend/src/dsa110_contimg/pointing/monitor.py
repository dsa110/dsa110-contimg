"""
Pointing Monitor - Tracks telescope pointing and predicts calibrator transits.

This module provides utilities for:
- Calculating Local Sidereal Time (LST)
- Predicting when calibrators transit the meridian
- Monitoring pointing status for the pipeline
- Maintaining pointing history in the database

The DSA-110 is a drift-scan telescope that observes sources as they transit
the meridian. This monitor helps coordinate observations with calibrator passes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time

from ..utils.constants import DSA110_LOCATION, DSA110_LONGITUDE

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_STATUS_FILE = Path("/data/dsa110-contimg/state/pointing_status.json")
DEFAULT_LOG_DIR = Path("/data/dsa110-contimg/state/logs")

# Standard VLA calibrators visible from DSA-110 (dec > -40 deg)
DEFAULT_CALIBRATORS = {
    "3C286": {"ra": 202.7845, "dec": 30.5092, "flux_1400": 14.65},  # Primary flux cal
    "3C48": {"ra": 24.4220, "dec": 33.1597, "flux_1400": 15.67},
    "3C147": {"ra": 85.6505, "dec": 49.8520, "flux_1400": 21.64},
    "3C138": {"ra": 80.2912, "dec": 16.6394, "flux_1400": 8.23},
    "J0834+555": {"ra": 128.5813, "dec": 55.5750, "flux_1400": 5.0},
    "J1331+3030": {"ra": 202.7845, "dec": 30.5092, "flux_1400": 14.65},  # = 3C286
}


@dataclass
class TransitPrediction:
    """Prediction for a calibrator transit."""
    
    calibrator: str
    ra_deg: float
    dec_deg: float
    transit_utc: datetime
    time_to_transit_sec: float
    lst_at_transit: float
    elevation_at_transit: float
    status: str  # 'upcoming', 'in_progress', 'completed'
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "calibrator": self.calibrator,
            "ra_deg": self.ra_deg,
            "dec_deg": self.dec_deg,
            "transit_utc": self.transit_utc.isoformat() + "Z",
            "time_to_transit_sec": round(self.time_to_transit_sec, 1),
            "lst_at_transit": round(self.lst_at_transit, 4),
            "elevation_at_transit": round(self.elevation_at_transit, 2),
            "status": self.status,
        }


@dataclass
class PointingStatus:
    """Current pointing monitor status."""
    
    current_lst: float
    current_utc: str
    active_calibrator: Optional[str] = None
    upcoming_transits: List[TransitPrediction] = field(default_factory=list)
    recent_transits: List[TransitPrediction] = field(default_factory=list)
    monitor_healthy: bool = True
    last_update: str = ""
    uptime_sec: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "current_lst": round(self.current_lst, 4),
            "current_utc": self.current_utc,
            "active_calibrator": self.active_calibrator,
            "upcoming_transits": [t.to_dict() for t in self.upcoming_transits],
            "recent_transits": [t.to_dict() for t in self.recent_transits],
            "monitor_healthy": self.monitor_healthy,
            "last_update": self.last_update,
            "uptime_sec": round(self.uptime_sec, 1),
        }


def calculate_lst(
    utc_time: Optional[datetime] = None,
    location: Optional[EarthLocation] = None,
) -> float:
    """
    Calculate Local Sidereal Time (LST) at DSA-110.
    
    Args:
        utc_time: UTC datetime (default: now)
        location: Observatory location (default: DSA-110)
        
    Returns:
        LST in hours (0-24)
    """
    if utc_time is None:
        utc_time = datetime.utcnow()
    if location is None:
        location = DSA110_LOCATION
    
    t = Time(utc_time, scale='utc', location=location)
    lst = t.sidereal_time('mean')
    return lst.hour


def calculate_elevation(
    ra_deg: float,
    dec_deg: float,
    utc_time: Optional[datetime] = None,
    location: Optional[EarthLocation] = None,
) -> float:
    """
    Calculate elevation of a source at DSA-110.
    
    Args:
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        utc_time: UTC datetime (default: now)
        location: Observatory location (default: DSA-110)
        
    Returns:
        Elevation in degrees
    """
    from astropy.coordinates import AltAz
    
    if utc_time is None:
        utc_time = datetime.utcnow()
    if location is None:
        location = DSA110_LOCATION
    
    t = Time(utc_time, scale='utc')
    coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame='icrs')
    altaz_frame = AltAz(obstime=t, location=location)
    altaz = coord.transform_to(altaz_frame)
    return float(altaz.alt.deg)


def predict_calibrator_transit(
    calibrator: str,
    from_time: Optional[datetime] = None,
    calibrators: Optional[Dict] = None,
    location: Optional[EarthLocation] = None,
) -> Optional[TransitPrediction]:
    """
    Predict the next transit of a calibrator.
    
    The transit occurs when LST = RA (source crosses meridian).
    
    Args:
        calibrator: Name of calibrator
        from_time: Start time for prediction (default: now)
        calibrators: Calibrator catalog (default: DEFAULT_CALIBRATORS)
        location: Observatory location (default: DSA-110)
        
    Returns:
        TransitPrediction or None if calibrator not found
    """
    if calibrators is None:
        calibrators = DEFAULT_CALIBRATORS
    if location is None:
        location = DSA110_LOCATION
    if from_time is None:
        from_time = datetime.utcnow()
    
    if calibrator not in calibrators:
        logger.warning(f"Unknown calibrator: {calibrator}")
        return None
    
    info = calibrators[calibrator]
    ra_deg = info["ra"]
    dec_deg = info["dec"]
    
    # RA in hours (transit occurs when LST = RA)
    ra_hours = ra_deg / 15.0
    
    # Current LST
    current_lst = calculate_lst(from_time, location)
    
    # Time until transit (in sidereal hours)
    hours_to_transit = ra_hours - current_lst
    if hours_to_transit < 0:
        hours_to_transit += 24.0  # Next day
    
    # Convert sidereal time to solar time (sidereal day = 23.9344696 hours)
    # 1 sidereal hour = 0.9972696 solar hours
    solar_hours_to_transit = hours_to_transit * 0.9972696
    
    transit_utc = from_time + timedelta(hours=solar_hours_to_transit)
    
    # Calculate elevation at transit
    elevation = calculate_elevation(ra_deg, dec_deg, transit_utc, location)
    
    # Determine status
    if hours_to_transit < 0.1:  # Within ~6 minutes
        status = "in_progress"
    elif hours_to_transit < 1.0:  # Within 1 hour
        status = "upcoming"
    else:
        status = "scheduled"
    
    return TransitPrediction(
        calibrator=calibrator,
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        transit_utc=transit_utc,
        time_to_transit_sec=solar_hours_to_transit * 3600,
        lst_at_transit=ra_hours,
        elevation_at_transit=elevation,
        status=status,
    )


def get_all_upcoming_transits(
    hours_ahead: float = 24.0,
    calibrators: Optional[Dict] = None,
    from_time: Optional[datetime] = None,
) -> List[TransitPrediction]:
    """
    Get all calibrator transits in the next N hours.
    
    Args:
        hours_ahead: How many hours to look ahead
        calibrators: Calibrator catalog (default: DEFAULT_CALIBRATORS)
        from_time: Start time (default: now)
        
    Returns:
        List of TransitPrediction sorted by transit time
    """
    if calibrators is None:
        calibrators = DEFAULT_CALIBRATORS
    if from_time is None:
        from_time = datetime.utcnow()
    
    predictions = []
    max_time = from_time + timedelta(hours=hours_ahead)
    
    for name in calibrators:
        pred = predict_calibrator_transit(name, from_time, calibrators)
        if pred and pred.transit_utc <= max_time:
            predictions.append(pred)
    
    return sorted(predictions, key=lambda p: p.transit_utc)


def get_active_calibrator(
    window_minutes: float = 5.0,
    calibrators: Optional[Dict] = None,
    at_time: Optional[datetime] = None,
) -> Optional[str]:
    """
    Get the calibrator currently transiting (within window).
    
    The DSA-110 observation window is ~5 minutes per field (309 seconds).
    
    Args:
        window_minutes: Transit window in minutes
        calibrators: Calibrator catalog
        at_time: Time to check (default: now)
        
    Returns:
        Calibrator name or None
    """
    if at_time is None:
        at_time = datetime.utcnow()
    
    # Check each calibrator's transit proximity
    for name in (calibrators or DEFAULT_CALIBRATORS):
        pred = predict_calibrator_transit(name, at_time, calibrators)
        if pred and abs(pred.time_to_transit_sec) < window_minutes * 60:
            return name
        # Also check if we're just past transit
        if pred and pred.time_to_transit_sec > 23 * 3600:
            # Wrapped around, check actual time since transit
            time_since = 24 * 3600 - pred.time_to_transit_sec
            if time_since < window_minutes * 60:
                return name
    
    return None


class PointingMonitor:
    """
    Long-running pointing monitor service.
    
    Monitors telescope pointing and tracks calibrator transits.
    Writes status to a JSON file for health check integration.
    """
    
    def __init__(
        self,
        status_file: Optional[Path] = None,
        update_interval_sec: float = 60.0,
        calibrators: Optional[Dict] = None,
    ):
        """
        Initialize the pointing monitor.
        
        Args:
            status_file: Path to write status JSON
            update_interval_sec: How often to update status
            calibrators: Calibrator catalog to track
        """
        self.status_file = status_file or DEFAULT_STATUS_FILE
        self.update_interval = update_interval_sec
        self.calibrators = calibrators or DEFAULT_CALIBRATORS
        
        self._running = False
        self._start_time: Optional[datetime] = None
        self._recent_transits: List[TransitPrediction] = []
        self._shutdown_event = asyncio.Event()
    
    def _write_status(self, status: PointingStatus) -> None:
        """Write status to JSON file."""
        try:
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.status_file, 'w') as f:
                json.dump(status.to_dict(), f, indent=2)
            
            logger.debug(f"Wrote status to {self.status_file}")
        except Exception as e:
            logger.error(f"Failed to write status file: {e}")
    
    def _update_recent_transits(
        self,
        predictions: List[TransitPrediction],
        max_age_hours: float = 6.0,
    ) -> None:
        """Update the recent transits list."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=max_age_hours)
        
        # Add completed transits
        for pred in predictions:
            if pred.status == "in_progress":
                # Check if this transit is completing
                pred_copy = TransitPrediction(
                    calibrator=pred.calibrator,
                    ra_deg=pred.ra_deg,
                    dec_deg=pred.dec_deg,
                    transit_utc=pred.transit_utc,
                    time_to_transit_sec=0,
                    lst_at_transit=pred.lst_at_transit,
                    elevation_at_transit=pred.elevation_at_transit,
                    status="completed",
                )
                # Avoid duplicates
                existing = [t for t in self._recent_transits 
                           if t.calibrator == pred.calibrator 
                           and abs((t.transit_utc - pred.transit_utc).total_seconds()) < 300]
                if not existing:
                    self._recent_transits.append(pred_copy)
        
        # Remove old transits
        self._recent_transits = [
            t for t in self._recent_transits
            if t.transit_utc > cutoff
        ]
    
    def get_status(self) -> PointingStatus:
        """Get current pointing status."""
        now = datetime.utcnow()
        
        # Calculate current LST
        current_lst = calculate_lst(now)
        
        # Get upcoming transits (next 24 hours)
        upcoming = get_all_upcoming_transits(hours_ahead=24.0, from_time=now)
        
        # Get active calibrator
        active = get_active_calibrator(at_time=now)
        
        # Update recent transits
        self._update_recent_transits(upcoming)
        
        # Calculate uptime
        uptime = 0.0
        if self._start_time:
            uptime = (now - self._start_time).total_seconds()
        
        return PointingStatus(
            current_lst=current_lst,
            current_utc=now.isoformat() + "Z",
            active_calibrator=active,
            upcoming_transits=upcoming[:5],  # Next 5 transits
            recent_transits=self._recent_transits[-5:],  # Last 5 completed
            monitor_healthy=self._running,
            last_update=now.isoformat() + "Z",
            uptime_sec=uptime,
        )
    
    async def run(self) -> None:
        """Run the pointing monitor loop."""
        self._running = True
        self._start_time = datetime.utcnow()
        
        logger.info(f"Starting pointing monitor, status file: {self.status_file}")
        logger.info(f"Tracking {len(self.calibrators)} calibrators")
        
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Get and write status
                    status = self.get_status()
                    self._write_status(status)
                    
                    # Log active calibrator
                    if status.active_calibrator:
                        logger.info(f"Active calibrator: {status.active_calibrator}")
                    
                    # Log upcoming transits
                    for pred in status.upcoming_transits[:2]:
                        if pred.time_to_transit_sec < 3600:  # Within 1 hour
                            logger.info(
                                f"Upcoming transit: {pred.calibrator} in "
                                f"{pred.time_to_transit_sec/60:.1f} min"
                            )
                    
                except Exception as e:
                    logger.error(f"Error in monitor loop: {e}", exc_info=True)
                
                # Wait for next update or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.update_interval,
                    )
                except asyncio.TimeoutError:
                    pass  # Normal timeout, continue loop
        
        finally:
            self._running = False
            logger.info("Pointing monitor stopped")
    
    def stop(self) -> None:
        """Signal the monitor to stop."""
        logger.info("Stopping pointing monitor...")
        self._shutdown_event.set()


async def run_monitor(
    status_file: Optional[Path] = None,
    update_interval: float = 60.0,
) -> None:
    """
    Run the pointing monitor with signal handling.
    
    Args:
        status_file: Path to status JSON file
        update_interval: Update interval in seconds
    """
    monitor = PointingMonitor(
        status_file=status_file,
        update_interval_sec=update_interval,
    )
    
    # Set up signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        monitor.stop()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    await monitor.run()


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="DSA-110 Pointing Monitor - Track calibrator transits"
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=DEFAULT_STATUS_FILE,
        help="Path to write status JSON",
    )
    parser.add_argument(
        "--update-interval",
        type=float,
        default=60.0,
        help="Update interval in seconds",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Log file path (default: stderr)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and print status (don't start daemon)",
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_config = {
        "level": getattr(logging, args.log_level),
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    }
    
    if args.log_file:
        log_config["filename"] = str(args.log_file)
        log_config["filemode"] = "a"
    
    logging.basicConfig(**log_config)
    
    if args.once:
        # Single status check
        monitor = PointingMonitor(status_file=args.status_file)
        status = monitor.get_status()
        print(json.dumps(status.to_dict(), indent=2))
        return
    
    # Run daemon
    try:
        asyncio.run(run_monitor(
            status_file=args.status_file,
            update_interval=args.update_interval,
        ))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    main()
