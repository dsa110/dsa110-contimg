"""
Custom Prometheus metrics for DSA-110 scientific workflow.

These metrics track pipeline throughput and scientific output,
complementing the HTTP metrics from prometheus-fastapi-instrumentator.

Usage in pipeline code:
    from dsa110_contimg.api.metrics import (
        ms_processed_counter,
        images_created_counter,
        photometry_recorded_counter,
    )
    
    # After processing an MS
    ms_processed_counter.labels(status='success', stage='calibrated').inc()
    
    # After creating an image
    images_created_counter.labels(type='continuum').inc()
    
    # After recording photometry
    photometry_recorded_counter.labels(source_type='transient').inc(count)
"""

from __future__ import annotations

import logging
import os
import sqlite3
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, Info

logger = logging.getLogger(__name__)

# =============================================================================
# Scientific Throughput Counters
# =============================================================================

ms_processed_counter = Counter(
    'dsa110_ms_processed_total',
    'Total measurement sets processed by the pipeline',
    ['status', 'stage'],  # status: success/failed, stage: calibrated/imaged/etc
)

images_created_counter = Counter(
    'dsa110_images_created_total',
    'Total images created by the pipeline',
    ['type'],  # type: continuum/dirty/residual/mosaic
)

photometry_recorded_counter = Counter(
    'dsa110_photometry_records_total',
    'Total photometry measurements recorded',
    ['source_type'],  # source_type: known/transient/calibrator
)

calibrations_counter = Counter(
    'dsa110_calibrations_total',
    'Total calibration operations performed',
    ['status', 'type'],  # status: success/failed, type: bandpass/gain/selfcal
)

sources_detected_counter = Counter(
    'dsa110_sources_detected_total',
    'Total sources detected in images',
    ['classification'],  # classification: point/extended/transient
)

# =============================================================================
# Current State Gauges (updated by periodic sync from database)
# =============================================================================

ms_count_gauge = Gauge(
    'dsa110_ms_count',
    'Current number of measurement sets in database',
    ['stage'],  # stage: ingested/calibrated/imaged/etc
)

images_count_gauge = Gauge(
    'dsa110_images_count',
    'Current number of images in database',
    ['type'],
)

sources_count_gauge = Gauge(
    'dsa110_sources_count',
    'Current number of unique sources in database',
)

photometry_count_gauge = Gauge(
    'dsa110_photometry_count',
    'Current number of photometry records in database',
)

pending_jobs_gauge = Gauge(
    'dsa110_pending_jobs',
    'Number of pending pipeline jobs',
)

running_jobs_gauge = Gauge(
    'dsa110_running_jobs',
    'Number of currently running pipeline jobs',
)

# =============================================================================
# Data Quality Histograms
# =============================================================================

image_noise_histogram = Histogram(
    'dsa110_image_noise_jy',
    'Image RMS noise in Jy',
    buckets=[1e-6, 5e-6, 1e-5, 2e-5, 5e-5, 1e-4, 2e-4, 5e-4, 1e-3, 5e-3],
)

image_dynamic_range_histogram = Histogram(
    'dsa110_image_dynamic_range',
    'Image dynamic range',
    buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000, 10000],
)

calibration_snr_histogram = Histogram(
    'dsa110_calibration_snr',
    'Calibration signal-to-noise ratio',
    buckets=[5, 10, 20, 50, 100, 200, 500, 1000],
)

# =============================================================================
# Pipeline Info
# =============================================================================

pipeline_info = Info(
    'dsa110_pipeline',
    'DSA-110 pipeline version and configuration',
)

# Set static info at import time
pipeline_info.info({
    'version': '0.1.0',
    'environment': os.getenv('DSA110_ENV', 'development'),
})


# =============================================================================
# Database Sync Functions
# =============================================================================

DEFAULT_DB_PATH = "/data/dsa110-contimg/state/products.sqlite3"
CAL_REGISTRY_DB_PATH = "/data/dsa110-contimg/state/cal_registry.sqlite3"


def sync_gauges_from_database(db_path: str = DEFAULT_DB_PATH) -> dict:
    """
    Sync gauge metrics from database state.
    
    Call this periodically (e.g., every 30s) to update gauges
    with current database counts.
    
    Returns dict with sync results for logging.
    """
    results = {}
    
    try:
        if not os.path.exists(db_path):
            logger.warning(f"Database not found: {db_path}")
            return {"error": "database not found"}
        
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        
        # MS counts by stage
        try:
            cursor = conn.execute("""
                SELECT stage, COUNT(*) as cnt 
                FROM ms_index 
                GROUP BY stage
            """)
            for row in cursor.fetchall():
                stage = row['stage'] or 'unknown'
                ms_count_gauge.labels(stage=stage).set(row['cnt'])
                results[f'ms_{stage}'] = row['cnt']
        except Exception as e:
            logger.warning(f"Failed to sync MS counts: {e}")
        
        # Image counts by type
        try:
            cursor = conn.execute("""
                SELECT type, COUNT(*) as cnt 
                FROM images 
                GROUP BY type
            """)
            for row in cursor.fetchall():
                img_type = row['type'] or 'unknown'
                images_count_gauge.labels(type=img_type).set(row['cnt'])
                results[f'images_{img_type}'] = row['cnt']
        except Exception as e:
            logger.warning(f"Failed to sync image counts: {e}")
        
        # Source count
        try:
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT source_id) as cnt FROM photometry
            """)
            count = cursor.fetchone()['cnt'] or 0
            sources_count_gauge.set(count)
            results['sources'] = count
        except Exception as e:
            logger.warning(f"Failed to sync source count: {e}")
        
        # Photometry count
        try:
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM photometry")
            count = cursor.fetchone()['cnt'] or 0
            photometry_count_gauge.set(count)
            results['photometry'] = count
        except Exception as e:
            logger.warning(f"Failed to sync photometry count: {e}")
        
        # Job counts
        try:
            cursor = conn.execute("""
                SELECT 
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running
                FROM batch_jobs
            """)
            row = cursor.fetchone()
            pending_jobs_gauge.set(row['pending'] or 0)
            running_jobs_gauge.set(row['running'] or 0)
            results['pending_jobs'] = row['pending'] or 0
            results['running_jobs'] = row['running'] or 0
        except Exception as e:
            logger.warning(f"Failed to sync job counts: {e}")
        
        conn.close()
        results['status'] = 'success'
        
    except Exception as e:
        logger.error(f"Database sync failed: {e}")
        results['status'] = 'error'
        results['error'] = str(e)
    
    return results


def record_image_quality(noise_jy: float, dynamic_range: float = None):
    """Record image quality metrics."""
    if noise_jy and noise_jy > 0:
        image_noise_histogram.observe(noise_jy)
    if dynamic_range and dynamic_range > 0:
        image_dynamic_range_histogram.observe(dynamic_range)


def record_calibration_quality(snr: float):
    """Record calibration quality metrics."""
    if snr and snr > 0:
        calibration_snr_histogram.observe(snr)
