import React, { useEffect, useRef, useState, useCallback } from "react";
import { loadEcharts } from "../../lib/loadEcharts";

/**
 * Type for ECharts tooltip formatter params
 */
interface EChartsTooltipParams {
  dataIndex: number;
  data: [number, number]; // [timestamp, value]
  seriesName?: string;
  seriesIndex?: number;
}

export interface LightCurveDataPoint {
  /** Timestamp in ISO format or Unix milliseconds */
  time: string | number;
  /** Flux value */
  flux: number;
  /** Optional flux error (for error bars) */
  fluxError?: number;
  /** Optional label for the point */
  label?: string;
  /** Optional color override */
  color?: string;
}

export interface LightCurveChartProps {
  /** Array of data points */
  data: LightCurveDataPoint[];
  /** Chart title */
  title?: string;
  /** Y-axis label (default: "Flux (Jy)") */
  yAxisLabel?: string;
  /** X-axis label (default: "Time") */
  xAxisLabel?: string;
  /** Height of the chart */
  height?: number | string;
  /** Enable zoom/pan (default: true) */
  enableZoom?: boolean;
  /** Show error bars if fluxError is provided (default: true) */
  showErrorBars?: boolean;
  /** Custom class name */
  className?: string;
  /** Callback when a point is clicked */
  onPointClick?: (point: LightCurveDataPoint, index: number) => void;
  /** Loading state */
  isLoading?: boolean;
  /** Automatically load chart library on mount (default: false) */
  autoLoad?: boolean;
}

type EChartsInstance = import("echarts").ECharts;
type EChartsEventParams = import("echarts").ECElementEvent;
type EChartsOption = import("echarts").EChartsOption;

/**
 * Zoomable time-series light curve chart using ECharts 5.5.
 * Displays flux measurements over time with optional error bars.
 */
export const escapeHtml = (value: string): string => {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
};

const LightCurveChart: React.FC<LightCurveChartProps> = ({
  data,
  title,
  yAxisLabel = "Flux (Jy)",
  xAxisLabel = "Time",
  height = 350,
  enableZoom = true,
  showErrorBars = true,
  className = "",
  onPointClick,
  isLoading = false,
  autoLoad = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<EChartsInstance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [libraryLoaded, setLibraryLoaded] = useState(autoLoad);

  // Initialize and update chart
  useEffect(() => {
    if (!libraryLoaded || error || !containerRef.current || isLoading) return;

    let cancelled = false;
    const renderChart = async () => {
      try {
        const echarts = await loadEcharts();
        if (!containerRef.current || cancelled) return;

        if (!chartRef.current) {
          chartRef.current = echarts.init(containerRef.current);
        }

        // Transform data
        const chartData: [number, number][] = data.map((point) => {
          const time =
            typeof point.time === "string"
              ? new Date(point.time).getTime()
              : point.time;
          return [time, point.flux];
        });

        // Build error bar data if available
        const errorBarData: { coord: [number, number, number, number] }[] = [];
        if (showErrorBars) {
          data.forEach((point, index) => {
            if (point.fluxError !== undefined) {
              const time = chartData[index][0];
              errorBarData.push({
                coord: [
                  time,
                  point.flux - point.fluxError,
                  time,
                  point.flux + point.fluxError,
                ],
              });
            }
          });
        }

        const formatFlux = (value: number): string => {
          if (Math.abs(value) < 0.001) {
            return `${(value * 1e6).toFixed(1)} μJy`;
          }
          if (Math.abs(value) < 1) {
            return `${(value * 1e3).toFixed(2)} mJy`;
          }
          return `${value.toFixed(3)} Jy`;
        };

        const option: EChartsOption = {
          title: title
            ? {
                text: title,
                left: "center",
                textStyle: { fontSize: 14, fontWeight: "bold" },
              }
            : undefined,
          tooltip: {
            trigger: "item",
            formatter: (params: EChartsTooltipParams) => {
              const point = data[params.dataIndex];
              const date = new Date(params.data[0]);
              let html = `<div class="text-sm">
                <div class="font-medium">${escapeHtml(
                  date.toLocaleString()
                )}</div>
                <div>Flux: ${escapeHtml(formatFlux(params.data[1]))}</div>`;
              if (point?.fluxError) {
                html += `<div>Error: ±${escapeHtml(
                  formatFlux(point.fluxError)
                )}</div>`;
              }
              if (point?.label) {
                html += `<div class="text-gray-500">${escapeHtml(
                  point.label
                )}</div>`;
              }
              html += "</div>";
              return html;
            },
            axisPointer: { type: "cross" },
          },
          xAxis: {
            type: "time",
            name: xAxisLabel,
            nameLocation: "middle",
            axisLabel: {
              formatter: (value: number) => {
                const date = new Date(value);
                return `${date.getMonth() + 1}/${date.getDate()}`;
              },
            },
          },
          yAxis: {
            type: "value",
            name: yAxisLabel,
            nameLocation: "middle",
            axisLabel: {
              formatter: formatFlux,
            },
          },
          series: [
            {
              type: "line",
              data: chartData,
              symbolSize: 8,
              itemStyle: { color: "#3b82f6" },
              lineStyle: { width: 2 },
              showSymbol: true,
              emphasis: {
                focus: "series",
                itemStyle: {
                  shadowBlur: 10,
                  shadowColor: "rgba(59, 130, 246, 0.5)",
                },
              },
            },
          ],
          dataZoom: enableZoom
            ? [
                { type: "inside", start: 0, end: 100, xAxisIndex: 0 },
                { type: "slider", start: 0, end: 100, xAxisIndex: 0 },
              ]
            : undefined,
          grid: {
            left: "15%",
            right: "10%",
            bottom: enableZoom ? "20%" : "15%",
            top: title ? "15%" : "10%",
            containLabel: true,
          },
          toolbox: {
            feature: {
              dataZoom: {
                yAxisIndex: "none",
                title: { zoom: "Zoom", back: "Reset" },
              },
              restore: { title: "Restore" },
              saveAsImage: { title: "Save" },
            },
          },
        };

        chartRef.current.setOption(option);

        if (onPointClick) {
          chartRef.current.off("click");
          chartRef.current.on("click", (params: EChartsEventParams) => {
            if (params.dataIndex !== undefined) {
              onPointClick(data[params.dataIndex], params.dataIndex);
            }
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to render chart"
          );
        }
      }
    };

    renderChart();

    return () => {
      cancelled = true;
      if (chartRef.current) {
        chartRef.current.off("click");
      }
    };
  }, [
    libraryLoaded,
    error,
    data,
    title,
    yAxisLabel,
    xAxisLabel,
    enableZoom,
    showErrorBars,
    onPointClick,
    isLoading,
  ]);

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (chartRef.current) {
        chartRef.current.resize();
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.dispose();
        chartRef.current = null;
      }
    };
  }, []);

  const handleResetZoom = useCallback(() => {
    if (chartRef.current) {
      chartRef.current.dispatchAction({
        type: "dataZoom",
        dataZoomIndex: 0,
        start: 0,
        end: 100,
      });
    }
  }, []);

  const heightStyle = typeof height === "number" ? `${height}px` : height;

  if (!libraryLoaded) {
    return (
      <div
        className={`bg-gray-100 rounded-lg flex items-center justify-center ${className}`}
        style={{ height: typeof height === "number" ? `${height}px` : height }}
      >
        <div className="flex flex-col items-center text-gray-600 gap-2">
          <p className="text-sm">Chart library is not loaded.</p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setLibraryLoaded(true)}
            aria-label="Load chart"
          >
            Load chart
          </button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`bg-gray-100 rounded-lg flex items-center justify-center ${className}`}
        style={{ height: heightStyle }}
      >
        <div className="text-center text-gray-500 p-4">
          <svg
            className="w-12 h-12 mx-auto mb-2 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className={`bg-gray-100 rounded-lg flex items-center justify-center ${className}`}
        style={{ height: heightStyle }}
      >
        <div className="flex flex-col items-center text-gray-500">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2" />
          <span className="text-sm">Loading light curve...</span>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div
        className={`bg-gray-100 rounded-lg flex items-center justify-center ${className}`}
        style={{ height: heightStyle }}
      >
        <div className="text-center text-gray-500 p-4">
          <svg
            className="w-12 h-12 mx-auto mb-2 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          <p className="text-sm">No light curve data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <div ref={containerRef} style={{ height: heightStyle, width: "100%" }} />
      {enableZoom && (
        <button
          type="button"
          onClick={handleResetZoom}
          className="absolute top-2 right-2 bg-white/90 hover:bg-white px-2 py-1 rounded shadow text-xs text-gray-700 hover:text-gray-900 transition-colors"
          title="Reset zoom"
        >
          Reset Zoom
        </button>
      )}
    </div>
  );
};

export default LightCurveChart;
