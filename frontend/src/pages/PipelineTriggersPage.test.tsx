/**
 * Tests for PipelineTriggersPage
 *
 * Tests:
 * - Trigger list display
 * - Create trigger modal
 * - Toggle trigger enable/disable
 * - Execute trigger manually
 * - Delete trigger
 * - Execution history
 * - Filter controls
 * - Statistics display
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PipelineTriggersPage } from "./PipelineTriggersPage";
import type {
  PipelineTrigger,
  TriggerExecution,
  AvailablePipeline,
} from "../api/triggers";

// ============================================================================
// Mocks
// ============================================================================

const mockTriggers: PipelineTrigger[] = [
  {
    id: "trigger-1",
    name: "Auto Process MS",
    description: "Automatically process new measurement sets",
    event: "new_measurement_set",
    status: "enabled",
    pipeline_id: "pipeline-1",
    pipeline_name: "Standard Imaging",
    conditions: [{ field: "source", operator: "equals", value: "DSA-110" }],
    parameters: {},
    priority: 1,
    max_concurrent: 3,
    retry_count: 2,
    retry_delay_seconds: 60,
    cooldown_seconds: 0,
    total_executions: 150,
    successful_executions: 140,
    failed_executions: 10,
    last_execution: "2024-01-15T10:00:00Z",
    created_at: "2024-01-01T00:00:00Z",
    created_by: "admin",
    updated_at: "2024-01-10T00:00:00Z",
    updated_by: "admin",
  },
  {
    id: "trigger-2",
    name: "Daily Cleanup",
    description: "Run cleanup pipeline daily",
    event: "schedule",
    status: "enabled",
    pipeline_id: "pipeline-2",
    pipeline_name: "Data Cleanup",
    conditions: [],
    schedule: {
      cron: "0 0 * * *",
      description: "Daily at midnight",
      timezone: "UTC",
      next_run: "2024-01-16T00:00:00Z",
    },
    parameters: {},
    priority: 5,
    max_concurrent: 1,
    retry_count: 1,
    retry_delay_seconds: 300,
    cooldown_seconds: 0,
    total_executions: 30,
    successful_executions: 30,
    failed_executions: 0,
    last_execution: "2024-01-15T00:00:00Z",
    created_at: "2024-01-01T00:00:00Z",
    created_by: "admin",
    updated_at: "2024-01-01T00:00:00Z",
    updated_by: "admin",
  },
  {
    id: "trigger-3",
    name: "Manual Pipeline",
    event: "manual",
    status: "disabled",
    pipeline_id: "pipeline-3",
    pipeline_name: "Custom Processing",
    conditions: [],
    parameters: {},
    priority: 10,
    max_concurrent: 1,
    retry_count: 0,
    retry_delay_seconds: 0,
    cooldown_seconds: 0,
    total_executions: 5,
    successful_executions: 2,
    failed_executions: 3,
    created_at: "2024-01-05T00:00:00Z",
    created_by: "operator",
    updated_at: "2024-01-05T00:00:00Z",
    updated_by: "operator",
  },
];

const mockExecutions: TriggerExecution[] = [
  {
    id: "exec-1",
    trigger_id: "trigger-1",
    trigger_name: "Auto Process MS",
    pipeline_id: "pipeline-1",
    pipeline_name: "Standard Imaging",
    status: "success",
    event_type: "new_measurement_set",
    job_id: "job-123",
    started_at: "2024-01-15T10:00:00Z",
    completed_at: "2024-01-15T10:05:00Z",
    duration_seconds: 300,
  },
  {
    id: "exec-2",
    trigger_id: "trigger-2",
    trigger_name: "Daily Cleanup",
    pipeline_id: "pipeline-2",
    pipeline_name: "Data Cleanup",
    status: "running",
    event_type: "schedule",
    started_at: "2024-01-16T00:00:00Z",
  },
  {
    id: "exec-3",
    trigger_id: "trigger-1",
    trigger_name: "Auto Process MS",
    pipeline_id: "pipeline-1",
    pipeline_name: "Standard Imaging",
    status: "failed",
    event_type: "new_measurement_set",
    started_at: "2024-01-14T15:00:00Z",
    completed_at: "2024-01-14T15:01:00Z",
    duration_seconds: 60,
    error_message: "Pipeline timeout",
  },
];

const mockPipelines: AvailablePipeline[] = [
  {
    id: "pipeline-1",
    name: "Standard Imaging",
    description: "Standard imaging pipeline",
    parameters: [],
  },
  {
    id: "pipeline-2",
    name: "Data Cleanup",
    description: "Clean up old data",
    parameters: [],
  },
];

const mockUseTriggers = vi.fn();
const mockUseCreateTrigger = vi.fn();
const mockUseDeleteTrigger = vi.fn();
const mockUseToggleTrigger = vi.fn();
const mockUseExecuteTrigger = vi.fn();
const mockUseRecentExecutions = vi.fn();
const mockUseAvailablePipelines = vi.fn();

vi.mock("../api/triggers", async () => {
  const actual = await vi.importActual("../api/triggers");
  return {
    ...actual,
    useTriggers: () => mockUseTriggers(),
    useCreateTrigger: () => mockUseCreateTrigger(),
    useDeleteTrigger: () => mockUseDeleteTrigger(),
    useToggleTrigger: () => mockUseToggleTrigger(),
    useExecuteTrigger: () => mockUseExecuteTrigger(),
    useRecentExecutions: () => mockUseRecentExecutions(),
    useAvailablePipelines: () => mockUseAvailablePipelines(),
  };
});

// ============================================================================
// Test Utils
// ============================================================================

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderPage() {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <PipelineTriggersPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

// ============================================================================
// Tests
// ============================================================================

describe("PipelineTriggersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    mockUseTriggers.mockReturnValue({
      data: mockTriggers,
      isLoading: false,
      error: null,
    });

    mockUseCreateTrigger.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockTriggers[0]),
      isPending: false,
      isError: false,
    });

    mockUseDeleteTrigger.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue("trigger-1"),
      isPending: false,
    });

    mockUseToggleTrigger.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockTriggers[0]),
      isPending: false,
    });

    mockUseExecuteTrigger.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockExecutions[0]),
      isPending: false,
    });

    mockUseRecentExecutions.mockReturnValue({
      data: mockExecutions,
      isLoading: false,
      error: null,
    });

    mockUseAvailablePipelines.mockReturnValue({
      data: mockPipelines,
      isLoading: false,
    });
  });

  describe("Page Header", () => {
    it("renders page title and description", () => {
      renderPage();

      expect(
        screen.getByRole("heading", { name: /pipeline triggers/i })
      ).toBeInTheDocument();
      expect(
        screen.getByText(/automate pipeline execution/i)
      ).toBeInTheDocument();
    });

    it("renders create trigger button", () => {
      renderPage();

      expect(
        screen.getByRole("button", { name: /create trigger/i })
      ).toBeInTheDocument();
    });
  });

  describe("Statistics", () => {
    it("shows total triggers count", () => {
      renderPage();

      expect(screen.getByText("Total Triggers")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("shows active triggers count", () => {
      renderPage();

      expect(screen.getByText("Active")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("shows total executions", () => {
      renderPage();

      expect(screen.getByText("Total Executions")).toBeInTheDocument();
      // 150 + 30 + 5 = 185
      expect(screen.getByText("185")).toBeInTheDocument();
    });

    it("shows average success rate", () => {
      renderPage();

      expect(screen.getByText("Avg Success Rate")).toBeInTheDocument();
    });
  });

  describe("Trigger List", () => {
    it("renders list of triggers", () => {
      renderPage();

      expect(screen.getByText("Auto Process MS")).toBeInTheDocument();
      expect(screen.getByText("Daily Cleanup")).toBeInTheDocument();
      expect(screen.getByText("Manual Pipeline")).toBeInTheDocument();
    });

    it("shows trigger event type and pipeline", () => {
      renderPage();

      expect(
        screen.getByText(/New Measurement Set → Standard Imaging/)
      ).toBeInTheDocument();
      expect(screen.getByText(/Scheduled → Data Cleanup/)).toBeInTheDocument();
    });

    it("shows trigger status badges", () => {
      renderPage();

      const enabledBadges = screen.getAllByText("enabled");
      expect(enabledBadges.length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText("disabled")).toBeInTheDocument();
    });

    it("shows trigger conditions count", () => {
      renderPage();

      expect(screen.getByText(/1 rule/)).toBeInTheDocument();
    });

    it("shows schedule info for scheduled triggers", () => {
      renderPage();

      expect(screen.getByText(/Daily at midnight/)).toBeInTheDocument();
    });

    it("shows execution statistics", () => {
      renderPage();

      // Check for execution count
      expect(screen.getByText("150")).toBeInTheDocument();
      expect(screen.getByText("Executions")).toBeInTheDocument();
    });

    it("shows success rate", () => {
      renderPage();

      // 140/150 = 93%
      expect(screen.getByText("93%")).toBeInTheDocument();
    });

    it("shows empty state when no triggers", () => {
      mockUseTriggers.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      renderPage();

      expect(screen.getByText("No Triggers Yet")).toBeInTheDocument();
    });

    it("shows loading skeleton when loading", () => {
      mockUseTriggers.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      renderPage();

      const loadingElements = document.querySelectorAll(".animate-pulse");
      expect(loadingElements.length).toBeGreaterThan(0);
    });

    it("shows error message on failure", () => {
      mockUseTriggers.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error("API error"),
      });

      renderPage();

      expect(screen.getByText(/failed to load triggers/i)).toBeInTheDocument();
    });
  });

  describe("Trigger Actions", () => {
    it("shows run now button for enabled triggers", () => {
      renderPage();

      const runButtons = screen.getAllByRole("button", { name: /run now/i });
      expect(runButtons.length).toBeGreaterThanOrEqual(2);
    });

    it("disables run now button for disabled triggers", () => {
      renderPage();

      const runButtons = screen.getAllByRole("button", { name: /run now/i });
      // The third trigger is disabled, so its Run Now button should be disabled
      const disabledButton = runButtons.find((btn) =>
        btn.hasAttribute("disabled")
      );
      expect(disabledButton).toBeDefined();
    });

    it("calls execute mutation when run now clicked", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue(mockExecutions[0]);
      mockUseExecuteTrigger.mockReturnValue({
        mutateAsync,
        isPending: false,
      });

      renderPage();

      const runButtons = screen.getAllByRole("button", { name: /run now/i });
      await user.click(runButtons[0]);

      expect(mutateAsync).toHaveBeenCalledWith({ id: "trigger-1" });
    });

    it("calls toggle mutation when toggle switch clicked", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue(mockTriggers[0]);
      mockUseToggleTrigger.mockReturnValue({
        mutateAsync,
        isPending: false,
      });

      renderPage();

      const toggles = screen.getAllByRole("checkbox");
      await user.click(toggles[0]);

      expect(mutateAsync).toHaveBeenCalledWith({
        id: "trigger-1",
        enabled: false,
      });
    });

    it("calls delete mutation when delete clicked and confirmed", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue("trigger-1");
      mockUseDeleteTrigger.mockReturnValue({
        mutateAsync,
        isPending: false,
      });

      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      renderPage();

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      await user.click(deleteButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();
      expect(mutateAsync).toHaveBeenCalledWith("trigger-1");

      confirmSpy.mockRestore();
    });
  });

  describe("Create Trigger Modal", () => {
    it("opens modal when create button clicked", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create trigger/i }));

      expect(
        screen.getByRole("heading", { name: /create pipeline trigger/i })
      ).toBeInTheDocument();
    });

    it("shows trigger name input", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create trigger/i }));

      expect(screen.getByLabelText(/trigger name/i)).toBeInTheDocument();
    });

    it("shows event type selector", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create trigger/i }));

      expect(screen.getByLabelText(/trigger event/i)).toBeInTheDocument();
    });

    it("shows pipeline selector", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create trigger/i }));

      expect(screen.getByLabelText(/pipeline to execute/i)).toBeInTheDocument();
    });

    it("shows schedule options when schedule event selected", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create trigger/i }));

      const eventSelect = screen.getByLabelText(/trigger event/i);
      await user.selectOptions(eventSelect, "schedule");

      expect(screen.getByLabelText(/cron expression/i)).toBeInTheDocument();
    });

    it("allows adding conditions", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create trigger/i }));
      await user.click(screen.getByRole("button", { name: /add condition/i }));

      // Check for condition inputs
      expect(screen.getByPlaceholderText("Field")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Value")).toBeInTheDocument();
    });

    it("submits create request", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue(mockTriggers[0]);
      mockUseCreateTrigger.mockReturnValue({
        mutateAsync,
        isPending: false,
        isError: false,
      });

      renderPage();

      await user.click(screen.getByRole("button", { name: /create trigger/i }));

      // Fill in required fields
      await user.type(screen.getByLabelText(/trigger name/i), "Test Trigger");
      await user.selectOptions(
        screen.getByLabelText(/pipeline to execute/i),
        "pipeline-1"
      );

      // Find and click the submit button (second "Create Trigger" button)
      const buttons = screen.getAllByRole("button", {
        name: /create trigger/i,
      });
      await user.click(buttons[buttons.length - 1]);

      await waitFor(() => {
        expect(mutateAsync).toHaveBeenCalled();
      });
    });

    it("closes modal on cancel", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create trigger/i }));
      await user.click(screen.getByRole("button", { name: /cancel/i }));

      await waitFor(() => {
        expect(
          screen.queryByRole("heading", { name: /create pipeline trigger/i })
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("Execution History", () => {
    it("shows recent executions panel", () => {
      renderPage();

      expect(screen.getByText("Recent Executions")).toBeInTheDocument();
    });

    it("shows execution entries", () => {
      renderPage();

      // Check for trigger names in execution history
      const autoProcessEntries = screen.getAllByText("Auto Process MS");
      expect(autoProcessEntries.length).toBeGreaterThanOrEqual(1);
    });

    it("shows execution status", () => {
      renderPage();

      expect(screen.getByText("success")).toBeInTheDocument();
      expect(screen.getAllByText("running").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("failed")).toBeInTheDocument();
    });

    it("shows error message for failed executions", () => {
      renderPage();

      expect(screen.getByText("Pipeline timeout")).toBeInTheDocument();
    });

    it("shows view job link for completed executions", () => {
      renderPage();

      expect(screen.getByText("View Job →")).toBeInTheDocument();
    });

    it("shows empty state when no executions", () => {
      mockUseRecentExecutions.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      renderPage();

      expect(screen.getByText("No recent executions")).toBeInTheDocument();
    });
  });

  describe("Filters", () => {
    it("shows event type filter", () => {
      renderPage();

      expect(
        screen.getByLabelText(/filter by event type/i)
      ).toBeInTheDocument();
    });

    it("shows status filter", () => {
      renderPage();

      expect(screen.getByLabelText(/filter by status/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has accessible page heading", () => {
      renderPage();

      expect(
        screen.getByRole("heading", { level: 1, name: /pipeline triggers/i })
      ).toBeInTheDocument();
    });

    it("has labeled toggle switches", () => {
      renderPage();

      const toggles = screen.getAllByRole("checkbox");
      toggles.forEach((toggle) => {
        expect(toggle).toHaveAccessibleName();
      });
    });

    it("has labeled form fields in modal", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create trigger/i }));

      expect(screen.getByLabelText(/trigger name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/trigger event/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/pipeline to execute/i)).toBeInTheDocument();
    });
  });
});
