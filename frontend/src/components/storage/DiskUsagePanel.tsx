/**
 * Disk Usage Panel Component
 *
 * Displays disk partition usage with visual progress bars and alerts.
 */

import React from "react";
import type { DiskPartition, StorageAlert } from "../../types/storage";

interface DiskUsagePanelProps {
  partitions: DiskPartition[];
  alerts?: StorageAlert[];
  className?: string;
}

function getUsageColor(percent: number): string {
  if (percent >= 90) return "bg-red-500";
  if (percent >= 80) return "bg-yellow-500";
  if (percent >= 70) return "bg-orange-400";
  return "bg-green-500";
}

function getUsageTextColor(percent: number): string {
  if (percent >= 90) return "text-red-600 dark:text-red-400";
  if (percent >= 80) return "text-yellow-600 dark:text-yellow-400";
  return "text-gray-600 dark:text-gray-400";
}

function PartitionCard({ partition }: { partition: DiskPartition }) {
  const usageColor = getUsageColor(partition.usage_percent);
  const textColor = getUsageTextColor(partition.usage_percent);

  return (
    <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h4 className="font-medium text-gray-900 dark:text-gray-100">
            {partition.mount_point}
          </h4>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {partition.device} • {partition.filesystem}
          </p>
        </div>
        <div className={`text-right ${textColor}`}>
          <span className="text-2xl font-bold">
            {partition.usage_percent.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full ${usageColor} transition-all duration-300`}
          style={{ width: `${partition.usage_percent}%` }}
        />
      </div>

      {/* Size details */}
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>Used: {partition.used_formatted}</span>
        <span>Free: {partition.free_formatted}</span>
        <span>Total: {partition.total_formatted}</span>
      </div>
    </div>
  );
}

function AlertBanner({ alerts }: { alerts: StorageAlert[] }) {
  if (alerts.length === 0) return null;

  const criticalAlerts = alerts.filter((a) => a.severity === "critical");
  const warningAlerts = alerts.filter((a) => a.severity === "warning");

  return (
    <div className="space-y-2 mb-4">
      {criticalAlerts.map((alert, i) => (
        <div
          key={`critical-${i}`}
          className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded-r-lg"
        >
          <span className="text-red-500 text-lg">⚠️</span>
          <span className="text-red-800 dark:text-red-200">
            {alert.message}
          </span>
        </div>
      ))}
      {warningAlerts.map((alert, i) => (
        <div
          key={`warning-${i}`}
          className="flex items-center gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-500 rounded-r-lg"
        >
          <span className="text-yellow-500 text-lg">⚡</span>
          <span className="text-yellow-800 dark:text-yellow-200">
            {alert.message}
          </span>
        </div>
      ))}
    </div>
  );
}

export function DiskUsagePanel({
  partitions,
  alerts = [],
  className = "",
}: DiskUsagePanelProps) {
  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Disk Usage
      </h3>

      <AlertBanner alerts={alerts} />

      <div className="space-y-4">
        {partitions.map((partition) => (
          <PartitionCard key={partition.mount_point} partition={partition} />
        ))}
      </div>

      {partitions.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No disk information available
        </div>
      )}
    </div>
  );
}

export default DiskUsagePanel;
