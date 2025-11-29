import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FilterPanel, { FilterConfig } from "./FilterPanel";

// Mock RangeSlider since it has complex internals
vi.mock("../widgets", () => ({
  RangeSlider: ({
    label,
    min,
    max,
    minValue,
    maxValue,
    onChange,
  }: {
    label?: string;
    min: number;
    max: number;
    minValue: number;
    maxValue: number;
    onChange: (min: number, max: number) => void;
  }) => (
    <div data-testid={`range-slider-${label}`}>
      <span data-testid="range-label">{label}</span>
      <button data-testid="range-change" onClick={() => onChange(minValue + 1, maxValue - 1)}>
        Change Range
      </button>
      <span data-testid="range-values">
        {minValue}-{maxValue}
      </span>
    </div>
  ),
}));

describe("FilterPanel", () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("renders with default title", () => {
      render(<FilterPanel filters={[]} values={{}} onChange={mockOnChange} />);
      expect(screen.getByText("Filters")).toBeInTheDocument();
    });

    it("renders with custom title", () => {
      render(
        <FilterPanel filters={[]} values={{}} onChange={mockOnChange} title="Custom Filters" />
      );
      expect(screen.getByText("Custom Filters")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <FilterPanel filters={[]} values={{}} onChange={mockOnChange} className="my-custom-class" />
      );
      expect(container.firstChild).toHaveClass("my-custom-class");
    });
  });

  describe("collapsible behavior", () => {
    const sampleFilters: FilterConfig[] = [{ id: "test", label: "Test Filter", type: "text" }];

    it("starts expanded by default", () => {
      render(<FilterPanel filters={sampleFilters} values={{}} onChange={mockOnChange} />);
      expect(screen.getByPlaceholderText(/Filter by test filter/i)).toBeInTheDocument();
    });

    it("starts collapsed when defaultCollapsed is true", () => {
      render(
        <FilterPanel
          filters={sampleFilters}
          values={{}}
          onChange={mockOnChange}
          defaultCollapsed={true}
        />
      );
      expect(screen.queryByPlaceholderText(/Filter by test filter/i)).not.toBeInTheDocument();
    });

    it("toggles collapse when header is clicked", async () => {
      render(<FilterPanel filters={sampleFilters} values={{}} onChange={mockOnChange} />);

      // Initially expanded
      expect(screen.getByPlaceholderText(/Filter by test filter/i)).toBeInTheDocument();

      // Click header to collapse
      fireEvent.click(screen.getByText("Filters"));

      // Should be collapsed
      expect(screen.queryByPlaceholderText(/Filter by test filter/i)).not.toBeInTheDocument();

      // Click header to expand
      fireEvent.click(screen.getByText("Filters"));

      // Should be expanded again
      expect(screen.getByPlaceholderText(/Filter by test filter/i)).toBeInTheDocument();
    });

    it("does not toggle when collapsible is false", () => {
      render(
        <FilterPanel
          filters={sampleFilters}
          values={{}}
          onChange={mockOnChange}
          collapsible={false}
        />
      );

      // Click header
      fireEvent.click(screen.getByText("Filters"));

      // Should still be visible (no collapse)
      expect(screen.getByPlaceholderText(/Filter by test filter/i)).toBeInTheDocument();
    });
  });

  describe("text filter", () => {
    const textFilters: FilterConfig[] = [{ id: "name", label: "Name", type: "text" }];

    it("renders text input", () => {
      render(<FilterPanel filters={textFilters} values={{}} onChange={mockOnChange} />);
      expect(screen.getByPlaceholderText(/Filter by name/i)).toBeInTheDocument();
    });

    it("displays current value", () => {
      render(
        <FilterPanel
          filters={textFilters}
          values={{ name: "test value" }}
          onChange={mockOnChange}
        />
      );
      expect(screen.getByDisplayValue("test value")).toBeInTheDocument();
    });

    it("calls onChange when text is entered", async () => {
      const user = userEvent.setup();
      render(<FilterPanel filters={textFilters} values={{ name: "" }} onChange={mockOnChange} />);

      const input = screen.getByPlaceholderText(/Filter by name/i);
      await user.type(input, "hello");

      // Should be called for each character
      expect(mockOnChange).toHaveBeenCalled();
      // Last call should have the updated value
      const lastCall = mockOnChange.mock.calls[mockOnChange.mock.calls.length - 1][0];
      expect(lastCall.name).toBe("hello");
    });

    it("sets undefined when text is cleared", async () => {
      const user = userEvent.setup();
      render(
        <FilterPanel filters={textFilters} values={{ name: "existing" }} onChange={mockOnChange} />
      );

      const input = screen.getByDisplayValue("existing");
      await user.clear(input);

      expect(mockOnChange).toHaveBeenCalledWith({ name: undefined });
    });
  });

  describe("select filter", () => {
    const selectFilters: FilterConfig[] = [
      {
        id: "status",
        label: "Status",
        type: "select",
        options: [
          { value: "pending", label: "Pending" },
          { value: "completed", label: "Completed" },
          { value: "failed", label: "Failed" },
        ],
      },
    ];

    it("renders select with options", () => {
      render(<FilterPanel filters={selectFilters} values={{}} onChange={mockOnChange} />);

      const select = screen.getByRole("combobox");
      expect(select).toBeInTheDocument();
      expect(screen.getByText("All")).toBeInTheDocument();
      expect(screen.getByText("Pending")).toBeInTheDocument();
      expect(screen.getByText("Completed")).toBeInTheDocument();
      expect(screen.getByText("Failed")).toBeInTheDocument();
    });

    it("displays current value", () => {
      render(
        <FilterPanel
          filters={selectFilters}
          values={{ status: "completed" }}
          onChange={mockOnChange}
        />
      );

      const select = screen.getByRole("combobox");
      expect(select).toHaveValue("completed");
    });

    it("calls onChange when selection changes", async () => {
      const user = userEvent.setup();
      render(
        <FilterPanel filters={selectFilters} values={{ status: "" }} onChange={mockOnChange} />
      );

      const select = screen.getByRole("combobox");
      await user.selectOptions(select, "pending");

      expect(mockOnChange).toHaveBeenCalledWith({ status: "pending" });
    });

    it('sets undefined when "All" is selected', async () => {
      const user = userEvent.setup();
      render(
        <FilterPanel
          filters={selectFilters}
          values={{ status: "pending" }}
          onChange={mockOnChange}
        />
      );

      const select = screen.getByRole("combobox");
      await user.selectOptions(select, "");

      expect(mockOnChange).toHaveBeenCalledWith({ status: undefined });
    });
  });

  describe("checkbox filter", () => {
    const checkboxFilters: FilterConfig[] = [
      { id: "includeArchived", label: "Include Archived", type: "checkbox" },
    ];

    it("renders checkbox", () => {
      render(<FilterPanel filters={checkboxFilters} values={{}} onChange={mockOnChange} />);

      expect(screen.getByRole("checkbox")).toBeInTheDocument();
      expect(screen.getByText("Include Archived")).toBeInTheDocument();
    });

    it("displays checked state", () => {
      render(
        <FilterPanel
          filters={checkboxFilters}
          values={{ includeArchived: true }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByRole("checkbox")).toBeChecked();
    });

    it("displays unchecked state", () => {
      render(
        <FilterPanel
          filters={checkboxFilters}
          values={{ includeArchived: false }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByRole("checkbox")).not.toBeChecked();
    });

    it("calls onChange when toggled", async () => {
      const user = userEvent.setup();
      render(
        <FilterPanel
          filters={checkboxFilters}
          values={{ includeArchived: false }}
          onChange={mockOnChange}
        />
      );

      await user.click(screen.getByRole("checkbox"));

      expect(mockOnChange).toHaveBeenCalledWith({ includeArchived: true });
    });
  });

  describe("range filter", () => {
    const rangeFilters: FilterConfig[] = [
      {
        id: "flux",
        label: "Flux Range",
        type: "range",
        min: 0,
        max: 100,
        step: 1,
        unit: "mJy",
      },
    ];

    it("renders range slider", () => {
      render(
        <FilterPanel filters={rangeFilters} values={{ flux: [10, 90] }} onChange={mockOnChange} />
      );

      expect(screen.getByTestId("range-slider-Flux Range")).toBeInTheDocument();
    });

    it("passes correct values to range slider", () => {
      render(
        <FilterPanel filters={rangeFilters} values={{ flux: [20, 80] }} onChange={mockOnChange} />
      );

      expect(screen.getByTestId("range-values")).toHaveTextContent("20-80");
    });

    it("uses default min/max when no value provided", () => {
      render(<FilterPanel filters={rangeFilters} values={{}} onChange={mockOnChange} />);

      expect(screen.getByTestId("range-values")).toHaveTextContent("0-100");
    });

    it("calls onChange when range changes", async () => {
      render(
        <FilterPanel filters={rangeFilters} values={{ flux: [10, 90] }} onChange={mockOnChange} />
      );

      fireEvent.click(screen.getByTestId("range-change"));

      expect(mockOnChange).toHaveBeenCalledWith({ flux: [11, 89] });
    });
  });

  describe("active filter count", () => {
    const filters: FilterConfig[] = [
      { id: "name", label: "Name", type: "text" },
      { id: "status", label: "Status", type: "select", options: [] },
      { id: "active", label: "Active", type: "checkbox", defaultValue: false },
      { id: "range", label: "Range", type: "range", min: 0, max: 100 },
    ];

    it("shows count badge when filters are active", () => {
      render(
        <FilterPanel
          filters={filters}
          values={{
            name: "test",
            status: "pending",
          }}
          onChange={mockOnChange}
        />
      );

      // Two active filters should show badge
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("does not show badge when no filters are active", () => {
      render(<FilterPanel filters={filters} values={{}} onChange={mockOnChange} />);

      // No badge should be present
      expect(screen.queryByText("0")).not.toBeInTheDocument();
    });

    it("counts range filter as active when changed from defaults", () => {
      render(
        <FilterPanel
          filters={filters}
          values={{
            range: [10, 90], // Not default 0-100
          }}
          onChange={mockOnChange}
        />
      );

      expect(screen.getByText("1")).toBeInTheDocument();
    });

    it("does not count range filter when at default values", () => {
      render(
        <FilterPanel
          filters={filters}
          values={{
            range: [0, 100], // Same as min/max
          }}
          onChange={mockOnChange}
        />
      );

      // No active filters
      expect(screen.queryByText("1")).not.toBeInTheDocument();
    });
  });

  describe("reset functionality", () => {
    const filters: FilterConfig[] = [
      { id: "name", label: "Name", type: "text", defaultValue: "" },
      { id: "active", label: "Active", type: "checkbox", defaultValue: false },
      { id: "count", label: "Count", type: "range", min: 0, max: 100, defaultValue: [0, 100] },
    ];

    it('shows "Reset all" button when filters are active', () => {
      render(<FilterPanel filters={filters} values={{ name: "test" }} onChange={mockOnChange} />);

      expect(screen.getByText("Reset all")).toBeInTheDocument();
    });

    it('hides "Reset all" button when no filters are active', () => {
      render(<FilterPanel filters={filters} values={{}} onChange={mockOnChange} />);

      expect(screen.queryByText("Reset all")).not.toBeInTheDocument();
    });

    it("resets all filters to default values when clicked", async () => {
      const user = userEvent.setup();
      render(
        <FilterPanel
          filters={filters}
          values={{ name: "test", active: true }}
          onChange={mockOnChange}
        />
      );

      await user.click(screen.getByText("Reset all"));

      expect(mockOnChange).toHaveBeenCalledWith({
        name: "",
        active: false,
        count: [0, 100],
      });
    });

    it("does not collapse panel when reset is clicked", async () => {
      const user = userEvent.setup();
      render(<FilterPanel filters={filters} values={{ name: "test" }} onChange={mockOnChange} />);

      await user.click(screen.getByText("Reset all"));

      // Panel should still be expanded
      expect(screen.getByText("Name")).toBeInTheDocument();
    });
  });

  describe("multiple filters", () => {
    const multiFilters: FilterConfig[] = [
      { id: "search", label: "Search", type: "text" },
      {
        id: "type",
        label: "Type",
        type: "select",
        options: [{ value: "source", label: "Source" }],
      },
      { id: "verified", label: "Verified", type: "checkbox" },
    ];

    it("renders all filter types together", () => {
      render(<FilterPanel filters={multiFilters} values={{}} onChange={mockOnChange} />);

      expect(screen.getByPlaceholderText(/Filter by search/i)).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toBeInTheDocument();
      expect(screen.getByRole("checkbox")).toBeInTheDocument();
    });

    it("preserves other values when one filter changes", async () => {
      const user = userEvent.setup();
      render(
        <FilterPanel
          filters={multiFilters}
          values={{ search: "existing", type: "source", verified: true }}
          onChange={mockOnChange}
        />
      );

      await user.click(screen.getByRole("checkbox"));

      expect(mockOnChange).toHaveBeenCalledWith({
        search: "existing",
        type: "source",
        verified: false,
      });
    });
  });

  describe("edge cases", () => {
    it("handles empty filters array", () => {
      render(<FilterPanel filters={[]} values={{}} onChange={mockOnChange} />);
      expect(screen.getByText("Filters")).toBeInTheDocument();
    });

    it("handles unknown filter type gracefully", () => {
      const unknownFilters = [{ id: "unknown", label: "Unknown", type: "unknown" as any }];

      render(<FilterPanel filters={unknownFilters} values={{}} onChange={mockOnChange} />);
      // Should not crash, just not render the unknown filter
      expect(screen.queryByText("Unknown")).not.toBeInTheDocument();
    });
  });
});
