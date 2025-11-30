import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";
import CelestialMap from "./CelestialMap";

describe("CelestialMap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders without crashing", () => {
      const { container } = render(<CelestialMap />);
      expect(container.firstChild).toBeInTheDocument();
    });

    it("renders container div", () => {
      render(<CelestialMap />);
      expect(document.querySelector("div")).toBeInTheDocument();
    });
  });

  describe("configuration props", () => {
    it("accepts projection config", () => {
      expect(() => {
        render(<CelestialMap config={{ projection: "mollweide" }} />);
      }).not.toThrow();
    });

    it("accepts transform config", () => {
      expect(() => {
        render(<CelestialMap config={{ transform: "galactic" }} />);
      }).not.toThrow();
    });

    it("accepts center coordinates", () => {
      expect(() => {
        render(<CelestialMap config={{ center: [180, 45, 0] }} />);
      }).not.toThrow();
    });

    it("accepts zoom level", () => {
      expect(() => {
        render(<CelestialMap config={{ zoomlevel: 2 }} />);
      }).not.toThrow();
    });

    it("accepts interactive option", () => {
      expect(() => {
        render(<CelestialMap config={{ interactive: true }} />);
      }).not.toThrow();
    });
  });

  describe("star configuration", () => {
    it("accepts star display options", () => {
      expect(() => {
        render(
          <CelestialMap
            stars={{
              show: true,
              limit: 6,
              colors: true,
              designation: true,
              propername: true,
            }}
          />
        );
      }).not.toThrow();
    });
  });

  describe("DSO configuration", () => {
    it("accepts DSO display options", () => {
      expect(() => {
        render(
          <CelestialMap
            dsos={{
              show: true,
              limit: 8,
              names: true,
            }}
          />
        );
      }).not.toThrow();
    });
  });

  describe("constellation configuration", () => {
    it("accepts constellation display options", () => {
      expect(() => {
        render(
          <CelestialMap
            constellations={{
              names: true,
              lines: true,
              bounds: true,
            }}
          />
        );
      }).not.toThrow();
    });
  });

  describe("custom markers", () => {
    it("accepts custom markers", () => {
      const markers = [
        { id: "m1", ra: 180, dec: 45, label: "Source 1" },
        { id: "m2", ra: 90, dec: 30, label: "Source 2" },
      ];
      expect(() => {
        render(<CelestialMap markers={markers} />);
      }).not.toThrow();
    });
  });

  describe("callbacks", () => {
    it("accepts onMarkerClick callback", () => {
      const onMarkerClick = vi.fn();
      expect(() => {
        render(<CelestialMap onMarkerClick={onMarkerClick} />);
      }).not.toThrow();
    });

    it("accepts onZoomChange callback", () => {
      const onZoomChange = vi.fn();
      expect(() => {
        render(<CelestialMap onZoomChange={onZoomChange} />);
      }).not.toThrow();
    });
  });

  describe("projection types", () => {
    const projections = [
      "aitoff",
      "azimuthalEqualArea",
      "azimuthalEquidistant",
      "equirectangular",
      "hammer",
      "mollweide",
      "orthographic",
      "stereographic",
    ] as const;

    projections.forEach((projection) => {
      it(`accepts ${projection} projection`, () => {
        expect(() => {
          render(<CelestialMap config={{ projection }} />);
        }).not.toThrow();
      });
    });
  });

  describe("transform types", () => {
    const transforms = ["equatorial", "ecliptic", "galactic", "supergalactic"] as const;

    transforms.forEach((transform) => {
      it(`accepts ${transform} transform`, () => {
        expect(() => {
          render(<CelestialMap config={{ transform }} />);
        }).not.toThrow();
      });
    });
  });
});
