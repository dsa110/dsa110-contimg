/**
 * Validity Window Timeline Component
 *
 * Visualizes calibration validity windows over time.
 */

import React, { useMemo } from "react";
import { useValidityTimeline } from "../../api/health";
import type { ValidityTimelineEntry } from "../../types/health";

interface ValidityWindowTimelineProps {
  hoursBack?: number;
  hoursForward?: number;
  className?: string;
}

const TABLE_TYPE_COLORS: Record<string, string> = {
  BP: "bg-blue-500",
  BA: "bg-blue-400",
  GP: "bg-green-500",
  GA: "bg-green-400",
  "2G": "bg-purple-500",
  K: "bg-yellow-500",
  FLUX: "bg-orange-500",
};

function getTableColor(tableType: string): string {
  return TABLE_TYPE_COLORS[tableType] || "bg-gray-500";
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

interface TimelineBarProps {
  entry: ValidityTimelineEntry;
  windowStartTime: number;
  windowEndTime: number;
  totalWidth: number;
}

function TimelineBar({
  entry,
  windowStartTime,
  windowEndTime,
  totalWidth,
}: TimelineBarProps) {
  const startTime = new Date(entry.start_iso).getTime();
  const endTime = new Date(entry.end_iso).getTime();
  const windowDuration = windowEndTime - windowStartTime;

  const left = Math.max(
    0,
    ((startTime - windowStartTime) / windowDuration) * totalWidth
  );
  const right = Math.min(
    totalWidth,
    ((endTime - windowStartTime) / windowDuration) * totalWidth
  );
  const width = Math.max(2, right - left);

  return (
    <div
      className={`absolute h-6 rounded ${getTableColor(
        entry.table_type
      )} opacity-80 hover:opacity-100 transition-opacity cursor-pointer`}
      style={{ left: `${left}%`, width: `${width}%` }}
      title={`${entry.set_name} (${entry.table_type})\n${formatDate(
        entry.start_iso
      )} ${formatTime(entry.start_iso)} - ${formatTime(entry.end_iso)}\n${
        entry.is_current ? "✓ Active" : ""
      }`}
    >
      <span className="text-xs text-white px-1 truncate block leading-6">
        {entry.table_type}
      </span>
    </div>
  );
}

export function ValidityWindowTimeline({
  hoursBack = 24,
  hoursForward = 24,
  className = "",
}: ValidityWindowTimelineProps) {
  const { data, isLoading, error } = useValidityTimeline(
    hoursBack,
    hoursForward
  );

  const timeMarkers = useMemo(() => {
    if (!data) return [];
    const start = new Date(data.timeline_start).getTime();
    const end = new Date(data.timeline_end).getTime();
    const duration = end - start;
    const markers: { position: number; label: string; isNow: boolean }[] = [];

    // Add markers every 6 hours
    const interval = 6 * 60 * 60 * 1000;
    let current = Math.ceil(start / interval) * interval;

    while (current < end) {
      const position = ((current - start) / duration) * 100;
      const date = new Date(current);
      markers.push({
        position,
        label: `${formatDate(date.toISOString())} ${formatTime(
          date.toISOString()
        )}`,
        isNow: false,
      });
      current += interval;
    }

    // Add "now" marker
    const now = new Date(data.current_time).getTime();
    const nowPosition = ((now - start) / duration) * 100;
    markers.push({
      position: nowPosition,
      label: "Now",
      isNow: true,
    });

    return markers;
  }, [data]);

  const groupedEntries = useMemo(() => {
    if (!data?.windows) return new Map<string, ValidityTimelineEntry[]>();
    const groups = new Map<string, ValidityTimelineEntry[]>();

    for (const entry of data.windows) {
      const key = entry.set_name;
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key)!.push(entry);
    }

    return groups;
  }, [data]);

  if (isLoading) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
      >
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4" />
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
      >
        <div className="text-red-500">Failed to load validity timeline</div>
      </div>
    );
  }

  if (!data || data.windows.length === 0) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
      >
        <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">
          Calibration Validity Windows
        </h3>
        <div className="text-gray-500 dark:text-gray-400 text-center py-8">
          No validity windows in the selected time range
        </div>
      </div>
    );
  }

  const windowStartTime = new Date(data.timeline_start).getTime();
  const windowEndTime = new Date(data.timeline_end).getTime();

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Calibration Validity Windows
        </h3>
        <div className="flex gap-2 text-xs">
          {Object.entries(TABLE_TYPE_COLORS).map(([type, color]) => (
            <span key={type} className="flex items-center gap-1">
              <span className={`w-3 h-3 rounded ${color}`} />
              {type}
            </span>
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Time axis */}
        <div className="relative h-6 border-b border-gray-300 dark:border-gray-600 mb-2">
          {timeMarkers.map((marker, idx) => (
            <div
              key={idx}
              className="absolute top-0 h-full flex flex-col items-center"
              style={{
                left: `${marker.position}%`,
                transform: "translateX(-50%)",
              }}
            >
              <div
                className={`w-px h-3 ${
                  marker.isNow ? "bg-red-500" : "bg-gray-400"
                }`}
              />
              <span
                className={`text-xs ${
                  marker.isNow ? "text-red-500 font-bold" : "text-gray-500"
                }`}
              >
                {marker.label}
              </span>
            </div>
          ))}
        </div>

        {/* Timeline rows */}
        <div className="space-y-2">
          {Array.from(groupedEntries.entries()).map(([setName, entries]) => (
            <div key={setName} className="flex items-center gap-2">
              <div
                className="w-32 text-sm text-gray-600 dark:text-gray-400 truncate"
                title={setName}
              >
                {setName.split("_").slice(-2).join("_")}
              </div>
              <div className="flex-1 relative h-6 bg-gray-100 dark:bg-gray-700 rounded">
                {entries.map((entry, idx) => (
                  <TimelineBar
                    key={`${entry.set_name}-${entry.table_type}-${idx}`}
                    entry={entry}
                    windowStartTime={windowStartTime}
                    windowEndTime={windowEndTime}
                    totalWidth={100}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Now line */}
        <div
          className="absolute top-6 bottom-0 w-px bg-red-500 z-10"
          style={{
            left: `${
              ((new Date(data.current_time).getTime() - windowStartTime) /
                (windowEndTime - windowStartTime)) *
              100
            }%`,
          }}
        />
      </div>

      <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
        {data.total_windows} calibration tables shown •{" "}
        {formatDate(data.timeline_start)} {formatTime(data.timeline_start)} to{" "}
        {formatDate(data.timeline_end)} {formatTime(data.timeline_end)}
      </div>
    </div>
  );
}

export default ValidityWindowTimeline;
