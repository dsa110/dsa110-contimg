import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ProvenanceLink from "./ProvenanceLink";

describe("ProvenanceLink", () => {
  describe("rendering links", () => {
    it("renders View Logs link when logsUrl is provided", () => {
      render(<ProvenanceLink logsUrl="/logs/run-123" />);
      const link = screen.getByRole("link", { name: /view logs/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "/logs/run-123");
      expect(link).not.toHaveAttribute("target");
    });

    it("renders QA Report link when qaUrl is provided", () => {
      render(<ProvenanceLink qaUrl="/qa/run-123" />);
      const link = screen.getByRole("link", { name: /qa report/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "/qa/run-123");
    });

    it("renders both links when both URLs are provided", () => {
      render(<ProvenanceLink logsUrl="/logs/run-123" qaUrl="/qa/run-123" />);
      expect(screen.getByRole("link", { name: /view logs/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /qa report/i })).toBeInTheDocument();
    });

    it("renders empty div when no URLs provided", () => {
      const { container } = render(<ProvenanceLink />);
      expect(container.querySelector("div")).toBeInTheDocument();
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
    });
  });

  describe("link attributes", () => {
    it("opens QA report in new tab", () => {
      render(<ProvenanceLink qaUrl="/qa/run-123" />);
      const link = screen.getByRole("link", { name: /qa report/i });
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    });

    it("keeps QA in new tab while logs are inline when both present", () => {
      render(<ProvenanceLink logsUrl="/logs/run-123" qaUrl="/qa/run-123" />);
      const logLink = screen.getByRole("link", { name: /view logs/i });
      const qaLink = screen.getByRole("link", { name: /qa report/i });
      expect(logLink).not.toHaveAttribute("target");
      expect(qaLink).toHaveAttribute("target", "_blank");
    });
  });
});
