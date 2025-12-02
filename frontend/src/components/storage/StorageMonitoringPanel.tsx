/**
 * Storage Monitoring Panel Component
 *
 * Main panel that combines disk usage, directory breakdown, and trends.
 */

import React, { useState } from "react";
import {
  useStorageSummary,
  useCleanupRecommendations,
  useStorageTrends,
} from "../../api/storage";
import { DiskUsagePanel } from "./DiskUsagePanel";
import { DirectoryBreakdown } from "./DirectoryBreakdown";
import { CleanupRecommendations } from "./CleanupRecommendations";
import { StorageTrendChart } from "./StorageTrendChart";

interface StorageMonitoringPanelProps {
  showTrends?: boolean;
  showCleanup?: boolean;
  className?: string;
}

type Tab = "overview" | "details" | "cleanup" | "trends";

export function StorageMonitoringPanel({
  showTrends = true,
  showCleanup = true,
  className = "",
}: StorageMonitoringPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const { data: summary, isLoading, error } = useStorageSummary();
  const { data: cleanup } = useCleanupRecommendations(showCleanup);
  const { data: trends } = useStorageTrends(30, showTrends);

  if (isLoading) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
      >
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
          <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
      >
        <div className="text-red-500 text-center py-8">
          <div className="text-4xl mb-2">⚠️</div>
          <div>Failed to load storage information</div>
          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {error instanceof Error ? error.message : "Unknown error"}
          </div>
        </div>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  const tabs: { id: Tab; label: string; badge?: number }[] = [
    { id: "overview", label: "Overview" },
    { id: "details", label: "Details" },
  ];

  if (showCleanup && cleanup) {
    tabs.push({
      id: "cleanup",
      label: "Cleanup",
      badge: cleanup.candidates.length,
    });
  }

  if (showTrends && trends) {
    tabs.push({ id: "trends", label: "Trends" });
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow ${className}`}>
      {/* Header with tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between px-4 pt-4 pb-0">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Storage Monitoring
          </h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Last updated: {new Date(summary.checked_at).toLocaleTimeString()}
          </span>
        </div>

        <div className="flex gap-1 px-4 mt-3">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === tab.id
                  ? "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
              }`}
            >
              {tab.label}
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-orange-500 text-white rounded-full">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="p-4">
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <DiskUsagePanel
              partitions={summary.partitions}
              alerts={summary.alerts}
            />
            <DirectoryBreakdown
              directories={summary.directories}
              totalSize={summary.total_pipeline_data_formatted}
            />
          </div>
        )}

        {activeTab === "details" && (
          <div className="space-y-4">
            <DiskUsagePanel
              partitions={summary.partitions}
              alerts={summary.alerts}
            />
            <DirectoryBreakdown
              directories={summary.directories}
              totalSize={summary.total_pipeline_data_formatted}
            />
          </div>
        )}

        {activeTab === "cleanup" && cleanup && (
          <CleanupRecommendations
            candidates={cleanup.candidates}
            totalReclaimable={cleanup.total_reclaimable_formatted}
          />
        )}

        {activeTab === "trends" && trends && (
          <StorageTrendChart trends={trends} />
        )}
      </div>
    </div>
  );
}

export default StorageMonitoringPanel;
