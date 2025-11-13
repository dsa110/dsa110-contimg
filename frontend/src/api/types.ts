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
