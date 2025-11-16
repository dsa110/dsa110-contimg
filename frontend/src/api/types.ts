// Dead Letter Queue Types
export interface DLQItem {
  id: number;
  component: string;
  operation: string;
  error_type: string;
  error_message: string;
  context: Record<string, any>;
  created_at: number;
  retry_count: number;
  status: "pending" | "retrying" | "resolved" | "failed";
  resolved_at?: number;
  resolution_note?: string;
}

export interface DLQStats {
  total: number;
  pending: number;
  retrying: number;
  resolved: number;
  failed: number;
}

export interface DLQRetryRequest {
  note?: string;
}

export interface DLQResolveRequest {
  note?: string;
}

// Circuit Breaker Types
export interface CircuitBreakerState {
  name: string;
  state: "closed" | "open" | "half_open";
  failure_count: number;
  last_failure_time?: number;
  recovery_timeout: number;
}

export interface CircuitBreakerList {
  circuit_breakers: CircuitBreakerState[];
}

// Pipeline Types
export type StageStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface StageStatusResponse {
  name: string;
  status: StageStatus;
  duration_seconds?: number;
  attempt: number;
  error_message?: string;
  started_at?: number;
  completed_at?: number;
}

export interface PipelineExecutionResponse {
  id: number;
  job_type: string;
  status: string;
  created_at: number;
  started_at?: number;
  finished_at?: number;
  duration_seconds?: number;
  stages: StageStatusResponse[];
  error_message?: string;
  retry_count: number;
}

export interface StageMetricsResponse {
  stage_name: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_duration_seconds: number;
  min_duration_seconds: number;
  max_duration_seconds: number;
  average_memory_mb?: number;
  average_cpu_percent?: number;
}

export interface DependencyGraphNode {
  id: string;
  label: string;
  type: string;
}

export interface DependencyGraphEdge {
  from: string;
  to: string;
  type: string;
}

export interface DependencyGraphResponse {
  nodes: DependencyGraphNode[];
  edges: DependencyGraphEdge[];
}

export interface PipelineMetricsSummary {
  total_jobs: number;
  running_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  success_rate: number;
  average_duration_seconds: number;
  timestamp: string;
}

// Event Bus Types (Phase 3)
export interface EventStreamItem {
  event_type: string;
  timestamp: number;
  timestamp_iso: string;
  [key: string]: any; // Additional event-specific fields
}

export interface EventStatistics {
  total_events: number;
  events_in_history: number;
  events_per_type: Record<string, number>;
  events_last_minute: number;
  events_last_hour: number;
  subscribers: Record<string, number>;
  event_types?: string[];
}

export interface EventType {
  value: string;
  name: string;
}

export interface EventTypesResponse {
  event_types: EventType[];
}

// Cache Types (Phase 3)
export interface CacheStatistics {
  backend_type: string;
  total_keys: number;
  active_keys: number;
  hits: number;
  misses: number;
  sets: number;
  deletes: number;
  hit_rate: number;
  miss_rate: number;
  total_requests: number;
}

export interface CacheKeyInfo {
  key: string;
  exists: boolean;
  has_value: boolean;
}

export interface CacheKeysResponse {
  keys: CacheKeyInfo[];
  total: number;
}

export interface CacheKeyDetail {
  key: string;
  value: any;
  value_type: string;
  value_size: number;
}

export interface CachePerformance {
  hit_rate: number;
  miss_rate: number;
  total_requests: number;
  hits: number;
  misses: number;
  backend_type: string;
}

// Source Search Types
export interface SourceFluxPoint {
  mjd: number;
  time?: string;
  flux_jy: number;
  flux_err_jy: number;
  image_id?: string;
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
  variability_index?: number;
  ese_candidate?: boolean;
  is_variable?: boolean;
}

export interface SourceSearchRequest {
  source_id?: string;
  limit?: number;
  variability_threshold?: number;
  ese_only?: boolean;
  dec_min?: number;
  dec_max?: number;
  ra_min?: number;
  ra_max?: number;
}

export interface SourceSearchResponse {
  sources: SourceTimeseries[];
  total: number;
}

// Image Types
export interface ImageInfo {
  id: number;
  path: string;
  ms_path: string;
  created_at?: string | null;
  type: string;
  source_id?: string | null;
  beam_major_arcsec?: number | null;
  beam_minor_arcsec?: number | null;
  beam_pa_deg?: number | null;
  noise_jy?: number | null;
  peak_flux_jy?: number | null;
  pbcor: boolean;
  center_ra_deg?: number | null;
  center_dec_deg?: number | null;
  image_size_deg?: number | null;
  pixel_size_arcsec?: number | null;
  calibrated?: boolean;
  fov_deg?: number;
  frequency_hz?: number;
  bandwidth_hz?: number;
  nchan?: number;
  npol?: number;
  naxis?: number[];
  bunit?: string;
  bmaj?: number;
  bmin?: number;
  bpa?: number;
  rms?: number;
  peak?: number;
}

// Additional types from backend API models
// QueueGroup interface for queue item details
export interface QueueGroup {
  group_id: string;
  state: string;
  received_at: string;
  last_update: string;
  subbands_present: number;
  expected_subbands: number;
  has_calibrator?: boolean | null;
  matches?: CalibratorMatch[] | null;
}

export interface QueueStats {
  total: number;
  pending: number;
  in_progress: number;
  failed: number;
  completed: number;
  collecting: number;
}

export interface CalibrationSet {
  set_name: string;
  tables: string[];
  active: number;
  total: number;
}

export interface PipelineStatus {
  queue: QueueStats;
  recent_groups: QueueGroup[];
  calibration_sets: CalibrationSet[];
  matched_recent?: number;
}

export interface SystemMetrics {
  ts: string;
  cpu_percent?: number | null;
  mem_percent?: number | null;
  mem_total?: number | null;
  mem_used?: number | null;
  disk_total?: number | null;
  disk_used?: number | null;
  disks?: DiskInfo[];
  load_1?: number | null;
  load_5?: number | null;
  load_15?: number | null;
}

export interface DatabaseMetrics {
  total_operations: number;
  error_count: number;
  error_rate: number;
  avg_duration: number;
  min_duration: number;
  max_duration: number;
  p50_duration: number;
  p95_duration: number;
  p99_duration: number;
}

export interface DiskInfo {
  mount_point: string;
  total: number;
  used: number;
  free: number;
  percent: number;
}

export interface CalibratorMatch {
  name: string;
  ra_deg: number;
  dec_deg: number;
  sep_deg: number;
  weighted_flux?: number | null;
}

export interface ESECandidatesResponse {
  candidates: ESECandidate[];
  total?: number;
}

export interface ESECandidate {
  source_id: string;
  ra_deg: number;
  dec_deg: number;
  variability_sigma: number;
  first_detection?: string;
  last_detection?: string;
  last_detection_at?: string;
  first_detection_at?: string;
  max_sigma_dev?: number;
  current_flux_jy?: number;
  baseline_flux_jy?: number;
  status?: string;
}

export interface MosaicQueryRequest {
  start_mjd?: number;
  end_mjd?: number;
  ra_deg?: number;
  dec_deg?: number;
  radius_deg?: number;
  start_time?: string;
  end_time?: string;
}

export interface MosaicQueryResponse {
  items: Mosaic[];
  total?: number;
  mosaics?: Mosaic[];
}

export interface Mosaic {
  id: string;
  center_ra_deg: number;
  center_dec_deg: number;
  start_mjd: number;
  end_mjd: number;
  image_count: number;
  name?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
  noise_jy?: number;
  source_count?: number;
  created_at?: string;
  path?: string;
  thumbnail_path?: string;
}

export interface AlertHistory {
  items: Alert[];
  total?: number;
}

export interface Alert {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  category?: string;
}

export interface MSList {
  items: MSListEntry[];
  total?: number;
  filtered?: MSListEntry[];
}

export interface MSListEntry {
  path: string;
  start_mjd?: number | null;
  end_mjd?: number | null;
  mid_mjd?: number | null;
  processed_at?: string | null;
  status?: string | null;
  stage?: string | null;
  stage_updated_at?: string | null;
  cal_applied?: number | null;
  imagename?: string | null;
  has_calibrator?: boolean;
  calibrator_name?: string | null;
  calibrator_quality?: string | null;
  is_calibrated?: boolean | null;
  is_imaged?: boolean | null;
  calibration_quality?: string | null;
  image_quality?: string | null;
  size_gb?: number | null;
  start_time?: string | null;
}

export interface MSListFilters {
  start_mjd?: number;
  end_mjd?: number;
  status?: string;
  stage?: string;
  scan?: string;
  search?: string;
  has_calibrator?: boolean;
  is_calibrated?: boolean;
  is_imaged?: boolean;
  calibrator_quality?: string;
  start_date?: string;
  end_date?: string;
  sort_by?: string;
  limit?: number;
  offset?: number;
  scan_dir?: string;
}

export interface MSMetadata {
  path: string;
  field_name?: string;
  ra_deg?: number;
  dec_deg?: number;
  start_mjd?: number;
  end_mjd?: number;
  start_time?: string;
  end_time?: string;
  duration_sec?: number;
  freq_min_ghz?: number;
  freq_max_ghz?: number;
  num_channels?: number;
  size_gb?: number;
  data_columns?: string[];
  calibrated?: boolean;
  num_fields?: number;
  field_names?: string[];
  num_antennas?: number;
  antennas?: AntennaInfo[];
  fields?: FieldInfo[];
  flagging_stats?: FlaggingStats;
}

export interface FieldInfo {
  id: number;
  name: string;
  ra_deg: number;
  dec_deg: number;
  field_id?: number;
}

export interface AntennaInfo {
  name: string;
  position: number[];
  antenna_id?: number;
}

export interface FlaggingStats {
  total_flagged?: number;
  percent_flagged?: number;
  total_fraction?: number;
  per_antenna?: Record<string, number>;
  per_field?: Record<string, number>;
}

export interface CalTableCompatibility {
  ms_path: string;
  compatible_tables: string[];
  incompatible_tables: string[];
}

export interface JobList {
  items: Job[];
  total?: number;
}

export interface Job {
  id: string;
  type: string;
  status: string;
  created_at: string;
  updated_at?: string;
  params?: Record<string, unknown>;
}

export interface JobCreateRequest {
  type: string;
  params: Record<string, unknown>;
}

export interface UVH5FileList {
  items: UVH5FileEntry[];
  total?: number;
}

export interface UVH5FileEntry {
  path: string;
  size?: number;
  modified_at?: string;
  size_mb?: number;
}

export interface ConversionJobCreateRequest {
  input_files: string[];
  output_dir?: string;
  params?: Record<string, unknown>;
}

export interface CalTableList {
  items: CalTableInfo[];
  total?: number;
}

export interface CalTableInfo {
  path: string;
  type?: string;
  created_at?: string;
  table_type?: string;
  filename?: string;
  size_mb?: number;
}

export interface MSCalibratorMatchList {
  items: MSCalibratorMatch[];
  matches?: MSCalibratorMatch[];
}

export interface MSCalibratorMatch {
  ms_path: string;
  matches: CalibratorMatch[];
}

export interface ExistingCalTables {
  ms_path?: string;
  items?: ExistingCalTable[];
  k_tables?: ExistingCalTable[];
  ba_tables?: ExistingCalTable[];
  bp_tables?: ExistingCalTable[];
  g_tables?: ExistingCalTable[];
  has_k?: boolean;
  has_bp?: boolean;
  has_g?: boolean;
}

export interface ExistingCalTable {
  path: string;
  filename: string;
  type?: string;
  size_mb?: number;
  age_hours?: number;
  modified_time?: string;
  created_at?: string;
}

export interface WorkflowJobCreateRequest {
  workflow_type: string;
  params: Record<string, unknown>;
}

export interface PerSPWStats {
  spw_id?: number;
  total_solutions?: number;
  flagged_solutions?: number;
  fraction_flagged?: number;
  n_channels?: number;
  channels_with_high_flagging?: number;
  avg_flagged_per_channel?: number;
  max_flagged_in_channel?: number;
  is_problematic?: boolean;
}

export interface CalibrationQA {
  group_id: string;
  artifacts: QAArtifact[];
  overall_quality?: string;
  flags_total?: number;
  k_metrics?: Record<string, unknown>;
  g_metrics?: Record<string, unknown>;
  bp_metrics?: Record<string, unknown>;
  per_spw_stats?: PerSPWStats[] | Record<string, unknown>;
}

export interface QAArtifact {
  group_id: string;
  name: string;
  path: string;
  created_at?: string | null;
}

export interface ImageQA {
  image_id: number;
  artifacts: QAArtifact[];
}

export interface CatalogValidationResults {
  image_id: number;
  validated: boolean;
  matches?: number;
  errors?: string[];
  astrometry?: Record<string, unknown>;
  flux_scale?: number;
  source_counts?: number;
}

export interface CatalogOverlayData {
  image_id: number;
  sources: CatalogSource[];
}

export interface CatalogSource {
  ra_deg: number;
  dec_deg: number;
  x?: number;
  y?: number;
  flux_jy?: number;
  name?: string;
}

export interface QAMetrics {
  group_id: string;
  metrics: Record<string, number>;
}

export interface BandpassPlotsList {
  items: BandpassPlot[];
  plots?: BandpassPlot[];
  count?: number;
}

export interface BandpassPlot {
  path: string;
  filename: string;
  type: string;
  spw: number | null;
  url: string;
  created_at?: string;
}

export interface BatchJob {
  id: string;
  type: string;
  status: string;
  created_at: string;
  job_count?: number;
  completed_count?: number;
  failed_count?: number;
}

export interface BatchJobList {
  items: BatchJob[];
  total?: number;
}

export interface BatchJobCreateRequest {
  type: string;
  job_params: Record<string, unknown>[];
}

export interface ImageList {
  items: ImageInfo[];
  total: number;
}

export interface ImageFilters {
  start_mjd?: number;
  end_mjd?: number;
  type?: string;
  pbcor?: boolean;
  limit?: number;
  offset?: number;
  ms_path?: string;
  image_type?: string;
  start_date?: string;
  end_date?: string;
  dec_min?: number;
  dec_max?: number;
  noise_max?: number;
  has_calibrator?: boolean;
}

export interface DataInstance {
  id: string;
  type: string;
  path: string;
  created_at: string;
  data_type?: string;
  qa_status?: string;
  finalization_status?: string;
  auto_publish_enabled?: boolean;
  published_at?: string;
  status?: string;
  map?: (fn: (id: string) => void) => void;
}

export interface DataInstanceDetail {
  id: string;
  type: string;
  path: string;
  created_at: string;
  metadata?: Record<string, unknown>;
  data_type?: string;
  qa_status?: string;
  validation_status?: string;
  finalization_status?: string;
  auto_publish_enabled?: boolean;
  published_at?: string;
  publish_mode?: string;
  status?: string;
  stage_path?: string;
  published_path?: string;
  processing_params?: Record<string, unknown>;
}

export interface AutoPublishStatus {
  enabled: boolean;
  last_publish?: string;
  next_publish?: string;
  criteria_met?: boolean;
  reasons?: string[];
}

export interface DataLineage {
  instance_id: string;
  parents: Record<string, string[]>;
  children: Record<string, string[]>;
  processing_history?: Array<Record<string, unknown>>;
}

export interface PointingHistoryList {
  items: PointingHistoryEntry[];
}

export interface PointingHistoryEntry {
  timestamp: number;
  ra_deg: number;
  dec_deg: number;
}

export interface DirectoryEntry {
  name: string;
  type: "file" | "directory";
  is_dir: boolean;
  size?: number;
  modified_at?: string;
  path?: string;
}

export interface DirectoryListing {
  path: string;
  items: DirectoryItem[];
  entries?: DirectoryEntry[];
  total_files?: number;
  total_dirs?: number;
  fits_count?: number;
  casatable_count?: number;
}

export interface DirectoryItem {
  name: string;
  type: "file" | "directory";
  size?: number;
  modified_at?: string;
}

export interface FITSInfo {
  path: string;
  exists?: boolean;
  header?: Record<string, unknown>;
  data_shape?: number[];
  shape?: number[];
  wcs?: Record<string, unknown>;
  summary?: Record<string, unknown>;
  naxis?: number[];
  header_keys?: string[];
}

export interface CasaTableInfo {
  path: string;
  type?: string;
  exists?: boolean;
  rows?: number;
  nrows?: number;
  columns?: string[];
  keywords?: Record<string, any>;
  subtables?: string[];
  is_writable?: boolean;
  error?: string;
}

export interface NotebookGenerateRequest {
  template: string;
  params: Record<string, unknown>;
}

export interface NotebookGenerateResponse {
  notebook_path: string;
  download_url?: string;
}

export interface QARunRequest {
  group_id: string;
  image_id?: number;
  options?: Record<string, unknown>;
}

export interface QAResultSummary {
  group_id: string;
  passed: boolean;
  success?: boolean;
  reasons?: string[];
  metrics?: Record<string, number>;
  artifacts?: QAArtifact[];
}

// Job parameter types
export interface JobParams {
  field?: string | null;
  refant?: string | null;
  gaintables?: string[] | null;
  gridder?: string;
  wprojplanes?: number;
}

export interface ConversionJobParams {
  input_files?: string[];
  output_dir?: string;
  writer_type?: string;
  subbands?: number;
  params?: Record<string, unknown>;
}
