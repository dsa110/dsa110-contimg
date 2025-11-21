import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from dsa110_contimg.photometry.source import Source, SourceError


@pytest.fixture
def mock_db_path(tmp_path):
    """Create a mock products database with necessary tables."""
    db_path = tmp_path / "test_products.sqlite3"
    conn = sqlite3.connect(db_path)

    # Create tables
    conn.execute(
        """
        CREATE TABLE photometry_timeseries (
            source_id TEXT,
            mjd REAL,
            normalized_flux_jy REAL,
            normalized_flux_err_jy REAL,
            flux_jy REAL,
            flux_err_jy REAL,
            image_path TEXT,
            measured_at REAL,
            ra_deg REAL,
            dec_deg REAL
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE variability_stats (
            source_id TEXT PRIMARY KEY,
            ra_deg REAL,
            dec_deg REAL,
            mean_flux_mjy REAL,
            eta_metric REAL,
            n_obs INTEGER
        )
    """
    )

    conn.commit()
    conn.close()
    return db_path


def populate_db(db_path, source_data, stats_data=None):
    """Helper to insert data into the mock DB."""
    conn = sqlite3.connect(db_path)

    # Insert timeseries
    for row in source_data:
        conn.execute(
            """
            INSERT INTO photometry_timeseries 
            (source_id, mjd, normalized_flux_jy, normalized_flux_err_jy, flux_jy, flux_err_jy, image_path, measured_at, ra_deg, dec_deg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            row,
        )

    # Insert stats
    if stats_data:
        for row in stats_data:
            conn.execute(
                """
                INSERT INTO variability_stats
                (source_id, ra_deg, dec_deg, mean_flux_mjy, eta_metric, n_obs)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                row,
            )

    conn.commit()
    conn.close()


def test_source_init_no_db():
    """Test Source initialization without DB."""
    # Should work if coordinates provided
    src = Source("TEST_SRC", ra_deg=10.0, dec_deg=20.0)
    assert src.measurements.empty
    assert src.ra_deg == 10.0

    # Should fail if no coordinates and no DB
    with pytest.raises(SourceError):
        Source("TEST_SRC")


def test_load_measurements(mock_db_path):
    """Test loading measurements from DB."""
    data = [
        ("SRC1", 59000.0, 1.0, 0.1, 1.0, 0.1, "img1.fits", 1600000000.0, 10.0, 20.0),
        ("SRC1", 59001.0, 1.1, 0.1, 1.1, 0.1, "img2.fits", 1600086400.0, 10.0, 20.0),
    ]
    populate_db(mock_db_path, data)

    src = Source("SRC1", products_db=mock_db_path)
    assert len(src.measurements) == 2
    assert "normalized_flux_jy" in src.measurements.columns
    assert src.ra_deg == 10.0


def test_find_stable_neighbors(mock_db_path):
    """Test finding stable neighbors."""
    # Target Source measurements (needed for median flux)
    # Target: ~10 mJy (0.010 Jy)
    target_data = [
        ("TARGET", 59000.0, 0.010, 0.001, 0.010, 0.001, "img1.fits", 0, 10.0, 10.0),
        ("TARGET", 59001.0, 0.010, 0.001, 0.010, 0.001, "img2.fits", 0, 10.0, 10.0),
    ]

    # Neighbor Stats
    stats_data = [
        # Valid Neighbor: Near, Stable (eta=0.5), Similar Flux (10 mJy)
        ("NEIGHBOR1", 10.1, 10.1, 10.0, 0.5, 20),
        # Distant Neighbor: > 0.5 deg away
        ("NEIGHBOR2", 12.0, 12.0, 10.0, 0.5, 20),
        # Unstable Neighbor: eta=2.0
        ("NEIGHBOR3", 10.05, 10.05, 10.0, 2.0, 20),
        # Faint Neighbor: 0.1 mJy (ratio 0.01 < 0.1)
        ("NEIGHBOR4", 10.05, 10.05, 0.1, 0.5, 20),
        # Self
        ("TARGET", 10.0, 10.0, 10.0, 0.5, 20),
    ]

    populate_db(mock_db_path, target_data, stats_data)

    src = Source("TARGET", products_db=mock_db_path)
    neighbors = src.find_stable_neighbors(radius_deg=0.5, max_eta=1.5, min_flux_ratio=0.1)

    assert "NEIGHBOR1" in neighbors
    assert "NEIGHBOR2" not in neighbors  # Too far
    assert "NEIGHBOR3" not in neighbors  # Unstable
    assert "NEIGHBOR4" not in neighbors  # Too faint
    assert "TARGET" not in neighbors  # Self


def test_calculate_relative_lightcurve(mock_db_path):
    """Test relative lightcurve calculation end-to-end."""
    # Target (Use small fluxes to match mJy scale of stats if needed, or match stats to Jy)
    # Target: ~15 mJy avg (0.015 Jy)
    target_data = [
        ("TARGET", 59000.0, 0.010, 0.001, 0.010, 0.001, "img1.fits", 0, 0.0, 0.0),
        ("TARGET", 59001.0, 0.020, 0.001, 0.020, 0.001, "img2.fits", 0, 0.0, 0.0),
    ]

    # Neighbor (Stable at 5 mJy = 0.005 Jy)
    neighbor_data = [
        ("NEIGHBOR1", 59000.0, 0.005, 0.0005, 0.005, 0.0005, "img1.fits", 0, 0.1, 0.1),
        ("NEIGHBOR1", 59001.0, 0.005, 0.0005, 0.005, 0.0005, "img2.fits", 0, 0.1, 0.1),
    ]

    # Neighbor Stats (mean_flux_mjy = 5.0)
    stats_data = [("NEIGHBOR1", 0.1, 0.1, 5.0, 0.1, 20)]

    populate_db(mock_db_path, target_data + neighbor_data, stats_data)

    src = Source("TARGET", products_db=mock_db_path)
    result = src.calculate_relative_lightcurve(min_neighbors=1)

    assert result["n_neighbors"] == 1
    assert result["neighbor_ids"] == ["NEIGHBOR1"]

    # Fluxes: Target=[0.010, 0.020], Neighbor=[0.005, 0.005]. Ratio=[2.0, 4.0].
    expected = np.array([2.0, 4.0])
    np.testing.assert_array_almost_equal(result["relative_flux"], expected)
    assert result["relative_flux_mean"] == 3.0


def test_calculate_relative_lightcurve_no_neighbors(mock_db_path):
    """Test graceful failure when no neighbors found."""
    target_data = [("TARGET", 59000.0, 10.0, 1.0, 10.0, 1.0, "img1.fits", 0, 0.0, 0.0)]
    populate_db(mock_db_path, target_data)  # No stats data -> no neighbors

    src = Source("TARGET", products_db=mock_db_path)
    result = src.calculate_relative_lightcurve(min_neighbors=1)

    assert result == {}


@patch("dsa110_contimg.photometry.source.check_all_services")
def test_crossmatch_external(mock_check_all, mock_db_path):
    """Test crossmatch_external integration."""
    # Setup
    data = [("SRC1", 59000.0, 1.0, 0.1, 1.0, 0.1, "img1.fits", 1600000000.0, 10.0, 20.0)]
    populate_db(mock_db_path, data)

    src = Source("SRC1", products_db=mock_db_path)

    # Mock return
    mock_check_all.return_value = {"Gaia": {"match1": 0.5}, "Simbad": {"match2": 1.0}}

    # Call
    results = src.crossmatch_external(radius_arcsec=5.0)

    # Verify
    assert "Gaia" in results
    assert "Simbad" in results
    assert results["Gaia"] == {"match1": 0.5}

    # Verify arguments
    args, kwargs = mock_check_all.call_args
    coord = args[0]
    assert coord.ra.value == 10.0
    assert coord.dec.value == 20.0
    assert kwargs["radius"].value == 5.0
