import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { useImages } from "../hooks/useQueries";
import { LoadingSpinner, SortableTableHeader, useTableSort } from "../components/common";

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

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Images</h1>

      {sortedImages && sortedImages.length > 0 ? (
        <div className="card overflow-hidden">
          <table className="table">
            <thead>
              <tr>
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
                <tr key={image.id}>
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
