# /data/dsa110-contimg/pipeline/scripts/cleanup_old_data.py

import os
from pathlib import Path
from datetime import datetime, timedelta
import shutil

def cleanup_old_ms_files(ms_dir, days_to_keep=30):
    """Delete MS files older than specified days."""
    cutoff = datetime.now() - timedelta(days=days_to_keep)
    
    for ms_file in Path(ms_dir).glob('*.ms'):
        mtime = datetime.fromtimestamp(ms_file.stat().st_mtime)
        if mtime < cutoff:
            print(f"Deleting old MS: {ms_file}")
            shutil.rmtree(ms_file)

def compress_old_logs(log_dir, days_to_keep=90):
    """Compress log files older than specified days."""
    cutoff = datetime.now() - timedelta(days=days_to_keep)
    
    for log_file in Path(log_dir).rglob('*.log'):
        if log_file.suffix == '.gz':
            continue  # Already compressed
            
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mtime < cutoff:
            print(f"Compressing log: {log_file}")
            os.system(f"gzip {log_file}")

# Run daily via cron:
# 0 4 * * * /data/dsa110-contimg/pipeline/scripts/cleanup_old_data.py