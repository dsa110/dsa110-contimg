import type { Meta, StoryObj } from "@storybook/react";
import React from "react";
import type { AntennaInfo, AntennaLayoutResponse } from "./AntennaLayoutWidget";

/**
 * AntennaLayoutWidget displays the DSA-110 T-shaped antenna array layout.
 *
 * Features:
 * - Native SVG rendering (no Python/casangi dependency)
 * - Antennas color-coded by flagging percentage
 * - Interactive tooltips with antenna details
 * - Legend with flagging status thresholds
 * - Summary statistics panel
 *
 * This component fetches antenna positions and flagging stats from the
 * `/ms/{path}/antennas` API endpoint.
 *
 * For Storybook, we use a mock wrapper that renders the visualization
 * directly without API calls.
 */

// Generate mock DSA-110 T-shaped antenna positions
function generateMockAntennas(
  count: number,
  flaggingScenario: "good" | "mixed" | "bad"
): AntennaLayoutResponse {
  const antennas: AntennaInfo[] = [];

  // DSA-110 T-shape: East-West arm (~1.2km) and North-South arm (~0.3km)
  for (let i = 0; i < count; i++) {
    let x: number, y: number;

    if (i < count * 0.7) {
      // East-West arm (70% of antennas)
      x = (i / (count * 0.7) - 0.5) * 1200; // -600m to +600m
      y = (Math.random() - 0.5) * 20; // Small offset
    } else {
      // North-South arm (30% of antennas)
      x = (Math.random() - 0.5) * 20; // Small offset
      y = ((i - count * 0.7) / (count * 0.3) - 0.5) * 300; // -150m to +150m
    }

    // Flagging percentage based on scenario
    let flagged_pct: number;
    switch (flaggingScenario) {
      case "good":
        flagged_pct = Math.random() * 15; // 0-15%
        break;
      case "mixed":
        flagged_pct = Math.random() * 60; // 0-60%
        break;
      case "bad":
        flagged_pct = 30 + Math.random() * 70; // 30-100%
        break;
    }

    antennas.push({
      id: i,
      name: `DSA-${(i + 1).toString().padStart(3, "0")}`,
      x_m: x,
      y_m: y,
      flagged_pct,
      baseline_count: Math.floor(count - 1 - Math.random() * 5),
    });
  }

  return {
    antennas,
    array_center_lon: -118.2817,
    array_center_lat: 37.2339,
    total_baselines: (count * (count - 1)) / 2,
  };
}

/**
 * Get color for antenna based on flagging percentage.
 */
function getFlagColor(flaggedPct: number): string {
  if (flaggedPct > 50) return "#EF4444"; // red-500 - severe flagging
  if (flaggedPct > 20) return "#F59E0B"; // amber-500 - moderate flagging
  return "#22C55E"; // green-500 - good
}

interface MockAntennaLayoutProps {
  data: AntennaLayoutResponse;
  height?: number;
  showLegend?: boolean;
  onAntennaClick?: (antenna: AntennaInfo) => void;
}

/**
 * Mock component that renders the antenna layout directly without API.
 */
const MockAntennaLayout: React.FC<MockAntennaLayoutProps> = ({
  data,
  height = 300,
  showLegend = true,
  onAntennaClick,
}) => {
  const { antennas, total_baselines } = data;

  // Calculate viewport bounds
  const xs = antennas.map((a) => a.x_m);
  const ys = antennas.map((a) => a.y_m);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const padX = Math.max((maxX - minX) * 0.1, 50);
  const padY = Math.max((maxY - minY) * 0.1, 50);

  const viewBox = {
    minX: minX - padX,
    minY: minY - padY,
    width: maxX - minX + 2 * padX,
    height: maxY - minY + 2 * padY,
  };

  const aspectRatio = viewBox.width / viewBox.height;
  const svgWidth = height * aspectRatio;
  const markerRadius = Math.max(viewBox.width, viewBox.height) * 0.015;

  return (
    <div className="antenna-layout-widget">
      <div className="flex gap-4">
        <div className="flex-1">
          <svg
            width={svgWidth}
            height={height}
            viewBox={`${viewBox.minX} ${viewBox.minY} ${viewBox.width} ${viewBox.height}`}
            className="bg-gray-900 rounded-lg"
            style={{ maxWidth: "100%" }}
          >
            {/* Grid lines */}
            <g stroke="#374151" strokeWidth={0.5} strokeDasharray="4,4">
              <line
                x1={viewBox.minX}
                y1={0}
                x2={viewBox.minX + viewBox.width}
                y2={0}
              />
              <line
                x1={0}
                y1={viewBox.minY}
                x2={0}
                y2={viewBox.minY + viewBox.height}
              />
            </g>

            {/* Antenna markers */}
            {antennas.map((antenna) => (
              <g
                key={antenna.id}
                className="cursor-pointer"
                onClick={() => onAntennaClick?.(antenna)}
              >
                <circle
                  cx={antenna.x_m}
                  cy={-antenna.y_m}
                  r={markerRadius}
                  fill={getFlagColor(antenna.flagged_pct)}
                  stroke="#fff"
                  strokeWidth={markerRadius * 0.15}
                >
                  <title>
                    {`${antenna.name}\nFlagged: ${antenna.flagged_pct.toFixed(
                      1
                    )}%\nBaselines: ${antenna.baseline_count}`}
                  </title>
                </circle>
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
          </svg>
        </div>

        {showLegend && (
          <div className="flex-shrink-0 w-32">
            <h4 className="text-xs font-medium text-gray-700 mb-2">
              Flagging Status
            </h4>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-xs text-gray-600">&lt;20%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="text-xs text-gray-600">20-50%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500" />
                <span className="text-xs text-gray-600">&gt;50%</span>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-200">
              <dl className="space-y-1">
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-500">Antennas</dt>
                  <dd className="text-xs font-medium text-gray-900">
                    {antennas.length}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-xs text-gray-500">Baselines</dt>
                  <dd className="text-xs font-medium text-gray-900">
                    {total_baselines}
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

const meta = {
  title: "Components/Antenna/AntennaLayoutWidget",
  component: MockAntennaLayout,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
} satisfies Meta<typeof MockAntennaLayout>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Good observation with minimal flagging (<20% on all antennas)
 */
export const GoodObservation: Story = {
  args: {
    data: generateMockAntennas(63, "good"),
    height: 300,
    showLegend: true,
  },
};

/**
 * Mixed observation with some problematic antennas
 */
export const MixedObservation: Story = {
  args: {
    data: generateMockAntennas(63, "mixed"),
    height: 300,
    showLegend: true,
  },
};

/**
 * Bad observation with significant flagging issues
 */
export const BadObservation: Story = {
  args: {
    data: generateMockAntennas(63, "bad"),
    height: 300,
    showLegend: true,
  },
};

/**
 * Full 110-antenna array
 */
export const FullArray: Story = {
  args: {
    data: generateMockAntennas(110, "mixed"),
    height: 400,
    showLegend: true,
  },
};

/**
 * Compact view without legend
 */
export const CompactNoLegend: Story = {
  args: {
    data: generateMockAntennas(63, "good"),
    height: 200,
    showLegend: false,
  },
};

/**
 * With click handler for antenna selection
 */
export const WithClickHandler: Story = {
  args: {
    data: generateMockAntennas(63, "mixed"),
    height: 300,
    showLegend: true,
    onAntennaClick: (antenna) => {
      alert(
        `Selected ${antenna.name}\nFlagged: ${antenna.flagged_pct.toFixed(1)}%`
      );
    },
  },
};

// =============================================================================
// Edge Cases & Realistic Scenarios
// =============================================================================

/**
 * Sparse array with only 10 antennas (test case)
 */
export const SparseArray: Story = {
  args: {
    data: generateMockAntennas(10, "good"),
    height: 250,
    showLegend: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Minimal array configuration for edge case testing.",
      },
    },
  },
};

/**
 * Single problematic antenna highlighted
 */
export const SingleFlaggedAntenna: Story = {
  args: {
    data: (() => {
      const data = generateMockAntennas(63, "good");
      // Make one antenna severely flagged
      data.antennas[15].flagged_pct = 85;
      data.antennas[15].name = "DSA-016 (FLAGGED)";
      return data;
    })(),
    height: 300,
    showLegend: true,
  },
  parameters: {
    docs: {
      description: {
        story:
          "Scenario where most antennas are good but one has severe flagging.",
      },
    },
  },
};

/**
 * RFI contamination pattern - cluster of bad antennas
 */
export const RFIContamination: Story = {
  args: {
    data: (() => {
      const data = generateMockAntennas(63, "good");
      // Simulate RFI affecting a cluster of antennas on the E-W arm
      for (let i = 20; i < 30; i++) {
        data.antennas[i].flagged_pct = 40 + Math.random() * 40;
      }
      return data;
    })(),
    height: 300,
    showLegend: true,
  },
  parameters: {
    docs: {
      description: {
        story:
          "RFI contamination affecting a cluster of adjacent antennas on the East-West arm.",
      },
    },
  },
};

/**
 * Maintenance scenario - multiple antennas offline
 */
export const MaintenanceMode: Story = {
  args: {
    data: (() => {
      const data = generateMockAntennas(63, "good");
      // 5 antennas fully flagged (offline for maintenance)
      [5, 22, 38, 45, 60].forEach((idx) => {
        if (data.antennas[idx]) {
          data.antennas[idx].flagged_pct = 100;
          data.antennas[idx].baseline_count = 0;
        }
      });
      return data;
    })(),
    height: 300,
    showLegend: true,
  },
  parameters: {
    docs: {
      description: {
        story: "Scenario with 5 antennas offline for scheduled maintenance.",
      },
    },
  },
};

/**
 * Mobile/responsive view
 */
export const ResponsiveSmall: Story = {
  args: {
    data: generateMockAntennas(63, "mixed"),
    height: 180,
    showLegend: false,
  },
  parameters: {
    viewport: { defaultViewport: "mobile1" },
    docs: {
      description: {
        story: "Compact view optimized for mobile devices.",
      },
    },
  },
};

/**
 * Large display for control room
 */
export const ControlRoomDisplay: Story = {
  args: {
    data: generateMockAntennas(110, "mixed"),
    height: 600,
    showLegend: true,
  },
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        story: "Large format display for observatory control room.",
      },
    },
  },
};

/**
 * In card container (typical usage in dashboard)
 */
export const InDashboardCard: Story = {
  render: (args) => (
    <div className="bg-white rounded-lg shadow-md p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold">Array Status</h3>
        <span className="text-xs text-gray-500">Last updated: 2 min ago</span>
      </div>
      <MockAntennaLayout {...args} />
      <div className="mt-3 pt-3 border-t border-gray-200 flex justify-between text-sm">
        <span className="text-gray-600">Observation: 2025-12-01T14:30:00</span>
        <a href="#" className="text-blue-600 hover:underline">
          View Details →
        </a>
      </div>
    </div>
  ),
  args: {
    data: generateMockAntennas(63, "mixed"),
    height: 280,
    showLegend: true,
  },
};
