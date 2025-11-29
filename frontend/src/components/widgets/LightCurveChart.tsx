import React, { useEffect, useRef, useState, useCallback } from "react";

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
}

declare global {
  interface Window {
    echarts?: {
      init: (element: HTMLElement, theme?: string) => EChartsInstance;
      getInstanceByDom: (element: HTMLElement) => EChartsInstance | undefined;
    };
  }
}

interface EChartsInstance {
  setOption: (option: EChartsOption) => void;
  resize: () => void;
  dispose: () => void;
  on: (eventName: string, handler: (params: EChartsEventParams) => void) => void;
  off: (eventName: string) => void;
  dispatchAction: (action: { type: string; dataZoomIndex?: number; start?: number; end?: number }) => void;
}

interface EChartsEventParams {
  dataIndex: number;
  data: [number, number];
}

interface EChartsOption {
  title?: { text?: string; left?: string; textStyle?: { fontSize?: number; fontWeight?: string } };
  tooltip?: {
    trigger?: string;
    formatter?: (params: EChartsTooltipParams) => string;
    axisPointer?: { type?: string };
  };
  xAxis?: {
    type?: string;
    name?: string;
    nameLocation?: string;
    axisLabel?: { formatter?: (value: number) => string };
  };
  yAxis?: {
    type?: string;
    name?: string;
    nameLocation?: string;
    axisLabel?: { formatter?: (value: number) => string };
  };
  series?: EChartsSeries[];
  dataZoom?: { type?: string; start?: number; end?: number; xAxisIndex?: number }[];
  grid?: { left?: string; right?: string; bottom?: string; top?: string; containLabel?: boolean };
  toolbox?: {
    feature?: {
      dataZoom?: { yAxisIndex?: string; title?: { zoom?: string; back?: string } };
      restore?: { title?: string };
      saveAsImage?: { title?: string };
    };
  };
}

interface EChartsSeries {
  type: string;
  data: [number, number][];
  symbolSize?: number;
  itemStyle?: { color?: string };
  lineStyle?: { width?: number };
  showSymbol?: boolean;
  emphasis?: { focus?: string; itemStyle?: { shadowBlur?: number; shadowColor?: string } };
}

interface EChartsTooltipParams {
  data: [number, number];
  dataIndex: number;
}

const ECHARTS_URL = "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js";

/**
 * Zoomable time-series light curve chart using ECharts 5.5.
 * Displays flux measurements over time with optional error bars.
 */
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
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<EChartsInstance | null>(null);
  const [isScriptLoading, setIsScriptLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load ECharts script
  useEffect(() => {
    const loadECharts = async () => {
      if (window.echarts) {
        setIsScriptLoading(false);
        return;
      }

      try {
        if (!document.querySelector(`script[src="${ECHARTS_URL}"]`)) {
          await new Promise<void>((resolve, reject) => {
            const script = document.createElement("script");
            script.src = ECHARTS_URL;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Failed to load ECharts"));
            document.head.appendChild(script);
          });
        }

        // Wait for echarts to be available
        let attempts = 0;
        while (!window.echarts && attempts < 50) {
          await new Promise((resolve) => setTimeout(resolve, 100));
          attempts++;
        }

        if (!window.echarts) {
          throw new Error("ECharts failed to initialize");
        }

        setIsScriptLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load chart library");
        setIsScriptLoading(false);
      }
    };

    loadECharts();
  }, []);

  // Initialize and update chart
  useEffect(() => {
    if (isScriptLoading || error || !containerRef.current || !window.echarts || isLoading) return;

    // Initialize or get existing instance
    if (!chartRef.current) {
      chartRef.current = window.echarts.init(containerRef.current);
    }

    // Transform data
    const chartData: [number, number][] = data.map((point) => {
      const time =
        typeof point.time === "string" ? new Date(point.time).getTime() : point.time;
      return [time, point.flux];
    });

    // Build error bar data if available
    const errorBarData: { coord: [number, number, number, number] }[] = [];
    if (showErrorBars) {
      data.forEach((point, index) => {
        if (point.fluxError !== undefined) {
          const time = chartData[index][0];
          errorBarData.push({
            coord: [time, point.flux - point.fluxError, time, point.flux + point.fluxError],
          });
        }
      });
    }

    // Format flux values smartly
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
            <div class="font-medium">${date.toLocaleString()}</div>
            <div>Flux: ${formatFlux(params.data[1])}</div>`;
          if (point?.fluxError) {
            html += `<div>Error: ±${formatFlux(point.fluxError)}</div>`;
          }
          if (point?.label) {
            html += `<div class="text-gray-500">${point.label}</div>`;
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
            itemStyle: { shadowBlur: 10, shadowColor: "rgba(59, 130, 246, 0.5)" },
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
          dataZoom: { yAxisIndex: "none", title: { zoom: "Zoom", back: "Reset" } },
          restore: { title: "Restore" },
          saveAsImage: { title: "Save" },
        },
      },
    };

    chartRef.current.setOption(option);

    // Handle click events
    if (onPointClick) {
      chartRef.current.off("click");
      chartRef.current.on("click", (params: EChartsEventParams) => {
        if (params.dataIndex !== undefined) {
          onPointClick(data[params.dataIndex], params.dataIndex);
        }
      });
    }

    // Cleanup
    return () => {
      if (chartRef.current) {
        chartRef.current.off("click");
      }
    };
  }, [
    isScriptLoading,
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

  if (isScriptLoading || isLoading) {
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
