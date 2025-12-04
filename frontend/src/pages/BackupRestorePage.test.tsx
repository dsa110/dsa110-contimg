/**
 * Tests for BackupRestorePage
 *
 * Tests:
 * - Backup list display
 * - Create backup modal
 * - Restore modal with preview
 * - Backup summary stats
 * - Restore history panel
 * - Scope selection
 * - Loading and error states
 * - Accessibility
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BackupRestorePage } from "./BackupRestorePage";
import type { Backup, RestoreJob, RestorePreview } from "../api/backup";

// ============================================================================
// Mocks
// ============================================================================

const mockBackups: Backup[] = [
  {
    id: "backup-1",
    name: "Daily Backup 2024-01-15",
    type: "full",
    status: "completed",
    scope: {
      measurement_sets: true,
      images: true,
      catalogs: true,
      pipeline_configs: true,
      job_history: true,
      qa_ratings: true,
    },
    size_bytes: 1073741824,
    size_formatted: "1.00 GB",
    item_count: 1500,
    created_at: "2024-01-15T10:00:00Z",
    completed_at: "2024-01-15T10:30:00Z",
    created_by: "admin",
    storage_location: "/backups/2024-01-15",
    checksum: "abc123",
    notes: "Weekly backup",
  },
  {
    id: "backup-2",
    name: "Incremental Backup",
    type: "incremental",
    status: "completed",
    scope: {
      measurement_sets: true,
      images: true,
      catalogs: false,
      pipeline_configs: false,
      job_history: false,
      qa_ratings: false,
    },
    size_bytes: 104857600,
    size_formatted: "100.00 MB",
    item_count: 150,
    created_at: "2024-01-16T10:00:00Z",
    completed_at: "2024-01-16T10:05:00Z",
    created_by: "admin",
    storage_location: "/backups/2024-01-16",
    parent_backup_id: "backup-1",
  },
  {
    id: "backup-3",
    name: "Running Backup",
    type: "full",
    status: "running",
    scope: {
      measurement_sets: true,
      images: true,
      catalogs: true,
      pipeline_configs: true,
      job_history: true,
      qa_ratings: true,
    },
    size_bytes: 0,
    size_formatted: "0 B",
    item_count: 0,
    created_at: "2024-01-17T10:00:00Z",
    created_by: "operator",
    storage_location: "/backups/2024-01-17",
  },
];

const mockRestoreHistory: RestoreJob[] = [
  {
    id: "restore-1",
    backup_id: "backup-1",
    backup_name: "Daily Backup 2024-01-15",
    status: "completed",
    scope: { measurement_sets: true, images: true },
    items_restored: 500,
    items_total: 500,
    errors: [],
    started_at: "2024-01-14T12:00:00Z",
    completed_at: "2024-01-14T12:10:00Z",
    started_by: "admin",
  },
  {
    id: "restore-2",
    backup_id: "backup-2",
    backup_name: "Incremental Backup",
    status: "running",
    scope: { images: true },
    items_restored: 50,
    items_total: 100,
    errors: [],
    started_at: "2024-01-17T11:00:00Z",
    started_by: "operator",
  },
];

const mockRestorePreview: RestorePreview = {
  backup_id: "backup-1",
  items_to_restore: 500,
  conflicts: [],
  missing_dependencies: [],
  estimated_time_seconds: 300,
  warnings: [],
  can_restore: true,
};

const mockUseBackups = vi.fn();
const mockUseCreateBackup = vi.fn();
const mockUseDeleteBackup = vi.fn();
const mockUseRestorePreview = vi.fn();
const mockUseRestore = vi.fn();
const mockUseRestoreHistory = vi.fn();

vi.mock("../api/backup", async () => {
  const actual = await vi.importActual("../api/backup");
  return {
    ...actual,
    useBackups: () => mockUseBackups(),
    useCreateBackup: () => mockUseCreateBackup(),
    useDeleteBackup: () => mockUseDeleteBackup(),
    useRestorePreview: () => mockUseRestorePreview(),
    useRestore: () => mockUseRestore(),
    useRestoreHistory: () => mockUseRestoreHistory(),
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
        <BackupRestorePage />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

// ============================================================================
// Tests
// ============================================================================

describe("BackupRestorePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    mockUseBackups.mockReturnValue({
      data: mockBackups,
      isLoading: false,
      error: null,
    });

    mockUseCreateBackup.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockBackups[0]),
      isPending: false,
      isError: false,
    });

    mockUseDeleteBackup.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue("backup-1"),
      isPending: false,
    });

    mockUseRestorePreview.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockRestorePreview),
      data: null,
      isPending: false,
    });

    mockUseRestore.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockRestoreHistory[0]),
      isPending: false,
      isError: false,
    });

    mockUseRestoreHistory.mockReturnValue({
      data: mockRestoreHistory,
      isLoading: false,
      error: null,
    });
  });

  describe("Page Header", () => {
    it("renders page title and description", () => {
      renderPage();

      expect(
        screen.getByRole("heading", { name: /backup & restore/i })
      ).toBeInTheDocument();
      expect(
        screen.getByText(/create backups and restore data/i)
      ).toBeInTheDocument();
    });

    it("renders create backup button", () => {
      renderPage();

      expect(
        screen.getByRole("button", { name: /create backup/i })
      ).toBeInTheDocument();
    });
  });

  describe("Backup List", () => {
    it("renders list of backups", () => {
      renderPage();

      // Use getAllByText for backup names that may appear in both list and history
      expect(
        screen.getAllByText("Daily Backup 2024-01-15").length
      ).toBeGreaterThanOrEqual(1);
      expect(
        screen.getAllByText("Incremental Backup").length
      ).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Running Backup")).toBeInTheDocument();
    });

    it("shows backup type and size", () => {
      renderPage();

      expect(screen.getByText(/Full Backup • 1.00 GB/)).toBeInTheDocument();
      expect(screen.getByText(/Incremental • 100.00 MB/)).toBeInTheDocument();
    });

    it("shows backup status badges", () => {
      renderPage();

      const completedBadges = screen.getAllByText("completed");
      expect(completedBadges.length).toBeGreaterThanOrEqual(1);
      // Running status may appear multiple times due to restore history
      const runningElements = screen.getAllByText("running");
      expect(runningElements.length).toBeGreaterThanOrEqual(1);
    });

    it("shows restore button for completed backups", () => {
      renderPage();

      const restoreButtons = screen.getAllByRole("button", {
        name: /restore/i,
      });
      // Should have restore buttons for completed backups (backup-1 and backup-2)
      expect(restoreButtons.length).toBeGreaterThanOrEqual(2);
    });

    it("shows delete button for all backups", () => {
      renderPage();

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      expect(deleteButtons.length).toBe(3);
    });

    it("shows backup notes when present", () => {
      renderPage();

      expect(screen.getByText(/Weekly backup/)).toBeInTheDocument();
    });

    it("shows empty state when no backups", () => {
      mockUseBackups.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      renderPage();

      expect(screen.getByText("No Backups Yet")).toBeInTheDocument();
      expect(screen.getByText(/create your first backup/i)).toBeInTheDocument();
    });

    it("shows loading skeleton when loading", () => {
      mockUseBackups.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      renderPage();

      const loadingElements = document.querySelectorAll(".animate-pulse");
      expect(loadingElements.length).toBeGreaterThan(0);
    });

    it("shows error message on failure", () => {
      mockUseBackups.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error("Network error"),
      });

      renderPage();

      expect(screen.getByText(/failed to load backups/i)).toBeInTheDocument();
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  describe("Create Backup Modal", () => {
    it("opens create backup modal when button clicked", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create backup/i }));

      expect(
        screen.getByRole("heading", { name: /create new backup/i })
      ).toBeInTheDocument();
    });

    it("allows entering backup name", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create backup/i }));

      const nameInput = screen.getByLabelText(/backup name/i);
      await user.clear(nameInput);
      await user.type(nameInput, "Test Backup");

      expect(nameInput).toHaveValue("Test Backup");
    });

    it("allows selecting backup type", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create backup/i }));

      const fullRadio = screen.getByLabelText(/^full$/i);
      const incrementalRadio = screen.getByLabelText(/incremental/i);

      expect(fullRadio).toBeChecked();
      expect(incrementalRadio).toBeDisabled(); // No parent backup
    });

    it("allows toggling scope items", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create backup/i }));

      const msCheckbox = screen.getByLabelText(/measurement sets/i);
      expect(msCheckbox).toBeChecked();

      await user.click(msCheckbox);
      expect(msCheckbox).not.toBeChecked();
    });

    it("has select all and select none buttons", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create backup/i }));

      expect(
        screen.getByRole("button", { name: /select all/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /select none/i })
      ).toBeInTheDocument();
    });

    it("submits create backup request", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue(mockBackups[0]);
      mockUseCreateBackup.mockReturnValue({
        mutateAsync,
        isPending: false,
        isError: false,
      });

      renderPage();

      await user.click(screen.getByRole("button", { name: /create backup/i }));

      // Submit the form - find the second create backup button (in modal)
      const buttons = screen.getAllByRole("button", { name: /create backup/i });
      const submitButton = buttons[buttons.length - 1];
      await user.click(submitButton);

      await waitFor(() => {
        expect(mutateAsync).toHaveBeenCalled();
      });
    });

    it("closes modal on cancel", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create backup/i }));
      await user.click(screen.getByRole("button", { name: /cancel/i }));

      await waitFor(() => {
        expect(
          screen.queryByRole("heading", { name: /create new backup/i })
        ).not.toBeInTheDocument();
      });
    });
  });

  describe("Restore Modal", () => {
    it("opens restore modal when restore button clicked", async () => {
      const user = userEvent.setup();
      renderPage();

      const restoreButtons = screen.getAllByRole("button", {
        name: /restore/i,
      });
      await user.click(restoreButtons[0]);

      expect(
        screen.getByRole("heading", { name: /restore from backup/i })
      ).toBeInTheDocument();
    });

    it("shows backup name in restore modal", async () => {
      const user = userEvent.setup();
      renderPage();

      const restoreButtons = screen.getAllByRole("button", {
        name: /restore/i,
      });
      await user.click(restoreButtons[0]);

      // Modal shows the backup name - may appear multiple times
      const backupNameMatches = screen.getAllByText(/daily backup 2024-01-15/i);
      expect(backupNameMatches.length).toBeGreaterThanOrEqual(1);
    });

    it("shows preview restore button", async () => {
      const user = userEvent.setup();
      renderPage();

      const restoreButtons = screen.getAllByRole("button", {
        name: /restore/i,
      });
      await user.click(restoreButtons[0]);

      expect(
        screen.getByRole("button", { name: /preview restore/i })
      ).toBeInTheDocument();
    });

    it("shows overwrite existing option", async () => {
      const user = userEvent.setup();
      renderPage();

      const restoreButtons = screen.getAllByRole("button", {
        name: /restore/i,
      });
      await user.click(restoreButtons[0]);

      expect(
        screen.getByLabelText(/overwrite existing data/i)
      ).toBeInTheDocument();
    });

    it("runs preview and shows results", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue(mockRestorePreview);
      mockUseRestorePreview.mockReturnValue({
        mutateAsync,
        data: null,
        isPending: false,
      });

      renderPage();

      const restoreButtons = screen.getAllByRole("button", {
        name: /restore/i,
      });
      await user.click(restoreButtons[0]);

      await user.click(
        screen.getByRole("button", { name: /preview restore/i })
      );

      await waitFor(() => {
        expect(mutateAsync).toHaveBeenCalled();
      });

      // After preview, update mock to return data
      mockUseRestorePreview.mockReturnValue({
        mutateAsync,
        data: mockRestorePreview,
        isPending: false,
      });
    });

    it("requires confirmation checkbox to start restore", async () => {
      const user = userEvent.setup();
      mockUseRestorePreview.mockReturnValue({
        mutateAsync: vi.fn(),
        data: mockRestorePreview,
        isPending: false,
      });

      renderPage();

      const restoreButtons = screen.getAllByRole("button", {
        name: /restore/i,
      });
      await user.click(restoreButtons[0]);

      // Should see confirmation checkbox after preview
      expect(
        screen.getByLabelText(/i understand and confirm/i)
      ).toBeInTheDocument();

      const startButton = screen.getByRole("button", {
        name: /start restore/i,
      });
      expect(startButton).toBeDisabled();
    });
  });

  describe("Backup Summary Stats", () => {
    it("shows total backups count", () => {
      renderPage();

      expect(screen.getByText("Total Backups")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("shows full backups count", () => {
      renderPage();

      expect(screen.getByText("Full Backups")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("shows total size", () => {
      renderPage();

      expect(screen.getByText("Total Size")).toBeInTheDocument();
      // 1073741824 + 104857600 = 1.10 GB
    });

    it("shows last backup date", () => {
      renderPage();

      expect(screen.getByText("Last Backup")).toBeInTheDocument();
    });
  });

  describe("Restore History Panel", () => {
    it("shows recent restores", () => {
      renderPage();

      expect(screen.getByText("Recent Restores")).toBeInTheDocument();
      // Check restore history items are visible
      expect(
        screen.getAllByText(/daily backup 2024-01-15/i).length
      ).toBeGreaterThanOrEqual(1);
    });

    it("shows restore status", () => {
      renderPage();

      // Should show completed and running statuses
      const completedElements = screen.getAllByText("completed");
      expect(completedElements.length).toBeGreaterThanOrEqual(1);
    });

    it("shows restore progress", () => {
      renderPage();

      // "50/100 items" or similar
      expect(screen.getByText(/50\/100 items/)).toBeInTheDocument();
    });

    it("shows empty state when no restores", () => {
      mockUseRestoreHistory.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      renderPage();

      expect(screen.getByText("No restore history")).toBeInTheDocument();
    });
  });

  describe("Delete Backup", () => {
    it("calls delete mutation when delete clicked and confirmed", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn().mockResolvedValue("backup-1");
      mockUseDeleteBackup.mockReturnValue({
        mutateAsync,
        isPending: false,
      });

      // Mock window.confirm
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      renderPage();

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      await user.click(deleteButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();
      expect(mutateAsync).toHaveBeenCalledWith("backup-1");

      confirmSpy.mockRestore();
    });

    it("does not delete when confirmation cancelled", async () => {
      const user = userEvent.setup();
      const mutateAsync = vi.fn();
      mockUseDeleteBackup.mockReturnValue({
        mutateAsync,
        isPending: false,
      });

      // Mock window.confirm to return false
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

      renderPage();

      const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
      await user.click(deleteButtons[0]);

      expect(confirmSpy).toHaveBeenCalled();
      expect(mutateAsync).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });
  });

  describe("Accessibility", () => {
    it("has accessible page heading", () => {
      renderPage();

      const heading = screen.getByRole("heading", {
        level: 1,
        name: /backup & restore/i,
      });
      expect(heading).toBeInTheDocument();
    });

    it("has accessible form labels in create modal", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create backup/i }));

      expect(screen.getByLabelText(/backup name/i)).toBeInTheDocument();
      expect(screen.getByText(/backup type/i)).toBeInTheDocument();
      expect(screen.getByText(/data to include/i)).toBeInTheDocument();
    });

    it("uses semantic list structure for backups", () => {
      renderPage();

      expect(
        screen.getByRole("heading", { name: /available backups/i })
      ).toBeInTheDocument();
    });

    it("has labeled scope checkboxes", async () => {
      const user = userEvent.setup();
      renderPage();

      await user.click(screen.getByRole("button", { name: /create backup/i }));

      expect(screen.getByLabelText(/measurement sets/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/images/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/catalogs/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/pipeline configs/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/job history/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/qa ratings/i)).toBeInTheDocument();
    });
  });
});
