/**
 * @vitest-environment jsdom
 */
import React, { useEffect } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { render, waitFor, screen } from "@testing-library/react";
import LogsPage from "./LogsPage";
import type { LogViewerProps } from "../components/logs/LogViewer";

let lastProps: LogViewerProps | null = null;
let shouldTriggerQueryChange = false;

vi.mock("../components/logs/LogViewer", () => {
  const MockLogViewer = (props: LogViewerProps) => {
    lastProps = props;
    const calledRef = React.useRef(false);
    useEffect(() => {
      if (!shouldTriggerQueryChange || calledRef.current) return;
      calledRef.current = true;
      props.onQueryChange?.({
        ...(props.initialQuery ?? {}),
        q: "updated",
        labels: { ...(props.initialQuery?.labels ?? {}), service: "api" },
      });
    }, [props]);
    return <div data-testid="mock-log-viewer" />;
  };
  return { __esModule: true, default: MockLogViewer };
});

function LocationSpy({
  onChange,
}: {
  onChange: (path: string, search: string) => void;
}) {
  const location = useLocation();
  useEffect(() => {
    onChange(location.pathname, location.search);
  }, [location, onChange]);
  return null;
}

describe("LogsPage", () => {
  beforeEach(() => {
    lastProps = null;
    shouldTriggerQueryChange = false;
  });

  it("parses runId and search params into initial query", () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/logs/run-42?service=scheduler&q=error&level=error,warning&start=2024-01-01",
        ]}
      >
        <Routes>
          <Route path="/logs/:runId" element={<LogsPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(lastProps?.initialQuery).toMatchObject({
      q: "error",
      level: ["error", "warning"],
      labels: { service: "scheduler", run_id: "run-42" },
      range: { start: "2024-01-01" },
    });
  });

  it("updates URL search params when query changes", async () => {
    shouldTriggerQueryChange = true;
    let currentPath = "";
    let currentSearch = "";

    render(
      <MemoryRouter initialEntries={["/logs/run-99"]}>
        <Routes>
          <Route
            path="/logs/:runId"
            element={
              <>
                <LogsPage />
                <LocationSpy
                  onChange={(path, search) => {
                    currentPath = path;
                    currentSearch = search;
                  }}
                />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId("mock-log-viewer")).toBeInTheDocument();

    await waitFor(() => {
      expect(currentPath).toBe("/logs/run-99");
      expect(currentSearch).toContain("q=updated");
      expect(currentSearch).toContain("service=api");
    });
  });
});
