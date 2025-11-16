#!/opt/miniforge/envs/casa6/bin/python
"""Create 10-minute mosaic with specified parameters.

Parameters:
- Calibrator: 0834+555
- Output: default (/stage/dsa110-contimg/mosaics/)
- Mosaic name: default (auto-generated)
- Method: pbweighted (default in orchestrator)
- Imaging: imsize=1024, robust=0, niter=1000
- Tile selection: default
- Validation: automatic
- Publishing: wait_for_published=False (stays in /stage/)
"""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

# Error log file location
ERROR_LOG = Path("/data/dsa110-contimg/src/mosaic_errors.log")
STATUS_FILE = Path("/data/dsa110-contimg/src/mosaic_status.txt")

def log_error(message, exception=None):
    """Log error to file with timestamp."""
    timestamp = datetime.now().isoformat()
    with open(ERROR_LOG, 'a') as f:
        f.write(f"[{timestamp}] ERROR: {message}\n")
        if exception:
            f.write(f"Exception: {str(exception)}\n")
            f.write(f"Traceback:\n{traceback.format_exc()}\n")
        f.write("-" * 80 + "\n")
    print(f"ERROR: {message}", file=sys.stderr)
    if exception:
        print(traceback.format_exc(), file=sys.stderr)

def write_status(status, details=""):
    """Write status to file for monitoring."""
    timestamp = datetime.now().isoformat()
    with open(STATUS_FILE, 'w') as f:
        f.write(f"Status: {status}\n")
        f.write(f"Timestamp: {timestamp}\n")
        if details:
            f.write(f"Details: {details}\n")

def main():
    """Main execution with error handling."""
    try:
        write_status("RUNNING", "Starting mosaic creation")
        
        # Set imaging parameters (applies to individual tiles)
        # Note: These are already the defaults, but setting explicitly for clarity
        os.environ['IMG_IMSIZE'] = '1024'
        os.environ['IMG_ROBUST'] = '0.0'
        os.environ['IMG_NITER'] = '1000'

        # Ensure output stays in /stage/ (default location)
        # Default is already /stage/dsa110-contimg/mosaics/ unless CONTIMG_MOSAIC_DIR is set

        # Initialize orchestrator
        write_status("RUNNING", "Initializing orchestrator")
        orchestrator = MosaicOrchestrator(
            products_db_path=Path("state/products.sqlite3")
        )

        # Create 10-minute mosaic centered on calibrator 0834+555
        # Note: Method is pbweighted by default (uses _build_weighted_mosaic)
        # Note: Validation happens automatically but can be bypassed if needed
        # Note: wait_for_published=False means it won't wait for publishing step
        # Note: dry_run=True to validate plan without building
        write_status("RUNNING", "Creating mosaic (dry run)")
        mosaic_path = orchestrator.create_mosaic_centered_on_calibrator(
            calibrator_name="0834+555",
            timespan_minutes=10,  # 10 minutes = 2 MS files (5 min each)
            wait_for_published=False,  # Don't wait for publishing, keep in /stage/
            dry_run=True  # Dry run: validate plan without building
        )

        if mosaic_path:
            if mosaic_path == "DRY_RUN":
                success_msg = "Dry run completed successfully - mosaic plan validated"
                print(f"✓ {success_msg}")
                print(f"  Run with dry_run=False to create the mosaic")
                write_status("SUCCESS", success_msg)
                return 0
            else:
                success_msg = f"Mosaic created successfully at: {mosaic_path}"
                print(f"✓ {success_msg}")
                print(f"  Location: /stage/dsa110-contimg/mosaics/")
                print(f"  Method: pbweighted (default)")
                print(f"  Validation: Automatic (no --ignore-validation needed in API)")
                write_status("SUCCESS", success_msg)
                return 0
        else:
            error_msg = "Failed to create mosaic (returned None)"
            log_error(error_msg)
            write_status("FAILED", error_msg)
            return 1

    except KeyboardInterrupt:
        error_msg = "Script interrupted by user"
        log_error(error_msg)
        write_status("INTERRUPTED", error_msg)
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        error_msg = f"Unexpected error during mosaic creation: {str(e)}"
        log_error(error_msg, e)
        write_status("FAILED", error_msg)
        return 1

if __name__ == "__main__":
    sys.exit(main())
