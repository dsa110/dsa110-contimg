import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import ErrorDisplay from "./ErrorDisplay";

describe("ErrorDisplay", () => {
  const mockError = {
    code: "CAL_TABLE_MISSING",
    http_status: 400,
    user_message: "Calibration table missing for MS /data/ms/foo.ms",
    action: "Re-run calibration for this MS or select an existing table",
    ref_id: "job-98213-abc",
    details: { path: "/data/ms/foo.ms" },
    trace_id: "c8f7ef",
    doc_anchor: "calibration_missing_table",
  };

  it("renders mapped user message and action", () => {
    render(<ErrorDisplay error={mockError} />);
    // Uses mapped message from errorMappings (not the raw backend message)
    expect(screen.getByText(/Calibration table not found/i)).toBeInTheDocument();
    expect(screen.getByText(/Re-run calibration or choose/i)).toBeInTheDocument();
  });

  it("shows details when expanded", () => {
    render(<ErrorDisplay error={mockError} />);
    fireEvent.click(screen.getByText("Show Details"));
    expect(screen.getByText(/\/data\/ms\/foo\.ms/)).toBeInTheDocument();
    expect(screen.getByText(/Trace ID: c8f7ef/)).toBeInTheDocument();
  });

  it("renders action links when ref_id and doc_anchor provided", () => {
    render(<ErrorDisplay error={mockError} />);
    expect(screen.getByText("View logs")).toHaveAttribute("href", "/logs/job-98213-abc");
    expect(screen.getByText("Troubleshoot")).toHaveAttribute(
      "href",
      "/docs#calibration_missing_table"
    );
  });

  it("handles unknown error codes gracefully", () => {
    const unknownError = { ...mockError, code: "UNKNOWN_CODE" };
    render(<ErrorDisplay error={unknownError} />);
    expect(screen.getByText("Request failed")).toBeInTheDocument();
    expect(screen.getByText("Please try again later")).toBeInTheDocument();
  });

  it("hides details expander when no details or trace_id", () => {
    const errorNoDetails = { ...mockError, details: undefined, trace_id: undefined };
    render(<ErrorDisplay error={errorNoDetails} />);
    expect(screen.queryByText("Show Details")).not.toBeInTheDocument();
  });

  it("hides action links when no ref_id or doc_anchor", () => {
    // Use an unknown code so the mapper falls back (no doc_anchor in fallback)
    const errorNoLinks = {
      code: "UNKNOWN_CODE",
      http_status: 500,
      user_message: "Some error",
      action: "Try again",
      ref_id: "",
    };
    render(<ErrorDisplay error={errorNoLinks} />);
    expect(screen.queryByText("View logs")).not.toBeInTheDocument();
    expect(screen.queryByText("Troubleshoot")).not.toBeInTheDocument();
  });
});
