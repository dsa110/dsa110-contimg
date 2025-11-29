import React from "react";
import { Link } from "react-router-dom";

/**
 * 404 Not Found page.
 */
const NotFoundPage: React.FC = () => {
  return (
    <div
      className="not-found-page"
      style={{
        textAlign: "center",
        padding: "60px 20px",
      }}
    >
      <h1 style={{ fontSize: "4rem", margin: "0 0 16px", color: "#ccc" }}>404</h1>
      <h2 style={{ margin: "0 0 24px", color: "#666" }}>Page Not Found</h2>
      <p style={{ color: "#888", marginBottom: "32px" }}>
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link
        to="/"
        style={{
          display: "inline-block",
          padding: "12px 24px",
          backgroundColor: "#1a1a2e",
          color: "white",
          textDecoration: "none",
          borderRadius: "4px",
        }}
      >
        Go to Home
      </Link>
    </div>
  );
};

export default NotFoundPage;
