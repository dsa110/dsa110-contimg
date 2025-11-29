import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import AladinLiteViewer from "../components/widgets/AladinLiteViewer";

describe("AladinLiteViewer", () => {
  beforeEach(() => {
    // @ts-expect-error allow reassignment in tests
    delete window.A;
  });

  it("defers loading until the user requests it", async () => {
    const aladinMock = vi.fn().mockReturnValue({
      gotoRaDec: vi.fn(),
      setFoV: vi.fn(),
      setImageSurvey: vi.fn(),
      addCatalog: vi.fn(),
      increaseZoom: vi.fn(),
      decreaseZoom: vi.fn(),
      toggleFullscreen: vi.fn(),
    });

    // Preload stub so the component doesn't try to fetch scripts in tests
    // @ts-expect-error adding test stub
    window.A = { aladin: aladinMock };

    const { getByRole, queryByText } = render(
      <AladinLiteViewer raDeg={10} decDeg={-5} height={300} />
    );

    expect(queryByText(/Load viewer/i)).toBeInTheDocument();
    fireEvent.click(getByRole("button", { name: /Load sky viewer/i }));

    await waitFor(() => expect(aladinMock).toHaveBeenCalled());
  });
});
