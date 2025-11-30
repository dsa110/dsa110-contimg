import React, { useState } from "react";
import { config } from "../../config";

export interface ImageThumbnailProps {
  /** Image ID for fetching thumbnail */
  imageId: string;
  /** Alt text for the image */
  alt?: string;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Click handler */
  onClick?: () => void;
  /** Show expand on hover */
  expandable?: boolean;
  /** API base URL */
  apiUrl?: string;
}

const sizeClasses = {
  sm: "w-24 h-24",
  md: "w-48 h-48",
  lg: "w-72 h-72",
};

/**
 * Display an image thumbnail with loading state and error handling.
 * Falls back to a placeholder if the image can't be loaded.
 */
const ImageThumbnail: React.FC<ImageThumbnailProps> = ({
  imageId,
  alt = "Image preview",
  size = "md",
  onClick,
  expandable = true,
  apiUrl = config.api.baseUrl,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState(false);

  // Thumbnail URL - assumes backend provides /images/{id}/thumbnail endpoint
  const thumbnailUrl = `${apiUrl}/images/${imageId}/thumbnail`;

  const handleLoad = () => {
    setLoading(false);
    setError(false);
  };

  const handleError = () => {
    setLoading(false);
    setError(true);
  };

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else if (expandable) {
      setExpanded(!expanded);
    }
  };

  return (
    <>
      <div
        className={`relative ${
          sizeClasses[size]
        } bg-gray-100 rounded-lg overflow-hidden border border-gray-200 ${
          onClick || expandable ? "cursor-pointer hover:border-blue-400 transition-colors" : ""
        }`}
        onClick={handleClick}
        role={onClick || expandable ? "button" : undefined}
        tabIndex={onClick || expandable ? 0 : undefined}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && (onClick || expandable)) {
            handleClick();
          }
        }}
      >
        {/* Loading state */}
        {loading && !error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="animate-pulse flex flex-col items-center">
              <svg
                className="w-8 h-8 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <span className="text-xs text-gray-400 mt-1">Loading...</span>
            </div>
          </div>
        )}

        {/* Error/placeholder state */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
            <div className="flex flex-col items-center text-gray-400">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <span className="text-xs mt-1">No preview</span>
            </div>
          </div>
        )}

        {/* Actual image */}
        <img
          src={thumbnailUrl}
          alt={alt}
          className={`w-full h-full object-cover ${loading || error ? "hidden" : ""}`}
          onLoad={handleLoad}
          onError={handleError}
        />

        {/* Expand indicator */}
        {expandable && !error && !loading && (
          <div className="absolute bottom-1 right-1 bg-black/50 rounded p-1">
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
              />
            </svg>
          </div>
        )}
      </div>

      {/* Expanded modal */}
      {expanded && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80"
          onClick={() => setExpanded(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="relative max-w-4xl max-h-[90vh] p-4">
            <img
              src={thumbnailUrl}
              alt={alt}
              className="max-w-full max-h-[85vh] object-contain rounded-lg"
            />
            <button
              className="absolute top-2 right-2 bg-white/90 rounded-full p-2 hover:bg-white transition-colors"
              onClick={() => setExpanded(false)}
              aria-label="Close"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default ImageThumbnail;
