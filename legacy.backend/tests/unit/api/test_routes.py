"""Tests for the monitoring API routes."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from dsa110_contimg.api.routes import create_app


def _init_queue_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute(
            """
            CREATE TABLE ingest_queue (
                group_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                received_at REAL NOT NULL,
                last_update REAL NOT NULL,
                expected_subbands INTEGER DEFAULT 16,
                chunk_minutes REAL DEFAULT 5.0,
                has_calibrator INTEGER DEFAULT NULL,
                calibrators TEXT DEFAULT NULL,
                processing_stage TEXT DEFAULT NULL,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT DEFAULT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE subband_files (
                group_id TEXT NOT NULL,
                subband_idx INTEGER NOT NULL,
                path TEXT NOT NULL,
                PRIMARY KEY (group_id, subband_idx)
            )
            """
        )

        now = datetime.now(tz=timezone.utc).timestamp()
        conn.execute(
            """
            INSERT INTO ingest_queue(group_id, state, received_at, last_update, expected_subbands)
            VALUES(?,?,?,?,?)
            """,
            ("2025-10-07T00:00:00", "pending", now, now, 16),
        )
        # simulate 10 subbands ingested
        conn.executemany(
            "INSERT INTO subband_files(group_id, subband_idx, path) VALUES(?,?,?)",
            [
                ("2025-10-07T00:00:00", idx, f"/data/subbands/file_sb{idx:02d}.hdf5")
                for idx in range(10)
            ],
        )


def _init_registry_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute(
            """
            CREATE TABLE caltables (
                id INTEGER PRIMARY KEY,
                set_name TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                table_type TEXT NOT NULL,
                order_index INTEGER NOT NULL,
                cal_field TEXT,
                refant TEXT,
                created_at REAL NOT NULL,
                valid_start_mjd REAL,
                valid_end_mjd REAL,
                status TEXT NOT NULL,
                notes TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO caltables(set_name, path, table_type, order_index, created_at, status) VALUES(?,?,?,?,?,?)",
            (
                "2025-10-06_J1234",
                "/data/cal/2025-10-06_J1234_kcal",
                "K",
                10,
                datetime.now(tz=timezone.utc).timestamp(),
                "active",
            ),
        )


def _init_products_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute(
            """
            CREATE TABLE images (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL,
                ms_path TEXT NOT NULL,
                created_at REAL NOT NULL,
                type TEXT NOT NULL,
                beam_major_arcsec REAL,
                noise_jy REAL,
                pbcor INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            INSERT INTO images(path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                "/data/images/2025-10-07T00:00:00_dirty.fits",
                "/data/ms/2025-10-07T00:00:00.ms",
                datetime.now(tz=timezone.utc).timestamp(),
                "dirty",
                12.5,
                0.002,
                1,
            ),
        )


def test_status_and_products_endpoints(tmp_path, monkeypatch):
    registry_db = tmp_path / "registry.sqlite3"
    queue_db = tmp_path / "queue.sqlite3"
    products_db = tmp_path / "products.sqlite3"

    _init_registry_db(registry_db)
    _init_queue_db(queue_db)
    _init_products_db(products_db)

    monkeypatch.setenv("CAL_REGISTRY_DB", str(registry_db))
    monkeypatch.setenv("PIPELINE_QUEUE_DB", str(queue_db))
    monkeypatch.setenv("PIPELINE_PRODUCTS_DB", str(products_db))

    app = create_app()
    client = TestClient(app)

    status_response = client.get("/api/status")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["queue"]["total"] == 1
    assert data["queue"]["pending"] == 1
    assert data["recent_groups"][0]["subbands_present"] == 10
    assert data["calibration_sets"][0]["set_name"] == "2025-10-06_J1234"

    products_response = client.get("/api/products")
    assert products_response.status_code == 200
    payload = products_response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["type"] == "dirty"
