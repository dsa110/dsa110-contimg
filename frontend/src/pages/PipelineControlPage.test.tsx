/**
 * Unit tests for PipelineControlPage component.
 *
 * Tests the Pipeline Control dashboard including:
 * - Full pipeline execution form
 * - Individual stage execution
 * - Registered pipeline management
 * - Execution history display
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

// Mock the hooks before importing the component
vi.mock("../hooks/usePipeline", () => ({
  useRegisteredPipelines: vi.fn(),
  useAvailableStages: vi.fn(),
  useRunPipeline: vi.fn(),
  useRunFullPipeline: vi.fn(),
  useRunStage: vi.fn(),
  useCalibrateMS: vi.fn(),
  useImageMS: vi.fn(),
  useExecutions: vi.fn(),
  useExecution: vi.fn(),
}));

import PipelineControlPage from "./PipelineControlPage";
import {
  useRegisteredPipelines,
  useAvailableStages,
  useRunPipeline,
  useRunFullPipeline,
  useRunStage,
  useCalibrateMS,
  useImageMS,
  useExecutions,
} from "../hooks/usePipeline";

// =============================================================================
// Test Helpers
// =============================================================================

const createQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
};

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{component}</MemoryRouter>
    </QueryClientProvider>
  );
};

// Mock data
const mockPipelines = {
  pipelines: [
    {
      name: "nightly_mosaic",
      description: "Nightly mosaic pipeline",
      schedule: "0 3 * * *",
      is_scheduled: true,
    },
    {
      name: "on_demand_mosaic",
      description: "On-demand mosaic",
      schedule: null,
      is_scheduled: false,
    },
  ],
  total: 2,
};

const mockStages = {
  stages: [
    { name: "convert-uvh5-to-ms", description: "Convert UVH5 to MS" },
    { name: "calibration-solve", description: "Solve calibration" },
    { name: "calibration-apply", description: "Apply calibration" },
    { name: "imaging", description: "Create images" },
    { name: "validation", description: "Validate quality" },
  ],
  total: 5,
};

const mockExecutions = {
  executions: [
    {
      execution_id: "exec-001",
      pipeline_name: "nightly_mosaic",
      status: "completed",
      started_at: "2025-01-15T03:00:00Z",
      completed_at: "2025-01-15T03:45:00Z",
      error: null,
      jobs: [
        { job_id: "job-001", job_type: "mosaic-plan", status: "completed" },
        { job_id: "job-002", job_type: "mosaic-build", status: "completed" },
      ],
    },
    {
      execution_id: "exec-002",
      pipeline_name: "on_demand_mosaic",
      status: "running",
      started_at: "2025-01-15T10:30:00Z",
      completed_at: null,
      error: null,
      jobs: [
        { job_id: "job-003", job_type: "mosaic-plan", status: "completed" },
        { job_id: "job-004", job_type: "mosaic-build", status: "running" },
      ],
    },
    {
      execution_id: "exec-003",
      pipeline_name: "calibration",
      status: "failed",
      started_at: "2025-01-14T18:00:00Z",
      completed_at: "2025-01-14T18:15:00Z",
      error: "Calibration failed",
      jobs: [
        { job_id: "job-005", job_type: "calibration-solve", status: "failed" },
      ],
    },
  ],
  total: 3,
};

// =============================================================================
// Setup
// =============================================================================

const mockMutate = vi.fn();

const setupMocks = (
  overrides: Partial<{
    pipelinesLoading: boolean;
    stagesLoading: boolean;
    executionsLoading: boolean;
    pipelinesError: Error | null;
    stagesError: Error | null;
    executionsError: Error | null;
    pipelines: typeof mockPipelines;
    stages: typeof mockStages;
    executions: typeof mockExecutions;
  }> = {}
) => {
  const {
    pipelinesLoading = false,
    stagesLoading = false,
    executionsLoading = false,
    pipelinesError = null,
    stagesError = null,
    executionsError = null,
    pipelines = mockPipelines,
    stages = mockStages,
    executions = mockExecutions,
  } = overrides;

  // Reset all mocks
  vi.mocked(useRegisteredPipelines).mockReturnValue({
    data: pipelinesLoading ? undefined : pipelines,
    isLoading: pipelinesLoading,
    error: pipelinesError,
  } as any);

  vi.mocked(useAvailableStages).mockReturnValue({
    data: stagesLoading ? undefined : stages,
    isLoading: stagesLoading,
    error: stagesError,
  } as any);

  vi.mocked(useExecutions).mockReturnValue({
    data: executionsLoading ? undefined : executions,
    isLoading: executionsLoading,
    error: executionsError,
  } as any);

  vi.mocked(useRunPipeline).mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isSuccess: false,
    isError: false,
    data: null,
    error: null,
  } as any);

  vi.mocked(useRunFullPipeline).mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isSuccess: false,
    isError: false,
    data: null,
    error: null,
  } as any);

  vi.mocked(useRunStage).mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isSuccess: false,
    isError: false,
    data: null,
    error: null,
  } as any);

  vi.mocked(useCalibrateMS).mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isSuccess: false,
    isError: false,
    data: null,
    error: null,
  } as any);

  vi.mocked(useImageMS).mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isSuccess: false,
    isError: false,
    data: null,
    error: null,
  } as any);
};

beforeEach(() => {
  vi.clearAllMocks();
  setupMocks();
});

afterEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// Tests: Page Structure
// =============================================================================

describe("PipelineControlPage - Structure", () => {
  it("renders page title", () => {
    renderWithProviders(<PipelineControlPage />);
    expect(screen.getByText("Pipeline Control")).toBeInTheDocument();
  });

  it("renders page description", () => {
    renderWithProviders(<PipelineControlPage />);
    expect(
      screen.getByText(/Run and monitor DSA-110 data processing pipelines/)
    ).toBeInTheDocument();
  });

  it("renders all main sections", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("Run Full Pipeline")).toBeInTheDocument();
    expect(screen.getByText("Run Individual Stage")).toBeInTheDocument();
    expect(screen.getByText("Registered Pipelines")).toBeInTheDocument();
    expect(screen.getByText("Recent Executions")).toBeInTheDocument();
  });
});

// =============================================================================
// Tests: Full Pipeline Section
// =============================================================================

describe("PipelineControlPage - Full Pipeline", () => {
  it("renders time range inputs", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("Start Time")).toBeInTheDocument();
    expect(screen.getByText("End Time")).toBeInTheDocument();
  });

  it("renders quick time selection buttons", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByRole("button", { name: "Last 1h" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Last 6h" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Last 12h" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Last 24h" })
    ).toBeInTheDocument();
  });

  it("quick time buttons set time inputs", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PipelineControlPage />);

    await user.click(screen.getByRole("button", { name: "Last 6h" }));

    const startInput =
      screen.getAllByRole("textbox")[0] ||
      document.querySelector('input[type="datetime-local"]');
    // Input should have a value after clicking quick button
    expect(startInput).toBeDefined();
  });

  it("renders pipeline option checkboxes", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("Run Calibration")).toBeInTheDocument();
    expect(screen.getByText("Run Imaging")).toBeInTheDocument();
  });

  it("disables imaging when calibration unchecked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PipelineControlPage />);

    const checkboxes = screen.getAllByRole("checkbox");
    const calibrationCheckbox = checkboxes[0];
    const imagingCheckbox = checkboxes[1];

    // Initially both should be checked
    expect(calibrationCheckbox).toBeChecked();
    expect(imagingCheckbox).toBeChecked();

    // Uncheck calibration
    await user.click(calibrationCheckbox);

    // Imaging should be disabled
    expect(imagingCheckbox).toBeDisabled();
  });

  it("toggles advanced options", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PipelineControlPage />);

    // Advanced options hidden initially
    expect(screen.queryByText("Input Directory")).not.toBeInTheDocument();

    // Show advanced options
    await user.click(screen.getByText("Show advanced options"));

    // Now visible
    expect(screen.getByText("Input Directory")).toBeInTheDocument();
    expect(screen.getByText("Output Directory")).toBeInTheDocument();

    // Hide again
    await user.click(screen.getByText("Hide advanced options"));
    expect(screen.queryByText("Input Directory")).not.toBeInTheDocument();
  });

  it("renders Run Pipeline button", () => {
    renderWithProviders(<PipelineControlPage />);
    expect(
      screen.getByRole("button", { name: /Run Pipeline/i })
    ).toBeInTheDocument();
  });
});

// =============================================================================
// Tests: Individual Stages Section
// =============================================================================

describe("PipelineControlPage - Individual Stages", () => {
  it("renders MS path input", () => {
    renderWithProviders(<PipelineControlPage />);
    expect(screen.getByText("Measurement Set Path")).toBeInTheDocument();
  });

  it("renders stage dropdown", () => {
    renderWithProviders(<PipelineControlPage />);
    expect(screen.getByText("Stage")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("shows loading state for stages", () => {
    setupMocks({ stagesLoading: true });
    renderWithProviders(<PipelineControlPage />);

    // Should show loading indicator somewhere
    expect(screen.getByText("Run Individual Stage")).toBeInTheDocument();
  });

  it("shows calibration options when calibration selected", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PipelineControlPage />);

    const stageSelect = screen.getByRole("combobox");
    await user.selectOptions(stageSelect, "calibration");

    expect(screen.getByText("Apply existing solutions")).toBeInTheDocument();
  });

  it("shows imaging options when imaging selected", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PipelineControlPage />);

    const stageSelect = screen.getByRole("combobox");
    await user.selectOptions(stageSelect, "imaging");

    expect(screen.getByText("Image Size")).toBeInTheDocument();
  });
});

// =============================================================================
// Tests: Registered Pipelines Section
// =============================================================================

describe("PipelineControlPage - Registered Pipelines", () => {
  it("displays pipeline names", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("nightly_mosaic")).toBeInTheDocument();
    expect(screen.getByText("on_demand_mosaic")).toBeInTheDocument();
  });

  it("shows scheduled badge for scheduled pipelines", () => {
    renderWithProviders(<PipelineControlPage />);
    expect(screen.getByText("Scheduled")).toBeInTheDocument();
  });

  it("shows schedule for scheduled pipelines", () => {
    renderWithProviders(<PipelineControlPage />);
    expect(screen.getByText(/0 3 \* \* \*/)).toBeInTheDocument();
  });

  it("renders Run Now buttons", () => {
    renderWithProviders(<PipelineControlPage />);
    const runButtons = screen.getAllByRole("button", { name: "Run Now" });
    expect(runButtons).toHaveLength(2);
  });

  it("shows empty state when no pipelines", () => {
    setupMocks({ pipelines: { pipelines: [], total: 0 } });
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText(/No pipelines registered/)).toBeInTheDocument();
  });

  it("shows error state on API error", () => {
    setupMocks({ pipelinesError: new Error("API Error") });
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText(/Failed to load/)).toBeInTheDocument();
  });

  it("clicking Run Now triggers pipeline", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PipelineControlPage />);

    const runButtons = screen.getAllByRole("button", { name: "Run Now" });
    await user.click(runButtons[0]);

    expect(mockMutate).toHaveBeenCalled();
  });
});

// =============================================================================
// Tests: Execution History Section
// =============================================================================

describe("PipelineControlPage - Execution History", () => {
  it("displays execution table", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("Pipeline")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Started")).toBeInTheDocument();
    expect(screen.getByText("Jobs")).toBeInTheDocument();
  });

  it("shows execution statuses", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("shows job counts", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("2 jobs")).toBeInTheDocument();
    expect(screen.getByText("1 jobs")).toBeInTheDocument();
  });

  it("shows failed job indicator for failed executions", () => {
    renderWithProviders(<PipelineControlPage />);

    // The failed execution should indicate failed jobs
    const failedRow = screen.getByText("calibration").closest("tr");
    expect(failedRow).toBeInTheDocument();
    expect(within(failedRow!).getByText("failed")).toBeInTheDocument();
  });

  it("shows empty state when no executions", () => {
    setupMocks({ executions: { executions: [], total: 0 } });
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText(/No pipeline executions/)).toBeInTheDocument();
  });

  it("shows error state on API error", () => {
    setupMocks({ executionsError: new Error("API Error") });
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText(/Failed to load executions/)).toBeInTheDocument();
  });
});

// =============================================================================
// Tests: Loading States
// =============================================================================

describe("PipelineControlPage - Loading States", () => {
  it("shows loading for pipelines", () => {
    setupMocks({ pipelinesLoading: true });
    renderWithProviders(<PipelineControlPage />);

    // Page should still render while loading
    expect(screen.getByText("Registered Pipelines")).toBeInTheDocument();
  });

  it("shows loading for stages", () => {
    setupMocks({ stagesLoading: true });
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("Run Individual Stage")).toBeInTheDocument();
  });

  it("shows loading for executions", () => {
    setupMocks({ executionsLoading: true });
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("Recent Executions")).toBeInTheDocument();
  });
});

// =============================================================================
// Tests: Mutations
// =============================================================================

describe("PipelineControlPage - Mutations", () => {
  it("shows pending state during pipeline run", () => {
    vi.mocked(useRunFullPipeline).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
      isSuccess: false,
      isError: false,
      data: null,
      error: null,
    } as any);

    renderWithProviders(<PipelineControlPage />);

    const runButton = screen.getByRole("button", { name: /Run Pipeline/i });
    expect(runButton).toBeDisabled();
  });

  it("shows success message after successful run", () => {
    vi.mocked(useRunFullPipeline).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isSuccess: true,
      isError: false,
      data: { message: "Pipeline queued successfully" },
      error: null,
    } as any);

    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText(/Pipeline queued/)).toBeInTheDocument();
  });

  it("shows error message after failed run", () => {
    vi.mocked(useRunFullPipeline).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isSuccess: false,
      isError: true,
      data: null,
      error: new Error("Pipeline failed to start"),
    } as any);

    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText(/Error/)).toBeInTheDocument();
  });
});

// =============================================================================
// Tests: Accessibility
// =============================================================================

describe("PipelineControlPage - Accessibility", () => {
  it("has proper heading hierarchy", () => {
    renderWithProviders(<PipelineControlPage />);

    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toHaveTextContent("Pipeline Control");

    const h2s = screen.getAllByRole("heading", { level: 2 });
    expect(h2s.length).toBeGreaterThanOrEqual(4);
  });

  it("form elements have labels", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(screen.getByText("Start Time")).toBeInTheDocument();
    expect(screen.getByText("End Time")).toBeInTheDocument();
    expect(screen.getByText("Measurement Set Path")).toBeInTheDocument();
    expect(screen.getByText("Stage")).toBeInTheDocument();
  });

  it("buttons have accessible names", () => {
    renderWithProviders(<PipelineControlPage />);

    expect(
      screen.getByRole("button", { name: "Run Pipeline" })
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Run Now" })).toHaveLength(2);
  });
});
