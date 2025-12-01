import type { Meta, StoryObj } from "@storybook/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HomePage from "./HomePage";
import AppLayout from "../components/layout/AppLayout";

// Mock data for different states
const mockImages = [
  {
    id: "img-001",
    path: "/data/images/2025-11-30T12-00-00.fits",
    qa_grade: "good" as const,
    created_at: "2025-11-30T12:00:00Z",
    pointing_ra_deg: 180.5,
    pointing_dec_deg: 45.2,
  },
  {
    id: "img-002",
    path: "/data/images/2025-11-30T12-30-00.fits",
    qa_grade: "good" as const,
    created_at: "2025-11-30T12:30:00Z",
    pointing_ra_deg: 185.3,
    pointing_dec_deg: 42.8,
  },
  {
    id: "img-003",
    path: "/data/images/2025-11-30T13-00-00.fits",
    qa_grade: "warn" as const,
    created_at: "2025-11-30T13:00:00Z",
    pointing_ra_deg: 190.1,
    pointing_dec_deg: 40.5,
  },
  {
    id: "img-004",
    path: "/data/images/2025-11-30T13-30-00.fits",
    qa_grade: "fail" as const,
    created_at: "2025-11-30T13:30:00Z",
    pointing_ra_deg: 175.8,
    pointing_dec_deg: 48.0,
  },
  {
    id: "img-005",
    path: "/data/images/2025-11-30T14-00-00.fits",
    qa_grade: "good" as const,
    created_at: "2025-11-30T14:00:00Z",
    pointing_ra_deg: 200.2,
    pointing_dec_deg: 35.5,
  },
];

const mockSources = [
  { id: "src-001", name: "J1230+4500", ra_deg: 187.5, dec_deg: 45.0 },
  { id: "src-002", name: "J1215+4230", ra_deg: 183.75, dec_deg: 42.5 },
  { id: "src-003", name: "J1245+4015", ra_deg: 191.25, dec_deg: 40.25 },
];

const mockJobs = [
  { id: "job-001", run_id: "run-2025-11-30-001", status: "completed" },
  { id: "job-002", run_id: "run-2025-11-30-002", status: "running" },
  { id: "job-003", run_id: "run-2025-11-30-003", status: "pending" },
];

const mockPipelineStatus = {
  stages: {
    "convert-uvh5-to-ms": { pending: 0, running: 1, completed: 3, failed: 0 },
    "calibration-solve": { pending: 1, running: 0, completed: 2, failed: 0 },
    "calibration-apply": { pending: 0, running: 0, completed: 2, failed: 0 },
    imaging: { pending: 0, running: 0, completed: 4, failed: 0 },
    validation: { pending: 0, running: 0, completed: 3, failed: 0 },
    crossmatch: { pending: 0, running: 0, completed: 3, failed: 0 },
    photometry: { pending: 0, running: 0, completed: 3, failed: 0 },
    "catalog-setup": { pending: 0, running: 0, completed: 3, failed: 0 },
    "organize-files": { pending: 0, running: 0, completed: 3, failed: 0 },
  },
  total: { pending: 1, running: 1, completed: 23, failed: 0 },
  worker_count: 12,
  last_updated: "2025-11-30T15:00:00Z",
  is_healthy: true,
};

// Large dataset for stress testing
const generateLargeDataset = (count: number) => {
  const images = [];
  const grades = ["good", "good", "good", "warn", "fail"] as const;
  for (let i = 0; i < count; i++) {
    images.push({
      id: `img-${String(i).padStart(4, "0")}`,
      path: `/data/images/2025-11-${String((i % 30) + 1).padStart(
        2,
        "0"
      )}T${String(i % 24).padStart(2, "0")}-00-00.fits`,
      qa_grade: grades[i % grades.length],
      created_at: new Date(Date.now() - i * 3600000).toISOString(),
      pointing_ra_deg: (i * 15) % 360,
      pointing_dec_deg: ((i * 7) % 180) - 90,
    });
  }
  return images;
};

/**
 * HomePage displays the main dashboard with pipeline statistics,
 * sky coverage map, and quick navigation to key sections.
 *
 * This story demonstrates different data states the page can be in.
 */
const meta = {
  title: "Pages/HomePage",
  component: HomePage,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "The main dashboard page showing pipeline overview, sky coverage visualization, and service status.",
      },
    },
  },
  decorators: [
    (Story, context) => {
      // Get mock data from story args or use defaults
      const mockData = context.args as {
        _mockImages?: typeof mockImages;
        _mockSources?: typeof mockSources;
        _mockJobs?: typeof mockJobs;
        _isLoading?: boolean;
      };

      const queryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false, staleTime: Infinity },
        },
      });

      // Pre-populate the query cache with mock data
      if (!mockData._isLoading) {
        queryClient.setQueryData(["images"], mockData._mockImages ?? []);
        queryClient.setQueryData(["sources"], mockData._mockSources ?? []);
        queryClient.setQueryData(["jobs"], mockData._mockJobs ?? []);
        queryClient.setQueryData(["absurd", "status"], mockPipelineStatus);
      }

      return (
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<Story />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
} satisfies Meta<typeof HomePage>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default state with typical data - a few images, sources, and jobs.
 * Shows the sky coverage map with colored observation markers.
 */
export const Default: Story = {
  args: {
    _mockImages: mockImages,
    _mockSources: mockSources,
    _mockJobs: mockJobs,
  } as any,
};

/**
 * Empty state when the pipeline has no data yet.
 * Sky coverage map is hidden, stats show zeros.
 */
export const Empty: Story = {
  args: {
    _mockImages: [],
    _mockSources: [],
    _mockJobs: [],
  } as any,
};

/**
 * Loading state while data is being fetched.
 * Shows loading indicators in stat cards.
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

      // Set queries to loading state by not providing data
      // The queries will be in 'pending' state

      return (
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<Story />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
};

/**
 * Large dataset to test performance and layout with many observations.
 * Shows 100 images scattered across the sky.
 */
export const LargeDataset: Story = {
  args: {
    _mockImages: generateLargeDataset(100),
    _mockSources: Array.from({ length: 50 }, (_, i) => ({
      id: `src-${i}`,
      name: `J${1200 + i}+${4000 + i}`,
      ra_deg: (i * 7.2) % 360,
      dec_deg: ((i * 3.6) % 180) - 90,
    })),
    _mockJobs: Array.from({ length: 25 }, (_, i) => ({
      id: `job-${i}`,
      run_id: `run-2025-11-${String((i % 30) + 1).padStart(2, "0")}-${String(
        i
      ).padStart(3, "0")}`,
      status: ["completed", "running", "pending", "failed"][i % 4],
    })),
  } as any,
};

/**
 * All QA grades are "good" - represents a healthy pipeline state.
 */
export const AllGood: Story = {
  args: {
    _mockImages: mockImages.map((img) => ({
      ...img,
      qa_grade: "good" as const,
    })),
    _mockSources: mockSources,
    _mockJobs: mockJobs.map((job) => ({ ...job, status: "completed" })),
  } as any,
};

/**
 * Mixed QA results with some failures - shows warning state.
 */
export const MixedQuality: Story = {
  args: {
    _mockImages: [
      ...mockImages,
      {
        id: "img-006",
        path: "/data/images/2025-11-30T15-00-00.fits",
        qa_grade: "fail" as const,
        created_at: "2025-11-30T15:00:00Z",
        pointing_ra_deg: 210.0,
        pointing_dec_deg: 30.0,
      },
      {
        id: "img-007",
        path: "/data/images/2025-11-30T15-30-00.fits",
        qa_grade: "fail" as const,
        created_at: "2025-11-30T15:30:00Z",
        pointing_ra_deg: 220.0,
        pointing_dec_deg: 25.0,
      },
    ],
    _mockSources: mockSources,
    _mockJobs: mockJobs,
  } as any,
};

/**
 * No sky coordinates available - sky map section is hidden.
 */
export const NoCoordinates: Story = {
  args: {
    _mockImages: mockImages.map((img) => ({
      ...img,
      pointing_ra_deg: undefined,
      pointing_dec_deg: undefined,
    })),
    _mockSources: mockSources,
    _mockJobs: mockJobs,
  } as any,
};
