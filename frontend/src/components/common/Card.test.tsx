import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Card from "./Card";

describe("Card", () => {
  describe("basic rendering", () => {
    it("renders children content", () => {
      render(<Card>Test content</Card>);
      expect(screen.getByText("Test content")).toBeInTheDocument();
    });

    it("renders with card class", () => {
      const { container } = render(<Card>Content</Card>);
      expect(container.firstChild).toHaveClass("card");
    });
  });

  describe("title and subtitle", () => {
    it("renders title when provided", () => {
      render(<Card title="Card Title">Content</Card>);
      expect(screen.getByText("Card Title")).toBeInTheDocument();
    });

    it("does not render title element when not provided", () => {
      render(<Card>Content</Card>);
      expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    });

    it("renders subtitle when provided", () => {
      render(
        <Card title="Title" subtitle="Card Subtitle">
          Content
        </Card>
      );
      expect(screen.getByText("Card Subtitle")).toBeInTheDocument();
    });

    it("renders subtitle as ReactNode", () => {
      render(
        <Card title="Title" subtitle={<button>Action</button>}>
          Content
        </Card>
      );
      expect(screen.getByRole("button", { name: "Action" })).toBeInTheDocument();
    });

    it("does not render header when no title or actions", () => {
      const { container } = render(<Card>Content</Card>);
      // Should only have the content, no header div
      expect(container.querySelector(".flex.items-start")).not.toBeInTheDocument();
    });
  });

  describe("actions", () => {
    it("renders actions in header when provided", () => {
      render(
        <Card title="Title" actions={<button>Edit</button>}>
          Content
        </Card>
      );
      expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    });

    it("renders multiple action buttons", () => {
      render(
        <Card
          title="Title"
          actions={
            <>
              <button>Edit</button>
              <button>Delete</button>
            </>
          }
        >
          Content
        </Card>
      );
      expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
    });

    it("renders header when only actions provided (no title)", () => {
      render(<Card actions={<button>Action</button>}>Content</Card>);
      expect(screen.getByRole("button", { name: "Action" })).toBeInTheDocument();
    });
  });

  describe("padding variants", () => {
    it("applies no padding when padding=none", () => {
      const { container } = render(<Card padding="none">Content</Card>);
      expect(container.firstChild).not.toHaveClass("p-3");
      expect(container.firstChild).not.toHaveClass("p-4");
      expect(container.firstChild).not.toHaveClass("p-6");
    });

    it("applies sm padding when padding=sm", () => {
      const { container } = render(<Card padding="sm">Content</Card>);
      expect(container.firstChild).toHaveClass("p-3");
    });

    it("applies md padding by default", () => {
      const { container } = render(<Card>Content</Card>);
      expect(container.firstChild).toHaveClass("p-4");
    });

    it("applies lg padding when padding=lg", () => {
      const { container } = render(<Card padding="lg">Content</Card>);
      expect(container.firstChild).toHaveClass("p-6");
    });
  });

  describe("hoverable state", () => {
    it("does not have hover classes by default", () => {
      const { container } = render(<Card>Content</Card>);
      expect(container.firstChild).not.toHaveClass("hover:shadow-md");
    });

    it("applies hover classes when hoverable=true", () => {
      const { container } = render(<Card hoverable>Content</Card>);
      expect(container.firstChild).toHaveClass("hover:shadow-md");
      expect(container.firstChild).toHaveClass("cursor-pointer");
    });
  });

  describe("custom className", () => {
    it("applies custom className", () => {
      const { container } = render(<Card className="my-custom-class">Content</Card>);
      expect(container.firstChild).toHaveClass("my-custom-class");
    });

    it("combines custom className with default classes", () => {
      const { container } = render(
        <Card className="custom-class" padding="lg">
          Content
        </Card>
      );
      expect(container.firstChild).toHaveClass("card");
      expect(container.firstChild).toHaveClass("p-6");
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("complex usage", () => {
    it("renders card with all props", () => {
      render(
        <Card
          title="Full Card"
          subtitle="With all features"
          actions={<button>Settings</button>}
          padding="lg"
          hoverable
          className="featured-card"
        >
          <p>Card body content</p>
        </Card>
      );

      expect(screen.getByText("Full Card")).toBeInTheDocument();
      expect(screen.getByText("With all features")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
      expect(screen.getByText("Card body content")).toBeInTheDocument();
    });

    it("renders nested cards", () => {
      render(
        <Card title="Outer">
          <Card title="Inner">Nested content</Card>
        </Card>
      );

      expect(screen.getByText("Outer")).toBeInTheDocument();
      expect(screen.getByText("Inner")).toBeInTheDocument();
      expect(screen.getByText("Nested content")).toBeInTheDocument();
    });
  });
});
