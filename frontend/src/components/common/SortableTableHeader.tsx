import React from "react";

export type SortDirection = "asc" | "desc" | null;

export interface SortableTableHeaderProps {
  /** Column key for sorting */
  columnKey: string;
  /** Display label */
  children: React.ReactNode;
  /** Current sort column */
  sortColumn: string | null;
  /** Current sort direction */
  sortDirection: SortDirection;
  /** Callback when header is clicked */
  onSort: (columnKey: string) => void;
  /** Additional className for alignment */
  className?: string;
}

/**
 * Sortable table header with visual sort indicators.
 * Click to toggle sort direction: none → asc → desc → none
 */
const SortableTableHeader: React.FC<SortableTableHeaderProps> = ({
  columnKey,
  children,
  sortColumn,
  sortDirection,
  onSort,
  className = "",
}) => {
  const isActive = sortColumn === columnKey;

  return (
    <th
      className={`cursor-pointer select-none hover:bg-gray-100 transition-colors ${className}`}
      onClick={() => onSort(columnKey)}
      role="columnheader"
      aria-sort={isActive ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}
    >
      <div className="flex items-center gap-1">
        <span>{children}</span>
        <span className="inline-flex flex-col text-[10px] leading-none ml-1">
          <span
            className={`${
              isActive && sortDirection === "asc" ? "text-blue-600" : "text-gray-300"
            }`}
          >
            ▲
          </span>
          <span
            className={`${
              isActive && sortDirection === "desc" ? "text-blue-600" : "text-gray-300"
            }`}
          >
            ▼
          </span>
        </span>
      </div>
    </th>
  );
};

export default SortableTableHeader;

/**
 * Hook to manage table sorting state
 */
export function useTableSort<T>(
  data: T[] | undefined,
  defaultColumn: string | null = null,
  defaultDirection: SortDirection = null
) {
  const [sortColumn, setSortColumn] = React.useState<string | null>(defaultColumn);
  const [sortDirection, setSortDirection] = React.useState<SortDirection>(defaultDirection);

  const handleSort = React.useCallback((columnKey: string) => {
    if (sortColumn !== columnKey) {
      setSortColumn(columnKey);
      setSortDirection("asc");
    } else if (sortDirection === "asc") {
      setSortDirection("desc");
    } else if (sortDirection === "desc") {
      setSortColumn(null);
      setSortDirection(null);
    } else {
      setSortColumn(columnKey);
      setSortDirection("asc");
    }
  }, [sortColumn, sortDirection]);

  const sortedData = React.useMemo(() => {
    if (!data || !sortColumn || !sortDirection) return data;

    return [...data].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortColumn];
      const bVal = (b as Record<string, unknown>)[sortColumn];

      // Handle null/undefined
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return sortDirection === "asc" ? 1 : -1;
      if (bVal == null) return sortDirection === "asc" ? -1 : 1;

      // Compare values
      let comparison = 0;
      if (typeof aVal === "string" && typeof bVal === "string") {
        comparison = aVal.localeCompare(bVal);
      } else if (typeof aVal === "number" && typeof bVal === "number") {
        comparison = aVal - bVal;
      } else {
        comparison = String(aVal).localeCompare(String(bVal));
      }

      return sortDirection === "asc" ? comparison : -comparison;
    });
  }, [data, sortColumn, sortDirection]);

  return {
    sortColumn,
    sortDirection,
    handleSort,
    sortedData,
  };
}
