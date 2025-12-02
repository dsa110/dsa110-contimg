"""
Tests for MS raster and antenna visualization endpoints.

These tests verify the casangi integration endpoints work correctly
without requiring actual MS files by mocking the casacore dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient


class TestMsRasterEndpoint:
    """Tests for the /ms/{path}/raster endpoint."""

    def test_raster_returns_png_content_type(self, client: TestClient, tmp_path):
        """Verify endpoint returns PNG image with correct content type."""
        # Create a fake MS directory structure
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        (ms_path / "ANTENNA").mkdir()

        with patch("dsa110_contimg.api.routes.ms._generate_raster_plot") as mock_gen:
            # Return a minimal valid PNG
            mock_gen.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

            response = client.get(
                f"/api/v1/ms/{str(ms_path)}/raster",
                params={"xaxis": "time", "yaxis": "amp"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.content.startswith(b"\x89PNG")

    def test_raster_validates_xaxis_param(self, client: TestClient, tmp_path):
        """Verify invalid xaxis parameter returns 422."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        response = client.get(
            f"/api/v1/ms/{str(ms_path)}/raster",
            params={"xaxis": "invalid_axis", "yaxis": "amp"},
        )

        assert response.status_code == 422
        assert "xaxis" in response.text.lower()

    def test_raster_validates_yaxis_param(self, client: TestClient, tmp_path):
        """Verify invalid yaxis parameter returns 422."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        response = client.get(
            f"/api/v1/ms/{str(ms_path)}/raster",
            params={"xaxis": "time", "yaxis": "invalid_component"},
        )

        assert response.status_code == 422
        assert "yaxis" in response.text.lower()

    def test_raster_validates_width_bounds(self, client: TestClient, tmp_path):
        """Verify width parameter is bounded."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        # Too small
        response = client.get(
            f"/api/v1/ms/{str(ms_path)}/raster",
            params={"xaxis": "time", "yaxis": "amp", "width": 50},
        )
        assert response.status_code == 422

        # Too large
        response = client.get(
            f"/api/v1/ms/{str(ms_path)}/raster",
            params={"xaxis": "time", "yaxis": "amp", "width": 5000},
        )
        assert response.status_code == 422

    def test_raster_returns_404_for_missing_ms(self, client: TestClient):
        """Verify 404 for non-existent MS."""
        response = client.get(
            "/api/v1/ms/%2Fnonexistent%2Fpath.ms/raster",
            params={"xaxis": "time", "yaxis": "amp"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_raster_handles_generation_error(self, client: TestClient, tmp_path):
        """Verify 500 error when plot generation fails."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        with patch("dsa110_contimg.api.routes.ms._generate_raster_plot") as mock_gen:
            mock_gen.side_effect = RuntimeError("CASA error")

            response = client.get(
                f"/api/v1/ms/{str(ms_path)}/raster",
                params={"xaxis": "time", "yaxis": "amp"},
            )

            assert response.status_code == 500
            assert "failed" in response.json()["detail"].lower()

    def test_raster_caches_response(self, client: TestClient, tmp_path):
        """Verify response includes cache headers."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        with patch("dsa110_contimg.api.routes.ms._generate_raster_plot") as mock_gen:
            mock_gen.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

            response = client.get(
                f"/api/v1/ms/{str(ms_path)}/raster",
                params={"xaxis": "time", "yaxis": "amp"},
            )

            assert "cache-control" in response.headers
            assert "max-age" in response.headers["cache-control"]


class TestAntennaLayoutEndpoint:
    """Tests for the /ms/{path}/antennas endpoint."""

    def test_antennas_returns_layout_response(self, client: TestClient, tmp_path):
        """Verify endpoint returns valid AntennaLayoutResponse."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        (ms_path / "ANTENNA").mkdir()

        with patch("dsa110_contimg.api.routes.ms._get_antenna_info") as mock_get:
            from dsa110_contimg.api.schemas import AntennaInfo, AntennaLayoutResponse

            mock_get.return_value = AntennaLayoutResponse(
                antennas=[
                    AntennaInfo(
                        id=0,
                        name="DSA-001",
                        x_m=0.0,
                        y_m=0.0,
                        flagged_pct=5.0,
                        baseline_count=109,
                    ),
                    AntennaInfo(
                        id=1,
                        name="DSA-002",
                        x_m=10.0,
                        y_m=0.0,
                        flagged_pct=0.0,
                        baseline_count=109,
                    ),
                ],
                array_center_lon=-118.2817,
                array_center_lat=37.2339,
                total_baselines=1,
            )

            response = client.get(f"/api/v1/ms/{str(ms_path)}/antennas")

            assert response.status_code == 200
            data = response.json()
            assert "antennas" in data
            assert len(data["antennas"]) == 2
            assert data["antennas"][0]["name"] == "DSA-001"
            assert data["total_baselines"] == 1
            assert "array_center_lon" in data

    def test_antennas_returns_404_for_missing_ms(self, client: TestClient):
        """Verify 404 for non-existent MS."""
        response = client.get("/api/v1/ms/%2Fnonexistent%2Fpath.ms/antennas")

        assert response.status_code == 404

    def test_antennas_returns_404_for_missing_antenna_table(
        self, client: TestClient, tmp_path
    ):
        """Verify 404 when ANTENNA subtable doesn't exist."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        # Don't create ANTENNA subdirectory

        response = client.get(f"/api/v1/ms/{str(ms_path)}/antennas")

        assert response.status_code == 404
        assert "antenna" in response.json()["detail"].lower()

    def test_antennas_handles_read_error(self, client: TestClient, tmp_path):
        """Verify 500 error when reading antenna data fails."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        (ms_path / "ANTENNA").mkdir()

        with patch("dsa110_contimg.api.routes.ms._get_antenna_info") as mock_get:
            mock_get.side_effect = RuntimeError("Table read error")

            response = client.get(f"/api/v1/ms/{str(ms_path)}/antennas")

            assert response.status_code == 500
            assert "failed" in response.json()["detail"].lower()


class TestGenerateRasterPlot:
    """Unit tests for the _generate_raster_plot function."""

    @pytest.fixture
    def mock_ms_data(self):
        """Create mock MS data for testing."""
        return {
            "TIME": np.array([1.0, 1.0, 1.0, 2.0, 2.0, 2.0]),
            "ANTENNA1": np.array([0, 0, 1, 0, 0, 1]),
            "ANTENNA2": np.array([1, 2, 2, 1, 2, 2]),
            "DATA": np.ones((6, 10, 4), dtype=np.complex64),
            "FLAG": np.zeros((6, 10, 4), dtype=bool),
        }

    def test_generate_raster_produces_png(self, tmp_path, mock_ms_data):
        """Verify function returns valid PNG bytes."""
        from dsa110_contimg.api.routes.ms import _generate_raster_plot

        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        # Mock casacore.tables.table
        mock_table = MagicMock()
        mock_table.__enter__ = MagicMock(return_value=mock_table)
        mock_table.__exit__ = MagicMock(return_value=False)

        # The production code tries CORRECTED_DATA first, then falls back to DATA
        # on RuntimeError. KeyError doesn't trigger the fallback, so we need to
        # raise RuntimeError for missing columns.
        def getcol_side_effect(col):
            if col in mock_ms_data:
                return mock_ms_data[col]
            raise RuntimeError(f"Column {col} not found")

        mock_table.getcol.side_effect = getcol_side_effect
        mock_table.close = MagicMock()

        with patch("casacore.tables.table", return_value=mock_table):
            result = _generate_raster_plot(
                ms_path=str(ms_path),
                xaxis="time",
                yaxis="amp",
                colormap="viridis",
                width=400,
                height=300,
            )

            assert isinstance(result, bytes)
            assert result.startswith(b"\x89PNG")

    def test_generate_raster_handles_corrected_data(self, tmp_path, mock_ms_data):
        """Verify function uses CORRECTED_DATA when available."""
        from dsa110_contimg.api.routes.ms import _generate_raster_plot

        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        mock_ms_data["CORRECTED_DATA"] = mock_ms_data["DATA"] * 2

        mock_table = MagicMock()
        mock_table.__enter__ = MagicMock(return_value=mock_table)
        mock_table.__exit__ = MagicMock(return_value=False)

        def getcol_side_effect(col):
            if col in mock_ms_data:
                return mock_ms_data[col]
            raise RuntimeError(f"Column {col} not found")

        mock_table.getcol.side_effect = getcol_side_effect
        mock_table.close = MagicMock()

        with patch("casacore.tables.table", return_value=mock_table):
            result = _generate_raster_plot(
                ms_path=str(ms_path),
                xaxis="time",
                yaxis="amp",
                colormap="viridis",
                width=400,
                height=300,
            )

            assert isinstance(result, bytes)


class TestGetAntennaInfo:
    """Unit tests for the _get_antenna_info function."""

    @pytest.fixture
    def mock_antenna_data(self):
        """Create mock antenna data."""
        return {
            "NAME": np.array(["DSA-001", "DSA-002", "DSA-003"]),
            "POSITION": np.array([
                [-2409150.0, -4478573.0, 3838617.0],
                [-2409160.0, -4478573.0, 3838617.0],
                [-2409150.0, -4478583.0, 3838617.0],
            ]),
        }

    @pytest.fixture
    def mock_main_data(self):
        """Create mock main table data."""
        return {
            "ANTENNA1": np.array([0, 0, 1]),
            "ANTENNA2": np.array([1, 2, 2]),
            "FLAG": np.zeros((3, 10, 4), dtype=bool),
        }

    def test_get_antenna_info_returns_response(
        self, tmp_path, mock_antenna_data, mock_main_data
    ):
        """Verify function returns AntennaLayoutResponse."""
        from dsa110_contimg.api.routes.ms import _get_antenna_info

        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        (ms_path / "ANTENNA").mkdir()

        # Mock antenna table
        mock_ant_table = MagicMock()
        mock_ant_table.getcol.side_effect = lambda col: mock_antenna_data[col]
        mock_ant_table.close = MagicMock()

        # Mock main table
        mock_main_table = MagicMock()
        mock_main_table.getcol.side_effect = lambda col: mock_main_data[col]
        mock_main_table.close = MagicMock()

        def table_factory(path, readonly=True):
            if "ANTENNA" in path:
                return mock_ant_table
            return mock_main_table

        with patch("casacore.tables.table", side_effect=table_factory):
            with patch("dsa110_contimg.utils.constants.DSA110_LATITUDE", 37.2339):
                with patch("dsa110_contimg.utils.constants.DSA110_LONGITUDE", -118.2817):
                    result = _get_antenna_info(str(ms_path))

                    assert result is not None
                    assert len(result.antennas) == 3
                    assert result.antennas[0].name == "DSA-001"
                    assert result.total_baselines == 3


# Fixtures for TestClient
@pytest.fixture
def client():
    """Create test client for API."""
    from dsa110_contimg.api.app import app

    with TestClient(app) as test_client:
        yield test_client
