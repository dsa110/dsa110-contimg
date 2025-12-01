import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import RegionToolbar from "./RegionToolbar";

/**
 * RegionToolbar provides tools for creating and managing DS9/CRTF regions on FITS images.
 *
 * Features:
 * - Shape tools: circle, box, ellipse, polygon, point
 * - Export formats: DS9, CRTF, JSON
 * - Clear all regions
 * - Download export file
 * - Save callback for backend integration
 *
 * This component works with JS9's region system to enable interactive
 * region creation on astronomical images. Regions can be used for:
 * - Source identification
 * - Exclusion zones
 * - Clean masks
 * - Calibrator field marking
 *
 * Note: Requires JS9 to be loaded. In Storybook, region operations
 * are mocked since JS9 is not available.
 */
const meta = {
  title: "Components/FITS/RegionToolbar",
  component: RegionToolbar,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component: `
RegionToolbar integrates with JS9's region tools to enable drawing
and exporting regions in multiple formats:

- **DS9**: Standard SAOImage DS9 region format (.reg)
- **CRTF**: CASA Region Text Format for use with CASA tasks
- **JSON**: Machine-readable format for programmatic use

The toolbar provides buttons for each shape type, a clear button,
format selector, and export/save buttons.
        `,
      },
    },
  },
  argTypes: {
    displayId: {
      description: "JS9 display ID to operate on",
      control: "text",
    },
    compact: {
      description: "Use compact button layout",
      control: "boolean",
    },
  },
  args: {
    displayId: "JS9",
    onSave: fn(),
    onChange: fn(),
  },
} satisfies Meta<typeof RegionToolbar>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default toolbar with all controls visible
 */
export const Default: Story = {
  args: {
    displayId: "JS9",
    compact: false,
  },
};

/**
 * Compact mode for space-constrained layouts
 */
export const Compact: Story = {
  args: {
    displayId: "JS9",
    compact: true,
  },
};

/**
 * With save callback for backend integration
 */
export const WithSaveCallback: Story = {
  args: {
    displayId: "JS9",
    compact: false,
    onSave: (regions, format) => {
      console.log(`Saving ${regions.length} regions as ${format}`);
      alert(`Would save ${regions.length} regions in ${format} format`);
    },
  },
  parameters: {
    docs: {
      description: {
        story:
          "When a save callback is provided, a Save button appears alongside Export.",
      },
    },
  },
};

/**
 * Without save callback (export-only mode)
 */
export const ExportOnly: Story = {
  args: {
    displayId: "JS9",
    compact: false,
    onSave: undefined,
  },
  parameters: {
    docs: {
      description: {
        story: "Without an onSave callback, only the Export button is shown.",
      },
    },
  },
};

/**
 * Custom styling
 */
export const CustomStyling: Story = {
  args: {
    displayId: "JS9",
    compact: false,
    className: "border-2 border-blue-500 shadow-lg",
  },
};

/**
 * In a card container (typical usage)
 */
export const InCardContainer: Story = {
  render: (args) => (
    <div className="bg-white rounded-lg shadow-md p-4 max-w-2xl">
      <h3 className="text-lg font-semibold mb-3">Region Tools</h3>
      <p className="text-sm text-gray-600 mb-4">
        Draw regions on the image below. Use the toolbar to select shapes and
        export in your preferred format.
      </p>
      <RegionToolbar {...args} />
      <div className="mt-4 bg-gray-800 rounded h-64 flex items-center justify-center text-gray-400">
        [JS9 Viewer would render here]
      </div>
    </div>
  ),
  args: {
    displayId: "JS9",
    compact: false,
  },
};

/**
 * Multiple toolbars for different displays
 */
export const MultipleDisplays: Story = {
  render: () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-4">
        <h4 className="font-medium mb-2">Display 1: Science Target</h4>
        <RegionToolbar displayId="JS9-1" />
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <h4 className="font-medium mb-2">Display 2: Calibrator</h4>
        <RegionToolbar displayId="JS9-2" />
      </div>
    </div>
  ),
};
