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
  /** Whether to format value with commas */
  formatNumber?: boolean;
  /** Loading state */
  isLoading?: boolean;
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
 * Summary statistic card with border accent, icon, and optional link.
 * Inspired by VAST pipeline run detail page stat cards.
 */
const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtitle,
  variant = "primary",
  icon,
  href,
  formatNumber = true,
  isLoading = false,
  className = "",
}) => {
  const formattedValue = formatNumber && typeof value === "number" ? value.toLocaleString() : value;

  const cardContent = (
    <div
      className={`
        card border-l-4 ${VARIANT_CLASSES[variant]} 
        py-3 px-4 h-full transition-all
        ${href ? "hover:shadow-lg cursor-pointer" : ""}
        ${className}
      `}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p
            className={`text-xs font-bold uppercase mb-1 ${VARIANT_CLASSES[variant].split(" ")[1]}`}
          >
            {label}
          </p>
          {isLoading ? (
            <div className="h-7 w-20 bg-gray-200 animate-pulse rounded" />
          ) : (
            <p className="text-xl font-bold text-gray-800">{formattedValue}</p>
          )}
          {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
        </div>
        {icon && <div className={`text-3xl ${ICON_CLASSES[variant]}`}>{icon}</div>}
      </div>
    </div>
  );

  if (href) {
    // Check if external link
    if (href.startsWith("http")) {
      return (
        <a href={href} target="_blank" rel="noreferrer" className="block no-underline">
          {cardContent}
        </a>
      );
    }
    return (
      <Link to={href} className="block no-underline">
        {cardContent}
      </Link>
    );
  }

  return cardContent;
};

export default StatCard;
