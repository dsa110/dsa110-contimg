/**
 * Health Monitoring Types
 *
 * TypeScript interfaces for the health monitoring API endpoints.
 */

// =============================================================================
// Service Health Types
// =============================================================================

export type ServiceStatusType = "running" | "stopped" | "degraded" | "error" | "unknown";

export interface ServiceHealthStatus {
  name: string;
  status: ServiceStatusType;
  message: string;
  response_time_ms?: number;
  details: Record<string, unknown>;
  checked_at: string;
}

export interface HealthSummary {
  total: number;
  running: number;
  stopped: number;
  degraded: number;
  error: number;
}

export interface SystemHealthReport {
  overall_status: ServiceStatusType;
  services: ServiceHealthStatus[];
  docker_available: boolean;
  systemd_available: boolean;
  summary: HealthSummary;
  checked_at: string;
  check_duration_ms: number;
}

// =============================================================================
// Validity Window Types
// =============================================================================

export interface ValidityWindowInfo {
  set_name: string;
  table_type: string;
  path: string;
  valid_start_mjd?: number;
  valid_end_mjd?: number;
  cal_field?: string;
  refant?: string;
  status: string;
  created_at: number;
}

export interface ActiveSetInfo {
  set_name: string;
  tables: ValidityWindowInfo[];
  earliest_start_mjd?: number;
  latest_end_mjd?: number;
  table_count: number;
}

export interface ActiveValidityWindows {
  query_mjd: number;
  query_iso: string;
  active_sets: ActiveSetInfo[];
  total_active_tables: number;
  overlapping_sets: number;
}

export interface ValidityTimelineEntry {
  set_name: string;
  table_type: string;
  valid_start_iso: string;
  valid_end_iso: string;
  valid_start_mjd: number;
  valid_end_mjd: number;
  is_current: boolean;
  hours_until_expiry?: number;
  cal_field?: string;
}

export interface ValidityTimeline {
  query_mjd: number;
  query_iso: string;
  window_start_iso: string;
  window_end_iso: string;
  entries: ValidityTimelineEntry[];
  total_entries: number;
}

// =============================================================================
// Flux Monitoring Types
// =============================================================================

export interface FluxMonitoringStatus {
  calibrator_name: string;
  n_measurements: number;
  latest_mjd?: number;
  latest_flux_ratio?: number;
  mean_flux_ratio?: number;
  flux_ratio_std?: number;
  is_stable: boolean;
  alerts_count: number;
}

export interface FluxMonitoringSummary {
  calibrators: FluxMonitoringStatus[];
  total_measurements: number;
  total_alerts: number;
  last_check_time?: string;
}

export interface FluxHistoryPoint {
  mjd: number;
  timestamp_iso: string;
  flux_ratio: number;
  observed_flux_jy: number;
  catalog_flux_jy: number;
  phase_rms_deg?: number;
  amp_rms?: number;
}

export interface FluxHistory {
  calibrator_name: string;
  measurements: FluxHistoryPoint[];
  stats: {
    mean_flux_ratio: number;
    std_flux_ratio: number;
    min_flux_ratio: number;
    max_flux_ratio: number;
  };
}

// =============================================================================
// Pointing/Transit Types
// =============================================================================

export interface TransitPrediction {
  calibrator: string;
  ra_deg: number;
  dec_deg: number;
  transit_utc: string;
  time_to_transit_sec: number;
  lst_at_transit: number;
  elevation_at_transit: number;
  status: "in_progress" | "upcoming" | "scheduled";
}

export interface PointingStatus {
  current_lst: number;
  current_lst_deg: number;
  active_calibrator?: string;
  upcoming_transits: TransitPrediction[];
  timestamp: string;
}

// =============================================================================
// Alert Types
// =============================================================================

export type AlertSeverity = "info" | "warning" | "critical";

export interface MonitoringAlert {
  id: number;
  alert_type: string;
  severity: AlertSeverity;
  calibrator_name?: string;
  message: string;
  triggered_at: string;
  acknowledged: boolean;
  acknowledged_at?: string;
  acknowledged_by?: string;
}

export interface AlertsResponse {
  alerts: MonitoringAlert[];
  total_count: number;
  unacknowledged_count: number;
}

// =============================================================================
// Database Health Types
// =============================================================================

export interface DatabaseHealth {
  name: string;
  path: string;
  status: "healthy" | "error" | "missing";
  size_mb?: number;
  table_count?: number;
  last_modified?: string;
  error?: string;
}

export interface DatabaseHealthResponse {
  databases: DatabaseHealth[];
  overall_status: "healthy" | "degraded" | "error";
  checked_at: string;
}
