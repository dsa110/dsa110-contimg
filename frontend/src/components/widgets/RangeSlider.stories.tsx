import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import RangeSlider from "./RangeSlider";

/**
 * RangeSlider provides a dual-handle slider for selecting a numeric range.
 *
 * Features:
 * - Dual handles for min and max values
 * - Optional histogram background
 * - Customizable step size
 * - Unit display
 * - Real-time value updates
 */
const meta = {
  title: "Components/Widgets/RangeSlider",
  component: RangeSlider,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
} satisfies Meta<typeof RangeSlider>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Interactive range slider with state
 */
export const Default: Story = {
  render: () => {
    const [range, setRange] = useState<[number, number]>([20, 80]);

    return (
      <div className="max-w-md">
        <RangeSlider
          label="Value Range"
          min={0}
          max={100}
          step={1}
          value={range}
          onChange={setRange}
        />
        <div className="mt-4 p-4 bg-gray-100 rounded">
          <strong>Selected Range:</strong> {range[0]} - {range[1]}
        </div>
      </div>
    );
  },
};

/**
 * Slider with unit label
 */
export const WithUnit: Story = {
  render: () => {
    const [flux, setFlux] = useState<[number, number]>([10, 500]);

    return (
      <div className="max-w-md">
        <RangeSlider
          label="Peak Flux"
          min={0}
          max={1000}
          step={10}
          value={flux}
          onChange={setFlux}
          unit="mJy"
        />
      </div>
    );
  },
};

/**
 * Slider with histogram background
 */
export const WithHistogram: Story = {
  render: () => {
    const [snr, setSnr] = useState<[number, number]>([5, 50]);
    // Generate sample histogram data
    const histogram = Array.from({ length: 20 }, (_, i) => Math.exp(-i / 5) * 100);

    return (
      <div className="max-w-md">
        <RangeSlider
          label="Signal-to-Noise Ratio"
          min={0}
          max={100}
          step={1}
          value={snr}
          onChange={setSnr}
          histogram={histogram}
        />
      </div>
    );
  },
};

/**
 * Slider with decimal step
 */
export const DecimalStep: Story = {
  render: () => {
    const [fov, setFov] = useState<[number, number]>([0.1, 2.5]);

    return (
      <div className="max-w-md">
        <RangeSlider
          label="Field of View"
          min={0}
          max={5}
          step={0.1}
          value={fov}
          onChange={setFov}
          unit="degrees"
        />
      </div>
    );
  },
};

/**
 * Narrow range slider
 */
export const NarrowRange: Story = {
  render: () => {
    const [value, setValue] = useState<[number, number]>([3, 7]);

    return (
      <div className="max-w-md">
        <RangeSlider
          label="Quality Score"
          min={0}
          max={10}
          step={1}
          value={value}
          onChange={setValue}
        />
      </div>
    );
  },
};

/**
 * Large range slider
 */
export const LargeRange: Story = {
  render: () => {
    const [value, setValue] = useState<[number, number]>([1000, 5000]);

    return (
      <div className="max-w-md">
        <RangeSlider
          label="Frequency"
          min={0}
          max={10000}
          step={100}
          value={value}
          onChange={setValue}
          unit="MHz"
        />
      </div>
    );
  },
};

/**
 * Multiple sliders in a form
 */
export const MultipleSliders: Story = {
  render: () => {
    const [ra, setRa] = useState<[number, number]>([0, 360]);
    const [dec, setDec] = useState<[number, number]>([-90, 90]);
    const [flux, setFlux] = useState<[number, number]>([10, 500]);

    return (
      <div className="max-w-md space-y-6">
        <RangeSlider
          label="Right Ascension"
          min={0}
          max={360}
          step={1}
          value={ra}
          onChange={setRa}
          unit="deg"
        />
        <RangeSlider
          label="Declination"
          min={-90}
          max={90}
          step={1}
          value={dec}
          onChange={setDec}
          unit="deg"
        />
        <RangeSlider
          label="Peak Flux"
          min={0}
          max={1000}
          step={10}
          value={flux}
          onChange={setFlux}
          unit="mJy"
        />

        <div className="mt-4 p-4 bg-blue-50 rounded">
          <h3 className="font-bold mb-2">Current Filter:</h3>
          <p className="text-sm">
            RA: {ra[0]}° - {ra[1]}°
          </p>
          <p className="text-sm">
            Dec: {dec[0]}° - {dec[1]}°
          </p>
          <p className="text-sm">
            Flux: {flux[0]} - {flux[1]} mJy
          </p>
        </div>
      </div>
    );
  },
};

/**
 * Disabled slider
 */
export const Disabled: Story = {
  args: {
    label: "Disabled Range",
    min: 0,
    max: 100,
    step: 1,
    value: [20, 80],
    onChange: () => {},
    disabled: true,
  },
};
