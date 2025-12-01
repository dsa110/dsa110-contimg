import type { Meta, StoryObj } from "@storybook/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ImageDetailPage from "./ImageDetailPage";
import AppLayout from "../components/layout/AppLayout";

// =============================================================================
// Mock Data
// =============================================================================

const createMockImage = (overrides = {}) => ({
  id: "img-2025-12-01-001",
  path: "/stage/dsa110-contimg/images/2025-12-01T14-30-00_3c286.fits",
  created_at: "2025-12-01T14:35:00Z",
  pointing_ra_deg: 202.7845,
  pointing_dec_deg: 30.5092,
  qa_grade: "good" as const,
  qa_summary: "Image passed all QA checks",
  noise_jy: 0.00085,
  dynamic_range: 2500,
  beam_major_arcsec: 3.2,
  beam_minor_arcsec: 2.8,
  beam_pa_deg: 45.0,
  ms_path: "/stage/dsa110-contimg/ms/2025-12-01T14-30-00.ms",
  cal_table: "/stage/dsa110-contimg/caltables/2025-12-01T14-30-00.bcal",
  run_id: "run-2025-12-01-001",
  ...overrides,
});

const mockGoodImage = createMockImage();

const mockWarnImage = createMockImage({
  id: "img-2025-12-01-002",
  path: "/stage/dsa110-contimg/images/2025-12-01T15-00-00.fits",
  qa_grade: "warn" as const,
  qa_summary: "High noise detected in outer regions",
  noise_jy: 0.0025,
  dynamic_range: 800,
});

const mockFailImage = createMockImage({
  id: "img-2025-12-01-003",
  path: "/stage/dsa110-contimg/images/2025-12-01T15-30-00_rfi.fits",
  qa_grade: "fail" as const,
  qa_summary: "Severe RFI contamination. Consider re-imaging with flagging.",
  noise_jy: 0.015,
  dynamic_range: 150,
});

const mockMinimalImage = {
  id: "img-minimal",
  path: "/stage/dsa110-contimg/images/minimal.fits",
  created_at: "2025-12-01T10:00:00Z",
  qa_grade: null,
};

/**
 * ImageDetailPage displays comprehensive information about a single FITS image.
 *
 * Features:
 * - FITS viewer with JS9 integration
 * - QA metrics and grade display
 * - Provenance tracking
 * - Sky position visualization (Aladin Lite)
 * - Animation player for time-lapse cutouts
 * - Rating system for human QA
 * - Mask Tools - Draw clean masks for re-imaging (NEW)
 * - Region Tools - Draw and export regions in DS9/CRTF format (NEW)
 *
 * The page uses a responsive two-column layout:
 * - Left: Preview thumbnail and action buttons
 * - Right: Detailed views and metadata
 */
const meta = {
  title: "Pages/ImageDetailPage",
  component: ImageDetailPage,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component: `
The Image Detail Page provides a comprehensive view of a single FITS image,
including interactive visualization, quality assessment, and analysis tools.

## New Features

### Mask Tools
Create clean masks for use during re-imaging:
- Draw circle/box/ellipse regions around sources
- Masks saved in DS9 format for CASA compatibility
- Used with tclean's \`usemask='user'\` parameter

### Region Tools
General-purpose region drawing:
- Multiple export formats (DS9, CRTF, JSON)
- Source identification and marking
- Exclusion zone definition
        `,
      },
    },
  },
  decorators: [
    (Story, context) => {
      const mockData = context.args as {
        _mockImage?: typeof mockGoodImage;
        _isLoading?: boolean;
        _error?: string;
      };

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: Infinity },
        },
      });

      // Pre-populate query cache
      if (!mockData._isLoading && !mockData._error) {
        const imageId = mockData._mockImage?.id || mockGoodImage.id;
        queryClient.setQueryData(["image", imageId], mockData._mockImage || mockGoodImage);
      }

      const imageId = mockData._mockImage?.id || mockGoodImage.id;

      return (
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[`/images/${imageId}`]}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route path="images/:imageId" element={<Story />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
} satisfies Meta<typeof ImageDetailPage>;

export default meta;
type Story = StoryObj<typeof meta>;

// =============================================================================
// Basic States
// =============================================================================

/**
 * Default view of a good quality image with all metadata
 */
export const Default: Story = {
  args: {
    _mockImage: mockGoodImage,
  } as any,
};

/**
 * Image with warning-level QA grade
 */
export const WarningGrade: Story = {
  args: {
    _mockImage: mockWarnImage,
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Image that passed QA with warnings - higher noise than expected.",
      },
    },
  },
};

/**
 * Image that failed QA
 */
export const FailedGrade: Story = {
  args: {
    _mockImage: mockFailImage,
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Image that failed QA due to RFI contamination.",
      },
    },
  },
};

/**
 * Minimal image with only required fields
 */
export const MinimalData: Story = {
  args: {
    _mockImage: mockMinimalImage,
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Image with minimal metadata - no QA grade or coordinates.",
      },
    },
  },
};

// =============================================================================
// Loading & Error States
// =============================================================================

/**
 * Loading state while fetching image data
 */
export const Loading: Story = {
  args: {
    _isLoading: true,
  } as any,
  decorators: [
    (Story) => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: Infinity },
        },
      });
      // Don't populate cache - will show loading state
      return (
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/images/loading-image"]}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route path="images/:imageId" element={<Story />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
};

// =============================================================================
// Interactive Tool Scenarios
// =============================================================================

/**
 * Scenario: Source identification workflow
 */
export const SourceIdentification: Story = {
  args: {
    _mockImage: mockGoodImage,
  } as any,
  parameters: {
    docs: {
      description: {
        story: `
**Use case**: Astronomer identifying sources in a field.

1. Open the FITS Viewer
2. Enable Region Tools
3. Use circle tool to mark point sources
4. Use ellipse for extended sources
5. Export regions as DS9 for catalog matching
        `,
      },
    },
  },
};

/**
 * Scenario: Creating a clean mask for re-imaging
 */
export const CleanMaskCreation: Story = {
  args: {
    _mockImage: mockWarnImage,
  } as any,
  parameters: {
    docs: {
      description: {
        story: `
**Use case**: Improving image quality through re-imaging with clean mask.

1. Review the warning in QA metrics (high noise)
2. Open FITS Viewer
3. Enable Mask Tools
4. Draw mask regions around bright sources
5. Save mask to backend
6. Use "Re-image with Mask" to create improved version
        `,
      },
    },
  },
};

/**
 * Scenario: QA review workflow
 */
export const QAReviewWorkflow: Story = {
  args: {
    _mockImage: createMockImage({
      qa_grade: null, // Not yet graded
      qa_summary: null,
    }),
  } as any,
  parameters: {
    docs: {
      description: {
        story: `
**Use case**: Human QA review of an ungraded image.

1. View image in FITS viewer
2. Check for artifacts, RFI, beam quality
3. Enable Rating card
4. Select appropriate grade and tags
5. Add notes if needed
6. Submit rating
        `,
      },
    },
  },
};

// =============================================================================
// Responsive & Accessibility
// =============================================================================

/**
 * Tablet viewport
 */
export const TabletView: Story = {
  args: {
    _mockImage: mockGoodImage,
  } as any,
  parameters: {
    viewport: { defaultViewport: "tablet" },
    docs: {
      description: {
        story: "Layout optimized for tablet screens.",
      },
    },
  },
};

/**
 * Mobile viewport
 */
export const MobileView: Story = {
  args: {
    _mockImage: mockGoodImage,
  } as any,
  parameters: {
    viewport: { defaultViewport: "mobile1" },
    docs: {
      description: {
        story: "Layout optimized for mobile screens - single column.",
      },
    },
  },
};

// =============================================================================
// Edge Cases
// =============================================================================

/**
 * Very long filename
 */
export const LongFilename: Story = {
  args: {
    _mockImage: createMockImage({
      path: "/stage/dsa110-contimg/images/very_long_observation_name_with_lots_of_details_2025-12-01T14-30-00_3c286_calibrated_cleaned_v2_final.fits",
    }),
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Tests text overflow handling for long filenames.",
      },
    },
  },
};

/**
 * High precision coordinates
 */
export const HighPrecisionCoordinates: Story = {
  args: {
    _mockImage: createMockImage({
      pointing_ra_deg: 202.784512345678,
      pointing_dec_deg: 30.509234567890,
    }),
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Tests coordinate display formatting with high precision values.",
      },
    },
  },
};

/**
 * Null coordinates (survey scan)
 */
export const NoCoordinates: Story = {
  args: {
    _mockImage: createMockImage({
      pointing_ra_deg: null,
      pointing_dec_deg: null,
    }),
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Image without specific pointing coordinates (e.g., all-sky survey).",
      },
    },
  },
};
