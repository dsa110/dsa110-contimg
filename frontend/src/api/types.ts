// ... existing code ...

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
  status: 'pending' | 'retrying' | 'resolved' | 'failed';
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
  state: 'closed' | 'open' | 'half_open';
  failure_count: number;
  last_failure_time?: number;
  recovery_timeout: number;
}

export interface CircuitBreakerList {
  circuit_breakers: CircuitBreakerState[];
}

// Health Check Types
export interface HealthCheck {
  healthy: boolean;
  error?: string;
  type?: string;
  [key: string]: any;
}

export interface HealthSummary {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  checks: Record<string, HealthCheck>;
  circuit_breakers: Array<{
    name: string;
    state: string;
    failure_count: number;
  }>;
  dlq_stats: DLQStats;
}

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
  status: 'pending' | 'retrying' | 'resolved' | 'failed';
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
  state: 'closed' | 'open' | 'half_open';
  failure_count: number;
  last_failure_time?: number;
  recovery_timeout: number;
}

export interface CircuitBreakerList {
  circuit_breakers: CircuitBreakerState[];
}

// Health Check Types (enhanced)
export interface HealthCheck {
  healthy: boolean;
  error?: string;
  type?: string;
  [key: string]: any;
}

export interface HealthSummary {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  checks: Record<string, HealthCheck>;
  circuit_breakers: Array<{
    name: string;
    state: string;
    failure_count: number;
  }>;
  dlq_stats: DLQStats;
}

// Pipeline Types
export type StageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

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
