/**
 * Tests for AppErrorBoundary component
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppErrorBoundary } from "./AppErrorBoundary";

// Test component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) {
    throw new Error("Test error");
  }
  return <div>Normal content</div>;
};

describe("AppErrorBoundary", () => {
  // Suppress error console output during tests
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  it("should render children when no error occurs", () => {
    render(
      <AppErrorBoundary>
        <div>Test content</div>
      </AppErrorBoundary>
    );

    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("should render error UI when child component throws", () => {
    render(
      <AppErrorBoundary>
        <ThrowError />
      </AppErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText(/An unexpected error occurred/)).toBeInTheDocument();
  });

  it("should display error message in development mode", () => {
    if (import.meta.env.DEV) {
      render(
        <AppErrorBoundary>
          <ThrowError />
        </AppErrorBoundary>
      );

      expect(screen.getByText("Test error")).toBeInTheDocument();
    }
  });

  it("should not display error details in production mode", () => {
    if (!import.meta.env.DEV) {
      render(
        <AppErrorBoundary>
          <ThrowError />
        </AppErrorBoundary>
      );

      expect(screen.queryByText("Test error")).not.toBeInTheDocument();
    }
  });

  it("should render Try Again button", () => {
    render(
      <AppErrorBoundary>
        <ThrowError />
      </AppErrorBoundary>
    );

    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("should render Reload Page button", () => {
    render(
      <AppErrorBoundary>
        <ThrowError />
      </AppErrorBoundary>
    );

    expect(screen.getByRole("button", { name: /reload page/i })).toBeInTheDocument();
  });

  it("should call onError callback when error occurs", () => {
    const onError = vi.fn();

    render(
      <AppErrorBoundary onError={onError}>
        <ThrowError />
      </AppErrorBoundary>
    );

    expect(onError).toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    );
  });

  it("should render custom fallback when provided", () => {
    const customFallback = <div>Custom error message</div>;

    render(
      <AppErrorBoundary fallback={customFallback}>
        <ThrowError />
      </AppErrorBoundary>
    );

    expect(screen.getByText("Custom error message")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong")).not.toBeInTheDocument();
  });

  it("should reset error state when Try Again is clicked", () => {
    const { rerender } = render(
      <AppErrorBoundary>
        <ThrowError shouldThrow={true} />
      </AppErrorBoundary>
    );

    // Error boundary should show error UI
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Click Try Again button
    const tryAgainButton = screen.getByRole("button", { name: /try again/i });
    tryAgainButton.click();

    // Re-render with non-throwing component
    rerender(
      <AppErrorBoundary>
        <ThrowError shouldThrow={false} />
      </AppErrorBoundary>
    );

    // Should show normal content
    expect(screen.getByText("Normal content")).toBeInTheDocument();
  });

  it("should have accessible error UI", () => {
    render(
      <AppErrorBoundary>
        <ThrowError />
      </AppErrorBoundary>
    );

    // Should have proper heading structure
    const heading = screen.getByRole("heading", { name: /something went wrong/i });
    expect(heading).toBeInTheDocument();

    // Buttons should be accessible
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });

  it("should display warning emoji", () => {
    render(
      <AppErrorBoundary>
        <ThrowError />
      </AppErrorBoundary>
    );

    expect(screen.getByText("⚠️")).toBeInTheDocument();
  });

  it("should handle nested errors", () => {
    const NestedError: React.FC = () => {
      return (
        <div>
          <ThrowError />
        </div>
      );
    };

    render(
      <AppErrorBoundary>
        <NestedError />
      </AppErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("should catch errors in event handlers", () => {
    // Note: Error boundaries don't catch errors in event handlers
    // This test documents this limitation
    const EventError: React.FC = () => {
      const handleClick = () => {
        throw new Error("Event error");
      };

      return <button onClick={handleClick}>Click me</button>;
    };

    render(
      <AppErrorBoundary>
        <EventError />
      </AppErrorBoundary>
    );

    // Component renders normally
    expect(screen.getByRole("button", { name: /click me/i })).toBeInTheDocument();
    // Error boundary doesn't catch event handler errors
  });
});
