import type { Meta, StoryObj } from "@storybook/react";
import { http, HttpResponse, delay } from "msw";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  PipelineStatusPanel,
  type PipelineStatusResponse,
} from "./PipelineStatusPanel";

/**
 * Pipeline Status Panel shows ABSURD workflow status with real-time
 * task counts per stage. Each stage is clickable and links to the
 * Jobs list filtered by that stage.
 */
const meta: Meta<typeof PipelineStatusPanel> = {
  title: "Pipeline/PipelineStatusPanel",
  component: PipelineStatusPanel,
  decorators: [
    (Story) => {
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            staleTime: Infinity,
          },
        },
      });
      return (
        <QueryClientProvider client={queryClient}>
          <MemoryRouter>
            <div className="p-4 max-w-5xl">
              <Story />
            </div>
          </MemoryRouter>
        </QueryClientProvider>
      );
    },
  ],
  parameters: {
    layout: "padded",
  },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof PipelineStatusPanel>;

// =============================================================================
// Mock Data
// =============================================================================

const healthyPipelineData: PipelineStatusResponse = {
  stages: {
    "convert-uvh5-to-ms": { pending: 2, running: 1, completed: 10, failed: 0 },
    "calibration-solve": { pending: 0, running: 0, completed: 5, failed: 0 },
    "calibration-apply": { pending: 3, running: 0, completed: 4, failed: 0 },
    imaging: { pending: 1, running: 2, completed: 8, failed: 0 },
    validation: { pending: 0, running: 0, completed: 8, failed: 0 },
    crossmatch: { pending: 0, running: 1, completed: 7, failed: 0 },
    photometry: { pending: 0, running: 0, completed: 7, failed: 0 },
    "catalog-setup": { pending: 0, running: 0, completed: 7, failed: 0 },
    "organize-files": { pending: 0, running: 0, completed: 6, failed: 0 },
  },
  total: { pending: 6, running: 4, completed: 62, failed: 0 },
  worker_count: 4,
  last_updated: new Date().toISOString(),
  is_healthy: true,
};

const withFailuresData: PipelineStatusResponse = {
  stages: {
    "convert-uvh5-to-ms": { pending: 0, running: 0, completed: 15, failed: 2 },
    "calibration-solve": { pending: 0, running: 0, completed: 10, failed: 3 },
    "calibration-apply": { pending: 0, running: 0, completed: 8, failed: 0 },
    imaging: { pending: 0, running: 1, completed: 5, failed: 1 },
    validation: { pending: 2, running: 0, completed: 4, failed: 0 },
    crossmatch: { pending: 0, running: 0, completed: 4, failed: 0 },
    photometry: { pending: 0, running: 0, completed: 4, failed: 0 },
    "catalog-setup": { pending: 0, running: 0, completed: 4, failed: 0 },
    "organize-files": { pending: 0, running: 0, completed: 3, failed: 0 },
  },
  total: { pending: 2, running: 1, completed: 57, failed: 6 },
  worker_count: 2,
  last_updated: new Date().toISOString(),
  is_healthy: false,
};

const emptyPipelineData: PipelineStatusResponse = {
  stages: {
    "convert-uvh5-to-ms": { pending: 0, running: 0, completed: 0, failed: 0 },
    "calibration-solve": { pending: 0, running: 0, completed: 0, failed: 0 },
    "calibration-apply": { pending: 0, running: 0, completed: 0, failed: 0 },
    imaging: { pending: 0, running: 0, completed: 0, failed: 0 },
    validation: { pending: 0, running: 0, completed: 0, failed: 0 },
    crossmatch: { pending: 0, running: 0, completed: 0, failed: 0 },
    photometry: { pending: 0, running: 0, completed: 0, failed: 0 },
    "catalog-setup": { pending: 0, running: 0, completed: 0, failed: 0 },
    "organize-files": { pending: 0, running: 0, completed: 0, failed: 0 },
  },
  total: { pending: 0, running: 0, completed: 0, failed: 0 },
  worker_count: 4,
  last_updated: new Date().toISOString(),
  is_healthy: true,
};

const busyPipelineData: PipelineStatusResponse = {
  stages: {
    "convert-uvh5-to-ms": { pending: 15, running: 4, completed: 50, failed: 0 },
    "calibration-solve": { pending: 8, running: 2, completed: 42, failed: 1 },
    "calibration-apply": { pending: 10, running: 3, completed: 38, failed: 0 },
    imaging: { pending: 12, running: 4, completed: 30, failed: 2 },
    validation: { pending: 8, running: 2, completed: 28, failed: 0 },
    crossmatch: { pending: 5, running: 1, completed: 25, failed: 0 },
    photometry: { pending: 4, running: 1, completed: 24, failed: 0 },
    "catalog-setup": { pending: 3, running: 0, completed: 24, failed: 0 },
    "organize-files": { pending: 2, running: 0, completed: 22, failed: 0 },
  },
  total: { pending: 67, running: 17, completed: 283, failed: 3 },
  worker_count: 8,
  last_updated: new Date().toISOString(),
  is_healthy: true,
};

// =============================================================================
// Stories
// =============================================================================

/**
 * Default healthy pipeline with active tasks across stages.
 */
export const Healthy: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("/api/absurd/status", () => {
          return HttpResponse.json(healthyPipelineData);
        }),
      ],
    },
  },
};

/**
 * Pipeline with failures showing degraded status.
 */
export const WithFailures: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("/api/absurd/status", () => {
          return HttpResponse.json(withFailuresData);
        }),
      ],
    },
  },
};

/**
 * Empty pipeline - no tasks have run yet.
 */
export const Empty: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("/api/absurd/status", () => {
          return HttpResponse.json(emptyPipelineData);
        }),
      ],
    },
  },
};

/**
 * Busy pipeline with many tasks in queue.
 */
export const Busy: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("/api/absurd/status", () => {
          return HttpResponse.json(busyPipelineData);
        }),
      ],
    },
  },
};

/**
 * Compact mode showing only 5 key stages.
 */
export const Compact: Story = {
  args: {
    compact: true,
  },
  parameters: {
    msw: {
      handlers: [
        http.get("/api/absurd/status", () => {
          return HttpResponse.json(healthyPipelineData);
        }),
      ],
    },
  },
};

/**
 * Loading state while fetching data.
 */
export const Loading: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("/api/absurd/status", async () => {
          await delay("infinite");
          return HttpResponse.json(healthyPipelineData);
        }),
      ],
    },
  },
};

/**
 * Error state when ABSURD is not available.
 */
export const Error: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("/api/absurd/status", () => {
          return HttpResponse.error();
        }),
      ],
    },
  },
};
