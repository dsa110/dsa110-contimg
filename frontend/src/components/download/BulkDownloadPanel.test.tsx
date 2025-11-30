import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BulkDownloadPanel, { DownloadItem } from "./BulkDownloadPanel";

describe("BulkDownloadPanel", () => {
  const mockOnSelectionChange = vi.fn();
  const mockOnDownload = vi.fn();

  const mockItems: DownloadItem[] = [
    { id: "1", name: "Image 1", type: "fits" },
    { id: "2", name: "Image 2", type: "fits" },
    { id: "3", name: "Image 3", type: "fits" },
  ];

  const defaultProps = {
    items: mockItems,
    selectedIds: [],
    onSelectionChange: mockOnSelectionChange,
    onDownload: mockOnDownload,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnDownload.mockResolvedValue(undefined);
  });

  describe("rendering", () => {
    it("renders panel header", () => {
      render(<BulkDownloadPanel {...defaultProps} />);
      expect(screen.getByText("Bulk Download")).toBeInTheDocument();
    });

    it("shows selection count", () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1", "2"]} />);
      expect(screen.getByText("2 of 3 selected")).toBeInTheDocument();
    });

    it("shows format options", () => {
      render(<BulkDownloadPanel {...defaultProps} />);
      expect(screen.getByText("FITS")).toBeInTheDocument();
      expect(screen.getByText("CSV")).toBeInTheDocument();
      expect(screen.getByText("JSON")).toBeInTheDocument();
      expect(screen.getByText("ZIP Archive")).toBeInTheDocument();
    });
  });

  describe("Select All", () => {
    it("selects all items when checkbox clicked", async () => {
      render(<BulkDownloadPanel {...defaultProps} />);
      const selectAll = screen.getByLabelText(/select all/i);
      await userEvent.click(selectAll);
      expect(mockOnSelectionChange).toHaveBeenCalledWith(["1", "2", "3"]);
    });

    it("deselects all when all are selected", async () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1", "2", "3"]} />);
      const selectAll = screen.getByLabelText(/select all/i);
      await userEvent.click(selectAll);
      expect(mockOnSelectionChange).toHaveBeenCalledWith([]);
    });

    it("is disabled when no items", () => {
      render(<BulkDownloadPanel {...defaultProps} items={[]} />);
      const selectAll = screen.getByRole("checkbox");
      expect(selectAll).toBeDisabled();
    });
  });

  describe("Clear selection", () => {
    it("shows clear button when items selected", () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1"]} />);
      expect(screen.getByText(/clear selection/i)).toBeInTheDocument();
    });

    it("hides clear button when nothing selected", () => {
      render(<BulkDownloadPanel {...defaultProps} />);
      expect(screen.queryByText(/clear selection/i)).not.toBeInTheDocument();
    });

    it("clears selection when clicked", async () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1", "2"]} />);
      await userEvent.click(screen.getByText(/clear selection/i));
      expect(mockOnSelectionChange).toHaveBeenCalledWith([]);
    });
  });

  describe("format selection", () => {
    it("defaults to FITS format", () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1"]} />);
      const downloadBtn = screen.getByRole("button", { name: /download.*fits/i });
      expect(downloadBtn).toBeInTheDocument();
    });

    it("changes format when option clicked", async () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1"]} />);
      await userEvent.click(screen.getByText("CSV"));
      expect(screen.getByRole("button", { name: /download.*csv/i })).toBeInTheDocument();
    });

    it("shows format description", () => {
      render(<BulkDownloadPanel {...defaultProps} />);
      expect(screen.getByText(/download raw fits files/i)).toBeInTheDocument();
    });
  });

  describe("download button", () => {
    it("is disabled when nothing selected", () => {
      render(<BulkDownloadPanel {...defaultProps} />);
      const downloadBtn = screen.getByRole("button", { name: /download 0 items/i });
      expect(downloadBtn).toBeDisabled();
    });

    it("shows correct count in button", () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1", "2"]} />);
      expect(screen.getByRole("button", { name: /download 2 items/i })).toBeInTheDocument();
    });

    it("shows singular when one item selected", () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1"]} />);
      expect(screen.getByRole("button", { name: /download 1 item /i })).toBeInTheDocument();
    });

    it("calls onDownload with selected IDs and format", async () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1", "2"]} />);
      await userEvent.click(screen.getByRole("button", { name: /download/i }));
      expect(mockOnDownload).toHaveBeenCalledWith(["1", "2"], "fits");
    });

    it("shows loading state while downloading", async () => {
      mockOnDownload.mockImplementation(() => new Promise(() => {})); // Never resolves
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1"]} />);
      await userEvent.click(screen.getByRole("button", { name: /download/i }));
      expect(screen.getByText(/preparing download/i)).toBeInTheDocument();
    });
  });

  describe("selected items preview", () => {
    it("shows selected item names", () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1", "2"]} />);
      expect(screen.getByText("Image 1")).toBeInTheDocument();
      expect(screen.getByText("Image 2")).toBeInTheDocument();
    });

    it("shows truncated list for many items", () => {
      const manyItems = Array.from({ length: 15 }, (_, i) => ({
        id: String(i),
        name: `Item ${i}`,
        type: "fits",
      }));
      const allIds = manyItems.map((i) => i.id);
      render(
        <BulkDownloadPanel
          items={manyItems}
          selectedIds={allIds}
          onSelectionChange={mockOnSelectionChange}
          onDownload={mockOnDownload}
        />
      );
      expect(screen.getByText(/\+5 more/i)).toBeInTheDocument();
    });

    it("allows removing items from selection", async () => {
      render(<BulkDownloadPanel {...defaultProps} selectedIds={["1", "2"]} />);
      const removeButtons = screen.getAllByText("×");
      await userEvent.click(removeButtons[0]);
      expect(mockOnSelectionChange).toHaveBeenCalledWith(["2"]);
    });
  });

  describe("disabled state", () => {
    it("disables all controls when disabled", () => {
      render(<BulkDownloadPanel {...defaultProps} disabled />);
      expect(screen.getByRole("checkbox")).toBeDisabled();
      expect(screen.getByRole("button", { name: /download/i })).toBeDisabled();
    });
  });

  describe("custom className", () => {
    it("applies custom className", () => {
      const { container } = render(
        <BulkDownloadPanel {...defaultProps} className="custom-class" />
      );
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });
});
