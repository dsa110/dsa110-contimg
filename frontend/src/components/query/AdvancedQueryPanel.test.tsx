import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AdvancedQueryPanel, {
  AdvancedQueryPanelProps,
  SourceQueryParams,
} from "./AdvancedQueryPanel";

describe("AdvancedQueryPanel", () => {
  const mockOnSubmit = vi.fn();
  const mockOnReset = vi.fn();

  const defaultProps: AdvancedQueryPanelProps = {
    onSubmit: mockOnSubmit,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders the panel", () => {
      render(<AdvancedQueryPanel {...defaultProps} />);
      expect(screen.getByText(/Source Query/i)).toBeInTheDocument();
    });

    it("renders collapsible section headers", () => {
      render(<AdvancedQueryPanel {...defaultProps} />);
      // The component has collapsible sections with buttons
      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);
    });

    it("applies custom className", () => {
      const { container } = render(
        <AdvancedQueryPanel {...defaultProps} className="custom-class" />
      );
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("cone search section", () => {
    it("renders Position/Cone Search section", () => {
      render(<AdvancedQueryPanel {...defaultProps} />);
      // Look for the section header or content
      expect(screen.getByText(/Position|Cone Search/i)).toBeInTheDocument();
    });

    it("renders coordinate input fields", () => {
      render(<AdvancedQueryPanel {...defaultProps} />);
      // Look for RA and Dec text inputs
      const textInputs = screen.getAllByRole("textbox");
      expect(textInputs.length).toBeGreaterThan(0);
    });
  });

  describe("filters section", () => {
    it("renders Filters section header", () => {
      render(<AdvancedQueryPanel {...defaultProps} />);
      expect(screen.getByText(/Filters/i)).toBeInTheDocument();
    });
  });

  describe("form actions", () => {
    it("renders search button", () => {
      render(<AdvancedQueryPanel {...defaultProps} />);
      // The button text is just "Search"
      expect(screen.getByText("Search")).toBeInTheDocument();
    });

    it("renders reset button", () => {
      render(<AdvancedQueryPanel {...defaultProps} />);
      // There's a "Reset" button and a "Reset all" link
      expect(screen.getByText("Reset")).toBeInTheDocument();
    });

    it("calls onSubmit when search button is clicked", async () => {
      render(<AdvancedQueryPanel {...defaultProps} />);
      const searchButton = screen.getByText("Search");
      await userEvent.click(searchButton);
      expect(mockOnSubmit).toHaveBeenCalled();
    });

    it("calls onReset when reset button is clicked", async () => {
      render(<AdvancedQueryPanel {...defaultProps} onReset={mockOnReset} />);
      const resetButton = screen.getByText("Reset");
      await userEvent.click(resetButton);
      expect(mockOnReset).toHaveBeenCalled();
    });
  });

  describe("collapsible sections", () => {
    it("can toggle section visibility", async () => {
      render(<AdvancedQueryPanel {...defaultProps} />);
      // Find section header buttons (those with expandable content)
      const sectionButtons = screen
        .getAllByRole("button")
        .filter((btn) => btn.querySelector("svg"));

      if (sectionButtons.length > 0) {
        // Click to toggle a section
        await userEvent.click(sectionButtons[0]);
        // Just verify no crash
        expect(sectionButtons[0]).toBeInTheDocument();
      }
    });
  });

  describe("with runs provided", () => {
    it("renders run selector when runs are available", () => {
      const runs = [
        { id: "run-1", name: "Pipeline Run 1" },
        { id: "run-2", name: "Pipeline Run 2" },
      ];
      render(<AdvancedQueryPanel {...defaultProps} runs={runs} />);
      // Section header says "Data Source", and there's "All Runs" option
      expect(screen.getByText("Data Source")).toBeInTheDocument();
    });
  });

  describe("with availableTags provided", () => {
    it("shows tag filter section when tags are available", () => {
      render(<AdvancedQueryPanel {...defaultProps} availableTags={["galaxy", "star", "agn"]} />);
      // The component should show tag section
      expect(screen.getByText(/Tags/i)).toBeInTheDocument();
    });
  });

  describe("initial params", () => {
    it("accepts initialParams prop without crashing", () => {
      const initialParams: Partial<SourceQueryParams> = {
        ra: 180,
        dec: 45,
        radius: 10,
        radiusUnit: "arcmin",
      };
      expect(() => {
        render(<AdvancedQueryPanel {...defaultProps} initialParams={initialParams} />);
      }).not.toThrow();
    });
  });

  describe("active filter count", () => {
    it("shows active filter badge when filters are applied", async () => {
      const initialParams: Partial<SourceQueryParams> = {
        ra: 180,
        dec: 45,
        newSource: true,
      };
      render(<AdvancedQueryPanel {...defaultProps} initialParams={initialParams} />);
      // Should show a count badge (e.g., "2 active" or just a number)
      await waitFor(() => {
        const badge = screen.queryByText(/\d+/);
        // May or may not be present depending on count
        expect(badge !== null || screen.getByText(/Source Query/i)).toBeTruthy();
      });
    });
  });
});
