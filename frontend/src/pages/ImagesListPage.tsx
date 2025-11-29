import React, { useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import { useImages } from "../hooks/useQueries";
import { LoadingSpinner, SortableTableHeader, useTableSort } from "../components/common";
import { BulkDownloadPanel } from "../components/download";
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
  const { sortKey, sortDirection, handleSort, sortItems } = useTableSort<ImageItem>(
    "created_at",
    "desc"
  );

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
    const baseUrl = import.meta.env.VITE_API_URL || "/api";
    const url = `${baseUrl}/images/bulk-download?ids=${ids.join(",")}&format=${format}`;
    window.open(url, "_blank");
  }, []);

  const sortedImages = useMemo(() => {
    if (!images) return [];
    return sortItems(images, sortKey, sortDirection);
  }, [images, sortKey, sortDirection, sortItems]);

  if (isLoading) {
    return <LoadingSpinner label="Loading images..." />;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        Failed to load images: {error.message}
      </div>
    );
  }

  // Prepare items for bulk download panel
  const downloadItems = useMemo(
    () =>
      sortedImages.map((img) => ({
        id: img.id,
        name: img.path?.split("/").pop() || img.id,
        type: "FITS",
      })),
    [sortedImages]
  );

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Images</h1>
        {selectedIds.length > 0 && (
          <span className="text-sm text-gray-500">{selectedIds.length} selected</span>
        )}
      </div>

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
                  label="Name"
                  sortKey="path"
                  currentSortKey={sortKey}
                  direction={sortDirection}
                  onSort={handleSort}
                />
                <SortableTableHeader
                  label="QA Grade"
                  sortKey="qa_grade"
                  currentSortKey={sortKey}
                  direction={sortDirection}
                  onSort={handleSort}
                  className="text-center"
                />
                <SortableTableHeader
                  label="Created"
                  sortKey="created_at"
                  currentSortKey={sortKey}
                  direction={sortDirection}
                  onSort={handleSort}
                  className="text-right"
                />
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
