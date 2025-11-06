import argparse
import logging
import sqlite3
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dsa110_contimg.pointing.utils import load_pointing
from dsa110_contimg.database.products import ensure_products_db

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_pointing_from_file(file_path: Path, conn: sqlite3.Connection):
    """Extracts pointing from a file and logs it to the database."""
    try:
        logger.info(f"Processing new file: {file_path}")
        info = load_pointing(file_path)
        if info and 'mid_time' in info and 'dec_deg' in info and 'ra_deg' in info:
            conn.execute(
                "INSERT OR REPLACE INTO pointing_history (timestamp, ra_deg, dec_deg) VALUES (?, ?, ?)",
                (info['mid_time'].mjd, info['ra_deg'], info['dec_deg'])
            )
            conn.commit()
            logger.info(f"Logged pointing from {file_path}: RA={info['ra_deg']:.2f}, Dec={info['dec_deg']:.2f}")
    except Exception as e:
        logger.error(f"Failed to process file {file_path}: {e}")

class NewFileHandler(FileSystemEventHandler):
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.name.endswith('_sb00.hdf5') or file_path.name.endswith('.ms'):
            log_pointing_from_file(file_path, self.conn)

def main():
    """Main function to monitor a directory for new observation files."""
    parser = argparse.ArgumentParser(description="Monitor a directory for new observation files and log their pointing.")
    parser.add_argument('watch_dir', type=Path, help="Directory to watch for new files (e.g., /data/incoming/).")
    parser.add_argument('products_db', type=Path, help="Path to the products database.")
    args = parser.parse_args()

    conn = ensure_products_db(args.products_db)
    
    event_handler = NewFileHandler(conn)
    observer = Observer()
    observer.schedule(event_handler, args.watch_dir, recursive=True)
    
    logger.info(f"Starting to monitor {args.watch_dir} for new observation files...")
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()
