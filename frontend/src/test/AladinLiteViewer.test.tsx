import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import AladinLiteViewer from "../components/widgets/AladinLiteViewer";

// Mock the aladin-lite module
vi.mock("aladin-lite", () => {
  const aladinMock = vi.fn().mockReturnValue({
    gotoRaDec: vi.fn(),
    setFoV: vi.fn(),
    setImageSurvey: vi.fn(),
    addCatalog: vi.fn(),
    increaseZoom: vi.fn(),
    decreaseZoom: vi.fn(),
    toggleFullscreen: vi.fn(),
    destroy: vi.fn(), // Mock the destroy method to prevent errors on cleanup
  });
  return {
    default: {
      init: Promise.resolve(),
      aladin: aladinMock,
      catalog: vi.fn().mockReturnValue({
        addSources: vi.fn(),
        removeSources: vi.fn(),
        hide: vi.fn(),
        show: vi.fn(),
        getSources: vi.fn().mockReturnValue([]),
      }),
      source: vi.fn().mockImplementation((ra, dec, data) => ({ ra, dec, data })),
    },
  };
});

describe("AladinLiteViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("defers loading until the user requests it", async () => {
    const { getByRole, queryByText } = render(
      <AladinLiteViewer raDeg={10} decDeg={-5} height={300} />
    );

    expect(queryByText(/Load viewer/i)).toBeInTheDocument();
    fireEvent.click(getByRole("button", { name: /Load sky viewer/i }));

    // The viewer should start loading after the button is clicked
    await waitFor(() => {
      // Either the loading state or the viewer should be present
      const loadingText = queryByText(/Loading sky viewer/i);
      const coordinateDisplay = queryByText(/10\.0000°/);
      expect(loadingText || coordinateDisplay).toBeTruthy();
    });
  });
});
