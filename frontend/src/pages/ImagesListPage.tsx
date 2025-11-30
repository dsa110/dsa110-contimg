import React, { useMemo, useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { useImages } from "../hooks/useQueries";
import { PageSkeleton, SortableTableHeader, useTableSort } from "../components/common";
import { BulkDownloadPanel } from "../components/download";
import { config } from "../config";
import { FitsViewerGrid } from "../components/fits";
import { FilterPanel, FilterConfig, FilterValues } from "../components/filters";
import { useSelectionStore } from "../stores/appStore";

interface ImageItem {
  id: string;
  path?: string;
  qa_grade?: string;
  created_at?: string;
}

/**
 * List page showing all images with sortable table headers.
 */
const ImagesListPage: React.FC = () => {
  const { data: images, isLoading, error } = useImages();

  // View mode: list or comparison
  const [viewMode, setViewMode] = useState<"list" | "compare">("list");

  // Filter state
  const [filterValues, setFilterValues] = useState<FilterValues>({});
  const filterConfigs: FilterConfig[] = [
    {
      id: "qa_grade",
      label: "QA Grade",
      type: "select",
      options: [
        { value: "good", label: "Good" },
        { value: "warn", label: "Warning" },
        { value: "fail", label: "Fail" },
      ],
    },
    {
      id: "search",
      label: "Search",
      type: "text",
    },
  ];

  // Multi-select state from store
  const selectedImages = useSelectionStore((s) => s.selectedImages);
  const toggleImageSelection = useSelectionStore((s) => s.toggleImageSelection);
  const selectAllImages = useSelectionStore((s) => s.selectAllImages);
  const clearImageSelection = useSelectionStore((s) => s.clearImageSelection);

  const selectedIds = useMemo(() => Array.from(selectedImages), [selectedImages]);

  const handleSelectionChange = useCallback(
    (ids: string[]) => {
      if (ids.length === 0) {
        clearImageSelection();
      } else {
        selectAllImages(ids);
      }
    },
    [clearImageSelection, selectAllImages]
  );

  const handleBulkDownload = useCallback(async (ids: string[], format: string) => {
    const baseUrl = config.api.baseUrl;
    const url = `${baseUrl}/images/bulk-download?ids=${ids.join(",")}&format=${format}`;
    window.open(url, "_blank");
  }, []);

  // Apply filters
  const filteredImages = useMemo(() => {
    if (!images) return [];
    let result = images as ImageItem[];

    if (filterValues.qa_grade) {
      result = result.filter((img) => img.qa_grade === filterValues.qa_grade);
    }
    if (filterValues.search && typeof filterValues.search === "string") {
      const term = filterValues.search.toLowerCase();
      result = result.filter(
        (img) => img.path?.toLowerCase().includes(term) || img.id.toLowerCase().includes(term)
      );
    }

    return result;
  }, [images, filterValues]);

  // Apply sorting using the hook with filtered data
  const {
    sortColumn,
    sortDirection,
    handleSort,
    sortedData: sortedImages,
  } = useTableSort<ImageItem>(filteredImages, "created_at", "desc");

  // Prepare items for bulk download panel - must be before early returns
  const downloadItems = useMemo(
    () =>
      sortedImages.map((img) => ({
        id: img.id,
        name: img.path?.split("/").pop() || img.id,
        type: "FITS",
      })),
    [sortedImages]
  );

  // FITS URLs for selected images comparison - must be before early returns
  const comparisonUrls = useMemo(() => {
    const baseUrl = config.api.baseUrl;
    return selectedIds.map((id) => `${baseUrl}/images/${id}/fits`);
  }, [selectedIds]);

  const comparisonLabels = useMemo(() => {
    return selectedIds.map((id) => {
      const img = sortedImages.find((i) => i.id === id);
      return img?.path?.split("/").pop() || id;
    });
  }, [selectedIds, sortedImages]);

  if (isLoading) {
    return <PageSkeleton variant="table" rows={8} showHeader />;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        Failed to load images: {error.message}
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">Images</h1>
          {selectedIds.length > 0 && (
            <span className="text-sm text-gray-500">{selectedIds.length} selected</span>
          )}
        </div>
        <div className="flex gap-2">
          {selectedIds.length >= 2 && selectedIds.length <= 4 && (
            <button
              onClick={() => setViewMode(viewMode === "compare" ? "list" : "compare")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                viewMode === "compare"
                  ? "bg-purple-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {viewMode === "compare" ? "Back to List" : "Compare Selected"}
            </button>
          )}
        </div>
      </div>

      {/* Filter Panel */}
      <div className="mb-4">
        <FilterPanel
          filters={filterConfigs}
          values={filterValues}
          onChange={setFilterValues}
          title="Filter Images"
          collapsible
          defaultCollapsed
        />
      </div>

      {/* Comparison View */}
      {viewMode === "compare" && selectedIds.length >= 2 && (
        <div className="mb-6">
          <div className="card p-4">
            <h3 className="text-lg font-semibold mb-4">Image Comparison</h3>
            <FitsViewerGrid
              fitsUrls={comparisonUrls}
              labels={comparisonLabels}
              columns={selectedIds.length <= 2 ? 2 : selectedIds.length <= 3 ? 3 : 4}
              viewerSize={350}
              syncViews
            />
          </div>
        </div>
      )}

      {/* Bulk Download Panel - show when items selected */}
      {sortedImages.length > 0 && (
        <div className="mb-6">
          <BulkDownloadPanel
            items={downloadItems}
            selectedIds={selectedIds}
            onSelectionChange={handleSelectionChange}
            onDownload={handleBulkDownload}
          />
        </div>
      )}

      {sortedImages && sortedImages.length > 0 ? (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
                <th className="w-10 px-3 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === sortedImages.length && sortedImages.length > 0}
                    ref={(el) => {
                      if (el)
                        el.indeterminate =
                          selectedIds.length > 0 && selectedIds.length < sortedImages.length;
                    }}
                    onChange={() => {
                      if (selectedIds.length === sortedImages.length) {
                        clearImageSelection();
                      } else {
                        selectAllImages(sortedImages.map((i) => i.id));
                      }
                    }}
                    className="h-4 w-4 text-blue-600 rounded"
                  />
                </th>
                <SortableTableHeader
                  columnKey="path"
                  sortColumn={sortColumn}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                >
                  Name
                </SortableTableHeader>
                <SortableTableHeader
                  columnKey="qa_grade"
                  sortColumn={sortColumn}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  className="text-center"
                >
                  QA Grade
                </SortableTableHeader>
                <SortableTableHeader
                  columnKey="created_at"
                  sortColumn={sortColumn}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  className="text-right"
                >
                  Created
                </SortableTableHeader>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedImages.map((image) => (
                <tr key={image.id} className={selectedImages.has(image.id) ? "bg-blue-50" : ""}>
                  <td className="px-3">
                    <input
                      type="checkbox"
                      checked={selectedImages.has(image.id)}
                      onChange={() => toggleImageSelection(image.id)}
                      className="h-4 w-4 text-blue-600 rounded"
                    />
                  </td>
                  <td>
                    <Link
                      to={`/images/${image.id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {image.path?.split("/").pop() || image.id}
                    </Link>
                  </td>
                  <td className="text-center">
                    {image.qa_grade && (
                      <span
                        className={`badge ${
                          image.qa_grade === "good"
                            ? "badge-success"
                            : image.qa_grade === "warn"
                            ? "badge-warning"
                            : "badge-error"
                        }`}
                      >
                        {image.qa_grade}
                      </span>
                    )}
                  </td>
                  <td className="text-right text-gray-500">
                    {image.created_at ? new Date(image.created_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-gray-500">No images found.</p>
      )}
    </div>
  );
};

export default ImagesListPage;
