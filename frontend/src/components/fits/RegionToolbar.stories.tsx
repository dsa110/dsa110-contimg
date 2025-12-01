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
  },
  parameters: {
    docs: {
      description: {
        story:
          "When a save callback is provided, a Save button appears alongside Export. Check the Actions panel to see events.",
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

// =============================================================================
// Edge Cases & Realistic Scenarios
// =============================================================================

/**
 * Disabled state (e.g., no image loaded)
 */
export const DisabledNoImage: Story = {
  render: () => (
    <div className="bg-white rounded-lg shadow-md p-4 max-w-2xl">
      <h3 className="text-lg font-semibold mb-3">Region Tools</h3>
      <div className="opacity-50 pointer-events-none">
        <RegionToolbar displayId="JS9" />
      </div>
      <p className="mt-2 text-sm text-amber-600 bg-amber-50 p-2 rounded">
        ⚠️ Load a FITS image to enable region tools
      </p>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Disabled state when no FITS image is loaded in the viewer.",
      },
    },
  },
};

/**
 * With pre-existing regions (editing scenario)
 */
export const WithExistingRegions: Story = {
  render: (args) => (
    <div className="bg-white rounded-lg shadow-md p-4 max-w-2xl">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold">Edit Regions</h3>
        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
          3 regions loaded
        </span>
      </div>
      <RegionToolbar {...args} />
      <div className="mt-4 bg-gray-800 rounded h-64 relative overflow-hidden">
        {/* Mock region overlays */}
        <div className="absolute top-1/4 left-1/3 w-16 h-16 border-2 border-green-500 rounded-full opacity-70" />
        <div className="absolute top-1/2 right-1/4 w-20 h-12 border-2 border-blue-500 opacity-70" />
        <div className="absolute bottom-1/4 left-1/2 w-4 h-4 bg-red-500 rounded-full" />
        <div className="absolute inset-0 flex items-center justify-center text-gray-500">
          [JS9 Viewer with regions]
        </div>
      </div>
      <div className="mt-3 text-sm text-gray-600">
        <strong>Loaded regions:</strong> circle (source), box (exclusion), point
        (marker)
      </div>
    </div>
  ),
  args: {
    displayId: "JS9",
    compact: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Scenario with pre-existing regions loaded from a file.",
      },
    },
  },
};

/**
 * Source identification workflow
 */
export const SourceIdentificationWorkflow: Story = {
  render: (args) => (
    <div className="max-w-4xl space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">
          📍 Source Identification
        </h3>
        <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
          <li>
            Select the <strong>Circle</strong> tool to mark point sources
          </li>
          <li>
            Use <strong>Ellipse</strong> for extended sources
          </li>
          <li>
            Export as <strong>DS9</strong> for use in other tools
          </li>
        </ol>
      </div>

      <div className="bg-white rounded-lg shadow-md p-4">
        <RegionToolbar {...args} />
        <div className="mt-4 bg-gray-900 rounded h-80 flex items-center justify-center text-gray-500">
          [FITS Image: 2025-12-01T14:30:00.fits]
        </div>
      </div>

      <div className="flex gap-2">
        <button className="btn btn-primary">Save & Continue</button>
        <button className="btn btn-secondary">Skip Image</button>
      </div>
    </div>
  ),
  args: {
    displayId: "JS9",
    compact: false,
  },
  parameters: {
    docs: {
      description: {
        story: "Complete source identification workflow with instructions.",
      },
    },
  },
};

/**
 * Calibrator field marking
 */
export const CalibratorFieldMarking: Story = {
  render: (args) => (
    <div className="bg-white rounded-lg shadow-md p-4 max-w-2xl">
      <div className="flex justify-between items-center mb-3">
        <div>
          <h3 className="text-lg font-semibold">Mark Calibrator Field</h3>
          <p className="text-sm text-gray-500">3C286 transit at field #17</p>
        </div>
        <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
          Calibrator detected
        </span>
      </div>
      <RegionToolbar {...args} />
      <div className="mt-4 bg-gray-800 rounded h-64 relative">
        {/* Mock calibrator highlight */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-24 h-24 border-2 border-yellow-400 rounded-full animate-pulse" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 mt-28 text-yellow-400 text-xs text-center">
          3C286
          <br />
          12.9 Jy
        </div>
      </div>
    </div>
  ),
  args: {
    displayId: "JS9",
    compact: true,
  },
};

/**
 * Mobile responsive toolbar
 */
export const MobileView: Story = {
  args: {
    displayId: "JS9",
    compact: true,
  },
  parameters: {
    viewport: { defaultViewport: "mobile1" },
    docs: {
      description: {
        story: "Compact toolbar optimized for mobile devices.",
      },
    },
  },
};

/**
 * Export format comparison
 */
export const ExportFormatComparison: Story = {
  render: () => (
    <div className="space-y-6 max-w-3xl">
      <h3 className="text-lg font-semibold">Region Export Formats</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="font-medium text-green-700 mb-2">DS9 Format</h4>
          <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">
            {`# DS9 version 4.1
global color=green
image
circle(256,256,30)
box(128,128,40,30,0)`}
          </pre>
          <p className="text-xs text-gray-500 mt-2">
            Standard SAOImage DS9 format. Compatible with most astronomy tools.
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="font-medium text-blue-700 mb-2">CRTF Format</h4>
          <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">
            {`#CRTFv0 CASA Region
global coord=J2000
circle [[12h30m00s, +45d00m00s], 30arcsec]`}
          </pre>
          <p className="text-xs text-gray-500 mt-2">
            CASA Region Text Format. Required for CASA tasks.
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="font-medium text-purple-700 mb-2">JSON Format</h4>
          <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">
            {`[{
  "shape": "circle",
  "ra": 187.5,
  "dec": 45.0,
  "radius_arcsec": 30
}]`}
          </pre>
          <p className="text-xs text-gray-500 mt-2">
            Machine-readable. Best for API integration.
          </p>
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4">
        <RegionToolbar displayId="JS9" />
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Comparison of the three supported export formats.",
      },
    },
  },
};
