/**
 * CARTA Viewer Page
 *
 * Embeds the CARTA (Cube Analysis and Rendering Tool for Astronomy) viewer
 * for advanced visualization of FITS images and measurement sets.
 *
 * Features:
 * - Embedded CARTA viewer via iframe
 * - Status checking and error handling
 * - File path parameter support (?ms= or ?file=)
 * - Fallback UI when CARTA is unavailable
 */

import React, { useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useCARTAStatus, getCARTAViewerUrl } from "../api/carta";
import { config } from "../config";

// ============================================================================
// Status Components
// ============================================================================

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600 dark:text-gray-400">
          Checking CARTA availability...
        </p>
      </div>
    </div>
  );
}

function UnavailableState({ message }: { message?: string }) {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-4">🔭</div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          CARTA Viewer Unavailable
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          {message ||
            "The CARTA visualization server is not currently available. Please try again later or contact your administrator."}
        </p>
        <div className="space-y-2">
          <Link
            to="/"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Return to Dashboard
          </Link>
          <p className="text-sm text-gray-500 dark:text-gray-500">
            CARTA is an optional component that may need to be deployed
            separately.
          </p>
        </div>
      </div>
    </div>
  );
}

function NoFileState() {
  return (
    <div className="flex items-center justify-center h-full min-h-[400px]">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-4">📂</div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          No File Specified
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          Please specify a file to open in CARTA. You can access CARTA from:
        </p>
        <ul className="text-left text-gray-600 dark:text-gray-400 mb-4 space-y-2">
          <li className="flex items-center gap-2">
            <span className="text-blue-500">→</span>
            The "Open in CARTA" button on measurement set detail pages
          </li>
          <li className="flex items-center gap-2">
            <span className="text-blue-500">→</span>
            Image gallery actions for FITS files
          </li>
        </ul>
        <Link
          to="/images"
          className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Browse Images
        </Link>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function CARTAViewerPage() {
  const [searchParams] = useSearchParams();
  const { data: status, isLoading } = useCARTAStatus();

  // Support both ?ms= (from MSDetailPage) and ?file= parameters
  const filePath = searchParams.get("ms") || searchParams.get("file");

  // Construct the CARTA iframe URL
  const cartaUrl = useMemo(() => {
    if (!filePath) return null;

    // If CARTA status provides a URL, use it; otherwise use default
    const baseUrl = status?.url || config.carta?.baseUrl || "/carta";
    return getCARTAViewerUrl(filePath, baseUrl);
  }, [filePath, status?.url]);

  // Loading state
  if (isLoading) {
    return (
      <div className="h-full">
        <LoadingState />
      </div>
    );
  }

  // No file specified
  if (!filePath) {
    return (
      <div className="h-full">
        <NoFileState />
      </div>
    );
  }

  // CARTA unavailable
  if (!status?.available) {
    return (
      <div className="h-full">
        <UnavailableState message={status?.message} />
      </div>
    );
  }

  // CARTA available - render iframe
  return (
    <div className="h-full flex flex-col">
      {/* Header bar with file info */}
      <div className="bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg">🔭</span>
          <div>
            <h1 className="text-sm font-medium text-gray-900 dark:text-gray-100">
              CARTA Viewer
            </h1>
            <p
              className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-md"
              title={filePath}
            >
              {filePath}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status?.version && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              v{status.version}
            </span>
          )}
          <a
            href={cartaUrl || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            Open in new tab ↗
          </a>
        </div>
      </div>

      {/* CARTA iframe */}
      <div className="flex-1 relative">
        <iframe
          src={cartaUrl || ""}
          className="absolute inset-0 w-full h-full border-0"
          title="CARTA Viewer"
          allow="fullscreen"
          sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
        />
      </div>
    </div>
  );
}
