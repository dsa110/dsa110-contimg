import type { Meta, StoryObj } from "@storybook/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import InteractiveImagingPage from "./InteractiveImagingPage";
import AppLayout from "../components/layout/AppLayout";

// =============================================================================
// Mock Data
// =============================================================================

interface MockSession {
  id: string;
  port: number;
  url: string;
  ms_path: string;
  imagename: string;
  created_at: string;
  age_hours: number;
  is_alive: boolean;
  user_id?: string;
}

const createMockSession = (overrides = {}): MockSession => ({
  id: "sess-abc12345-6789-def0-1234-567890abcdef",
  port: 6001,
  url: "http://localhost:6001/bokeh-app",
  ms_path: "/stage/dsa110-contimg/ms/2025-12-01T14-30-00.ms",
  imagename: "/stage/dsa110-contimg/images/interactive_2025-12-01",
  created_at: "2025-12-01T15:00:00Z",
  age_hours: 0.5,
  is_alive: true,
  ...overrides,
});

const mockSingleSession = {
  sessions: [createMockSession()],
  total: 1,
  available_ports: 19,
};

const mockManySessions = {
  sessions: [
    createMockSession({ id: "sess-001", port: 6001, age_hours: 0.1 }),
    createMockSession({
      id: "sess-002",
      port: 6002,
      ms_path: "/stage/dsa110-contimg/ms/2025-12-01T15-00-00.ms",
      age_hours: 1.5,
    }),
    createMockSession({
      id: "sess-003",
      port: 6003,
      ms_path: "/stage/dsa110-contimg/ms/2025-12-01T15-30-00.ms",
      age_hours: 2.3,
    }),
    createMockSession({
      id: "sess-004",
      port: 6004,
      ms_path: "/stage/dsa110-contimg/ms/2025-12-01T16-00-00.ms",
      age_hours: 4.0,
      is_alive: false,
    }),
  ],
  total: 4,
  available_ports: 16,
};

const mockNoSessions = {
  sessions: [],
  total: 0,
  available_ports: 20,
};

const mockImagingDefaults = {
  imsize: [5040, 5040],
  cell: "2.5arcsec",
  specmode: "mfs",
  deconvolver: "mtmfs",
  weighting: "briggs",
  robust: 0.5,
  niter: 10000,
  threshold: "0.5mJy",
  nterms: 2,
  datacolumn: "DATA",
};

// InteractiveImagingPage manages CASA InteractiveClean Bokeh sessions.
// Users can view active sessions, launch new ones, and stop running sessions.
const meta = {
  title: "Pages/InteractiveImagingPage",
  component: InteractiveImagingPage,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component: `
The Interactive Imaging Page provides session management for CASA InteractiveClean.

## Features

### Session Management
- View all active Bokeh sessions
- Launch new sessions from MS files
- Stop/cleanup sessions
- Monitor session health (alive/dead status)

### Session Launch Form
Configure imaging parameters:
- Image size (pixels)
- Cell size (angular resolution)
- Max iterations and threshold
- Weighting scheme (Briggs/Natural/Uniform)
- Robust parameter for Briggs weighting

### Backend Integration
- Sessions run as Bokeh server processes
- Ports allocated from pool (6001-6020)
- Automatic cleanup of stale sessions
        `,
      },
    },
  },
  decorators: [
    (Story, context) => {
      const mockData = context.args as {
        _mockSessions?: typeof mockSingleSession;
        _mockDefaults?: typeof mockImagingDefaults;
        _isLoading?: boolean;
        _isError?: boolean;
      };

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: Infinity },
        },
      });

      // Pre-populate query cache
      if (!mockData._isLoading && !mockData._isError) {
        queryClient.setQueryData(
          ["imaging", "sessions"],
          mockData._mockSessions || mockNoSessions
        );
        queryClient.setQueryData(
          ["imaging", "defaults"],
          mockData._mockDefaults || mockImagingDefaults
        );
      }

      return (
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/imaging"]}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route path="imaging" element={<Story />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
} satisfies Meta<typeof InteractiveImagingPage>;

export default meta;
type Story = StoryObj<typeof meta>;

// =============================================================================
// Basic States
// =============================================================================

// Default view - no active sessions
export const Default: Story = {
  args: {
    _mockSessions: mockNoSessions,
  } as any,
};

// Single active session
export const SingleSession: Story = {
  args: {
    _mockSessions: mockSingleSession,
  } as any,
  parameters: {
    docs: {
      description: {
        story: "One active InteractiveClean session running.",
      },
    },
  },
};

// Multiple active sessions
export const ManySessions: Story = {
  args: {
    _mockSessions: mockManySessions,
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Multiple sessions running - includes one dead session.",
      },
    },
  },
};

// =============================================================================
// Session States
// =============================================================================

// Session that has been running for a long time
export const LongRunningSession: Story = {
  args: {
    _mockSessions: {
      sessions: [
        createMockSession({
          age_hours: 12.5,
          is_alive: true,
        }),
      ],
      total: 1,
      available_ports: 19,
    },
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Session running for 12+ hours - may need cleanup.",
      },
    },
  },
};

// Dead session that needs cleanup
export const DeadSession: Story = {
  args: {
    _mockSessions: {
      sessions: [
        createMockSession({
          is_alive: false,
          age_hours: 3.0,
        }),
      ],
      total: 1,
      available_ports: 19,
    },
  } as any,
  parameters: {
    docs: {
      description: {
        story: "Session that has died - needs manual cleanup.",
      },
    },
  },
};

// All ports exhausted
export const NoPortsAvailable: Story = {
  args: {
    _mockSessions: {
      sessions: Array.from({ length: 20 }, (_, i) =>
        createMockSession({
          id: `sess-${String(i + 1).padStart(3, "0")}`,
          port: 6001 + i,
        })
      ),
      total: 20,
      available_ports: 0,
    },
  } as any,
  parameters: {
    docs: {
      description: {
        story: "All 20 ports in use - cannot launch new sessions.",
      },
    },
  },
};

// =============================================================================
// Workflow Scenarios
// =============================================================================

// Pre-filled from MS detail page
export const FromMSDetail: Story = {
  args: {
    _mockSessions: mockNoSessions,
  } as any,
  parameters: {
    docs: {
      description: {
        story: `
**Workflow**: User clicks "Interactive Clean" from MS detail page.

The MS path is passed via router state and pre-fills the form.
User only needs to specify output image name and imaging parameters.
        `,
      },
    },
  },
};

// Active monitoring workflow
export const MonitoringSessions: Story = {
  args: {
    _mockSessions: mockManySessions,
  } as any,
  parameters: {
    docs: {
      description: {
        story: `
**Workflow**: Pipeline operator monitoring active sessions.

Check for:
- Dead sessions that need cleanup (red indicator)
- Long-running sessions that may be stalled
- Port availability before launching new sessions
        `,
      },
    },
  },
};

// =============================================================================
// Responsive Views
// =============================================================================

// Tablet viewport
export const TabletView: Story = {
  args: {
    _mockSessions: mockSingleSession,
  } as any,
  parameters: {
    viewport: { defaultViewport: "tablet" },
    docs: {
      description: {
        story: "Form layout adapts to tablet screen width.",
      },
    },
  },
};

// Mobile viewport
export const MobileView: Story = {
  args: {
    _mockSessions: mockSingleSession,
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
