import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ImageThumbnail from "./ImageThumbnail";

describe("ImageThumbnail", () => {
  const defaultProps = {
    imageId: "test-img-123",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("renders with correct thumbnail URL", () => {
      render(<ImageThumbnail {...defaultProps} />);
      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("src", expect.stringContaining("/images/test-img-123/thumbnail"));
    });

    it("uses custom apiUrl when provided", () => {
      render(<ImageThumbnail {...defaultProps} apiUrl="http://custom-api.com" />);
      const img = screen.getByRole("img");
      expect(img).toHaveAttribute("src", "http://custom-api.com/images/test-img-123/thumbnail");
    });

    it("applies default alt text", () => {
      render(<ImageThumbnail {...defaultProps} />);
      expect(screen.getByRole("img")).toHaveAttribute("alt", "Image preview");
    });

    it("applies custom alt text", () => {
      render(<ImageThumbnail {...defaultProps} alt="Custom alt text" />);
      expect(screen.getByRole("img")).toHaveAttribute("alt", "Custom alt text");
    });
  });

  describe("size variants", () => {
    it("applies sm size class", () => {
      const { container } = render(<ImageThumbnail {...defaultProps} size="sm" />);
      expect(container.firstChild).toHaveClass("w-24", "h-24");
    });

    it("applies md size class by default", () => {
      const { container } = render(<ImageThumbnail {...defaultProps} />);
      expect(container.firstChild).toHaveClass("w-48", "h-48");
    });

    it("applies lg size class", () => {
      const { container } = render(<ImageThumbnail {...defaultProps} size="lg" />);
      expect(container.firstChild).toHaveClass("w-72", "h-72");
    });
  });

  describe("loading state", () => {
    it("shows loading indicator initially", () => {
      render(<ImageThumbnail {...defaultProps} />);
      expect(screen.getByText("Loading...")).toBeInTheDocument();
    });

    it("hides loading indicator after image loads", async () => {
      render(<ImageThumbnail {...defaultProps} />);

      const img = screen.getByRole("img");
      fireEvent.load(img);

      await waitFor(() => {
        expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
      });
    });
  });

  describe("error state", () => {
    it("shows error placeholder on image load error", async () => {
      render(<ImageThumbnail {...defaultProps} />);

      const img = screen.getByRole("img");
      fireEvent.error(img);

      await waitFor(() => {
        expect(screen.getByText("No preview")).toBeInTheDocument();
      });
    });

    it("hides loading state on error", async () => {
      render(<ImageThumbnail {...defaultProps} />);

      const img = screen.getByRole("img");
      fireEvent.error(img);

      await waitFor(() => {
        expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
      });
    });

    it("hides image on error", async () => {
      render(<ImageThumbnail {...defaultProps} />);

      const img = screen.getByRole("img");
      fireEvent.error(img);

      await waitFor(() => {
        expect(img).toHaveClass("hidden");
      });
    });
  });

  describe("click behavior", () => {
    it("calls onClick when provided and clicked", async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();

      render(<ImageThumbnail {...defaultProps} onClick={handleClick} />);

      // Simulate load first to show the image
      const img = screen.getByRole("img");
      fireEvent.load(img);

      await user.click(screen.getByRole("button"));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("has cursor-pointer when clickable", () => {
      const { container } = render(<ImageThumbnail {...defaultProps} onClick={() => {}} />);
      expect(container.firstChild).toHaveClass("cursor-pointer");
    });

    it("has cursor-pointer when expandable", () => {
      const { container } = render(<ImageThumbnail {...defaultProps} expandable />);
      expect(container.firstChild).toHaveClass("cursor-pointer");
    });

    it("handles keyboard activation with Enter", async () => {
      const handleClick = vi.fn();
      render(<ImageThumbnail {...defaultProps} onClick={handleClick} />);

      const button = screen.getByRole("button");
      fireEvent.keyDown(button, { key: "Enter" });

      expect(handleClick).toHaveBeenCalled();
    });

    it("handles keyboard activation with Space", async () => {
      const handleClick = vi.fn();
      render(<ImageThumbnail {...defaultProps} onClick={handleClick} />);

      const button = screen.getByRole("button");
      fireEvent.keyDown(button, { key: " " });

      expect(handleClick).toHaveBeenCalled();
    });
  });

  describe("expandable behavior", () => {
    it("is expandable by default", () => {
      const { container } = render(<ImageThumbnail {...defaultProps} />);
      expect(container.firstChild).toHaveAttribute("role", "button");
    });

    it("shows expand indicator after image loads", async () => {
      const { container } = render(<ImageThumbnail {...defaultProps} expandable />);

      const img = screen.getByRole("img");
      fireEvent.load(img);

      await waitFor(() => {
        // Look for the expand icon container
        const expandIcon = container.querySelector(".absolute.bottom-1.right-1");
        expect(expandIcon).toBeInTheDocument();
      });
    });

    it("does not show expand indicator on error", async () => {
      const { container } = render(<ImageThumbnail {...defaultProps} expandable />);

      const img = screen.getByRole("img");
      fireEvent.error(img);

      await waitFor(() => {
        const expandIcon = container.querySelector(".absolute.bottom-1.right-1");
        expect(expandIcon).not.toBeInTheDocument();
      });
    });

    it("opens modal when clicked (expandable mode)", async () => {
      const user = userEvent.setup();
      render(<ImageThumbnail {...defaultProps} expandable />);

      // Load image first
      const img = screen.getByRole("img");
      fireEvent.load(img);

      // Click to expand
      await user.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });

    it("closes modal when clicking close button", async () => {
      const user = userEvent.setup();
      render(<ImageThumbnail {...defaultProps} expandable />);

      const img = screen.getByRole("img");
      fireEvent.load(img);

      // Open modal
      await user.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Close modal
      await user.click(screen.getByLabelText("Close"));

      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
    });

    it("closes modal when clicking backdrop", async () => {
      const user = userEvent.setup();
      render(<ImageThumbnail {...defaultProps} expandable />);

      const img = screen.getByRole("img");
      fireEvent.load(img);

      // Open modal
      await user.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Click backdrop
      await user.click(screen.getByRole("dialog"));

      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
    });

    it("disables expand behavior when expandable=false", () => {
      const { container } = render(<ImageThumbnail {...defaultProps} expandable={false} />);
      expect(container.firstChild).not.toHaveAttribute("role", "button");
    });
  });

  describe("modal content", () => {
    it("shows full-size image in modal", async () => {
      const user = userEvent.setup();
      render(<ImageThumbnail {...defaultProps} expandable />);

      const img = screen.getByRole("img");
      fireEvent.load(img);

      await user.click(screen.getByRole("button"));

      await waitFor(() => {
        const modalImages = screen.getAllByRole("img");
        // Should have at least 2 images: thumbnail and modal
        expect(modalImages.length).toBeGreaterThanOrEqual(2);
      });
    });

    it("modal image uses same URL as thumbnail", async () => {
      const user = userEvent.setup();
      render(<ImageThumbnail {...defaultProps} expandable />);

      const img = screen.getByRole("img");
      fireEvent.load(img);

      await user.click(screen.getByRole("button"));

      await waitFor(() => {
        const images = screen.getAllByRole("img");
        const modalImg = images[images.length - 1];
        expect(modalImg).toHaveAttribute(
          "src",
          expect.stringContaining("/images/test-img-123/thumbnail")
        );
      });
    });
  });

  describe("accessibility", () => {
    it("has correct tabIndex when interactive", () => {
      render(<ImageThumbnail {...defaultProps} expandable />);
      expect(screen.getByRole("button")).toHaveAttribute("tabIndex", "0");
    });

    it("has no tabIndex when not interactive", () => {
      const { container } = render(<ImageThumbnail {...defaultProps} expandable={false} />);
      expect(container.firstChild).not.toHaveAttribute("tabIndex");
    });

    it("modal has aria-modal attribute", async () => {
      const user = userEvent.setup();
      render(<ImageThumbnail {...defaultProps} expandable />);

      fireEvent.load(screen.getByRole("img"));
      await user.click(screen.getByRole("button"));

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
      });
    });
  });
});
