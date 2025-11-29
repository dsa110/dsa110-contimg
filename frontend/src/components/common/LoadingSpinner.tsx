import React from "react";

export interface LoadingSpinnerProps {
  /** Size of the spinner */
  size?: "sm" | "md" | "lg";
  /** Optional label text */
  label?: string;
  /** Center in container */
  centered?: boolean;
}

/**
 * Animated loading spinner with optional label.
 * Inspired by Bootstrap spinner design.
 */
const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = "md", label, centered = true }) => {
  const sizeClasses = {
    sm: "w-4 h-4 border-2",
    md: "w-8 h-8 border-3",
    lg: "w-12 h-12 border-4",
  };

  const spinner = (
    <div
      className={`${sizeClasses[size]} border-blue-600 border-t-transparent rounded-full animate-spin`}
      role="status"
      aria-label={label || "Loading"}
    />
  );

  if (centered) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-12">
        {spinner}
        {label && <span className="text-gray-500 text-sm">{label}</span>}
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-2">
      {spinner}
      {label && <span className="text-gray-500 text-sm">{label}</span>}
    </div>
  );
};

export default LoadingSpinner;
