import React, { useEffect, useRef, useState, useCallback } from "react";
import * as echarts from "echarts";
import VariabilityControls, {
  VariabilityControlsValues,
} from "./VariabilityControls";
import SourcePreview from "./SourcePreview";

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

  // Filter sources by min data points
  const filteredSources = sources.filter(
    (s) => (s.nMeasurements ?? 10) >= controls.minDataPoints
  );

  // Identify candidates (above both thresholds)
  const { etaLine, vLine } = calculateThresholds();
  const candidates = filteredSources.filter(
    (s) => s.eta > etaLine && s.v > vLine
  );

  // Color mapping function
  const getPointColor = useCallback(
    (source: SourcePoint, isCandidate: boolean) => {
      if (isCandidate) return "#ff0000";
      if (controls.colorBy === "none") return "rgba(79, 195, 161, 0.6)";

      let value = 0;
      let max = 1;

      switch (controls.colorBy) {
        case "variability":
          value = source.eta * source.v;
          max = Math.max(...filteredSources.map((s) => s.eta * s.v));
          break;
        case "flux":
          value = source.peakFlux ?? 0;
          max = Math.max(...filteredSources.map((s) => s.peakFlux ?? 0));
          break;
        case "measurements":
          value = source.nMeasurements ?? 0;
          max = Math.max(...filteredSources.map((s) => s.nMeasurements ?? 0));
          break;
      }

      const ratio = Math.min(value / max, 1);
      // Gradient from green (#4fc3a1) to yellow (#f0c674)
      const r = Math.round(79 + ratio * (240 - 79));
      const g = Math.round(195 + ratio * (198 - 195));
      const b = Math.round(161 - ratio * (161 - 116));
      return `rgba(${r}, ${g}, ${b}, 0.7)`;
    },
    [controls.colorBy, filteredSources]
  );

  // Initialize chart
  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);

    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chartInstance.current?.dispose();
    };
  }, []);

  // Update chart
  useEffect(() => {
    if (!chartInstance.current || isLoading) return;

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

    const option: echarts.EChartsOption = {
      title: {
        text: "η-V Variability Plot",
        subtext: `${filteredSources.length} sources, ${candidates.length} candidates`,
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
        // η threshold line
        {
          type: "line",
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#ff6b6b", type: "dashed", width: 2 },
            data: [[{ xAxis: etaLine, yAxis: "min" }, { xAxis: etaLine, yAxis: "max" }]],
            label: {
              formatter: `η = ${etaLine.toFixed(2)}`,
              position: "end",
            },
          },
        },
        // V threshold line
        {
          type: "line",
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#ff6b6b", type: "dashed", width: 2 },
            data: [[{ xAxis: "min", yAxis: vLine }, { xAxis: "max", yAxis: vLine }]],
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

    chartInstance.current.setOption(option);

    // Event handlers
    chartInstance.current.on("mouseover", (params: any) => {
      if (params.componentType === "series" && params.data?.source) {
        const event = params.event?.event;
        setHoverSource(params.data.source);
        if (event) {
          setHoverPosition({ x: event.clientX, y: event.clientY });
        }
      }
    });

    chartInstance.current.on("mouseout", () => {
      setHoverSource(null);
    });

    chartInstance.current.on("click", (params: any) => {
      if (params.componentType === "series" && params.data?.source) {
        setSelectedSource(params.data.source);
        setHoverSource(null);
      }
    });
  }, [filteredSources, candidates, controls, isLoading, etaLine, vLine, getPointColor]);

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
                  <p className="text-xs text-red-500">
                    +{candidates.length - 10} more
                  </p>
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
