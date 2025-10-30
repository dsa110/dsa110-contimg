/**
 * TypeScript type definitions for DSA-110 pipeline API.
 */

export interface QueueStats {
  total: number;
  pending: number;
  in_progress: number;
  failed: number;
  completed: number;
  collecting: number;
}

export interface CalibrationSet {
  id: string;
  name: string;
  created_at: string;
}

export interface QueueGroup {
  group_id: string;
  state: string;
  subbands_present: number;
  expected_subbands: number;
  has_calibrator?: boolean;
}

export interface PipelineStatus {
  queue: QueueStats;
  recent_groups: QueueGroup[];
  calibration_sets: CalibrationSet[];
  matched_recent: number;
}

export interface SystemMetrics {
  ts: string;
  cpu_percent: number;
  mem_percent: number;
  mem_total: number;
  mem_used: number;
  disk_total: number;
  disk_used: number;
  load_1: number;
  load_5: number;
  load_15: number;
}

export interface CalibratorMatch {
  source_id: string;
  ra_deg: number;
  dec_deg: number;
  flux_jy: number;
  catalog: string;
}

// New types for enhanced features

export interface ESECandidate {
  id?: number;
  source_id: string;
  ra_deg: number;
  dec_deg: number;
  first_detection_at: string;
  last_detection_at: string;
  max_sigma_dev: number;
  current_flux_jy: number;
  baseline_flux_jy: number;
  status: 'active' | 'resolved' | 'false_positive';
  notes?: string;
}

export interface Mosaic {
  id?: number;
  name: string;
  path: string;
  start_mjd: number;
  end_mjd: number;
  start_time: string;
  end_time: string;
  created_at: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  image_count: number;
  noise_jy: number;
  source_count: number;
  thumbnail_path?: string;
}

export interface SourceFluxPoint {
  mjd: number;
  time: string;
  flux_jy: number;
  flux_err_jy: number;
  image_id: string;
}

export interface SourceTimeseries {
  source_id: string;
  ra_deg: number;
  dec_deg: number;
  catalog: string;
  flux_points: SourceFluxPoint[];
  mean_flux_jy: number;
  std_flux_jy: number;
  chi_sq_nu: number;
  is_variable: boolean;
}

export interface AlertHistory {
  id: number;
  source_id: string;
  alert_type: 'ESE_CANDIDATE' | 'CALIBRATOR_ISSUE' | 'SYSTEM_WARNING';
  severity: 'info' | 'warning' | 'critical';
  message: string;
  triggered_at: string;
  resolved_at?: string;
}

export interface UserPreferences {
  user_id: string;
  ese_sigma_threshold: number;
  slack_webhook_url?: string;
  slack_alert_channel?: string;
}

// Request/Response types for new endpoints

export interface MosaicQueryRequest {
  start_time: string;
  end_time: string;
}

export interface MosaicQueryResponse {
  mosaics: Mosaic[];
  total: number;
}

export interface ESECandidatesResponse {
  candidates: ESECandidate[];
  total: number;
}

export interface SourceSearchRequest {
  source_id?: string;
  ra_deg?: number;
  dec_deg?: number;
  radius_arcmin?: number;
  limit?: number;
}

export interface SourceSearchResponse {
  sources: SourceTimeseries[];
  total: number;
}

// Control panel types

export interface JobParams {
  field?: string;
  refant?: string;
  gaintables?: string[];
  gridder?: string;
  wprojplanes?: number;
  datacolumn?: string;
  quick?: boolean;
  skip_fits?: boolean;
}

export interface Job {
  id: number;
  type: string;
  status: string;
  ms_path: string;
  params: JobParams;
  logs?: string;
  artifacts: string[];
  created_at: string;
  started_at?: string;
  finished_at?: string;
}

export interface JobList {
  items: Job[];
}

export interface JobCreateRequest {
  ms_path: string;
  params: JobParams;
}

/**
 * Measurement Set list entry with enhanced status information.
 * Includes calibrator detection, QA metrics, and processing status.
 */
export interface MSListEntry {
  // Basic MS info
  path: string;
  mid_mjd?: number;
  status?: string;
  cal_applied?: number;
  
  // Calibrator info (from calibrator matching)
  has_calibrator: boolean;
  calibrator_name?: string;
  calibrator_quality?: 'excellent' | 'good' | 'marginal' | 'poor';
  
  // Processing status
  is_calibrated: boolean;
  is_imaged: boolean;
  
  // QA metrics (from calibration_qa and image_qa tables)
  calibration_quality?: 'excellent' | 'good' | 'marginal' | 'poor' | 'unknown';
  image_quality?: 'excellent' | 'good' | 'marginal' | 'poor' | 'unknown';
  
  // File info
  size_gb?: number;
  start_time?: string;  // ISO 8601 format
}

/**
 * MS list with pagination and filtering metadata.
 */
export interface MSList {
  items: MSListEntry[];
  total: number;      // Total MS count before filtering
  filtered: number;   // Count after filtering
}

/**
 * Filters for MS list queries.
 * All filters are optional and can be combined.
 */
export interface MSListFilters {
  search?: string;                    // Search in path or calibrator name
  has_calibrator?: boolean;           // Filter by calibrator presence
  is_calibrated?: boolean;            // Filter by calibration status
  is_imaged?: boolean;                // Filter by imaging status
  calibrator_quality?: 'excellent' | 'good' | 'marginal' | 'poor';
  start_date?: string;                // YYYY-MM-DD format
  end_date?: string;                  // YYYY-MM-DD format
  sort_by?: 'time_desc' | 'time_asc' | 'name_asc' | 'name_desc' | 'size_asc' | 'size_desc';
  limit?: number;                     // Pagination limit (default: 100)
  offset?: number;                    // Pagination offset (default: 0)
  scan?: boolean;                     // If true, scan filesystem before listing
  scan_dir?: string;                  // Directory to scan (defaults to configured MS directory)
}

// UVH5 file discovery types
export interface UVH5FileEntry {
  path: string;
  timestamp?: string;
  subband?: string;
  size_mb?: number;
}

export interface UVH5FileList {
  items: UVH5FileEntry[];
}

// Conversion job types
export interface ConversionJobParams {
  input_dir: string;
  output_dir: string;
  start_time: string;
  end_time: string;
  writer?: string;
  stage_to_tmpfs?: boolean;
  max_workers?: number;
}

export interface ConversionJobCreateRequest {
  params: ConversionJobParams;
}

// Calibration table models
export interface CalTableInfo {
  path: string;
  filename: string;
  table_type: string;
  size_mb: number;
  modified_time: string;
}

export interface CalTableList {
  items: CalTableInfo[];
}

// MS metadata models
export interface FieldInfo {
  field_id: number;
  name: string;
  ra_deg: number;
  dec_deg: number;
}

export interface AntennaInfo {
  antenna_id: number;
  name: string;
}

export interface FlaggingStats {
  total_fraction: number;
  per_antenna?: Record<string, number>;
  per_field?: Record<string, number>;
}

export interface MSMetadata {
  path: string;
  start_time?: string;
  end_time?: string;
  duration_sec?: number;
  num_fields?: number;
  field_names?: string[];
  fields?: FieldInfo[];
  freq_min_ghz?: number;
  freq_max_ghz?: number;
  num_channels?: number;
  num_antennas?: number;
  antennas?: AntennaInfo[];
  data_columns: string[];
  size_gb?: number;
  calibrated: boolean;
  flagging_stats?: FlaggingStats;
}

export interface CalTableCompatibility {
  is_compatible: boolean;
  caltable_path: string;
  ms_path: string;
  issues: string[];
  warnings: string[];
  ms_antennas: number[];
  caltable_antennas: number[];
  ms_freq_min_ghz?: number;
  ms_freq_max_ghz?: number;
  caltable_freq_min_ghz?: number;
  caltable_freq_max_ghz?: number;
}

// MS Calibrator match models
export interface MSCalibratorMatch {
  name: string;
  ra_deg: number;
  dec_deg: number;
  flux_jy: number;
  sep_deg: number;
  pb_response: number;
  weighted_flux: number;
  quality: 'excellent' | 'good' | 'marginal' | 'poor';
  recommended_fields?: number[];
}

export interface MSCalibratorMatchList {
  ms_path: string;
  pointing_dec: number;
  mid_mjd?: number;
  matches: MSCalibratorMatch[];
  has_calibrator: boolean;
}

// Enhanced calibration job parameters
export interface CalibrateJobParams {
  field?: string;
  refant?: string;
  
  // Cal table selection
  solve_delay?: boolean;     // K-cal
  solve_bandpass?: boolean;  // BP-cal
  solve_gains?: boolean;     // G-cal
  
  // Advanced options
  delay_solint?: string;
  bandpass_solint?: string;
  gain_solint?: string;
  gain_calmode?: 'ap' | 'p' | 'a';  // amp+phase, phase-only, amp-only
  
  // Field selection
  auto_fields?: boolean;
  manual_fields?: number[];
  
  // Catalog matching
  cal_catalog?: string;
  search_radius_deg?: number;
  min_pb?: number;
  
  // Flagging
  do_flagging?: boolean;
  
  // Existing table handling
  use_existing_tables?: 'auto' | 'manual' | 'none';
  existing_k_table?: string;
  existing_bp_table?: string;
  existing_g_table?: string;
}

// Existing cal table discovery
export interface ExistingCalTable {
  path: string;
  filename: string;
  size_mb: number;
  modified_time: string;
  age_hours: number;
}

export interface ExistingCalTables {
  ms_path: string;
  k_tables: ExistingCalTable[];
  bp_tables: ExistingCalTable[];
  g_tables: ExistingCalTable[];
  has_k: boolean;
  has_bp: boolean;
  has_g: boolean;
}

/**
 * Quality Assessment (QA) metrics types.
 * These mirror the backend Pydantic models for QA data.
 */

/**
 * Calibration QA metrics for a single MS.
 * Contains metrics for K, BP, and G calibration tables.
 */
export interface CalibrationQA {
  ms_path: string;
  job_id: number;
  k_metrics?: {
    flag_fraction?: number;
    avg_snr?: number;
  };
  bp_metrics?: {
    flag_fraction?: number;
    amp_mean?: number;
    amp_std?: number;
  };
  g_metrics?: {
    flag_fraction?: number;
    amp_mean?: number;
  };
  overall_quality: 'excellent' | 'good' | 'marginal' | 'poor' | 'unknown';
  flags_total?: number;
  timestamp: string;
}

/**
 * Image QA metrics for a single MS.
 * Contains image statistics and quality assessment.
 */
export interface ImageQA {
  ms_path: string;
  job_id: number;
  image_path: string;
  rms_noise?: number;          // Jy/beam
  peak_flux?: number;           // Jy/beam
  dynamic_range?: number;      // peak_flux / rms_noise
  beam_major?: number;          // arcsec
  beam_minor?: number;          // arcsec
  beam_pa?: number;             // degrees
  num_sources?: number;
  thumbnail_path?: string;
  overall_quality: 'excellent' | 'good' | 'marginal' | 'poor' | 'unknown';
  timestamp: string;
}

/**
 * Combined QA metrics (calibration + image) for an MS.
 */
export interface QAMetrics {
  ms_path: string;
  calibration_qa?: CalibrationQA;
  image_qa?: ImageQA;
}

/**
 * Batch job types for processing multiple MS files.
 */

/**
 * Status of a single item within a batch job.
 */
export interface BatchJobStatus {
  ms_path: string;
  job_id?: number;
  status: 'pending' | 'running' | 'done' | 'failed' | 'cancelled';
  error?: string;
  started_at?: string;
  completed_at?: string;
}

/**
 * Batch job containing multiple MS processing tasks.
 */
export interface BatchJob {
  id: number;
  type: string;
  created_at: string;
  status: 'pending' | 'running' | 'done' | 'failed' | 'cancelled';
  total_items: number;
  completed_items: number;
  failed_items: number;
  params: Record<string, any>;
  items: BatchJobStatus[];
}

/**
 * List of batch jobs.
 */
export interface BatchJobList {
  items: BatchJob[];
}

/**
 * Parameters for batch calibration.
 */
export interface BatchCalibrateParams {
  ms_paths: string[];
  params: CalibrateJobParams;
}

/**
 * Parameters for batch apply.
 */
export interface BatchApplyParams {
  ms_paths: string[];
  params: JobParams;
}

/**
 * Parameters for batch imaging.
 */
export interface BatchImageParams {
  ms_paths: string[];
  params: JobParams;
}

/**
 * Request to create a batch job.
 */
export interface BatchJobCreateRequest {
  job_type: 'calibrate' | 'apply' | 'image';
  params: BatchCalibrateParams | BatchApplyParams | BatchImageParams;
}

// Workflow models
export interface WorkflowParams {
  start_time: string;
  end_time: string;
  input_dir?: string;
  output_dir?: string;
  writer?: string;
  stage_to_tmpfs?: boolean;
  max_workers?: number;
  field?: string;
  refant?: string;
  gridder?: string;
  wprojplanes?: number;
}

export interface WorkflowJobCreateRequest {
  params: WorkflowParams;
}
