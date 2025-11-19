from unittest.mock import MagicMock, patch

import astropy.units as u
import pandas as pd
import pytest
from astropy.coordinates import SkyCoord

from dsa110_contimg.catalog.multiwavelength import check_nvss, check_vlass


def test_check_nvss_local_success():
    source = SkyCoord(10.0, 20.0, unit="deg")

    mock_df = pd.DataFrame({"ra_deg": [10.0001], "dec_deg": [20.0001], "flux_mjy": [100.0]})

    with patch(
        "dsa110_contimg.calibration.catalogs.query_catalog_sources", return_value=mock_df
    ) as mock_query:
        with patch("dsa110_contimg.catalog.multiwavelength._check_vizier") as mock_vizier:
            result = check_nvss(source, radius=10 * u.arcsec)

            # Should verify local query was called
            mock_query.assert_called_once()
            args, _ = mock_query.call_args
            assert args[0] == "nvss"

            # Should verify result contains formatted name
            assert len(result) == 1
            assert any("NVSS J" in k for k in result.keys())

            # Should verify vizier was NOT called
            mock_vizier.assert_not_called()


def test_check_nvss_local_failure_fallback():
    source = SkyCoord(10.0, 20.0, unit="deg")

    # Simulate ImportError or empty result to trigger fallback
    with patch(
        "dsa110_contimg.calibration.catalogs.query_catalog_sources",
        side_effect=ImportError("No module"),
    ):
        with patch("dsa110_contimg.catalog.multiwavelength._check_vizier") as mock_vizier:
            check_nvss(source, radius=10 * u.arcsec)
            mock_vizier.assert_called_once()


def test_check_vlass_local_success():
    source = SkyCoord(30.0, 40.0, unit="deg")
    mock_df = pd.DataFrame({"ra_deg": [30.0001], "dec_deg": [40.0001], "flux_mjy": [50.0]})

    with patch(
        "dsa110_contimg.calibration.catalogs.query_catalog_sources", return_value=mock_df
    ) as mock_query:
        result = check_vlass(source, radius=10 * u.arcsec)
        assert len(result) == 1
        assert any("VLASS J" in k for k in result.keys())
