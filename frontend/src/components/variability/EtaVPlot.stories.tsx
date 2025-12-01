import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import EtaVPlot, { SourcePoint } from "./EtaVPlot";

/**
 * EtaVPlot displays variability metrics (η vs V) for astronomical sources.
 *
 * Features:
 * - Interactive scatter plot with zoom and pan
 * - Color coding by peak flux
 * - Source preview on hover
 * - Filtering controls
 * - Click to select sources
 */
const meta = {
  title: "Components/Visualization/EtaVPlot",
  component: EtaVPlot,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
  args: {
    onSourceSelect: fn(),
  },
} satisfies Meta<typeof EtaVPlot>;

export default meta;
type Story = StoryObj<typeof meta>;

// Generate sample data
const generateSampleSources = (count: number): SourcePoint[] => {
  return Array.from({ length: count }, (_, i) => ({
    id: `source-${i}`,
    name: `J${String(i).padStart(6, "0")}`,
    ra: Math.random() * 360,
    dec: (Math.random() - 0.5) * 180,
    eta: Math.random() * 10,
    v: Math.random() * 2,
    peakFlux: Math.random() * 1000,
    nMeasurements: Math.floor(Math.random() * 50) + 10,
  }));
};

/**
 * Default plot with sample sources
 */
export const Default: Story = {
  args: {
    sources: generateSampleSources(100),
    height: 600,
  },
};

/**
 * Plot with many sources
 */
export const LargeDataset: Story = {
  args: {
    sources: generateSampleSources(1000),
    height: 600,
  },
};

/**
 * Plot with few sources
 */
export const SmallDataset: Story = {
  args: {
    sources: generateSampleSources(10),
    height: 600,
  },
};

/**
 * Plot showing highly variable sources
 */
export const HighlyVariableSources: Story = {
  args: {
    sources: Array.from({ length: 50 }, (_, i) => ({
      id: `var-${i}`,
      name: `Variable-${i}`,
      ra: Math.random() * 360,
      dec: (Math.random() - 0.5) * 180,
      eta: 5 + Math.random() * 10, // High eta values
      v: 1 + Math.random() * 2, // High V values
      peakFlux: 100 + Math.random() * 900,
      nMeasurements: 30 + Math.floor(Math.random() * 20),
    })),
    height: 600,
  },
};

/**
 * Plot showing stable sources
 */
export const StableSources: Story = {
  args: {
    sources: Array.from({ length: 50 }, (_, i) => ({
      id: `stable-${i}`,
      name: `Stable-${i}`,
      ra: Math.random() * 360,
      dec: (Math.random() - 0.5) * 180,
      eta: Math.random() * 2, // Low eta values
      v: Math.random() * 0.5, // Low V values
      peakFlux: 10 + Math.random() * 100,
      nMeasurements: 20 + Math.floor(Math.random() * 30),
    })),
    height: 600,
  },
};

/**
 * Loading state
 */
export const Loading: Story = {
  args: {
    sources: [],
    isLoading: true,
    height: 600,
  },
};

/**
 * Empty state (no sources)
 */
export const Empty: Story = {
  args: {
    sources: [],
    isLoading: false,
    height: 600,
  },
};

/**
 * Custom height
 */
export const CustomHeight: Story = {
  args: {
    sources: generateSampleSources(100),
    height: 400,
  },
};

/**
 * With custom styling
 */
export const CustomStyling: Story = {
  args: {
    sources: generateSampleSources(100),
    height: 600,
    className: "border-4 border-blue-500 rounded-lg shadow-xl",
  },
};
