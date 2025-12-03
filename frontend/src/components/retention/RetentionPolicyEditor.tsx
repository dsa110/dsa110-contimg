/**
 * RetentionPolicyEditor Component
 *
 * Form for creating and editing retention policies with rule configuration.
 */

import React, { useState, useCallback } from "react";
import type {
  RetentionPolicy,
  RetentionPolicyFormData,
  RetentionRule,
  RetentionDataType,
  RetentionPriority,
  RetentionTriggerType,
  RetentionAction,
} from "../../types/retention";
import {
  DATA_TYPE_LABELS,
  PRIORITY_LABELS,
  ACTION_LABELS,
} from "../../types/retention";

interface RetentionPolicyEditorProps {
  /** Existing policy to edit (undefined for create mode) */
  policy?: RetentionPolicy;
  /** Callback when form is submitted */
  onSubmit: (data: RetentionPolicyFormData) => void;
  /** Callback when form is cancelled */
  onCancel: () => void;
  /** Whether form is submitting */
  isSubmitting?: boolean;
}

/**
 * Default empty rule
 */
const createEmptyRule = (): Omit<RetentionRule, "id"> => ({
  name: "",
  description: "",
  triggerType: "age",
  action: "delete",
  threshold: 30,
  thresholdUnit: "days",
  enabled: true,
});

/**
 * Threshold units by trigger type
 */
const thresholdUnitOptions: Record<
  RetentionTriggerType,
  { value: RetentionRule["thresholdUnit"]; label: string }[]
> = {
  age: [
    { value: "hours", label: "Hours" },
    { value: "days", label: "Days" },
  ],
  size: [
    { value: "GB", label: "GB" },
    { value: "TB", label: "TB" },
  ],
  count: [{ value: "count", label: "Items" }],
  manual: [],
};

export function RetentionPolicyEditor({
  policy,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: RetentionPolicyEditorProps) {
  const isEditMode = !!policy;

  // Form state
  const [name, setName] = useState(policy?.name ?? "");
  const [description, setDescription] = useState(policy?.description ?? "");
  const [dataType, setDataType] = useState<RetentionDataType>(
    policy?.dataType ?? "temporary"
  );
  const [priority, setPriority] = useState<RetentionPriority>(
    policy?.priority ?? "medium"
  );
  const [rules, setRules] = useState<Omit<RetentionRule, "id">[]>(
    policy?.rules.map(({ id: _id, ...rule }) => rule) ?? [createEmptyRule()]
  );
  const [filePattern, setFilePattern] = useState(policy?.filePattern ?? "");
  const [minFileSize, setMinFileSize] = useState<string>(
    policy?.minFileSize ? String(policy.minFileSize / (1024 * 1024 * 1024)) : ""
  );
  const [maxFileSize, setMaxFileSize] = useState<string>(
    policy?.maxFileSize ? String(policy.maxFileSize / (1024 * 1024 * 1024)) : ""
  );
  const [excludePatterns, setExcludePatterns] = useState(
    policy?.excludePatterns?.join("\n") ?? ""
  );
  const [requireConfirmation, setRequireConfirmation] = useState(
    policy?.requireConfirmation ?? true
  );
  const [createBackupBeforeDelete, setCreateBackupBeforeDelete] = useState(
    policy?.createBackupBeforeDelete ?? false
  );

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  const dataTypes: RetentionDataType[] = [
    "measurement_set",
    "calibration",
    "image",
    "source_catalog",
    "job_log",
    "temporary",
  ];

  const priorities: RetentionPriority[] = ["low", "medium", "high", "critical"];
  const triggerTypes: { value: RetentionTriggerType; label: string }[] = [
    { value: "age", label: "Age-based" },
    { value: "size", label: "Size-based" },
    { value: "count", label: "Count-based" },
    { value: "manual", label: "Manual only" },
  ];
  const actions: RetentionAction[] = [
    "delete",
    "archive",
    "compress",
    "notify",
  ];

  const addRule = useCallback(() => {
    setRules([...rules, createEmptyRule()]);
  }, [rules]);

  const removeRule = useCallback(
    (index: number) => {
      setRules(rules.filter((_, i) => i !== index));
    },
    [rules]
  );

  const updateRule = useCallback(
    (index: number, updates: Partial<Omit<RetentionRule, "id">>) => {
      setRules(
        rules.map((rule, i) => (i === index ? { ...rule, ...updates } : rule))
      );
    },
    [rules]
  );

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) {
      newErrors.name = "Name is required";
    }

    if (rules.length === 0) {
      newErrors.rules = "At least one rule is required";
    }

    rules.forEach((rule, index) => {
      if (!rule.name.trim()) {
        newErrors[`rule-${index}-name`] = "Rule name is required";
      }
      if (rule.triggerType !== "manual" && rule.threshold <= 0) {
        newErrors[`rule-${index}-threshold`] = "Threshold must be positive";
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    const formData: RetentionPolicyFormData = {
      name: name.trim(),
      description: description.trim() || undefined,
      dataType,
      priority,
      status: policy?.status ?? "active",
      rules,
      filePattern: filePattern.trim() || undefined,
      minFileSize: minFileSize
        ? parseFloat(minFileSize) * 1024 * 1024 * 1024
        : undefined,
      maxFileSize: maxFileSize
        ? parseFloat(maxFileSize) * 1024 * 1024 * 1024
        : undefined,
      excludePatterns: excludePatterns
        ? excludePatterns.split("\n").filter((p) => p.trim())
        : undefined,
      requireConfirmation,
      createBackupBeforeDelete,
    };

    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Basic Info */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Basic Information
        </h3>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Policy Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 ${
                errors.name
                  ? "border-red-500"
                  : "border-gray-300 dark:border-gray-600"
              } focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
              placeholder="e.g., Temporary Files Cleanup"
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-500">{errors.name}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Describe what this policy does..."
            />
          </div>

          {/* Data Type and Priority */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Data Type <span className="text-red-500">*</span>
              </label>
              <select
                value={dataType}
                onChange={(e) =>
                  setDataType(e.target.value as RetentionDataType)
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {dataTypes.map((type) => (
                  <option key={type} value={type}>
                    {DATA_TYPE_LABELS[type]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) =>
                  setPriority(e.target.value as RetentionPriority)
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {priorities.map((p) => (
                  <option key={p} value={p}>
                    {PRIORITY_LABELS[p]}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Rules */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Retention Rules
          </h3>
          <button
            type="button"
            onClick={addRule}
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Add Rule
          </button>
        </div>

        {errors.rules && (
          <p className="mb-4 text-sm text-red-500">{errors.rules}</p>
        )}

        <div className="space-y-4">
          {rules.map((rule, index) => (
            <div
              key={index}
              className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900/50"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Rule {index + 1}
                </span>
                {rules.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeRule(index)}
                    className="text-red-600 hover:text-red-700 dark:text-red-400 text-sm"
                  >
                    Remove
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* Rule Name */}
                <div>
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                    Rule Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={rule.name}
                    onChange={(e) =>
                      updateRule(index, { name: e.target.value })
                    }
                    className={`w-full px-3 py-1.5 text-sm border rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 ${
                      errors[`rule-${index}-name`]
                        ? "border-red-500"
                        : "border-gray-300 dark:border-gray-600"
                    }`}
                    placeholder="e.g., Delete old files"
                  />
                </div>

                {/* Trigger Type */}
                <div>
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                    Trigger Type
                  </label>
                  <select
                    value={rule.triggerType}
                    onChange={(e) => {
                      const newType = e.target.value as RetentionTriggerType;
                      const units = thresholdUnitOptions[newType];
                      updateRule(index, {
                        triggerType: newType,
                        thresholdUnit: units[0]?.value ?? "days",
                      });
                    }}
                    className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  >
                    {triggerTypes.map((tt) => (
                      <option key={tt.value} value={tt.value}>
                        {tt.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Threshold (only for non-manual) */}
                {rule.triggerType !== "manual" && (
                  <>
                    <div>
                      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                        Threshold
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="number"
                          value={rule.threshold}
                          onChange={(e) =>
                            updateRule(index, {
                              threshold: parseFloat(e.target.value) || 0,
                            })
                          }
                          min="0"
                          className={`flex-1 px-3 py-1.5 text-sm border rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 ${
                            errors[`rule-${index}-threshold`]
                              ? "border-red-500"
                              : "border-gray-300 dark:border-gray-600"
                          }`}
                        />
                        <select
                          value={rule.thresholdUnit}
                          onChange={(e) =>
                            updateRule(index, {
                              thresholdUnit: e.target
                                .value as RetentionRule["thresholdUnit"],
                            })
                          }
                          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                        >
                          {thresholdUnitOptions[rule.triggerType].map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </>
                )}

                {/* Action */}
                <div>
                  <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                    Action
                  </label>
                  <select
                    value={rule.action}
                    onChange={(e) =>
                      updateRule(index, {
                        action: e.target.value as RetentionAction,
                      })
                    }
                    className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  >
                    {actions.map((action) => (
                      <option key={action} value={action}>
                        {ACTION_LABELS[action]}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Enabled Toggle */}
                <div className="md:col-span-2 flex items-center">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rule.enabled}
                      onChange={(e) =>
                        updateRule(index, { enabled: e.target.checked })
                      }
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Rule enabled
                    </span>
                  </label>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Advanced Options */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg border border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Advanced Options
        </h3>

        <div className="space-y-4">
          {/* File Pattern */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              File Pattern (glob)
            </label>
            <input
              type="text"
              value={filePattern}
              onChange={(e) => setFilePattern(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
              placeholder="e.g., /data/**/*.fits"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Only files matching this pattern will be considered
            </p>
          </div>

          {/* File Size Range */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Minimum File Size (GB)
              </label>
              <input
                type="number"
                value={minFileSize}
                onChange={(e) => setMinFileSize(e.target.value)}
                min="0"
                step="0.1"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Maximum File Size (GB)
              </label>
              <input
                type="number"
                value={maxFileSize}
                onChange={(e) => setMaxFileSize(e.target.value)}
                min="0"
                step="0.1"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="No limit"
              />
            </div>
          </div>

          {/* Exclude Patterns */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Exclude Patterns (one per line)
            </label>
            <textarea
              value={excludePatterns}
              onChange={(e) => setExcludePatterns(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
              placeholder="/data/protected/**&#10;*.important"
            />
          </div>

          {/* Safety Options */}
          <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={requireConfirmation}
                onChange={(e) => setRequireConfirmation(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Require confirmation before execution
              </span>
            </label>
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={createBackupBeforeDelete}
                onChange={(e) => setCreateBackupBeforeDelete(e.target.checked)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Create backup before deletion
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* Form Actions */}
      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {isSubmitting && (
            <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          )}
          {isEditMode ? "Update Policy" : "Create Policy"}
        </button>
      </div>
    </form>
  );
}

export default RetentionPolicyEditor;
