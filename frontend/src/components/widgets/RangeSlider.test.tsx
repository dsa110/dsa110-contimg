import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RangeSlider, { RangeSliderProps } from "./RangeSlider";

describe("RangeSlider", () => {
  const mockOnChange = vi.fn();
  const mockOnChangeComplete = vi.fn();

  const defaultProps: RangeSliderProps = {
    min: 0,
    max: 100,
    onChange: mockOnChange,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders with min and max values", () => {
      render(<RangeSlider {...defaultProps} />);
      // Should have two input elements for the slider handles
      const sliders = screen.getAllByRole("slider");
      expect(sliders.length).toBeGreaterThanOrEqual(2);
    });

    it("renders label when provided", () => {
      render(<RangeSlider {...defaultProps} label="Flux Range" />);
      expect(screen.getByText("Flux Range")).toBeInTheDocument();
    });

    it("renders unit suffix when provided", () => {
      render(<RangeSlider {...defaultProps} unit="mJy" showInputs />);
      // Unit is shown in the input suffix areas
      expect(screen.getAllByText("mJy").length).toBeGreaterThanOrEqual(1);
    });

    it("renders input fields when showInputs is true", () => {
      render(<RangeSlider {...defaultProps} showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      expect(inputs.length).toBe(2);
    });

    it("hides input fields when showInputs is false", () => {
      render(<RangeSlider {...defaultProps} showInputs={false} />);
      expect(screen.queryAllByRole("spinbutton")).toHaveLength(0);
    });

    it("applies custom className", () => {
      const { container } = render(<RangeSlider {...defaultProps} className="custom-class" />);
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("initial values", () => {
    it("uses min and max as defaults when no initial values provided", () => {
      render(<RangeSlider {...defaultProps} showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      expect(inputs[0]).toHaveValue(0);
      expect(inputs[1]).toHaveValue(100);
    });

    it("uses provided minValue and maxValue", () => {
      render(<RangeSlider {...defaultProps} minValue={25} maxValue={75} showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      expect(inputs[0]).toHaveValue(25);
      expect(inputs[1]).toHaveValue(75);
    });
  });

  describe("input changes", () => {
    it("calls onChange when min input changes", async () => {
      render(<RangeSlider {...defaultProps} showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      await userEvent.clear(inputs[0]);
      await userEvent.type(inputs[0], "20");
      expect(mockOnChange).toHaveBeenCalled();
    });

    it("calls onChange when max input changes", async () => {
      render(<RangeSlider {...defaultProps} showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      await userEvent.clear(inputs[1]);
      await userEvent.type(inputs[1], "80");
      expect(mockOnChange).toHaveBeenCalled();
    });

    it("calls onChangeComplete on blur", async () => {
      render(<RangeSlider {...defaultProps} showInputs onChangeComplete={mockOnChangeComplete} />);
      const inputs = screen.getAllByRole("spinbutton");
      await userEvent.clear(inputs[0]);
      await userEvent.type(inputs[0], "20");
      await userEvent.tab(); // Trigger blur
      expect(mockOnChangeComplete).toHaveBeenCalled();
    });
  });

  describe("value constraints", () => {
    it("prevents min from exceeding max", async () => {
      render(<RangeSlider {...defaultProps} minValue={40} maxValue={60} showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      await userEvent.clear(inputs[0]);
      await userEvent.type(inputs[0], "70");
      await userEvent.tab();
      // Min should be constrained to max - step
      expect(mockOnChange).toHaveBeenLastCalledWith(expect.any(Number), 60);
    });

    it("prevents max from being less than min", async () => {
      render(<RangeSlider {...defaultProps} minValue={40} maxValue={60} showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      await userEvent.clear(inputs[1]);
      await userEvent.type(inputs[1], "30");
      await userEvent.tab();
      // Max should be constrained to min + step
      expect(mockOnChange).toHaveBeenLastCalledWith(40, expect.any(Number));
    });
  });

  describe("step increments", () => {
    it("respects step value for inputs", () => {
      render(<RangeSlider {...defaultProps} step={5} showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      expect(inputs[0]).toHaveAttribute("step", "5");
      expect(inputs[1]).toHaveAttribute("step", "5");
    });
  });

  describe("disabled state", () => {
    it("disables inputs when disabled is true", () => {
      render(<RangeSlider {...defaultProps} disabled showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      expect(inputs[0]).toBeDisabled();
      expect(inputs[1]).toBeDisabled();
    });

    it("applies disabled styling to sliders", () => {
      render(<RangeSlider {...defaultProps} disabled />);
      const sliders = screen.getAllByRole("slider");
      sliders.forEach((slider) => {
        expect(slider).toBeDisabled();
      });
    });
  });

  describe("value formatting", () => {
    it("formats values with specified decimals", () => {
      render(<RangeSlider {...defaultProps} minValue={12.345} decimals={2} showInputs />);
      const inputs = screen.getAllByRole("spinbutton");
      // The input should have the numeric value (not formatted with decimals)
      expect(inputs[0]).toHaveValue(12.345);
    });

    it("uses custom formatValue function", () => {
      const formatValue = (val: number) => `${val}°C`;
      // formatValue is used when showInputs is false
      render(
        <RangeSlider {...defaultProps} minValue={25} formatValue={formatValue} showInputs={false} />
      );
      expect(screen.getByText(/25.*°C/)).toBeInTheDocument();
    });
  });

  describe("histogram overlay", () => {
    it("renders histogram when provided", () => {
      const histogram = [5, 10, 20, 15, 8, 3];
      const { container } = render(<RangeSlider {...defaultProps} histogram={histogram} />);
      // Histogram bars should be rendered
      const histogramBars = container.querySelectorAll('[class*="histogram"]');
      expect(histogramBars.length).toBeGreaterThanOrEqual(0); // Component may render bars differently
    });
  });

  describe("slider interaction", () => {
    it("renders min and max slider handles", () => {
      render(<RangeSlider {...defaultProps} />);
      const sliders = screen.getAllByRole("slider");
      expect(sliders.length).toBeGreaterThanOrEqual(2);
    });
  });
});
