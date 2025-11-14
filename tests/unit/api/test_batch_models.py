"""Unit tests for batch job API models.

Focus: Fast validation tests for batch conversion, publishing, and photometry models.
"""

from __future__ import annotations

from typing import Tuple

import pytest
from pydantic import ValidationError

from dsa110_contimg.api.models import (
    BatchConversionParams,
    BatchPublishParams,
    Coordinate,
    PhotometryMeasureBatchRequest,
    PhotometryMeasureRequest,
    PhotometryResult,
    TimeWindow,
)

# Rebuild models to resolve forward references
PhotometryMeasureRequest.model_rebuild()
PhotometryMeasureBatchRequest.model_rebuild()


class TestTimeWindow:
    """Test TimeWindow model."""

    def test_valid_time_window(self):
        """Test valid TimeWindow creation."""
        tw = TimeWindow(
            start_time="2025-11-12T10:00:00",
            end_time="2025-11-12T10:50:00",
        )
        assert tw.start_time == "2025-11-12T10:00:00"
        assert tw.end_time == "2025-11-12T10:50:00"

    def test_time_window_required_fields(self):
        """Test TimeWindow requires both start_time and end_time."""
        with pytest.raises(ValidationError):
            TimeWindow(start_time="2025-11-12T10:00:00")


class TestBatchConversionParams:
    """Test BatchConversionParams model."""

    def test_valid_batch_conversion_params(self):
        """Test valid BatchConversionParams creation."""
        from dsa110_contimg.api.models import ConversionJobParams

        params = BatchConversionParams(
            time_windows=[
                TimeWindow(
                    start_time="2025-11-12T10:00:00",
                    end_time="2025-11-12T10:50:00",
                )
            ],
            params=ConversionJobParams(
                input_dir="/data/incoming",
                output_dir="/stage/ms",
                start_time="2025-11-12T10:00:00",
                end_time="2025-11-12T10:50:00",
            ),
        )
        assert len(params.time_windows) == 1
        assert params.params is not None

    def test_batch_conversion_params_empty_windows(self):
        """Test BatchConversionParams with empty time_windows."""
        from dsa110_contimg.api.models import ConversionJobParams

        params = BatchConversionParams(
            time_windows=[],
            params=ConversionJobParams(
                input_dir="/data/incoming",
                output_dir="/stage/ms",
                start_time="2025-11-12T10:00:00",
                end_time="2025-11-12T10:50:00",
            ),
        )
        assert len(params.time_windows) == 0


class TestBatchPublishParams:
    """Test BatchPublishParams model."""

    def test_valid_batch_publish_params(self):
        """Test valid BatchPublishParams creation."""
        params = BatchPublishParams(
            data_ids=["mosaic_001", "mosaic_002"],
            products_base="/data/products",
        )
        assert len(params.data_ids) == 2
        assert params.products_base == "/data/products"

    def test_batch_publish_params_no_base(self):
        """Test BatchPublishParams without products_base."""
        params = BatchPublishParams(data_ids=["mosaic_001"])
        assert len(params.data_ids) == 1
        assert params.products_base is None

    def test_batch_publish_params_empty_ids(self):
        """Test BatchPublishParams with empty data_ids."""
        params = BatchPublishParams(data_ids=[])
        assert len(params.data_ids) == 0


class TestCoordinate:
    """Test Coordinate model."""

    def test_valid_coordinate(self):
        """Test valid Coordinate creation."""
        coord = Coordinate(ra_deg=123.456, dec_deg=-45.678)
        assert coord.ra_deg == 123.456
        assert coord.dec_deg == -45.678

    def test_coordinate_required_fields(self):
        """Test Coordinate requires both ra_deg and dec_deg."""
        with pytest.raises(ValidationError):
            Coordinate(ra_deg=123.456)


class TestPhotometryMeasureRequest:
    """Test PhotometryMeasureRequest model."""

    def test_valid_photometry_request(self):
        """Test valid PhotometryMeasureRequest creation."""
        req = PhotometryMeasureRequest(
            fits_path="/path/to/image.fits",
            ra_deg=123.456,
            dec_deg=-45.678,
        )
        assert req.fits_path == "/path/to/image.fits"
        assert req.ra_deg == 123.456
        assert req.dec_deg == -45.678
        assert req.box_size_pix == 5  # default
        assert req.use_aegean is False  # default

    def test_photometry_request_with_options(self):
        """Test PhotometryMeasureRequest with all options."""
        req = PhotometryMeasureRequest(
            fits_path="/path/to/image.fits",
            ra_deg=123.456,
            dec_deg=-45.678,
            box_size_pix=10,
            annulus_pix=(15, 25),
            use_aegean=True,
            aegean_prioritized=True,
        )
        assert req.box_size_pix == 10
        assert req.annulus_pix == (15, 25)
        assert req.use_aegean is True
        assert req.aegean_prioritized is True


class TestPhotometryMeasureBatchRequest:
    """Test PhotometryMeasureBatchRequest model."""

    def test_valid_batch_request(self):
        """Test valid PhotometryMeasureBatchRequest creation."""
        req = PhotometryMeasureBatchRequest(
            fits_path="/path/to/image.fits",
            coordinates=[
                Coordinate(ra_deg=123.456, dec_deg=-45.678),
                Coordinate(ra_deg=124.456, dec_deg=-46.678),
            ],
        )
        assert req.fits_path == "/path/to/image.fits"
        assert len(req.coordinates) == 2
        assert req.coordinates[0].ra_deg == 123.456

    def test_batch_request_empty_coords(self):
        """Test PhotometryMeasureBatchRequest with empty coordinates."""
        req = PhotometryMeasureBatchRequest(
            fits_path="/path/to/image.fits",
            coordinates=[],
        )
        assert len(req.coordinates) == 0


class TestPhotometryResult:
    """Test PhotometryResult model."""

    def test_valid_result(self):
        """Test valid PhotometryResult creation."""
        result = PhotometryResult(
            ra_deg=123.456,
            dec_deg=-45.678,
            peak_jyb=1.23,
            peak_err_jyb=0.05,
            success=True,
            method="peak",
        )
        assert result.ra_deg == 123.456
        assert result.peak_jyb == 1.23
        assert result.success is True

    def test_result_with_error(self):
        """Test PhotometryResult with error."""
        result = PhotometryResult(
            ra_deg=123.456,
            dec_deg=-45.678,
            success=False,
            error_message="Measurement failed",
            method="peak",
        )
        assert result.success is False
        assert result.error_message == "Measurement failed"
