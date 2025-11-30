import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SourcePreview, { SourcePreviewProps } from "./SourcePreview";

describe("SourcePreview", () => {
  const defaultProps: SourcePreviewProps = {
    sourceId: "src-123",
    name: "J1234+5678",
    ra: 180.0,
    dec: 45.0,
    eta: 3.5,
    v: 0.25,
  };

  describe("rendering", () => {
    it("renders source name", () => {
      render(<SourcePreview {...defaultProps} />);
      expect(screen.getByText("J1234+5678")).toBeInTheDocument();
    });

    it("renders source ID when name not provided", () => {
      render(<SourcePreview {...defaultProps} name="" />);
      expect(screen.getByText("src-123")).toBeInTheDocument();
    });

    it("renders RA coordinate", () => {
      render(<SourcePreview {...defaultProps} />);
      expect(screen.getByText(/ra:/i)).toBeInTheDocument();
    });

    it("renders Dec coordinate", () => {
      render(<SourcePreview {...defaultProps} />);
      expect(screen.getByText(/dec:/i)).toBeInTheDocument();
    });

    it("renders η value", () => {
      render(<SourcePreview {...defaultProps} />);
      // eta.toFixed(2) = "3.50"
      expect(screen.getByText("3.50")).toBeInTheDocument();
      expect(screen.getByText("η")).toBeInTheDocument();
    });

    it("renders V value", () => {
      render(<SourcePreview {...defaultProps} />);
      // v.toFixed(3) = "0.250"
      expect(screen.getByText("0.250")).toBeInTheDocument();
      expect(screen.getByText("V")).toBeInTheDocument();
    });
  });

  describe("optional fields", () => {
    it("renders peak flux when provided", () => {
      render(<SourcePreview {...defaultProps} peakFlux={12.5} />);
      expect(screen.getByText(/12\.5/)).toBeInTheDocument();
    });

    it("renders number of measurements when provided", () => {
      render(<SourcePreview {...defaultProps} nMeasurements={15} />);
      expect(screen.getByText("15")).toBeInTheDocument();
    });
  });

  describe("positioning", () => {
    it("applies position styles when position provided", () => {
      const { container } = render(
        <SourcePreview {...defaultProps} position={{ x: 100, y: 200 }} />
      );
      const element = container.firstChild as HTMLElement;
      expect(element.style.position).toBe("absolute");
      expect(element.style.left).toBe("110px"); // x + 10
      expect(element.style.top).toBe("210px"); // y + 10
    });
  });

  describe("hover vs selected mode", () => {
    it("uses smaller width for hover mode", () => {
      const { container } = render(<SourcePreview {...defaultProps} isHover />);
      expect(container.firstChild).toHaveClass("min-w-48");
    });

    it("uses larger width for selected mode", () => {
      const { container } = render(<SourcePreview {...defaultProps} isHover={false} />);
      expect(container.firstChild).toHaveClass("min-w-64");
    });

    it("shows close button in selected mode", () => {
      const onClose = vi.fn();
      render(<SourcePreview {...defaultProps} isHover={false} onClose={onClose} />);
      expect(screen.getByText("×")).toBeInTheDocument();
    });

    it("hides close button in hover mode", () => {
      const onClose = vi.fn();
      render(<SourcePreview {...defaultProps} isHover onClose={onClose} />);
      expect(screen.queryByText("×")).not.toBeInTheDocument();
    });
  });

  describe("interactions", () => {
    it("calls onClose when close button clicked", async () => {
      const onClose = vi.fn();
      render(<SourcePreview {...defaultProps} isHover={false} onClose={onClose} />);
      await userEvent.click(screen.getByText("×"));
      expect(onClose).toHaveBeenCalled();
    });

    it("calls onNavigate when navigate button clicked", async () => {
      const onNavigate = vi.fn();
      // Button only appears when isHover is false
      render(<SourcePreview {...defaultProps} isHover={false} onNavigate={onNavigate} />);
      const viewButton = screen.getByRole("button", { name: /view source details/i });
      await userEvent.click(viewButton);
      expect(onNavigate).toHaveBeenCalledWith("src-123");
    });
  });

  describe("coordinate formatting", () => {
    it("formats RA in hours/minutes/seconds", () => {
      render(<SourcePreview {...defaultProps} ra={180} />);
      // 180 degrees = 12 hours
      expect(screen.getByText(/12h/)).toBeInTheDocument();
    });

    it("formats Dec with degree sign", () => {
      render(<SourcePreview {...defaultProps} dec={45} />);
      expect(screen.getByText(/45°/)).toBeInTheDocument();
    });

    it("handles negative Dec values", () => {
      render(<SourcePreview {...defaultProps} dec={-30} />);
      // The formatCoord function uses sign + Math.floor(Math.abs(value))
      // So for -30, it will show "-30° ..."
      expect(screen.getByText(/30°/)).toBeInTheDocument();
    });
  });
});
