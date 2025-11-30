import React from "react";

/**
 * Props for the Skeleton component.
 */
export interface SkeletonProps {
  /** Width of the skeleton element */
  width?: number | string;
  /** Height of the skeleton element */
  height?: number | string;
  /** Whether the skeleton should be rounded */
  rounded?: boolean;
  /** Whether the skeleton should be a circle */
  circle?: boolean;
  /** Custom class name */
  className?: string;
}

/**
 * A single skeleton placeholder element with pulsing animation.
 */
const Skeleton: React.FC<SkeletonProps> = ({
  width,
  height = "1rem",
  rounded = true,
  circle = false,
  className = "",
}) => {
  const style: React.CSSProperties = {
    width: typeof width === "number" ? `${width}px` : width || "100%",
    height: typeof height === "number" ? `${height}px` : height,
  };

  const roundingClass = circle ? "rounded-full" : rounded ? "rounded" : "";

  return (
    <div
      className={`bg-gray-200 animate-pulse ${roundingClass} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
};

/**
 * Props for PageSkeleton component.
 */
export interface PageSkeletonProps {
  /** Type of page layout to render */
  variant?: "list" | "detail" | "cards" | "table";
  /** Number of rows/items to show */
  rows?: number;
  /** Whether to show a header section */
  showHeader?: boolean;
  /** Whether to show a sidebar */
  showSidebar?: boolean;
  /** Custom class name */
  className?: string;
}

/**
 * Loading skeleton for full page layouts.
 *
 * Provides consistent loading states across the application.
 * Matches the actual content structure to reduce layout shift.
 *
 * @example
 * ```tsx
 * if (isLoading) {
 *   return <PageSkeleton variant="detail" showHeader showSidebar />;
 * }
 * ```
 */
export const PageSkeleton: React.FC<PageSkeletonProps> = ({
  variant = "list",
  rows = 5,
  showHeader = true,
  showSidebar = false,
  className = "",
}) => {
  // Header section
  const headerSection = showHeader && (
    <div className="mb-6 space-y-3">
      <Skeleton width={120} height={16} />
      <Skeleton width="60%" height={28} />
      <div className="flex gap-2">
        <Skeleton width={80} height={20} rounded />
        <Skeleton width={80} height={20} rounded />
        <Skeleton width={80} height={20} rounded />
      </div>
    </div>
  );

  // List variant - rows of items
  const listContent = (
    <div className="space-y-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="p-4 bg-white rounded-lg border border-gray-200 flex items-center gap-4"
        >
          <Skeleton width={48} height={48} rounded />
          <div className="flex-1 space-y-2">
            <Skeleton width="40%" height={18} />
            <Skeleton width="60%" height={14} />
          </div>
          <Skeleton width={60} height={24} rounded />
        </div>
      ))}
    </div>
  );

  // Card grid variant
  const cardsContent = (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
          <Skeleton height={120} />
          <Skeleton width="70%" height={18} />
          <Skeleton width="50%" height={14} />
        </div>
      ))}
    </div>
  );

  // Table variant
  const tableContent = (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Table header */}
      <div className="flex gap-4 p-4 border-b border-gray-200 bg-gray-50">
        <Skeleton width={40} height={16} />
        <Skeleton width="30%" height={16} />
        <Skeleton width="20%" height={16} />
        <Skeleton width="15%" height={16} />
        <Skeleton width="15%" height={16} />
      </div>
      {/* Table rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 p-4 border-b border-gray-100 last:border-b-0">
          <Skeleton width={40} height={16} />
          <Skeleton width="30%" height={16} />
          <Skeleton width="20%" height={16} />
          <Skeleton width="15%" height={16} />
          <Skeleton width="15%" height={16} />
        </div>
      ))}
    </div>
  );

  // Detail variant - sidebar + content layout
  const detailContent = (
    <div className={`grid gap-6 ${showSidebar ? "lg:grid-cols-3" : ""}`}>
      {showSidebar && (
        <div className="lg:col-span-1 space-y-4">
          {/* Preview card */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <Skeleton width="50%" height={18} className="mb-3" />
            <Skeleton height={200} />
          </div>
          {/* Actions card */}
          <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-2">
            <Skeleton width="40%" height={18} className="mb-3" />
            <Skeleton height={36} rounded />
            <Skeleton height={36} rounded />
            <Skeleton height={36} rounded />
          </div>
        </div>
      )}
      <div className={showSidebar ? "lg:col-span-2" : ""}>
        <div className="space-y-6">
          {/* Content cards */}
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
              <Skeleton width="30%" height={18} />
              <Skeleton height={80} />
              <div className="flex gap-4">
                <Skeleton width="25%" height={14} />
                <Skeleton width="25%" height={14} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // Select content based on variant
  const content = {
    list: listContent,
    cards: cardsContent,
    table: tableContent,
    detail: detailContent,
  }[variant];

  return (
    <div className={`max-w-6xl mx-auto p-6 ${className}`} role="status" aria-label="Loading">
      {headerSection}
      {content}
      <span className="sr-only">Loading content...</span>
    </div>
  );
};

export { Skeleton };
export default PageSkeleton;
