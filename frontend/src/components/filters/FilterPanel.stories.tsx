import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import FilterPanel, { FilterConfig, FilterValues } from "./FilterPanel";

/**
 * FilterPanel provides a collapsible panel with various filter types including
 * range sliders, selects, checkboxes, and text inputs.
 *
 * Used throughout the app for filtering images, sources, and jobs.
 */
const meta = {
  title: "Components/Filters/FilterPanel",
  component: FilterPanel,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
} satisfies Meta<typeof FilterPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

const exampleFilters: FilterConfig[] = [
  {
    id: "flux",
    label: "Peak Flux",
    type: "range",
    min: 0,
    max: 1000,
    step: 10,
    unit: "mJy",
    defaultValue: [0, 1000],
  },
  {
    id: "snr",
    label: "Signal-to-Noise Ratio",
    type: "range",
    min: 0,
    max: 100,
    step: 1,
    defaultValue: [5, 100],
  },
  {
    id: "quality",
    label: "Quality Rating",
    type: "select",
    options: [
      { value: "all", label: "All" },
      { value: "good", label: "Good" },
      { value: "fair", label: "Fair" },
      { value: "poor", label: "Poor" },
    ],
    defaultValue: "all",
  },
  {
    id: "showFlags",
    label: "Show Flagged Sources",
    type: "checkbox",
    defaultValue: false,
  },
];

/**
 * Interactive filter panel with various filter types
 */
export const Default: Story = {
  args: {},
  render: () => {
    const [values, setValues] = useState<FilterValues>({
      flux: [0, 1000],
      snr: [5, 100],
      quality: "all",
      showFlags: false,
    });

    return (
      <div className="max-w-md">
        <FilterPanel
          filters={exampleFilters}
          values={values}
          onChange={setValues}
          title="Source Filters"
        />
        <div className="mt-4 p-4 bg-gray-100 rounded">
          <h3 className="font-bold mb-2">Current Values:</h3>
          <pre className="text-sm">{JSON.stringify(values, null, 2)}</pre>
        </div>
      </div>
    );
  },
};

/**
 * Filter panel in collapsed state
 */
export const Collapsed: Story = {
  args: {},
  render: () => {
    const [values, setValues] = useState<FilterValues>({
      flux: [0, 1000],
      snr: [5, 100],
    });

    return (
      <div className="max-w-md">
        <FilterPanel
          filters={exampleFilters}
          values={values}
          onChange={setValues}
          title="Source Filters"
          defaultCollapsed={true}
        />
      </div>
    );
  },
};

/**
 * Filter panel with range sliders only
 */
export const RangeSlidersOnly: Story = {
  args: {},
  render: () => {
    const [values, setValues] = useState<FilterValues>({
      ra: [0, 360],
      dec: [-90, 90],
      radius: [0, 5],
    });

    const rangeFilters: FilterConfig[] = [
      {
        id: "ra",
        label: "Right Ascension",
        type: "range",
        min: 0,
        max: 360,
        step: 1,
        unit: "deg",
        defaultValue: [0, 360],
      },
      {
        id: "dec",
        label: "Declination",
        type: "range",
        min: -90,
        max: 90,
        step: 1,
        unit: "deg",
        defaultValue: [-90, 90],
      },
      {
        id: "radius",
        label: "Search Radius",
        type: "range",
        min: 0,
        max: 5,
        step: 0.1,
        unit: "deg",
        defaultValue: [0, 5],
      },
    ];

    return (
      <div className="max-w-md">
        <FilterPanel
          filters={rangeFilters}
          values={values}
          onChange={setValues}
          title="Coordinate Filters"
        />
      </div>
    );
  },
};

/**
 * Non-collapsible filter panel
 */
export const NonCollapsible: Story = {
  args: {},
  render: () => {
    const [values, setValues] = useState<FilterValues>({
      flux: [0, 1000],
      quality: "good",
    });

    return (
      <div className="max-w-md">
        <FilterPanel
          filters={exampleFilters.slice(0, 2)}
          values={values}
          onChange={setValues}
          title="Quick Filters"
          collapsible={false}
        />
      </div>
    );
  },
};

/**
 * Empty filter panel (no filters configured)
 */
export const Empty: Story = {
  args: {},
  render: () => {
    const [values, setValues] = useState<FilterValues>({});

    return (
      <div className="max-w-md">
        <FilterPanel
          filters={[]}
          values={values}
          onChange={setValues}
          title="No Filters Available"
        />
      </div>
    );
  },
};
