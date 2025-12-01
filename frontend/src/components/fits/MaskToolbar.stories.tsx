import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import MaskToolbar from "./MaskToolbar";

/**
 * MaskToolbar extends RegionToolbar with backend integration for saving clean masks.
 *
 * Features:
 * - All RegionToolbar drawing capabilities
 * - Automatic DS9 format conversion for CASA compatibility
 * - Backend persistence via /images/{id}/masks API
 * - Status feedback (saving, saved, error states)
 * - Saved masks can be used during re-imaging
 *
 * This component is specifically designed for creating clean masks
 * that define regions to include during deconvolution. The masks
 * are saved alongside the image and can be referenced when
 * re-imaging with different parameters.
 *
 * Note: Requires JS9 to be loaded. In Storybook, JS9 operations
 * are mocked since the library is not available.
 */
const meta = {
  title: "Components/FITS/MaskToolbar",
  component: MaskToolbar,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component: `
MaskToolbar provides a specialized interface for creating clean masks
used during radio interferometric imaging. Unlike general regions,
masks are:

- Saved to the backend with the image
- Stored in DS9 format for CASA compatibility
- Available for re-imaging workflows
- Tracked in the image's metadata

**Typical workflow:**
1. Open an image that needs re-imaging
2. Draw mask regions around sources
3. Save the mask
4. Use "Re-image with mask" to run tclean with the mask
        `,
      },
    },
  },
  argTypes: {
    displayId: {
      description: "JS9 display ID",
      control: "text",
    },
    imageId: {
      description: "Image ID for backend storage",
      control: "text",
    },
  },
  args: {
    displayId: "JS9",
    imageId: "test-image-123",
    onMaskSaved: fn(),
    onModeChange: fn(),
  },
} satisfies Meta<typeof MaskToolbar>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default mask toolbar
 */
export const Default: Story = {
  args: {
    displayId: "JS9",
    imageId: "image-001",
  },
};

/**
 * With save callback for notifications
 */
export const WithSaveCallback: Story = {
  args: {
    displayId: "JS9",
    imageId: "image-002",
  },
  parameters: {
    docs: {
      description: {
        story: "Check the Actions panel to see onMaskSaved events.",
      },
    },
  },
};

/**
 * In the ImageDetailPage context
 */
export const InImageDetailPage: Story = {
  render: (args) => (
    <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-800 text-white p-4">
        <h2 className="text-xl font-bold">
          observation_2025-01-15T12:30:00.fits
        </h2>
        <p className="text-gray-300 text-sm">
          QA: Pass | 1.2 mJy RMS | 45° beam PA
        </p>
      </div>

      {/* Viewer area */}
      <div className="p-4">
        <div className="mb-4">
          <h3 className="font-semibold mb-2">Create Clean Mask</h3>
          <MaskToolbar {...args} />
        </div>

        {/* Mock JS9 viewer */}
        <div className="bg-gray-900 rounded-lg h-96 flex items-center justify-center">
          <div className="text-center text-gray-400">
            <svg
              className="w-16 h-16 mx-auto mb-2 opacity-50"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" />
            </svg>
            <p>JS9 FITS Viewer</p>
            <p className="text-sm">Draw mask regions on the image</p>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 flex gap-2">
          <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Re-image with Mask
          </button>
          <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
            View Previous Masks
          </button>
        </div>
      </div>
    </div>
  ),
  args: {
    displayId: "JS9-detail",
    imageId: "obs-2025-01-15",
  },
};

/**
 * Side-by-side with region toolbar comparison
 */
export const ComparisonWithRegionToolbar: Story = {
  render: () => (
    <div className="space-y-6 max-w-2xl">
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold text-lg mb-1">MaskToolbar</h3>
        <p className="text-sm text-gray-600 mb-3">
          For creating clean masks (saves to backend, DS9 format)
        </p>
        <MaskToolbar displayId="JS9-mask" imageId="test-image" />
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="font-semibold text-lg mb-1">RegionToolbar</h3>
        <p className="text-sm text-gray-600 mb-3">
          For general regions (export only, multiple formats)
        </p>
        <div className="region-toolbar bg-gray-100 rounded-lg p-2">
          {/* Simplified RegionToolbar representation */}
          <div className="flex gap-2 items-center text-sm text-gray-500">
            [Circle] [Box] [Ellipse] [Polygon] [Point] | Clear | [DS9 ▼] Export
          </div>
        </div>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: `
MaskToolbar is built on top of RegionToolbar but adds:
- Backend integration for mask persistence
- Status feedback (saving, saved, error)
- Usage hints for the re-imaging workflow
- DS9 format enforcement for CASA compatibility
        `,
      },
    },
  },
};

// =============================================================================
// Edge Cases & Realistic Scenarios
// =============================================================================

/**
 * Saving state during backend operation
 */
export const SavingState: Story = {
  render: () => (
    <div className="bg-white rounded-lg shadow-md p-4 max-w-2xl">
      <h3 className="text-lg font-semibold mb-3">Create Clean Mask</h3>
      <div className="opacity-75 pointer-events-none">
        <MaskToolbar displayId="JS9" imageId="test" />
      </div>
      <div className="mt-3 flex items-center gap-2 text-blue-600">
        <svg
          className="animate-spin h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <span className="text-sm">Saving mask to server...</span>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Loading state while mask is being saved to the backend.",
      },
    },
  },
};

/**
 * Success state after saving
 */
export const SavedSuccessfully: Story = {
  render: () => (
    <div className="bg-white rounded-lg shadow-md p-4 max-w-2xl">
      <h3 className="text-lg font-semibold mb-3">Create Clean Mask</h3>
      <MaskToolbar displayId="JS9" imageId="test" />
      <div className="mt-3 flex items-center gap-2 text-green-600 bg-green-50 p-2 rounded">
        <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-sm">
          Mask saved:{" "}
          <code className="text-xs">/masks/obs-2025-12-01.mask.reg</code>
        </span>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Success feedback after mask is saved.",
      },
    },
  },
};

/**
 * Error state when save fails
 */
export const SaveError: Story = {
  render: () => (
    <div className="bg-white rounded-lg shadow-md p-4 max-w-2xl">
      <h3 className="text-lg font-semibold mb-3">Create Clean Mask</h3>
      <MaskToolbar displayId="JS9" imageId="test" />
      <div className="mt-3 flex items-center gap-2 text-red-600 bg-red-50 p-2 rounded">
        <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-sm">
          Failed to save mask: Server returned 500 - disk quota exceeded
        </span>
        <button className="ml-auto text-xs text-red-700 underline">
          Retry
        </button>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Error feedback when mask save fails.",
      },
    },
  },
};

/**
 * Clean mask creation workflow - Step 1: Draw regions
 */
export const WorkflowStep1Draw: Story = {
  render: (args) => (
    <div className="max-w-4xl">
      {/* Progress indicator */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm">
          <span className="flex items-center justify-center w-6 h-6 bg-blue-600 text-white rounded-full text-xs font-bold">
            1
          </span>
          <span className="font-medium text-blue-600">Draw Mask Regions</span>
          <span className="text-gray-400">→</span>
          <span className="flex items-center justify-center w-6 h-6 bg-gray-300 text-gray-600 rounded-full text-xs">
            2
          </span>
          <span className="text-gray-500">Save Mask</span>
          <span className="text-gray-400">→</span>
          <span className="flex items-center justify-center w-6 h-6 bg-gray-300 text-gray-600 rounded-full text-xs">
            3
          </span>
          <span className="text-gray-500">Re-image</span>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-4">
        <div className="mb-4">
          <h3 className="font-semibold mb-2">Draw Clean Mask Regions</h3>
          <p className="text-sm text-gray-600">
            Use circle or box tools to mark regions to include during
            deconvolution. Draw around sources you want to clean deeply.
          </p>
        </div>
        <MaskToolbar {...args} />
        <div className="mt-4 bg-gray-900 rounded h-80 flex items-center justify-center text-gray-500">
          [FITS Viewer: observation_2025-12-01.fits]
        </div>
      </div>
    </div>
  ),
  args: {
    displayId: "JS9",
    imageId: "obs-2025-12-01",
  },
  parameters: {
    docs: {
      description: {
        story: "Step 1 of the clean mask workflow: Drawing mask regions.",
      },
    },
  },
};

/**
 * Multiple masks for comparison
 */
export const MultipleMasksComparison: Story = {
  render: () => (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Compare Mask Strategies</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="font-medium mb-2">Conservative Mask</h4>
          <p className="text-xs text-gray-500 mb-3">
            Small regions around bright sources only
          </p>
          <MaskToolbar displayId="JS9-conservative" imageId="img-cons" />
          <div className="mt-3 bg-gray-800 rounded h-40 relative">
            <div className="absolute top-1/3 left-1/3 w-8 h-8 border-2 border-cyan-400 rounded-full" />
            <div className="absolute top-1/2 right-1/3 w-6 h-6 border-2 border-cyan-400 rounded-full" />
          </div>
          <p className="mt-2 text-xs text-gray-600">
            2 regions • 45 sq. arcsec total
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h4 className="font-medium mb-2">Aggressive Mask</h4>
          <p className="text-xs text-gray-500 mb-3">
            Large regions including extended emission
          </p>
          <MaskToolbar displayId="JS9-aggressive" imageId="img-aggr" />
          <div className="mt-3 bg-gray-800 rounded h-40 relative">
            <div className="absolute top-1/4 left-1/4 w-24 h-16 border-2 border-cyan-400 rounded" />
            <div className="absolute bottom-1/4 right-1/4 w-20 h-20 border-2 border-cyan-400 rounded-full" />
          </div>
          <p className="mt-2 text-xs text-gray-600">
            2 regions • 380 sq. arcsec total
          </p>
        </div>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "Compare different masking strategies side by side.",
      },
    },
  },
};

/**
 * Re-imaging with existing mask
 */
export const ReImageWithMask: Story = {
  render: (args) => (
    <div className="bg-white rounded-lg shadow-md p-4 max-w-2xl">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Re-image with Clean Mask</h3>
          <p className="text-sm text-gray-500">
            Using mask: obs-2025-12-01.mask.reg
          </p>
        </div>
        <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
          Mask loaded
        </span>
      </div>

      {/* Mask preview */}
      <div className="mb-4 bg-gray-100 rounded p-3">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium">Loaded Mask</span>
          <button className="text-xs text-blue-600 hover:underline">
            Edit Mask
          </button>
        </div>
        <div className="text-xs text-gray-600 space-y-1">
          <div>• 3 circle regions (sources)</div>
          <div>• 1 box region (extended emission)</div>
          <div>• Total area: 125 sq. arcsec</div>
        </div>
      </div>

      {/* Imaging parameters */}
      <div className="mb-4">
        <h4 className="text-sm font-medium mb-2">Imaging Parameters</h4>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="bg-gray-50 p-2 rounded">
            <span className="text-gray-500">niter:</span> 50000
          </div>
          <div className="bg-gray-50 p-2 rounded">
            <span className="text-gray-500">threshold:</span> 0.5 mJy
          </div>
          <div className="bg-gray-50 p-2 rounded">
            <span className="text-gray-500">robust:</span> 0.5
          </div>
          <div className="bg-gray-50 p-2 rounded">
            <span className="text-gray-500">cell:</span> 1 arcsec
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        <button className="btn btn-primary flex-1">Start Re-imaging</button>
        <button className="btn btn-secondary">Preview</button>
      </div>
    </div>
  ),
  args: {
    displayId: "JS9",
    imageId: "obs-2025-12-01",
  },
  parameters: {
    docs: {
      description: {
        story: "Dialog for re-imaging with a saved clean mask.",
      },
    },
  },
};
