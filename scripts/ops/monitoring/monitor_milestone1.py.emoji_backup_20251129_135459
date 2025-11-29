#!/opt/miniforge/envs/casa6/bin/python
"""
Monitor milestone1_pipeline.py progress.

Usage:
    python scripts/monitor_milestone1.py [--watch] [--interval 60]
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

PROGRESS_FILE = Path("/tmp/milestone1_progress.json")
HEARTBEAT_TIMEOUT = 600  # 10 minutes - if no heartbeat for this long, process may be stuck


def load_progress() -> dict:
    """Load progress file."""
    if not PROGRESS_FILE.exists():
        return {"error": "Progress file not found"}
    
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Failed to load progress: {e}"}


def check_heartbeat(progress: dict) -> tuple[bool, str]:
    """Check if heartbeat is recent."""
    if "error" in progress:
        return False, progress["error"]
    
    last_heartbeat = progress.get("last_heartbeat")
    if not last_heartbeat:
        return False, "No heartbeat recorded"
    
    try:
        heartbeat_time = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
        if heartbeat_time.tzinfo is None:
            heartbeat_time = heartbeat_time.replace(tzinfo=None)
            now = datetime.utcnow()
        else:
            now = datetime.now(heartbeat_time.tzinfo)
        
        elapsed = (now - heartbeat_time).total_seconds()
        
        if elapsed > HEARTBEAT_TIMEOUT:
            return False, f"Heartbeat stale: {elapsed:.0f}s ago (timeout: {HEARTBEAT_TIMEOUT}s)"
        
        return True, f"Heartbeat OK: {elapsed:.0f}s ago"
    except Exception as e:
        return False, f"Failed to parse heartbeat: {e}"


def print_status(progress: dict):
    """Print current status."""
    if "error" in progress:
        print(f"ERROR: {progress['error']}")
        return
    
    print("="*80)
    print("MILESTONE 1 PROGRESS")
    print("="*80)
    
    # Basic info
    if "start_time" in progress:
        start = progress["start_time"]
        print(f"Started: {start}")
    
    if "last_heartbeat" in progress:
        print(f"Last heartbeat: {progress['last_heartbeat']}")
    
    # Current stage
    stage = progress.get("current_stage", "unknown")
    print(f"\nCurrent stage: {stage}")
    
    # MS processing progress
    if "total_ms" in progress:
        total = progress["total_ms"]
        completed = progress.get("completed_ms", 0)
        failed = progress.get("failed_ms", 0)
        current_idx = progress.get("ms_index", 0)
        
        print(f"\nMS Processing:")
        print(f"  Total MS files: {total}")
        print(f"  Completed: {completed}")
        print(f"  Failed: {failed}")
        print(f"  Current: {current_idx}/{total}")
        
        if current_idx > 0:
            pct = (completed / total) * 100
            print(f"  Progress: {pct:.1f}%")
    
    if "current_ms" in progress:
        print(f"\nCurrent MS: {progress['current_ms']}")
    
    # Stage timing
    if "stage_start_time" in progress:
        elapsed = time.time() - progress["stage_start_time"]
        print(f"\nStage runtime: {elapsed:.0f}s")
    
    # Errors
    errors = progress.get("errors", [])
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for i, err in enumerate(errors[-5:], 1):  # Show last 5 errors
            print(f"  {i}. {err.get('stage', 'unknown')}: {err.get('error', 'unknown')}")
    
    # Heartbeat check
    is_ok, msg = check_heartbeat(progress)
    print(f"\nHeartbeat: {':check:' if is_ok else ':cross:'} {msg}")
    
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description="Monitor milestone1_pipeline.py progress")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch mode: continuously monitor progress"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Update interval in seconds (default: 60)"
    )
    
    args = parser.parse_args()
    
    if args.watch:
        print("Watching progress (Ctrl+C to stop)...")
        try:
            while True:
                progress = load_progress()
                print_status(progress)
                print(f"\nNext update in {args.interval}s...\n")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        progress = load_progress()
        print_status(progress)
        
        # Exit with error if heartbeat is stale
        is_ok, _ = check_heartbeat(progress)
        sys.exit(0 if is_ok else 1)


if __name__ == "__main__":
    main()

