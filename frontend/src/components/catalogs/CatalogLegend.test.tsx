import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CatalogLegend from "./CatalogLegend";
import type { CatalogDefinition } from "../../constants/catalogDefinitions";

describe("CatalogLegend", () => {
  const mockCatalogs: CatalogDefinition[] = [
    {
      id: "nvss",
      name: "NVSS",
      description: "NRAO VLA Sky Survey",
      color: "#ff0000",
      symbol: "circle",
    },
    { id: "first", name: "FIRST", description: "Faint Images", color: "#00ff00", symbol: "square" },
    {
      id: "vlass",
      name: "VLASS",
      description: "VLA Sky Survey",
      color: "#0000ff",
      symbol: "diamond",
    },
  ];

  describe("rendering", () => {
    it("returns null when catalogs array is empty", () => {
      const { container } = render(<CatalogLegend catalogs={[]} />);
      expect(container.firstChild).toBeNull();
    });

    it("renders all catalog entries", () => {
      render(<CatalogLegend catalogs={mockCatalogs} />);
      expect(screen.getByText("NVSS")).toBeInTheDocument();
      expect(screen.getByText("FIRST")).toBeInTheDocument();
      expect(screen.getByText("VLASS")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <CatalogLegend catalogs={mockCatalogs} className="custom-class" />
      );
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("symbol rendering", () => {
    it("renders circle symbol", () => {
      const circleCatalog: CatalogDefinition[] = [
        { id: "test", name: "Circle", description: "Test", color: "#ff0000", symbol: "circle" },
      ];
      render(<CatalogLegend catalogs={circleCatalog} />);
      expect(screen.getByText("Circle")).toBeInTheDocument();
      expect(document.querySelector("circle")).toBeInTheDocument();
    });

    it("renders square symbol", () => {
      const squareCatalog: CatalogDefinition[] = [
        { id: "test", name: "Square", description: "Test", color: "#ff0000", symbol: "square" },
      ];
      render(<CatalogLegend catalogs={squareCatalog} />);
      expect(document.querySelector("rect")).toBeInTheDocument();
    });

    it("renders diamond symbol", () => {
      const diamondCatalog: CatalogDefinition[] = [
        { id: "test", name: "Diamond", description: "Test", color: "#ff0000", symbol: "diamond" },
      ];
      render(<CatalogLegend catalogs={diamondCatalog} />);
      expect(document.querySelector("polygon")).toBeInTheDocument();
    });

    it("renders triangle symbol", () => {
      const triangleCatalog: CatalogDefinition[] = [
        { id: "test", name: "Triangle", description: "Test", color: "#ff0000", symbol: "triangle" },
      ];
      render(<CatalogLegend catalogs={triangleCatalog} />);
      expect(document.querySelector("polygon")).toBeInTheDocument();
    });

    it("renders star symbol", () => {
      const starCatalog: CatalogDefinition[] = [
        { id: "test", name: "Star", description: "Test", color: "#ff0000", symbol: "star" },
      ];
      render(<CatalogLegend catalogs={starCatalog} />);
      expect(document.querySelector("polygon")).toBeInTheDocument();
    });

    it("renders plus symbol", () => {
      const plusCatalog: CatalogDefinition[] = [
        { id: "test", name: "Plus", description: "Test", color: "#ff0000", symbol: "plus" },
      ];
      render(<CatalogLegend catalogs={plusCatalog} />);
      expect(document.querySelector("path")).toBeInTheDocument();
    });

    it("renders cross symbol", () => {
      const crossCatalog: CatalogDefinition[] = [
        { id: "test", name: "Cross", description: "Test", color: "#ff0000", symbol: "cross" },
      ];
      render(<CatalogLegend catalogs={crossCatalog} />);
      expect(document.querySelector("path")).toBeInTheDocument();
    });

    it("renders fallback for unknown symbol", () => {
      const unknownCatalog: CatalogDefinition[] = [
        {
          id: "test",
          name: "Unknown",
          description: "Test",
          color: "#ff0000",
          symbol: "unknown" as CatalogDefinition["symbol"],
        },
      ];
      render(<CatalogLegend catalogs={unknownCatalog} />);
      // Fallback renders a span with rounded-full class
      expect(document.querySelector(".rounded-full")).toBeInTheDocument();
    });
  });

  describe("colors", () => {
    it("applies correct colors to catalog names", () => {
      const colorCatalog: CatalogDefinition[] = [
        { id: "test", name: "ColorTest", description: "Test", color: "#ff5500", symbol: "circle" },
      ];
      render(<CatalogLegend catalogs={colorCatalog} />);
      const text = screen.getByText("ColorTest");
      expect(text).toHaveStyle({ color: "#ff5500" });
    });
  });

  describe("tooltips", () => {
    it("shows description in title attribute", () => {
      render(<CatalogLegend catalogs={mockCatalogs} />);
      const nvssEntry = screen.getByText("NVSS").closest("div");
      expect(nvssEntry).toHaveAttribute("title", "NRAO VLA Sky Survey");
    });
  });
});
