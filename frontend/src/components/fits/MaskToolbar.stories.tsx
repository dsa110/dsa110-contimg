import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "storybook/test";
import { http, HttpResponse } from "msw";
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

// MSW handlers
const successHandler = http.post("*/images/*/masks", async () => {
  await new Promise((r) => setTimeout(r, 500)); // Simulate network delay
  return HttpResponse.json({
    id: "mask-abc123",
    path: "/stage/dsa110-contimg/images/test.mask.abc123.reg",
    format: "ds9",
    region_count: 3,
    created_at: new Date().toISOString(),
  });
});

const errorHandler = http.post("*/images/*/masks", () => {
  return new HttpResponse("Failed to save mask: disk full", { status: 500 });
});

/**
 * Default mask toolbar
 */
export const Default: Story = {
  args: {
    displayId: "JS9",
    imageId: "image-001",
  },
  parameters: {
    msw: {
      handlers: [successHandler],
    },
  },
};

/**
 * With save callback for notifications
 */
export const WithSaveCallback: Story = {
  args: {
    displayId: "JS9",
    imageId: "image-002",
    onMaskSaved: (maskPath) => {
      console.log("Mask saved to:", maskPath);
      alert(`Mask saved successfully!\n\nPath: ${maskPath}`);
    },
  },
  parameters: {
    msw: {
      handlers: [successHandler],
    },
  },
};

/**
 * Error state when save fails
 */
export const SaveError: Story = {
  args: {
    displayId: "JS9",
    imageId: "image-error",
  },
  parameters: {
    msw: {
      handlers: [errorHandler],
    },
    docs: {
      description: {
        story:
          "Demonstrates error handling when the backend fails to save the mask.",
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
  parameters: {
    msw: {
      handlers: [successHandler],
    },
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
