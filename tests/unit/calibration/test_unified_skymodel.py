from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from dsa110_contimg.calibration.skymodels import make_unified_skymodel


@pytest.fixture
def mock_query_sources():
    with patch("dsa110_contimg.catalog.query.query_sources") as mock:
        yield mock


def test_unified_merging_logic(mock_query_sources):
    # Setup mock returns
    # FIRST: Source A (100, 45)
    df_first = pd.DataFrame({"ra_deg": [100.0], "dec_deg": [45.0], "flux_mjy": [100.0]})

    # RACS: Source A (100.0001, 45.0001) [close to A] + Source B (101.0, 45.0)
    df_rax = pd.DataFrame(
        {"ra_deg": [100.0001, 101.0], "dec_deg": [45.0001, 45.0], "flux_mjy": [100.0, 50.0]}
    )

    # NVSS: Source A [close to A] + Source B [close to B] + Source C (102.0, 45.0)
    df_nvss = pd.DataFrame(
        {
            "ra_deg": [100.0002, 101.0002, 102.0],
            "dec_deg": [45.0002, 45.0002, 45.0],
            "flux_mjy": [100.0, 50.0, 10.0],
        }
    )

    def side_effect(catalog_type, **kwargs):
        if catalog_type == "first":
            return df_first
        if catalog_type == "rax":
            return df_rax
        if catalog_type == "nvss":
            return df_nvss
        return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

    mock_query_sources.side_effect = side_effect

    # Run
    # match_radius_arcsec=5.0 means sources within ~5 arcsec are considered the same
    sky = make_unified_skymodel(100.0, 45.0, 5.0, match_radius_arcsec=5.0)

    # Verify
    # Should have 3 sources: A (FIRST), B (RACS), C (NVSS)
    assert sky.Ncomponents == 3

    names = sky.name
    origins = [n.split("_")[0] for n in names]

    # Check counts
    assert origins.count("FIRST") == 1
    assert origins.count("RACS") == 1
    assert origins.count("NVSS") == 1

    # Verify Source A came from FIRST (exact coordinates)
    # Index of FIRST source
    idx_first = origins.index("FIRST")
    assert np.isclose(sky.skycoord[idx_first].ra.deg, 100.0)

    # Verify Source B came from RACS
    idx_racs = origins.index("RACS")
    assert np.isclose(sky.skycoord[idx_racs].ra.deg, 101.0)

    # Verify Source C came from NVSS
    idx_nvss = origins.index("NVSS")
    assert np.isclose(sky.skycoord[idx_nvss].ra.deg, 102.0)


def test_unified_empty_catalogs(mock_query_sources):
    # Test when catalogs return empty
    mock_query_sources.return_value = pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

    sky = make_unified_skymodel(0, 0, 1.0)
    assert sky.Ncomponents == 0


def test_unified_fallback(mock_query_sources):
    # Test when FIRST is empty, should fallback to RACS/NVSS
    df_rax = pd.DataFrame({"ra_deg": [100.0], "dec_deg": [45.0], "flux_mjy": [50.0]})

    def side_effect(catalog_type, **kwargs):
        if catalog_type == "rax":
            return df_rax
        return pd.DataFrame(columns=["ra_deg", "dec_deg", "flux_mjy"])

    mock_query_sources.side_effect = side_effect

    sky = make_unified_skymodel(100.0, 45.0, 1.0)
    assert sky.Ncomponents == 1
    assert "RACS" in sky.name[0]
