import type { Meta, StoryObj } from "@storybook/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import CARTAViewerPage from "./CARTAViewerPage";

// =============================================================================
// Mock Data
// =============================================================================

const mockCARTAAvailable = {
  available: true,
  version: "4.0.0",
  url: "http://carta.local:3000",
  sessions_active: 2,
  max_sessions: 10,
};

const mockCARTAUnavailable = {
  available: false,
  message: "CARTA server is not currently running",
};

const mockCARTAMaintenance = {
  available: false,
  message: "CARTA is undergoing scheduled maintenance. Please try again later.",
};

// =============================================================================
// Meta Configuration
// =============================================================================

/**
 * The CARTA Viewer Page provides embedded access to CARTA (Cube Analysis and
 * Rendering Tool for Astronomy) for advanced visualization of FITS images and
 * Measurement Sets.
 *
 * ## Features
 *
 * - **Embedded Viewer**: Full CARTA interface embedded via iframe
 * - **Status Checking**: Automatic detection of CARTA availability
 * - **Multiple File Types**: Supports MS files (?ms=) and FITS files (?file=)
 * - **Graceful Degradation**: Clear messaging when CARTA is unavailable
 *
 * ## URL Parameters
 *
 * - `?ms=/path/to/file.ms` - Open a Measurement Set
 * - `?file=/path/to/file.fits` - Open a FITS image
 *
 * ## Integration Points
 *
 * The CARTA viewer is accessed from:
 * - "Open in CARTA" button on MS Detail pages
 * - Image gallery actions for FITS files
 */
const meta = {
  title: "Pages/CARTAViewerPage",
  component: CARTAViewerPage,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "The CARTA Viewer Page embeds the CARTA (Cube Analysis and Rendering Tool for Astronomy) " +
          "viewer for advanced astronomical data visualization.\n\n" +
          "## Key States\n\n" +
          "### Available\n" +
          "When CARTA is running and accessible, the page displays:\n" +
          "- Header bar with file path and version\n" +
          "- Open in new tab link for full-screen access\n" +
          "- Embedded CARTA viewer iframe\n\n" +
          "### Unavailable\n" +
          "When CARTA is not running, shows a friendly message with:\n" +
          "- Clear explanation of the issue\n" +
          "- Link to return to dashboard\n" +
          "- Information about CARTA being an optional component\n\n" +
          "### No File Specified\n" +
          "When accessed without a file parameter:\n" +
          "- Instructions on how to access CARTA\n" +
          "- Links to image browser\n\n" +
          "## Backend Requirements\n\n" +
          "This page requires the following backend endpoints:\n" +
          "- `GET /api/v1/carta/status` - Check CARTA availability",
      },
    },
  },
  decorators: [
    (Story, context) => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            staleTime: Infinity,
          },
        },
      });

      // Get route from story args or default
      const route =
        (context.args as { _route?: string })._route || "/viewer/carta";

      return (
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[route]}>
            <Routes>
              <Route path="/viewer/carta" element={<Story />} />
              <Route path="/" element={<div>Dashboard</div>} />
              <Route path="/images" element={<div>Images List</div>} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
} satisfies Meta<typeof CARTAViewerPage>;

export default meta;
type Story = StoryObj<typeof meta>;

// =============================================================================
// Stories
// =============================================================================

/**
 * CARTA is available and a Measurement Set file is specified.
 * Shows the embedded viewer with header bar.
 */
export const Available: Story = {
  args: {
    _route: "/viewer/carta?ms=/stage/dsa110-contimg/ms/2025-01-15T14-30-00.ms",
  } as any,
  parameters: {
    msw: {
      handlers: [
        http.get("*/carta/status", () => {
          return HttpResponse.json(mockCARTAAvailable);
        }),
      ],
    },
  },
};

/**
 * CARTA is available and a FITS image file is specified.
 */
export const AvailableWithFITS: Story = {
  args: {
    _route: "/viewer/carta?file=/stage/dsa110-contimg/images/2025-01-15.fits",
  } as any,
  parameters: {
    msw: {
      handlers: [
        http.get("*/carta/status", () => {
          return HttpResponse.json(mockCARTAAvailable);
        }),
      ],
    },
  },
};

/**
 * CARTA server is not running or unreachable.
 * Shows a friendly unavailable message with return link.
 */
export const Unavailable: Story = {
  args: {
    _route: "/viewer/carta?ms=/stage/dsa110-contimg/ms/2025-01-15.ms",
  } as any,
  parameters: {
    msw: {
      handlers: [
        http.get("*/carta/status", () => {
          return HttpResponse.json(mockCARTAUnavailable);
        }),
      ],
    },
  },
};

/**
 * CARTA is under maintenance with a custom message.
 */
export const Maintenance: Story = {
  args: {
    _route: "/viewer/carta?ms=/stage/dsa110-contimg/ms/2025-01-15.ms",
  } as any,
  parameters: {
    msw: {
      handlers: [
        http.get("*/carta/status", () => {
          return HttpResponse.json(mockCARTAMaintenance);
        }),
      ],
    },
  },
};

/**
 * No file path specified in URL parameters.
 * Shows instructions on how to access CARTA.
 */
export const NoFileSpecified: Story = {
  args: {
    _route: "/viewer/carta",
  } as any,
  parameters: {
    msw: {
      handlers: [
        http.get("*/carta/status", () => {
          return HttpResponse.json(mockCARTAAvailable);
        }),
      ],
    },
  },
};

/**
 * Loading state while checking CARTA availability.
 */
export const Loading: Story = {
  args: {
    _route: "/viewer/carta?ms=/stage/dsa110-contimg/ms/2025-01-15.ms",
  } as any,
  parameters: {
    msw: {
      handlers: [
        http.get("*/carta/status", async () => {
          // Delay response to show loading state
          await new Promise((resolve) => setTimeout(resolve, 60000));
          return HttpResponse.json(mockCARTAAvailable);
        }),
      ],
    },
  },
};

/**
 * Network error when checking CARTA status.
 * Falls back to unavailable state.
 */
export const NetworkError: Story = {
  args: {
    _route: "/viewer/carta?ms=/stage/dsa110-contimg/ms/2025-01-15.ms",
  } as any,
  parameters: {
    msw: {
      handlers: [
        http.get("*/carta/status", () => {
          return HttpResponse.error();
        }),
      ],
    },
  },
};

/**
 * CARTA available but without version information.
 */
export const NoVersionInfo: Story = {
  args: {
    _route: "/viewer/carta?ms=/stage/dsa110-contimg/ms/2025-01-15.ms",
  } as any,
  parameters: {
    msw: {
      handlers: [
        http.get("*/carta/status", () => {
          return HttpResponse.json({
            available: true,
            // No version field
          });
        }),
      ],
    },
  },
};
