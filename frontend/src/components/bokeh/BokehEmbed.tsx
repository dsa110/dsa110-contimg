import React, { useState, useEffect, useCallback, useRef } from "react";
import { LoadingSpinner, Card } from "../common";

/**
 * Status of a Bokeh session.
 */
export type BokehSessionStatus =
  | "connecting"
  | "connected"
  | "disconnected"
  | "error"
  | "idle";

/**
 * Session information from the backend.
 */
export interface BokehSessionInfo {
  id: string;
  url: string;
  ms_path: string;
  imagename: string;
  created_at: string;
  last_activity: string;
  status: string;
}

/**
 * Progress update from the imaging session.
 */
export interface ImagingProgress {
  iteration: number;
  max_iterations: number;
  peak_residual: number;
  rms: number;
  stage: "initializing" | "major_cycle" | "minor_cycle" | "finalizing" | "done";
}

interface BokehEmbedProps {
  /** Session information */
  session: BokehSessionInfo;
  /** Callback when session status changes */
  onStatusChange?: (status: BokehSessionStatus) => void;
  /** Callback when progress updates */
  onProgressUpdate?: (progress: ImagingProgress) => void;
  /** Callback when user closes the session */
  onClose?: () => void;
  /** Width of the embed */
  width?: string | number;
  /** Height of the embed */
  height?: string | number;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show controls bar */
  showControls?: boolean;
  /** Timeout for connection in ms */
  connectionTimeout?: number;
}

/**
 * Component for embedding Bokeh server applications (InteractiveClean).
 *
 * Provides:
 * - iframe embedding of the Bokeh server
 * - Connection status monitoring
 * - Progress tracking via WebSocket
 * - Session controls (stop, detach, fullscreen)
 */
const BokehEmbed: React.FC<BokehEmbedProps> = ({
  session,
  onStatusChange,
  onProgressUpdate,
  onClose,
  width = "100%",
  height = 600,
  className = "",
  showControls = true,
  connectionTimeout = 30000,
}) => {
  const [status, setStatus] = useState<BokehSessionStatus>("connecting");
  const [progress, setProgress] = useState<ImagingProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Update status with callback
  const updateStatus = useCallback(
    (newStatus: BokehSessionStatus) => {
      setStatus(newStatus);
      onStatusChange?.(newStatus);
    },
    [onStatusChange]
  );

  // Connect to WebSocket for progress updates
  useEffect(() => {
    const wsUrl = `ws://${window.location.host}/api/imaging/session/${session.id}/ws`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(
          `[BokehEmbed] WebSocket connected for session ${session.id}`
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "progress") {
            setProgress(data.payload);
            onProgressUpdate?.(data.payload);
          } else if (data.type === "status") {
            if (data.payload === "stopped") {
              updateStatus("disconnected");
            }
          }
        } catch (e) {
          console.warn("[BokehEmbed] Failed to parse WebSocket message:", e);
        }
      };

      ws.onerror = (e) => {
        console.warn("[BokehEmbed] WebSocket error:", e);
        // Don't fail on WS error - iframe can work without progress updates
      };

      ws.onclose = () => {
        console.log("[BokehEmbed] WebSocket closed");
      };
    } catch (e) {
      // WebSocket connection failed - continue without progress updates
      console.warn("[BokehEmbed] WebSocket not available:", e);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [session.id, onProgressUpdate, updateStatus]);

  // Handle iframe load/error events
  const handleIframeLoad = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    updateStatus("connected");
    setError(null);
  }, [updateStatus]);

  const handleIframeError = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    updateStatus("error");
    setError("Failed to load Bokeh application");
  }, [updateStatus]);

  // Set connection timeout
  useEffect(() => {
    timeoutRef.current = setTimeout(() => {
      if (status === "connecting") {
        updateStatus("error");
        setError("Connection timeout - Bokeh server may not be responding");
      }
    }, connectionTimeout);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [connectionTimeout, status, updateStatus]);

  // Toggle fullscreen
  const handleFullscreen = useCallback(() => {
    if (!document.fullscreenElement && iframeRef.current) {
      iframeRef.current.requestFullscreen().catch((e) => {
        console.warn("[BokehEmbed] Fullscreen failed:", e);
      });
      setIsFullscreen(true);
    } else if (document.exitFullscreen) {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, []);

  // Open in new tab
  const handleDetach = useCallback(() => {
    window.open(session.url, "_blank");
  }, [session.url]);

  // Calculate progress percentage
  const progressPct = progress
    ? Math.round((progress.iteration / progress.max_iterations) * 100)
    : 0;

  // Status indicator styles
  const statusColors: Record<BokehSessionStatus, string> = {
    connecting: "bg-yellow-500",
    connected: "bg-green-500",
    disconnected: "bg-gray-500",
    error: "bg-red-500",
    idle: "bg-blue-500",
  };

  const statusLabels: Record<BokehSessionStatus, string> = {
    connecting: "Connecting...",
    connected: "Connected",
    disconnected: "Disconnected",
    error: "Error",
    idle: "Idle",
  };

  return (
    <div
      className={`flex flex-col bg-gray-900 rounded-lg overflow-hidden ${className}`}
    >
      {/* Controls bar */}
      {showControls && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
          {/* Left: Status and progress */}
          <div className="flex items-center gap-4">
            {/* Status indicator */}
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${statusColors[status]} animate-pulse`}
              />
              <span className="text-sm text-gray-300">
                {statusLabels[status]}
              </span>
            </div>

            {/* Progress bar (when connected and running) */}
            {status === "connected" &&
              progress &&
              progress.stage !== "done" && (
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400">
                    {progress.iteration}/{progress.max_iterations}
                  </span>
                </div>
              )}

            {/* Stage indicator */}
            {progress && (
              <span className="text-xs text-gray-500 capitalize">
                {progress.stage.replace("_", " ")}
              </span>
            )}
          </div>

          {/* Right: Action buttons */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDetach}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
              title="Open in new tab"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </button>

            <button
              type="button"
              onClick={handleFullscreen}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
              title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                {isFullscreen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 9V5m0 0H5m4 0L3 11m12-2V5m0 0h4m-4 0l6 6m-9 9v-4m0 4H5m4 0L3 13m12 6v-4m0 4h4m-4 0l6-6"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
                  />
                )}
              </svg>
            </button>

            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded"
                title="Stop session"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Main content area */}
      <div
        className="relative"
        style={{ height: typeof height === "number" ? height : undefined }}
      >
        {/* Loading overlay */}
        {status === "connecting" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 z-10">
            <LoadingSpinner size="lg" label="Connecting to Bokeh server..." />
            <p className="text-gray-500 text-sm mt-4">
              Starting interactive imaging session...
            </p>
          </div>
        )}

        {/* Error overlay */}
        {status === "error" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 z-10">
            <svg
              className="w-16 h-16 text-red-500 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p className="text-red-400 text-lg font-medium">
              {error || "Connection Error"}
            </p>
            <p className="text-gray-500 text-sm mt-2">
              The Bokeh server may not be running or is unreachable.
            </p>
            <button
              type="button"
              onClick={handleDetach}
              className="mt-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
            >
              Try Opening in New Tab
            </button>
          </div>
        )}

        {/* Iframe */}
        <iframe
          ref={iframeRef}
          src={session.url}
          title={`Interactive Clean - ${session.imagename}`}
          width={width}
          height={height}
          onLoad={handleIframeLoad}
          onError={handleIframeError}
          className={`border-0 ${
            status === "connected" ? "opacity-100" : "opacity-0"
          }`}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        />
      </div>

      {/* Session info footer */}
      {showControls && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-t border-gray-700 text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span>
              MS:{" "}
              <code className="text-gray-400">
                {session.ms_path.split("/").pop()}
              </code>
            </span>
            <span>
              Output: <code className="text-gray-400">{session.imagename}</code>
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span>
              Session:{" "}
              <code className="text-gray-400">{session.id.slice(0, 8)}...</code>
            </span>
            {progress && (
              <>
                <span>
                  Peak:{" "}
                  <code className="text-gray-400">
                    {progress.peak_residual.toExponential(2)}
                  </code>
                </span>
                <span>
                  RMS:{" "}
                  <code className="text-gray-400">
                    {progress.rms.toExponential(2)}
                  </code>
                </span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default BokehEmbed;
