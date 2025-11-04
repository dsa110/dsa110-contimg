import argparse
import sched
import sqlite3
import time
from pathlib import Path

from astropy.time import Time

from dsa110_contimg.calibration.schedule import DSA110_LOCATION
from dsa110_contimg.database.products import ensure_products_db


def log_pointing(conn: sqlite3.Connection, pt_dec_deg: float):
    """Logs the current pointing to the database."""
    now = Time.now()
    ra_deg = now.sidereal_time('apparent', longitude=DSA110_LOCATION.lon).deg
    conn.execute(
        "INSERT OR REPLACE INTO pointing_history (timestamp, ra_deg, dec_deg) VALUES (?, ?, ?)",
        (now.mjd, ra_deg, pt_dec_deg)
    )
    conn.commit()


def main(products_db: Path, pt_dec_deg: float, interval_s: float):
    """Main loop for the pointing logger service."""
    conn = ensure_products_db(products_db)
    scheduler = sched.scheduler(time.time, time.sleep)

    def run():
        log_pointing(conn, pt_dec_deg)
        scheduler.enter(interval_s, 1, run)

    run()
    scheduler.run()


def cli():
    """Command line interface for the pointing logger service."""
    parser = argparse.ArgumentParser()
    parser.add_argument('products_db', type=Path, help='Path to the products database')
    parser.add_argument('--pt-dec-deg', type=float, required=True, help='Pointing declination in degrees')
    parser.add_argument('--interval-s', type=float, default=60.0, help='Logging interval in seconds')
    args = parser.parse_args()
    main(args.products_db, args.pt_dec_deg, args.interval_s)


if __name__ == '__main__':
    cli()
