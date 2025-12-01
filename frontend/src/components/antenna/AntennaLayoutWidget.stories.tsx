import type { Meta, StoryObj } from "@storybook/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import AntennaLayoutWidget from "./AntennaLayoutWidget";
import type { AntennaLayoutResponse } from "./AntennaLayoutWidget";

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
 */
const meta = {
  title: "Components/Antenna/AntennaLayoutWidget",
  component: AntennaLayoutWidget,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
  decorators: [
    (Story) => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: Infinity },
        },
      });
      return (
        <QueryClientProvider client={queryClient}>
          <Story />
        </QueryClientProvider>
      );
    },
  ],
} satisfies Meta<typeof AntennaLayoutWidget>;

export default meta;
type Story = StoryObj<typeof meta>;

// Generate mock DSA-110 T-shaped antenna positions
function generateMockAntennas(
  count: number,
  flaggingScenario: "good" | "mixed" | "bad"
): AntennaLayoutResponse {
  const antennas = [];

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

// MSW handlers for different scenarios
const createHandler = (scenario: "good" | "mixed" | "bad", antennaCount = 63) =>
  http.get("*/ms/*/antennas", () => {
    return HttpResponse.json(generateMockAntennas(antennaCount, scenario));
  });

/**
 * Good observation with minimal flagging (<20% on all antennas)
 */
export const GoodObservation: Story = {
  args: {
    msPath: "/stage/dsa110-contimg/ms/good_observation.ms",
    height: 300,
    showLegend: true,
  },
  parameters: {
    msw: {
      handlers: [createHandler("good")],
    },
  },
};

/**
 * Mixed observation with some problematic antennas
 */
export const MixedObservation: Story = {
  args: {
    msPath: "/stage/dsa110-contimg/ms/mixed_observation.ms",
    height: 300,
    showLegend: true,
  },
  parameters: {
    msw: {
      handlers: [createHandler("mixed")],
    },
  },
};

/**
 * Bad observation with significant flagging issues
 */
export const BadObservation: Story = {
  args: {
    msPath: "/stage/dsa110-contimg/ms/bad_observation.ms",
    height: 300,
    showLegend: true,
  },
  parameters: {
    msw: {
      handlers: [createHandler("bad")],
    },
  },
};

/**
 * Full 110-antenna array
 */
export const FullArray: Story = {
  args: {
    msPath: "/stage/dsa110-contimg/ms/full_array.ms",
    height: 400,
    showLegend: true,
  },
  parameters: {
    msw: {
      handlers: [createHandler("mixed", 110)],
    },
  },
};

/**
 * Compact view without legend
 */
export const CompactNoLegend: Story = {
  args: {
    msPath: "/stage/dsa110-contimg/ms/compact.ms",
    height: 200,
    showLegend: false,
  },
  parameters: {
    msw: {
      handlers: [createHandler("good", 63)],
    },
  },
};

/**
 * With click handler for antenna selection
 */
export const WithClickHandler: Story = {
  args: {
    msPath: "/stage/dsa110-contimg/ms/interactive.ms",
    height: 300,
    showLegend: true,
    onAntennaClick: (antenna) => {
      console.log("Clicked antenna:", antenna);
      alert(
        `Selected ${antenna.name}\nFlagged: ${antenna.flagged_pct.toFixed(1)}%`
      );
    },
  },
  parameters: {
    msw: {
      handlers: [createHandler("mixed")],
    },
  },
};

/**
 * Loading state (no MSW handler to trigger loading)
 */
export const Loading: Story = {
  args: {
    msPath: "/stage/dsa110-contimg/ms/loading.ms",
    height: 300,
    showLegend: true,
  },
  parameters: {
    msw: {
      handlers: [
        http.get("*/ms/*/antennas", async () => {
          // Never resolve to show loading state
          await new Promise(() => {});
        }),
      ],
    },
  },
};

/**
 * Error state
 */
export const Error: Story = {
  args: {
    msPath: "/stage/dsa110-contimg/ms/error.ms",
    height: 300,
    showLegend: true,
  },
  parameters: {
    msw: {
      handlers: [
        http.get("*/ms/*/antennas", () => {
          return new HttpResponse(null, { status: 500 });
        }),
      ],
    },
  },
};
