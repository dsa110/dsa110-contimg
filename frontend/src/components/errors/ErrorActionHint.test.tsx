import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ErrorActionHint from "./ErrorActionHint";

describe("ErrorActionHint", () => {
  describe("rendering", () => {
    it("returns null when no props provided", () => {
      const { container } = render(<ErrorActionHint />);
      expect(container.firstChild).toBeNull();
    });

    it("returns null when both props are undefined", () => {
      const { container } = render(<ErrorActionHint refId={undefined} docAnchor={undefined} />);
      expect(container.firstChild).toBeNull();
    });
  });

  describe("View logs link", () => {
    it("renders View logs link when refId is provided", () => {
      render(<ErrorActionHint refId="error-123" />);
      const link = screen.getByRole("link", { name: /view logs/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "/logs/error-123");
    });

    it("does not render View logs link when refId is not provided", () => {
      render(<ErrorActionHint docAnchor="network-errors" />);
      expect(screen.queryByRole("link", { name: /view logs/i })).not.toBeInTheDocument();
    });
  });

  describe("Troubleshoot link", () => {
    it("renders Troubleshoot link when docAnchor is provided", () => {
      render(<ErrorActionHint docAnchor="network-errors" />);
      const link = screen.getByRole("link", { name: /troubleshoot/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "/docs#network-errors");
    });

    it("does not render Troubleshoot link when docAnchor is not provided", () => {
      render(<ErrorActionHint refId="error-123" />);
      expect(screen.queryByRole("link", { name: /troubleshoot/i })).not.toBeInTheDocument();
    });
  });

  describe("both links", () => {
    it("renders both links when both props are provided", () => {
      render(<ErrorActionHint refId="error-123" docAnchor="network-errors" />);
      expect(screen.getByRole("link", { name: /view logs/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /troubleshoot/i })).toBeInTheDocument();
    });
  });
});
