import React from "react";

export interface CardProps {
  /** Card title */
  title?: string;
  /** Card subtitle or description (can be string or ReactNode for action buttons) */
  subtitle?: React.ReactNode;
  /** Card content */
  children: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Header actions (buttons, links) */
  actions?: React.ReactNode;
  /** Padding size */
  padding?: "none" | "sm" | "md" | "lg";
  /** Show hover effect */
  hoverable?: boolean;
}

const paddingClasses = {
  none: "",
  sm: "p-3",
  md: "p-4",
  lg: "p-6",
};

/**
 * A card component for grouping related content.
 */
const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  children,
  className = "",
  actions,
  padding = "md",
  hoverable = false,
}) => {
  return (
    <div
      className={`card ${paddingClasses[padding]} ${
        hoverable ? "hover:shadow-md transition-shadow cursor-pointer" : ""
      } ${className}`}
    >
      {(title || actions) && (
        <div className="flex items-start justify-between mb-3">
          <div>
            {title && <h3 className="font-semibold text-gray-900">{title}</h3>}
            {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
};

export default Card;
