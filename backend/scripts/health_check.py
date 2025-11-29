#!/usr/bin/env python3
"""
Health Check Utility for DSA-110 Continuum Imaging Pipeline.

Performs comprehensive health checks on all pipeline components:
- Database connectivity and schema
- Disk space on data directories
- Service endpoints (API, Redis, Prometheus)
- File permissions
- Stale lock files
- Worker processes

Usage:
    python health_check.py              # Run all checks
    python health_check.py --json       # Output as JSON
    python health_check.py --component db  # Check only databases
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """Result of a health check."""
    component: str
    name: str
    status: str  # "ok", "warning", "error"
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


def check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a port is listening."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_database(db_name: str, db_path: Path) -> HealthCheck:
    """Check database health."""
    if not db_path.exists():
        return HealthCheck(
            component="database",
            name=db_name,
            status="warning",
            message=f"Database not found: {db_path}",
        )
    
    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.execute("PRAGMA busy_timeout=5000")
        
        # Check integrity
        result = conn.execute("PRAGMA quick_check").fetchone()[0]
        if result != "ok":
            conn.close()
            return HealthCheck(
                component="database",
                name=db_name,
                status="error",
                message=f"Integrity check failed: {result}",
            )
        
        # Get size and table count
        size_mb = db_path.stat().st_size / (1024 * 1024)
        tables = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        
        conn.close()
        
        return HealthCheck(
            component="database",
            name=db_name,
            status="ok",
            message=f"Healthy ({size_mb:.1f} MB, {tables} tables)",
            details={"path": str(db_path), "size_mb": size_mb, "tables": tables},
        )
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            return HealthCheck(
                component="database",
                name=db_name,
                status="error",
                message=f"Database locked: {e}",
            )
        return HealthCheck(
            component="database",
            name=db_name,
            status="error",
            message=f"Connection error: {e}",
        )


def check_disk_space(path: Path, warn_gb: float = 10.0, error_gb: float = 1.0) -> HealthCheck:
    """Check disk space."""
    name = str(path)
    
    if not path.exists():
        return HealthCheck(
            component="disk",
            name=name,
            status="warning",
            message=f"Path does not exist: {path}",
        )
    
    try:
        usage = shutil.disk_usage(path)
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        percent_used = (usage.used / usage.total) * 100
        
        if free_gb < error_gb:
            status = "error"
            message = f"Critical: {free_gb:.1f} GB free ({percent_used:.0f}% used)"
        elif free_gb < warn_gb:
            status = "warning"
            message = f"Low space: {free_gb:.1f} GB free ({percent_used:.0f}% used)"
        else:
            status = "ok"
            message = f"{free_gb:.1f} GB free ({percent_used:.0f}% used)"
        
        return HealthCheck(
            component="disk",
            name=name,
            status=status,
            message=message,
            details={"free_gb": free_gb, "total_gb": total_gb, "percent_used": percent_used},
        )
    except OSError as e:
        return HealthCheck(
            component="disk",
            name=name,
            status="error",
            message=f"Error checking disk: {e}",
        )


def check_service(name: str, host: str, port: int) -> HealthCheck:
    """Check if a service is running."""
    if check_port(host, port):
        return HealthCheck(
            component="service",
            name=name,
            status="ok",
            message=f"Listening on {host}:{port}",
            details={"host": host, "port": port},
        )
    else:
        return HealthCheck(
            component="service",
            name=name,
            status="error",
            message=f"Not responding on {host}:{port}",
            details={"host": host, "port": port},
        )


def check_directory_permissions(path: Path, need_write: bool = True) -> HealthCheck:
    """Check directory exists and has correct permissions."""
    name = str(path)
    
    if not path.exists():
        return HealthCheck(
            component="filesystem",
            name=name,
            status="warning",
            message="Directory does not exist",
        )
    
    if not path.is_dir():
        return HealthCheck(
            component="filesystem",
            name=name,
            status="error",
            message="Path exists but is not a directory",
        )
    
    readable = os.access(path, os.R_OK)
    writable = os.access(path, os.W_OK) if need_write else True
    
    if readable and writable:
        return HealthCheck(
            component="filesystem",
            name=name,
            status="ok",
            message="Readable and writable",
        )
    elif readable and not need_write:
        return HealthCheck(
            component="filesystem",
            name=name,
            status="ok",
            message="Readable",
        )
    elif readable:
        return HealthCheck(
            component="filesystem",
            name=name,
            status="error",
            message="Not writable (permission denied)",
        )
    else:
        return HealthCheck(
            component="filesystem",
            name=name,
            status="error",
            message="Not readable (permission denied)",
        )


def check_stale_locks(state_dir: Path) -> HealthCheck:
    """Check for stale lock files."""
    lock_files = list(state_dir.glob("*.lock"))
    stale_locks = []
    
    for lock_file in lock_files:
        try:
            with open(lock_file, "r") as f:
                content = f.read().strip()
            
            if content.isdigit():
                pid = int(content)
                try:
                    os.kill(pid, 0)
                except OSError:
                    # Process doesn't exist - stale lock
                    stale_locks.append(str(lock_file))
        except Exception:
            stale_locks.append(str(lock_file))
    
    if stale_locks:
        return HealthCheck(
            component="locks",
            name="stale_locks",
            status="warning",
            message=f"{len(stale_locks)} stale lock files found",
            details={"stale_locks": stale_locks},
        )
    elif lock_files:
        return HealthCheck(
            component="locks",
            name="lock_files",
            status="ok",
            message=f"{len(lock_files)} active lock files",
        )
    else:
        return HealthCheck(
            component="locks",
            name="lock_files",
            status="ok",
            message="No lock files",
        )


def check_systemd_service(service_name: str) -> HealthCheck:
    """Check if a systemd service is running."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        status_text = result.stdout.strip()
        if status_text == "active":
            return HealthCheck(
                component="systemd",
                name=service_name,
                status="ok",
                message="Service is active",
            )
        elif status_text == "inactive":
            return HealthCheck(
                component="systemd",
                name=service_name,
                status="warning",
                message="Service is inactive",
            )
        else:
            return HealthCheck(
                component="systemd",
                name=service_name,
                status="error",
                message=f"Service status: {status_text}",
            )
    except subprocess.TimeoutExpired:
        return HealthCheck(
            component="systemd",
            name=service_name,
            status="error",
            message="Timeout checking service status",
        )
    except FileNotFoundError:
        return HealthCheck(
            component="systemd",
            name=service_name,
            status="warning",
            message="systemctl not available",
        )
    except Exception as e:
        return HealthCheck(
            component="systemd",
            name=service_name,
            status="error",
            message=f"Error checking service: {e}",
        )


def run_all_checks() -> List[HealthCheck]:
    """Run all health checks."""
    results = []
    
    # Database checks
    db_paths = {
        "products": Path("/data/dsa110-contimg/state/products.sqlite3"),
        "cal_registry": Path("/data/dsa110-contimg/state/cal_registry.sqlite3"),
        "hdf5": Path("/data/dsa110-contimg/state/hdf5_index.sqlite3"),
        "ingest": Path("/data/dsa110-contimg/state/ingest.sqlite3"),
        "data_registry": Path("/data/dsa110-contimg/state/data_registry.sqlite3"),
    }
    
    for name, path in db_paths.items():
        # Check environment override
        env_map = {
            "products": "PIPELINE_PRODUCTS_DB",
            "cal_registry": "PIPELINE_CAL_REGISTRY_DB",
            "hdf5": "PIPELINE_HDF5_DB",
            "ingest": "PIPELINE_INGEST_DB",
            "data_registry": "PIPELINE_DATA_REGISTRY_DB",
        }
        if env_map.get(name) and os.environ.get(env_map[name]):
            path = Path(os.environ[env_map[name]])
        results.append(check_database(name, path))
    
    # Disk space checks
    disk_paths = [
        Path("/data/dsa110-contimg/state"),
        Path("/data/dsa110-contimg/ms"),
        Path("/stage/dsa110-contimg"),
        Path("/tmp"),
    ]
    for path in disk_paths:
        results.append(check_disk_space(path))
    
    # Service checks
    services = [
        ("api", "localhost", 8000),
        ("redis", "localhost", 6379),
        ("prometheus", "localhost", 9090),
        ("grafana", "localhost", 3030),
    ]
    for name, host, port in services:
        results.append(check_service(name, host, port))
    
    # Directory permission checks
    directories = [
        Path("/data/dsa110-contimg/state"),
        Path("/data/dsa110-contimg/ms"),
        Path("/stage/dsa110-contimg"),
    ]
    for path in directories:
        results.append(check_directory_permissions(path))
    
    # Stale lock check
    results.append(check_stale_locks(Path("/data/dsa110-contimg/state")))
    
    # Systemd service checks
    systemd_services = [
        "dsa110-api.service",
        "redis-server.service",
        "prometheus.service",
    ]
    for service in systemd_services:
        results.append(check_systemd_service(service))
    
    return results


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Health check utility for DSA-110 pipeline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--component",
        choices=["db", "disk", "service", "filesystem", "locks", "systemd", "all"],
        default="all",
        help="Component to check",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only show errors and warnings",
    )
    
    args = parser.parse_args(argv)
    
    results = run_all_checks()
    
    # Filter by component
    if args.component != "all":
        component_map = {
            "db": "database",
            "disk": "disk",
            "service": "service",
            "filesystem": "filesystem",
            "locks": "locks",
            "systemd": "systemd",
        }
        filter_component = component_map.get(args.component, args.component)
        results = [r for r in results if r.component == filter_component]
    
    # Filter by status if quiet
    if args.quiet:
        results = [r for r in results if r.status != "ok"]
    
    # Output
    if args.json:
        output = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": [asdict(r) for r in results],
            "summary": {
                "total": len(results),
                "ok": sum(1 for r in results if r.status == "ok"),
                "warnings": sum(1 for r in results if r.status == "warning"),
                "errors": sum(1 for r in results if r.status == "error"),
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print("\n" + "=" * 60)
        print("DSA-110 PIPELINE HEALTH CHECK")
        print("=" * 60)
        print(f"Timestamp: {datetime.utcnow().isoformat()}Z\n")
        
        # Group by component
        components = {}
        for r in results:
            if r.component not in components:
                components[r.component] = []
            components[r.component].append(r)
        
        status_icons = {"ok": ":check:", "warning": ":warning:", "error": ":cross:"}
        
        for component, checks in components.items():
            print(f"\n{component.upper()}")
            print("-" * 40)
            for check in checks:
                icon = status_icons.get(check.status, ":question:")
                print(f"  {icon} {check.name}: {check.message}")
        
        # Summary
        errors = sum(1 for r in results if r.status == "error")
        warnings = sum(1 for r in results if r.status == "warning")
        ok = sum(1 for r in results if r.status == "ok")
        
        print("\n" + "=" * 60)
        if errors:
            print(f":cross: {errors} errors, {warnings} warnings, {ok} ok")
            return 1
        elif warnings:
            print(f":warning:  {warnings} warnings, {ok} ok")
            return 0
        else:
            print(f":check: All {ok} checks passed")
            return 0


if __name__ == "__main__":
    sys.exit(main())
