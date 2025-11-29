import React from "react";
import StatCard, { StatCardProps } from "./StatCard";

export interface StatCardGridProps {
  /** Array of stat card configurations */
  cards: StatCardProps[];
  /** Number of columns (responsive) */
  columns?: 2 | 3 | 4;
  /** Loading state for all cards */
  isLoading?: boolean;
  /** Custom class name */
  className?: string;
}

const COLUMN_CLASSES = {
  2: "grid-cols-1 sm:grid-cols-2",
  3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
};

/**
 * Responsive grid layout for StatCard components.
 */
const StatCardGrid: React.FC<StatCardGridProps> = ({
  cards,
  columns = 4,
  isLoading = false,
  className = "",
}) => {
  return (
    <div className={`grid ${COLUMN_CLASSES[columns]} gap-4 ${className}`}>
      {cards.map((card, index) => (
        <StatCard key={card.label || index} {...card} isLoading={isLoading} />
      ))}
    </div>
  );
};

export default StatCardGrid;
