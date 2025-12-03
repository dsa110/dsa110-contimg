import { useEffect, useMemo, useState } from "react";
import { z } from "zod";
import type { AlertPolicy, AlertPolicyInput, AlertComparisonOperator } from "@/types/alerts";
import type { NotificationChannel } from "@/types/notifications";
import type { AlertSeverity } from "@/types/health";
import { useAlertPolicyDryRun } from "@/api/alertPolicies";

type RuleForm = {
  metric: string;
  operator: AlertComparisonOperator;
  threshold: string;
  for_seconds?: string;
  labelsText?: string;
};

interface AlertPolicyEditorProps {
  policy?: AlertPolicy;
  onSave: (input: AlertPolicyInput) => Promise<void> | void;
  onCancel: () => void;
  isSaving?: boolean;
}

const OPERATORS = [">", ">=", "<", "<=", "==", "!="] as const;
const SEVERITIES = ["info", "warning", "critical"] as const;
const CHANNELS = ["email", "slack", "webhook"] as const;

const ruleSchema = z
  .object({
    metric: z.string().trim().min(1, "Metric is required"),
    operator: z.enum(OPERATORS),
    threshold: z
      .string()
      .trim()
      .min(1, "Threshold is required")
      .refine((val) => !Number.isNaN(Number(val)), "Threshold must be a number")
      .transform((val) => Number(val)),
    for_seconds: z
      .string()
      .optional()
      .transform((val) => (val && val.trim() !== "" ? Number(val) : undefined))
      .refine(
        (val) => val === undefined || (!Number.isNaN(val) && val >= 0),
        "Duration must be a non-negative number"
      ),
    labelsText: z.string().optional(),
  })
  .transform((rule) => {
    const labels = parseLabels(rule.labelsText ?? "");
    return {
      metric: rule.metric,
      operator: rule.operator,
      threshold: rule.threshold,
      for_seconds: rule.for_seconds,
      labels,
    };
  });

const policySchema = z.object({
  name: z.string().trim().min(1, "Name is required"),
  description: z.string().optional(),
  severity: z.enum(SEVERITIES),
  channels: z.array(z.enum(CHANNELS)).min(1, "Select at least one channel"),
  enabled: z.boolean(),
  repeat_interval_seconds: z
    .union([z.string(), z.number(), z.undefined()])
    .optional()
    .transform((val) => {
      if (typeof val === "number") return val;
      if (typeof val === "string" && val.trim() !== "") {
        const parsed = Number(val);
        return Number.isNaN(parsed) ? undefined : parsed;
      }
      return undefined;
    }),
  rules: z.array(ruleSchema).min(1, "At least one rule is required"),
  overrides: z.array(ruleSchema).optional(),
});

function parseLabels(text: string): Record<string, string> | undefined {
  const trimmed = text.trim();
  if (!trimmed) return undefined;
  const parts = trimmed.split(",").map((p) => p.trim());
  const labels: Record<string, string> = {};
  for (const part of parts) {
    if (!part) continue;
    const [key, value] = part.split("=").map((p) => p?.trim() ?? "");
    if (!key || value === undefined || value === "") {
      throw new Error("Labels must be key=value pairs separated by commas");
    }
    labels[key] = value;
  }
  return Object.keys(labels).length ? labels : undefined;
}

function buildRuleForm(rule?: Partial<RuleForm>) {
  return {
    metric: rule?.metric ?? "",
    operator: rule?.operator ?? ">",
    threshold: rule?.threshold ?? "",
    for_seconds: rule?.for_seconds,
    labelsText: rule?.labelsText ?? "",
  };
}

function toFormState(policy?: AlertPolicy): {
  name: string;
  description?: string;
  severity: AlertSeverity;
  channels: NotificationChannel[];
  enabled: boolean;
  repeat_interval_seconds?: number;
  rules: RuleForm[];
  overrides: RuleForm[];
} {
  if (!policy) {
    return {
      name: "",
      description: "",
      severity: "warning",
      channels: ["email"],
      enabled: true,
      repeat_interval_seconds: undefined,
      rules: [buildRuleForm({ operator: ">", threshold: "1" })],
      overrides: [],
    };
  }

  const ruleToForm = (rule: { metric: string; operator: AlertComparisonOperator; threshold: number; for_seconds?: number; labels?: Record<string, string> }) =>
    buildRuleForm({
      metric: rule.metric,
      operator: rule.operator,
      threshold: rule.threshold?.toString(),
      for_seconds: rule.for_seconds?.toString(),
      labelsText: rule.labels
        ? Object.entries(rule.labels)
            .map(([k, v]) => `${k}=${v}`)
            .join(", ")
        : "",
    });

  return {
    name: policy.name,
    description: policy.description,
    severity: policy.severity,
    channels: policy.channels,
    enabled: policy.enabled,
    repeat_interval_seconds: policy.repeat_interval_seconds,
    rules: policy.rules.map(ruleToForm),
    overrides: (policy.overrides ?? []).map(ruleToForm),
  };
}

export function AlertPolicyEditor({ policy, onSave, onCancel, isSaving }: AlertPolicyEditorProps) {
  const [formState, setFormState] = useState(() => toFormState(policy));
  const [error, setError] = useState<string | null>(null);
  const dryRunMutation = useAlertPolicyDryRun();
  const dryRunResult = dryRunMutation.data;

  useEffect(() => {
    setFormState(toFormState(policy));
  }, [policy]);

  const handleRuleChange = (index: number, field: keyof RuleForm, value: string) => {
    setFormState((prev) => {
      const rules = [...prev.rules];
      rules[index] = { ...rules[index], [field]: value };
      return { ...prev, rules };
    });
  };

  const handleOverrideChange = (index: number, field: keyof RuleForm, value: string) => {
    setFormState((prev) => {
      const overrides = [...prev.overrides];
      overrides[index] = { ...overrides[index], [field]: value };
      return { ...prev, overrides };
    });
  };

  const addRule = () => {
    setFormState((prev) => ({
      ...prev,
      rules: [...prev.rules, buildRuleForm({ operator: ">", threshold: "1" })],
    }));
  };

  const addOverride = () => {
    setFormState((prev) => ({
      ...prev,
      overrides: [...prev.overrides, buildRuleForm({ operator: ">", threshold: "1" })],
    }));
  };

  const removeRule = (index: number) => {
    setFormState((prev) => ({
      ...prev,
      rules: prev.rules.filter((_, i) => i !== index),
    }));
  };

  const removeOverride = (index: number) => {
    setFormState((prev) => ({
      ...prev,
      overrides: prev.overrides.filter((_, i) => i !== index),
    }));
  };

  const handleSave = async () => {
    setError(null);
    try {
      const parsed = policySchema.parse({
        ...formState,
        repeat_interval_seconds:
          typeof formState.repeat_interval_seconds === "number"
            ? formState.repeat_interval_seconds
            : formState.repeat_interval_seconds ?? undefined,
      }) as AlertPolicyInput;
      await onSave(parsed);
    } catch (err) {
      if (err instanceof z.ZodError) {
        setError(err.errors[0]?.message ?? "Invalid policy");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unknown validation error");
      }
    }
  };

  const handleDryRun = async () => {
    setError(null);
    try {
      const parsed = policySchema.parse(formState) as AlertPolicyInput;
      await dryRunMutation.mutateAsync({ policy: parsed });
    } catch (err) {
      if (err instanceof z.ZodError) {
        setError(err.errors[0]?.message ?? "Invalid policy");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unknown validation error");
      }
    }
  };

  const dryRunContent = useMemo(() => {
    if (!dryRunResult) return null;
    if (!dryRunResult.results.length) {
      return <div className="text-sm text-gray-500">No alerts would fire for this policy.</div>;
    }
    return (
      <div className="space-y-2">
        {dryRunResult.results.map((result) => (
          <div
            key={result.policy_id}
            className="rounded border border-gray-200 dark:border-gray-700 p-3 bg-gray-50 dark:bg-gray-800/50"
          >
            <div className="flex items-center justify-between">
              <div className="font-medium text-gray-900 dark:text-gray-100">
                {result.policy_name}
              </div>
              <span
                className={`px-2 py-0.5 rounded text-xs font-semibold ${
                  result.would_fire
                    ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200"
                    : "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-200"
                }`}
              >
                {result.would_fire ? "Would fire" : "Would not fire"}
              </span>
            </div>
            {result.sample_alerts?.length ? (
              <ul className="mt-2 space-y-1 text-sm text-gray-700 dark:text-gray-300">
                {result.sample_alerts.map((alert, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="mt-0.5 inline-block h-2 w-2 rounded-full bg-red-400" />
                    <div>
                      <div className="font-medium">{alert.message}</div>
                      {alert.labels && (
                        <div className="text-xs text-gray-500">
                          {Object.entries(alert.labels)
                            .map(([k, v]) => `${k}=${v}`)
                            .join(", ")}
                        </div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-xs text-gray-500">No sample alerts provided.</div>
            )}
          </div>
        ))}
      </div>
    );
  }, [dryRunResult]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {policy ? "Edit Alert Policy" : "Create Alert Policy"}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Define thresholds, channels, and silences for monitoring alerts.
            </p>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Close"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {error && (
            <div className="rounded-md bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 px-3 py-2 text-sm text-red-700 dark:text-red-200">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Name
              </label>
              <input
                type="text"
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                value={formState.name}
                onChange={(e) => setFormState((prev) => ({ ...prev, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Severity
              </label>
              <select
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                value={formState.severity}
                onChange={(e) =>
                  setFormState((prev) => ({ ...prev, severity: e.target.value as AlertSeverity }))
                }
              >
                {SEVERITIES.map((severity) => (
                  <option key={severity} value={severity}>
                    {severity}
                  </option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Description
              </label>
              <textarea
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                value={formState.description ?? ""}
                onChange={(e) => setFormState((prev) => ({ ...prev, description: e.target.value }))}
                rows={2}
                placeholder="Describe the purpose of this policy"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Notification channels
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 dark:border-gray-700 text-primary-600 focus:ring-primary-500"
                  checked={formState.enabled}
                  onChange={(e) => setFormState((prev) => ({ ...prev, enabled: e.target.checked }))}
                />
                Enabled
              </label>
            </div>
            <div className="flex gap-3">
              {CHANNELS.map((channel) => {
                const checked = formState.channels.includes(channel);
                return (
                  <label
                    key={channel}
                    className="flex items-center gap-2 rounded-md border border-gray-200 dark:border-gray-700 px-3 py-2 cursor-pointer hover:border-primary-500"
                  >
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 dark:border-gray-700 text-primary-600 focus:ring-primary-500"
                      checked={checked}
                      onChange={(e) =>
                        setFormState((prev) => ({
                          ...prev,
                          channels: e.target.checked
                            ? [...prev.channels, channel]
                            : prev.channels.filter((c) => c !== channel),
                        }))
                      }
                    />
                    <span className="capitalize">{channel}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Repeat interval (seconds)
              </label>
              <input
                type="number"
                min={0}
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                value={formState.repeat_interval_seconds ?? ""}
                onChange={(e) =>
                  setFormState((prev) => ({
                    ...prev,
                    repeat_interval_seconds:
                      e.target.value === "" ? undefined : Number(e.target.value),
                  }))
                }
                placeholder="Optional delay between repeats"
              />
            </div>
          </div>

          <RuleList
            title="Rules"
            rules={formState.rules}
            onAdd={addRule}
            onChange={handleRuleChange}
            onRemove={removeRule}
          />

          <RuleList
            title="Overrides (optional)"
            rules={formState.overrides}
            onAdd={addOverride}
            onChange={handleOverrideChange}
            onRemove={removeOverride}
            emptyHint="Use overrides to fine-tune thresholds for specific labels or metrics"
          />

          {dryRunMutation.isPending && (
            <div className="text-sm text-gray-500">Running dry-run...</div>
          )}
          {dryRunContent && (
            <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                  Dry-run preview
                </h3>
                <span className="text-xs text-gray-500">
                  Evaluated at {new Date(dryRunResult?.evaluated_at ?? "").toLocaleString()}
                </span>
              </div>
              {dryRunContent}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-800">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleDryRun}
              className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50"
            >
              Dry-run
            </button>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSaving ? "Saving..." : policy ? "Save changes" : "Create policy"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function RuleList({
  title,
  rules,
  onAdd,
  onChange,
  onRemove,
  emptyHint,
}: {
  title: string;
  rules: RuleForm[];
  onAdd: () => void;
  onChange: (index: number, field: keyof RuleForm, value: string) => void;
  onRemove: (index: number) => void;
  emptyHint?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">{title}</h3>
          {emptyHint && rules.length === 0 && (
            <p className="text-xs text-gray-500 mt-1">{emptyHint}</p>
          )}
        </div>
        <button
          type="button"
          onClick={onAdd}
          className="inline-flex items-center px-2.5 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md text-xs font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50"
        >
          Add rule
        </button>
      </div>

      <div className="space-y-3">
        {rules.map((rule, index) => (
          <div
            key={index}
            className="p-3 rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60"
          >
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
                  Metric
                </label>
                <input
                  type="text"
                  className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  value={rule.metric}
                  onChange={(e) => onChange(index, "metric", e.target.value)}
                  placeholder="e.g. pipeline_latency_seconds"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
                  Operator
                </label>
                <select
                  className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  value={rule.operator}
                  onChange={(e) => onChange(index, "operator", e.target.value)}
                >
                  {OPERATORS.map((op) => (
                    <option key={op} value={op}>
                      {op}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
                  Threshold
                </label>
                <input
                  type="number"
                  className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  value={rule.threshold}
                  onChange={(e) => onChange(index, "threshold", e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
                  For (seconds)
                </label>
                <input
                  type="number"
                  className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                  value={rule.for_seconds ?? ""}
                  onChange={(e) => onChange(index, "for_seconds", e.target.value)}
                  placeholder="Optional"
                  min={0}
                />
              </div>
            </div>
            <div className="mt-3">
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-300">
                Labels (key=value, comma-separated)
              </label>
              <input
                type="text"
                className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                value={rule.labelsText ?? ""}
                onChange={(e) => onChange(index, "labelsText", e.target.value)}
                placeholder="env=prod, service=imager"
              />
            </div>
            <div className="mt-3 flex justify-end">
              <button
                type="button"
                onClick={() => onRemove(index)}
                className="text-xs text-red-600 hover:text-red-700 dark:text-red-400"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
