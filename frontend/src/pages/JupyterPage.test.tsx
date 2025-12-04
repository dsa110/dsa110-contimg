/**
 * Tests for JupyterPage
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import JupyterPage from "./JupyterPage";

// Mock the jupyter API hooks
const mockUseKernels = vi.fn();
const mockUseNotebooks = vi.fn();
const mockUseSessions = vi.fn();
const mockUseNotebookTemplates = vi.fn();
const mockUseJupyterStats = vi.fn();
const mockUseJupyterUrl = vi.fn();
const mockUseStartKernel = vi.fn();
const mockUseRestartKernel = vi.fn();
const mockUseInterruptKernel = vi.fn();
const mockUseShutdownKernel = vi.fn();
const mockUseDeleteNotebook = vi.fn();
const mockUseCreateSession = vi.fn();
const mockUseDeleteSession = vi.fn();
const mockUseLaunchNotebook = vi.fn();

vi.mock("../api/jupyter", () => ({
  useKernels: () => mockUseKernels(),
  useNotebooks: () => mockUseNotebooks(),
  useSessions: () => mockUseSessions(),
  useNotebookTemplates: () => mockUseNotebookTemplates(),
  useJupyterStats: () => mockUseJupyterStats(),
  useJupyterUrl: () => mockUseJupyterUrl(),
  useStartKernel: () => mockUseStartKernel(),
  useRestartKernel: () => mockUseRestartKernel(),
  useInterruptKernel: () => mockUseInterruptKernel(),
  useShutdownKernel: () => mockUseShutdownKernel(),
  useDeleteNotebook: () => mockUseDeleteNotebook(),
  useCreateSession: () => mockUseCreateSession(),
  useDeleteSession: () => mockUseDeleteSession(),
  useLaunchNotebook: () => mockUseLaunchNotebook(),
}));

// Mock data
const mockKernels = [
  {
    id: "kernel-1",
    name: "python3",
    display_name: "Python 3",
    language: "python",
    status: "idle" as const,
    last_activity: "2024-01-15T10:30:00Z",
    execution_count: 42,
    connections: 1,
  },
  {
    id: "kernel-2",
    name: "python3",
    display_name: "Python 3",
    language: "python",
    status: "busy" as const,
    last_activity: "2024-01-15T10:35:00Z",
    execution_count: 15,
    connections: 2,
  },
];

const mockNotebooks = [
  {
    id: "nb-1",
    name: "analysis.ipynb",
    path: "/notebooks/analysis.ipynb",
    type: "notebook" as const,
    created: "2024-01-10T08:00:00Z",
    last_modified: "2024-01-15T09:00:00Z",
    size: 15360,
    kernel_id: "kernel-1",
  },
  {
    id: "nb-2",
    name: "exploration.ipynb",
    path: "/notebooks/exploration.ipynb",
    type: "notebook" as const,
    created: "2024-01-12T14:00:00Z",
    last_modified: "2024-01-14T16:00:00Z",
    size: 8192,
  },
];

const mockSessions = [
  {
    id: "session-1",
    notebook: {
      name: "analysis.ipynb",
      path: "/notebooks/analysis.ipynb",
    },
    kernel: mockKernels[0],
    created: "2024-01-15T10:00:00Z",
  },
];

const mockTemplates = [
  {
    id: "tmpl-1",
    name: "Source Analysis",
    description: "Analyze a radio source from the catalog",
    category: "source_analysis" as const,
    parameters: [
      {
        name: "source_id",
        type: "source_id" as const,
        required: true,
        description: "The ID of the source to analyze",
      },
    ],
  },
  {
    id: "tmpl-2",
    name: "Image Inspection",
    description: "Inspect FITS image data",
    category: "image_inspection" as const,
    parameters: [
      {
        name: "image_id",
        type: "image_id" as const,
        required: true,
        description: "The ID of the image to inspect",
      },
    ],
  },
];

const mockStats = {
  total_notebooks: 10,
  active_kernels: 2,
  total_sessions: 3,
  kernel_usage: {
    python3: 2,
  },
  disk_usage_mb: 150,
  max_disk_mb: 500,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <JupyterPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe("JupyterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Set up default mock returns
    mockUseKernels.mockReturnValue({
      data: mockKernels,
      isPending: false,
      error: null,
    });
    mockUseNotebooks.mockReturnValue({
      data: mockNotebooks,
      isPending: false,
      error: null,
    });
    mockUseSessions.mockReturnValue({
      data: mockSessions,
      isPending: false,
      error: null,
    });
    mockUseNotebookTemplates.mockReturnValue({
      data: mockTemplates,
      isPending: false,
      error: null,
    });
    mockUseJupyterStats.mockReturnValue({
      data: mockStats,
      isPending: false,
      error: null,
    });
    mockUseJupyterUrl.mockReturnValue({
      data: "http://localhost:8888",
      isPending: false,
      error: null,
    });
    mockUseStartKernel.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    mockUseRestartKernel.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
    mockUseInterruptKernel.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
    mockUseShutdownKernel.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
    mockUseDeleteNotebook.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
    mockUseCreateSession.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    mockUseDeleteSession.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
    mockUseLaunchNotebook.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
  });

  describe("Page Layout", () => {
    it("renders page title", () => {
      renderPage();

      expect(screen.getByText("Jupyter Integration")).toBeInTheDocument();
      expect(
        screen.getByText("Manage notebooks and kernels for data analysis")
      ).toBeInTheDocument();
    });

    it("renders page icon", () => {
      renderPage();

      expect(screen.getByText("🪐")).toBeInTheDocument();
    });

    it("renders Start Kernel button", () => {
      renderPage();

      expect(
        screen.getByRole("button", { name: /start kernel/i })
      ).toBeInTheDocument();
    });

    it("renders Open JupyterLab button", () => {
      renderPage();

      const openButtons = screen.getAllByRole("button", {
        name: /open jupyterlab/i,
      });
      expect(openButtons.length).toBeGreaterThanOrEqual(1);
    });

    it("renders tab buttons", () => {
      renderPage();

      expect(
        screen.getByRole("button", { name: /kernels/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /notebooks/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /sessions/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /templates/i })
      ).toBeInTheDocument();
    });
  });

  describe("Kernels Tab", () => {
    it("shows kernels list by default", () => {
      renderPage();

      // Python 3 appears multiple times (one per kernel)
      const python3Elements = screen.getAllByText("Python 3");
      expect(python3Elements.length).toBeGreaterThanOrEqual(1);
    });

    it("shows kernel status badges", () => {
      renderPage();

      expect(screen.getByText("idle")).toBeInTheDocument();
      expect(screen.getByText("busy")).toBeInTheDocument();
    });

    it("shows kernel execution count", () => {
      renderPage();

      expect(screen.getByText("42")).toBeInTheDocument();
    });

    it("shows restart button for each kernel", () => {
      renderPage();

      const restartButtons = screen.getAllByRole("button", {
        name: /restart/i,
      });
      expect(restartButtons.length).toBeGreaterThanOrEqual(2);
    });

    it("shows shutdown button for each kernel", () => {
      renderPage();

      const shutdownButtons = screen.getAllByRole("button", {
        name: /shutdown/i,
      });
      expect(shutdownButtons.length).toBeGreaterThanOrEqual(2);
    });

    it("shows interrupt button for busy kernels", () => {
      renderPage();

      expect(
        screen.getByRole("button", { name: /interrupt/i })
      ).toBeInTheDocument();
    });

    it("restarts kernel on button click", async () => {
      const user = userEvent.setup();
      const restartMutate = vi.fn();
      mockUseRestartKernel.mockReturnValue({
        mutate: restartMutate,
        isPending: false,
      });

      renderPage();

      const restartButtons = screen.getAllByRole("button", {
        name: /restart/i,
      });
      await user.click(restartButtons[0]);

      expect(restartMutate).toHaveBeenCalledWith("kernel-1");
    });

    it("shuts down kernel on button click", async () => {
      const user = userEvent.setup();
      const shutdownMutate = vi.fn();
      mockUseShutdownKernel.mockReturnValue({
        mutate: shutdownMutate,
        isPending: false,
      });

      renderPage();

      const shutdownButtons = screen.getAllByRole("button", {
        name: /shutdown/i,
      });
      await user.click(shutdownButtons[0]);

      expect(shutdownMutate).toHaveBeenCalledWith("kernel-1");
    });

    it("shows loading state", () => {
      mockUseKernels.mockReturnValue({
        data: undefined,
        isPending: true,
        error: null,
      });

      renderPage();

      expect(screen.getByText("Loading kernels...")).toBeInTheDocument();
    });

    it("shows error state", () => {
      mockUseKernels.mockReturnValue({
        data: undefined,
        isPending: false,
        error: new Error("Failed"),
      });

      renderPage();

      expect(screen.getByText("Error loading kernels")).toBeInTheDocument();
    });

    it("shows empty state", () => {
      mockUseKernels.mockReturnValue({
        data: [],
        isPending: false,
        error: null,
      });

      renderPage();

      expect(
        screen.getByText("No active kernels. Start one to begin.")
      ).toBeInTheDocument();
    });
  });

  describe("Notebooks Tab", () => {
    it("switches to notebooks tab", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /notebooks/i }));

      expect(screen.getByText("analysis.ipynb")).toBeInTheDocument();
      expect(screen.getByText("exploration.ipynb")).toBeInTheDocument();
    });

    it("shows notebook path", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /notebooks/i }));

      expect(screen.getByText("/notebooks/analysis.ipynb")).toBeInTheDocument();
    });

    it("shows active badge for notebook with kernel", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /notebooks/i }));

      expect(screen.getByText("Active")).toBeInTheDocument();
    });

    it("shows open button for notebooks", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /notebooks/i }));

      const openButtons = screen.getAllByRole("button", { name: /^open$/i });
      expect(openButtons.length).toBeGreaterThanOrEqual(2);
    });

    it("shows delete button for notebooks", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /notebooks/i }));

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      expect(deleteButtons.length).toBeGreaterThanOrEqual(2);
    });

    it("deletes notebook on button click", async () => {
      const user = userEvent.setup();
      const deleteMutate = vi.fn();
      mockUseDeleteNotebook.mockReturnValue({
        mutate: deleteMutate,
        isPending: false,
      });

      renderPage();

      await user.click(screen.getByRole("button", { name: /notebooks/i }));

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      await user.click(deleteButtons[0]);

      expect(deleteMutate).toHaveBeenCalledWith("nb-1");
    });
  });

  describe("Sessions Tab", () => {
    it("switches to sessions tab", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /sessions/i }));

      expect(screen.getByText("analysis.ipynb")).toBeInTheDocument();
    });

    it("shows session kernel info", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /sessions/i }));

      expect(screen.getByText("Python 3")).toBeInTheDocument();
    });

    it("shows close button for sessions", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /sessions/i }));

      expect(
        screen.getByRole("button", { name: /close/i })
      ).toBeInTheDocument();
    });

    it("closes session on button click", async () => {
      const user = userEvent.setup();
      const deleteMutate = vi.fn();
      mockUseDeleteSession.mockReturnValue({
        mutate: deleteMutate,
        isPending: false,
      });

      renderPage();

      await user.click(screen.getByRole("button", { name: /sessions/i }));
      await user.click(screen.getByRole("button", { name: /close/i }));

      expect(deleteMutate).toHaveBeenCalledWith("session-1");
    });
  });

  describe("Templates Tab", () => {
    it("switches to templates tab", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /templates/i }));

      expect(screen.getByText("Source Analysis")).toBeInTheDocument();
      expect(screen.getByText("Image Inspection")).toBeInTheDocument();
    });

    it("shows template descriptions", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /templates/i }));

      expect(
        screen.getByText("Analyze a radio source from the catalog")
      ).toBeInTheDocument();
    });

    it("shows parameter count", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /templates/i }));

      const parameterTexts = screen.getAllByText("1 parameter required");
      expect(parameterTexts.length).toBeGreaterThanOrEqual(2);
    });

    it("shows launch button for templates", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /templates/i }));

      const launchButtons = screen.getAllByRole("button", {
        name: /launch notebook/i,
      });
      expect(launchButtons.length).toBeGreaterThanOrEqual(2);
    });

    it("opens launch modal on button click", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /templates/i }));

      const launchButtons = screen.getAllByRole("button", {
        name: /launch notebook/i,
      });
      await user.click(launchButtons[0]);

      expect(screen.getByText("Launch Source Analysis")).toBeInTheDocument();
    });
  });

  describe("Start Kernel Modal", () => {
    it("opens start kernel modal", async () => {
      const user = userEvent.setup();
      renderPage();

      // Get header "Start Kernel" button (first one)
      const startButtons = screen.getAllByRole("button", {
        name: /start kernel/i,
      });
      await user.click(startButtons[0]);

      expect(screen.getByText("Start New Kernel")).toBeInTheDocument();
    });

    it("shows kernel type selector", async () => {
      const user = userEvent.setup();
      renderPage();

      const startButtons = screen.getAllByRole("button", {
        name: /start kernel/i,
      });
      await user.click(startButtons[0]);

      expect(screen.getByLabelText(/kernel type/i)).toBeInTheDocument();
    });

    it("closes modal on cancel", async () => {
      const user = userEvent.setup();
      renderPage();

      const startButtons = screen.getAllByRole("button", {
        name: /start kernel/i,
      });
      await user.click(startButtons[0]);
      await user.click(screen.getByRole("button", { name: /cancel/i }));

      await waitFor(() => {
        expect(screen.queryByText("Start New Kernel")).not.toBeInTheDocument();
      });
    });

    it("starts kernel on submit", async () => {
      const user = userEvent.setup();
      const startMutateAsync = vi.fn().mockResolvedValue({});
      mockUseStartKernel.mockReturnValue({
        mutateAsync: startMutateAsync,
        isPending: false,
      });

      renderPage();

      const startButtons = screen.getAllByRole("button", {
        name: /start kernel/i,
      });
      await user.click(startButtons[0]);

      // Submit button in modal has exact text "Start Kernel"
      const submitButton = screen.getByRole("button", {
        name: /^start kernel$/i,
      });
      await user.click(submitButton);

      await waitFor(() => {
        expect(startMutateAsync).toHaveBeenCalledWith("python3");
      });
    });
  });

  describe("Launch Notebook Modal", () => {
    it("shows notebook name input", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /templates/i }));

      const launchButtons = screen.getAllByRole("button", {
        name: /launch notebook/i,
      });
      await user.click(launchButtons[0]);

      expect(screen.getByLabelText(/notebook name/i)).toBeInTheDocument();
    });

    it("shows parameter inputs", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /templates/i }));

      const launchButtons = screen.getAllByRole("button", {
        name: /launch notebook/i,
      });
      await user.click(launchButtons[0]);

      expect(
        screen.getByText("The ID of the source to analyze")
      ).toBeInTheDocument();
    });

    it("closes modal on cancel", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /templates/i }));

      const launchButtons = screen.getAllByRole("button", {
        name: /launch notebook/i,
      });
      await user.click(launchButtons[0]);
      await user.click(screen.getByRole("button", { name: /cancel/i }));

      await waitFor(() => {
        expect(
          screen.queryByText("Launch Source Analysis")
        ).not.toBeInTheDocument();
      });
    });

    it("launches notebook on submit", async () => {
      const user = userEvent.setup();
      const launchMutateAsync = vi.fn().mockResolvedValue({});
      mockUseLaunchNotebook.mockReturnValue({
        mutateAsync: launchMutateAsync,
        isPending: false,
      });

      renderPage();

      await user.click(screen.getByRole("button", { name: /templates/i }));

      const launchButtons = screen.getAllByRole("button", {
        name: /launch notebook/i,
      });
      await user.click(launchButtons[0]);

      // Fill in required parameter
      const paramInput = screen.getByRole("textbox", { name: /source_id/i });
      await user.type(paramInput, "src-123");

      await user.click(screen.getByRole("button", { name: /^launch$/i }));

      await waitFor(() => {
        expect(launchMutateAsync).toHaveBeenCalled();
      });
    });
  });

  describe("Statistics Panel", () => {
    it("shows statistics heading", () => {
      renderPage();

      expect(screen.getByText("Jupyter Statistics")).toBeInTheDocument();
    });

    it("shows total notebooks count", () => {
      renderPage();

      expect(screen.getByText("10")).toBeInTheDocument();
      expect(screen.getByText("Notebooks")).toBeInTheDocument();
    });

    it("shows active kernels count", () => {
      renderPage();

      // "2" appears multiple times (kernels, connections)
      const twoElements = screen.getAllByText("2");
      expect(twoElements.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Active Kernels")).toBeInTheDocument();
    });

    it("shows sessions count", () => {
      renderPage();

      expect(screen.getByText("3")).toBeInTheDocument();
      expect(screen.getByText("Sessions")).toBeInTheDocument();
    });

    it("shows disk usage", () => {
      renderPage();

      expect(screen.getByText("Disk Usage")).toBeInTheDocument();
      expect(screen.getByText("150 / 500 MB")).toBeInTheDocument();
    });
  });

  describe("Quick Actions", () => {
    it("shows quick actions panel", () => {
      renderPage();

      expect(screen.getByText("Quick Actions")).toBeInTheDocument();
    });

    it("shows open jupyterlab quick action", () => {
      renderPage();

      const openButtons = screen.getAllByText(/open jupyterlab/i);
      expect(openButtons.length).toBeGreaterThanOrEqual(1);
    });

    it("shows start new kernel quick action", () => {
      renderPage();

      const startButtons = screen.getAllByText(/start new kernel/i);
      expect(startButtons.length).toBeGreaterThanOrEqual(1);
    });

    it("shows create from template quick action", () => {
      renderPage();

      expect(screen.getByText(/create from template/i)).toBeInTheDocument();
    });
  });

  describe("Tips Panel", () => {
    it("shows tips heading", () => {
      renderPage();

      expect(screen.getByText("💡 Tips")).toBeInTheDocument();
    });

    it("shows usage tips", () => {
      renderPage();

      expect(
        screen.getByText(/use templates for source\/image analysis/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/idle kernels are automatically shut down/i)
      ).toBeInTheDocument();
    });
  });

  describe("Open JupyterLab", () => {
    it("opens JupyterLab in new window", async () => {
      const user = userEvent.setup();
      const windowOpenSpy = vi
        .spyOn(window, "open")
        .mockImplementation(() => null);

      renderPage();

      // Get first "Open JupyterLab" button (header button)
      const openButtons = screen.getAllByRole("button", {
        name: /open jupyterlab/i,
      });
      await user.click(openButtons[0]);

      expect(windowOpenSpy).toHaveBeenCalledWith(
        "http://localhost:8888",
        "_blank"
      );

      windowOpenSpy.mockRestore();
    });

    it("disables button when URL not available", () => {
      mockUseJupyterUrl.mockReturnValue({
        data: undefined,
        isPending: false,
        error: null,
      });

      renderPage();

      const openButtons = screen.getAllByRole("button", {
        name: /open jupyterlab/i,
      });
      expect(openButtons[0]).toBeDisabled();
    });
  });
});
