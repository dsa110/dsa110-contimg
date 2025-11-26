import sqlite3
import time

DB_PATH = "/data/dsa110-contimg/state/db/products.sqlite3"


def migrate():
    print(f"Migrating database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='transient_candidates'"
    )
    if cursor.fetchone():
        print("Table 'transient_candidates' already exists.")
    else:
        print("Creating table 'transient_candidates'...")
        cursor.execute(
            """
            CREATE TABLE transient_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT NOT NULL,
                ms_path TEXT NOT NULL,
                ra_deg REAL NOT NULL,
                dec_deg REAL NOT NULL,
                snr REAL NOT NULL,
                peak_flux_mjy REAL NOT NULL,
                local_rms_mjy REAL NOT NULL,
                timestamp_mjd REAL,
                timestamp_iso TEXT,
                frame_index INTEGER,
                created_at REAL NOT NULL,
                status TEXT DEFAULT 'new',
                notes TEXT
            )
        """
        )

        # Create indices
        cursor.execute("CREATE INDEX idx_transient_ms_path ON transient_candidates(ms_path)")
        cursor.execute("CREATE INDEX idx_transient_snr ON transient_candidates(snr)")
        cursor.execute("CREATE INDEX idx_transient_created ON transient_candidates(created_at)")
        print("Table created successfully.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
