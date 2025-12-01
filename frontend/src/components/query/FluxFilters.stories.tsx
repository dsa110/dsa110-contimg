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
  },
} satisfies Meta<typeof FluxFilters>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default flux filters with standard ranges
 */
export const Default: Story = {
  args: {
    minFlux: undefined,
    maxFlux: undefined,
    minIntFlux: undefined,
    maxIntFlux: undefined,
    minSnr: undefined,
    maxSnr: undefined,
  },
};

/**
 * Filters with preset values
 */
export const WithPresetValues: Story = {
  args: {
    minFlux: 10,
    maxFlux: 500,
    minIntFlux: 20,
    maxIntFlux: 1000,
    minSnr: 5,
    maxSnr: 50,
  },
};

/**
 * Filters for bright sources only
 */
export const BrightSourcesOnly: Story = {
  args: {
    minFlux: 100,
    maxFlux: undefined,
    minSnr: 10,
    maxSnr: undefined,
  },
};

/**
 * Filters for faint sources
 */
export const FaintSources: Story = {
  args: {
    minFlux: 1,
    maxFlux: 50,
    minSnr: 3,
    maxSnr: 10,
  },
};

/**
 * Custom styling example
 */
export const CustomStyling: Story = {
  args: {
    minFlux: 10,
    maxFlux: 500,
    className: "bg-slate-50 p-6 rounded-lg shadow-md",
  },
};
