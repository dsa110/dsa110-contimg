import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Modal from "./Modal";

describe("Modal", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    title: "Test Modal",
    children: <p>Modal content</p>,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Reset body overflow style
    document.body.style.overflow = "";
  });

  describe("basic rendering", () => {
    it("renders when isOpen is true", () => {
      render(<Modal {...defaultProps} />);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("does not render when isOpen is false", () => {
      render(<Modal {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("renders title", () => {
      render(<Modal {...defaultProps} />);
      expect(screen.getByText("Test Modal")).toBeInTheDocument();
    });

    it("renders children content", () => {
      render(<Modal {...defaultProps} />);
      expect(screen.getByText("Modal content")).toBeInTheDocument();
    });

    it("has correct aria attributes", () => {
      render(<Modal {...defaultProps} />);
      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
      expect(dialog).toHaveAttribute("aria-labelledby", "modal-title");
    });
  });

  describe("close button", () => {
    it("renders close button", () => {
      render(<Modal {...defaultProps} />);
      expect(screen.getByLabelText("Close modal")).toBeInTheDocument();
    });

    it("calls onClose when close button is clicked", async () => {
      const user = userEvent.setup();
      render(<Modal {...defaultProps} />);

      await user.click(screen.getByLabelText("Close modal"));

      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("escape key", () => {
    it("closes on Escape key by default", () => {
      render(<Modal {...defaultProps} />);

      fireEvent.keyDown(document, { key: "Escape" });

      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
    });

    it("does not close on Escape when closeOnEscape is false", () => {
      render(<Modal {...defaultProps} closeOnEscape={false} />);

      fireEvent.keyDown(document, { key: "Escape" });

      expect(defaultProps.onClose).not.toHaveBeenCalled();
    });

    it("removes event listener when modal closes", () => {
      const { rerender } = render(<Modal {...defaultProps} />);

      rerender(<Modal {...defaultProps} isOpen={false} />);

      fireEvent.keyDown(document, { key: "Escape" });

      // onClose should not be called after modal is closed
      expect(defaultProps.onClose).not.toHaveBeenCalled();
    });
  });

  describe("outside click", () => {
    it("closes when clicking outside (backdrop)", async () => {
      const user = userEvent.setup();
      render(<Modal {...defaultProps} />);

      // Click the backdrop (the dialog element itself with bg-black bg-opacity-50)
      const backdrop = screen.getByRole("dialog");
      await user.click(backdrop);

      expect(defaultProps.onClose).toHaveBeenCalled();
    });

    it("does not close when clicking modal content", async () => {
      const user = userEvent.setup();
      render(<Modal {...defaultProps} />);

      await user.click(screen.getByText("Modal content"));

      expect(defaultProps.onClose).not.toHaveBeenCalled();
    });

    it("does not close on outside click when closeOnOutsideClick is false", async () => {
      const user = userEvent.setup();
      render(<Modal {...defaultProps} closeOnOutsideClick={false} />);

      const backdrop = screen.getByRole("dialog");
      await user.click(backdrop);

      expect(defaultProps.onClose).not.toHaveBeenCalled();
    });
  });

  describe("size variants", () => {
    it("applies sm size class", () => {
      render(<Modal {...defaultProps} size="sm" />);
      // Size classes are on the inner modal content div, not the backdrop
      const modalContent = screen.getByRole("dialog").querySelector(".bg-white.rounded-lg");
      expect(modalContent).toHaveClass("max-w-sm");
    });

    it("applies md size class by default", () => {
      render(<Modal {...defaultProps} />);
      const modalContent = screen.getByRole("dialog").querySelector(".bg-white.rounded-lg");
      expect(modalContent).toHaveClass("max-w-md");
    });

    it("applies lg size class", () => {
      render(<Modal {...defaultProps} size="lg" />);
      const modalContent = screen.getByRole("dialog").querySelector(".bg-white.rounded-lg");
      expect(modalContent).toHaveClass("max-w-lg");
    });

    it("applies xl size class", () => {
      render(<Modal {...defaultProps} size="xl" />);
      const modalContent = screen.getByRole("dialog").querySelector(".bg-white.rounded-lg");
      expect(modalContent).toHaveClass("max-w-xl");
    });
  });

  describe("footer", () => {
    it("renders footer when provided", () => {
      render(
        <Modal {...defaultProps} footer={<button>Save</button>}>
          Content
        </Modal>
      );
      expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    });

    it("does not render footer section when not provided", () => {
      const { container } = render(<Modal {...defaultProps} />);
      expect(
        container.querySelector(".border-t.border-gray-200.bg-gray-50")
      ).not.toBeInTheDocument();
    });

    it("renders multiple footer buttons", () => {
      render(
        <Modal
          {...defaultProps}
          footer={
            <>
              <button>Cancel</button>
              <button>Confirm</button>
            </>
          }
        >
          Content
        </Modal>
      );
      expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument();
    });
  });

  describe("body scroll lock", () => {
    it("locks body scroll when modal opens", () => {
      render(<Modal {...defaultProps} />);
      expect(document.body.style.overflow).toBe("hidden");
    });

    it("restores body scroll when modal closes", () => {
      const { rerender } = render(<Modal {...defaultProps} />);
      expect(document.body.style.overflow).toBe("hidden");

      rerender(<Modal {...defaultProps} isOpen={false} />);
      expect(document.body.style.overflow).toBe("");
    });

    it("restores body scroll on unmount", () => {
      const { unmount } = render(<Modal {...defaultProps} />);
      expect(document.body.style.overflow).toBe("hidden");

      unmount();
      expect(document.body.style.overflow).toBe("");
    });
  });

  describe("custom className", () => {
    it("applies custom className to modal content", () => {
      render(<Modal {...defaultProps} className="custom-modal-class" />);
      // Custom class is applied to the inner modal content div, not the backdrop
      const modalContent = screen.getByRole("dialog").querySelector(".bg-white.rounded-lg");
      expect(modalContent).toHaveClass("custom-modal-class");
    });

    it("combines custom className with default classes", () => {
      render(<Modal {...defaultProps} className="my-class" />);
      const modalContent = screen.getByRole("dialog").querySelector(".bg-white.rounded-lg");
      expect(modalContent).toHaveClass("my-class");
      expect(modalContent).toHaveClass("bg-white");
      expect(modalContent).toHaveClass("rounded-lg");
    });
  });

  describe("focus management", () => {
    it("focuses the modal when opened", async () => {
      render(<Modal {...defaultProps} />);

      await waitFor(() => {
        // The focusable element is the inner modal content div
        const dialog = screen.getByRole("dialog");
        const focusableContent = dialog.querySelector('[tabindex="-1"]');
        expect(document.activeElement).toBe(focusableContent);
      });
    });

    it("modal content has tabIndex for focus", () => {
      render(<Modal {...defaultProps} />);
      const dialog = screen.getByRole("dialog");
      const focusableContent = dialog.querySelector('[tabindex="-1"]');
      expect(focusableContent).toBeInTheDocument();
    });
  });
  describe("backdrop styling", () => {
    it("has semi-transparent backdrop", () => {
      const { container } = render(<Modal {...defaultProps} />);
      const backdrop = container.querySelector(".fixed.inset-0");
      expect(backdrop).toHaveClass("bg-black", "bg-opacity-50");
    });

    it("has high z-index for overlay", () => {
      const { container } = render(<Modal {...defaultProps} />);
      const backdrop = container.querySelector(".fixed.inset-0");
      expect(backdrop).toHaveClass("z-50");
    });
  });

  describe("content overflow", () => {
    it("has scrollable body content", () => {
      const { container } = render(
        <Modal {...defaultProps}>
          <div style={{ height: "2000px" }}>Tall content</div>
        </Modal>
      );
      const body = container.querySelector(".overflow-y-auto");
      expect(body).toBeInTheDocument();
    });

    it("limits body height", () => {
      const { container } = render(<Modal {...defaultProps} />);
      const body = container.querySelector(".max-h-\\[60vh\\]");
      expect(body).toBeInTheDocument();
    });
  });

  describe("complex scenarios", () => {
    it("handles form submission in modal", async () => {
      const handleSubmit = vi.fn((e) => e.preventDefault());
      const user = userEvent.setup();

      render(
        <Modal
          {...defaultProps}
          footer={
            <button type="submit" form="modal-form">
              Submit
            </button>
          }
        >
          <form id="modal-form" onSubmit={handleSubmit}>
            <input type="text" placeholder="Enter name" />
          </form>
        </Modal>
      );

      await user.type(screen.getByPlaceholderText("Enter name"), "Test");
      await user.click(screen.getByRole("button", { name: "Submit" }));

      expect(handleSubmit).toHaveBeenCalled();
    });

    it("multiple modals do not interfere", () => {
      const onClose1 = vi.fn();
      const onClose2 = vi.fn();

      render(
        <>
          <Modal isOpen={true} onClose={onClose1} title="Modal 1">
            Content 1
          </Modal>
          <Modal isOpen={true} onClose={onClose2} title="Modal 2">
            Content 2
          </Modal>
        </>
      );

      expect(screen.getAllByRole("dialog")).toHaveLength(2);
      expect(screen.getByText("Modal 1")).toBeInTheDocument();
      expect(screen.getByText("Modal 2")).toBeInTheDocument();
    });
  });
});
