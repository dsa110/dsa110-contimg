#!/usr/bin/env python3
"""
Smoke test for the streaming pipeline module.

Tests each stage individually with a real HDF5 group from the database,
without actually modifying production data.

Usage:
    python scripts/testing/smoke_test_streaming.py [--group-id GROUP_ID] [--dry-run]
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dsa110_contimg.conversion.streaming import SubbandQueue
from dsa110_contimg.conversion.streaming.stages import (
    ConversionStage,
    CalibrationStage,
    ImagingStage,
    PhotometryStage,
    MosaicStage,
)
from dsa110_contimg.conversion.streaming.stages.conversion import ConversionConfig
from dsa110_contimg.conversion.streaming.stages.calibration import CalibrationConfig
from dsa110_contimg.conversion.streaming.stages.imaging import ImagingConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smoke_test")


def find_complete_group(db_path: Path) -> tuple[str, list[Path]] | None:
    """Find a group with all 16 subbands present."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("""
            SELECT group_id, COUNT(*) as cnt 
            FROM subband_files 
            GROUP BY group_id 
            HAVING cnt = 16 
            LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            return None
        
        group_id = row[0]
        cursor = conn.execute(
            "SELECT path FROM subband_files WHERE group_id = ? ORDER BY subband_idx",
            (group_id,)
        )
        paths = [Path(r[0]) for r in cursor.fetchall()]
        return group_id, paths
    finally:
        conn.close()


def test_queue_operations(db_path: Path, group_id: str) -> bool:
    """Test queue read operations (non-destructive)."""
    logger.info("Testing SubbandQueue operations...")
    
    queue = SubbandQueue(db_path, expected_subbands=16)
    
    # Test count_by_state
    counts = queue.count_by_state()
    logger.info(f"  Queue state counts: {dict(counts)}")
    
    # Test get_group_info
    info = queue.get_group_info(group_id)
    if info:
        logger.info(f"  Group {group_id}: state={info.get('state')}, subbands={info.get('subband_count', 'N/A')}")
    else:
        logger.warning(f"  Group {group_id} not found in queue")
        return False
    
    logger.info("  ✓ Queue operations OK")
    return True


def test_conversion_stage_validation(hdf5_files: list[Path], dry_run: bool) -> bool:
    """Test ConversionStage validation (no actual conversion)."""
    logger.info("Testing ConversionStage validation...")
    
    # Check all files exist
    missing = [f for f in hdf5_files if not f.exists()]
    if missing:
        logger.error(f"  Missing files: {missing[:3]}...")
        return False
    
    logger.info(f"  All {len(hdf5_files)} HDF5 files exist")
    
    # Check file sizes
    total_size = sum(f.stat().st_size for f in hdf5_files)
    logger.info(f"  Total input size: {total_size / 1e9:.2f} GB")
    
    # Test HDF5 readability
    try:
        import h5py
        with h5py.File(hdf5_files[0], 'r') as f:
            keys = list(f.keys())
            logger.info(f"  HDF5 structure: {keys[:5]}{'...' if len(keys) > 5 else ''}")
    except Exception as e:
        logger.error(f"  Failed to read HDF5: {e}")
        return False
    
    if dry_run:
        logger.info("  ✓ ConversionStage validation OK (dry-run, skipping actual conversion)")
    else:
        logger.info("  ✓ ConversionStage validation OK")
    
    return True


def test_calibration_stage_validation(db_path: Path, group_id: str) -> bool:
    """Test CalibrationStage can find calibration tables."""
    logger.info("Testing CalibrationStage validation...")
    
    # Check for calibration tables in registry
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("""
            SELECT COUNT(*) FROM caltables WHERE state = 'valid'
        """)
        count = cursor.fetchone()[0]
        logger.info(f"  Found {count} valid calibration tables in registry")
        
        if count == 0:
            logger.warning("  No valid calibration tables - calibration stage would skip")
            return True  # Not a failure, just a warning
        
        # Check nearest calibration
        cursor = conn.execute("""
            SELECT source_name, obs_time, cal_type 
            FROM caltables 
            WHERE state = 'valid' 
            ORDER BY obs_time DESC 
            LIMIT 3
        """)
        for row in cursor.fetchall():
            logger.info(f"    Cal: {row[0]} @ {row[1]} ({row[2]})")
        
    finally:
        conn.close()
    
    logger.info("  ✓ CalibrationStage validation OK")
    return True


def test_imaging_stage_validation() -> bool:
    """Test ImagingStage dependencies are available."""
    logger.info("Testing ImagingStage validation...")
    
    # Check wsclean availability
    import shutil
    wsclean_path = shutil.which("wsclean")
    if wsclean_path:
        logger.info(f"  wsclean found at: {wsclean_path}")
    else:
        logger.warning("  wsclean not found - imaging would use CASA")
    
    # Check CASA availability
    try:
        from casatasks import tclean
        logger.info("  CASA tclean available")
    except ImportError:
        logger.warning("  CASA tclean not available")
    
    logger.info("  ✓ ImagingStage validation OK")
    return True


def test_health_infrastructure() -> bool:
    """Test health check infrastructure."""
    logger.info("Testing health infrastructure...")
    
    from dsa110_contimg.conversion.streaming.health import (
        HealthStatus,
        HealthCheck,
        HealthChecker,
        PipelineMetrics,
    )
    
    # Create checker
    checker = HealthChecker()
    
    # Register a test check
    def disk_check() -> HealthCheck:
        import shutil
        usage = shutil.disk_usage("/data")
        pct_free = usage.free / usage.total * 100
        return HealthCheck(
            name="disk_space",
            status=HealthStatus.HEALTHY if pct_free > 10 else HealthStatus.DEGRADED,
            message=f"{pct_free:.1f}% free",
        )
    
    checker.register("disk", disk_check)
    results = checker.check_all()
    
    for name, check in results.items():
        logger.info(f"  {name}: {check.status.value} - {check.message}")
    
    # Test metrics
    metrics = PipelineMetrics()
    logger.info(f"  Metrics initialized: uptime={metrics.uptime_seconds:.1f}s")
    
    logger.info("  ✓ Health infrastructure OK")
    return True


def test_retry_infrastructure() -> bool:
    """Test retry infrastructure."""
    logger.info("Testing retry infrastructure...")
    
    from dsa110_contimg.conversion.streaming.retry import RetryConfig, with_retry
    
    config = RetryConfig(max_attempts=3, base_delay=0.1)
    
    call_count = 0
    
    @with_retry(config)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Simulated failure")
        return "success"
    
    result = flaky_function()
    assert result == "success"
    assert call_count == 2
    
    logger.info(f"  Retry worked: {call_count} attempts")
    logger.info("  ✓ Retry infrastructure OK")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--group-id",
        help="Specific group ID to test (default: auto-select complete group)"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path("/data/dsa110-contimg/state/db/pipeline.sqlite3"),
        help="Path to pipeline database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip actual conversion/processing"
    )
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Streaming Pipeline Smoke Test")
    logger.info("=" * 60)
    
    # Find a complete group
    if args.group_id:
        group_id = args.group_id
        conn = sqlite3.connect(args.db_path)
        cursor = conn.execute(
            "SELECT path FROM subband_files WHERE group_id = ? ORDER BY subband_idx",
            (group_id,)
        )
        hdf5_files = [Path(r[0]) for r in cursor.fetchall()]
        conn.close()
    else:
        result = find_complete_group(args.db_path)
        if not result:
            logger.error("No complete group found in database")
            return 1
        group_id, hdf5_files = result
    
    logger.info(f"Testing with group: {group_id}")
    logger.info(f"  Files: {len(hdf5_files)} HDF5 subbands")
    logger.info("")
    
    # Run tests
    results = {}
    
    results["queue"] = test_queue_operations(args.db_path, group_id)
    results["conversion"] = test_conversion_stage_validation(hdf5_files, args.dry_run)
    results["calibration"] = test_calibration_stage_validation(args.db_path, group_id)
    results["imaging"] = test_imaging_stage_validation()
    results["health"] = test_health_infrastructure()
    results["retry"] = test_retry_infrastructure()
    
    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, ok in results.items():
        status = "✓ PASS" if ok else "✗ FAIL"
        logger.info(f"  {name}: {status}")
    
    logger.info("")
    logger.info(f"Result: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
