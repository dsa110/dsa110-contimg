import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CoordinateDisplay from "./CoordinateDisplay";

// Mock coordinate formatter
vi.mock("../../utils/coordinateFormatter", () => ({
  formatRA: (raDeg: number) => {
    const hours = Math.floor(raDeg / 15);
    const mins = Math.floor((raDeg / 15 - hours) * 60);
    const secs = ((raDeg / 15 - hours) * 60 - mins) * 60;
    return `${hours.toString().padStart(2, "0")}h ${mins.toString().padStart(2, "0")}m ${secs
      .toFixed(2)
      .padStart(5, "0")}s`;
  },
  formatDec: (decDeg: number) => {
    const sign = decDeg >= 0 ? "+" : "-";
    const absVal = Math.abs(decDeg);
    const deg = Math.floor(absVal);
    const arcmin = Math.floor((absVal - deg) * 60);
    const arcsec = ((absVal - deg) * 60 - arcmin) * 60;
    return `${sign}${deg.toString().padStart(2, "0")}° ${arcmin
      .toString()
      .padStart(2, "0")}′ ${arcsec.toFixed(1).padStart(4, "0")}″`;
  },
  formatDegrees: (deg: number, precision: number = 4) => `${deg.toFixed(precision)}°`,
}));

describe("CoordinateDisplay", () => {
  const testRA = 180.0; // 12h 00m 00s
  const testDec = 45.0; // +45° 00' 00"

  describe("basic rendering", () => {
    it("renders RA and Dec labels in non-compact mode", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} />);
      expect(screen.getByText("Right Ascension")).toBeInTheDocument();
      expect(screen.getByText("Declination")).toBeInTheDocument();
    });

    it("renders HMS/DMS format by default", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} />);
      // Should show HMS format for RA
      expect(screen.getByText(/12h 00m/)).toBeInTheDocument();
      // Should show DMS format for Dec
      expect(screen.getByText(/\+45°/)).toBeInTheDocument();
    });
  });

  describe("showDecimal option", () => {
    it("shows decimal degrees when showDecimal=true (default)", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} showDecimal={true} />);
      expect(screen.getByText("180.000000°")).toBeInTheDocument();
      expect(screen.getByText("45.000000°")).toBeInTheDocument();
    });

    it("hides decimal degrees when showDecimal=false", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} showDecimal={false} />);
      expect(screen.queryByText("180.000000°")).not.toBeInTheDocument();
      expect(screen.queryByText("45.000000°")).not.toBeInTheDocument();
    });
  });

  describe("compact mode", () => {
    it("renders in single line for compact mode", () => {
      const { container } = render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} compact />);
      // Compact mode should not have the grid layout
      expect(container.querySelector(".grid")).not.toBeInTheDocument();
    });

    it("shows comma separator in compact mode", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} compact />);
      expect(screen.getByText(",")).toBeInTheDocument();
    });

    it("shows label prefix in compact mode when provided", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} compact label="Position" />);
      expect(screen.getByText("Position:")).toBeInTheDocument();
    });
  });

  describe("label", () => {
    it("renders label when provided in non-compact mode", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} label="Source Position" />);
      expect(screen.getByText("Source Position")).toBeInTheDocument();
    });

    it("does not render label section when not provided", () => {
      const { container } = render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} />);
      // Without label or toggle button, there should be no header flex container
      expect(container.querySelector(".flex.items-center.justify-between")).not.toBeInTheDocument();
    });
  });

  describe("format toggle", () => {
    it("shows toggle button when allowFormatToggle=true", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} allowFormatToggle />);
      expect(screen.getByRole("button", { name: /Decimal|Toggle/i })).toBeInTheDocument();
    });

    it("does not show toggle button by default", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} />);
      expect(screen.queryByRole("button", { name: /Decimal|Toggle|HMS/i })).not.toBeInTheDocument();
    });

    it("toggles from HMS/DMS to decimal when clicked", async () => {
      const user = userEvent.setup();
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} allowFormatToggle />);

      // Initially shows HMS/DMS as primary
      expect(screen.getByText(/12h 00m/)).toBeInTheDocument();

      // Click toggle
      await user.click(screen.getByRole("button", { name: /Decimal/i }));

      // After toggle, decimal should be primary (shown first)
      // The button text should change to indicate HMS/DMS mode
      expect(screen.getByRole("button", { name: /HMS/i })).toBeInTheDocument();
    });

    it("toggles back from decimal to HMS/DMS when clicked again", async () => {
      const user = userEvent.setup();
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} allowFormatToggle />);

      const button = screen.getByRole("button", { name: /Decimal/i });

      // Toggle to decimal
      await user.click(button);

      // Toggle back to HMS
      await user.click(screen.getByRole("button", { name: /HMS/i }));

      // Should be back to HMS/DMS mode
      expect(screen.getByRole("button", { name: /Decimal/i })).toBeInTheDocument();
    });

    it("shows toggle button in compact mode", async () => {
      const user = userEvent.setup();
      render(<CoordinateDisplay raDeg={testRA} decDeg={testDec} compact allowFormatToggle />);

      expect(screen.getByRole("button", { name: /Toggle/i })).toBeInTheDocument();

      // Clicking should toggle format
      await user.click(screen.getByRole("button", { name: /Toggle/i }));

      // Should now show decimal format in compact view
      expect(screen.getByText("180.000000°")).toBeInTheDocument();
    });
  });

  describe("negative declination", () => {
    it("displays negative declination with minus sign", () => {
      render(<CoordinateDisplay raDeg={testRA} decDeg={-30.5} />);
      expect(screen.getByText(/-30°/)).toBeInTheDocument();
    });
  });

  describe("edge cases", () => {
    it("handles RA at 0 degrees", () => {
      render(<CoordinateDisplay raDeg={0} decDeg={0} />);
      expect(screen.getByText(/00h 00m/)).toBeInTheDocument();
    });

    it("handles RA near 360 degrees", () => {
      render(<CoordinateDisplay raDeg={359.5} decDeg={0} />);
      expect(screen.getByText(/23h 58m/)).toBeInTheDocument();
    });

    it("handles Dec at +90 degrees", () => {
      render(<CoordinateDisplay raDeg={0} decDeg={90} />);
      expect(screen.getByText(/\+90°/)).toBeInTheDocument();
    });

    it("handles Dec at -90 degrees", () => {
      render(<CoordinateDisplay raDeg={0} decDeg={-90} />);
      expect(screen.getByText(/-90°/)).toBeInTheDocument();
    });
  });

  describe("decimal values", () => {
    it("formats decimal RA correctly", () => {
      render(<CoordinateDisplay raDeg={83.63308} decDeg={22.0145} />);
      expect(screen.getByText("83.633080°")).toBeInTheDocument();
    });

    it("formats decimal Dec correctly", () => {
      render(<CoordinateDisplay raDeg={83.63308} decDeg={22.0145} />);
      expect(screen.getByText("22.014500°")).toBeInTheDocument();
    });
  });
});
