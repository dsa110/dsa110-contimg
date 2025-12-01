import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import apiClient from "../../api/client";

/**
 * Information about a single antenna.
 */
export interface AntennaInfo {
  id: number;
  name: string;
  x_m: number;
  y_m: number;
  flagged_pct: number;
  baseline_count: number;
}

/**
 * Response from the antenna layout API endpoint.
 */
export interface AntennaLayoutResponse {
  antennas: AntennaInfo[];
  array_center_lon: number;
  array_center_lat: number;
  total_baselines: number;
}

interface AntennaLayoutWidgetProps {
  /** Path to the Measurement Set */
  msPath: string;
  /** Widget height in pixels */
  height?: number;
  /** Whether to show the legend */
  showLegend?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Callback when an antenna is clicked */
  onAntennaClick?: (antenna: AntennaInfo) => void;
}

/**
 * Query key for antenna positions.
 */
export const antennaQueryKey = (msPath: string) => ["ms", msPath, "antennas"] as const;

/**
 * Hook to fetch antenna positions for an MS.
 */
export function useAntennaPositions(msPath: string | undefined) {
  return useQuery({
    queryKey: antennaQueryKey(msPath ?? ""),
    queryFn: async () => {
      const encodedPath = encodeURIComponent(msPath ?? "");
      const response = await apiClient.get<AntennaLayoutResponse>(`/ms/${encodedPath}/antennas`);
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Get color for antenna based on flagging percentage.
 */
function getFlagColor(flaggedPct: number): string {
  if (flaggedPct > 50) return "#EF4444"; // red-500 - severe flagging
  if (flaggedPct > 20) return "#F59E0B"; // amber-500 - moderate flagging
  return "#22C55E"; // green-500 - good
}

/**
 * Get status label for flagging percentage.
 */
function getFlagStatus(flaggedPct: number): string {
  if (flaggedPct > 50) return "Severe";
  if (flaggedPct > 20) return "Moderate";
  return "Good";
}

/**
 * Antenna layout visualization component.
 *
 * Displays the DSA-110 T-shaped array layout with antennas color-coded
 * by their flagging percentage. Hover over antennas to see details.
 */
const AntennaLayoutWidget: React.FC<AntennaLayoutWidgetProps> = ({
  msPath,
  height = 300,
  showLegend = true,
  className = "",
  onAntennaClick,
}) => {
  const { data, isLoading, error } = useAntennaPositions(msPath);

  // Calculate SVG viewport bounds based on antenna positions
  const viewBox = useMemo(() => {
    if (!data?.antennas || data.antennas.length === 0) {
      return { minX: -100, minY: -100, width: 200, height: 200 };
    }

    const xs = data.antennas.map((a) => a.x_m);
    const ys = data.antennas.map((a) => a.y_m);

    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    // Add 10% padding
    const padX = Math.max((maxX - minX) * 0.1, 50);
    const padY = Math.max((maxY - minY) * 0.1, 50);

    return {
      minX: minX - padX,
      minY: minY - padY,
      width: maxX - minX + 2 * padX,
      height: maxY - minY + 2 * padY,
    };
  }, [data]);

  // Calculate aspect ratio for SVG
  const aspectRatio = viewBox.width / viewBox.height;
  const svgWidth = height * aspectRatio;

  // Antenna marker radius (in data coordinates)
  const markerRadius = Math.max(viewBox.width, viewBox.height) * 0.015;

  if (isLoading) {
    return (
      <div className={`antenna-layout-widget ${className}`} style={{ height }}>
        <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
          <div className="flex flex-col items-center">
            <svg
              className="animate-spin h-6 w-6 text-blue-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="mt-2 text-sm text-gray-500">Loading antenna positions...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`antenna-layout-widget ${className}`} style={{ height }}>
        <div className="flex items-center justify-center h-full bg-red-50 rounded-lg">
          <div className="text-center p-4">
            <svg
              className="mx-auto h-8 w-8 text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="mt-2 text-sm text-red-600">Failed to load antenna data</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data?.antennas || data.antennas.length === 0) {
    return (
      <div className={`antenna-layout-widget ${className}`} style={{ height }}>
        <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-500">No antenna data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`antenna-layout-widget ${className}`}>
      <div className="flex gap-4">
        {/* SVG Plot */}
        <div className="flex-1">
          <svg
            width={svgWidth}
            height={height}
            viewBox={`${viewBox.minX} ${viewBox.minY} ${viewBox.width} ${viewBox.height}`}
            className="bg-gray-900 rounded-lg"
            style={{ maxWidth: "100%" }}
          >
            {/* Grid lines */}
            <g className="grid-lines" stroke="#374151" strokeWidth={0.5} strokeDasharray="4,4">
              {/* Horizontal center line */}
              <line
                x1={viewBox.minX}
                y1={0}
                x2={viewBox.minX + viewBox.width}
                y2={0}
              />
              {/* Vertical center line */}
              <line
                x1={0}
                y1={viewBox.minY}
                x2={0}
                y2={viewBox.minY + viewBox.height}
              />
            </g>

            {/* Antenna markers */}
            {data.antennas.map((antenna) => (
              <g
                key={antenna.id}
                className="antenna-marker cursor-pointer"
                onClick={() => onAntennaClick?.(antenna)}
              >
                {/* Antenna circle */}
                <circle
                  cx={antenna.x_m}
                  cy={-antenna.y_m} // Flip Y for SVG coordinate system
                  r={markerRadius}
                  fill={getFlagColor(antenna.flagged_pct)}
                  stroke="#fff"
                  strokeWidth={markerRadius * 0.15}
                  className="transition-all duration-150 hover:r-[${markerRadius * 1.3}]"
                >
                  <title>
                    {`${antenna.name}\nFlagged: ${antenna.flagged_pct.toFixed(1)}%\nBaselines: ${antenna.baseline_count}`}
                  </title>
                </circle>
                {/* Antenna label (only show for sparse arrays or on hover) */}
                {data.antennas.length <= 30 && (
                  <text
                    x={antenna.x_m}
                    y={-antenna.y_m - markerRadius * 1.5}
                    textAnchor="middle"
                    fill="#9CA3AF"
                    fontSize={markerRadius * 0.8}
                    className="pointer-events-none"
                  >
                    {antenna.name.replace("DSA-", "")}
                  </text>
                )}
              </g>
            ))}

            {/* Axis labels */}
            <text
              x={viewBox.minX + viewBox.width / 2}
              y={viewBox.minY + viewBox.height - 10}
              textAnchor="middle"
              fill="#9CA3AF"
              fontSize={markerRadius * 1.2}
            >
              East (m)
            </text>
            <text
              x={viewBox.minX + 15}
              y={viewBox.minY + viewBox.height / 2}
              textAnchor="middle"
              fill="#9CA3AF"
              fontSize={markerRadius * 1.2}
              transform={`rotate(-90, ${viewBox.minX + 15}, ${viewBox.minY + viewBox.height / 2})`}
            >
              North (m)
            </text>
          </svg>
        </div>

        {/* Legend */}
        {showLegend && (
          <div className="flex-shrink-0 w-32">
            <h4 className="text-xs font-medium text-gray-700 mb-2">Flagging Status</h4>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-xs text-gray-600">Good (&lt;20%)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-xs text-gray-600">Moderate (20-50%)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500" />
                <span className="text-xs text-gray-600">Severe (&gt;50%)</span>
              </div>
            </div>

            {/* Summary stats */}
            <div className="mt-4 pt-3 border-t border-gray-200">
              <dl className="space-y-1">
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-500">Antennas</dt>
                  <dd className="text-xs font-medium text-gray-900">{data.antennas.length}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-500">Baselines</dt>
                  <dd className="text-xs font-medium text-gray-900">{data.total_baselines}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-500">Good</dt>
                  <dd className="text-xs font-medium text-green-600">
                    {data.antennas.filter((a) => a.flagged_pct < 20).length}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-500">Flagged</dt>
                  <dd className="text-xs font-medium text-red-600">
                    {data.antennas.filter((a) => a.flagged_pct >= 50).length}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AntennaLayoutWidget;
