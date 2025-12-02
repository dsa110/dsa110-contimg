import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import FluxFilters from "./FluxFilters";

/**
 * FluxFilters provides range controls for filtering sources by flux measurements.
 *
 * Includes:
 * - Peak flux range
 * - Integrated flux range
 * - SNR (Signal-to-Noise Ratio) range
 */
const meta = {
  title: "Components/Query/FluxFilters",
  component: FluxFilters,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
  args: {
    onChange: fn(),
    values: {},
  },
} satisfies Meta<typeof FluxFilters>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default flux filters with standard ranges
 */
export const Default: Story = {
  args: {
    values: {},
  },
};

/**
 * Filters with preset values
 */
export const WithPresetValues: Story = {
  args: {
    values: {
      minFlux: { min: 10, max: 500, type: "peak" },
      maxFlux: { min: 20, max: 1000, type: "peak" },
    },
  },
};

/**
 * Filters for bright sources only
 */
export const BrightSourcesOnly: Story = {
  args: {
    values: {
      minFlux: { min: 100, type: "peak" },
    },
  },
};

/**
 * Filters for faint sources
 */
export const FaintSources: Story = {
  args: {
    values: {
      minFlux: { min: 1, max: 50, type: "peak" },
    },
  },
};

/**
 * Custom styling example
 */
export const CustomStyling: Story = {
  args: {
    values: {
      minFlux: { min: 10, max: 500, type: "peak" },
    },
    className: "bg-slate-50 p-6 rounded-lg shadow-md",
  },
};
