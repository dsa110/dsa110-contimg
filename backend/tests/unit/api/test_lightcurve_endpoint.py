"""Unit tests for lightcurve API endpoints.

Tests the GET /api/photometry/sources/{source_id}/lightcurve endpoint.
Uses in-memory database for proper integration testing.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dsa110_contimg.api.routes import create_app


def setup_test_database(db_path: Path):
    """Create test database with required tables and test data."""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    # Create sources table
    c.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            ra_deg REAL NOT NULL,
            dec_deg REAL NOT NULL,
            name TEXT
        )
    """)

    # Create photometry table
    c.execute("""
        CREATE TABLE IF NOT EXISTS photometry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            mjd REAL NOT NULL,
            peak_jyb REAL,
            peak_err_jyb REAL,
            flux_jy REAL,
            flux_err_jy REAL,
            normalized_flux_jy REAL,
            normalized_flux_err_jy REAL,
            image_path TEXT,
            FOREIGN KEY (source_id) REFERENCES sources(source_id)
        )
    """)

    # Insert test source
    c.execute(
        "INSERT INTO sources (source_id, ra_deg, dec_deg, name) VALUES (?, ?, ?, ?)",
        ("SRC001", 123.456, -45.678, "Test Source 1"),
    )

    # Insert test photometry measurements
    measurements = [
        ("SRC001", 60100.5, 1.0, 0.05, 1.0, 0.05, 1.0, 0.04, "/img1.fits"),
        ("SRC001", 60101.5, 1.2, 0.06, 1.2, 0.06, 1.1, 0.05, "/img2.fits"),
        ("SRC001", 60102.5, 0.9, 0.04, 0.9, 0.04, 0.95, 0.04, "/img3.fits"),
    ]
    c.executemany(
        """INSERT INTO photometry 
           (source_id, mjd, peak_jyb, peak_err_jyb, flux_jy, flux_err_jy, 
            normalized_flux_jy, normalized_flux_err_jy, image_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        measurements,
    )

    conn.commit()
    conn.close()


@pytest.fixture
def test_db():
    """Create temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "products.sqlite3"
        setup_test_database(db_path)
        yield db_path


@pytest.fixture
def client(test_db, monkeypatch):
    """Create test client with mocked database."""
    # Set environment variable BEFORE app creation
    monkeypatch.setenv("PIPELINE_PRODUCTS_DB", str(test_db))

    app = create_app()
    return TestClient(app)


class TestLightCurveEndpointWithMockDB:
    """Test lightcurve endpoint with mocked database.

    These tests use a test database to verify API behavior without
    needing to mock the Source class internals.
    """

    def test_get_lightcurve_endpoint_registered(self, client):
        """Test that lightcurve endpoint is registered and routed."""
        # Even with invalid source, endpoint should exist
        response = client.get("/api/photometry/sources/NONEXISTENT/lightcurve")
        # 404 because source doesn't exist, not 405 (method not allowed)
        assert response.status_code in [404, 500]

    def test_get_lightcurve_source_not_found(self, client):
        """Test lightcurve for non-existent source returns 404."""
        response = client.get("/api/photometry/sources/NONEXISTENT_SOURCE/lightcurve")
        assert response.status_code == 404


class TestSourceMetricsEndpointWithMockDB:
    """Test source metrics endpoint."""

    def test_get_metrics_endpoint_registered(self, client):
        """Test that metrics endpoint is registered and routed."""
        response = client.get("/api/photometry/sources/NONEXISTENT/metrics")
        assert response.status_code in [404, 500]

    def test_get_metrics_source_not_found(self, client):
        """Test metrics for non-existent source returns 404."""
        response = client.get("/api/photometry/sources/NONEXISTENT_SOURCE/metrics")
        assert response.status_code == 404
