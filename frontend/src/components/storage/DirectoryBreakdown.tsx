/**
 * Directory Breakdown Component
 *
 * Displays storage usage by directory category with visual breakdown.
 */

import React from "react";
import type { DirectoryUsage } from "../../types/storage";

interface DirectoryBreakdownProps {
  directories: DirectoryUsage[];
  totalSize?: string;
  className?: string;
}

const categoryColors: Record<DirectoryUsage["category"], string> = {
  hdf5: "bg-blue-500",
  ms: "bg-purple-500",
  images: "bg-green-500",
  calibration: "bg-orange-500",
  logs: "bg-gray-500",
  other: "bg-slate-400",
};

const categoryLabels: Record<DirectoryUsage["category"], string> = {
  hdf5: "HDF5 Data",
  ms: "Measurement Sets",
  images: "Images",
  calibration: "Calibration",
  logs: "Logs",
  other: "Other",
};

const categoryIcons: Record<DirectoryUsage["category"], string> = {
  hdf5: "📦",
  ms: "📊",
  images: "🖼️",
  calibration: "🎯",
  logs: "📝",
  other: "📁",
};

function DirectoryRow({ directory }: { directory: DirectoryUsage }) {
  return (
    <div className="flex items-center gap-3 p-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg transition-colors">
      <span className="text-lg">{categoryIcons[directory.category]}</span>
      <div
        className={`w-3 h-3 rounded-full ${categoryColors[directory.category]}`}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="font-medium text-gray-900 dark:text-gray-100 truncate">
            {directory.name}
          </span>
          <span className="text-sm font-mono text-gray-600 dark:text-gray-400 ml-2">
            {directory.size_formatted}
          </span>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
          {directory.path}
        </div>
      </div>
      <div className="text-xs text-gray-400 dark:text-gray-500">
        {directory.file_count.toLocaleString()} files
      </div>
    </div>
  );
}

function CategorySummary({
  directories,
  totalBytes,
}: {
  directories: DirectoryUsage[];
  totalBytes: number;
}) {
  // Group by category
  const byCategory = directories.reduce((acc, dir) => {
    const existing = acc.get(dir.category) || 0;
    acc.set(dir.category, existing + dir.size_bytes);
    return acc;
  }, new Map<DirectoryUsage["category"], number>());

  const categories = Array.from(byCategory.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([category, bytes]) => ({
      category,
      bytes,
      percent: totalBytes > 0 ? (bytes / totalBytes) * 100 : 0,
    }));

  return (
    <div className="mb-4">
      {/* Stacked bar */}
      <div className="h-4 flex rounded-full overflow-hidden bg-gray-200 dark:bg-gray-600">
        {categories.map(({ category, percent }) => (
          <div
            key={category}
            className={`${categoryColors[category]} transition-all duration-300`}
            style={{ width: `${percent}%` }}
            title={`${categoryLabels[category]}: ${percent.toFixed(1)}%`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-3">
        {categories.map(({ category, percent }) => (
          <div key={category} className="flex items-center gap-1.5 text-xs">
            <div
              className={`w-2.5 h-2.5 rounded-full ${categoryColors[category]}`}
            />
            <span className="text-gray-600 dark:text-gray-400">
              {categoryLabels[category]}
            </span>
            <span className="text-gray-400 dark:text-gray-500">
              {percent.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function DirectoryBreakdown({
  directories,
  totalSize,
  className = "",
}: DirectoryBreakdownProps) {
  const totalBytes = directories.reduce((sum, d) => sum + d.size_bytes, 0);
  const sortedDirs = [...directories].sort(
    (a, b) => b.size_bytes - a.size_bytes
  );

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Storage Breakdown
        </h3>
        {totalSize && (
          <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
            Total: {totalSize}
          </span>
        )}
      </div>

      <CategorySummary directories={directories} totalBytes={totalBytes} />

      <div className="space-y-1 max-h-64 overflow-y-auto">
        {sortedDirs.map((dir) => (
          <DirectoryRow key={dir.path} directory={dir} />
        ))}
      </div>

      {directories.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          No directory information available
        </div>
      )}
    </div>
  );
}

export default DirectoryBreakdown;
