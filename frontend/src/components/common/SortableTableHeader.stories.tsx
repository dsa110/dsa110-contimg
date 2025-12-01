import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import SortableTableHeader from "./SortableTableHeader";

/**
 * SortableTableHeader provides a clickable table header with sort indicators.
 *
 * Features:
 * - Click to cycle through sort states (none → asc → desc → none)
 * - Visual indicators for current sort direction
 * - Accessible labels
 */
const meta = {
  title: "Components/Common/SortableTableHeader",
  component: SortableTableHeader,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
  },
  args: {
    onSort: fn(),
  },
} satisfies Meta<typeof SortableTableHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default unsorted header
 */
export const Unsorted: Story = {
  args: {
    column: "name",
    label: "Name",
    currentSort: null,
  },
};

/**
 * Header sorted ascending
 */
export const SortedAscending: Story = {
  args: {
    column: "flux",
    label: "Peak Flux (mJy)",
    currentSort: { column: "flux", direction: "asc" },
  },
};

/**
 * Header sorted descending
 */
export const SortedDescending: Story = {
  args: {
    column: "snr",
    label: "SNR",
    currentSort: { column: "snr", direction: "desc" },
  },
};

/**
 * Header not currently sorted (but another column is)
 */
export const NotCurrentSort: Story = {
  args: {
    column: "ra",
    label: "RA (deg)",
    currentSort: { column: "dec", direction: "asc" },
  },
};

/**
 * Complete table example with multiple sortable headers
 */
export const CompleteTable: Story = {
  render: (args) => (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse">
        <thead className="bg-gray-50">
          <tr>
            <SortableTableHeader
              column="name"
              label="Source Name"
              currentSort={args.currentSort}
              onSort={args.onSort}
            />
            <SortableTableHeader
              column="ra"
              label="RA (deg)"
              currentSort={args.currentSort}
              onSort={args.onSort}
            />
            <SortableTableHeader
              column="dec"
              label="Dec (deg)"
              currentSort={args.currentSort}
              onSort={args.onSort}
            />
            <SortableTableHeader
              column="flux"
              label="Peak Flux (mJy)"
              currentSort={args.currentSort}
              onSort={args.onSort}
            />
            <SortableTableHeader
              column="snr"
              label="SNR"
              currentSort={args.currentSort}
              onSort={args.onSort}
            />
          </tr>
        </thead>
        <tbody>
          <tr className="border-t">
            <td className="px-4 py-2">J000001</td>
            <td className="px-4 py-2">180.5</td>
            <td className="px-4 py-2">45.2</td>
            <td className="px-4 py-2">125.3</td>
            <td className="px-4 py-2">8.5</td>
          </tr>
          <tr className="border-t bg-gray-50">
            <td className="px-4 py-2">J000002</td>
            <td className="px-4 py-2">182.1</td>
            <td className="px-4 py-2">46.8</td>
            <td className="px-4 py-2">98.7</td>
            <td className="px-4 py-2">12.3</td>
          </tr>
          <tr className="border-t">
            <td className="px-4 py-2">J000003</td>
            <td className="px-4 py-2">179.3</td>
            <td className="px-4 py-2">44.5</td>
            <td className="px-4 py-2">215.9</td>
            <td className="px-4 py-2">15.7</td>
          </tr>
        </tbody>
      </table>
    </div>
  ),
  args: {
    currentSort: { column: "flux", direction: "desc" },
  },
};
