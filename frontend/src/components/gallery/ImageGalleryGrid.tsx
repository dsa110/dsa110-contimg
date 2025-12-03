/**
 * Image Gallery Grid Component
 *
 * Displays images in a responsive thumbnail grid with:
 * - Filters by observation date, field, image type
 * - Sort by date, size, RMS noise
 * - Lazy loading for large galleries
 * - Click to open viewer modal
 */

import React, {
  useState,
  useMemo,
  useCallback,
  useRef,
  useEffect,
} from "react";
import { ImageThumbnail } from "../common";
import type { ImageSummary } from "../../types";

// ============================================================================
// Types
// ============================================================================

export type ImageType = "continuum" | "mosaic" | "snapshot" | "all";
export type SortField = "date" | "size" | "rms" | "name";
export type SortDirection = "asc" | "desc";

export interface ImageGalleryFilters {
  /** Start date filter (ISO string) */
  dateFrom?: string;
  /** End date filter (ISO string) */
  dateTo?: string;
  /** Field/pointing filter */
  field?: string;
  /** Image type filter */
  imageType?: ImageType;
  /** QA grade filter */
  qaGrade?: "good" | "warn" | "fail" | "all";
  /** Minimum RMS noise (mJy) */
  rmsMin?: number;
  /** Maximum RMS noise (mJy) */
  rmsMax?: number;
  /** Search term */
  search?: string;
}

export interface ImageGalleryImage extends ImageSummary {
  /** File size in bytes */
  size_bytes?: number;
  /** RMS noise in Jy */
  noise_jy?: number;
  /** Image type */
  image_type?: ImageType;
  /** Field/pointing name */
  field?: string;
  /** Dynamic range */
  dynamic_range?: number;
}

export interface ImageGalleryGridProps {
  /** Images to display */
  images: ImageGalleryImage[];
  /** Number of columns (responsive default) */
  columns?: 2 | 3 | 4 | 5 | 6;
  /** Items per page for lazy loading */
  pageSize?: number;
  /** Initial filters */
  initialFilters?: ImageGalleryFilters;
  /** Callback when image is clicked */
  onImageClick?: (image: ImageGalleryImage) => void;
  /** Callback when selection changes */
  onSelectionChange?: (selectedIds: string[]) => void;
  /** Enable multi-select mode */
  multiSelect?: boolean;
  /** Show filter panel */
  showFilters?: boolean;
  /** Custom class name */
  className?: string;
  /** Loading state */
  isLoading?: boolean;
}

// ============================================================================
// Filter Panel Component
// ============================================================================

interface FilterPanelProps {
  filters: ImageGalleryFilters;
  onChange: (filters: ImageGalleryFilters) => void;
  availableFields?: string[];
}

const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onChange,
  availableFields = [],
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleChange = (key: keyof ImageGalleryFilters, value: unknown) => {
    onChange({ ...filters, [key]: value || undefined });
  };

  const clearFilters = () => {
    onChange({});
  };

  const activeFilterCount = Object.values(filters).filter(
    (v) => v !== undefined && v !== "" && v !== "all"
  ).length;

  return (
    <div className="bg-white border border-gray-200 rounded-lg mb-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
          <span className="font-medium text-gray-700">Filters</span>
          {activeFilterCount > 0 && (
            <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded-full">
              {activeFilterCount}
            </span>
          )}
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${
            isExpanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-100">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Date range */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Date From
              </label>
              <input
                type="date"
                value={filters.dateFrom || ""}
                onChange={(e) => handleChange("dateFrom", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Date To
              </label>
              <input
                type="date"
                value={filters.dateTo || ""}
                onChange={(e) => handleChange("dateTo", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Field filter */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Field
              </label>
              <select
                value={filters.field || ""}
                onChange={(e) => handleChange("field", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">All Fields</option>
                {availableFields.map((field) => (
                  <option key={field} value={field}>
                    {field}
                  </option>
                ))}
              </select>
            </div>

            {/* Image type */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Image Type
              </label>
              <select
                value={filters.imageType || "all"}
                onChange={(e) =>
                  handleChange("imageType", e.target.value as ImageType)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Types</option>
                <option value="continuum">Continuum</option>
                <option value="mosaic">Mosaic</option>
                <option value="snapshot">Snapshot</option>
              </select>
            </div>

            {/* QA Grade */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                QA Grade
              </label>
              <select
                value={filters.qaGrade || "all"}
                onChange={(e) =>
                  handleChange(
                    "qaGrade",
                    e.target.value as ImageGalleryFilters["qaGrade"]
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Grades</option>
                <option value="good">Good</option>
                <option value="warn">Warning</option>
                <option value="fail">Fail</option>
              </select>
            </div>

            {/* RMS range */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                RMS Min (mJy)
              </label>
              <input
                type="number"
                step="0.001"
                min="0"
                value={filters.rmsMin ?? ""}
                onChange={(e) =>
                  handleChange(
                    "rmsMin",
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                RMS Max (mJy)
              </label>
              <input
                type="number"
                step="0.001"
                min="0"
                value={filters.rmsMax ?? ""}
                onChange={(e) =>
                  handleChange(
                    "rmsMax",
                    e.target.value ? parseFloat(e.target.value) : undefined
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="∞"
              />
            </div>

            {/* Search */}
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Search
              </label>
              <input
                type="text"
                value={filters.search || ""}
                onChange={(e) => handleChange("search", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Search by name..."
              />
            </div>
          </div>

          {activeFilterCount > 0 && (
            <div className="mt-4 flex justify-end">
              <button
                onClick={clearFilters}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Clear all filters
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Sort Controls Component
// ============================================================================

interface SortControlsProps {
  sortField: SortField;
  sortDirection: SortDirection;
  onSortChange: (field: SortField, direction: SortDirection) => void;
  totalCount: number;
  visibleCount: number;
}

const SortControls: React.FC<SortControlsProps> = ({
  sortField,
  sortDirection,
  onSortChange,
  totalCount,
  visibleCount,
}) => {
  const toggleDirection = () => {
    onSortChange(sortField, sortDirection === "asc" ? "desc" : "asc");
  };

  return (
    <div className="flex items-center justify-between mb-4">
      <div className="text-sm text-gray-600">
        Showing {visibleCount} of {totalCount} images
      </div>
      <div className="flex items-center gap-3">
        <label className="text-sm text-gray-600">Sort by:</label>
        <select
          value={sortField}
          onChange={(e) =>
            onSortChange(e.target.value as SortField, sortDirection)
          }
          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="date">Date</option>
          <option value="name">Name</option>
          <option value="size">Size</option>
          <option value="rms">RMS Noise</option>
        </select>
        <button
          onClick={toggleDirection}
          className="p-1.5 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          title={sortDirection === "asc" ? "Ascending" : "Descending"}
        >
          <svg
            className={`w-4 h-4 text-gray-600 transition-transform ${
              sortDirection === "desc" ? "rotate-180" : ""
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12"
            />
          </svg>
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// Image Card Component
// ============================================================================

interface ImageCardProps {
  image: ImageGalleryImage;
  isSelected: boolean;
  multiSelect: boolean;
  onSelect: () => void;
  onClick: () => void;
}

const ImageCard: React.FC<ImageCardProps> = ({
  image,
  isSelected,
  multiSelect,
  onSelect,
  onClick,
}) => {
  const filename = image.path?.split("/").pop() || image.id;
  const rmsDisplay = image.noise_jy
    ? `${(image.noise_jy * 1000).toFixed(2)} mJy`
    : null;
  const dateDisplay = image.created_at
    ? new Date(image.created_at).toLocaleDateString()
    : null;

  const qaColors = {
    good: "bg-green-100 text-green-800 border-green-200",
    warn: "bg-yellow-100 text-yellow-800 border-yellow-200",
    fail: "bg-red-100 text-red-800 border-red-200",
  };

  return (
    <div
      className={`relative bg-white border rounded-lg overflow-hidden transition-all hover:shadow-lg ${
        isSelected ? "ring-2 ring-blue-500 border-blue-500" : "border-gray-200"
      }`}
    >
      {/* Selection checkbox */}
      {multiSelect && (
        <div className="absolute top-2 left-2 z-10">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => {
              e.stopPropagation();
              onSelect();
            }}
            className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
        </div>
      )}

      {/* QA badge */}
      {image.qa_grade && (
        <div className="absolute top-2 right-2 z-10">
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
              qaColors[image.qa_grade] || "bg-gray-100 text-gray-800"
            }`}
          >
            {image.qa_grade.toUpperCase()}
          </span>
        </div>
      )}

      {/* Thumbnail */}
      <button
        type="button"
        onClick={onClick}
        className="w-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
      >
        <div className="aspect-square bg-gray-100">
          <ImageThumbnail
            imageId={image.id}
            alt={filename}
            size="lg"
            expandable={false}
          />
        </div>
      </button>

      {/* Info footer */}
      <div className="p-3">
        <h3
          className="text-sm font-medium text-gray-900 truncate"
          title={filename}
        >
          {filename}
        </h3>
        <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
          {dateDisplay && <span>{dateDisplay}</span>}
          {rmsDisplay && (
            <>
              <span className="text-gray-300">•</span>
              <span title="RMS noise">{rmsDisplay}</span>
            </>
          )}
        </div>
        {image.dynamic_range && (
          <div className="mt-1 text-xs text-gray-500">
            DR: {image.dynamic_range.toFixed(0)}
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

const ImageGalleryGrid: React.FC<ImageGalleryGridProps> = ({
  images,
  columns = 4,
  pageSize = 24,
  initialFilters = {},
  onImageClick,
  onSelectionChange,
  multiSelect = false,
  showFilters = true,
  className = "",
  isLoading = false,
}) => {
  // State
  const [filters, setFilters] = useState<ImageGalleryFilters>(initialFilters);
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [visibleCount, setVisibleCount] = useState(pageSize);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Extract unique fields for filter dropdown
  const availableFields = useMemo(() => {
    const fields = new Set<string>();
    images.forEach((img) => {
      if (img.field) fields.add(img.field);
    });
    return Array.from(fields).sort();
  }, [images]);

  // Apply filters
  const filteredImages = useMemo(() => {
    let result = [...images];

    // Date filter
    if (filters.dateFrom) {
      const fromDate = new Date(filters.dateFrom);
      result = result.filter(
        (img) => img.created_at && new Date(img.created_at) >= fromDate
      );
    }
    if (filters.dateTo) {
      const toDate = new Date(filters.dateTo);
      toDate.setHours(23, 59, 59, 999);
      result = result.filter(
        (img) => img.created_at && new Date(img.created_at) <= toDate
      );
    }

    // Field filter
    if (filters.field) {
      result = result.filter((img) => img.field === filters.field);
    }

    // Image type filter
    if (filters.imageType && filters.imageType !== "all") {
      result = result.filter((img) => img.image_type === filters.imageType);
    }

    // QA grade filter
    if (filters.qaGrade && filters.qaGrade !== "all") {
      result = result.filter((img) => img.qa_grade === filters.qaGrade);
    }

    // RMS range filter
    if (filters.rmsMin !== undefined) {
      const minJy = filters.rmsMin / 1000; // Convert mJy to Jy
      result = result.filter(
        (img) => img.noise_jy !== undefined && img.noise_jy >= minJy
      );
    }
    if (filters.rmsMax !== undefined) {
      const maxJy = filters.rmsMax / 1000;
      result = result.filter(
        (img) => img.noise_jy !== undefined && img.noise_jy <= maxJy
      );
    }

    // Search filter
    if (filters.search) {
      const term = filters.search.toLowerCase();
      result = result.filter(
        (img) =>
          img.path?.toLowerCase().includes(term) ||
          img.id.toLowerCase().includes(term) ||
          img.field?.toLowerCase().includes(term)
      );
    }

    return result;
  }, [images, filters]);

  // Apply sorting
  const sortedImages = useMemo(() => {
    const sorted = [...filteredImages];

    sorted.sort((a, b) => {
      let cmp = 0;

      switch (sortField) {
        case "date":
          cmp =
            new Date(a.created_at || 0).getTime() -
            new Date(b.created_at || 0).getTime();
          break;
        case "name":
          cmp = (a.path || a.id).localeCompare(b.path || b.id);
          break;
        case "size":
          cmp = (a.size_bytes || 0) - (b.size_bytes || 0);
          break;
        case "rms":
          cmp = (a.noise_jy || 0) - (b.noise_jy || 0);
          break;
      }

      return sortDirection === "asc" ? cmp : -cmp;
    });

    return sorted;
  }, [filteredImages, sortField, sortDirection]);

  // Visible images (lazy loading)
  const visibleImages = useMemo(() => {
    return sortedImages.slice(0, visibleCount);
  }, [sortedImages, visibleCount]);

  // Intersection observer for lazy loading
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && visibleCount < sortedImages.length) {
          setVisibleCount((prev) =>
            Math.min(prev + pageSize, sortedImages.length)
          );
        }
      },
      { threshold: 0.1 }
    );

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer.disconnect();
  }, [sortedImages.length, visibleCount, pageSize]);

  // Reset visible count when filters change
  useEffect(() => {
    setVisibleCount(pageSize);
  }, [filters, pageSize]);

  // Handlers
  const handleSortChange = useCallback(
    (field: SortField, direction: SortDirection) => {
      setSortField(field);
      setSortDirection(direction);
    },
    []
  );

  const handleToggleSelect = useCallback(
    (imageId: string) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(imageId)) {
          next.delete(imageId);
        } else {
          next.add(imageId);
        }
        onSelectionChange?.(Array.from(next));
        return next;
      });
    },
    [onSelectionChange]
  );

  const handleImageClick = useCallback(
    (image: ImageGalleryImage) => {
      onImageClick?.(image);
    },
    [onImageClick]
  );

  // Grid columns class
  const gridClass = {
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
    5: "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5",
    6: "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6",
  }[columns];

  // Loading state
  if (isLoading) {
    return (
      <div className={className}>
        {showFilters && (
          <div className="h-14 bg-gray-100 rounded-lg mb-4 animate-pulse" />
        )}
        <div className={`grid ${gridClass} gap-4`}>
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="aspect-square bg-gray-100 rounded-lg animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  // Empty state
  if (images.length === 0) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <svg
          className="w-16 h-16 mx-auto text-gray-300 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
        <h3 className="text-lg font-medium text-gray-900 mb-1">No images</h3>
        <p className="text-gray-500">No images available to display.</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Filters */}
      {showFilters && (
        <FilterPanel
          filters={filters}
          onChange={setFilters}
          availableFields={availableFields}
        />
      )}

      {/* Sort controls */}
      <SortControls
        sortField={sortField}
        sortDirection={sortDirection}
        onSortChange={handleSortChange}
        totalCount={sortedImages.length}
        visibleCount={visibleImages.length}
      />

      {/* No results after filtering */}
      {sortedImages.length === 0 && (
        <div className="text-center py-12">
          <svg
            className="w-12 h-12 mx-auto text-gray-300 mb-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-1">
            No matching images
          </h3>
          <p className="text-gray-500">
            Try adjusting your filters to find images.
          </p>
        </div>
      )}

      {/* Image grid */}
      {sortedImages.length > 0 && (
        <>
          <div className={`grid ${gridClass} gap-4`}>
            {visibleImages.map((image) => (
              <ImageCard
                key={image.id}
                image={image}
                isSelected={selectedIds.has(image.id)}
                multiSelect={multiSelect}
                onSelect={() => handleToggleSelect(image.id)}
                onClick={() => handleImageClick(image)}
              />
            ))}
          </div>

          {/* Load more trigger */}
          {visibleCount < sortedImages.length && (
            <div
              ref={loadMoreRef}
              className="flex items-center justify-center py-8"
            >
              <div className="flex items-center gap-2 text-gray-500">
                <svg
                  className="w-5 h-5 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span>Loading more images...</span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ImageGalleryGrid;
