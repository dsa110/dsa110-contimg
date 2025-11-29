import React from "react";
import { Link } from "react-router-dom";

export type StatCardVariant = "primary" | "info" | "warning" | "success" | "danger" | "secondary";

export interface StatCardProps {
  /** The metric label */
  label: string;
  /** The metric value */
  value: number | string;
  /** Optional subtitle or additional info */
  subtitle?: string;
  /** Card color variant */
  variant?: StatCardVariant;
  /** Icon to display (emoji or component) */
  icon?: React.ReactNode;
  /** Link to navigate to on click */
  href?: string;
  /** Click handler (alternative to href) */
  onClick?: () => void;
  /** Whether to format value with commas */
  formatNumber?: boolean;
  /** Use compact number formatting (1.2K, 3.4M) */
  compactFormat?: boolean;
  /** Loading state */
  isLoading?: boolean;
  /** Error state */
  error?: string;
  /** Accessible label for screen readers */
  ariaLabel?: string;
  /** Custom class name */
  className?: string;
}

const VARIANT_CLASSES: Record<StatCardVariant, string> = {
  primary: "border-l-blue-500 text-blue-500",
  info: "border-l-teal-500 text-teal-500",
  warning: "border-l-yellow-500 text-yellow-500",
  success: "border-l-green-500 text-green-500",
  danger: "border-l-red-500 text-red-500",
  secondary: "border-l-gray-500 text-gray-500",
};

const ICON_CLASSES: Record<StatCardVariant, string> = {
  primary: "text-blue-200",
  info: "text-teal-200",
  warning: "text-yellow-200",
  success: "text-green-200",
  danger: "text-red-200",
  secondary: "text-gray-200",
};

/**
 * Format a number compactly (1.2K, 3.4M, etc.)
 * Preserves one decimal place for clarity (e.g., 1000 -> "1.0K" not "1K")
 */
function formatCompact(value: number): string {
  const formatWithSuffix = (num: number, suffix: string): string => {
    // Always show one decimal place for consistency
    const formatted = num.toFixed(1);
    return `${formatted}${suffix}`;
  };

  if (value >= 1_000_000_000) {
    return formatWithSuffix(value / 1_000_000_000, "B");
  }
  if (value >= 1_000_000) {
    return formatWithSuffix(value / 1_000_000, "M");
  }
  if (value >= 1_000) {
    return formatWithSuffix(value / 1_000, "K");
  }
  return value.toString();
}

/**
 * Summary statistic card with border accent, icon, and optional link/click.
 * Inspired by VAST pipeline run detail page stat cards.
 */
const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtitle,
  variant = "primary",
  icon,
  href,
  onClick,
  formatNumber = true,
  compactFormat = false,
  isLoading = false,
  error,
  ariaLabel,
  className = "",
}) => {
  // Format the displayed value
  let formattedValue: string | React.ReactNode;
  if (error) {
    formattedValue = "—";
  } else if (typeof value === "number") {
    if (compactFormat) {
      formattedValue = formatCompact(value);
    } else if (formatNumber) {
      formattedValue = value.toLocaleString();
    } else {
      formattedValue = value.toString();
    }
  } else {
    formattedValue = value;
  }

  const isClickable = !!(href || onClick);
  const accessibleLabel =
    ariaLabel || `${label}: ${formattedValue}${subtitle ? `, ${subtitle}` : ""}`;

  const cardContent = (
    <div
      className={`
        card border-l-4 ${VARIANT_CLASSES[variant]} 
        py-3 px-4 h-full transition-all
        ${
          isClickable
            ? "hover:shadow-lg cursor-pointer focus-within:ring-2 focus-within:ring-blue-300"
            : ""
        }
        ${error ? "opacity-75" : ""}
        ${className}
      `}
      role={isClickable ? "button" : undefined}
      tabIndex={onClick && !href ? 0 : undefined}
      onClick={onClick && !href ? onClick : undefined}
      onKeyDown={
        onClick && !href
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      aria-label={accessibleLabel}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p
            className={`text-xs font-bold uppercase mb-1 ${VARIANT_CLASSES[variant].split(" ")[1]}`}
          >
            {label}
          </p>
          {isLoading ? (
            <div
              className="h-7 w-20 bg-gray-200 animate-pulse rounded"
              role="status"
              aria-label="Loading..."
            />
          ) : error ? (
            <p className="text-xl font-bold text-red-500" title={error}>
              —
            </p>
          ) : (
            <p className="text-xl font-bold text-gray-800">{formattedValue}</p>
          )}
          {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
        </div>
        {icon && (
          <div className={`text-3xl ${ICON_CLASSES[variant]}`} aria-hidden="true">
            {icon}
          </div>
        )}
      </div>
    </div>
  );

  if (href) {
    // Check if external link
    if (href.startsWith("http")) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="block no-underline focus:outline-none"
          aria-label={accessibleLabel}
        >
          {cardContent}
        </a>
      );
    }
    return (
      <Link
        to={href}
        className="block no-underline focus:outline-none"
        aria-label={accessibleLabel}
      >
        {cardContent}
      </Link>
    );
  }

  return cardContent;
};

export default StatCard;
