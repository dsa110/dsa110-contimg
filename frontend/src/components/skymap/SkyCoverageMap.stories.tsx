import type { Meta, StoryObj } from "@storybook/react";
import SkyCoverageMap, { Pointing, SURVEY_FOOTPRINTS } from "./SkyCoverageMap";

/**
 * SkyCoverageMap displays astronomical observations on a sky projection map.
 *
 * Features:
 * - Multiple projections (Aitoff, Mollweide, Hammer, Mercator)
 * - Galactic plane and ecliptic overlays
 * - Constellation names, lines, and boundaries
 * - Survey footprint overlays (NVSS, FIRST, VLASS, RACS)
 * - Color coding by status or epoch
 * - Interactive zoom and pan
 */
const meta = {
  title: "Components/Visualization/SkyCoverageMap",
  component: SkyCoverageMap,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
  },
} satisfies Meta<typeof SkyCoverageMap>;

export default meta;
type Story = StoryObj<typeof meta>;

// Generate sample pointings across the sky
const generatePointings = (count: number): Pointing[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: `pointing-${i}`,
    ra: (i * 360) / count,
    dec: Math.sin((i * Math.PI * 2) / count) * 60,
    radius: 1.5,
    label: `P${i}`,
    status: ["completed", "scheduled", "failed"][i % 3] as Pointing["status"],
    epoch: new Date(2024, 0, 1 + i).toISOString(),
  }));
};

/**
 * Default sky coverage map with sample pointings
 */
export const Default: Story = {
  args: {
    pointings: generatePointings(50),
    projection: "mollweide",
    showGalacticPlane: true,
    showEcliptic: false,
    showConstellations: true,
    showSurveyFootprints: true,
  },
};

/**
 * Map with survey footprints (NVSS, FIRST, VLASS, RACS)
 * Shows the coverage of reference catalogs used in the DSA-110 pipeline.
 */
export const WithSurveyFootprints: Story = {
  args: {
    pointings: generatePointings(30),
    projection: "mollweide",
    showGalacticPlane: true,
    showSurveyFootprints: true,
    surveyFootprints: SURVEY_FOOTPRINTS,
  },
};

/**
 * Map with Global Sky Model (GSM) radio background showing the radio sky at 1400 MHz.
 * The bright band across the center is the galactic plane.
 * Similar to VAST/ASKAP sky coverage plots.
 */
export const WithRadioBackground: Story = {
  args: {
    pointings: generatePointings(30),
    projection: "mollweide",
    showGalacticPlane: true,
    showSurveyFootprints: true,
    showRadioBackground: true,
  },
};

/**
 * Map without radio background (plain dark background)
 */
export const WithoutRadioBackground: Story = {
  args: {
    pointings: generatePointings(30),
    projection: "mollweide",
    showGalacticPlane: true,
    showSurveyFootprints: true,
    showRadioBackground: false,
  },
};

/**
 * Map without survey footprints
 */
export const WithoutSurveyFootprints: Story = {
  args: {
    pointings: generatePointings(50),
    projection: "mollweide",
    showGalacticPlane: true,
    showSurveyFootprints: false,
  },
};

/**
 * Map with Aitoff projection
 */
export const AitoffProjection: Story = {
  args: {
    pointings: generatePointings(50),
    projection: "aitoff",
    showGalacticPlane: true,
    showSurveyFootprints: true,
  },
};

/**
 * Map with Mollweide projection
 */
export const MollweideProjection: Story = {
  args: {
    pointings: generatePointings(50),
    projection: "mollweide",
    showGalacticPlane: true,
  },
};

/**
 * Map with Hammer projection
 */
export const HammerProjection: Story = {
  args: {
    pointings: generatePointings(50),
    projection: "hammer",
    showGalacticPlane: true,
  },
};

/**
 * Map showing galactic plane and ecliptic
 */
export const WithGalacticAndEcliptic: Story = {
  args: {
    pointings: generatePointings(30),
    projection: "aitoff",
    showGalacticPlane: true,
    showEcliptic: true,
    showConstellations: false,
  },
};

/**
 * Map with constellation boundaries
 */
export const WithConstellationBoundaries: Story = {
  args: {
    pointings: generatePointings(20),
    projection: "aitoff",
    showConstellations: {
      names: true,
      lines: true,
      bounds: true,
    },
  },
};

/**
 * Map colored by observation status
 */
export const ColoredByStatus: Story = {
  args: {
    pointings: generatePointings(40),
    projection: "aitoff",
    colorScheme: "status",
    showGalacticPlane: true,
  },
};

/**
 * Map colored by epoch
 */
export const ColoredByEpoch: Story = {
  args: {
    pointings: generatePointings(40),
    projection: "aitoff",
    colorScheme: "epoch",
    showGalacticPlane: true,
  },
};

/**
 * Map with uniform coloring
 */
export const UniformColor: Story = {
  args: {
    pointings: generatePointings(40),
    projection: "aitoff",
    colorScheme: "uniform",
    showGalacticPlane: true,
  },
};

/**
 * Dense coverage map
 */
export const DenseCoverage: Story = {
  args: {
    pointings: generatePointings(200),
    projection: "aitoff",
    showGalacticPlane: true,
    showConstellations: false,
  },
};

/**
 * Sparse coverage map
 */
export const SparseCoverage: Story = {
  args: {
    pointings: generatePointings(10),
    projection: "aitoff",
    showGalacticPlane: true,
    showConstellations: true,
  },
};

/**
 * Empty map (no pointings)
 */
export const Empty: Story = {
  args: {
    pointings: [],
    projection: "aitoff",
    showGalacticPlane: true,
    showConstellations: true,
  },
};

/**
 * Custom dimensions
 */
export const CustomSize: Story = {
  args: {
    pointings: generatePointings(50),
    projection: "aitoff",
    width: 1200,
    height: 600,
    showGalacticPlane: true,
  },
};
