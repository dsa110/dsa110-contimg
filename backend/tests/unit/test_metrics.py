"""
Unit tests for metrics.py - Prometheus metrics for DSA-110 pipeline.

Tests for:
- Counter metrics
- Gauge metrics  
- Histogram metrics
- Database sync functions
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from dsa110_contimg.api.metrics import (
    ms_processed_counter,
    images_created_counter,
    photometry_recorded_counter,
    calibrations_counter,
    sources_detected_counter,
    ms_count_gauge,
    images_count_gauge,
    sources_count_gauge,
    photometry_count_gauge,
    pending_jobs_gauge,
    running_jobs_gauge,
    image_noise_histogram,
    image_dynamic_range_histogram,
    calibration_snr_histogram,
    pipeline_info,
    sync_gauges_from_database,
    record_image_quality,
    record_calibration_quality,
)


class TestCounterMetrics:
    """Tests for counter metrics."""

    def test_ms_processed_counter_exists(self):
        """Test ms_processed_counter is defined."""
        assert ms_processed_counter is not None
        assert 'dsa110_ms_processed' in ms_processed_counter._name

    def test_ms_processed_counter_labels(self):
        """Test ms_processed_counter has correct labels."""
        # Access labels to verify they exist
        labeled = ms_processed_counter.labels(status='success', stage='calibrated')
        assert labeled is not None

    def test_images_created_counter_exists(self):
        """Test images_created_counter is defined."""
        assert images_created_counter is not None
        assert 'dsa110_images_created' in images_created_counter._name

    def test_images_created_counter_labels(self):
        """Test images_created_counter has correct labels."""
        labeled = images_created_counter.labels(type='continuum')
        assert labeled is not None

    def test_photometry_recorded_counter_exists(self):
        """Test photometry_recorded_counter is defined."""
        assert photometry_recorded_counter is not None
        assert 'dsa110_photometry_records' in photometry_recorded_counter._name

    def test_calibrations_counter_exists(self):
        """Test calibrations_counter is defined."""
        assert calibrations_counter is not None
        assert 'dsa110_calibrations' in calibrations_counter._name

    def test_sources_detected_counter_exists(self):
        """Test sources_detected_counter is defined."""
        assert sources_detected_counter is not None
        assert 'dsa110_sources_detected' in sources_detected_counter._name


class TestGaugeMetrics:
    """Tests for gauge metrics."""

    def test_ms_count_gauge_exists(self):
        """Test ms_count_gauge is defined."""
        assert ms_count_gauge is not None
        assert ms_count_gauge._name == 'dsa110_ms_count'

    def test_images_count_gauge_exists(self):
        """Test images_count_gauge is defined."""
        assert images_count_gauge is not None
        assert images_count_gauge._name == 'dsa110_images_count'

    def test_sources_count_gauge_exists(self):
        """Test sources_count_gauge is defined."""
        assert sources_count_gauge is not None
        assert sources_count_gauge._name == 'dsa110_sources_count'

    def test_photometry_count_gauge_exists(self):
        """Test photometry_count_gauge is defined."""
        assert photometry_count_gauge is not None
        assert photometry_count_gauge._name == 'dsa110_photometry_count'

    def test_pending_jobs_gauge_exists(self):
        """Test pending_jobs_gauge is defined."""
        assert pending_jobs_gauge is not None
        assert pending_jobs_gauge._name == 'dsa110_pending_jobs'

    def test_running_jobs_gauge_exists(self):
        """Test running_jobs_gauge is defined."""
        assert running_jobs_gauge is not None
        assert running_jobs_gauge._name == 'dsa110_running_jobs'


class TestHistogramMetrics:
    """Tests for histogram metrics."""

    def test_image_noise_histogram_exists(self):
        """Test image_noise_histogram is defined."""
        assert image_noise_histogram is not None
        assert image_noise_histogram._name == 'dsa110_image_noise_jy'

    def test_image_noise_histogram_has_buckets(self):
        """Test image_noise_histogram has appropriate buckets."""
        # Buckets should span typical noise values (uJy to mJy range)
        assert len(image_noise_histogram._upper_bounds) > 5

    def test_image_dynamic_range_histogram_exists(self):
        """Test image_dynamic_range_histogram is defined."""
        assert image_dynamic_range_histogram is not None
        assert image_dynamic_range_histogram._name == 'dsa110_image_dynamic_range'

    def test_calibration_snr_histogram_exists(self):
        """Test calibration_snr_histogram is defined."""
        assert calibration_snr_histogram is not None
        assert calibration_snr_histogram._name == 'dsa110_calibration_snr'


class TestPipelineInfo:
    """Tests for pipeline info metric."""

    def test_pipeline_info_exists(self):
        """Test pipeline_info is defined."""
        assert pipeline_info is not None
        assert pipeline_info._name == 'dsa110_pipeline'


class TestRecordImageQuality:
    """Tests for record_image_quality function."""

    def test_record_positive_noise(self):
        """Test recording positive noise value."""
        # Should not raise
        record_image_quality(noise_jy=1e-5)

    def test_record_positive_dynamic_range(self):
        """Test recording positive dynamic range."""
        # Should not raise
        record_image_quality(noise_jy=1e-5, dynamic_range=1000)

    def test_record_zero_noise_skipped(self):
        """Test zero noise is not recorded."""
        # Should not raise, but not record
        record_image_quality(noise_jy=0)

    def test_record_negative_noise_skipped(self):
        """Test negative noise is not recorded."""
        # Should not raise, but not record  
        record_image_quality(noise_jy=-1e-5)

    def test_record_none_dynamic_range_skipped(self):
        """Test None dynamic range is not recorded."""
        # Should not raise
        record_image_quality(noise_jy=1e-5, dynamic_range=None)


class TestRecordCalibrationQuality:
    """Tests for record_calibration_quality function."""

    def test_record_positive_snr(self):
        """Test recording positive SNR."""
        # Should not raise
        record_calibration_quality(snr=100)

    def test_record_zero_snr_skipped(self):
        """Test zero SNR is not recorded."""
        record_calibration_quality(snr=0)

    def test_record_negative_snr_skipped(self):
        """Test negative SNR is not recorded."""
        record_calibration_quality(snr=-50)

    def test_record_none_snr_skipped(self):
        """Test None SNR is not recorded."""
        record_calibration_quality(snr=None)


class TestSyncGaugesFromDatabase:
    """Tests for sync_gauges_from_database function."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary SQLite database with test data."""
        db_path = tmp_path / "test_products.sqlite3"
        
        conn = sqlite3.connect(db_path)
        
        # Create tables matching the expected schema
        conn.execute("""
            CREATE TABLE ms_index (
                id INTEGER PRIMARY KEY,
                stage TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE images (
                id INTEGER PRIMARY KEY,
                type TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE photometry (
                id INTEGER PRIMARY KEY,
                source_id TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE batch_jobs (
                id INTEGER PRIMARY KEY,
                status TEXT
            )
        """)
        
        # Insert test data
        conn.executemany(
            "INSERT INTO ms_index (stage) VALUES (?)",
            [("ingested",), ("calibrated",), ("calibrated",), ("imaged",)]
        )
        conn.executemany(
            "INSERT INTO images (type) VALUES (?)",
            [("continuum",), ("continuum",), ("dirty",)]
        )
        conn.executemany(
            "INSERT INTO photometry (source_id) VALUES (?)",
            [("src-1",), ("src-1",), ("src-2",), ("src-3",)]
        )
        conn.executemany(
            "INSERT INTO batch_jobs (status) VALUES (?)",
            [("pending",), ("pending",), ("running",), ("completed",)]
        )
        
        conn.commit()
        conn.close()
        
        return str(db_path)

    def test_sync_success(self, temp_db):
        """Test successful sync from database."""
        results = sync_gauges_from_database(temp_db)
        
        assert results['status'] == 'success'
        # Check MS counts
        assert results['ms_ingested'] == 1
        assert results['ms_calibrated'] == 2
        assert results['ms_imaged'] == 1
        
        # Check image counts
        assert results['images_continuum'] == 2
        assert results['images_dirty'] == 1
        
        # Check photometry counts
        assert results['photometry'] == 4
        assert results['sources'] == 3  # 3 unique source_ids
        
        # Check job counts
        assert results['pending_jobs'] == 2
        assert results['running_jobs'] == 1

    def test_sync_missing_database(self, tmp_path):
        """Test sync with missing database."""
        missing_path = tmp_path / "nonexistent.sqlite3"
        
        results = sync_gauges_from_database(str(missing_path))
        
        assert results.get('error') == 'database not found'

    def test_sync_empty_database(self, tmp_path):
        """Test sync with empty database (tables exist but no data)."""
        db_path = tmp_path / "empty.sqlite3"
        
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE ms_index (id INTEGER, stage TEXT)")
        conn.execute("CREATE TABLE images (id INTEGER, type TEXT)")
        conn.execute("CREATE TABLE photometry (id INTEGER, source_id TEXT)")
        conn.execute("CREATE TABLE batch_jobs (id INTEGER, status TEXT)")
        conn.commit()
        conn.close()
        
        results = sync_gauges_from_database(str(db_path))
        
        assert results['status'] == 'success'
        # Should have zero counts but not fail
        assert results.get('photometry', 0) == 0
        assert results.get('sources', 0) == 0

    def test_sync_handles_missing_tables(self, tmp_path):
        """Test sync handles missing tables gracefully."""
        db_path = tmp_path / "partial.sqlite3"
        
        conn = sqlite3.connect(db_path)
        # Only create ms_index table, skip others
        conn.execute("CREATE TABLE ms_index (id INTEGER, stage TEXT)")
        conn.execute("INSERT INTO ms_index (stage) VALUES ('ingested')")
        conn.commit()
        conn.close()
        
        # Should not raise, just log warnings for missing tables
        results = sync_gauges_from_database(str(db_path))
        
        # Status should still be success even if some tables missing
        assert results['status'] == 'success'
        assert results['ms_ingested'] == 1


class TestMetricLabelValues:
    """Tests for metric label value patterns."""

    def test_ms_stage_labels(self):
        """Test MS counter accepts expected stage values."""
        stages = ['ingested', 'calibrated', 'imaged', 'flagged']
        for stage in stages:
            labeled = ms_processed_counter.labels(status='success', stage=stage)
            assert labeled is not None

    def test_ms_status_labels(self):
        """Test MS counter accepts expected status values."""
        statuses = ['success', 'failed']
        for status in statuses:
            labeled = ms_processed_counter.labels(status=status, stage='calibrated')
            assert labeled is not None

    def test_image_type_labels(self):
        """Test image counter accepts expected type values."""
        types = ['continuum', 'dirty', 'residual', 'mosaic']
        for img_type in types:
            labeled = images_created_counter.labels(type=img_type)
            assert labeled is not None

    def test_calibration_type_labels(self):
        """Test calibration counter accepts expected type values."""
        types = ['bandpass', 'gain', 'selfcal', 'delay']
        for cal_type in types:
            labeled = calibrations_counter.labels(status='success', type=cal_type)
            assert labeled is not None

    def test_source_classification_labels(self):
        """Test source counter accepts expected classification values."""
        classifications = ['point', 'extended', 'transient']
        for cls in classifications:
            labeled = sources_detected_counter.labels(classification=cls)
            assert labeled is not None


class TestMetricOperations:
    """Tests for metric operations."""

    def test_counter_increment(self):
        """Test counter can be incremented."""
        # Get initial value (may have been incremented by previous tests)
        counter = ms_processed_counter.labels(status='test', stage='test')
        
        # Should not raise
        counter.inc()
        counter.inc(5)

    def test_gauge_set(self):
        """Test gauge can be set."""
        # Should not raise
        pending_jobs_gauge.set(10)
        running_jobs_gauge.set(2)

    def test_histogram_observe(self):
        """Test histogram can observe values."""
        # Should not raise
        image_noise_histogram.observe(1e-5)
        image_dynamic_range_histogram.observe(500)
        calibration_snr_histogram.observe(100)
