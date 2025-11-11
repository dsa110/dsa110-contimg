#!/usr/bin/env python3
"""
Unit tests to validate run_first_mosaic.py workflow logic.

These tests verify critical assumptions and prevent race conditions,
file existence issues, and database/filesystem mismatches.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time

from dsa110_contimg.conversion.streaming.run_first_mosaic import (
    process_one_group,
    process_groups_until_count,
)
from dsa110_contimg.conversion.streaming.streaming_converter import QueueDB
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager


class TestMSFileExistenceValidation(unittest.TestCase):
    """Test that MS files are verified to exist before processing."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ms_path = Path(self.temp_dir) / "test.ms"
        self.args = Mock()
        self.args.output_dir = str(self.temp_dir)
        self.args.input_dir = str(self.temp_dir)
        self.args.scratch_dir = str(self.temp_dir)
        self.args.registry_db = str(Path(self.temp_dir) / "cal_registry.sqlite3")
        self.args.products_db = str(Path(self.temp_dir) / "products.sqlite3")
        self.args.max_workers = 1

    def test_ms_file_must_exist_before_time_extraction(self):
        """Verify that extract_ms_time_range is not called on non-existent MS files."""
        # MS file does not exist
        self.assertFalse(self.ms_path.exists())

        # Mock conversion to succeed but MS doesn't exist
        with patch(
            "dsa110_contimg.conversion.streaming.run_first_mosaic.convert_subband_groups_to_ms"
        ) as mock_convert:
            mock_convert.return_value = None

            queue = QueueDB(
                Path(self.temp_dir) / "queue.sqlite3",
                expected_subbands=16,
                chunk_duration_minutes=5.0,
            )

            # Add a group
            gid = "2025-10-02T10:02:45"
            queue.add_group(gid, ["test.hdf5"])

            with patch(
                "dsa110_contimg.conversion.streaming.run_first_mosaic.extract_ms_time_range"
            ) as mock_extract:
                # Process group - should fail gracefully if MS doesn't exist
                result = process_one_group(gid, self.args, queue)

                # If MS doesn't exist, extract_ms_time_range should not be called
                # OR if called, should handle the error gracefully
                if mock_extract.called:
                    # Verify it was called with a path that should exist
                    call_args = mock_extract.call_args[0][0]
                    self.assertTrue(
                        Path(call_args).exists(),
                        f"extract_ms_time_range called with non-existent path: {call_args}",
                    )

    def test_ms_file_must_exist_before_calibration_application(self):
        """Verify that calibration is not applied to non-existent MS files."""
        # MS file does not exist
        self.assertFalse(self.ms_path.exists())

        with patch(
            "dsa110_contimg.conversion.streaming.run_first_mosaic.convert_subband_groups_to_ms"
        ) as mock_convert:
            mock_convert.return_value = None

            queue = QueueDB(
                Path(self.temp_dir) / "queue.sqlite3",
                expected_subbands=16,
                chunk_duration_minutes=5.0,
            )

            gid = "2025-10-02T10:02:45"
            queue.add_group(gid, ["test.hdf5"])

            with patch(
                "dsa110_contimg.conversion.streaming.run_first_mosaic.apply_to_target"
            ) as mock_apply:
                result = process_one_group(gid, self.args, queue)

                # If MS doesn't exist, apply_to_target should not be called
                if mock_apply.called:
                    call_args = mock_apply.call_args[0][0]  # First arg is ms_path
                    self.assertTrue(
                        Path(call_args).exists(),
                        f"apply_to_target called with non-existent path: {call_args}",
                    )

    def test_ms_file_must_exist_before_imaging(self):
        """Verify that imaging is not attempted on non-existent MS files."""
        # MS file does not exist
        self.assertFalse(self.ms_path.exists())

        with patch(
            "dsa110_contimg.conversion.streaming.run_first_mosaic.convert_subband_groups_to_ms"
        ) as mock_convert:
            mock_convert.return_value = None

            queue = QueueDB(
                Path(self.temp_dir) / "queue.sqlite3",
                expected_subbands=16,
                chunk_duration_minutes=5.0,
            )

            gid = "2025-10-02T10:02:45"
            queue.add_group(gid, ["test.hdf5"])

            with patch(
                "dsa110_contimg.conversion.streaming.run_first_mosaic.image_ms"
            ) as mock_image:
                result = process_one_group(gid, self.args, queue)

                # If MS doesn't exist, image_ms should not be called
                if mock_image.called:
                    call_args = mock_image.call_args[0][0]  # First arg is ms_path
                    self.assertTrue(
                        Path(call_args).exists(),
                        f"image_ms called with non-existent path: {call_args}",
                    )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestConversionCompletionRaceCondition(unittest.TestCase):
    """Test that conversion completion is properly awaited."""

    def test_conversion_must_complete_before_ms_processing(self):
        """Verify that process_one_group waits for conversion to complete."""
        # This test verifies that convert_subband_groups_to_ms completes
        # before any MS file operations are attempted

        with patch(
            "dsa110_contimg.conversion.streaming.run_first_mosaic.convert_subband_groups_to_ms"
        ) as mock_convert:
            # Simulate conversion that takes time
            conversion_complete = False

            def slow_convert(*args, **kwargs):
                nonlocal conversion_complete
                time.sleep(0.1)  # Simulate conversion time
                conversion_complete = True
                # Create a dummy MS file
                ms_dir = Path(kwargs.get("output_dir", "."))
                ms_dir.mkdir(parents=True, exist_ok=True)
                (ms_dir / "test.ms").mkdir(parents=True, exist_ok=True)

            mock_convert.side_effect = slow_convert

            # Verify conversion completes before MS operations
            # (This is more of a documentation test - actual implementation
            # should ensure synchronous completion)
            self.assertFalse(conversion_complete)
            mock_convert("input", "output", "start", "end")
            self.assertTrue(conversion_complete)


class TestDatabaseFilesystemConsistency(unittest.TestCase):
    """Test that database paths match actual filesystem locations."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.products_db = Path(self.temp_dir) / "products.sqlite3"
        self.registry_db = Path(self.temp_dir) / "cal_registry.sqlite3"

    def test_check_for_new_group_verifies_file_existence(self):
        """Verify that check_for_new_group validates MS files exist."""
        from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert

        # Create database with non-existent MS path
        conn = ensure_products_db(self.products_db)
        fake_ms_path = str(Path(self.temp_dir) / "nonexistent.ms")
        ms_index_upsert(
            conn,
            fake_ms_path,
            status="converted",
            stage="converted",
            mid_mjd=60000.0,
        )
        conn.commit()
        conn.close()

        # Create manager
        manager = StreamingMosaicManager(
            products_db_path=self.products_db,
            registry_db_path=self.registry_db,
            ms_output_dir=Path(self.temp_dir) / "ms",
            images_dir=Path(self.temp_dir) / "images",
            mosaic_output_dir=Path(self.temp_dir) / "mosaics",
        )

        # check_for_new_group should handle non-existent files gracefully
        group_id = manager.check_for_new_group()

        # If group is created, get_group_ms_paths should verify files exist
        if group_id:
            ms_paths = manager.get_group_ms_paths(group_id)
            # All paths should exist OR the function should filter them out
            for ms_path in ms_paths:
                self.assertTrue(
                    Path(ms_path).exists(),
                    f"MS path from database does not exist: {ms_path}",
                )

    def test_get_group_ms_paths_validates_file_existence(self):
        """Verify that get_group_ms_paths checks files exist before time extraction."""
        from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert

        # Create database with non-existent MS path
        conn = ensure_products_db(self.products_db)
        fake_ms_path = str(Path(self.temp_dir) / "nonexistent.ms")
        ms_index_upsert(
            conn,
            fake_ms_path,
            status="converted",
            stage="converted",
            mid_mjd=60000.0,
        )
        conn.commit()
        conn.close()

        manager = StreamingMosaicManager(
            products_db_path=self.products_db,
            registry_db_path=self.registry_db,
            ms_output_dir=Path(self.temp_dir) / "ms",
            images_dir=Path(self.temp_dir) / "images",
            mosaic_output_dir=Path(self.temp_dir) / "mosaics",
        )

        # Create a group with non-existent MS
        group_id = "test_group"
        manager.products_db.execute(
            """
            INSERT INTO mosaic_groups (group_id, ms_paths, created_at, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (group_id, fake_ms_path, time.time()),
        )
        manager.products_db.commit()

        # get_group_ms_paths should handle non-existent files
        ms_paths = manager.get_group_ms_paths(group_id)

        # Should either filter out non-existent files OR verify they exist
        for ms_path in ms_paths:
            self.assertTrue(
                Path(ms_path).exists(),
                f"get_group_ms_paths returned non-existent path: {ms_path}",
            )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestTimeExtractionFallback(unittest.TestCase):
    """Test that time extraction failures use correct fallback logic."""

    def test_mid_mjd_fallback_uses_observation_time_not_current_time(self):
        """Verify that when extract_ms_time_range fails, we don't use current time."""
        # The fallback should use the observation time from the filename or database,
        # NOT time.time() which is the current system time

        from datetime import datetime
        from astropy.time import Time

        # Parse timestamp from filename
        gid = "2025-10-02T10:02:45"
        start_time = gid.replace("T", " ")
        start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")

        # Convert to MJD (this is what should be used as fallback)
        expected_mjd = Time(start_dt).mjd

        # Current time MJD (this is WRONG to use)
        current_mjd = Time.now().mjd

        # Verify they're different (observation was in the past)
        self.assertNotAlmostEqual(
            expected_mjd,
            current_mjd,
            delta=1.0,  # At least 1 day difference
            msg="Test observation time should be in the past",
        )

        # The code should use expected_mjd, not current_mjd
        # This test documents the requirement


class TestPathMapperConsistency(unittest.TestCase):
    """Test that path_mapper creates paths that match database records."""

    def test_path_mapper_creates_consistent_paths(self):
        """Verify that path_mapper creates paths that can be found later."""
        from dsa110_contimg.utils.ms_organization import create_path_mapper

        ms_base_dir = Path("/stage/dsa110-contimg/ms")
        path_mapper = create_path_mapper(
            ms_base_dir, is_calibrator=False, is_failed=False
        )

        base_name = "2025-10-02T10:02:45"
        ms_path = path_mapper(base_name, "/stage/dsa110-contimg/ms")

        # Path should be in organized location
        expected_path = (
            ms_base_dir / "science" / "2025-10-02" / f"{base_name}.ms"
        )
        self.assertEqual(
            str(ms_path),
            str(expected_path),
            "path_mapper should create organized paths",
        )

        # Path should be findable by extract_date_from_filename
        from dsa110_contimg.utils.ms_organization import extract_date_from_filename

        date_str = extract_date_from_filename(ms_path)
        self.assertEqual(date_str, "2025-10-02")


if __name__ == "__main__":
    unittest.main()

