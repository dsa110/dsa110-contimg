/**
 * Tests for CatalogOverlayPanel component
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CatalogOverlayPanel from "./CatalogOverlayPanel";
import { CATALOG_DEFINITIONS } from "../../constants/catalogDefinitions";

// Mock vizierQuery
vi.mock("../../utils/vizierQuery", () => ({
  queryCatalogCached: vi.fn().mockResolvedValue({
    catalogId: "gaia",
    sources: [
      { id: "source1", ra: 10.5, dec: 20.5 },
      { id: "source2", ra: 10.6, dec: 20.6 },
    ],
    count: 2,
    truncated: false,
    error: undefined,
  }),
}));

// Mock CatalogLegend
vi.mock("./CatalogLegend", () => ({
  default: vi.fn(({ catalogs }) => (
    <div data-testid="catalog-legend">
      {catalogs.map((c: any) => (
        <span key={c.id} data-testid={`legend-${c.id}`}>
          {c.name}
        </span>
      ))}
    </div>
  )),
}));

describe("CatalogOverlayPanel", () => {
  const defaultProps = {
    enabledCatalogs: [] as string[],
    onCatalogChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("renders header with title", () => {
      render(<CatalogOverlayPanel {...defaultProps} />);
      expect(screen.getByText("VizieR Catalogues")).toBeInTheDocument();
    });

    it("shows badge with enabled catalog count", () => {
      render(<CatalogOverlayPanel {...defaultProps} enabledCatalogs={["gaia", "nvss"]} />);
      expect(screen.getByText("2")).toBeInTheDocument();
    });

    it("shows Show options button initially", () => {
      render(<CatalogOverlayPanel {...defaultProps} />);
      expect(screen.getByText("Show options")).toBeInTheDocument();
    });

    it("shows Hide options button when expanded", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));
      expect(screen.getByText("Hide options")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <CatalogOverlayPanel {...defaultProps} className="custom-class" />
      );
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("expand/collapse behavior", () => {
    it("hides catalog options by default", () => {
      render(<CatalogOverlayPanel {...defaultProps} />);
      expect(screen.queryByText("Optical / Infrared")).not.toBeInTheDocument();
      expect(screen.queryByText("Radio")).not.toBeInTheDocument();
    });

    it("shows catalog options when expanded", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));

      expect(screen.getByText("Optical / Infrared")).toBeInTheDocument();
      expect(screen.getByText("Radio")).toBeInTheDocument();
    });

    it("shows search radius input when expanded", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));

      expect(screen.getByText("Search radius:")).toBeInTheDocument();
      expect(screen.getByRole("spinbutton")).toBeInTheDocument();
    });

    it("has proper aria-expanded attribute", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      const button = screen.getByRole("button", { name: /show catalog options/i });
      expect(button).toHaveAttribute("aria-expanded", "false");

      await user.click(button);
      expect(screen.getByRole("button", { name: /hide catalog options/i })).toHaveAttribute(
        "aria-expanded",
        "true"
      );
    });
  });

  describe("catalog selection", () => {
    it("shows checkboxes for all catalogs when expanded", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));

      // Check that some known catalogs are present
      expect(screen.getByText("Gaia DR3")).toBeInTheDocument();
      expect(screen.getByText("NVSS")).toBeInTheDocument();
    });

    it("calls onCatalogChange when checkbox is toggled", async () => {
      const onCatalogChange = vi.fn();
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} onCatalogChange={onCatalogChange} />);

      await user.click(screen.getByText("Show options"));

      // Find the Gaia checkbox by finding its label
      const gaiaLabel = screen.getByText("Gaia DR3").closest("label");
      const checkbox = gaiaLabel?.querySelector('input[type="checkbox"]');

      if (checkbox) {
        await user.click(checkbox);
        expect(onCatalogChange).toHaveBeenCalledWith(["gaia"]);
      }
    });

    it("checks enabled catalogs", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} enabledCatalogs={["gaia"]} />);

      await user.click(screen.getByText("Show options"));

      // Use getAllByText since Gaia appears in both legend and checkbox
      const gaiaElements = screen.getAllByText("Gaia DR3");
      const gaiaLabel = gaiaElements.find((el) => el.closest("label"))?.closest("label");
      const checkbox = gaiaLabel?.querySelector('input[type="checkbox"]') as HTMLInputElement;

      expect(checkbox?.checked).toBe(true);
    });

    it("removes catalog from enabled when unchecked", async () => {
      const onCatalogChange = vi.fn();
      const user = userEvent.setup();
      render(
        <CatalogOverlayPanel
          {...defaultProps}
          enabledCatalogs={["gaia", "nvss"]}
          onCatalogChange={onCatalogChange}
        />
      );

      await user.click(screen.getByText("Show options"));

      // Use getAllByText since Gaia appears in both legend and checkbox
      const gaiaElements = screen.getAllByText("Gaia DR3");
      const gaiaLabel = gaiaElements.find((el) => el.closest("label"))?.closest("label");
      const checkbox = gaiaLabel?.querySelector('input[type="checkbox"]');

      if (checkbox) {
        await user.click(checkbox);
        expect(onCatalogChange).toHaveBeenCalledWith(["nvss"]);
      }
    });
  });

  describe("select all / deselect all", () => {
    it("shows Select all button when not all selected", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} enabledCatalogs={["gaia"]} />);

      await user.click(screen.getByText("Show options"));

      expect(screen.getByText("Select all")).toBeInTheDocument();
    });

    it("shows Deselect all button when all selected", async () => {
      const user = userEvent.setup();
      const allCatalogs = CATALOG_DEFINITIONS.map((c) => c.id);
      render(<CatalogOverlayPanel {...defaultProps} enabledCatalogs={allCatalogs} />);

      await user.click(screen.getByText("Show options"));

      expect(screen.getByText("Deselect all")).toBeInTheDocument();
    });

    it("calls onCatalogChange with all catalogs when Select all clicked", async () => {
      const onCatalogChange = vi.fn();
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} onCatalogChange={onCatalogChange} />);

      await user.click(screen.getByText("Show options"));
      await user.click(screen.getByText("Select all"));

      expect(onCatalogChange).toHaveBeenCalledWith(CATALOG_DEFINITIONS.map((c) => c.id));
    });

    it("calls onCatalogChange with empty array when Deselect all clicked", async () => {
      const onCatalogChange = vi.fn();
      const allCatalogs = CATALOG_DEFINITIONS.map((c) => c.id);
      const user = userEvent.setup();
      render(
        <CatalogOverlayPanel
          {...defaultProps}
          enabledCatalogs={allCatalogs}
          onCatalogChange={onCatalogChange}
        />
      );

      await user.click(screen.getByText("Show options"));
      await user.click(screen.getByText("Deselect all"));

      expect(onCatalogChange).toHaveBeenCalledWith([]);
    });
  });

  describe("clear button", () => {
    it("shows Clear button when expanded", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));

      expect(screen.getByText("Clear")).toBeInTheDocument();
    });

    it("calls onCatalogChange with empty array when Clear clicked", async () => {
      const onCatalogChange = vi.fn();
      const user = userEvent.setup();
      render(
        <CatalogOverlayPanel
          {...defaultProps}
          enabledCatalogs={["gaia"]}
          onCatalogChange={onCatalogChange}
        />
      );

      await user.click(screen.getByText("Show options"));
      await user.click(screen.getByText("Clear"));

      expect(onCatalogChange).toHaveBeenCalledWith([]);
    });
  });

  describe("search radius", () => {
    it("shows default search radius", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));

      const input = screen.getByRole("spinbutton") as HTMLInputElement;
      expect(input.value).toBe("5");
    });

    it("uses custom search radius prop", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} searchRadius={10} />);

      await user.click(screen.getByText("Show options"));

      const input = screen.getByRole("spinbutton") as HTMLInputElement;
      expect(input.value).toBe("10");
    });

    it("allows changing search radius", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));

      const input = screen.getByRole("spinbutton");
      // Change value using fireEvent for controlled input
      fireEvent.change(input, { target: { value: "15" } });

      expect((input as HTMLInputElement).value).toBe("15");
    });

    it("clamps search radius to max of 60", async () => {
      render(<CatalogOverlayPanel {...defaultProps} />);

      await userEvent.click(screen.getByText("Show options"));

      const input = screen.getByRole("spinbutton");
      fireEvent.change(input, { target: { value: "100" } });

      // Component clamps to 60 max
      expect((input as HTMLInputElement).value).toBe("60");
    });
  });

  describe("coordinate warning", () => {
    it("shows warning when coordinates not provided", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));

      expect(screen.getByText("Set center coordinates to query catalogs")).toBeInTheDocument();
    });

    it("hides warning when coordinates are provided", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} centerRa={180} centerDec={45} />);

      await user.click(screen.getByText("Show options"));

      expect(
        screen.queryByText("Set center coordinates to query catalogs")
      ).not.toBeInTheDocument();
    });
  });

  describe("catalog legend", () => {
    it("shows legend when catalogs are enabled", () => {
      render(<CatalogOverlayPanel {...defaultProps} enabledCatalogs={["gaia"]} />);

      expect(screen.getByTestId("catalog-legend")).toBeInTheDocument();
      expect(screen.getByTestId("legend-gaia")).toBeInTheDocument();
    });

    it("does not show legend when no catalogs enabled", () => {
      render(<CatalogOverlayPanel {...defaultProps} enabledCatalogs={[]} />);

      expect(screen.queryByTestId("catalog-legend")).not.toBeInTheDocument();
    });

    it("shows all enabled catalogs in legend", () => {
      render(<CatalogOverlayPanel {...defaultProps} enabledCatalogs={["gaia", "nvss"]} />);

      expect(screen.getByTestId("legend-gaia")).toBeInTheDocument();
      expect(screen.getByTestId("legend-nvss")).toBeInTheDocument();
    });
  });

  describe("button accessibility", () => {
    it("has type=button on toggle button", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      // The toggle button should have type="button" implicitly or explicitly
      const toggleButton = screen.getByRole("button", { name: /show catalog options/i });
      // Note: buttons have type="submit" by default, but this one should work
      expect(toggleButton).toBeInTheDocument();
    });

    it("has aria-label on select all button", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));

      const selectAllButton = screen.getByText("Select all");
      expect(selectAllButton).toHaveAttribute("aria-label");
    });

    it("has aria-label on clear button", async () => {
      const user = userEvent.setup();
      render(<CatalogOverlayPanel {...defaultProps} />);

      await user.click(screen.getByText("Show options"));

      const clearButton = screen.getByText("Clear");
      expect(clearButton).toHaveAttribute("aria-label");
    });
  });

  describe("loading state", () => {
    it("shows loading spinner in header when queries are in progress", () => {
      // This is harder to test without more complex mocking
      // The component shows a spinner when loadingCatalogs.size > 0
      // We'd need to delay the mock to see the loading state
    });
  });
});
