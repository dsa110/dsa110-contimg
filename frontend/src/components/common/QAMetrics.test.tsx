import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import QAMetrics from "./QAMetrics";

describe("QAMetrics", () => {
  describe("grade display", () => {
    it("renders good grade with green styling", () => {
      render(<QAMetrics grade="good" />);
      expect(screen.getByText(/good/i)).toBeInTheDocument();
    });

    it("renders warn grade with yellow styling", () => {
      render(<QAMetrics grade="warn" />);
      expect(screen.getByText(/warn/i)).toBeInTheDocument();
    });

    it("renders fail grade with red styling", () => {
      render(<QAMetrics grade="fail" />);
      expect(screen.getByText(/fail/i)).toBeInTheDocument();
    });

    it("renders without grade when not provided", () => {
      render(<QAMetrics noiseJy={0.001} />);
      expect(screen.queryByText(/GOOD|WARN|FAIL/)).not.toBeInTheDocument();
    });

    it("handles null grade", () => {
      render(<QAMetrics grade={null} noiseJy={0.001} />);
      expect(screen.queryByText(/GOOD|WARN|FAIL/)).not.toBeInTheDocument();
    });

    it("handles undefined grade", () => {
      render(<QAMetrics grade={undefined} noiseJy={0.001} />);
      expect(screen.queryByText(/GOOD|WARN|FAIL/)).not.toBeInTheDocument();
    });
  });

  describe("summary display", () => {
    it("renders summary text with grade", () => {
      render(<QAMetrics grade="good" summary="Excellent image quality" />);
      expect(screen.getByText(/Excellent image quality/)).toBeInTheDocument();
    });
  });

  describe("noise formatting", () => {
    it("formats noise < 0.001 Jy in μJy", () => {
      render(<QAMetrics noiseJy={0.0001} />);
      expect(screen.getByText(/100\.0 μJy\/beam/)).toBeInTheDocument();
    });

    it("formats noise < 1 Jy in mJy", () => {
      render(<QAMetrics noiseJy={0.005} />);
      expect(screen.getByText(/5\.00 mJy\/beam/)).toBeInTheDocument();
    });

    it("formats noise >= 1 Jy in Jy", () => {
      render(<QAMetrics noiseJy={2.5} />);
      expect(screen.getByText(/2\.500 Jy\/beam/)).toBeInTheDocument();
    });

    it("shows RMS Noise label in non-compact mode", () => {
      render(<QAMetrics noiseJy={0.001} />);
      expect(screen.getByText("RMS Noise")).toBeInTheDocument();
    });
  });

  describe("dynamic range", () => {
    it("displays dynamic range with :1 suffix", () => {
      render(<QAMetrics dynamicRange={1000} />);
      expect(screen.getByText("1000:1")).toBeInTheDocument();
    });

    it("shows Dynamic Range label", () => {
      render(<QAMetrics dynamicRange={500} />);
      expect(screen.getByText("Dynamic Range")).toBeInTheDocument();
    });

    it("rounds dynamic range to integer", () => {
      render(<QAMetrics dynamicRange={1234.567} />);
      expect(screen.getByText("1235:1")).toBeInTheDocument();
    });
  });

  describe("peak flux formatting", () => {
    it("formats peak flux < 0.001 in μJy", () => {
      render(<QAMetrics peakFluxJy={0.0005} />);
      expect(screen.getByText(/500\.0 μJy/)).toBeInTheDocument();
    });

    it("formats peak flux < 1 in mJy", () => {
      render(<QAMetrics peakFluxJy={0.1} />);
      expect(screen.getByText(/100\.00 mJy/)).toBeInTheDocument();
    });

    it("formats peak flux >= 1 in Jy", () => {
      render(<QAMetrics peakFluxJy={5.5} />);
      expect(screen.getByText(/5\.500 Jy/)).toBeInTheDocument();
    });

    it("handles negative peak flux", () => {
      render(<QAMetrics peakFluxJy={-0.001} />);
      expect(screen.getByText(/-1\.00 mJy/)).toBeInTheDocument();
    });
  });

  describe("beam size", () => {
    it("displays beam dimensions", () => {
      render(<QAMetrics beamMajorArcsec={30.5} beamMinorArcsec={15.2} />);
      expect(screen.getByText(/30\.5″ × 15\.2″/)).toBeInTheDocument();
    });

    it("displays beam position angle when provided", () => {
      render(<QAMetrics beamMajorArcsec={30.5} beamMinorArcsec={15.2} beamPaDeg={45.7} />);
      expect(screen.getByText(/@ 46°/)).toBeInTheDocument();
    });

    it("does not show beam when only major axis is provided", () => {
      render(<QAMetrics beamMajorArcsec={30.5} />);
      expect(screen.queryByText("Beam Size")).not.toBeInTheDocument();
    });

    it("does not show beam when only minor axis is provided", () => {
      render(<QAMetrics beamMinorArcsec={15.2} />);
      expect(screen.queryByText("Beam Size")).not.toBeInTheDocument();
    });
  });

  describe("compact mode", () => {
    it("renders in compact layout", () => {
      const { container } = render(
        <QAMetrics grade="good" noiseJy={0.001} dynamicRange={500} compact />
      );
      // Compact mode uses flex layout
      expect(container.querySelector(".flex.items-center.gap-3")).toBeInTheDocument();
    });

    it("shows badge-style grade in compact mode", () => {
      render(<QAMetrics grade="good" compact />);
      expect(screen.getByText("GOOD")).toHaveClass("badge");
    });

    it("shows abbreviated noise label in compact mode", () => {
      render(<QAMetrics noiseJy={0.001} compact />);
      expect(screen.getByText("σ:")).toBeInTheDocument();
    });

    it("shows abbreviated dynamic range label in compact mode", () => {
      render(<QAMetrics dynamicRange={500} compact />);
      expect(screen.getByText("DR:")).toBeInTheDocument();
    });

    it("does not show beam size in compact mode", () => {
      render(<QAMetrics beamMajorArcsec={30} beamMinorArcsec={15} compact />);
      expect(screen.queryByText("Beam Size")).not.toBeInTheDocument();
    });
  });

  describe("non-compact mode layout", () => {
    it("renders metrics in grid layout", () => {
      const { container } = render(<QAMetrics grade="good" noiseJy={0.001} dynamicRange={500} />);
      expect(container.querySelector(".grid")).toBeInTheDocument();
    });

    it("shows all metric labels", () => {
      render(
        <QAMetrics
          grade="good"
          noiseJy={0.001}
          dynamicRange={500}
          peakFluxJy={0.1}
          beamMajorArcsec={30}
          beamMinorArcsec={15}
        />
      );
      expect(screen.getByText("RMS Noise")).toBeInTheDocument();
      expect(screen.getByText("Dynamic Range")).toBeInTheDocument();
      expect(screen.getByText("Peak Flux")).toBeInTheDocument();
      expect(screen.getByText("Beam Size")).toBeInTheDocument();
    });
  });

  describe("grade colors", () => {
    it("applies green background for good grade", () => {
      const { container } = render(<QAMetrics grade="good" />);
      expect(container.firstChild).toHaveClass("bg-green-50");
    });

    it("applies yellow background for warn grade", () => {
      const { container } = render(<QAMetrics grade="warn" />);
      expect(container.firstChild).toHaveClass("bg-yellow-50");
    });

    it("applies red background for fail grade", () => {
      const { container } = render(<QAMetrics grade="fail" />);
      expect(container.firstChild).toHaveClass("bg-red-50");
    });

    it("applies gray background when no grade", () => {
      const { container } = render(<QAMetrics noiseJy={0.001} />);
      expect(container.firstChild).toHaveClass("bg-gray-50");
    });
  });

  describe("empty state", () => {
    it("renders without any metrics", () => {
      const { container } = render(<QAMetrics />);
      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe("compact mode badges", () => {
    it("uses badge-success for good grade", () => {
      render(<QAMetrics grade="good" compact />);
      expect(screen.getByText("GOOD")).toHaveClass("badge-success");
    });

    it("uses badge-warning for warn grade", () => {
      render(<QAMetrics grade="warn" compact />);
      expect(screen.getByText("WARN")).toHaveClass("badge-warning");
    });

    it("uses badge-error for fail grade", () => {
      render(<QAMetrics grade="fail" compact />);
      expect(screen.getByText("FAIL")).toHaveClass("badge-error");
    });
  });
});
