import React from "react";
import { Link } from "react-router-dom";
import { useImages } from "../hooks/useQueries";

/**
 * List page showing all images.
 */
const ImagesListPage: React.FC = () => {
  const { data: images, isLoading, error } = useImages();

  if (isLoading) {
    return <div style={{ padding: "20px" }}>Loading images...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: "20px", color: "#dc3545" }}>
        Failed to load images: {error.message}
      </div>
    );
  }

  return (
    <div className="images-list-page">
      <h1 style={{ marginTop: 0 }}>Images</h1>

      {images && images.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: "16px",
          }}
        >
          {images.map((image) => (
            <Link
              key={image.id}
              to={`/images/${image.id}`}
              style={{
                display: "block",
                backgroundColor: "white",
                padding: "16px",
                borderRadius: "8px",
                boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <h3 style={{ margin: "0 0 8px", fontSize: "1rem" }}>
                {image.path?.split("/").pop() || image.id}
              </h3>
              <div style={{ fontSize: "0.85rem", color: "#666" }}>
                {image.qa_grade && (
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: "4px",
                      backgroundColor:
                        image.qa_grade === "good"
                          ? "#d4edda"
                          : image.qa_grade === "warn"
                            ? "#fff3cd"
                            : "#f8d7da",
                      color:
                        image.qa_grade === "good"
                          ? "#155724"
                          : image.qa_grade === "warn"
                            ? "#856404"
                            : "#721c24",
                      marginRight: "8px",
                    }}
                  >
                    {image.qa_grade}
                  </span>
                )}
                {image.created_at && <span>{new Date(image.created_at).toLocaleDateString()}</span>}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <p style={{ color: "#666" }}>No images found.</p>
      )}
    </div>
  );
};

export default ImagesListPage;
