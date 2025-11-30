import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ProvenanceBadge from "./ProvenanceBadge";

describe("ProvenanceBadge", () => {
  describe("rendering based on qaGrade", () => {
    it("renders 'Good' with success badge for good grade", () => {
      render(<ProvenanceBadge qaGrade="good" />);
      const badge = screen.getByText("Good");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("badge-success");
    });

    it("renders 'Warn' with warning badge for warn grade", () => {
      render(<ProvenanceBadge qaGrade="warn" />);
      const badge = screen.getByText("Warn");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("badge-warning");
    });

    it("renders 'Fail' with danger badge for fail grade", () => {
      render(<ProvenanceBadge qaGrade="fail" />);
      const badge = screen.getByText("Fail");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("badge-danger");
    });

    it("renders 'Unknown' with secondary badge for null grade", () => {
      render(<ProvenanceBadge qaGrade={null} />);
      const badge = screen.getByText("Unknown");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("badge-secondary");
    });

    it("renders 'Unknown' with secondary badge when qaGrade is undefined", () => {
      render(<ProvenanceBadge />);
      const badge = screen.getByText("Unknown");
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass("badge-secondary");
    });
  });

  describe("tooltip/title", () => {
    it("shows qaSummary in title when provided", () => {
      render(<ProvenanceBadge qaGrade="good" qaSummary="All calibrations passed" />);
      const badge = screen.getByText("Good");
      expect(badge).toHaveAttribute("title", "All calibrations passed");
    });

    it("shows default message when qaSummary not provided", () => {
      render(<ProvenanceBadge qaGrade="good" />);
      const badge = screen.getByText("Good");
      expect(badge).toHaveAttribute("title", "No QA summary available");
    });
  });

  describe("capitalization", () => {
    it("capitalizes first letter of grade", () => {
      render(<ProvenanceBadge qaGrade="fail" />);
      expect(screen.getByText("Fail")).toBeInTheDocument();
    });
  });
});
