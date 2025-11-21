"""Unit tests for unified QA CLI.

Tests the QA CLI commands with focus on:
- Fast execution (mocked QA functions)
- Accurate targeting of CLI functionality
- Error handling and validation
"""

from unittest.mock import MagicMock, patch

from dsa110_contimg.qa.cli import cmd_calibration, cmd_image, cmd_mosaic, cmd_report


class TestCalibrationQA:
    """Test calibration QA command."""

    @patch("dsa110_contimg.qa.casa_ms_qa.generate_plots")
    @patch("dsa110_contimg.qa.casa_ms_qa.vis_statistics")
    @patch("dsa110_contimg.qa.casa_ms_qa.flag_summary")
    @patch("dsa110_contimg.qa.casa_ms_qa.listobs_dump")
    @patch("dsa110_contimg.qa.casa_ms_qa.inventory_and_provenance")
    @patch("dsa110_contimg.qa.casa_ms_qa.structural_validation")
    def test_calibration_qa_success(
        self,
        mock_plots,
        mock_vis_stats,
        mock_flag,
        mock_listobs,
        mock_inventory,
        mock_structural,
        tmp_path,
    ):
        """Test successful calibration QA execution."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()  # MS is a directory
        output_dir = tmp_path / "qa"

        mock_structural.return_value = {"status": "ok"}
        mock_inventory.return_value = str(output_dir / "inventory.json")
        mock_listobs.return_value = str(output_dir / "listobs.txt")
        mock_flag.return_value = str(output_dir / "flag_summary.json")
        mock_vis_stats.return_value = {"DATA": "stats.json"}
        mock_plots.return_value = ["plot1.png"]

        args = MagicMock()
        args.ms_path = str(ms_path)
        args.output_dir = str(output_dir)
        args.check_caltables = False
        args.skip_plots = False

        result = cmd_calibration(args)

        assert result == 0
        mock_structural.assert_called_once()
        mock_inventory.assert_called_once()
        mock_listobs.assert_called_once()
        mock_flag.assert_called_once()
        mock_vis_stats.assert_called_once()
        mock_plots.assert_called_once()

    def test_calibration_qa_missing_ms(self, tmp_path):
        """Test calibration QA with missing MS path."""
        args = MagicMock()
        args.ms_path = str(tmp_path / "nonexistent.ms")
        args.output_dir = None
        args.check_caltables = False
        args.skip_plots = False

        result = cmd_calibration(args)

        assert result == 1

    @patch("dsa110_contimg.qa.casa_ms_qa.structural_validation")
    def test_calibration_qa_exception_handling(self, mock_structural, tmp_path):
        """Test exception handling in calibration QA."""
        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()
        output_dir = tmp_path / "qa"

        mock_structural.side_effect = Exception("Test error")

        args = MagicMock()
        args.ms_path = str(ms_path)
        args.output_dir = str(output_dir)
        args.check_caltables = False
        args.skip_plots = False

        result = cmd_calibration(args)

        assert result == 1


class TestImageQA:
    """Test image QA command."""

    @patch("dsa110_contimg.qa.catalog_validation.validate_flux_scale")
    def test_image_qa_success(self, mock_validate, tmp_path):
        """Test successful image QA execution."""
        image_path = tmp_path / "test.fits"
        image_path.touch()
        output_dir = tmp_path / "qa"

        from dsa110_contimg.qa.catalog_validation import CatalogValidationResult

        mock_result = CatalogValidationResult(
            validation_type="flux_scale",
            image_path=str(image_path),
            catalog_used="nvss",
            n_matched=10,
            n_catalog=100,
            n_detected=50,
            mean_flux_ratio=1.0,
            rms_flux_ratio=0.1,
            flux_scale_error=0.05,
            has_issues=False,
            has_warnings=False,
            issues=[],
            warnings=[],
        )
        mock_validate.return_value = mock_result

        args = MagicMock()
        args.image_path = str(image_path)
        args.output_dir = str(output_dir)
        args.validate_flux_scale = True
        args.catalog = "nvss"
        args.min_snr = 5.0
        args.min_flux = 0.01
        args.max_flux = 10.0
        args.max_flux_error = 0.2

        result = cmd_image(args)

        assert result == 0
        mock_validate.assert_called_once()

    def test_image_qa_missing_image(self, tmp_path):
        """Test image QA with missing image path."""
        args = MagicMock()
        args.image_path = str(tmp_path / "nonexistent.fits")
        args.output_dir = None
        args.validate_flux_scale = False

        result = cmd_image(args)

        # If validate_flux_scale is False, function returns early with 0
        # But if image doesn't exist, it checks first and returns 1
        assert result == 1  # Returns 1 if image path doesn't exist

    @patch("dsa110_contimg.qa.catalog_validation.validate_flux_scale")
    def test_image_qa_with_issues(self, mock_validate, tmp_path):
        """Test image QA with validation issues."""
        image_path = tmp_path / "test.fits"
        image_path.touch()
        output_dir = tmp_path / "qa"

        from dsa110_contimg.qa.catalog_validation import CatalogValidationResult

        mock_result = CatalogValidationResult(
            validation_type="flux_scale",
            image_path=str(image_path),
            catalog_used="nvss",
            n_matched=10,
            n_catalog=100,
            n_detected=50,
            mean_flux_ratio=1.0,
            rms_flux_ratio=0.1,
            flux_scale_error=0.05,
            has_issues=True,
            has_warnings=False,
            issues=["Flux scale error too high"],
            warnings=[],
        )
        mock_validate.return_value = mock_result

        args = MagicMock()
        args.image_path = str(image_path)
        args.output_dir = str(output_dir)
        args.validate_flux_scale = True
        args.catalog = "nvss"
        args.min_snr = 5.0
        args.min_flux = 0.01
        args.max_flux = 10.0
        args.max_flux_error = 0.2

        result = cmd_image(args)

        assert result == 1  # Should return 1 when issues detected


class TestMosaicQA:
    """Test mosaic QA command."""

    @patch("dsa110_contimg.mosaic.validation.validate_tiles_consistency")
    @patch("dsa110_contimg.mosaic.validation.validate_tile_quality")
    def test_mosaic_qa_success(self, mock_consistency, mock_tile_quality, tmp_path):
        """Test successful mosaic QA execution."""
        products_db = tmp_path / "products.sqlite3"
        mosaic_path = tmp_path / "mosaic.fits"
        mosaic_path.touch()
        output_dir = tmp_path / "qa"

        # Mock database
        import sqlite3

        conn = sqlite3.connect(str(products_db))
        conn.execute(
            """
            CREATE TABLE mosaics (
                id TEXT PRIMARY KEY,
                path TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO mosaics (id, path) VALUES (?, ?)",
            ("mosaic_test", str(mosaic_path)),
        )
        conn.commit()
        conn.close()

        mock_tile_quality.return_value = MagicMock(model_dump=lambda: {"status": "ok"})
        mock_consistency.return_value = MagicMock(model_dump=lambda: {"status": "ok"})

        args = MagicMock()
        args.mosaic_id = "mosaic_test"
        args.products_db = str(products_db)
        args.output_dir = str(output_dir)
        args.check_astrometry = False
        args.check_calibration = False
        args.check_primary_beam = False

        result = cmd_mosaic(args)

        assert result == 0
        mock_tile_quality.assert_called_once()
        mock_consistency.assert_called_once()

    def test_mosaic_qa_not_found(self, tmp_path):
        """Test mosaic QA with non-existent mosaic."""
        products_db = tmp_path / "products.sqlite3"

        import sqlite3

        conn = sqlite3.connect(str(products_db))
        conn.execute(
            """
            CREATE TABLE mosaics (
                id TEXT PRIMARY KEY,
                path TEXT
            )
            """
        )
        conn.commit()
        conn.close()

        args = MagicMock()
        args.mosaic_id = "nonexistent"
        args.products_db = str(products_db)
        args.output_dir = None
        args.check_astrometry = False
        args.check_calibration = False
        args.check_primary_beam = False

        result = cmd_mosaic(args)

        assert result == 1


class TestReportQA:
    """Test comprehensive QA report command."""

    @patch("dsa110_contimg.qa.cli.cmd_calibration")
    @patch("dsa110_contimg.database.data_registry.get_data")
    def test_report_qa_for_ms(self, mock_get_data, mock_calibration, tmp_path):
        """Test QA report generation for MS data."""
        from dsa110_contimg.database.data_registry import DataRecord

        ms_path = tmp_path / "test.ms"
        ms_path.mkdir()

        mock_record = DataRecord(
            id=1,
            data_id="ms_test",
            data_type="ms",
            base_path=str(tmp_path),
            status="staging",
            stage_path=str(ms_path),
            published_path=None,
            created_at=1234567890.0,
            staged_at=1234567890.0,
            published_at=None,
            publish_mode=None,
            metadata_json=None,
            qa_status=None,
            validation_status=None,
            finalization_status="pending",
            auto_publish_enabled=False,
            publish_attempts=0,
            publish_error=None,
        )
        mock_get_data.return_value = mock_record
        mock_calibration.return_value = 0

        args = MagicMock()
        args.data_id = "ms_test"
        args.output_dir = None
        args.skip_plots = False
        args.catalog = "nvss"
        args.min_snr = 5.0
        args.min_flux = 0.01
        args.max_flux = 10.0
        args.max_flux_error = 0.2

        result = cmd_report(args)

        assert result == 0
        mock_get_data.assert_called_once()
        mock_calibration.assert_called_once()

    @patch("dsa110_contimg.qa.cli.cmd_image")
    @patch("dsa110_contimg.database.data_registry.get_data")
    def test_report_qa_for_image(self, mock_get_data, mock_image, tmp_path):
        """Test QA report generation for image data."""
        from dsa110_contimg.database.data_registry import DataRecord

        image_path = tmp_path / "test.fits"
        image_path.touch()

        mock_record = DataRecord(
            id=2,
            data_id="image_test",
            data_type="image",
            base_path=str(tmp_path),
            status="staging",
            stage_path=str(image_path),
            published_path=None,
            created_at=1234567890.0,
            staged_at=1234567890.0,
            published_at=None,
            publish_mode=None,
            metadata_json=None,
            qa_status=None,
            validation_status=None,
            finalization_status="pending",
            auto_publish_enabled=False,
            publish_attempts=0,
            publish_error=None,
        )
        mock_get_data.return_value = mock_record
        mock_image.return_value = 0

        args = MagicMock()
        args.data_id = "image_test"
        args.output_dir = None
        args.skip_plots = False
        args.catalog = "nvss"
        args.min_snr = 5.0
        args.min_flux = 0.01
        args.max_flux = 10.0
        args.max_flux_error = 0.2

        result = cmd_report(args)

        assert result == 0
        mock_get_data.assert_called_once()
        mock_image.assert_called_once()

    @patch("dsa110_contimg.database.data_registry.get_data")
    def test_report_qa_data_not_found(self, mock_get_data):
        """Test QA report with non-existent data."""
        mock_get_data.return_value = None

        args = MagicMock()
        args.data_id = "nonexistent"
        args.output_dir = None
        args.skip_plots = False
        args.catalog = "nvss"
        args.min_snr = 5.0
        args.min_flux = 0.01
        args.max_flux = 10.0
        args.max_flux_error = 0.2

        result = cmd_report(args)

        assert result == 1
        mock_get_data.assert_called_once()
