import argparse
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.pointing.utils import load_pointing

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def find_observation_files(
    data_dir: Path, start_date: datetime, end_date: datetime
) -> List[Tuple[datetime, Path]]:
    """Finds primary observation files (_sb00.hdf5 or .ms) within a date range."""
    files_to_process = []
    logger.info(
        f"Scanning for primary files in {data_dir} from {start_date.date()} to {end_date.date()}"
    )
    end_date_inclusive = end_date + timedelta(days=1)
    for root, _, files in os.walk(data_dir):
        for filename in files:
            if not (filename.endswith("_sb00.hdf5") or filename.endswith(".ms")):
                continue
            try:
                timestamp_str = filename.split("_")[0]
                file_date = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
                if start_date <= file_date < end_date_inclusive:
                    files_to_process.append(
                        (file_date, Path(os.path.join(root, filename)))
                    )
            except (ValueError, IndexError):
                continue
    files_to_process.sort()
    logger.info(f"Found {len(files_to_process)} primary observation files to process.")
    return files_to_process


def extract_pointing_data(
    files_with_dates: List[Tuple[datetime, Path]],
) -> pd.DataFrame:
    """Extracts pointing data from a list of observation files, including RA and MJD."""
    pointing_data = []
    for file_date, file_path in files_with_dates:
        try:
            info = load_pointing(file_path)
            if info and "mid_time" in info and "dec_deg" in info and "ra_deg" in info:
                pointing_data.append(
                    {
                        "mjd": info["mid_time"].mjd,
                        "ra_deg": info["ra_deg"],
                        "dec_deg": info["dec_deg"],
                        "datetime": file_date,
                    }
                )
        except Exception as e:
            logger.warning(f"Could not process file {file_path}: {e}")
    return pd.DataFrame(pointing_data)


def backfill_database(conn: sqlite3.Connection, data: pd.DataFrame):
    """Inserts pointing data into the database using INSERT OR REPLACE."""
    if data.empty:
        logger.warning("No pointing data to backfill.")
        return

    insert_count = 0
    for _, row in data.iterrows():
        try:
            conn.execute(
                "INSERT OR REPLACE INTO pointing_history (timestamp, ra_deg, dec_deg) VALUES (?, ?, ?)",
                (row["mjd"], row["ra_deg"], row["dec_deg"]),
            )
            insert_count += 1
        except Exception as e:
            logger.error(f"Failed to insert row for timestamp {row['mjd']}: {e}")

    conn.commit()
    logger.info(
        f"Successfully inserted or replaced {insert_count} rows in the pointing_history table."
    )


def main():
    """Main function to backfill the pointing database using a sparse sampling strategy."""
    parser = argparse.ArgumentParser(
        description="Backfill pointing history database from existing observation data."
    )
    parser.add_argument(
        "data_dir", type=Path, help="Directory containing the observation data."
    )
    parser.add_argument("products_db", type=Path, help="Path to the products database.")
    parser.add_argument(
        "--start-date",
        type=str,
        default="2025-10-01",
        help="Start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2025-10-23",
        help="End date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--jump-threshold-deg",
        type=float,
        default=0.1,
        help="Declination change to trigger granular search.",
    )
    args = parser.parse_args()

    start_dt = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(args.end_date, "%Y-%m-%d")

    all_files_with_dates = find_observation_files(args.data_dir, start_dt, end_dt)
    if not all_files_with_dates:
        logger.warning(
            "No primary observation files found in the specified date range."
        )
        return

    # Sparse sampling logic from plotting script
    sparse_files_with_dates = []
    last_day = None
    for file_date, file_path in all_files_with_dates:
        if last_day is None or (file_date.date() - last_day).days >= 1:
            sparse_files_with_dates.append((file_date, file_path))
            last_day = file_date.date()

    sparse_pointing_df = extract_pointing_data(sparse_files_with_dates)
    if sparse_pointing_df.empty:
        logger.error("Could not extract any pointing data from the sparse file sample.")
        return
    sparse_pointing_df = sparse_pointing_df.sort_values(by="datetime").reset_index(
        drop=True
    )

    final_dfs = []
    last_idx = 0
    for i in range(1, len(sparse_pointing_df)):
        dec_diff = abs(
            sparse_pointing_df.loc[i, "dec_deg"]
            - sparse_pointing_df.loc[i - 1, "dec_deg"]
        )
        if dec_diff > args.jump_threshold_deg:
            logger.info(
                f"Declination jump of {dec_diff:.2f} deg detected. Processing granularly."
            )
            start_time = sparse_pointing_df.loc[i - 1, "datetime"]
            end_time = sparse_pointing_df.loc[i, "datetime"]

            final_dfs.append(sparse_pointing_df.iloc[last_idx:i])

            files_in_jump_with_dates = [
                (d, p) for d, p in all_files_with_dates if start_time <= d <= end_time
            ]
            detailed_df = extract_pointing_data(files_in_jump_with_dates)
            final_dfs.append(detailed_df)
            last_idx = i

    final_dfs.append(sparse_pointing_df.iloc[last_idx:])

    if not final_dfs:
        logger.warning("No data to backfill after processing.")
        return

    final_pointing_df = pd.concat(final_dfs, ignore_index=True)

    conn = ensure_products_db(args.products_db)
    backfill_database(conn, final_pointing_df)
    conn.close()


if __name__ == "__main__":
    main()
