/**
 * Log query and response types for the log aggregation UI.
 */

export type LogLevel =
  | "trace"
  | "debug"
  | "info"
  | "warn"
  | "warning"
  | "error"
  | "critical"
  | "fatal";

export interface LogEntry {
  /** Unique identifier or cursor for the log line */
  id?: string;
  /** ISO timestamp of the log line */
  timestamp: string;
  level: LogLevel;
  message: string;
  /** Key/value labels such as service, job, run_id */
  labels?: Record<string, string>;
  /** Optional cursor returned by the log store for pagination/tailing */
  cursor?: string;
  /** Optional line number or offset within the stream */
  line?: number;
  /** Structured context (if provided by backend) */
  context?: Record<string, unknown>;
}

export interface LogTimeRange {
  /** Start time (ISO string, epoch ms, or Date) */
  start: string | number | Date;
  /** End time (ISO string, epoch ms, or Date) */
  end?: string | number | Date;
}

export interface LogQueryParams {
  /** Full-text search expression */
  q?: string;
  /** Level filter (single level or comma-joined array) */
  level?: LogLevel | LogLevel[];
  /** Label filters, e.g. { service: "scheduler", run_id: "abc" } */
  labels?: Record<string, string | number | Array<string | number>>;
  /** Time range constraint */
  range?: LogTimeRange;
  /** Cursor for pagination */
  cursor?: string;
}

export interface LogQueryRequest extends LogQueryParams {
  /** Max number of entries to return */
  limit?: number;
  /** Fetch direction relative to cursor */
  direction?: "forward" | "backward";
}

export interface LogSearchResponse {
  entries: LogEntry[];
  /** Cursor for fetching the next page */
  next_cursor?: string | null;
  /** Cursor for fetching the previous page */
  prev_cursor?: string | null;
  /** Whether more results are available in the requested direction */
  has_more?: boolean;
  /** Log store stats for the query (optional) */
  stats?: {
    fetched: number;
    dropped?: number;
    filtered?: number;
    duration_ms?: number;
  };
}
