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
 * - File browser when no file specified
 * - Fallback UI when CARTA is unavailable
 */

import React, { useMemo } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import {
  useCARTAStatus,
  useCARTASessions,
  getCARTAViewerUrl,
} from "../api/carta";
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

interface FileBrowserStateProps {
  sessions: Array<{
    id: string;
    file_path: string;
    file_type: string;
    created_at: string;
  }>;
  onSelectFile: (path: string) => void;
}

function FileBrowserState({ sessions, onSelectFile }: FileBrowserStateProps) {
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="text-center mb-8">
        <div className="text-6xl mb-4">🔭</div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          CARTA Viewer
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Advanced visualization for FITS images and measurement sets
        </p>
      </div>

      {/* Quick access cards */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <Link
          to="/images"
          className="block p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
        >
          <div className="flex items-center gap-4">
            <div className="text-4xl">🖼️</div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Browse Images
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                View FITS images and open in CARTA
              </p>
            </div>
          </div>
        </Link>

        <Link
          to="/sources"
          className="block p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
        >
          <div className="flex items-center gap-4">
            <div className="text-4xl">📡</div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Browse Sources
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Find sources and view their measurement sets
              </p>
            </div>
          </div>
        </Link>
      </div>

      {/* Recent sessions */}
      {sessions.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <h2 className="font-semibold text-gray-900 dark:text-gray-100">
              Recent CARTA Sessions
            </h2>
          </div>
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {sessions.map((session) => (
              <li key={session.id}>
                <button
                  onClick={() => onSelectFile(session.file_path)}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">
                        {session.file_type === "ms" ? "📊" : "🖼️"}
                      </span>
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate max-w-md">
                          {session.file_path.split("/").pop()}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-md">
                          {session.file_path}
                        </p>
                      </div>
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(session.created_at).toLocaleString()}
                    </span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Empty state for no sessions */}
      {sessions.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <p>No recent CARTA sessions.</p>
          <p className="text-sm mt-2">
            Open a file from the Images or Sources pages to get started.
          </p>
        </div>
      )}

      {/* Help text */}
      <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
          💡 How to use CARTA
        </h3>
        <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
          <li>
            • Navigate to an <strong>Image</strong> or{" "}
            <strong>Measurement Set</strong> detail page
          </li>
          <li>
            • Click the <strong>&ldquo;Open in CARTA&rdquo;</strong> button
          </li>
          <li>• Or select a file from your recent sessions above</li>
        </ul>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function CARTAViewerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { data: status, isLoading: statusLoading } = useCARTAStatus();
  const { data: sessions = [] } = useCARTASessions();

  // Support both ?ms= (from MSDetailPage) and ?file= parameters
  const filePath = searchParams.get("ms") || searchParams.get("file");

  // Handle file selection from browser
  const handleSelectFile = (path: string) => {
    // Determine file type from extension
    const isMs = path.endsWith(".ms") || path.includes(".ms/");
    setSearchParams({ [isMs ? "ms" : "file"]: path });
  };

  // Construct the CARTA iframe URL
  const cartaUrl = useMemo(() => {
    if (!filePath) return null;

    // If CARTA status provides a URL, use it; otherwise use default
    const baseUrl = status?.url || config.carta?.baseUrl || "/carta";
    return getCARTAViewerUrl(filePath, baseUrl);
  }, [filePath, status?.url]);

  // Loading state
  if (statusLoading) {
    return (
      <div className="h-full">
        <LoadingState />
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

  // No file specified - show file browser
  if (!filePath) {
    return (
      <div className="h-full">
        <FileBrowserState sessions={sessions} onSelectFile={handleSelectFile} />
      </div>
    );
  }

  // CARTA available - render iframe
  return (
    <div className="h-full flex flex-col">
      {/* Header bar with file info */}
      <div className="bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSearchParams({})}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            title="Back to file browser"
          >
            ←
          </button>
          <span className="text-lg">🔭</span>
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
