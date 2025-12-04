/**
 * Backup & Restore Page
 *
 * Provides UI for:
 * - Creating new backups (full, incremental, differential)
 * - Viewing backup history
 * - Validating backup integrity
 * - Restoring from backups with preview
 */

import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  useBackups,
  useCreateBackup,
  useDeleteBackup,
  useRestorePreview,
  useRestore,
  useRestoreHistory,
  type Backup,
  type BackupType,
  type BackupScope,
  type RestoreJob,
  formatBackupType,
  getDefaultBackupScope,
  getScopeSummary,
} from "../api/backup";
import { ROUTES } from "../constants/routes";

// ============================================================================
// Sub-components
// ============================================================================

interface BackupScopeSelectorProps {
  scope: BackupScope;
  onChange: (scope: BackupScope) => void;
  disabled?: boolean;
}

function BackupScopeSelector({
  scope,
  onChange,
  disabled,
}: BackupScopeSelectorProps) {
  const scopeItems: Array<{ key: keyof BackupScope; label: string; desc: string }> = [
    { key: "measurement_sets", label: "Measurement Sets", desc: "Raw visibility data" },
    { key: "images", label: "Images", desc: "FITS image products" },
    { key: "catalogs", label: "Catalogs", desc: "Source catalogs" },
    { key: "pipeline_configs", label: "Pipeline Configs", desc: "Processing configurations" },
    { key: "job_history", label: "Job History", desc: "Pipeline run records" },
    { key: "qa_ratings", label: "QA Ratings", desc: "Quality assessments" },
  ];

  const toggleScope = (key: keyof BackupScope) => {
    onChange({ ...scope, [key]: !scope[key] });
  };

  const selectAll = () => {
    onChange(getDefaultBackupScope());
  };

  const selectNone = () => {
    onChange({
      measurement_sets: false,
      images: false,
      catalogs: false,
      pipeline_configs: false,
      job_history: false,
      qa_ratings: false,
    });
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          Data to Include
        </label>
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            onClick={selectAll}
            disabled={disabled}
            className="text-blue-600 hover:text-blue-700 disabled:opacity-50"
          >
            Select All
          </button>
          <span className="text-gray-400">|</span>
          <button
            type="button"
            onClick={selectNone}
            disabled={disabled}
            className="text-blue-600 hover:text-blue-700 disabled:opacity-50"
          >
            Select None
          </button>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {scopeItems.map((item) => (
          <label
            key={item.key}
            className={`flex items-start gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${
              scope[item.key]
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
            } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            <input
              type="checkbox"
              checked={scope[item.key]}
              onChange={() => toggleScope(item.key)}
              disabled={disabled}
              className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <div>
              <div className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                {item.label}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {item.desc}
              </div>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}

interface CreateBackupModalProps {
  isOpen: boolean;
  onClose: () => void;
  parentBackup?: Backup;
}

function CreateBackupModal({ isOpen, onClose, parentBackup }: CreateBackupModalProps) {
  const [name, setName] = useState("");
  const [type, setType] = useState<BackupType>(parentBackup ? "incremental" : "full");
  const [scope, setScope] = useState<BackupScope>(getDefaultBackupScope());
  const [notes, setNotes] = useState("");

  const createBackup = useCreateBackup();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createBackup.mutateAsync({
        name: name || `Backup ${new Date().toISOString().slice(0, 10)}`,
        type,
        scope,
        notes: notes || undefined,
        parent_backup_id: parentBackup?.id,
      });
      onClose();
      setName("");
      setNotes("");
      setScope(getDefaultBackupScope());
    } catch {
      // Error handled by mutation
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div
          className="fixed inset-0 bg-black/50 transition-opacity"
          onClick={onClose}
        />
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <form onSubmit={handleSubmit}>
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Create New Backup
              </h2>
            </div>

            <div className="p-6 space-y-6">
              {/* Backup Name */}
              <div>
                <label
                  htmlFor="backup-name"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Backup Name
                </label>
                <input
                  id="backup-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={`Backup ${new Date().toISOString().slice(0, 10)}`}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              {/* Backup Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Backup Type
                </label>
                <div className="flex gap-4">
                  {(["full", "incremental", "differential"] as BackupType[]).map(
                    (t) => (
                      <label key={t} className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="backup-type"
                          value={t}
                          checked={type === t}
                          onChange={() => setType(t)}
                          disabled={
                            (t === "incremental" || t === "differential") &&
                            !parentBackup
                          }
                          className="text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-gray-700 dark:text-gray-300 capitalize">
                          {t}
                        </span>
                      </label>
                    )
                  )}
                </div>
                {type !== "full" && !parentBackup && (
                  <p className="mt-1 text-sm text-yellow-600 dark:text-yellow-400">
                    Incremental/Differential requires a parent backup
                  </p>
                )}
              </div>

              {/* Scope Selection */}
              <BackupScopeSelector
                scope={scope}
                onChange={setScope}
                disabled={createBackup.isPending}
              />

              {/* Notes */}
              <div>
                <label
                  htmlFor="backup-notes"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Notes (optional)
                </label>
                <textarea
                  id="backup-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Reason for backup..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              {createBackup.isError && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
                  Failed to create backup:{" "}
                  {(createBackup.error as Error)?.message || "Unknown error"}
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createBackup.isPending || !Object.values(scope).some(Boolean)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {createBackup.isPending ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    Creating...
                  </>
                ) : (
                  <>
                    <span>💾</span>
                    Create Backup
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

interface RestoreModalProps {
  backup: Backup | null;
  onClose: () => void;
}

function RestoreModal({ backup, onClose }: RestoreModalProps) {
  const [scope, setScope] = useState<BackupScope>(
    backup?.scope ?? getDefaultBackupScope()
  );
  const [overwrite, setOverwrite] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [notes, setNotes] = useState("");

  const previewMutation = useRestorePreview();
  const restoreMutation = useRestore();

  const handlePreview = async () => {
    if (!backup) return;
    await previewMutation.mutateAsync({
      backup_id: backup.id,
      scope,
      overwrite_existing: overwrite,
      dry_run: true,
    });
  };

  const handleRestore = async () => {
    if (!backup) return;
    try {
      await restoreMutation.mutateAsync({
        backup_id: backup.id,
        scope,
        overwrite_existing: overwrite,
        dry_run: false,
        notes: notes || undefined,
      });
      onClose();
    } catch {
      // Error handled by mutation
    }
  };

  if (!backup) return null;

  const preview = previewMutation.data;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        <div
          className="fixed inset-0 bg-black/50 transition-opacity"
          onClick={onClose}
        />
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Restore from Backup
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {backup.name} ({formatBackupType(backup.type)})
            </p>
          </div>

          <div className="p-6 space-y-6">
            {/* Scope Selection */}
            <BackupScopeSelector
              scope={scope}
              onChange={setScope}
              disabled={restoreMutation.isPending}
            />

            {/* Overwrite Option */}
            <label className="flex items-start gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg cursor-pointer">
              <input
                type="checkbox"
                checked={overwrite}
                onChange={(e) => setOverwrite(e.target.checked)}
                disabled={restoreMutation.isPending}
                className="mt-0.5 rounded border-gray-300 text-yellow-600 focus:ring-yellow-500"
              />
              <div>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  Overwrite existing data
                </span>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  If checked, existing data will be replaced. Otherwise, only missing data will be restored.
                </p>
              </div>
            </label>

            {/* Preview Button */}
            {!preview && (
              <button
                type="button"
                onClick={handlePreview}
                disabled={previewMutation.isPending || !Object.values(scope).some(Boolean)}
                className="w-full px-4 py-2 border border-blue-500 text-blue-600 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {previewMutation.isPending ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    Analyzing...
                  </>
                ) : (
                  <>
                    <span>🔍</span>
                    Preview Restore
                  </>
                )}
              </button>
            )}

            {/* Preview Results */}
            {preview && (
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                    Restore Preview
                  </h4>
                  <dl className="grid grid-cols-2 gap-2 text-sm">
                    <dt className="text-gray-500 dark:text-gray-400">Items to restore:</dt>
                    <dd className="text-gray-900 dark:text-gray-100">{preview.items_to_restore}</dd>
                    <dt className="text-gray-500 dark:text-gray-400">Conflicts:</dt>
                    <dd className="text-gray-900 dark:text-gray-100">{preview.conflicts.length}</dd>
                    <dt className="text-gray-500 dark:text-gray-400">Estimated time:</dt>
                    <dd className="text-gray-900 dark:text-gray-100">
                      {Math.ceil(preview.estimated_time_seconds / 60)} min
                    </dd>
                  </dl>
                </div>

                {preview.warnings.length > 0 && (
                  <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                    <h5 className="font-medium text-yellow-700 dark:text-yellow-300 mb-1">
                      Warnings
                    </h5>
                    <ul className="text-sm text-yellow-600 dark:text-yellow-400 list-disc list-inside">
                      {preview.warnings.map((w: string, i: number) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {!preview.can_restore && (
                  <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                    Cannot restore: Missing dependencies or validation failed
                  </div>
                )}

                {/* Confirmation */}
                {preview.can_restore && (
                  <>
                    <div>
                      <label
                        htmlFor="restore-notes"
                        className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                      >
                        Restore Notes
                      </label>
                      <textarea
                        id="restore-notes"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        rows={2}
                        placeholder="Reason for restore..."
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      />
                    </div>

                    <label className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg cursor-pointer">
                      <input
                        type="checkbox"
                        checked={confirmed}
                        onChange={(e) => setConfirmed(e.target.checked)}
                        disabled={restoreMutation.isPending}
                        className="mt-0.5 rounded border-gray-300 text-red-600 focus:ring-red-500"
                      />
                      <div>
                        <span className="font-medium text-gray-900 dark:text-gray-100">
                          I understand and confirm this restore operation
                        </span>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          This will restore {preview.items_to_restore} items from the backup.
                          {overwrite && " Existing data will be overwritten."}
                        </p>
                      </div>
                    </label>
                  </>
                )}
              </div>
            )}

            {restoreMutation.isError && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
                Restore failed: {(restoreMutation.error as Error)?.message || "Unknown error"}
              </div>
            )}
          </div>

          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            {preview?.can_restore && (
              <button
                type="button"
                onClick={handleRestore}
                disabled={!confirmed || restoreMutation.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {restoreMutation.isPending ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    Restoring...
                  </>
                ) : (
                  <>
                    <span>🔄</span>
                    Start Restore
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface BackupCardProps {
  backup: Backup;
  onRestore: (backup: Backup) => void;
  onDelete: (id: string) => void;
}

function BackupCard({ backup, onRestore, onDelete }: BackupCardProps) {
  const statusColors: Record<string, string> = {
    pending: "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30",
    running: "text-blue-600 bg-blue-100 dark:bg-blue-900/30",
    completed: "text-green-600 bg-green-100 dark:bg-green-900/30",
    failed: "text-red-600 bg-red-100 dark:bg-red-900/30",
    cancelled: "text-gray-600 bg-gray-100 dark:bg-gray-700",
  };

  const typeIcons: Record<BackupType, string> = {
    full: "📦",
    incremental: "📥",
    differential: "📊",
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <span className="text-2xl">{typeIcons[backup.type]}</span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-gray-100">
              {backup.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {formatBackupType(backup.type)} • {backup.size_formatted}
            </p>
          </div>
        </div>
        <span
          className={`px-2 py-1 text-xs font-medium rounded-full capitalize ${
            statusColors[backup.status]
          }`}
        >
          {backup.status}
        </span>
      </div>

      <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
        <p>{getScopeSummary(backup.scope)}</p>
        <p className="mt-1">
          {backup.item_count.toLocaleString()} items •{" "}
          {new Date(backup.created_at).toLocaleString()}
        </p>
        {backup.notes && (
          <p className="mt-2 italic text-gray-400 dark:text-gray-500">
            &ldquo;{backup.notes}&rdquo;
          </p>
        )}
      </div>

      <div className="mt-4 flex gap-2">
        {backup.status === "completed" && (
          <button
            onClick={() => onRestore(backup)}
            className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-1"
          >
            <span>🔄</span>
            Restore
          </button>
        )}
        <button
          onClick={() => onDelete(backup.id)}
          className="px-3 py-1.5 text-sm border border-red-300 text-red-600 rounded hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-1"
        >
          <span>🗑️</span>
          Delete
        </button>
      </div>
    </div>
  );
}

function RestoreHistoryPanel() {
  const { data: restores, isLoading, error } = useRestoreHistory(5);

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-500 dark:text-red-400">
        Failed to load restore history
      </div>
    );
  }

  if (!restores || restores.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <div className="text-4xl mb-2">📋</div>
        <div>No restore history</div>
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    pending: "text-yellow-600",
    running: "text-blue-600",
    completed: "text-green-600",
    failed: "text-red-600",
    cancelled: "text-gray-600",
  };

  return (
    <div className="space-y-2">
      {restores.map((restore: RestoreJob) => (
        <Link
          key={restore.id}
          to={ROUTES.JOBS.DETAIL(restore.id)}
          className="block p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-900 dark:text-gray-100 text-sm">
              {restore.backup_name}
            </span>
            <span className={`text-xs capitalize ${statusColors[restore.status]}`}>
              {restore.status}
            </span>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {new Date(restore.started_at).toLocaleString()} •{" "}
            {restore.items_restored}/{restore.items_total} items
          </div>
        </Link>
      ))}
    </div>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

export function BackupRestorePage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [restoreBackup, setRestoreBackup] = useState<Backup | null>(null);

  const { data: backups, isLoading, error } = useBackups({ limit: 20 });
  const deleteBackup = useDeleteBackup();

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this backup?")) {
      await deleteBackup.mutateAsync(id);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Backup & Restore
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Create backups and restore data with full audit trail
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <span>💾</span>
              Create Backup
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Backups List */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Available Backups
            </h2>

            {isLoading && (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse"
                  />
                ))}
              </div>
            )}

            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                Failed to load backups: {(error as Error)?.message}
              </div>
            )}

            {backups && backups.length === 0 && (
              <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
                <div className="text-6xl mb-4">💾</div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  No Backups Yet
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mt-1">
                  Create your first backup to protect your data
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Create Backup
                </button>
              </div>
            )}

            {backups && backups.length > 0 && (
              <div className="space-y-4">
                {backups.map((backup: Backup) => (
                  <BackupCard
                    key={backup.id}
                    backup={backup}
                    onRestore={setRestoreBackup}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Restore History */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Recent Restores
              </h3>
              <RestoreHistoryPanel />
            </div>

            {/* Quick Stats */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Backup Summary
              </h3>
              {backups && (
                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500 dark:text-gray-400">Total Backups</dt>
                    <dd className="font-medium text-gray-900 dark:text-gray-100">
                      {backups.length}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500 dark:text-gray-400">Full Backups</dt>
                    <dd className="font-medium text-gray-900 dark:text-gray-100">
                      {backups.filter((b: Backup) => b.type === "full").length}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500 dark:text-gray-400">Total Size</dt>
                    <dd className="font-medium text-gray-900 dark:text-gray-100">
                      {formatBytes(
                        backups.reduce((sum: number, b: Backup) => sum + b.size_bytes, 0)
                      )}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500 dark:text-gray-400">Last Backup</dt>
                    <dd className="font-medium text-gray-900 dark:text-gray-100">
                      {backups.length > 0
                        ? new Date(backups[0].created_at).toLocaleDateString()
                        : "Never"}
                    </dd>
                  </div>
                </dl>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Modals */}
      <CreateBackupModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
      <RestoreModal backup={restoreBackup} onClose={() => setRestoreBackup(null)} />
    </div>
  );
}

// Utility function
function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export default BackupRestorePage;
