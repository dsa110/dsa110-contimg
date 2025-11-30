import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import VariabilityFilters, { VariabilityFiltersProps } from "./VariabilityFilters";

describe("VariabilityFilters", () => {
  const mockOnChange = vi.fn();

  const defaultProps: VariabilityFiltersProps = {
    values: {},
    onChange: mockOnChange,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders Eta metric filter", () => {
      render(<VariabilityFilters {...defaultProps} />);
      expect(screen.getByText(/η.*metric/i)).toBeInTheDocument();
    });

    it("renders V metric filter", () => {
      render(<VariabilityFilters {...defaultProps} />);
      expect(screen.getByText(/v metric/i)).toBeInTheDocument();
    });

    it("renders Vs metric filter", () => {
      render(<VariabilityFilters {...defaultProps} />);
      expect(screen.getByText(/vs metric/i)).toBeInTheDocument();
    });

    it("renders m metric filter", () => {
      render(<VariabilityFilters {...defaultProps} />);
      expect(screen.getByText(/m metric/i)).toBeInTheDocument();
    });

    it("renders min and max inputs for each metric", () => {
      render(<VariabilityFilters {...defaultProps} />);
      const minInputs = screen.getAllByPlaceholderText("Min");
      const maxInputs = screen.getAllByPlaceholderText("Max");
      expect(minInputs).toHaveLength(4);
      expect(maxInputs).toHaveLength(4);
    });

    it("applies custom className", () => {
      const { container } = render(
        <VariabilityFilters {...defaultProps} className="custom-class" />
      );
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("flux type options", () => {
    it("shows Peak Flux option", () => {
      render(<VariabilityFilters {...defaultProps} />);
      const options = screen.getAllByText("Peak Flux");
      expect(options.length).toBeGreaterThan(0);
    });

    it("shows Int Flux option", () => {
      render(<VariabilityFilters {...defaultProps} />);
      const options = screen.getAllByText("Int Flux");
      expect(options.length).toBeGreaterThan(0);
    });
  });

  describe("value changes", () => {
    it("calls onChange when eta min value changes", async () => {
      render(<VariabilityFilters {...defaultProps} />);
      const minInputs = screen.getAllByPlaceholderText("Min");
      await userEvent.type(minInputs[0], "1.5");
      expect(mockOnChange).toHaveBeenCalled();
    });

    it("calls onChange when eta max value changes", async () => {
      render(<VariabilityFilters {...defaultProps} />);
      const maxInputs = screen.getAllByPlaceholderText("Max");
      await userEvent.type(maxInputs[0], "10");
      expect(mockOnChange).toHaveBeenCalled();
    });

    it("calls onChange when flux type changes", async () => {
      render(<VariabilityFilters {...defaultProps} />);
      const selects = screen.getAllByRole("combobox");
      await userEvent.selectOptions(selects[0], "int");
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          eta: expect.objectContaining({ type: "int" }),
        })
      );
    });
  });

  describe("with existing values", () => {
    it("displays existing eta values", () => {
      const values = {
        eta: { min: 2.5, max: 8.0, type: "peak" as const },
      };
      render(<VariabilityFilters values={values} onChange={mockOnChange} />);
      const minInputs = screen.getAllByPlaceholderText("Min");
      const maxInputs = screen.getAllByPlaceholderText("Max");
      expect(minInputs[0]).toHaveValue(2.5);
      expect(maxInputs[0]).toHaveValue(8.0);
    });

    it("displays existing flux type", () => {
      const values = {
        eta: { min: 2.5, max: 8.0, type: "int" as const },
      };
      render(<VariabilityFilters values={values} onChange={mockOnChange} />);
      const selects = screen.getAllByRole("combobox");
      expect(selects[0]).toHaveValue("int");
    });
  });

  describe("tooltips", () => {
    it("shows tooltip icons for each metric", () => {
      render(<VariabilityFilters {...defaultProps} />);
      const tooltips = document.querySelectorAll("span[title]");
      expect(tooltips.length).toBe(4);
    });

    it("has tooltip for eta metric", () => {
      render(<VariabilityFilters {...defaultProps} />);
      const etaTooltip = document.querySelector('span[title*="chi-squared"]');
      expect(etaTooltip).toBeInTheDocument();
    });
  });
});
