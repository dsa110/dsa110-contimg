import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ErrorDetailsExpander from "./ErrorDetailsExpander";

describe("ErrorDetailsExpander", () => {
  describe("rendering", () => {
    it("returns null when details is empty and no traceId", () => {
      const { container } = render(<ErrorDetailsExpander details={{}} />);
      expect(container.firstChild).toBeNull();
    });

    it("renders when details has content", () => {
      render(<ErrorDetailsExpander details={{ field: "value" }} />);
      expect(screen.getByRole("button", { name: /show details/i })).toBeInTheDocument();
    });

    it("renders when traceId is provided", () => {
      render(<ErrorDetailsExpander details={{}} traceId="trace-123" />);
      expect(screen.getByRole("button", { name: /show details/i })).toBeInTheDocument();
    });
  });

  describe("expand/collapse behavior", () => {
    it("starts collapsed", () => {
      render(<ErrorDetailsExpander details={{ field: "value" }} />);
      expect(screen.getByRole("button")).toHaveTextContent("Show Details");
      expect(screen.queryByText(/"field"/)).not.toBeInTheDocument();
    });

    it("expands when button clicked", async () => {
      render(<ErrorDetailsExpander details={{ field: "value" }} />);
      await userEvent.click(screen.getByRole("button"));
      expect(screen.getByRole("button")).toHaveTextContent("Hide Details");
    });

    it("shows details content when expanded", async () => {
      render(<ErrorDetailsExpander details={{ field: "value" }} />);
      await userEvent.click(screen.getByRole("button"));
      expect(screen.getByText(/"field":/)).toBeInTheDocument();
      expect(screen.getByText(/"value"/)).toBeInTheDocument();
    });

    it("collapses when button clicked again", async () => {
      render(<ErrorDetailsExpander details={{ field: "value" }} />);
      await userEvent.click(screen.getByRole("button")); // expand
      await userEvent.click(screen.getByRole("button")); // collapse
      expect(screen.getByRole("button")).toHaveTextContent("Show Details");
      expect(screen.queryByText(/"field"/)).not.toBeInTheDocument();
    });
  });

  describe("content display", () => {
    it("shows JSON formatted details", async () => {
      const details = { key1: "value1", nested: { key2: "value2" } };
      render(<ErrorDetailsExpander details={details} />);
      await userEvent.click(screen.getByRole("button"));
      // Should show formatted JSON
      expect(screen.getByText(/"key1":/)).toBeInTheDocument();
      expect(screen.getByText(/"nested":/)).toBeInTheDocument();
    });

    it("shows trace ID when provided", async () => {
      render(<ErrorDetailsExpander details={{}} traceId="trace-abc-123" />);
      await userEvent.click(screen.getByRole("button"));
      expect(screen.getByText(/trace id:/i)).toBeInTheDocument();
      expect(screen.getByText(/trace-abc-123/)).toBeInTheDocument();
    });

    it("shows both details and trace ID", async () => {
      render(<ErrorDetailsExpander details={{ error: "test" }} traceId="trace-xyz" />);
      await userEvent.click(screen.getByRole("button"));
      expect(screen.getByText(/"error":/)).toBeInTheDocument();
      expect(screen.getByText(/trace-xyz/)).toBeInTheDocument();
    });
  });
});
