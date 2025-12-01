import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import LightCurveChart from "../components/widgets/LightCurveChart";

const setOptionMock = vi.fn();
const onMock = vi.fn();
const offMock = vi.fn();
const initMock = vi.fn(() => ({
  setOption: setOptionMock,
  resize: vi.fn(),
  dispose: vi.fn(),
  on: onMock,
  off: offMock,
  dispatchAction: vi.fn(),
}));

vi.mock("../lib/loadEcharts", () => ({
  loadEcharts: vi.fn(async () => ({
    init: initMock,
  })),
}));

describe("LightCurveChart", () => {
  beforeEach(() => {
    setOptionMock.mockReset();
    onMock.mockReset();
    offMock.mockReset();
    initMock.mockReset().mockImplementation(() => ({
      setOption: setOptionMock,
      resize: vi.fn(),
      dispose: vi.fn(),
      on: onMock,
      off: offMock,
      dispatchAction: vi.fn(),
    }));
  });

  it("escapes tooltip content to prevent HTML injection", async () => {
    const data = [
      {
        time: "2024-01-01T00:00:00Z",
        flux: 1,
        label: '<img src=x onerror="alert(1)">',
        fluxError: 0.1,
      },
    ];

    render(<LightCurveChart data={data} autoLoad />);

    await waitFor(() => expect(setOptionMock).toHaveBeenCalled());

    const option = setOptionMock.mock.calls[0][0];
    const html = option.tooltip.formatter({ data: [Date.parse(data[0].time), 1], dataIndex: 0 });

    expect(html).toContain("&lt;img");
    expect(html).not.toContain("<img");
    expect(html).toContain("±");
  });
});
