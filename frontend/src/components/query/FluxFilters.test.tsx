import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FluxFilters, { FluxFiltersProps } from "./FluxFilters";

describe("FluxFilters", () => {
  const mockOnChange = vi.fn();

  const defaultProps: FluxFiltersProps = {
    values: {},
    onChange: mockOnChange,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders Min. Flux filter", () => {
      render(<FluxFilters {...defaultProps} />);
      expect(screen.getByText("Min. Flux")).toBeInTheDocument();
    });

    it("renders Max. Flux filter", () => {
      render(<FluxFilters {...defaultProps} />);
      expect(screen.getByText("Max. Flux")).toBeInTheDocument();
    });

    it("renders Avg. Flux filter", () => {
      render(<FluxFilters {...defaultProps} />);
      expect(screen.getByText("Avg. Flux")).toBeInTheDocument();
    });

    it("renders min and max inputs for each filter", () => {
      render(<FluxFilters {...defaultProps} />);
      const minInputs = screen.getAllByPlaceholderText(/min/i);
      const maxInputs = screen.getAllByPlaceholderText(/max/i);
      expect(minInputs).toHaveLength(3);
      expect(maxInputs).toHaveLength(3);
    });

    it("renders flux type selects", () => {
      render(<FluxFilters {...defaultProps} />);
      const selects = screen.getAllByRole("combobox");
      expect(selects).toHaveLength(3);
    });

    it("applies custom className", () => {
      const { container } = render(<FluxFilters {...defaultProps} className="custom-class" />);
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("flux type options", () => {
    it("shows Peak Flux option", () => {
      render(<FluxFilters {...defaultProps} />);
      const options = screen.getAllByText("Peak Flux");
      expect(options.length).toBeGreaterThan(0);
    });

    it("shows Int Flux option", () => {
      render(<FluxFilters {...defaultProps} />);
      const options = screen.getAllByText("Int Flux");
      expect(options.length).toBeGreaterThan(0);
    });
  });

  describe("value changes", () => {
    it("calls onChange when min value changes", async () => {
      render(<FluxFilters {...defaultProps} />);
      const minInputs = screen.getAllByPlaceholderText(/min/i);
      await userEvent.type(minInputs[0], "10");
      expect(mockOnChange).toHaveBeenCalled();
    });

    it("calls onChange when max value changes", async () => {
      render(<FluxFilters {...defaultProps} />);
      const maxInputs = screen.getAllByPlaceholderText(/max/i);
      await userEvent.type(maxInputs[0], "100");
      expect(mockOnChange).toHaveBeenCalled();
    });

    it("calls onChange when flux type changes", async () => {
      render(<FluxFilters {...defaultProps} />);
      const selects = screen.getAllByRole("combobox");
      await userEvent.selectOptions(selects[0], "int");
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.objectContaining({
          minFlux: expect.objectContaining({ type: "int" }),
        })
      );
    });
  });

  describe("with existing values", () => {
    it("displays existing min value", () => {
      const values = {
        minFlux: { min: 5, max: 50, type: "peak" as const },
      };
      render(<FluxFilters values={values} onChange={mockOnChange} />);
      const minInputs = screen.getAllByPlaceholderText(/min/i);
      expect(minInputs[0]).toHaveValue(5);
    });

    it("displays existing max value", () => {
      const values = {
        minFlux: { min: 5, max: 50, type: "peak" as const },
      };
      render(<FluxFilters values={values} onChange={mockOnChange} />);
      const maxInputs = screen.getAllByPlaceholderText(/max/i);
      expect(maxInputs[0]).toHaveValue(50);
    });

    it("displays existing flux type", () => {
      const values = {
        minFlux: { min: 5, max: 50, type: "int" as const },
      };
      render(<FluxFilters values={values} onChange={mockOnChange} />);
      const selects = screen.getAllByRole("combobox");
      expect(selects[0]).toHaveValue("int");
    });
  });

  describe("tooltips", () => {
    it("shows tooltip icons for each filter", () => {
      render(<FluxFilters {...defaultProps} />);
      const tooltips = document.querySelectorAll("span[title]");
      expect(tooltips.length).toBe(3);
    });
  });
});
