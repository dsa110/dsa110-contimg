import type { Meta, StoryObj } from "@storybook/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MSDetailPage from "./MSDetailPage";
import AppLayout from "../components/layout/AppLayout";

// =============================================================================
// Mock Data
// =============================================================================

const createMockMS = (overrides = {}) => ({
  id: "ms-2025-12-01-001",
  path: "/stage/dsa110-contimg/ms/2025-12-01T14-30-00.ms",
  created_at: "2025-12-01T14:32:00Z",
  pointing_ra_deg: 202.7845,
  pointing_dec_deg: 30.5092,
  qa_grade: "good" as const,
  qa_summary: "All baselines present, good UV coverage",
  run_id: "run-2025-12-01-001",
  calibrator_matches: [
    {
      type: "bandpass" as const,
      calibrator: "3C286",
      cal_table: "/stage/dsa110-contimg/caltables/2025-12-01T14-30-00.bcal",
    },
    {
      type: "gain" as const,
      calibrator: "3C286",
      cal_table: "/stage/dsa110-contimg/caltables/2025-12-01T14-30-00.gcal",
    },
  ],
  ...overrides,
});

const mockGoodMS = createMockMS();

const mockUncalibratedMS = createMockMS({
  id: "ms-2025-12-01-002",
  path: "/stage/dsa110-contimg/ms/2025-12-01T15-00-00_raw.ms",
  qa_grade: null,
  qa_summary: null,
  calibrator_matches: [],
});

const mockWarningMS = createMockMS({
  id: "ms-2025-12-01-003",
  path: "/stage/dsa110-contimg/ms/2025-12-01T15-30-00.ms",
  qa_grade: "warn" as const,
  qa_summary: "Some flagged antennas detected, UV coverage may be reduced",
});

const mockFailedMS = createMockMS({
  id: "ms-2025-12-01-004",
  path: "/stage/dsa110-contimg/ms/2025-12-01T16-00-00_bad.ms",
  qa_grade: "fail" as const,
  qa_summary:
    "Severe RFI contamination. Manual flagging recommended before imaging.",
});

// MSDetailPage displays comprehensive information about a Measurement Set.
// Features: visibility raster plot, antenna layout, calibration status,
// QA metrics, and direct links to Interactive Clean and CARTA.
const meta = {
  title: "Pages/MSDetailPage",
  component: MSDetailPage,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component: `
The Measurement Set Detail Page provides a comprehensive view of visibility data.

## Key Components

### Visibility Raster Plot
Interactive visualization of visibility amplitudes across time and frequency.
Color-coded to highlight RFI, flagged data, and calibration artifacts.

### Antenna Layout Widget
D3/SVG visualization of the DSA-110 T-shaped array:
- Color-coded by flagging percentage
- Green (<20% flagged): Good
- Amber (20-50% flagged): Moderate issues
- Red (>50% flagged): Severe issues

### Calibration Status
Shows applied calibration tables:
- Bandpass (frequency-dependent gains)
- Complex gain (time-dependent gains)
- Delay calibration (if applicable)
        `,
      },
    },
  },
  decorators: [
    (Story, context) => {
      const mockData = context.args as {
        _mockMS?: typeof mockGoodMS;
        _isLoading?: boolean;
      };

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: Infinity },
        },
      });

      // Pre-populate query cache
      if (!mockData._isLoading) {
        const msPath = mockData._mockMS?.path || mockGoodMS.path;
        queryClient.setQueryData(
          ["ms", msPath],
          mockData._mockMS || mockGoodMS
        );
      }

      const msPath = mockData._mockMS?.path || mockGoodMS.path;

      return (
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[`/ms/${msPath}`]}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route path="ms/*" element={<Story />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
} satisfies Meta<typeof MSDetailPage>;

export default meta;
type Story = StoryObj<typeof meta>;

// =============================================================================
// Basic States
// =============================================================================

/**
 * Default view with calibrated MS and good QA grade
 */
export const Default: Story = {
  args: {
    _mockMS: mockGoodMS,
  } as any,
};

/**
 * Uncalibrated MS - no calibration tables applied yet
 */
export const Uncalibrated: Story = {
  args: {
    _mockMS: mockUncalibratedMS,
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Raw MS before calibration pipeline has processed it.",
      },
    },
  },
};

/**
 * MS with QA warnings
 */
export const WarningQA: Story = {
  args: {
    _mockMS: mockWarningMS,
  } as any,
  parameters: {
    docs: {
      description: {
        story: "MS with some flagged antennas - may affect image quality.",
      },
    },
  },
};

/**
 * MS that failed QA
 */
export const FailedQA: Story = {
  args: {
    _mockMS: mockFailedMS,
  } as any,
  parameters: {
    docs: {
      description: {
        story: "MS with severe issues - manual intervention recommended.",
      },
    },
  },
};

// =============================================================================
// Workflow Scenarios
// =============================================================================

/**
 * Pre-imaging inspection workflow
 */
export const PreImagingInspection: Story = {
  args: {
    _mockMS: mockGoodMS,
  } as any,
  parameters: {
    docs: {
      description: {
        story: `
**Use case**: Astronomer preparing to image a calibrated MS.

Workflow:
1. Check QA grade (top-left card)
2. Inspect visibility plot for RFI or artifacts
3. Review antenna layout for flagged antennas
4. Verify calibration tables are applied
5. Click "Interactive Clean" to start imaging
        `,
      },
    },
  },
};

/**
 * Troubleshooting bad data
 */
export const TroubleshootingBadData: Story = {
  args: {
    _mockMS: mockFailedMS,
  } as any,
  parameters: {
    docs: {
      description: {
        story: `
**Use case**: Diagnosing why an MS failed QA.

Steps:
1. Read QA summary for initial diagnosis
2. Check visibility plot for RFI patterns
3. Examine antenna layout - which antennas are flagged?
4. Open in CARTA for detailed inspection
5. Apply manual flagging if needed
        `,
      },
    },
  },
};

// =============================================================================
// Edge Cases
// =============================================================================

/**
 * MS with many calibration tables
 */
export const ManyCalTables: Story = {
  args: {
    _mockMS: createMockMS({
      calibrator_matches: [
        { type: "bandpass", calibrator: "3C286", cal_table: "/path/to/bcal_1" },
        { type: "bandpass", calibrator: "3C286", cal_table: "/path/to/bcal_2" },
        { type: "gain", calibrator: "3C286", cal_table: "/path/to/gcal_1" },
        { type: "gain", calibrator: "3C84", cal_table: "/path/to/gcal_2" },
        { type: "delay", calibrator: "3C286", cal_table: "/path/to/dcal" },
        { type: "flux", calibrator: "3C286", cal_table: "/path/to/fcal" },
      ],
    }),
  } as any,
  parameters: {
    docs: {
      description: {
        story: "MS with multiple calibration tables applied.",
      },
    },
  },
};

/**
 * MS with very long path
 */
export const LongPath: Story = {
  args: {
    _mockMS: createMockMS({
      path: "/stage/dsa110-contimg/ms/archive/2025/12/01/observation_session_14_30_00_3c286_calibrated_flagged_averaged_v2.ms",
    }),
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Tests path truncation for deeply nested MS files.",
      },
    },
  },
};

/**
 * MS without pointing coordinates
 */
export const NoCoordinates: Story = {
  args: {
    _mockMS: createMockMS({
      pointing_ra_deg: null,
      pointing_dec_deg: null,
    }),
  } as any,
  parameters: {
    docs: {
      description: {
        story: "MS without specific pointing information (e.g., drift scan).",
      },
    },
  },
};

// =============================================================================
// Responsive Views
// =============================================================================

/**
 * Tablet viewport
 */
export const TabletView: Story = {
  args: {
    _mockMS: mockGoodMS,
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
    _mockMS: mockGoodMS,
  } as any,
  parameters: {
    viewport: { defaultViewport: "mobile1" },
    docs: {
      description: {
        story: "Single-column layout for mobile devices.",
      },
    },
  },
};
