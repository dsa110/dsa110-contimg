/**
 * Prometheus Metrics Types
 *
 * TypeScript interfaces for Prometheus metrics data.
 */

// =============================================================================
// Time Series Types
// =============================================================================

export interface MetricDataPoint {
  /** Unix timestamp in seconds */
  timestamp: number;
  /** Metric value */
  value: number;
}

export interface MetricSeries {
  /** Metric name */
  metric: string;
  /** Metric labels */
  labels: Record<string, string>;
  /** Data points */
  values: MetricDataPoint[];
}

export interface PrometheusQueryResult {
  /** Query that was executed */
  query: string;
  /** Result type (vector, matrix, scalar) */
  resultType: "vector" | "matrix" | "scalar" | "string";
  /** Result data */
  data: MetricSeries[];
}

// =============================================================================
// Dashboard Metric Types
// =============================================================================

export interface SystemMetric {
  /** Metric identifier */
  id: string;
  /** Display name */
  name: string;
  /** Description */
  description: string;
  /** Unit (%, bytes, etc.) */
  unit: string;
  /** Current value */
  current: number;
  /** Trend direction */
  trend: "up" | "down" | "stable";
  /** Trend percentage change */
  trendPercent: number;
  /** Status based on thresholds */
  status: "healthy" | "warning" | "critical";
  /** Time series data */
  history: MetricDataPoint[];
}

export interface MetricThreshold {
  /** Warning threshold */
  warning: number;
  /** Critical threshold */
  critical: number;
  /** Whether higher is worse (e.g., CPU usage) */
  higherIsWorse: boolean;
}

// =============================================================================
// Pipeline Metrics Types
// =============================================================================

export interface PipelineMetrics {
  /** Jobs processed in last hour */
  jobs_per_hour: number;
  /** Average job duration (seconds) */
  avg_job_duration_sec: number;
  /** Job success rate (0-100) */
  success_rate_percent: number;
  /** Current queue depth */
  queue_depth: number;
  /** Active workers */
  active_workers: number;
  /** Total workers */
  total_workers: number;
}

export interface ResourceMetrics {
  /** CPU usage (0-100) */
  cpu_percent: number;
  /** Memory usage (0-100) */
  memory_percent: number;
  /** Disk I/O (MB/s) */
  disk_io_mbps: number;
  /** Network I/O (MB/s) */
  network_io_mbps: number;
}

/** Extended resource metrics with history for detailed visualization */
export interface ResourceMetricsDetailed {
  cpu: SystemMetric;
  memory: SystemMetric & { total: number };
  diskIO: SystemMetric;
  network: SystemMetric;
}

export interface MetricsDashboard {
  /** System resource metrics */
  resources: ResourceMetrics;
  /** Pipeline processing metrics */
  pipeline: PipelineMetrics;
  /** Individual metrics with history */
  metrics: SystemMetric[];
  /** Last update timestamp */
  updated_at: string;
}
