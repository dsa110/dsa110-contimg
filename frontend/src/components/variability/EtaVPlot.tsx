import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import type * as echarts from "echarts";
import type { ECElementEvent } from "echarts";
import { loadEcharts } from "../../lib/loadEcharts";
import VariabilityControls, { VariabilityControlsValues } from "./VariabilityControls";
import SourcePreview from "./SourcePreview";

/**
 * Extended event data for EtaVPlot scatter points.
 * The data property contains the source information attached to each point.
 */
interface EtaVPlotEventData {
  source?: SourcePoint;
  [key: string]: unknown;
}

/**
 * Extended ECharts element event with typed data.
 */
interface EtaVPlotClickEvent extends Omit<ECElementEvent, "data"> {
  data?: EtaVPlotEventData;
  event?: {
    event?: MouseEvent;
  };
}

export interface SourcePoint {
  id: string;
  name: string;
  ra: number;
  dec: number;
  eta: number;
  v: number;
  peakFlux?: number;
  nMeasurements?: number;
}

export interface EtaVPlotProps {
  /** Source data to plot */
  sources: SourcePoint[];
  /** Whether data is loading */
  isLoading?: boolean;
  /** Callback when source is selected */
  onSourceSelect?: (sourceId: string) => void;
  /** Height of the chart */
  height?: number;
  /** Custom class name */
  className?: string;
}

/**
 * η-V variability scatter plot using ECharts.
 * Highlights potential transient candidates above thresholds.
 */
const EtaVPlot: React.FC<EtaVPlotProps> = ({
  sources,
  isLoading = false,
  onSourceSelect,
  height = 500,
  className = "",
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [echartsReady, setEchartsReady] = useState(false);

  // Control state
  const [controls, setControls] = useState<VariabilityControlsValues>({
    etaThreshold: 1.5,
    vThreshold: 0.1,
    etaSigma: 2,
    vSigma: 2,
    useSigmaThreshold: true,
    minDataPoints: 3,
    colorBy: "variability",
  });

  // Preview state
  const [hoverSource, setHoverSource] = useState<SourcePoint | null>(null);
  const [hoverPosition, setHoverPosition] = useState({ x: 0, y: 0 });
  const [selectedSource, setSelectedSource] = useState<SourcePoint | null>(null);

  // Escape key handler for modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && selectedSource) {
        setSelectedSource(null);
      }
    };
    if (selectedSource) {
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }
  }, [selectedSource]);

  // Calculate dynamic thresholds
  const calculateThresholds = useCallback(() => {
    if (!controls.useSigmaThreshold || sources.length === 0) {
      return { etaLine: controls.etaThreshold, vLine: controls.vThreshold };
    }

    const etaValues = sources.map((s) => s.eta);
    const vValues = sources.map((s) => s.v);

    const mean = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;
    const std = (arr: number[]) => {
      const m = mean(arr);
      return Math.sqrt(arr.reduce((sum, x) => sum + (x - m) ** 2, 0) / arr.length);
    };

    const etaMean = mean(etaValues);
    const etaStd = std(etaValues);
    const vMean = mean(vValues);
    const vStd = std(vValues);

    return {
      etaLine: etaMean + controls.etaSigma * etaStd,
      vLine: vMean + controls.vSigma * vStd,
    };
  }, [sources, controls]);

  // Filter sources by min data points and ensure positive values for log scale
  const filteredSources = useMemo(
    () =>
      sources.filter(
        (s) => (s.nMeasurements ?? 10) >= controls.minDataPoints && s.eta > 0 && s.v > 0 // Filter out non-positive values for log scale
      ),
    [sources, controls.minDataPoints]
  );

  // Count filtered out sources
  const filteredOutCount = sources.length - filteredSources.length;

  // Identify candidates (above both thresholds)
  const { etaLine, vLine } = calculateThresholds();
  const candidates = useMemo(
    () => filteredSources.filter((s) => s.eta > etaLine && s.v > vLine),
    [filteredSources, etaLine, vLine]
  );

  // Pre-compute max values once to avoid O(n²) in color mapping
  const colorMaxValues = useMemo(() => {
    if (filteredSources.length === 0) return { variability: 1, flux: 1, measurements: 1 };
    return {
      variability: Math.max(...filteredSources.map((s) => s.eta * s.v), 1),
      flux: Math.max(...filteredSources.map((s) => s.peakFlux ?? 0), 1),
      measurements: Math.max(...filteredSources.map((s) => s.nMeasurements ?? 0), 1),
    };
  }, [filteredSources]);

  // Color mapping function - now O(1) per point
  const getPointColor = useCallback(
    (source: SourcePoint, isCandidate: boolean) => {
      if (isCandidate) return "#ff0000";
      if (controls.colorBy === "none") return "rgba(79, 195, 161, 0.6)";

      let value = 0;
      let max = 1;

      switch (controls.colorBy) {
        case "variability":
          value = source.eta * source.v;
          max = colorMaxValues.variability;
          break;
        case "flux":
          value = source.peakFlux ?? 0;
          max = colorMaxValues.flux;
          break;
        case "measurements":
          value = source.nMeasurements ?? 0;
          max = colorMaxValues.measurements;
          break;
      }

      const ratio = Math.min(value / max, 1);
      // Gradient from green (#4fc3a1) to yellow (#f0c674)
      const r = Math.round(79 + ratio * (240 - 79));
      const g = Math.round(195 + ratio * (198 - 195));
      const b = Math.round(161 - ratio * (161 - 116));
      return `rgba(${r}, ${g}, ${b}, 0.7)`;
    },
    [controls.colorBy, colorMaxValues]
  );

  // Initialize chart with lazy-loaded ECharts
  useEffect(() => {
    if (!chartRef.current) return;

    let mounted = true;

    const initChart = async () => {
      const echartsModule = await loadEcharts();
      if (!mounted || !chartRef.current) return;
      
      chartInstance.current = echartsModule.init(chartRef.current);
      setEchartsReady(true);
    };

    initChart();

    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      mounted = false;
      window.removeEventListener("resize", handleResize);
      chartInstance.current?.dispose();
    };
  }, []);

  // Update chart
  useEffect(() => {
    if (!chartInstance.current || !echartsReady || isLoading) return;

    const candidateIds = new Set(candidates.map((c) => c.id));

    // Prepare scatter data
    const scatterData = filteredSources.map((source) => ({
      value: [source.eta, source.v],
      itemStyle: {
        color: getPointColor(source, candidateIds.has(source.id)),
      },
      symbolSize: candidateIds.has(source.id) ? 10 : 6,
      source,
    }));

    // Compute data bounds for threshold lines (log scale doesn't support "min"/"max")
    const etaValues = filteredSources.map((s) => s.eta);
    const vValues = filteredSources.map((s) => s.v);
    const etaMin = Math.min(...etaValues) * 0.5;
    const etaMax = Math.max(...etaValues) * 2;
    const vMin = Math.min(...vValues) * 0.5;
    const vMax = Math.max(...vValues) * 2;

    // Build subtitle with excluded count info
    const excludedInfo = filteredOutCount > 0 ? ` (${filteredOutCount} excluded: η≤0 or v≤0)` : "";
    const subtext = `${filteredSources.length} sources, ${candidates.length} candidates${excludedInfo}`;

    const option: echarts.EChartsOption = {
      title: {
        text: "η-V Variability Plot",
        subtext,
        left: "center",
        textStyle: { color: "#324960", fontSize: 16 },
        subtextStyle: { color: "#666" },
      },
      tooltip: {
        trigger: "item",
        formatter: () => "",
        show: false,
      },
      xAxis: {
        name: "η (eta)",
        nameLocation: "middle",
        nameGap: 30,
        type: "log",
        axisLabel: { formatter: "{value}" },
      },
      yAxis: {
        name: "V",
        nameLocation: "middle",
        nameGap: 40,
        type: "log",
      },
      series: [
        {
          type: "scatter",
          data: scatterData,
          emphasis: {
            itemStyle: {
              borderColor: "#324960",
              borderWidth: 2,
            },
          },
        },
        // η threshold line - use computed bounds for log scale
        {
          type: "line",
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#ff6b6b", type: "dashed", width: 2 },
            data: [
              [
                { xAxis: etaLine, yAxis: vMin },
                { xAxis: etaLine, yAxis: vMax },
              ],
            ],
            label: {
              formatter: `η = ${etaLine.toFixed(2)}`,
              position: "end",
            },
          },
        },
        // V threshold line - use computed bounds for log scale
        {
          type: "line",
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#ff6b6b", type: "dashed", width: 2 },
            data: [
              [
                { xAxis: etaMin, yAxis: vLine },
                { xAxis: etaMax, yAxis: vLine },
              ],
            ],
            label: {
              formatter: `V = ${vLine.toFixed(3)}`,
              position: "end",
            },
          },
        },
      ],
      toolbox: {
        right: 20,
        feature: {
          dataZoom: { title: { zoom: "Zoom", back: "Reset" } },
          restore: { title: "Reset" },
          saveAsImage: { title: "Save" },
        },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: 0 },
        { type: "inside", yAxisIndex: 0 },
      ],
    };

    chartInstance.current.setOption(option, { notMerge: false });

    // Clean up previous event handlers before adding new ones
    const chart = chartInstance.current;
    chart.off("mouseover");
    chart.off("mouseout");
    chart.off("click");

    // Event handlers
    chart.on("mouseover", (params: EtaVPlotClickEvent) => {
      if (params.componentType === "series" && params.data?.source) {
        const event = params.event?.event;
        setHoverSource(params.data.source);
        if (event) {
          setHoverPosition({ x: event.clientX, y: event.clientY });
        }
      }
    });

    chart.on("mouseout", () => {
      setHoverSource(null);
    });

    chart.on("click", (params: EtaVPlotClickEvent) => {
      if (params.componentType === "series" && params.data?.source) {
        setSelectedSource(params.data.source);
        setHoverSource(null);
      }
    });
  }, [
    echartsReady,
    filteredSources,
    filteredOutCount,
    candidates,
    controls,
    isLoading,
    etaLine,
    vLine,
    getPointColor,
  ]);

  const handleControlChange = (values: Partial<VariabilityControlsValues>) => {
    setControls((prev) => ({ ...prev, ...values }));
  };

  const handleNavigate = (sourceId: string) => {
    onSourceSelect?.(sourceId);
    setSelectedSource(null);
  };

  return (
    <div className={`${className}`}>
      <div className="flex gap-4">
        {/* Chart area */}
        <div className="flex-1 relative">
          {isLoading ? (
            <div
              className="flex items-center justify-center bg-gray-50 rounded-lg"
              style={{ height }}
            >
              <div className="text-center">
                <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <span className="text-gray-500">Loading sources...</span>
              </div>
            </div>
          ) : (
            <div ref={chartRef} style={{ height, width: "100%" }} />
          )}

          {/* Hover preview */}
          {hoverSource && (
            <SourcePreview
              {...hoverSource}
              sourceId={hoverSource.id}
              position={hoverPosition}
              isHover={true}
            />
          )}
        </div>

        {/* Controls panel */}
        <div className="w-64 flex-shrink-0">
          <VariabilityControls {...controls} onChange={handleControlChange} />

          {/* Candidates list */}
          {candidates.length > 0 && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3">
              <h4 className="font-semibold text-red-700 text-sm mb-2">
                Candidates ({candidates.length})
              </h4>
              <div className="max-h-40 overflow-y-auto space-y-1">
                {candidates.slice(0, 10).map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setSelectedSource(c)}
                    className="w-full text-left text-xs p-1.5 bg-white rounded hover:bg-red-100 transition-colors"
                  >
                    <span className="font-medium">{c.name || c.id}</span>
                    <span className="text-gray-500 ml-2">
                      η={c.eta.toFixed(2)}, V={c.v.toFixed(3)}
                    </span>
                  </button>
                ))}
                {candidates.length > 10 && (
                  <p className="text-xs text-red-500">+{candidates.length - 10} more</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Selected source detail */}
      {selectedSource && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <SourcePreview
            {...selectedSource}
            sourceId={selectedSource.id}
            isHover={false}
            onNavigate={handleNavigate}
            onClose={() => setSelectedSource(null)}
          />
        </div>
      )}
    </div>
  );
};

export default EtaVPlot;
