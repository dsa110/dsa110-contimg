/**
 * Alert policy and silence types
 *
 * Models configurable alert policies, dry-run previews, and silences.
 */
import type { AlertSeverity } from "./health";
import type { NotificationChannel } from "./notifications";

export type AlertComparisonOperator = ">" | ">=" | "<" | "<=" | "==" | "!=";

export interface AlertPolicyRule {
  /** Metric or signal name this rule evaluates */
  metric: string;
  /** Optional label selector map for scoping the metric */
  labels?: Record<string, string>;
  /** Comparison operator for threshold evaluation */
  operator: AlertComparisonOperator;
  /** Numeric threshold */
  threshold: number;
  /** Minimum duration the condition must hold (seconds) */
  for_seconds?: number;
}

export interface AlertPolicy {
  id: string;
  name: string;
  description?: string;
  severity: AlertSeverity;
  channels: NotificationChannel[];
  enabled: boolean;
  rules: AlertPolicyRule[];
  /** Optional per-metric overrides for targeted tuning */
  overrides?: AlertPolicyRule[];
  /** Minimum time between repeated notifications (seconds) */
  repeat_interval_seconds?: number;
  created_at?: string;
  updated_at?: string;
}

export interface AlertPolicyInput
  extends Omit<AlertPolicy, "id" | "created_at" | "updated_at"> {}

export interface AlertPolicyListResponse {
  policies: AlertPolicy[];
  total?: number;
}

export interface AlertSilence {
  id: string;
  policy_id: string;
  reason: string;
  created_by?: string;
  starts_at: string;
  ends_at: string;
  created_at?: string;
}

export interface CreateSilenceInput
  extends Omit<AlertSilence, "id" | "created_at" | "policy_id"> {}

export interface DryRunAlert {
  policy_id: string;
  policy_name: string;
  would_fire: boolean;
  sample_alerts: {
    message: string;
    severity: AlertSeverity;
    labels?: Record<string, string>;
  }[];
}

export interface AlertPolicyDryRunRequest {
  policy: AlertPolicyInput;
}

export interface AlertPolicyDryRunResponse {
  results: DryRunAlert[];
  evaluated_at: string;
}
