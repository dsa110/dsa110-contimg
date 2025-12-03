import { useMemo, useState } from "react";
import {
  useAlertPolicies,
  useCreateAlertPolicy,
  useUpdateAlertPolicy,
  useDeleteAlertPolicy,
  useToggleAlertPolicy,
  useAlertSilences,
  useCreateAlertSilence,
} from "@/api/alertPolicies";
import type { AlertPolicy, AlertPolicyInput, AlertSilence } from "@/types/alerts";
import { AlertPolicyEditor } from "./AlertPolicyEditor";

type BadgeTone = "gray" | "green" | "yellow" | "red" | "blue";

function Badge({ label, tone = "gray" }: { label: string; tone?: BadgeTone }) {
  const toneClasses: Record<BadgeTone, string> = {
    gray: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200",
    green: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200",
    yellow: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200",
    red: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
    blue: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-semibold rounded ${toneClasses[tone]}`}>
      {label}
    </span>
  );
}

export function AlertPolicyList() {
  const { data, isLoading, error } = useAlertPolicies();
  const { data: silences } = useAlertSilences();
  const createMutation = useCreateAlertPolicy();
  const updateMutation = useUpdateAlertPolicy();
  const deleteMutation = useDeleteAlertPolicy();
  const toggleMutation = useToggleAlertPolicy();
  const createSilenceMutation = useCreateAlertSilence();

  const [showEditor, setShowEditor] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<AlertPolicy | undefined>();
  const [silenceTarget, setSilenceTarget] = useState<AlertPolicy | undefined>();

  const policies = data?.policies ?? [];
  const activeSilencesByPolicy = useMemo(() => {
    if (!silences) return {} as Record<string, AlertSilence[]>;
    const grouped: Record<string, AlertSilence[]> = {};
    for (const silence of silences) {
      if (!grouped[silence.policy_id]) grouped[silence.policy_id] = [];
      grouped[silence.policy_id].push(silence);
    }
    return grouped;
  }, [silences]);

  const handleSave = async (input: AlertPolicyInput) => {
    if (editingPolicy) {
      await updateMutation.mutateAsync({ id: editingPolicy.id, input });
    } else {
      await createMutation.mutateAsync(input);
    }
    setShowEditor(false);
    setEditingPolicy(undefined);
  };

  const handleDelete = async (policy: AlertPolicy) => {
    const confirmed = window.confirm(`Delete alert policy "${policy.name}"?`);
    if (!confirmed) return;
    await deleteMutation.mutateAsync(policy.id);
  };

  const handleToggle = async (policy: AlertPolicy, enabled: boolean) => {
    await toggleMutation.mutateAsync({ id: policy.id, enabled });
  };

  const openCreate = () => {
    setEditingPolicy(undefined);
    setShowEditor(true);
  };

  const openEdit = (policy: AlertPolicy) => {
    setEditingPolicy(policy);
    setShowEditor(true);
  };

  const openSilence = (policy: AlertPolicy) => {
    setSilenceTarget(policy);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Alert policies</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Configure thresholds, delivery channels, and silences.
          </p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
        >
          New policy
        </button>
      </div>

      {isLoading && <div className="text-sm text-gray-500">Loading policies...</div>}
      {error && (
        <div className="text-sm text-red-600">
          Failed to load alert policies
        </div>
      )}

      {!isLoading && !error && (
        <>
          {policies.length === 0 ? (
            <div className="text-sm text-gray-500">
              No alert policies found. Create one to start monitoring custom thresholds.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Severity
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Channels
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Rules
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Silences
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {policies.map((policy) => {
                    const policySilences = activeSilencesByPolicy[policy.id] ?? [];
                    return (
                      <tr key={policy.id}>
                        <td className="px-4 py-3">
                          <div className="font-medium text-gray-900 dark:text-gray-100">{policy.name}</div>
                          <div className="text-xs text-gray-500 dark:text-gray-400">{policy.description}</div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            label={policy.severity}
                            tone={
                              policy.severity === "critical"
                                ? "red"
                                : policy.severity === "warning"
                                ? "yellow"
                                : "blue"
                            }
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {policy.channels.map((channel) => (
                              <Badge key={channel} label={channel} tone="gray" />
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="text-sm text-gray-900 dark:text-gray-100">
                            {policy.rules.length} rule{policy.rules.length === 1 ? "" : "s"}
                          </div>
                          {policy.overrides?.length ? (
                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              {policy.overrides.length} override{policy.overrides.length === 1 ? "" : "s"}
                            </div>
                          ) : null}
                        </td>
                        <td className="px-4 py-3">
                          {policySilences.length === 0 ? (
                            <span className="text-xs text-gray-500">None</span>
                          ) : (
                            <div className="flex flex-col gap-1">
                              {policySilences.map((silence) => (
                                <span key={silence.id} className="text-xs text-gray-700 dark:text-gray-300">
                                  {new Date(silence.starts_at).toLocaleString()} →
                                  {` ${new Date(silence.ends_at).toLocaleString()}`}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <label className="inline-flex items-center cursor-pointer">
                            <input
                              type="checkbox"
                              className="sr-only peer"
                              checked={policy.enabled}
                              onChange={(e) => handleToggle(policy, e.target.checked)}
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500 rounded-full peer dark:bg-gray-700 peer-checked:bg-primary-600 relative transition-colors">
                              <span
                                className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5"
                                aria-hidden="true"
                              />
                            </div>
                          </label>
                        </td>
                        <td className="px-4 py-3 text-right space-x-2">
                          <button
                            type="button"
                            onClick={() => openEdit(policy)}
                            className="text-sm text-primary-600 hover:text-primary-700"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => openSilence(policy)}
                            className="text-sm text-gray-600 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100"
                          >
                            Silence
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(policy)}
                            className="text-sm text-red-600 hover:text-red-700"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {showEditor && (
        <AlertPolicyEditor
          policy={editingPolicy}
          onSave={handleSave}
          onCancel={() => {
            setShowEditor(false);
            setEditingPolicy(undefined);
          }}
          isSaving={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {silenceTarget && (
        <SilenceModal
          policy={silenceTarget}
          onClose={() => setSilenceTarget(undefined)}
          onCreate={async (payload) => {
            await createSilenceMutation.mutateAsync({ policyId: silenceTarget.id, input: payload });
            setSilenceTarget(undefined);
          }}
          isSaving={createSilenceMutation.isPending}
        />
      )}
    </div>
  );
}

function SilenceModal({
  policy,
  onClose,
  onCreate,
  isSaving,
}: {
  policy: AlertPolicy;
  onClose: () => void;
  onCreate: (input: { reason: string; starts_at: string; ends_at: string }) => Promise<void>;
  isSaving: boolean;
}) {
  const now = new Date();
  const defaultEnd = new Date(now.getTime() + 60 * 60 * 1000);
  const [reason, setReason] = useState("Maintenance window");
  const [start, setStart] = useState(toDateTimeLocal(now));
  const [end, setEnd] = useState(toDateTimeLocal(defaultEnd));
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    const startDate = new Date(start);
    const endDate = new Date(end);
    if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
      setError("Start and end times are required");
      return;
    }
    if (endDate <= startDate) {
      setError("End time must be after start time");
      return;
    }
    await onCreate({
      reason: reason.trim() || "Silenced from UI",
      starts_at: startDate.toISOString(),
      ends_at: endDate.toISOString(),
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Create silence</h3>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Close"
          >
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="px-4 py-3 space-y-3">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Policy: <span className="font-medium">{policy.name}</span>
          </p>

          {error && (
            <div className="rounded-md bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 px-3 py-2 text-sm text-red-700 dark:text-red-200">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
              Reason
            </label>
            <input
              type="text"
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
              Starts at
            </label>
            <input
              type="datetime-local"
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
              Ends at
            </label>
            <input
              type="datetime-local"
              className="mt-1 w-full rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </div>
        </div>
        <div className="flex items-center justify-end px-4 py-3 border-t border-gray-200 dark:border-gray-800">
          <button
            type="button"
            onClick={onClose}
            className="mr-2 inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSaving}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSaving ? "Saving..." : "Create silence"}
          </button>
        </div>
      </div>
    </div>
  );
}

function toDateTimeLocal(date: Date) {
  const pad = (n: number) => `${n}`.padStart(2, "0");
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}
