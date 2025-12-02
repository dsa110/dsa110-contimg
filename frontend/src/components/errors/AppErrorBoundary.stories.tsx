import type { Meta, StoryObj } from "@storybook/react";
import { AppErrorBoundary } from "./AppErrorBoundary";
import { useState } from "react";
import { logger } from "../../utils/logger";

/**
 * AppErrorBoundary catches React errors and displays a user-friendly fallback UI.
 *
 * In production, it shows a minimal error message with recovery options.
 * In development, it includes the error stack trace for debugging.
 */
const meta: Meta<typeof AppErrorBoundary> = {
  title: "Components/Errors/AppErrorBoundary",
  component: AppErrorBoundary,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Component that throws an error when the button is clicked.
 * Used to demonstrate error boundary behavior.
 */
function ErrorThrower() {
  const [shouldThrow, setShouldThrow] = useState(false);

  if (shouldThrow) {
    throw new Error("This is a simulated error for testing the error boundary");
  }

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold mb-4">Normal Component</h2>
      <p className="mb-4">This component is working normally.</p>
      <button
        onClick={() => setShouldThrow(true)}
        className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
      >
        Trigger Error
      </button>
    </div>
  );
}

/**
 * Default story showing the error boundary catching an error.
 * Click the button to trigger an error and see the fallback UI.
 */
export const Default: Story = {
  render: () => (
    <AppErrorBoundary>
      <ErrorThrower />
    </AppErrorBoundary>
  ),
};

/**
 * Story showing a custom fallback component.
 * The error boundary can accept a custom fallback to match your app's design.
 */
export const WithCustomFallback: Story = {
  render: () => (
    <AppErrorBoundary
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-purple-50">
          <div className="text-center">
            <div className="text-6xl mb-4">💜</div>
            <h1 className="text-2xl font-bold text-purple-900 mb-2">
              Custom Error UI
            </h1>
            <p className="text-purple-700">
              This is a custom fallback component
            </p>
          </div>
        </div>
      }
    >
      <ErrorThrower />
    </AppErrorBoundary>
  ),
};

/**
 * Story showing the onError callback being triggered.
 * Useful for error logging and monitoring integration.
 */
export const WithOnErrorCallback: Story = {
  render: () => (
    <AppErrorBoundary
      onError={(error, errorInfo) => {
        // Demo: In real app, send to error tracking service
        logger.info("Error caught", {
          error: error.message,
          stack: errorInfo.componentStack,
        });
      }}
    >
      <ErrorThrower />
    </AppErrorBoundary>
  ),
};

/**
 * Story showing normal operation (no errors).
 * The error boundary renders children normally when no error occurs.
 */
export const NoError: Story = {
  render: () => (
    <AppErrorBoundary>
      <div className="p-8">
        <h2 className="text-2xl font-bold mb-4">Everything is working!</h2>
        <p className="text-gray-600">
          The error boundary passes through children when no error occurs.
        </p>
      </div>
    </AppErrorBoundary>
  ),
};
