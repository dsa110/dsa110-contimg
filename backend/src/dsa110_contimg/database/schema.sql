-- =============================================================================
-- DSA-110 Continuum Imaging Pipeline: Unified Database Schema
-- =============================================================================
-- 
-- All pipeline data is stored in a single unified database (pipeline.sqlite3)
-- for simpler operations, atomic transactions, and cross-domain queries.
--
-- Table Domains:
--   - Products: ms_index, images, photometry, transients
--   - Calibration: calibration_tables, calibrator_transits
--   - HDF5: hdf5_files, pointing_history
--   - Queue: processing_queue, performance_metrics
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Products Domain
-- ---------------------------------------------------------------------------

-- Measurement Set index with processing stage tracking
CREATE TABLE IF NOT EXISTS ms_index (
    path TEXT PRIMARY KEY,
    start_mjd REAL,
    end_mjd REAL,
    mid_mjd REAL,
    processed_at REAL,
    status TEXT,
    stage TEXT,
    stage_updated_at REAL,
    cal_applied INTEGER DEFAULT 0,
    imagename TEXT,
    field_name TEXT,
    pointing_ra_deg REAL,
    pointing_dec_deg REAL,
    ra_deg REAL,
    dec_deg REAL,
    group_id TEXT,
    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_ms_index_mid_mjd ON ms_index(mid_mjd);
CREATE INDEX IF NOT EXISTS idx_ms_index_status ON ms_index(status);
CREATE INDEX IF NOT EXISTS idx_ms_index_stage ON ms_index(stage);
CREATE INDEX IF NOT EXISTS idx_ms_index_group_id ON ms_index(group_id);

-- Image products linked to MS
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    ms_path TEXT NOT NULL,
    created_at REAL NOT NULL,
    type TEXT NOT NULL,
    format TEXT DEFAULT 'fits',
    beam_major_arcsec REAL,
    beam_minor_arcsec REAL,
    beam_pa_deg REAL,
    noise_jy REAL,
    dynamic_range REAL,
    pbcor INTEGER DEFAULT 0,
    field_name TEXT,
    center_ra_deg REAL,
    center_dec_deg REAL,
    imsize_x INTEGER,
    imsize_y INTEGER,
    cellsize_arcsec REAL,
    freq_ghz REAL,
    bandwidth_mhz REAL,
    integration_sec REAL,
    FOREIGN KEY (ms_path) REFERENCES ms_index(path)
);

CREATE INDEX IF NOT EXISTS idx_images_ms_path ON images(ms_path);
CREATE INDEX IF NOT EXISTS idx_images_type ON images(type);
CREATE INDEX IF NOT EXISTS idx_images_created_at ON images(created_at);

-- Photometric measurements
CREATE TABLE IF NOT EXISTS photometry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL,
    source_id TEXT NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_jy REAL NOT NULL,
    flux_err_jy REAL,
    peak_flux_jy REAL,
    rms_jy REAL,
    snr REAL,
    major_arcsec REAL,
    minor_arcsec REAL,
    pa_deg REAL,
    measured_at REAL NOT NULL,
    quality_flag TEXT,
    FOREIGN KEY (image_path) REFERENCES images(path)
);

CREATE INDEX IF NOT EXISTS idx_photometry_image ON photometry(image_path);
CREATE INDEX IF NOT EXISTS idx_photometry_source ON photometry(source_id);
CREATE INDEX IF NOT EXISTS idx_photometry_coords ON photometry(ra_deg, dec_deg);

-- ---------------------------------------------------------------------------
-- Calibration Domain
-- ---------------------------------------------------------------------------

-- Calibration table registry
CREATE TABLE IF NOT EXISTS calibration_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    set_name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    table_type TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    cal_field TEXT,
    refant TEXT,
    created_at REAL NOT NULL,
    valid_start_mjd REAL,
    valid_end_mjd REAL,
    status TEXT NOT NULL DEFAULT 'active',
    source_ms_path TEXT,
    solver_command TEXT,
    solver_version TEXT,
    solver_params TEXT,
    quality_metrics TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_caltables_set ON calibration_tables(set_name);
CREATE INDEX IF NOT EXISTS idx_caltables_valid ON calibration_tables(valid_start_mjd, valid_end_mjd);
CREATE INDEX IF NOT EXISTS idx_caltables_status ON calibration_tables(status);

-- Record of calibration applications
CREATE TABLE IF NOT EXISTS calibration_applied (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ms_path TEXT NOT NULL,
    caltable_path TEXT NOT NULL,
    applied_at REAL NOT NULL,
    quality REAL,
    success INTEGER DEFAULT 1,
    error_message TEXT,
    FOREIGN KEY (ms_path) REFERENCES ms_index(path),
    FOREIGN KEY (caltable_path) REFERENCES calibration_tables(path)
);

CREATE INDEX IF NOT EXISTS idx_cal_applied_ms ON calibration_applied(ms_path);

-- ---------------------------------------------------------------------------
-- Calibrator Catalog (from calibrators.sqlite3)
-- ---------------------------------------------------------------------------

-- Known bandpass calibrators
CREATE TABLE IF NOT EXISTS calibrator_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_jy REAL,
    flux_freq_ghz REAL,
    dec_range_min REAL,
    dec_range_max REAL,
    source_catalog TEXT,
    status TEXT DEFAULT 'active',
    registered_at REAL NOT NULL,
    registered_by TEXT,
    code_20_cm TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_calibrators_name ON calibrator_catalog(name);
CREATE INDEX IF NOT EXISTS idx_calibrators_dec ON calibrator_catalog(dec_deg);
CREATE INDEX IF NOT EXISTS idx_calibrators_status ON calibrator_catalog(status);

-- Calibrator transit calculations
CREATE TABLE IF NOT EXISTS calibrator_transits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calibrator_name TEXT NOT NULL,
    transit_mjd REAL NOT NULL,
    transit_iso TEXT NOT NULL,
    has_data INTEGER NOT NULL DEFAULT 0,
    group_id TEXT,
    group_mid_iso TEXT,
    delta_minutes REAL,
    pb_response REAL,
    dec_match INTEGER NOT NULL DEFAULT 0,
    calculated_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(calibrator_name, transit_mjd)
);

CREATE INDEX IF NOT EXISTS idx_transits_calibrator ON calibrator_transits(calibrator_name);
CREATE INDEX IF NOT EXISTS idx_transits_mjd ON calibrator_transits(transit_mjd DESC);
CREATE INDEX IF NOT EXISTS idx_transits_has_data ON calibrator_transits(has_data);

-- ---------------------------------------------------------------------------
-- HDF5 Domain
-- ---------------------------------------------------------------------------

-- Raw HDF5 file tracking
CREATE TABLE IF NOT EXISTS hdf5_files (
    path TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    group_id TEXT NOT NULL,
    subband_code TEXT NOT NULL,
    subband_num INTEGER,
    timestamp_iso TEXT,
    timestamp_mjd REAL,
    file_size_bytes INTEGER,
    modified_time REAL,
    indexed_at REAL NOT NULL,
    stored INTEGER DEFAULT 1,
    ra_deg REAL,
    dec_deg REAL,
    obs_date TEXT,
    obs_time TEXT
);

CREATE INDEX IF NOT EXISTS idx_hdf5_group ON hdf5_files(group_id);
CREATE INDEX IF NOT EXISTS idx_hdf5_timestamp ON hdf5_files(timestamp_mjd);
CREATE INDEX IF NOT EXISTS idx_hdf5_stored ON hdf5_files(stored);
CREATE INDEX IF NOT EXISTS idx_hdf5_coords ON hdf5_files(ra_deg, dec_deg);

-- Pointing history (from both hdf5 and ingest)
CREATE TABLE IF NOT EXISTS pointing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_mjd REAL NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    source TEXT,
    recorded_at REAL NOT NULL,
    UNIQUE(timestamp_mjd, source)
);

CREATE INDEX IF NOT EXISTS idx_pointing_time ON pointing_history(timestamp_mjd);

-- ---------------------------------------------------------------------------
-- Queue Domain
-- ---------------------------------------------------------------------------

-- Ingest/processing queue with state machine
CREATE TABLE IF NOT EXISTS processing_queue (
    group_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,  -- collecting, pending, in_progress, completed, failed
    received_at REAL NOT NULL,
    last_update REAL NOT NULL,
    expected_subbands INTEGER,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    error_message TEXT,
    checkpoint_path TEXT,
    processing_stage TEXT DEFAULT 'collecting',
    chunk_minutes REAL,
    has_calibrator INTEGER DEFAULT NULL,
    calibrators TEXT
);

CREATE INDEX IF NOT EXISTS idx_queue_state ON processing_queue(state);
CREATE INDEX IF NOT EXISTS idx_queue_received ON processing_queue(received_at);

-- Subband files for each group
CREATE TABLE IF NOT EXISTS subband_files (
    group_id TEXT NOT NULL,
    subband_idx INTEGER NOT NULL,
    path TEXT NOT NULL UNIQUE,
    PRIMARY KEY (group_id, subband_idx),
    FOREIGN KEY (group_id) REFERENCES processing_queue(group_id)
);

-- Performance metrics for processed groups
CREATE TABLE IF NOT EXISTS performance_metrics (
    group_id TEXT PRIMARY KEY,
    load_time REAL,
    phase_time REAL,
    write_time REAL,
    total_time REAL,
    writer_type TEXT,
    recorded_at REAL NOT NULL,
    FOREIGN KEY (group_id) REFERENCES processing_queue(group_id)
);

-- Dead letter queue for failed items
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_table TEXT NOT NULL,
    original_id TEXT NOT NULL,
    error_message TEXT,
    payload TEXT,
    failed_at REAL NOT NULL,
    retry_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_dlq_table ON dead_letter_queue(original_table);

-- ---------------------------------------------------------------------------
-- Storage Locations (moved from products)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS storage_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    location_type TEXT NOT NULL,  -- 'ms', 'image', 'caltable', 'hdf5'
    size_bytes INTEGER,
    created_at REAL NOT NULL,
    last_checked REAL,
    status TEXT DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_storage_type ON storage_locations(location_type);
CREATE INDEX IF NOT EXISTS idx_storage_status ON storage_locations(status);

-- ---------------------------------------------------------------------------
-- Alert History (from alerts.sqlite3)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    triggered_at REAL NOT NULL,
    resolved_at REAL,
    acknowledged_by TEXT,
    acknowledged_at REAL
);

CREATE INDEX IF NOT EXISTS idx_alerts_name ON alert_history(alert_name);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alert_history(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON alert_history(triggered_at);

-- ---------------------------------------------------------------------------
-- Jobs Domain (from products.sqlite3)
-- ---------------------------------------------------------------------------

-- Individual processing jobs
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    ms_path TEXT NOT NULL,
    params TEXT,
    logs TEXT,
    artifacts TEXT,
    created_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_ms_path ON jobs(ms_path);

-- Batch job containers
CREATE TABLE IF NOT EXISTS batch_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    created_at REAL NOT NULL,
    status TEXT NOT NULL,
    total_items INTEGER NOT NULL,
    completed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    params TEXT
);

CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(status);

-- Items within batch jobs
CREATE TABLE IF NOT EXISTS batch_job_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    ms_path TEXT NOT NULL,
    job_id INTEGER,
    status TEXT NOT NULL,
    error TEXT,
    started_at REAL,
    completed_at REAL,
    data_id TEXT DEFAULT NULL,
    FOREIGN KEY (batch_id) REFERENCES batch_jobs(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_batch_items_batch_id ON batch_job_items(batch_id);
CREATE INDEX IF NOT EXISTS idx_batch_items_ms_path ON batch_job_items(ms_path);

-- ---------------------------------------------------------------------------
-- QA Domain (from products.sqlite3)
-- ---------------------------------------------------------------------------

-- Generic QA artifacts
CREATE TABLE IF NOT EXISTS qa_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(group_id, name)
);

CREATE INDEX IF NOT EXISTS idx_qa_artifacts_group ON qa_artifacts(group_id);

-- Image quality assessment
CREATE TABLE IF NOT EXISTS image_qa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ms_path TEXT NOT NULL,
    job_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    rms_noise REAL,
    peak_flux REAL,
    dynamic_range REAL,
    beam_major REAL,
    beam_minor REAL,
    beam_pa REAL,
    num_sources INTEGER,
    thumbnail_path TEXT,
    overall_quality TEXT,
    timestamp REAL NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_img_qa_ms_path ON image_qa(ms_path);
CREATE INDEX IF NOT EXISTS idx_img_qa_job ON image_qa(job_id);

-- Calibration quality assessment
CREATE TABLE IF NOT EXISTS calibration_qa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ms_path TEXT NOT NULL,
    job_id INTEGER NOT NULL,
    k_metrics TEXT,
    bp_metrics TEXT,
    g_metrics TEXT,
    overall_quality TEXT,
    flags_total REAL,
    timestamp REAL NOT NULL,
    per_spw_stats TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_cal_qa_ms_path ON calibration_qa(ms_path);
CREATE INDEX IF NOT EXISTS idx_cal_qa_job ON calibration_qa(job_id);

-- ---------------------------------------------------------------------------
-- Mosaic Domain (from products.sqlite3)
-- ---------------------------------------------------------------------------

-- Mosaic products
CREATE TABLE IF NOT EXISTS mosaics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at REAL NOT NULL,
    start_mjd REAL NOT NULL,
    end_mjd REAL NOT NULL,
    integration_sec REAL,
    n_images INTEGER,
    center_ra_deg REAL,
    center_dec_deg REAL,
    dec_min_deg REAL,
    dec_max_deg REAL,
    noise_jy REAL,
    beam_major_arcsec REAL,
    beam_minor_arcsec REAL,
    beam_pa_deg REAL,
    n_sources INTEGER,
    thumbnail_path TEXT,
    status TEXT,
    method TEXT,
    tiles TEXT,
    output_path TEXT,
    validation_issues TEXT,
    metrics_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_mosaics_name ON mosaics(name);
CREATE INDEX IF NOT EXISTS idx_mosaics_status ON mosaics(status);
CREATE INDEX IF NOT EXISTS idx_mosaics_time ON mosaics(start_mjd, end_mjd);

-- Mosaic groups (MS files grouped for mosaicking)
CREATE TABLE IF NOT EXISTS mosaic_groups (
    group_id TEXT PRIMARY KEY,
    mosaic_id TEXT,
    ms_paths TEXT NOT NULL,
    calibration_ms_path TEXT,
    bpcal_solved INTEGER DEFAULT 0,
    created_at REAL NOT NULL,
    calibrated_at REAL,
    imaged_at REAL,
    mosaicked_at REAL,
    status TEXT DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_mosaic_groups_status ON mosaic_groups(status);
CREATE INDEX IF NOT EXISTS idx_mosaic_groups_mosaic ON mosaic_groups(mosaic_id);

-- Image regions/annotations
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    coordinates TEXT NOT NULL,
    image_path TEXT NOT NULL,
    created_at REAL NOT NULL,
    created_by TEXT,
    updated_at REAL,
    FOREIGN KEY (image_path) REFERENCES images(path)
);

CREATE INDEX IF NOT EXISTS idx_regions_image ON regions(image_path);
CREATE INDEX IF NOT EXISTS idx_regions_type ON regions(type);
CREATE INDEX IF NOT EXISTS idx_regions_name ON regions(name);

-- ---------------------------------------------------------------------------
-- Transient Domain (from products.sqlite3)
-- ---------------------------------------------------------------------------

-- Transient candidates
CREATE TABLE IF NOT EXISTS transient_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    detection_type TEXT NOT NULL,
    flux_obs_mjy REAL NOT NULL,
    flux_baseline_mjy REAL,
    flux_ratio REAL,
    significance_sigma REAL NOT NULL,
    baseline_catalog TEXT,
    detected_at REAL NOT NULL,
    mosaic_id INTEGER,
    classification TEXT,
    variability_index REAL,
    last_updated REAL NOT NULL,
    notes TEXT,
    classified_by TEXT,
    classified_at REAL,
    follow_up_status TEXT,
    FOREIGN KEY (mosaic_id) REFERENCES mosaics(id)
);

CREATE INDEX IF NOT EXISTS idx_transients_type ON transient_candidates(detection_type, significance_sigma DESC);
CREATE INDEX IF NOT EXISTS idx_transients_coords ON transient_candidates(ra_deg, dec_deg);
CREATE INDEX IF NOT EXISTS idx_transients_detected ON transient_candidates(detected_at DESC);

-- Transient alerts
CREATE TABLE IF NOT EXISTS transient_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    alert_level TEXT NOT NULL,
    alert_message TEXT NOT NULL,
    created_at REAL NOT NULL,
    acknowledged INTEGER DEFAULT 0,
    acknowledged_at REAL,
    acknowledged_by TEXT,
    follow_up_status TEXT,
    notes TEXT,
    FOREIGN KEY (candidate_id) REFERENCES transient_candidates(id)
);

CREATE INDEX IF NOT EXISTS idx_transient_alerts_level ON transient_alerts(alert_level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transient_alerts_status ON transient_alerts(acknowledged, created_at DESC);

-- Transient light curves
CREATE TABLE IF NOT EXISTS transient_lightcurves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    mjd REAL NOT NULL,
    flux_mjy REAL NOT NULL,
    flux_err_mjy REAL,
    frequency_ghz REAL NOT NULL,
    mosaic_id INTEGER,
    measured_at REAL NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES transient_candidates(id),
    FOREIGN KEY (mosaic_id) REFERENCES mosaics(id)
);

CREATE INDEX IF NOT EXISTS idx_lightcurves_candidate ON transient_lightcurves(candidate_id, mjd);

-- ---------------------------------------------------------------------------
-- Variability Domain (from products.sqlite3)
-- ---------------------------------------------------------------------------

-- Source variability statistics
CREATE TABLE IF NOT EXISTS variability_stats (
    source_id TEXT PRIMARY KEY,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    nvss_flux_mjy REAL,
    n_obs INTEGER DEFAULT 0,
    mean_flux_mjy REAL,
    std_flux_mjy REAL,
    min_flux_mjy REAL,
    max_flux_mjy REAL,
    chi2_nu REAL,
    sigma_deviation REAL,
    last_measured_at REAL,
    last_mjd REAL,
    updated_at REAL NOT NULL,
    eta_metric REAL
);

CREATE INDEX IF NOT EXISTS idx_variability_chi2 ON variability_stats(chi2_nu);
CREATE INDEX IF NOT EXISTS idx_variability_sigma ON variability_stats(sigma_deviation);
CREATE INDEX IF NOT EXISTS idx_variability_last_mjd ON variability_stats(last_mjd);
CREATE INDEX IF NOT EXISTS idx_variability_eta ON variability_stats(eta_metric);

-- Monitored sources for variability tracking
CREATE TABLE IF NOT EXISTS monitoring_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT UNIQUE NOT NULL,
    name TEXT,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    catalog TEXT,
    priority TEXT DEFAULT 'normal',
    n_detections INTEGER DEFAULT 0,
    mean_flux_jy REAL,
    std_flux_jy REAL,
    eta REAL,
    v_index REAL,
    chi_squared REAL,
    is_variable INTEGER DEFAULT 0,
    ese_candidate INTEGER DEFAULT 0,
    first_detected_at REAL,
    last_detected_at REAL,
    last_updated REAL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_monitoring_source_id ON monitoring_sources(source_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_variable ON monitoring_sources(is_variable);

-- Extreme scattering event candidates
CREATE TABLE IF NOT EXISTS ese_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    flagged_at REAL NOT NULL,
    flagged_by TEXT DEFAULT 'auto',
    significance REAL NOT NULL,
    flag_type TEXT NOT NULL,
    notes TEXT,
    status TEXT DEFAULT 'active',
    investigated_at REAL,
    dismissed_at REAL,
    FOREIGN KEY (source_id) REFERENCES variability_stats(source_id)
);

CREATE INDEX IF NOT EXISTS idx_ese_source ON ese_candidates(source_id);
CREATE INDEX IF NOT EXISTS idx_ese_status ON ese_candidates(status);
CREATE INDEX IF NOT EXISTS idx_ese_flagged ON ese_candidates(flagged_at);

-- ---------------------------------------------------------------------------
-- Astrometry Domain (from products.sqlite3)
-- ---------------------------------------------------------------------------

-- Astrometric solutions
CREATE TABLE IF NOT EXISTS astrometric_solutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mosaic_id INTEGER NOT NULL,
    reference_catalog TEXT NOT NULL,
    n_matches INTEGER NOT NULL,
    ra_offset_mas REAL NOT NULL,
    dec_offset_mas REAL NOT NULL,
    ra_offset_err_mas REAL NOT NULL,
    dec_offset_err_mas REAL NOT NULL,
    rotation_deg REAL,
    scale_factor REAL,
    rms_residual_mas REAL NOT NULL,
    applied INTEGER DEFAULT 0,
    computed_at REAL NOT NULL,
    applied_at REAL,
    notes TEXT,
    FOREIGN KEY (mosaic_id) REFERENCES mosaics(id)
);

CREATE INDEX IF NOT EXISTS idx_astrometry_mosaic ON astrometric_solutions(mosaic_id, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_astrometry_applied ON astrometric_solutions(applied, computed_at DESC);

-- Astrometric residuals per source
CREATE TABLE IF NOT EXISTS astrometric_residuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    solution_id INTEGER NOT NULL,
    source_ra_deg REAL NOT NULL,
    source_dec_deg REAL NOT NULL,
    reference_ra_deg REAL NOT NULL,
    reference_dec_deg REAL NOT NULL,
    ra_offset_mas REAL NOT NULL,
    dec_offset_mas REAL NOT NULL,
    separation_mas REAL NOT NULL,
    source_flux_mjy REAL,
    reference_flux_mjy REAL,
    measured_at REAL NOT NULL,
    FOREIGN KEY (solution_id) REFERENCES astrometric_solutions(id)
);

CREATE INDEX IF NOT EXISTS idx_residuals_solution ON astrometric_residuals(solution_id);

-- ---------------------------------------------------------------------------
-- VLA Calibrators Domain (from calibrators.sqlite3)
-- ---------------------------------------------------------------------------

-- VLA calibrator catalog
CREATE TABLE IF NOT EXISTS vla_calibrators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_jy REAL,
    flux_freq_ghz REAL,
    code_20_cm TEXT,
    registered_at REAL NOT NULL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_vla_radec ON vla_calibrators(ra_deg, dec_deg);
CREATE INDEX IF NOT EXISTS idx_vla_name ON vla_calibrators(name);

-- VLA flux measurements at different frequencies
CREATE TABLE IF NOT EXISTS vla_flux_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vla_calibrator_id INTEGER NOT NULL,
    frequency_ghz REAL NOT NULL,
    flux_jy REAL NOT NULL,
    flux_uncertainty REAL,
    measurement_date TEXT,
    FOREIGN KEY (vla_calibrator_id) REFERENCES vla_calibrators(id),
    UNIQUE(vla_calibrator_id, frequency_ghz)
);

CREATE INDEX IF NOT EXISTS idx_vla_flux_cal ON vla_flux_info(vla_calibrator_id);

-- Generic catalog sources (crossmatch reference)
CREATE TABLE IF NOT EXISTS catalog_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_jy REAL,
    flux_freq_ghz REAL,
    spectral_index REAL,
    catalog TEXT NOT NULL,
    catalog_id TEXT,
    position_uncertainty_arcsec REAL,
    flux_uncertainty REAL,
    is_extended INTEGER DEFAULT 0,
    major_axis_arcsec REAL,
    minor_axis_arcsec REAL,
    position_angle_deg REAL,
    matched_to TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(catalog, catalog_id)
);

CREATE INDEX IF NOT EXISTS idx_catalog_radec ON catalog_sources(ra_deg, dec_deg);
CREATE INDEX IF NOT EXISTS idx_catalog_name ON catalog_sources(source_name);
CREATE INDEX IF NOT EXISTS idx_catalog_type ON catalog_sources(catalog);

-- Sky model metadata for calibrator fields
CREATE TABLE IF NOT EXISTS skymodel_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field_id TEXT NOT NULL,
    skymodel_path TEXT NOT NULL,
    n_sources INTEGER NOT NULL,
    total_flux_jy REAL,
    created_at REAL NOT NULL,
    created_by TEXT,
    notes TEXT,
    UNIQUE(field_id, skymodel_path)
);

CREATE INDEX IF NOT EXISTS idx_skymodel_field ON skymodel_metadata(field_id);

-- Bandpass calibrators registry
CREATE TABLE IF NOT EXISTS bandpass_calibrators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calibrator_name TEXT NOT NULL UNIQUE,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    dec_range_min REAL,
    dec_range_max REAL,
    source_catalog TEXT,
    flux_jy REAL,
    registered_at REAL NOT NULL,
    registered_by TEXT,
    status TEXT DEFAULT 'active',
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_bp_dec_range ON bandpass_calibrators(dec_range_min, dec_range_max);
CREATE INDEX IF NOT EXISTS idx_bp_status ON bandpass_calibrators(status);
CREATE INDEX IF NOT EXISTS idx_bp_name ON bandpass_calibrators(calibrator_name);

-- Gain calibrators per field
CREATE TABLE IF NOT EXISTS gain_calibrators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_jy REAL,
    catalog_source TEXT,
    catalog_id TEXT,
    created_at REAL NOT NULL,
    skymodel_path TEXT,
    notes TEXT,
    UNIQUE(field_id, source_name)
);

CREATE INDEX IF NOT EXISTS idx_gain_field ON gain_calibrators(field_id);
