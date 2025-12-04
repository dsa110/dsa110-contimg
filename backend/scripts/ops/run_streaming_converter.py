#!/usr/bin/env python3
"""
Streaming Converter Runner - Elegant Python-based file watcher for /data/incoming/

This script provides a simple way to run the streaming converter without systemd.
It can be run directly, via screen/tmux, or as a background process.

Usage:
    # Run in foreground (Ctrl+C to stop)
    python scripts/ops/run_streaming_converter.py

    # Run in background with nohup
    nohup python scripts/ops/run_streaming_converter.py &

    # Run in screen session
    screen -S stream -dm python scripts/ops/run_streaming_converter.py

    # Run in tmux session  
    tmux new-session -d -s stream 'python scripts/ops/run_streaming_converter.py'

Configuration:
    Edit the constants below or use environment variables.
"""

import os
import sys
import signal
import logging
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# =============================================================================
# CONFIGURATION (edit these or use environment variables)
# =============================================================================

INPUT_DIR = os.getenv("CONTIMG_INPUT_DIR", "/data/incoming")
OUTPUT_DIR = os.getenv("CONTIMG_OUTPUT_DIR", "/data/dsa110-contimg/ms")
QUEUE_DB = os.getenv("CONTIMG_QUEUE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
REGISTRY_DB = os.getenv("CONTIMG_REGISTRY_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
SCRATCH_DIR = os.getenv("CONTIMG_SCRATCH_DIR", "/stage/dsa110-contimg")
LOG_LEVEL = os.getenv("CONTIMG_LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("CONTIMG_LOG_FILE", "/data/dsa110-contimg/state/logs/streaming-converter.log")

# Processing options
EXPECTED_SUBBANDS = int(os.getenv("CONTIMG_EXPECTED_SUBBANDS", "16"))
CHUNK_DURATION_MINUTES = float(os.getenv("CONTIMG_CHUNK_MINUTES", "5.0"))
POLL_INTERVAL = float(os.getenv("CONTIMG_POLL_INTERVAL", "5.0"))
MONITOR_INTERVAL = float(os.getenv("CONTIMG_MONITOR_INTERVAL", "60.0"))
MAX_WORKERS = int(os.getenv("CONTIMG_MAX_WORKERS", "4"))

# Feature flags
ENABLE_MONITORING = os.getenv("CONTIMG_ENABLE_MONITORING", "true").lower() == "true"
ENABLE_CALIBRATION = os.getenv("CONTIMG_ENABLE_CALIBRATION", "false").lower() == "true"
ENABLE_IMAGING = os.getenv("CONTIMG_ENABLE_IMAGING", "false").lower() == "true"

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging to both file and console."""
    log_dir = Path(LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the streaming converter."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("DSA-110 Streaming Converter")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info(f"Input directory: {INPUT_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Queue database: {QUEUE_DB}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("")
    
    # Validate paths
    if not Path(INPUT_DIR).exists():
        logger.error(f"Input directory does not exist: {INPUT_DIR}")
        return 1
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(SCRATCH_DIR).mkdir(parents=True, exist_ok=True)
    
    # Build arguments for streaming converter
    argv = [
        "--input-dir", INPUT_DIR,
        "--output-dir", OUTPUT_DIR,
        "--queue-db", QUEUE_DB,
        "--registry-db", REGISTRY_DB,
        "--scratch-dir", SCRATCH_DIR,
        "--log-level", LOG_LEVEL,
        "--expected-subbands", str(EXPECTED_SUBBANDS),
        "--chunk-duration", str(CHUNK_DURATION_MINUTES),
        "--poll-interval", str(POLL_INTERVAL),
        "--worker-poll-interval", str(POLL_INTERVAL),
        "--max-workers", str(MAX_WORKERS),
        "--execution-mode", "auto",
    ]
    
    if ENABLE_MONITORING:
        argv.extend(["--monitoring", "--monitor-interval", str(MONITOR_INTERVAL)])
    
    if ENABLE_CALIBRATION:
        argv.append("--enable-calibration-solving")
    
    if ENABLE_IMAGING:
        argv.append("--enable-group-imaging")
    
    logger.info(f"Arguments: {' '.join(argv)}")
    logger.info("")
    
    # Import and run the streaming converter
    try:
        from dsa110_contimg.conversion.streaming_converter import main as stream_main
        
        # Handle graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Starting streaming converter (watching for new files)...")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        return stream_main(argv)
        
    except ImportError as e:
        logger.error(f"Failed to import streaming converter: {e}")
        logger.error("Make sure you're running in the casa6 conda environment")
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Streaming converter failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
