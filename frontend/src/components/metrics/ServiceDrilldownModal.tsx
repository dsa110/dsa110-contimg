/**
 * Service Drilldown Modal Component
 *
 * Displays detailed metrics for a specific service/pod with:
 * - Time series charts with legend toggles
 * - Export to CSV/PNG functionality
 * - Historical comparison
 */

import React, { useRef, useCallback, useState } from "react";
import type { SystemMetric } from "../../types/prometheus";
import { MetricsTimeSeriesChart } from "./MetricsTimeSeriesChart";

export interface ServiceMetricsData {
  service: string;
  pod?: string;
  metrics: SystemMetric[];
  lastUpdated: string;
}

export interface ServiceDrilldownModalProps {
  /** Modal open state */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Service metrics data */
  data: ServiceMetricsData | null;
  /** Title override */
  title?: string;
}

type TimeRange = "1h" | "6h" | "24h";

function formatBytes(bytes: number): string {
  if (bytes >= 1e12) return `${(bytes / 1e12).toFixed(2)} TB`;
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(2)} MB`;
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(2)} KB`;
  return `${bytes.toFixed(2)} B`;
}

function formatValue(value: number, unit: string): string {
  if (unit === "%" || unit === "percent") {
    return `${value.toFixed(2)}%`;
  }
  if (unit === "bytes" || unit === "B") {
    return formatBytes(value);
  }
  if (unit === "ms") {
    return `${value.toFixed(2)} ms`;
  }
  return `${value.toFixed(2)} ${unit}`;
}

export function ServiceDrilldownModal({
  isOpen,
  onClose,
  data,
  title,
}: ServiceDrilldownModalProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [visibleMetrics, setVisibleMetrics] = useState<Set<string>>(new Set());
  const [timeRange, setTimeRange] = useState<TimeRange>("1h");
  const [isExporting, setIsExporting] = useState(false);

  // Initialize visible metrics when data changes
  React.useEffect(() => {
    if (data?.metrics) {
      setVisibleMetrics(new Set(data.metrics.map((m) => m.id)));
    }
  }, [data?.metrics]);

  // Toggle metric visibility
  const toggleMetric = useCallback((metricId: string) => {
    setVisibleMetrics((prev) => {
      const next = new Set(prev);
      if (next.has(metricId)) {
        next.delete(metricId);
      } else {
        next.add(metricId);
      }
      return next;
    });
  }, []);

  // Export as CSV
  const exportCSV = useCallback(() => {
    if (!data) return;
    setIsExporting(true);

    try {
      const headers = ["timestamp", ...data.metrics.map((m) => m.name)];
      const rows: string[][] = [];

      // Get all unique timestamps
      const allTimestamps = new Set<number>();
      data.metrics.forEach((metric) => {
        metric.history.forEach((point) => allTimestamps.add(point.timestamp));
      });

      // Sort timestamps
      const sortedTimestamps = Array.from(allTimestamps).sort((a, b) => a - b);

      // Build rows
      sortedTimestamps.forEach((ts) => {
        const row = [new Date(ts * 1000).toISOString()];
        data.metrics.forEach((metric) => {
          const point = metric.history.find((p) => p.timestamp === ts);
          row.push(point ? point.value.toString() : "");
        });
        rows.push(row);
      });

      // Create CSV content
      const csvContent = [
        headers.join(","),
        ...rows.map((row) => row.join(",")),
      ].join("\n");

      // Download
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${data.service}_metrics_${
        new Date().toISOString().split("T")[0]
      }.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  }, [data]);

  // Export as PNG using canvas API (SVG-based fallback)
  const exportPNG = useCallback(async () => {
    if (!chartContainerRef.current || !data) return;
    setIsExporting(true);

    try {
      // Try to find SVG elements from charts and convert to canvas
      const svgElements = chartContainerRef.current.querySelectorAll("svg");
      if (svgElements.length === 0) {
        console.warn("No SVG charts found for PNG export");
        setIsExporting(false);
        return;
      }

      // Create a combined canvas
      const canvas = document.createElement("canvas");
      const padding = 20;
      const svgWidth = svgElements[0]?.clientWidth || 400;
      const totalHeight = Array.from(svgElements).reduce(
        (h, svg) => h + (svg.clientHeight || 150) + padding,
        padding
      );
      canvas.width = svgWidth + padding * 2;
      canvas.height = totalHeight;

      const ctx = canvas.getContext("2d");
      if (!ctx) {
        throw new Error("Failed to get canvas context");
      }

      // White background
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Title
      ctx.fillStyle = "#1f2937";
      ctx.font = "bold 16px sans-serif";
      ctx.fillText(`${data.service} Metrics`, padding, padding + 16);

      // Convert each SVG to image and draw
      let yOffset = padding + 40;
      for (const svg of Array.from(svgElements)) {
        const svgData = new XMLSerializer().serializeToString(svg);
        const svgBlob = new Blob([svgData], {
          type: "image/svg+xml;charset=utf-8",
        });
        const svgUrl = URL.createObjectURL(svgBlob);

        await new Promise<void>((resolve) => {
          const img = new Image();
          img.onload = () => {
            ctx.drawImage(img, padding, yOffset);
            yOffset += img.height + padding;
            URL.revokeObjectURL(svgUrl);
            resolve();
          };
          img.onerror = () => {
            URL.revokeObjectURL(svgUrl);
            resolve();
          };
          img.src = svgUrl;
        });
      }

      // Download
      const link = document.createElement("a");
      link.href = canvas.toDataURL("image/png");
      link.download = `${data.service}_metrics_${
        new Date().toISOString().split("T")[0]
      }.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("Failed to export PNG:", err);
    } finally {
      setIsExporting(false);
    }
  }, [data]);

  // Filter metrics by time range
  const filterByTimeRange = useCallback(
    (metric: SystemMetric): SystemMetric => {
      const now = Date.now() / 1000;
      const rangeSeconds = {
        "1h": 3600,
        "6h": 6 * 3600,
        "24h": 24 * 3600,
      }[timeRange];

      return {
        ...metric,
        history: metric.history.filter(
          (p) => now - p.timestamp <= rangeSeconds
        ),
      };
    },
    [timeRange]
  );

  if (!isOpen) return null;

  const displayTitle =
    title || (data ? `${data.service} Metrics` : "Service Metrics");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="drilldown-title"
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2
              id="drilldown-title"
              className="text-lg font-semibold text-gray-900 dark:text-gray-100"
            >
              {displayTitle}
            </h2>
            {data?.pod && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Pod: {data.pod}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* Export buttons */}
            <button
              onClick={exportCSV}
              disabled={isExporting || !data}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Export as CSV"
            >
              <span className="flex items-center gap-1.5">
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                CSV
              </span>
            </button>
            <button
              onClick={exportPNG}
              disabled={isExporting || !data}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Export as PNG"
            >
              <span className="flex items-center gap-1.5">
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                PNG
              </span>
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
              aria-label="Close modal"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-700">
          {/* Time range selector */}
          <div className="flex items-center gap-1">
            <span className="text-sm text-gray-500 dark:text-gray-400 mr-2">
              Time range:
            </span>
            {(["1h", "6h", "24h"] as TimeRange[]).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-2 py-1 text-xs font-medium rounded ${
                  timeRange === range
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-500"
                } transition-colors`}
              >
                {range}
              </button>
            ))}
          </div>

          {/* Legend toggles */}
          {data && data.metrics.length > 1 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Show:
              </span>
              {data.metrics.map((metric) => (
                <button
                  key={metric.id}
                  onClick={() => toggleMetric(metric.id)}
                  className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                    visibleMetrics.has(metric.id)
                      ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 border border-transparent"
                  }`}
                >
                  {metric.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4" ref={chartContainerRef}>
          {!data ? (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              No metrics data available
            </div>
          ) : (
            <div className="space-y-6">
              {/* Current values summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {data.metrics
                  .filter((m) => visibleMetrics.has(m.id))
                  .map((metric) => (
                    <div
                      key={metric.id}
                      className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3"
                    >
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {metric.name}
                      </div>
                      <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                        {formatValue(metric.current, metric.unit)}
                      </div>
                      {metric.trendPercent !== undefined && (
                        <div
                          className={`text-xs ${
                            metric.trend === "up"
                              ? "text-red-500"
                              : metric.trend === "down"
                              ? "text-green-500"
                              : "text-gray-400"
                          }`}
                        >
                          {metric.trend === "up"
                            ? "↑"
                            : metric.trend === "down"
                            ? "↓"
                            : "→"}{" "}
                          {metric.trendPercent.toFixed(1)}%
                        </div>
                      )}
                    </div>
                  ))}
              </div>

              {/* Charts */}
              <div className="space-y-4">
                {data.metrics
                  .filter((m) => visibleMetrics.has(m.id))
                  .map((metric) => (
                    <div
                      key={metric.id}
                      className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                    >
                      <MetricsTimeSeriesChart
                        metric={filterByTimeRange(metric)}
                        height={150}
                        showLegend
                      />
                    </div>
                  ))}
              </div>

              {/* Last updated */}
              <div className="text-xs text-gray-400 dark:text-gray-500 text-right">
                Last updated: {new Date(data.lastUpdated).toLocaleString()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ServiceDrilldownModal;
