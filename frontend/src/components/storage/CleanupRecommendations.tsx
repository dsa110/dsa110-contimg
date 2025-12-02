/**
 * Cleanup Recommendations Component
 *
 * Displays storage cleanup recommendations with reclaimable space estimates.
 */

import React, { useState } from "react";
import type { CleanupCandidate } from "../../types/storage";

interface CleanupRecommendationsProps {
  candidates: CleanupCandidate[];
  totalReclaimable?: string;
  className?: string;
  onRequestCleanup?: (paths: string[]) => void;
}

const categoryLabels: Record<CleanupCandidate["category"], string> = {
  old_ms: "Old Measurement Sets",
  old_images: "Old Images",
  old_logs: "Old Logs",
  temp: "Temporary Files",
  orphaned: "Orphaned Data",
};

const categoryColors: Record<CleanupCandidate["category"], string> = {
  old_ms:
    "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  old_images:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  old_logs: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
  temp: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
  orphaned: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

function CandidateRow({
  candidate,
  isSelected,
  onSelect,
}: {
  candidate: CleanupCandidate;
  isSelected: boolean;
  onSelect: (selected: boolean) => void;
}) {
  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
        isSelected
          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
          : "border-gray-200 dark:border-gray-700"
      }`}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={(e) => onSelect(e.target.checked)}
        disabled={!candidate.safe_to_delete}
        className="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 disabled:opacity-50"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span
            className={`px-2 py-0.5 text-xs font-medium rounded ${
              categoryColors[candidate.category]
            }`}
          >
            {categoryLabels[candidate.category]}
          </span>
          <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
            {candidate.size_formatted}
          </span>
        </div>
        <div className="text-sm text-gray-900 dark:text-gray-100 truncate">
          {candidate.path}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {candidate.reason} • {candidate.age_days} days old
        </div>
        {!candidate.safe_to_delete && (
          <div className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
            ⚠️ Manual review recommended before deletion
          </div>
        )}
      </div>
    </div>
  );
}

export function CleanupRecommendations({
  candidates,
  totalReclaimable,
  className = "",
  onRequestCleanup,
}: CleanupRecommendationsProps) {
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());

  const togglePath = (path: string, selected: boolean) => {
    const newSet = new Set(selectedPaths);
    if (selected) {
      newSet.add(path);
    } else {
      newSet.delete(path);
    }
    setSelectedPaths(newSet);
  };

  const selectAllSafe = () => {
    const safePaths = candidates
      .filter((c) => c.safe_to_delete)
      .map((c) => c.path);
    setSelectedPaths(new Set(safePaths));
  };

  const clearSelection = () => {
    setSelectedPaths(new Set());
  };

  const selectedSize = candidates
    .filter((c) => selectedPaths.has(c.path))
    .reduce((sum, c) => sum + c.size_bytes, 0);

  const formatBytes = (bytes: number): string => {
    if (bytes >= 1e12) return `${(bytes / 1e12).toFixed(2)} TB`;
    if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`;
    if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(2)} MB`;
    return `${(bytes / 1e3).toFixed(2)} KB`;
  };

  // Group by category for summary
  const byCategory = candidates.reduce((acc, c) => {
    if (!acc[c.category]) {
      acc[c.category] = { count: 0, bytes: 0 };
    }
    acc[c.category].count++;
    acc[c.category].bytes += c.size_bytes;
    return acc;
  }, {} as Record<string, { count: number; bytes: number }>);

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Cleanup Recommendations
          </h3>
          {totalReclaimable && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Up to {totalReclaimable} can be reclaimed
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={selectAllSafe}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Select all safe
          </button>
          <span className="text-gray-300 dark:text-gray-600">|</span>
          <button
            onClick={clearSelection}
            className="text-sm text-gray-600 dark:text-gray-400 hover:underline"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Category summary */}
      <div className="flex flex-wrap gap-2 mb-4">
        {Object.entries(byCategory).map(([cat, stats]) => (
          <span
            key={cat}
            className={`px-2 py-1 text-xs rounded ${
              categoryColors[cat as CleanupCandidate["category"]]
            }`}
          >
            {stats.count} {categoryLabels[cat as CleanupCandidate["category"]]}
          </span>
        ))}
      </div>

      {/* Candidates list */}
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {candidates.map((candidate) => (
          <CandidateRow
            key={candidate.path}
            candidate={candidate}
            isSelected={selectedPaths.has(candidate.path)}
            onSelect={(selected) => togglePath(candidate.path, selected)}
          />
        ))}
      </div>

      {candidates.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <div className="text-4xl mb-2">✨</div>
          <div>No cleanup recommendations</div>
          <div className="text-sm">Storage is well maintained</div>
        </div>
      )}

      {/* Action bar */}
      {selectedPaths.size > 0 && onRequestCleanup && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {selectedPaths.size} items selected ({formatBytes(selectedSize)})
          </div>
          <button
            onClick={() => onRequestCleanup(Array.from(selectedPaths))}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
          >
            Request Cleanup
          </button>
        </div>
      )}
    </div>
  );
}

export default CleanupRecommendations;
