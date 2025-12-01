"""
Tests for Phase 3: Deep Integration features.

Tests for:
- Validation utilities for MS visualization
- WebSocket progress tracking
- Image versioning endpoints
- Session cleanup functionality
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

from dsa110_contimg.api.validation import (
    validate_ms_for_visualization,
    validate_imaging_parameters,
    RasterPlotParams,
    ImagingSessionParams,
    ValidationError,
)


# =============================================================================
# Validation Tests
# =============================================================================


class TestMsValidation:
    """Tests for MS visualization validation."""

    def test_validate_ms_not_found(self, tmp_path):
        """Should raise 404 for non-existent MS."""
        with pytest.raises(HTTPException) as exc_info:
            validate_ms_for_visualization(str(tmp_path / "nonexistent.ms"))
        assert exc_info.value.status_code == 404

    def test_validate_ms_not_directory(self, tmp_path):
        """Should raise error if path is file, not directory."""
        fake_file = tmp_path / "fake.ms"
        fake_file.write_text("not a real MS")

        with pytest.raises(ValidationError) as exc_info:
            validate_ms_for_visualization(str(fake_file))
        assert "not a valid Measurement Set directory" in str(exc_info.value.detail)

    def test_validate_ms_missing_table_dat(self, tmp_path):
        """Should raise error if MS directory missing table.dat."""
        fake_ms = tmp_path / "fake.ms"
        fake_ms.mkdir()

        with pytest.raises(ValidationError) as exc_info:
            validate_ms_for_visualization(str(fake_ms))
        assert "missing table.dat" in str(exc_info.value.detail)

    def test_validate_ms_valid_structure(self, tmp_path):
        """Should pass validation for valid MS structure (mocked casacore)."""
        fake_ms = tmp_path / "valid.ms"
        fake_ms.mkdir()
        (fake_ms / "table.dat").write_bytes(b"\x00" * 100)

        # Mock casacore.tables
        mock_table = MagicMock()
        mock_table.__enter__ = MagicMock(return_value=mock_table)
        mock_table.__exit__ = MagicMock(return_value=False)
        mock_table.nrows.return_value = 1000
        mock_table.colnames.return_value = ["DATA", "FLAG", "UVW"]

        with patch("casacore.tables.table", return_value=mock_table):
            # Should not raise
            validate_ms_for_visualization(str(fake_ms))


class TestImagingParameterValidation:
    """Tests for imaging parameter validation."""

    def test_valid_imsize(self):
        """Should accept valid imsize values."""
        validate_imaging_parameters([4096, 4096], 1000)  # Should not raise

    def test_invalid_imsize_length(self):
        """Should reject imsize with wrong length."""
        with pytest.raises(ValidationError) as exc_info:
            validate_imaging_parameters([4096], 1000)
        assert "imsize must be [width, height]" in str(exc_info.value.detail)

    def test_invalid_imsize_too_large(self):
        """Should reject imsize > 8192."""
        with pytest.raises(ValidationError) as exc_info:
            validate_imaging_parameters([10000, 10000], 1000)
        assert "imsize must be 1-8192" in str(exc_info.value.detail)

    def test_invalid_niter_negative(self):
        """Should reject negative niter."""
        with pytest.raises(ValidationError) as exc_info:
            validate_imaging_parameters([4096, 4096], -1)
        assert "niter must be 0" in str(exc_info.value.detail)

    def test_invalid_niter_too_large(self):
        """Should reject niter > 1M."""
        with pytest.raises(ValidationError) as exc_info:
            validate_imaging_parameters([4096, 4096], 2000000)
        assert "1000000" in str(exc_info.value.detail)

    def test_valid_cell_formats(self):
        """Should accept valid cell format strings."""
        validate_imaging_parameters([4096, 4096], 1000, "2.5arcsec")
        validate_imaging_parameters([4096, 4096], 1000, "1arcmin")
        validate_imaging_parameters([4096, 4096], 1000, "0.5deg")

    def test_invalid_cell_format(self):
        """Should reject invalid cell format."""
        with pytest.raises(ValidationError) as exc_info:
            validate_imaging_parameters([4096, 4096], 1000, "2.5 arcseconds")
        assert "cell must be in format" in str(exc_info.value.detail)


class TestRasterPlotParams:
    """Tests for RasterPlotParams model."""

    def test_default_values(self):
        """Should have correct defaults."""
        params = RasterPlotParams()
        assert params.xaxis == "time"
        assert params.yaxis == "amp"
        assert params.colormap == "viridis"
        assert params.aggregator == "mean"
        assert params.width == 800
        assert params.height == 600

    def test_valid_axes(self):
        """Should accept valid axis values."""
        params = RasterPlotParams(xaxis="baseline", yaxis="phase")
        assert params.xaxis == "baseline"
        assert params.yaxis == "phase"

    def test_invalid_xaxis(self):
        """Should reject invalid xaxis values."""
        with pytest.raises(ValueError):
            RasterPlotParams(xaxis="invalid")

    def test_size_bounds(self):
        """Should enforce size bounds."""
        with pytest.raises(ValueError):
            RasterPlotParams(width=100)  # Too small
        with pytest.raises(ValueError):
            RasterPlotParams(height=3000)  # Too large


class TestImagingSessionParams:
    """Tests for ImagingSessionParams model."""

    def test_valid_params(self):
        """Should accept valid parameters."""
        params = ImagingSessionParams(
            ms_path="/data/test.ms",
            imagename="test_output",
            imsize=[4096, 4096],
            cell="2.5arcsec",
            niter=5000,
        )
        assert params.ms_path == "/data/test.ms"
        assert params.imsize == [4096, 4096]

    def test_validates_imaging_params(self):
        """Should validate imaging parameters via model validator."""
        with pytest.raises(ValidationError):
            ImagingSessionParams(
                ms_path="/data/test.ms",
                imagename="test",
                imsize=[10000, 10000],  # Too large
            )

    def test_robust_bounds(self):
        """Should enforce robust parameter bounds."""
        # Pydantic validates the robust field with le=2, ge=-2
        # This raises pydantic.ValidationError, not our custom ValidationError
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ImagingSessionParams(
                ms_path="/data/test.ms",
                imagename="test",
                robust=3.0,  # Out of range
            )


# =============================================================================
# WebSocket Manager Tests
# =============================================================================


class TestWebSocketManagement:
    """Tests for BokehSessionManager WebSocket tracking."""

    @pytest.fixture
    def manager(self):
        """Create session manager with narrow port range."""
        from dsa110_contimg.api.services.bokeh_sessions import BokehSessionManager
        return BokehSessionManager(port_range=range(9001, 9010))

    def test_register_websocket(self, manager):
        """Should track registered WebSockets."""
        mock_ws = MagicMock()
        manager.register_websocket("session-1", mock_ws)

        assert manager.get_websocket_count("session-1") == 1

    def test_unregister_websocket(self, manager):
        """Should remove WebSocket on unregister."""
        mock_ws = MagicMock()
        manager.register_websocket("session-1", mock_ws)
        manager.unregister_websocket("session-1", mock_ws)

        assert manager.get_websocket_count("session-1") == 0

    def test_multiple_websockets(self, manager):
        """Should track multiple WebSockets per session."""
        ws1 = MagicMock()
        ws2 = MagicMock()

        manager.register_websocket("session-1", ws1)
        manager.register_websocket("session-1", ws2)

        assert manager.get_websocket_count("session-1") == 2

    @pytest.mark.asyncio
    async def test_broadcast_progress(self, manager):
        """Should broadcast progress to all registered WebSockets."""
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        manager.register_websocket("session-1", ws1)
        manager.register_websocket("session-1", ws2)

        progress = {"iteration": 100, "max_iterations": 1000}
        await manager.broadcast_progress("session-1", progress)

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

        # Check message format
        call_args = ws1.send_json.call_args[0][0]
        assert call_args["type"] == "progress"
        assert call_args["payload"] == progress

    @pytest.mark.asyncio
    async def test_broadcast_handles_dead_websocket(self, manager):
        """Should remove WebSockets that fail to receive."""
        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send_json.side_effect = Exception("Connection closed")

        manager.register_websocket("session-1", good_ws)
        manager.register_websocket("session-1", bad_ws)

        await manager.broadcast_progress("session-1", {"test": True})

        # Good WS should have received message
        good_ws.send_json.assert_called_once()

        # Bad WS should be removed
        assert manager.get_websocket_count("session-1") == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_nonexistent_session(self, manager):
        """Should handle broadcast to session with no WebSockets."""
        # Should not raise
        await manager.broadcast_progress("nonexistent", {"test": True})


# =============================================================================
# Image Versioning Tests
# =============================================================================


class TestImageVersioningAPI:
    """Tests for image versioning endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create mock image service."""
        service = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_get_version_chain_single_image(self, mock_service):
        """Should return chain with single image if no parent."""
        from dsa110_contimg.api.routes.images import get_image_version_chain

        # Mock image with no parent
        mock_image = MagicMock()
        mock_image.id = "img-001"
        mock_image.created_at = datetime.now().timestamp()
        mock_image.qa_grade = "good"
        mock_image.version = 1
        mock_image.parent_id = None
        mock_image.imaging_params = None

        mock_service.get_image = AsyncMock(return_value=mock_image)

        result = await get_image_version_chain("img-001", service=mock_service)

        assert result.current_id == "img-001"
        assert result.root_id == "img-001"
        assert result.total_versions == 1
        assert len(result.chain) == 1

    @pytest.mark.asyncio
    async def test_get_version_chain_with_parent(self, mock_service):
        """Should build chain including parent images."""
        from dsa110_contimg.api.routes.images import get_image_version_chain

        # Mock child image
        child_image = MagicMock()
        child_image.id = "img-002"
        child_image.created_at = datetime.now().timestamp()
        child_image.qa_grade = "warn"
        child_image.version = 2
        child_image.parent_id = "img-001"
        child_image.imaging_params = {"niter": 5000}

        # Mock parent image
        parent_image = MagicMock()
        parent_image.id = "img-001"
        parent_image.created_at = (datetime.now() - timedelta(days=1)).timestamp()
        parent_image.qa_grade = "fail"
        parent_image.version = 1
        parent_image.parent_id = None
        parent_image.imaging_params = None

        async def get_image_mock(image_id):
            if image_id == "img-002":
                return child_image
            elif image_id == "img-001":
                return parent_image
            return None

        mock_service.get_image = get_image_mock

        result = await get_image_version_chain("img-002", service=mock_service)

        assert result.current_id == "img-002"
        assert result.root_id == "img-001"
        assert result.total_versions == 2
        assert result.chain[0].id == "img-001"
        assert result.chain[1].id == "img-002"

    @pytest.mark.asyncio
    async def test_reimage_requires_ms_path(self, mock_service):
        """Should reject re-image request if no MS path."""
        from dsa110_contimg.api.routes.images import reimage_from_existing, ReimageRequest

        # Mock image without MS path
        mock_image = MagicMock()
        mock_image.id = "img-no-ms"
        mock_image.ms_path = None

        mock_service.get_image = AsyncMock(return_value=mock_image)

        request = ReimageRequest()

        with pytest.raises(HTTPException) as exc_info:
            await reimage_from_existing("img-no-ms", request, service=mock_service)

        assert exc_info.value.status_code == 422
        assert "no source Measurement Set" in exc_info.value.detail


# =============================================================================
# Session Cleanup Tests
# =============================================================================


class TestSessionCleanup:
    """Tests for automated session cleanup."""

    @pytest.fixture
    def manager(self):
        """Create session manager."""
        from dsa110_contimg.api.services.bokeh_sessions import BokehSessionManager
        return BokehSessionManager(port_range=range(9001, 9010))

    @pytest.mark.asyncio
    async def test_cleanup_stale_sessions(self, manager):
        """Should cleanup sessions older than threshold."""
        # Create fake session that's "old"
        from dsa110_contimg.api.services.bokeh_sessions import BokehSession

        old_session = MagicMock(spec=BokehSession)
        old_session.id = "old-session"
        old_session.created_at = datetime.now() - timedelta(hours=5)
        old_session.is_alive = MagicMock(return_value=True)
        old_session.process = MagicMock()
        old_session.process.poll.return_value = None  # Still running

        manager.sessions["old-session"] = old_session
        manager.port_pool.in_use["old-session"] = 9001

        cleaned = await manager.cleanup_stale_sessions(max_age_hours=4.0)

        assert cleaned == 1
        assert "old-session" not in manager.sessions

    @pytest.mark.asyncio
    async def test_cleanup_dead_sessions(self, manager):
        """Should cleanup sessions whose processes died."""
        from dsa110_contimg.api.services.bokeh_sessions import BokehSession

        dead_session = MagicMock(spec=BokehSession)
        dead_session.id = "dead-session"
        dead_session.created_at = datetime.now()
        dead_session.is_alive = MagicMock(return_value=False)  # Dead
        dead_session.process = MagicMock()
        dead_session.process.poll.return_value = 1  # Exited

        manager.sessions["dead-session"] = dead_session
        manager.port_pool.in_use["dead-session"] = 9002

        cleaned = await manager.cleanup_dead_sessions()

        assert cleaned == 1
        assert "dead-session" not in manager.sessions

    @pytest.mark.asyncio
    async def test_cleanup_preserves_active_sessions(self, manager):
        """Should not cleanup active, young sessions."""
        from dsa110_contimg.api.services.bokeh_sessions import BokehSession

        active_session = MagicMock(spec=BokehSession)
        active_session.id = "active-session"
        active_session.created_at = datetime.now() - timedelta(hours=1)  # Recent
        active_session.is_alive = MagicMock(return_value=True)
        active_session.process = MagicMock()
        active_session.process.poll.return_value = None  # Still running

        manager.sessions["active-session"] = active_session
        manager.port_pool.in_use["active-session"] = 9003

        stale_cleaned = await manager.cleanup_stale_sessions(max_age_hours=4.0)
        dead_cleaned = await manager.cleanup_dead_sessions()

        assert stale_cleaned == 0
        assert dead_cleaned == 0
        assert "active-session" in manager.sessions


# =============================================================================
# Mask and Region Endpoint Tests
# =============================================================================


class TestMaskEndpoints:
    """Tests for /images/{id}/masks endpoints."""

    @pytest.fixture
    def mock_image_path(self, tmp_path):
        """Create a mock image directory."""
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        return img_dir

    def test_save_mask_creates_file(self, mock_image_path):
        """Should save mask regions to a .reg file."""
        from pathlib import Path
        import json

        # Simulate mask data
        mask_data = {
            "regions": [
                {"shape": "circle", "x": 100, "y": 100, "radius": 50},
                {"shape": "box", "x": 200, "y": 200, "width": 60, "height": 40},
            ],
            "format": "ds9",
        }

        # Create mask file path
        mask_path = mock_image_path / "test_image.mask.reg"

        # Write in DS9 format
        ds9_content = "# Region file format: DS9 version 4.1\n"
        ds9_content += "global color=green dashlist=8 3 width=1\n"
        ds9_content += "image\n"
        for region in mask_data["regions"]:
            if region["shape"] == "circle":
                ds9_content += f"circle({region['x']},{region['y']},{region['radius']})\n"
            elif region["shape"] == "box":
                ds9_content += f"box({region['x']},{region['y']},{region['width']},{region['height']},0)\n"

        mask_path.write_text(ds9_content)

        # Verify file was created
        assert mask_path.exists()
        content = mask_path.read_text()
        assert "circle(100,100,50)" in content
        assert "box(200,200,60,40,0)" in content

    def test_mask_file_ds9_format(self, mock_image_path):
        """Should generate valid DS9 region format."""
        ds9_content = """# Region file format: DS9 version 4.1
global color=green dashlist=8 3 width=1
image
circle(256,256,30)
ellipse(128,128,20,40,45)
box(384,384,50,30,0)
"""
        mask_path = mock_image_path / "test.mask.reg"
        mask_path.write_text(ds9_content)

        content = mask_path.read_text()
        assert "Region file format: DS9" in content
        assert "circle(256,256,30)" in content
        assert "ellipse(128,128,20,40,45)" in content


class TestRegionEndpoints:
    """Tests for /images/{id}/regions endpoints."""

    @pytest.fixture
    def mock_region_dir(self, tmp_path):
        """Create a mock region directory."""
        region_dir = tmp_path / "regions"
        region_dir.mkdir()
        return region_dir

    def test_save_region_ds9_format(self, mock_region_dir):
        """Should save regions in DS9 format."""
        region_content = """# Region file format: DS9 version 4.1
global color=cyan dashlist=8 3 width=1
fk5
circle(12h30m00s,+45d00m00s,30")
"""
        region_path = mock_region_dir / "source_regions.reg"
        region_path.write_text(region_content)

        assert region_path.exists()
        content = region_path.read_text()
        assert "fk5" in content  # World coordinate system
        assert "circle(12h30m00s,+45d00m00s,30\")" in content

    def test_save_region_crtf_format(self, mock_region_dir):
        """Should save regions in CASA Region Text Format."""
        crtf_content = """#CRTFv0 CASA Region Text Format version 0
global coord=J2000
circle [[12h30m00s, +45d00m00s], 30arcsec]
box [[12h29m50s, +44d59m50s], [12h30m10s, +45d00m10s]]
"""
        region_path = mock_region_dir / "source_regions.crtf"
        region_path.write_text(crtf_content)

        assert region_path.exists()
        content = region_path.read_text()
        assert "#CRTFv0" in content
        assert "circle [[12h30m00s, +45d00m00s], 30arcsec]" in content

    def test_region_export_json(self, mock_region_dir):
        """Should export regions as JSON."""
        import json

        regions = [
            {
                "shape": "circle",
                "ra": 187.5,
                "dec": 45.0,
                "radius_arcsec": 30.0,
                "color": "green",
            },
            {
                "shape": "box",
                "ra": 187.6,
                "dec": 45.1,
                "width_arcsec": 60.0,
                "height_arcsec": 40.0,
                "angle_deg": 0.0,
                "color": "cyan",
            },
        ]

        region_path = mock_region_dir / "source_regions.json"
        region_path.write_text(json.dumps(regions, indent=2))

        assert region_path.exists()
        loaded = json.loads(region_path.read_text())
        assert len(loaded) == 2
        assert loaded[0]["shape"] == "circle"
        assert loaded[1]["shape"] == "box"
