import React from "react";
import { Link } from "react-router-dom";
import { useImages } from "../hooks/useQueries";
import { LoadingSpinner } from "../components/common";

/**
 * List page showing all images.
 */
const ImagesListPage: React.FC = () => {
  const { data: images, isLoading, error } = useImages();

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

      {images && images.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {images.map((image) => (
            <Link
              key={image.id}
              to={`/images/${image.id}`}
              className="card p-4 hover:shadow-lg transition-shadow"
            >
              <h3 className="font-medium text-gray-900 mb-2 truncate">
                {image.path?.split("/").pop() || image.id}
              </h3>
              <div className="flex items-center gap-2 text-sm">
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
                {image.created_at && (
                  <span className="text-gray-500">
                    {new Date(image.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-gray-500">No images found.</p>
      )}
    </div>
  );
};

export default ImagesListPage;
