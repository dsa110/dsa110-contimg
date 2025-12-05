"""Maintenance tasks for ABSURD scheduler.

This module provides scheduled maintenance tasks that run via ABSURD:
- Database backups (hourly)
- Calibration table backups (daily)
- Storage reconciliation (daily)
- Health checks (hourly)
- Session cleanup (hourly)
- Data retention cleanup (daily)

These tasks replace the previous cron jobs and systemd timers, providing
a unified scheduling system with built-in retry, monitoring, and history.
"""

import gzip
import logging
import os
import shutil
import sqlite3
import subprocess
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from dsa110_contimg.absurd import AbsurdClient

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_BACKUP_ROOT = "/stage/backups"
DEFAULT_PIPELINE_DB = "/data/dsa110-contimg/state/db/pipeline.sqlite3"
DEFAULT_CALTABLES_DIR = "/products/caltables"
DEFAULT_INCOMING_DIR = "/data/incoming"
DEFAULT_HDF5_DB = "/data/dsa110-contimg/state/db/hdf5.sqlite3"

# Retention settings
HOURLY_RETENTION_DAYS = 7
DAILY_RETENTION_DAYS = 30


async def execute_backup_database(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute database backup task.

    Creates a compressed SQLite backup using the online backup API.

    Args:
        params: Task parameters:
            - backup_type: "hourly" or "daily" (default: "hourly")
            - backup_root: Root backup directory (default: /stage/backups)
            - pipeline_db: Path to pipeline database (default: env or standard path)

    Returns:
        Result dict with backup path, size, and retention info.
    """
    logger.info("[Maintenance] Starting database backup")

    try:
        inputs = params.get("inputs", {})
        backup_type = inputs.get("backup_type", "hourly")
        backup_root = Path(
            inputs.get("backup_root", os.environ.get("BACKUP_DIR", DEFAULT_BACKUP_ROOT))
        )
        pipeline_db = Path(
            inputs.get("pipeline_db", os.environ.get("PIPELINE_DB", DEFAULT_PIPELINE_DB))
        )

        # Determine backup directory and retention
        if backup_type == "daily":
            backup_dir = backup_root / "daily"
            retention_days = DAILY_RETENTION_DAYS
        else:
            backup_dir = backup_root / "hourly"
            retention_days = HOURLY_RETENTION_DAYS

        # Ensure directory exists
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"pipeline_{timestamp}.sqlite3"
        backup_file_gz = backup_file.with_suffix(".sqlite3.gz")

        # Perform backup using SQLite's online backup API
        if not pipeline_db.exists():
            return {
                "status": "error",
                "message": f"Pipeline database not found: {pipeline_db}",
                "errors": [f"Database file does not exist: {pipeline_db}"],
            }

        # Use subprocess to call sqlite3 .backup command (safest for concurrent access)
        result = subprocess.run(
            ["sqlite3", str(pipeline_db), f".backup '{backup_file}'"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "message": f"SQLite backup failed: {result.stderr}",
                "errors": [result.stderr],
            }

        # Compress the backup
        with open(backup_file, "rb") as f_in:
            with gzip.open(backup_file_gz, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remove uncompressed file
        backup_file.unlink()

        # Get compressed size
        backup_size = backup_file_gz.stat().st_size
        backup_size_mb = backup_size / (1024 * 1024)

        # Create latest symlink
        latest_link = backup_dir / "pipeline_latest.sqlite3.gz"
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(backup_file_gz.name)

        # Cleanup old backups
        cleaned = _cleanup_old_backups(backup_dir, "pipeline_*.sqlite3.gz", retention_days)

        logger.info(
            f"[Maintenance] Database backup complete: {backup_file_gz} "
            f"({backup_size_mb:.1f} MB), cleaned {cleaned} old backups"
        )

        return {
            "status": "success",
            "outputs": {
                "backup_path": str(backup_file_gz),
                "backup_size_bytes": backup_size,
                "backup_size_mb": round(backup_size_mb, 2),
                "backup_type": backup_type,
                "old_backups_cleaned": cleaned,
                "retention_days": retention_days,
            },
            "message": f"Database backup completed: {backup_file_gz.name} ({backup_size_mb:.1f} MB)",
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Database backup timed out after 5 minutes",
            "errors": ["Backup operation exceeded timeout"],
        }
    except Exception as e:
        logger.exception(f"[Maintenance] Database backup failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_backup_caltables(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute calibration tables backup task.

    Creates a compressed tar archive of the calibration tables directory.

    Args:
        params: Task parameters:
            - backup_root: Root backup directory (default: /stage/backups)
            - caltables_dir: Path to calibration tables (default: /products/caltables)

    Returns:
        Result dict with backup path, size, and file count.
    """
    logger.info("[Maintenance] Starting caltables backup")

    try:
        inputs = params.get("inputs", {})
        backup_root = Path(
            inputs.get("backup_root", os.environ.get("BACKUP_DIR", DEFAULT_BACKUP_ROOT))
        )
        caltables_dir = Path(
            inputs.get("caltables_dir", os.environ.get("CALTABLES_DIR", DEFAULT_CALTABLES_DIR))
        )

        backup_dir = backup_root / "daily"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename (daily - use date only)
        timestamp = datetime.now().strftime("%Y%m%d")
        backup_file = backup_dir / f"caltables_{timestamp}.tar.gz"

        if not caltables_dir.exists():
            logger.warning(f"[Maintenance] Caltables directory not found: {caltables_dir}")
            return {
                "status": "success",
                "outputs": {"skipped": True, "reason": "Caltables directory not found"},
                "message": f"Skipped: caltables directory {caltables_dir} does not exist",
            }

        # Count files before backup
        file_count = sum(1 for _ in caltables_dir.rglob("*") if _.is_file())

        # Create tar archive
        with tarfile.open(backup_file, "w:gz") as tar:
            tar.add(caltables_dir, arcname=caltables_dir.name)

        # Get backup size
        backup_size = backup_file.stat().st_size
        backup_size_mb = backup_size / (1024 * 1024)

        # Create latest symlink
        latest_link = backup_dir / "caltables_latest.tar.gz"
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(backup_file.name)

        # Cleanup old backups
        cleaned = _cleanup_old_backups(backup_dir, "caltables_*.tar.gz", DAILY_RETENTION_DAYS)

        logger.info(
            f"[Maintenance] Caltables backup complete: {backup_file} "
            f"({backup_size_mb:.1f} MB, {file_count} files), cleaned {cleaned} old backups"
        )

        return {
            "status": "success",
            "outputs": {
                "backup_path": str(backup_file),
                "backup_size_bytes": backup_size,
                "backup_size_mb": round(backup_size_mb, 2),
                "file_count": file_count,
                "old_backups_cleaned": cleaned,
            },
            "message": f"Caltables backup completed: {backup_file.name} ({backup_size_mb:.1f} MB, {file_count} files)",
        }

    except Exception as e:
        logger.exception(f"[Maintenance] Caltables backup failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_storage_reconciliation(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute storage reconciliation task.

    Validates HDF5 database against filesystem and optionally reconciles.

    Args:
        params: Task parameters:
            - do_reconcile: Whether to fix discrepancies (default: False)
            - sync_threshold: Alert threshold percentage (default: 95.0)
            - hdf5_db: Path to HDF5 database
            - incoming_dir: Path to incoming HDF5 files

    Returns:
        Result dict with sync metrics and reconciliation stats.
    """
    logger.info("[Maintenance] Starting storage reconciliation")

    try:
        inputs = params.get("inputs", {})
        do_reconcile = inputs.get("do_reconcile", False)
        sync_threshold = inputs.get("sync_threshold", 95.0)
        hdf5_db = Path(inputs.get("hdf5_db", os.environ.get("HDF5_DB", DEFAULT_HDF5_DB)))
        incoming_dir = Path(
            inputs.get("incoming_dir", os.environ.get("INCOMING_DIR", DEFAULT_INCOMING_DIR))
        )

        # Import storage validator
        try:
            from dsa110_contimg.database.storage_validator import (
                full_reconciliation,
                get_storage_metrics,
            )
        except ImportError:
            return {
                "status": "error",
                "message": "storage_validator module not available",
                "errors": ["Could not import storage_validator"],
            }

        # Get current metrics
        metrics = get_storage_metrics(str(hdf5_db), str(incoming_dir))

        # Calculate sync percentage
        if metrics.get("files_on_disk", 0) == 0:
            sync_pct = 100.0
        else:
            sync_pct = (metrics.get("files_in_db_stored", 0) / metrics["files_on_disk"]) * 100

        below_threshold = sync_pct < sync_threshold

        result_outputs = {
            "sync_percentage": round(sync_pct, 2),
            "sync_threshold": sync_threshold,
            "below_threshold": below_threshold,
            "metrics": metrics,
            "reconciled": False,
        }

        # Run reconciliation if requested
        if do_reconcile:
            recon_result = full_reconciliation(str(hdf5_db), str(incoming_dir))
            result_outputs["reconciled"] = True
            result_outputs["reconciliation_stats"] = recon_result

        status_msg = f"Storage sync: {sync_pct:.1f}%"
        if below_threshold:
            status_msg += f" (BELOW threshold {sync_threshold}%)"

        logger.info(f"[Maintenance] Storage reconciliation complete: {status_msg}")

        return {
            "status": "success",
            "outputs": result_outputs,
            "message": status_msg,
        }

    except Exception as e:
        logger.exception(f"[Maintenance] Storage reconciliation failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_health_check(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute system health check task.

    Checks API availability, database connectivity, disk space, and service status.

    Args:
        params: Task parameters:
            - api_url: API base URL (default: http://localhost:8000)
            - check_services: List of systemd services to check

    Returns:
        Result dict with health check results.
    """
    logger.info("[Maintenance] Starting health check")

    try:
        inputs = params.get("inputs", {})
        api_url = inputs.get("api_url", os.environ.get("API_URL", "http://localhost:8000"))
        check_services = inputs.get("check_services", ["contimg-api", "contimg-stream"])

        health_results = {
            "api_healthy": False,
            "database_healthy": False,
            "disk_space_ok": True,
            "services": {},
            "issues": [],
        }

        # Check API health
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_url}/health", timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    health_results["api_healthy"] = resp.status == 200
                    if resp.status != 200:
                        health_results["issues"].append(f"API returned status {resp.status}")
        except Exception as e:
            health_results["issues"].append(f"API unreachable: {e}")

        # Check database connectivity
        try:
            pipeline_db = os.environ.get("PIPELINE_DB", DEFAULT_PIPELINE_DB)
            conn = sqlite3.connect(pipeline_db, timeout=5)
            conn.execute("SELECT 1")
            conn.close()
            health_results["database_healthy"] = True
        except Exception as e:
            health_results["issues"].append(f"Database error: {e}")

        # Check disk space
        for mount in ["/data", "/stage"]:
            if os.path.exists(mount):
                stat = os.statvfs(mount)
                free_pct = (stat.f_bavail / stat.f_blocks) * 100
                if free_pct < 15:
                    health_results["disk_space_ok"] = False
                    health_results["issues"].append(f"{mount} has only {free_pct:.1f}% free")

        # Check systemd services
        for service in check_services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                is_active = result.stdout.strip() == "active"
                health_results["services"][service] = is_active
                if not is_active:
                    health_results["issues"].append(f"Service {service} is not active")
            except Exception as e:
                health_results["services"][service] = False
                health_results["issues"].append(f"Could not check {service}: {e}")

        # Overall health
        overall_healthy = (
            health_results["api_healthy"]
            and health_results["database_healthy"]
            and health_results["disk_space_ok"]
            and all(health_results["services"].values())
        )

        health_results["overall_healthy"] = overall_healthy

        status = (
            "healthy" if overall_healthy else f"unhealthy ({len(health_results['issues'])} issues)"
        )
        logger.info(f"[Maintenance] Health check complete: {status}")

        return {
            "status": "success",
            "outputs": health_results,
            "message": f"Health check: {status}",
        }

    except Exception as e:
        logger.exception(f"[Maintenance] Health check failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_session_cleanup(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute session cleanup task.

    Removes expired sessions from the database.

    Args:
        params: Task parameters:
            - max_age_hours: Maximum session age in hours (default: 24)

    Returns:
        Result dict with cleanup statistics.
    """
    logger.info("[Maintenance] Starting session cleanup")

    try:
        inputs = params.get("inputs", {})
        max_age_hours = inputs.get("max_age_hours", 24)

        pipeline_db = os.environ.get("PIPELINE_DB", DEFAULT_PIPELINE_DB)
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        cutoff_str = cutoff.isoformat()

        conn = sqlite3.connect(pipeline_db)
        cursor = conn.cursor()

        # Check if sessions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        if not cursor.fetchone():
            conn.close()
            return {
                "status": "success",
                "outputs": {"sessions_deleted": 0, "skipped": True},
                "message": "Sessions table does not exist, skipping cleanup",
            }

        # Delete expired sessions
        cursor.execute(
            "DELETE FROM sessions WHERE last_activity < ? OR expires_at < ?",
            (cutoff_str, datetime.utcnow().isoformat()),
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"[Maintenance] Session cleanup complete: {deleted} sessions deleted")

        return {
            "status": "success",
            "outputs": {"sessions_deleted": deleted, "max_age_hours": max_age_hours},
            "message": f"Cleaned up {deleted} expired sessions",
        }

    except Exception as e:
        logger.exception(f"[Maintenance] Session cleanup failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


async def execute_data_retention_cleanup(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute data retention cleanup task.

    Removes old data products according to retention policy.

    Args:
        params: Task parameters:
            - ms_retention_days: Days to keep MS files (default: 30)
            - image_retention_days: Days to keep images (default: 90)
            - dry_run: If True, only report what would be deleted

    Returns:
        Result dict with cleanup statistics.
    """
    logger.info("[Maintenance] Starting data retention cleanup")

    try:
        inputs = params.get("inputs", {})
        ms_retention_days = inputs.get("ms_retention_days", 30)
        image_retention_days = inputs.get("image_retention_days", 90)
        dry_run = inputs.get("dry_run", False)

        stats = {
            "ms_files_deleted": 0,
            "ms_bytes_freed": 0,
            "images_deleted": 0,
            "image_bytes_freed": 0,
            "dry_run": dry_run,
        }

        # MS files cleanup
        ms_dir = Path("/stage/dsa110-contimg/ms")
        if ms_dir.exists():
            ms_cutoff = datetime.now().timestamp() - (ms_retention_days * 86400)
            for ms_path in ms_dir.glob("*.ms"):
                if ms_path.stat().st_mtime < ms_cutoff:
                    size = sum(f.stat().st_size for f in ms_path.rglob("*") if f.is_file())
                    if not dry_run:
                        shutil.rmtree(ms_path)
                    stats["ms_files_deleted"] += 1
                    stats["ms_bytes_freed"] += size

        # Images cleanup
        images_dir = Path("/stage/dsa110-contimg/images")
        if images_dir.exists():
            image_cutoff = datetime.now().timestamp() - (image_retention_days * 86400)
            for img_path in images_dir.glob("*.fits"):
                if img_path.stat().st_mtime < image_cutoff:
                    size = img_path.stat().st_size
                    if not dry_run:
                        img_path.unlink()
                    stats["images_deleted"] += 1
                    stats["image_bytes_freed"] += size

        # Convert bytes to MB
        stats["ms_mb_freed"] = round(stats["ms_bytes_freed"] / (1024 * 1024), 2)
        stats["image_mb_freed"] = round(stats["image_bytes_freed"] / (1024 * 1024), 2)

        action = "Would delete" if dry_run else "Deleted"
        logger.info(
            f"[Maintenance] Data retention cleanup complete: {action} "
            f"{stats['ms_files_deleted']} MS files, {stats['images_deleted']} images"
        )

        return {
            "status": "success",
            "outputs": stats,
            "message": f"{action} {stats['ms_files_deleted']} MS files ({stats['ms_mb_freed']} MB), "
            f"{stats['images_deleted']} images ({stats['image_mb_freed']} MB)",
        }

    except Exception as e:
        logger.exception(f"[Maintenance] Data retention cleanup failed: {e}")
        return {"status": "error", "message": str(e), "errors": [str(e)]}


def _cleanup_old_backups(backup_dir: Path, pattern: str, retention_days: int) -> int:
    """Remove backup files older than retention period.

    Args:
        backup_dir: Directory containing backups
        pattern: Glob pattern for backup files
        retention_days: Days to keep backups

    Returns:
        Number of files deleted
    """
    import fnmatch

    cutoff = datetime.now().timestamp() - (retention_days * 86400)
    deleted = 0

    for path in backup_dir.iterdir():
        if fnmatch.fnmatch(path.name, pattern):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1

    return deleted


# Default schedule definitions for automatic registration
DEFAULT_SCHEDULES = [
    {
        "name": "hourly_database_backup",
        "task_name": "backup-database",
        "cron_expression": "0 * * * *",  # Every hour at :00
        "params": {"inputs": {"backup_type": "hourly"}},
        "description": "Hourly SQLite database backup with 7-day retention",
        "queue_name": "maintenance",
    },
    {
        "name": "daily_database_backup",
        "task_name": "backup-database",
        "cron_expression": "0 3 * * *",  # 3:00 AM daily
        "params": {"inputs": {"backup_type": "daily"}},
        "description": "Daily SQLite database backup with 30-day retention",
        "queue_name": "maintenance",
    },
    {
        "name": "daily_caltables_backup",
        "task_name": "backup-caltables",
        "cron_expression": "0 3 * * *",  # 3:00 AM daily
        "params": {},
        "description": "Daily calibration tables backup",
        "queue_name": "maintenance",
    },
    {
        "name": "daily_storage_reconciliation",
        "task_name": "storage-reconciliation",
        "cron_expression": "0 2 * * *",  # 2:00 AM daily
        "params": {"inputs": {"do_reconcile": False, "sync_threshold": 95.0}},
        "description": "Daily storage validation and sync check",
        "queue_name": "maintenance",
    },
    {
        "name": "hourly_health_check",
        "task_name": "health-check",
        "cron_expression": "15 * * * *",  # Every hour at :15
        "params": {},
        "description": "Hourly system health check",
        "queue_name": "maintenance",
    },
    {
        "name": "hourly_session_cleanup",
        "task_name": "session-cleanup",
        "cron_expression": "30 * * * *",  # Every hour at :30
        "params": {"inputs": {"max_age_hours": 24}},
        "description": "Hourly expired session cleanup",
        "queue_name": "maintenance",
    },
    {
        "name": "daily_data_retention_cleanup",
        "task_name": "data-retention-cleanup",
        "cron_expression": "0 4 * * *",  # 4:00 AM daily
        "params": {"inputs": {"ms_retention_days": 30, "image_retention_days": 90}},
        "description": "Daily old data cleanup according to retention policy",
        "queue_name": "maintenance",
    },
]


async def setup_default_schedules(client: "AbsurdClient") -> Dict[str, Any]:
    """Register default maintenance schedules with ABSURD.

    This function should be called during application startup to ensure
    all maintenance tasks are scheduled.

    Args:
        client: AbsurdClient instance

    Returns:
        Dict with registration results
    """
    results = {"registered": [], "skipped": [], "errors": []}

    for schedule in DEFAULT_SCHEDULES:
        try:
            # Check if schedule already exists
            existing = await client.get_schedule(schedule["name"])
            if existing:
                results["skipped"].append(schedule["name"])
                continue

            # Create schedule
            await client.create_schedule(
                name=schedule["name"],
                queue_name=schedule["queue_name"],
                task_name=schedule["task_name"],
                cron_expression=schedule["cron_expression"],
                params=schedule.get("params", {}),
                description=schedule.get("description"),
            )
            results["registered"].append(schedule["name"])

        except Exception as e:
            logger.error(f"Failed to register schedule {schedule['name']}: {e}")
            results["errors"].append({"name": schedule["name"], "error": str(e)})

    logger.info(
        f"[Maintenance] Schedule setup complete: "
        f"{len(results['registered'])} registered, "
        f"{len(results['skipped'])} skipped, "
        f"{len(results['errors'])} errors"
    )

    return results
