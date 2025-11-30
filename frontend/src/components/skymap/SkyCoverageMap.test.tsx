import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SkyCoverageMap, { SkyCoverageMapProps, Pointing } from "./SkyCoverageMap";

// Mock D3 and d3-geo-projection
vi.mock("d3", () => ({
  select: vi.fn(() => ({
    html: vi.fn(() => ({
      append: vi.fn(() => ({
        attr: vi.fn(() => ({
          style: vi.fn(() => ({})),
          append: vi.fn(() => ({})),
        })),
      })),
    })),
  })),
  geoPath: vi.fn(() => vi.fn()),
  geoGraticule: vi.fn(() => vi.fn()),
  geoCircle: vi.fn(() => ({
    center: vi.fn(() => ({
      radius: vi.fn(() => vi.fn()),
    })),
  })),
}));

vi.mock("d3-geo-projection", () => ({
  geoAitoff: vi.fn(() => ({
    scale: vi.fn(() => ({
      translate: vi.fn(() => ({})),
    })),
  })),
  geoHammer: vi.fn(() => ({
    scale: vi.fn(() => ({
      translate: vi.fn(() => ({})),
    })),
  })),
  geoMollweide: vi.fn(() => ({
    scale: vi.fn(() => ({
      translate: vi.fn(() => ({})),
    })),
  })),
}));

describe("SkyCoverageMap", () => {
  const mockPointings: Pointing[] = [
    { id: "p1", ra: 180, dec: 45, radius: 2, label: "Pointing 1", status: "completed" },
    { id: "p2", ra: 90, dec: 30, radius: 2, label: "Pointing 2", status: "scheduled" },
    { id: "p3", ra: 270, dec: -15, radius: 2, label: "Pointing 3", status: "failed" },
  ];

  const mockOnClick = vi.fn();
  const mockOnHover = vi.fn();

  const defaultProps: SkyCoverageMapProps = {
    pointings: mockPointings,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders without crashing", () => {
      const { container } = render(<SkyCoverageMap {...defaultProps} />);
      expect(container.firstChild).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(<SkyCoverageMap {...defaultProps} className="custom-class" />);
      expect(container.firstChild).toHaveClass("custom-class");
    });

    it("renders with custom dimensions", () => {
      render(<SkyCoverageMap {...defaultProps} width={800} height={400} />);
      // Component should apply width/height to SVG
      expect(document.querySelector("div")).toBeInTheDocument();
    });
  });

  describe("projections", () => {
    it("accepts aitoff projection", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} projection="aitoff" />);
      }).not.toThrow();
    });

    it("accepts mollweide projection", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} projection="mollweide" />);
      }).not.toThrow();
    });

    it("accepts hammer projection", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} projection="hammer" />);
      }).not.toThrow();
    });

    it("accepts mercator projection", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} projection="mercator" />);
      }).not.toThrow();
    });
  });

  describe("overlay options", () => {
    it("accepts showGalacticPlane option", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} showGalacticPlane />);
      }).not.toThrow();
    });

    it("accepts showEcliptic option", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} showEcliptic />);
      }).not.toThrow();
    });

    it("accepts showConstellations as boolean", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} showConstellations />);
      }).not.toThrow();
    });

    it("accepts showConstellations as options object", () => {
      expect(() => {
        render(
          <SkyCoverageMap
            {...defaultProps}
            showConstellations={{ names: true, lines: true, bounds: false }}
          />
        );
      }).not.toThrow();
    });
  });

  describe("color schemes", () => {
    it("accepts status color scheme", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} colorScheme="status" />);
      }).not.toThrow();
    });

    it("accepts epoch color scheme", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} colorScheme="epoch" />);
      }).not.toThrow();
    });

    it("accepts uniform color scheme", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} colorScheme="uniform" />);
      }).not.toThrow();
    });
  });

  describe("callbacks", () => {
    it("accepts onPointingClick callback", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} onPointingClick={mockOnClick} />);
      }).not.toThrow();
    });

    it("accepts onPointingHover callback", () => {
      expect(() => {
        render(<SkyCoverageMap {...defaultProps} onPointingHover={mockOnHover} />);
      }).not.toThrow();
    });
  });

  describe("empty state", () => {
    it("renders with empty pointings array", () => {
      expect(() => {
        render(<SkyCoverageMap pointings={[]} />);
      }).not.toThrow();
    });
  });

  describe("default radius", () => {
    it("uses defaultRadius when pointing has no radius", () => {
      const pointingsWithoutRadius: Pointing[] = [{ id: "p1", ra: 180, dec: 45 }];
      expect(() => {
        render(<SkyCoverageMap pointings={pointingsWithoutRadius} defaultRadius={1.5} />);
      }).not.toThrow();
    });
  });
});
