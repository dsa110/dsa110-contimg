import React from "react";
import { render } from "@testing-library/react";
import ProvenanceStrip from "./ProvenanceStrip";

describe("ProvenanceStrip", () => {
  it("renders without crashing", () => {
    const { container } = render(<ProvenanceStrip />);
    expect(container).toBeInTheDocument();
  });

  it("displays runId when provided", () => {
    const { getByText } = render(<ProvenanceStrip runId="job-123" />);
    expect(getByText(/Run:/i)).toBeInTheDocument();
    expect(getByText(/job-123/i)).toBeInTheDocument();
  });

  it("displays MS path when provided", () => {
    const { getByText } = render(<ProvenanceStrip msPath="/data/ms/foo.ms" />);
    expect(getByText(/foo\.ms/i)).toBeInTheDocument();
  });

  it("displays calibration table when provided", () => {
    const { getByText } = render(<ProvenanceStrip calTable="cal_table_1" />);
    expect(getByText(/cal_table_1/i)).toBeInTheDocument();
  });

  it("displays pointing coordinates when provided", () => {
    const { getByText } = render(
      <ProvenanceStrip pointingRaDeg={123.456} pointingDecDeg={-45.678} />
    );
    // Check that pointing label and coordinates are present (exact format depends on formatRA/formatDec)
    expect(getByText(/Pointing:/i)).toBeInTheDocument();
    expect(getByText(/RA/i)).toBeInTheDocument();
    expect(getByText(/Dec/i)).toBeInTheDocument();
  });

  it("displays QA badge when provided", () => {
    const { getByText } = render(
      <ProvenanceStrip qaGrade="good" qaSummary="RMS 0.35 mJy, DR 1200" />
    );
    expect(getByText(/QA:/i)).toBeInTheDocument();
    expect(getByText(/Good/i)).toBeInTheDocument();
  });

  it("displays createdAt date in relative time", () => {
    const { getByText } = render(<ProvenanceStrip createdAt="2023-10-01T12:00:00Z" />);
    expect(getByText(/Created:/i)).toBeInTheDocument();
    expect(getByText(/ago/i)).toBeInTheDocument();
  });

  it("hides fields that are not provided", () => {
    const { queryByText } = render(<ProvenanceStrip />);
    expect(queryByText(/Run:/i)).not.toBeInTheDocument();
    expect(queryByText(/MS:/i)).not.toBeInTheDocument();
    expect(queryByText(/Cal:/i)).not.toBeInTheDocument();
    expect(queryByText(/Pointing:/i)).not.toBeInTheDocument();
    expect(queryByText(/QA:/i)).not.toBeInTheDocument();
    expect(queryByText(/Created:/i)).not.toBeInTheDocument();
  });
});
