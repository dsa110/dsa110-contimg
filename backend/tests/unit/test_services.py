"""
Tests for service layer classes.
"""

import pytest
from dataclasses import dataclass
from typing import Optional, List
from unittest.mock import MagicMock, patch


# Mock record types for testing
@dataclass
class MockImageRecord:
    id: str = "img-001"
    run_id: str = "run-001"
    ms_path: str = "/data/test.ms"
    qa_grade: str = "A"
    qa_summary: str = "Good quality"
    noise_jy: float = 0.001
    dynamic_range: float = 500.0
    beam_major_arcsec: float = 5.0
    beam_minor_arcsec: float = 4.0
    beam_pa_deg: float = 45.0
    qa_metrics: Optional[dict] = None
    qa_flags: Optional[List[dict]] = None
    qa_timestamp: Optional[float] = None


@dataclass
class MockMSRecord:
    path: str = "/data/test.ms"
    qa_grade: str = "B"
    qa_summary: str = "Acceptable"
    stage: str = "calibrated"
    status: str = "completed"
    cal_applied: int = 1
    qa_metrics: Optional[dict] = None
    qa_flags: Optional[List[dict]] = None
    qa_timestamp: Optional[float] = None


@dataclass
class MockJobRecord:
    run_id: str = "run-001"
    qa_grade: str = "A"
    qa_summary: str = "Successful"
    input_ms_path: str = "/data/input.ms"
    cal_table_path: str = "/data/cal.tbl"
    output_image_id: str = "img-001"
    qa_flags: Optional[List[dict]] = None
    queue_status: Optional[str] = None
    config: Optional[dict] = None


@dataclass
class MockSourceRecord:
    id: str = "src-001"
    name: str = "Test Source"


class TestQAService:
    """Tests for QAService."""
    
    @pytest.fixture
    def qa_service(self):
        from dsa110_contimg.api.services.qa_service import QAService
        return QAService()
    
    def test_build_image_qa_returns_dict(self, qa_service):
        """Test that build_image_qa returns a dictionary."""
        image = MockImageRecord()
        result = qa_service.build_image_qa(image)
        assert isinstance(result, dict)
    
    def test_build_image_qa_has_required_fields(self, qa_service):
        """Test that image QA contains required fields."""
        image = MockImageRecord()
        result = qa_service.build_image_qa(image)

        assert "image_id" in result
        assert "qa_grade" in result
        assert "qa_summary" in result
        assert "quality_metrics" in result

    def test_build_image_qa_metrics_structure(self, qa_service):
        """Test metrics structure in image QA."""
        image = MockImageRecord()
        result = qa_service.build_image_qa(image)

        metrics = result["quality_metrics"]
        assert "rms_noise" in metrics
        assert "dynamic_range" in metrics
        assert "beam_major_arcsec" in metrics
        assert "beam_minor_arcsec" in metrics
        assert "beam_pa_deg" in metrics

    def test_build_image_qa_uses_image_values(self, qa_service):
        """Test that QA uses actual image values."""
        image = MockImageRecord(
            id="custom-id",
            qa_grade="C",
            noise_jy=0.005
        )
        result = qa_service.build_image_qa(image)

        assert result["image_id"] == "custom-id"
        assert result["qa_grade"] == "C"
        assert result["quality_metrics"]["rms_noise"] == 0.005

    def test_build_ms_qa_returns_dict(self, qa_service):
        """Test that build_ms_qa returns a dictionary."""
        ms = MockMSRecord()
        result = qa_service.build_ms_qa(ms)
        assert isinstance(result, dict)
    
    def test_build_ms_qa_has_required_fields(self, qa_service):
        """Test that MS QA contains required fields."""
        ms = MockMSRecord()
        result = qa_service.build_ms_qa(ms)
        
        assert "ms_path" in result
        assert "qa_grade" in result
        assert "qa_summary" in result
        assert "stage" in result
        assert "status" in result
        assert "cal_applied" in result
    
    def test_build_ms_qa_cal_applied_boolean(self, qa_service):
        """Test cal_applied is converted to boolean."""
        ms = MockMSRecord(cal_applied=1)
        result = qa_service.build_ms_qa(ms)
        assert result["cal_applied"] is True
        
        ms_uncal = MockMSRecord(cal_applied=0)
        result_uncal = qa_service.build_ms_qa(ms_uncal)
        assert result_uncal["cal_applied"] is False
    
    def test_build_job_qa_returns_dict(self, qa_service):
        """Test that build_job_qa returns a dictionary."""
        job = MockJobRecord()
        result = qa_service.build_job_qa(job)
        assert isinstance(result, dict)
    
    def test_build_job_qa_has_required_fields(self, qa_service):
        """Test that job QA contains required fields."""
        job = MockJobRecord()
        result = qa_service.build_job_qa(job)
        
        assert "run_id" in result
        assert "qa_grade" in result
        assert "qa_summary" in result
        assert "ms_path" in result
        assert "cal_table" in result


class TestImageService:
    """Tests for AsyncImageService (sync utility methods)."""
    
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()
    
    @pytest.fixture
    def image_service(self, mock_repo):
        from dsa110_contimg.api.services.async_services import AsyncImageService
        return AsyncImageService(repository=mock_repo)
    
    @pytest.mark.asyncio
    async def test_get_image_calls_repo(self, image_service, mock_repo):
        """Test get_image delegates to repository."""
        from unittest.mock import AsyncMock
        mock_repo.get_by_id = AsyncMock(return_value=MockImageRecord())
        _ = await image_service.get_image("img-001")
        mock_repo.get_by_id.assert_called_once_with("img-001")

    @pytest.mark.asyncio
    async def test_list_images_calls_repo(self, image_service, mock_repo):
        """Test list_images delegates to repository."""
        from unittest.mock import AsyncMock
        mock_repo.list_all = AsyncMock(return_value=[MockImageRecord()])
        _ = await image_service.list_images(limit=50, offset=10)
        mock_repo.list_all.assert_called_once_with(limit=50, offset=10)
    
    def test_build_provenance_links_structure(self, image_service):
        """Test provenance links structure."""
        image = MockImageRecord()
        result = image_service.build_provenance_links(image)
        
        assert "logs_url" in result
        assert "qa_url" in result
        assert "ms_url" in result
        assert "image_url" in result
    
    def test_build_provenance_links_with_run_id(self, image_service):
        """Test provenance links contain run_id."""
        image = MockImageRecord(run_id="run-123")
        result = image_service.build_provenance_links(image)
        
        assert "/api/logs/run-123" in result["logs_url"]
    
    def test_build_provenance_links_no_run_id(self, image_service):
        """Test provenance links handle missing run_id."""
        image = MockImageRecord(run_id=None)
        result = image_service.build_provenance_links(image)
        
        assert result["logs_url"] is None
    
    def test_build_provenance_links_no_ms_path(self, image_service):
        """Test provenance links handle missing ms_path."""
        image = MockImageRecord(ms_path=None)
        result = image_service.build_provenance_links(image)
        
        assert result["ms_url"] is None
    
    def test_build_qa_report_structure(self, image_service):
        """Test QA report structure."""
        image = MockImageRecord()
        result = image_service.build_qa_report(image)
        
        assert "image_id" in result
        assert "qa_grade" in result
        assert "quality_metrics" in result
        assert "beam" in result
        assert "warnings" in result
    
    def test_build_qa_report_high_noise_warning(self, image_service):
        """Test QA report warns on high noise."""
        image = MockImageRecord(noise_jy=0.02)  # 20 mJy > 10 mJy threshold
        result = image_service.build_qa_report(image)
        
        assert "High noise level detected" in result["warnings"]
    
    def test_build_qa_report_low_dr_warning(self, image_service):
        """Test QA report warns on low dynamic range."""
        image = MockImageRecord(dynamic_range=50)  # < 100 threshold
        result = image_service.build_qa_report(image)
        
        assert "Low dynamic range" in result["warnings"]
    
    def test_build_qa_report_no_warnings(self, image_service):
        """Test QA report has no warnings for good image."""
        image = MockImageRecord(noise_jy=0.001, dynamic_range=500)
        result = image_service.build_qa_report(image)
        
        assert len(result["warnings"]) == 0


class TestSourceService:
    """Tests for AsyncSourceService (sync utility methods)."""
    
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()
    
    @pytest.fixture
    def source_service(self, mock_repo):
        from dsa110_contimg.api.services.async_services import AsyncSourceService
        return AsyncSourceService(repository=mock_repo)
    
    def test_get_source_calls_repo(self, source_service, mock_repo):
        """Test get_source delegates to repository."""
        mock_repo.get_by_id.return_value = MockSourceRecord()
        source_service.get_source("src-001")
        mock_repo.get_by_id.assert_called_once_with("src-001")
    
    def test_list_sources_calls_repo(self, source_service, mock_repo):
        """Test list_sources delegates to repository."""
        mock_repo.list_all.return_value = [MockSourceRecord()]
        source_service.list_sources(limit=25, offset=5)
        mock_repo.list_all.assert_called_once_with(limit=25, offset=5)
    
    def test_get_lightcurve_calls_repo(self, source_service, mock_repo):
        """Test get_lightcurve delegates to repository."""
        mock_repo.get_lightcurve.return_value = []
        source_service.get_lightcurve("src-001", start_mjd=59000.0, end_mjd=60000.0)
        mock_repo.get_lightcurve.assert_called_once_with("src-001", 59000.0, 60000.0)
    
    def test_calculate_variability_insufficient_epochs(self, source_service):
        """Test variability with insufficient epochs."""
        source = MockSourceRecord()
        epochs = [{"flux_jy": 1.0}]  # Only 1 epoch
        
        result = source_service.calculate_variability(source, epochs)
        
        assert result["variability_index"] is None
        assert "Insufficient epochs" in result.get("message", "")
    
    def test_calculate_variability_no_epochs(self, source_service):
        """Test variability with no epochs."""
        source = MockSourceRecord()
        epochs = []
        
        result = source_service.calculate_variability(source, epochs)
        
        assert result["n_epochs"] == 0
        assert result["variability_index"] is None
    
    def test_calculate_variability_with_epochs(self, source_service):
        """Test variability calculation with valid epochs."""
        source = MockSourceRecord()
        epochs = [
            {"flux_jy": 1.0, "flux_err_jy": 0.1},
            {"flux_jy": 1.2, "flux_err_jy": 0.1},
            {"flux_jy": 0.8, "flux_err_jy": 0.1},
        ]
        
        result = source_service.calculate_variability(source, epochs)
        
        assert result["n_epochs"] == 3
        assert result["variability_index"] is not None
        assert result["flux_stats"] is not None
    
    def test_calculate_variability_variable_source(self, source_service):
        """Test variability detects variable source."""
        source = MockSourceRecord()
        # High variance: std/mean will be > 0.1
        epochs = [
            {"flux_jy": 0.5},
            {"flux_jy": 1.5},
        ]
        
        result = source_service.calculate_variability(source, epochs)
        
        # std = 0.707, mean = 1.0, V = 0.707 > 0.1
        assert result["is_variable"] is True
    
    def test_calculate_variability_stable_source(self, source_service):
        """Test variability detects stable source."""
        source = MockSourceRecord()
        # Low variance: std/mean will be < 0.1
        epochs = [
            {"flux_jy": 1.0},
            {"flux_jy": 1.01},
        ]
        
        result = source_service.calculate_variability(source, epochs)
        
        assert result["is_variable"] is False
    
    def test_calculate_variability_flux_stats(self, source_service):
        """Test flux statistics are calculated correctly."""
        source = MockSourceRecord()
        epochs = [
            {"flux_jy": 1.0},
            {"flux_jy": 2.0},
            {"flux_jy": 3.0},
        ]
        
        result = source_service.calculate_variability(source, epochs)
        stats = result["flux_stats"]
        
        assert stats["mean_jy"] == 2.0
        assert stats["min_jy"] == 1.0
        assert stats["max_jy"] == 3.0
    
    def test_calculate_variability_chi_squared(self, source_service):
        """Test chi-squared is calculated when errors present."""
        source = MockSourceRecord()
        epochs = [
            {"flux_jy": 1.0, "flux_err_jy": 0.1},
            {"flux_jy": 1.5, "flux_err_jy": 0.1},
            {"flux_jy": 2.0, "flux_err_jy": 0.1},
        ]
        
        result = source_service.calculate_variability(source, epochs)
        
        assert result["chi_squared"] is not None
        assert result["chi_squared_reduced"] is not None


class TestJobService:
    """Tests for AsyncJobService (sync utility methods)."""
    
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()
    
    @pytest.fixture
    def job_service(self, mock_repo):
        from dsa110_contimg.api.services.async_services import AsyncJobService
        return AsyncJobService(repository=mock_repo)
    
    def test_get_job_calls_repo(self, job_service, mock_repo):
        """Test get_job delegates to repository."""
        mock_repo.get_by_run_id.return_value = MockJobRecord()
        job_service.get_job("run-001")
        mock_repo.get_by_run_id.assert_called_once_with("run-001")
    
    def test_list_jobs_calls_repo(self, job_service, mock_repo):
        """Test list_jobs delegates to repository."""
        mock_repo.list_all.return_value = [MockJobRecord()]
        job_service.list_jobs(limit=20, offset=0)
        mock_repo.list_all.assert_called_once_with(limit=20, offset=0)
    
    def test_get_job_status_completed(self, job_service):
        """Test status is completed when qa_grade exists."""
        job = MockJobRecord(qa_grade="A")
        status = job_service.get_job_status(job)
        assert status == "completed"
    
    def test_get_job_status_pending(self, job_service):
        """Test status is pending when no qa_grade."""
        job = MockJobRecord(qa_grade=None)
        status = job_service.get_job_status(job)
        assert status == "pending"
    
    def test_build_provenance_links_structure(self, job_service):
        """Test provenance links structure."""
        job = MockJobRecord()
        result = job_service.build_provenance_links(job)
        
        assert "logs_url" in result
        assert "qa_url" in result
        assert "ms_url" in result
        assert "image_url" in result
    
    def test_build_provenance_links_values(self, job_service):
        """Test provenance links contain correct values."""
        job = MockJobRecord(
            run_id="run-123",
            output_image_id="img-456"
        )
        result = job_service.build_provenance_links(job)
        
        assert "/api/logs/run-123" in result["logs_url"]
        assert "/api/qa/job/run-123" in result["qa_url"]
        assert "/api/images/img-456" in result["image_url"]
    
    def test_build_provenance_links_no_ms_path(self, job_service):
        """Test provenance links handle missing ms_path."""
        job = MockJobRecord(input_ms_path=None)
        result = job_service.build_provenance_links(job)
        
        assert result["ms_url"] is None
    
    def test_build_provenance_links_no_output_image(self, job_service):
        """Test provenance links handle missing output image."""
        job = MockJobRecord(output_image_id=None)
        result = job_service.build_provenance_links(job)
        
        assert result["image_url"] is None
    
    def test_find_log_file_not_found(self, job_service):
        """Test find_log_file returns None when not found."""
        result = job_service.find_log_file("nonexistent-run")
        assert result is None
    
    @patch('pathlib.Path.exists')
    def test_find_log_file_found(self, mock_exists, job_service):
        """Test find_log_file returns path when found."""
        mock_exists.return_value = True
        result = job_service.find_log_file("run-123")
        assert result is not None
    
    def test_read_log_tail_not_found(self, job_service):
        """Test read_log_tail handles missing log file."""
        result = job_service.read_log_tail("nonexistent-run")
        
        assert "error" in result
        assert result["logs"] == []


class TestMSService:
    """Tests for AsyncMSService (sync utility methods)."""
    
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()
    
    @pytest.fixture
    def ms_service(self, mock_repo):
        from dsa110_contimg.api.services.async_services import AsyncMSService
        return AsyncMSService(repository=mock_repo)
    
    def test_get_metadata_calls_repo(self, ms_service, mock_repo):
        """Test get_metadata delegates to repository."""
        mock_repo.get_metadata.return_value = MockMSRecord()
        ms_service.get_metadata("/data/test.ms")
        mock_repo.get_metadata.assert_called_once_with("/data/test.ms")
    
    def test_get_pointing_prefers_explicit(self, ms_service):
        """Test get_pointing prefers explicit pointing over derived."""
        ms = MagicMock()
        ms.pointing_ra_deg = 10.0
        ms.pointing_dec_deg = 20.0
        ms.ra_deg = 1.0
        ms.dec_deg = 2.0
        
        ra, dec = ms_service.get_pointing(ms)
        assert ra == 10.0
        assert dec == 20.0
    
    def test_get_pointing_falls_back_to_derived(self, ms_service):
        """Test get_pointing falls back to derived coordinates."""
        ms = MagicMock()
        ms.pointing_ra_deg = None
        ms.pointing_dec_deg = None
        ms.ra_deg = 1.0
        ms.dec_deg = 2.0
        
        ra, dec = ms_service.get_pointing(ms)
        assert ra == 1.0
        assert dec == 2.0
    
    def test_get_primary_cal_table_with_tables(self, ms_service):
        """Test get_primary_cal_table returns first table."""
        ms = MagicMock()
        ms.calibrator_tables = [
            {"cal_table": "/data/cal1.tbl"},
            {"cal_table": "/data/cal2.tbl"},
        ]
        
        result = ms_service.get_primary_cal_table(ms)
        assert result == "/data/cal1.tbl"
    
    def test_get_primary_cal_table_empty(self, ms_service):
        """Test get_primary_cal_table handles empty list."""
        ms = MagicMock()
        ms.calibrator_tables = []
        
        result = ms_service.get_primary_cal_table(ms)
        assert result is None
    
    def test_get_primary_cal_table_none(self, ms_service):
        """Test get_primary_cal_table handles None."""
        ms = MagicMock()
        ms.calibrator_tables = None
        
        result = ms_service.get_primary_cal_table(ms)
        assert result is None
    
    def test_build_provenance_links_structure(self, ms_service):
        """Test provenance links structure."""
        ms = MagicMock()
        ms.path = "/data/test.ms"
        ms.run_id = "run-001"
        ms.imagename = "image-001"
        
        result = ms_service.build_provenance_links(ms)
        
        assert "logs_url" in result
        assert "qa_url" in result
        assert "ms_url" in result
        assert "image_url" in result
