/**
 * Transit Widget Component
 *
 * Shows upcoming calibrator transits and current LST.
 */

import React, { useMemo } from "react";
import { usePointingStatus } from "../../api/health";
import type { TransitPrediction } from "../../types/health";

interface TransitWidgetProps {
  maxTransits?: number;
  className?: string;
}

function formatTimeUntil(seconds: number): string {
  if (seconds < 0) {
    return "Now";
  }
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m`;
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

function formatLST(hours: number): string {
  const h = Math.floor(hours);
  const m = Math.floor((hours - h) * 60);
  const s = Math.floor(((hours - h) * 60 - m) * 60);
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function TransitStatusBadge({ status }: { status: TransitPrediction["status"] }) {
  const styles = {
    in_progress: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
    upcoming: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    scheduled: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
  };
  
  const labels = {
    in_progress: "● In Progress",
    upcoming: "◐ Upcoming",
    scheduled: "○ Scheduled",
  };
  
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded ${styles[status]}`}>
      {labels[status]}
    </span>
  );
}

function TransitCard({ transit }: { transit: TransitPrediction }) {
  const transitTime = new Date(transit.transit_utc);
  const timeUntil = formatTimeUntil(transit.time_to_transit_sec);
  
  return (
    <div
      className={`p-3 rounded-lg border ${
        transit.status === "in_progress"
          ? "border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-900/20"
          : transit.status === "upcoming"
          ? "border-yellow-300 bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-900/20"
          : "border-gray-200 dark:border-gray-700"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-gray-900 dark:text-gray-100">
          {transit.calibrator}
        </span>
        <TransitStatusBadge status={transit.status} />
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <div className="text-gray-500 dark:text-gray-400">
          Transit: <span className="text-gray-700 dark:text-gray-300">
            {transitTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} UTC
          </span>
        </div>
        <div className="text-gray-500 dark:text-gray-400">
          In: <span className="text-gray-700 dark:text-gray-300 font-medium">{timeUntil}</span>
        </div>
        <div className="text-gray-500 dark:text-gray-400">
          RA: <span className="text-gray-700 dark:text-gray-300">{transit.ra_deg.toFixed(2)}°</span>
        </div>
        <div className="text-gray-500 dark:text-gray-400">
          Elev: <span className="text-gray-700 dark:text-gray-300">{transit.elevation_at_transit.toFixed(1)}°</span>
        </div>
      </div>
    </div>
  );
}

function LSTDisplay({ lst, lstDeg }: { lst: number; lstDeg: number }) {
  return (
    <div className="flex items-center gap-4 p-3 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg text-white">
      <div className="flex flex-col items-center">
        <span className="text-xs opacity-75">Local Sidereal Time</span>
        <span className="text-2xl font-mono font-bold">{formatLST(lst)}</span>
      </div>
      <div className="h-10 w-px bg-white/30" />
      <div className="flex flex-col items-center">
        <span className="text-xs opacity-75">LST (degrees)</span>
        <span className="text-xl font-mono">{lstDeg.toFixed(2)}°</span>
      </div>
    </div>
  );
}

export function TransitWidget({ maxTransits = 5, className = "" }: TransitWidgetProps) {
  const { data, isLoading, error } = usePointingStatus();
  
  const sortedTransits = useMemo(() => {
    if (!data?.upcoming_transits) return [];
    return [...data.upcoming_transits]
      .sort((a, b) => a.time_to_transit_sec - b.time_to_transit_sec)
      .slice(0, maxTransits);
  }, [data, maxTransits]);
  
  if (isLoading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}>
        <div className="animate-pulse">
          <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-200 dark:bg-gray-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}>
        <div className="text-red-500">Failed to load pointing status</div>
      </div>
    );
  }
  
  if (!data) {
    return null;
  }
  
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 ${className}`}>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        Calibrator Transits
      </h3>
      
      {/* LST Display */}
      <LSTDisplay lst={data.current_lst} lstDeg={data.current_lst_deg} />
      
      {/* Active calibrator indicator */}
      {data.active_calibrator && (
        <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
            <span className="text-green-700 dark:text-green-400 font-medium">
              {data.active_calibrator} currently transiting
            </span>
          </div>
        </div>
      )}
      
      {/* Upcoming transits */}
      <div className="mt-4">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Upcoming Transits
        </h4>
        {sortedTransits.length > 0 ? (
          <div className="space-y-2">
            {sortedTransits.map((transit) => (
              <TransitCard key={transit.calibrator} transit={transit} />
            ))}
          </div>
        ) : (
          <div className="text-gray-500 dark:text-gray-400 text-center py-4">
            No upcoming transits in the next 24 hours
          </div>
        )}
      </div>
      
      {/* Last updated */}
      <div className="mt-4 text-xs text-gray-500 dark:text-gray-400 text-right">
        Updated: {new Date(data.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}

export default TransitWidget;
