-- PostgreSQL Schema for DSA-110 Continuum Imaging Pipeline
-- Converted from SQLite schema in /data/dsa110-contimg/state/products.sqlite3
--
-- Run with: psql -U dsa110 -d dsa110 -f init.sql
-- Or automatically via Docker init.d
--
-- Key differences from SQLite:
--   - AUTOINCREMENT → SERIAL/BIGSERIAL
--   - TEXT → TEXT (same)
--   - REAL → DOUBLE PRECISION
--   - BLOB → BYTEA
--   - datetime('now') → NOW()
--   - Added explicit timestamp types

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search
CREATE EXTENSION IF NOT EXISTS btree_gist; -- For range indexes

-- =============================================================================
-- Core Pipeline Tables
-- =============================================================================

-- Dead letter queue for failed operations
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id SERIAL PRIMARY KEY,
    queue_name TEXT NOT NULL,
    item_id TEXT NOT NULL,
    error_message TEXT,
    error_traceback TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW(),
    last_retry_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by TEXT,
    UNIQUE(queue_name, item_id)
);

-- MS (Measurement Set) index for converted files
CREATE TABLE IF NOT EXISTS ms_index (
    id SERIAL PRIMARY KEY,
    ms_path TEXT UNIQUE NOT NULL,
    group_id TEXT,
    source_files TEXT,  -- JSON array of source HDF5 files
    n_subbands INTEGER,
    n_antennas INTEGER,
    n_channels INTEGER,
    n_polarizations INTEGER,
    n_integrations INTEGER,
    obs_start_mjd DOUBLE PRECISION,
    obs_end_mjd DOUBLE PRECISION,
    freq_min_hz DOUBLE PRECISION,
    freq_max_hz DOUBLE PRECISION,
    phase_center_ra DOUBLE PRECISION,
    phase_center_dec DOUBLE PRECISION,
    total_size_bytes BIGINT,
    conversion_time_s DOUBLE PRECISION,
    writer_type TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,
    validation_status TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_ms_obs_time ON ms_index(obs_start_mjd, obs_end_mjd);
CREATE INDEX IF NOT EXISTS idx_ms_group ON ms_index(group_id);

-- Images table for imaging products
CREATE TABLE IF NOT EXISTS images (
    id SERIAL PRIMARY KEY,
    ms_path TEXT,
    image_path TEXT UNIQUE NOT NULL,
    image_type TEXT,  -- 'continuum', 'spectral', 'stokes', etc.
    stokes TEXT,  -- 'I', 'Q', 'U', 'V', 'XX', 'YY', etc.
    freq_center_hz DOUBLE PRECISION,
    freq_width_hz DOUBLE PRECISION,
    n_pixels_x INTEGER,
    n_pixels_y INTEGER,
    pixel_size_arcsec DOUBLE PRECISION,
    beam_major_arcsec DOUBLE PRECISION,
    beam_minor_arcsec DOUBLE PRECISION,
    beam_pa_deg DOUBLE PRECISION,
    rms_jy DOUBLE PRECISION,
    peak_jy DOUBLE PRECISION,
    dynamic_range DOUBLE PRECISION,
    imaging_software TEXT,  -- 'wsclean', 'tclean', etc.
    imaging_params TEXT,  -- JSON of imaging parameters
    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,
    validation_status TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_images_ms ON images(ms_path);
CREATE INDEX IF NOT EXISTS idx_images_type ON images(image_type);

-- Photometry measurements
CREATE TABLE IF NOT EXISTS photometry (
    id SERIAL PRIMARY KEY,
    image_id INTEGER REFERENCES images(id) ON DELETE CASCADE,
    source_id TEXT,
    source_name TEXT,
    ra_deg DOUBLE PRECISION,
    dec_deg DOUBLE PRECISION,
    ra_err_arcsec DOUBLE PRECISION,
    dec_err_arcsec DOUBLE PRECISION,
    flux_jy DOUBLE PRECISION,
    flux_err_jy DOUBLE PRECISION,
    peak_jy DOUBLE PRECISION,
    peak_err_jy DOUBLE PRECISION,
    major_arcsec DOUBLE PRECISION,
    minor_arcsec DOUBLE PRECISION,
    pa_deg DOUBLE PRECISION,
    local_rms_jy DOUBLE PRECISION,
    snr DOUBLE PRECISION,
    extraction_method TEXT,  -- 'aperture', 'gaussian', 'catalog_match', etc.
    catalog_match TEXT,  -- matched catalog name
    catalog_match_dist_arcsec DOUBLE PRECISION,
    catalog_flux_jy DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW(),
    flags TEXT  -- JSON array of QA flags
);

CREATE INDEX IF NOT EXISTS idx_photometry_image ON photometry(image_id);
CREATE INDEX IF NOT EXISTS idx_photometry_source ON photometry(source_id);
CREATE INDEX IF NOT EXISTS idx_photometry_coords ON photometry(ra_deg, dec_deg);
CREATE INDEX IF NOT EXISTS idx_photometry_flux ON photometry(flux_jy);

-- Jobs for async processing
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    priority INTEGER DEFAULT 0,
    payload TEXT,  -- JSON parameters
    result TEXT,  -- JSON result
    error_message TEXT,
    error_traceback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    worker_id TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER,
    depends_on TEXT  -- JSON array of job IDs
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority DESC, created_at);

-- Batch jobs for grouped processing
CREATE TABLE IF NOT EXISTS batch_jobs (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    status TEXT DEFAULT 'pending',
    job_ids TEXT,  -- JSON array of job IDs
    total_jobs INTEGER,
    completed_jobs INTEGER DEFAULT 0,
    failed_jobs INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_batch_status ON batch_jobs(status);

-- =============================================================================
-- Time-series and Variability Tables
-- =============================================================================

-- Variability statistics per source
CREATE TABLE IF NOT EXISTS variability_stats (
    id SERIAL PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_name TEXT,
    ra_deg DOUBLE PRECISION,
    dec_deg DOUBLE PRECISION,
    n_epochs INTEGER,
    mean_flux_jy DOUBLE PRECISION,
    std_flux_jy DOUBLE PRECISION,
    min_flux_jy DOUBLE PRECISION,
    max_flux_jy DOUBLE PRECISION,
    chi2_reduced DOUBLE PRECISION,
    variability_index DOUBLE PRECISION,  -- V = (max-min)/mean
    modulation_index DOUBLE PRECISION,  -- m = std/mean
    first_detection_mjd DOUBLE PRECISION,
    last_detection_mjd DOUBLE PRECISION,
    is_variable BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_variability_source ON variability_stats(source_id);
CREATE INDEX IF NOT EXISTS idx_variability_variable ON variability_stats(is_variable);
CREATE INDEX IF NOT EXISTS idx_variability_index ON variability_stats(variability_index);

-- Transient candidates
CREATE TABLE IF NOT EXISTS transient_candidates (
    id SERIAL PRIMARY KEY,
    source_id TEXT,
    photometry_id INTEGER REFERENCES photometry(id),
    image_id INTEGER REFERENCES images(id),
    ra_deg DOUBLE PRECISION,
    dec_deg DOUBLE PRECISION,
    detection_mjd DOUBLE PRECISION,
    flux_jy DOUBLE PRECISION,
    flux_err_jy DOUBLE PRECISION,
    snr DOUBLE PRECISION,
    transient_type TEXT,  -- 'new_source', 'flare', 'brightening', 'fading'
    upper_limit_jy DOUBLE PRECISION,  -- previous non-detection limit
    rise_time_days DOUBLE PRECISION,
    classification TEXT,  -- 'real', 'artifact', 'pending', 'rejected'
    classification_reason TEXT,
    follow_up_status TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transient_source ON transient_candidates(source_id);
CREATE INDEX IF NOT EXISTS idx_transient_type ON transient_candidates(transient_type);
CREATE INDEX IF NOT EXISTS idx_transient_class ON transient_candidates(classification);
CREATE INDEX IF NOT EXISTS idx_transient_mjd ON transient_candidates(detection_mjd);

-- =============================================================================
-- Mosaics and Combined Products
-- =============================================================================

-- Mosaic images from multiple pointings
CREATE TABLE IF NOT EXISTS mosaics (
    id SERIAL PRIMARY KEY,
    mosaic_path TEXT UNIQUE NOT NULL,
    mosaic_type TEXT,  -- 'daily', 'weekly', 'deep', 'custom'
    stokes TEXT,
    n_images INTEGER,
    image_ids TEXT,  -- JSON array of constituent image IDs
    ra_center_deg DOUBLE PRECISION,
    dec_center_deg DOUBLE PRECISION,
    field_size_deg DOUBLE PRECISION,
    n_pixels_x INTEGER,
    n_pixels_y INTEGER,
    pixel_size_arcsec DOUBLE PRECISION,
    beam_major_arcsec DOUBLE PRECISION,
    beam_minor_arcsec DOUBLE PRECISION,
    beam_pa_deg DOUBLE PRECISION,
    rms_jy DOUBLE PRECISION,
    peak_jy DOUBLE PRECISION,
    start_mjd DOUBLE PRECISION,
    end_mjd DOUBLE PRECISION,
    total_integration_s DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,
    validation_status TEXT
);

CREATE INDEX IF NOT EXISTS idx_mosaics_type ON mosaics(mosaic_type);
CREATE INDEX IF NOT EXISTS idx_mosaics_time ON mosaics(start_mjd, end_mjd);

-- =============================================================================
-- Calibration Tables
-- =============================================================================

-- Calibrator transits for scheduling
CREATE TABLE IF NOT EXISTS calibrator_transits (
    id SERIAL PRIMARY KEY,
    calibrator_name TEXT NOT NULL,
    transit_mjd DOUBLE PRECISION NOT NULL,
    transit_lst DOUBLE PRECISION,
    ra_deg DOUBLE PRECISION,
    dec_deg DOUBLE PRECISION,
    elevation_deg DOUBLE PRECISION,
    expected_flux_jy DOUBLE PRECISION,
    observed_flux_jy DOUBLE PRECISION,
    ms_path TEXT,
    caltable_path TEXT,
    status TEXT DEFAULT 'predicted',  -- predicted, observed, calibrated, failed
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transit_cal ON calibrator_transits(calibrator_name);
CREATE INDEX IF NOT EXISTS idx_transit_mjd ON calibrator_transits(transit_mjd);
CREATE INDEX IF NOT EXISTS idx_transit_status ON calibrator_transits(status);

-- Calibration solutions registry
CREATE TABLE IF NOT EXISTS calibration_solutions (
    id SERIAL PRIMARY KEY,
    caltable_path TEXT UNIQUE NOT NULL,
    caltable_type TEXT,  -- 'bandpass', 'delay', 'gain', 'polarization'
    calibrator_name TEXT,
    ms_path TEXT,
    transit_id INTEGER REFERENCES calibrator_transits(id),
    obs_mjd DOUBLE PRECISION,
    valid_start_mjd DOUBLE PRECISION,
    valid_end_mjd DOUBLE PRECISION,
    n_antennas INTEGER,
    n_spw INTEGER,
    n_channels INTEGER,
    freq_min_hz DOUBLE PRECISION,
    freq_max_hz DOUBLE PRECISION,
    applied_count INTEGER DEFAULT 0,
    quality_score DOUBLE PRECISION,
    flags TEXT,  -- JSON array of flagged antennas/channels
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_calsol_type ON calibration_solutions(caltable_type);
CREATE INDEX IF NOT EXISTS idx_calsol_cal ON calibration_solutions(calibrator_name);
CREATE INDEX IF NOT EXISTS idx_calsol_valid ON calibration_solutions(valid_start_mjd, valid_end_mjd);

-- =============================================================================
-- Quality Assurance Tables
-- =============================================================================

-- QA metrics per MS/image
CREATE TABLE IF NOT EXISTS qa_metrics (
    id SERIAL PRIMARY KEY,
    target_type TEXT NOT NULL,  -- 'ms', 'image', 'caltable', 'mosaic'
    target_id INTEGER,
    target_path TEXT,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    metric_unit TEXT,
    threshold_min DOUBLE PRECISION,
    threshold_max DOUBLE PRECISION,
    status TEXT,  -- 'pass', 'warn', 'fail'
    details TEXT,  -- JSON with additional context
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qa_target ON qa_metrics(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_qa_metric ON qa_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_qa_status ON qa_metrics(status);

-- =============================================================================
-- Session and Audit Tables
-- =============================================================================

-- API sessions (if using session-based auth)
CREATE TABLE IF NOT EXISTS api_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_session_user ON api_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_session_active ON api_sessions(is_active, expires_at);

-- Audit log for important operations
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    event_type TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    user_id TEXT,
    action TEXT,
    old_value TEXT,  -- JSON
    new_value TEXT,  -- JSON
    ip_address TEXT,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_log(target_type, target_id);

-- =============================================================================
-- Alembic Migration Tracking
-- =============================================================================

CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Insert initial version marker
INSERT INTO alembic_version (version_num) VALUES ('postgresql_initial')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- Comments and Documentation
-- =============================================================================

COMMENT ON TABLE ms_index IS 'Index of converted Measurement Sets from UVH5 files';
COMMENT ON TABLE images IS 'Imaging products from wsclean/tclean';
COMMENT ON TABLE photometry IS 'Source extraction and photometry measurements';
COMMENT ON TABLE variability_stats IS 'Time-series variability statistics per source';
COMMENT ON TABLE transient_candidates IS 'Candidate transient and variable sources';
COMMENT ON TABLE calibrator_transits IS 'Predicted and observed calibrator transits';
COMMENT ON TABLE calibration_solutions IS 'Registry of calibration tables';

-- =============================================================================
-- Initial Data
-- =============================================================================

-- Insert known calibrators (from VLA calibrator catalog)
-- This is handled by the application at runtime via calibrator_registry.sqlite3
