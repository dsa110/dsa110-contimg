/**
 * CARTA Integration Component
 *
 * Provides integration with CARTA (Cube Analysis and Rendering Tool for Astronomy)
 * for advanced visualization of FITS images. Includes:
 * - Open in CARTA button
 * - Status checking for CARTA availability
 * - SAMP integration for image transfer
 * - Graceful handling when CARTA is unavailable
 */

import React, { useState, useCallback, useEffect } from "react";
import { config } from "@/config";

// ============================================================================
// Types
// ============================================================================

export type CARTAStatus = "available" | "unavailable" | "checking" | "error";

export interface CARTAIntegrationProps {
  /** Image ID to open in CARTA */
  imageId: string;
  /** Image file path */
  imagePath: string;
  /** Optional custom CARTA URL */
  cartaUrl?: string;
  /** Display mode - button or link */
  mode?: "button" | "link" | "icon-button";
  /** Button size variant */
  size?: "sm" | "md" | "lg";
  /** Whether to show status indicator */
  showStatus?: boolean;
  /** Callback when CARTA opens successfully */
  onOpen?: (url: string) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
  /** Additional CSS class */
  className?: string;
  /** Whether component is disabled */
  disabled?: boolean;
}

export interface CARTAConfig {
  baseUrl: string;
  checkEndpoint: string;
  openEndpoint: string;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_CARTA_CONFIG: CARTAConfig = {
  baseUrl: "/viewer/carta",
  checkEndpoint: "/api/carta/status",
  openEndpoint: "/api/carta/open",
};

// ============================================================================
// Hooks
// ============================================================================

/**
 * Hook to check CARTA availability
 */
export function useCARTAStatus(checkEndpoint?: string): {
  status: CARTAStatus;
  error: Error | null;
  recheck: () => void;
} {
  const [status, setStatus] = useState<CARTAStatus>("checking");
  const [error, setError] = useState<Error | null>(null);

  const checkStatus = useCallback(async () => {
    setStatus("checking");
    setError(null);

    try {
      const endpoint = checkEndpoint ?? `${config.api.baseUrl}/carta/status`;
      const response = await fetch(endpoint, {
        method: "GET",
        headers: { Accept: "application/json" },
      });

      if (response.ok) {
        const data = await response.json();
        setStatus(data.available ? "available" : "unavailable");
      } else if (response.status === 404) {
        // CARTA status endpoint not found - assume unavailable
        setStatus("unavailable");
      } else {
        setStatus("error");
        setError(
          new Error(`CARTA status check failed: ${response.statusText}`)
        );
      }
    } catch (err) {
      // Network error or CARTA not deployed
      setStatus("unavailable");
      setError(
        err instanceof Error ? err : new Error("Failed to check CARTA status")
      );
    }
  }, [checkEndpoint]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  return { status, error, recheck: checkStatus };
}

// ============================================================================
// Sub-Components
// ============================================================================

/**
 * Status indicator dot
 */
function StatusIndicator({ status }: { status: CARTAStatus }) {
  const colorClass = {
    available: "bg-green-500",
    unavailable: "bg-gray-400",
    checking: "bg-yellow-500 animate-pulse",
    error: "bg-red-500",
  }[status];

  const title = {
    available: "CARTA is available",
    unavailable: "CARTA is not available",
    checking: "Checking CARTA status...",
    error: "Error checking CARTA status",
  }[status];

  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${colorClass}`}
      title={title}
      data-testid="carta-status-indicator"
    />
  );
}

/**
 * CARTA icon SVG
 */
function CARTAIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {/* Simple cube/3D representation for CARTA */}
      <path d="M12 2L2 7l10 5 10-5-10-5z" />
      <path d="M2 17l10 5 10-5" />
      <path d="M2 12l10 5 10-5" />
    </svg>
  );
}

/**
 * External link icon
 */
function ExternalLinkIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function CARTAIntegration({
  imageId,
  imagePath,
  cartaUrl,
  mode = "button",
  size = "md",
  showStatus = true,
  onOpen,
  onError,
  className = "",
  disabled = false,
}: CARTAIntegrationProps) {
  const { status, recheck } = useCARTAStatus();
  const [isOpening, setIsOpening] = useState(false);

  // Build CARTA URL
  const buildCARTAUrl = useCallback(() => {
    const baseUrl = cartaUrl ?? DEFAULT_CARTA_CONFIG.baseUrl;
    const params = new URLSearchParams({
      file: imagePath,
      imageId: imageId,
    });
    return `${baseUrl}?${params.toString()}`;
  }, [cartaUrl, imagePath, imageId]);

  // Handle opening CARTA
  const handleOpenInCARTA = useCallback(async () => {
    if (disabled || status === "unavailable" || isOpening) {
      return;
    }

    setIsOpening(true);

    try {
      const url = buildCARTAUrl();

      // First, try to notify the CARTA backend (if available)
      try {
        const openEndpoint = `${config.api.baseUrl}/carta/open`;
        await fetch(openEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            imageId,
            imagePath,
          }),
        });
      } catch {
        // Ignore backend notification errors - still open the URL
      }

      // Open CARTA in new window/tab
      window.open(url, "_blank", "noopener,noreferrer");

      onOpen?.(url);
    } catch (err) {
      const error =
        err instanceof Error ? err : new Error("Failed to open CARTA");
      onError?.(error);
    } finally {
      setIsOpening(false);
    }
  }, [
    disabled,
    status,
    isOpening,
    buildCARTAUrl,
    imageId,
    imagePath,
    onOpen,
    onError,
  ]);

  // Size classes
  const sizeClasses = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  }[size];

  const iconSizeClass = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5",
  }[size];

  // Determine if button should be disabled
  const isDisabled =
    disabled || status === "unavailable" || status === "checking" || isOpening;

  // Render based on mode
  if (mode === "icon-button") {
    return (
      <button
        type="button"
        onClick={handleOpenInCARTA}
        disabled={isDisabled}
        className={`
          inline-flex items-center justify-center
          p-2 rounded-md
          ${
            isDisabled
              ? "bg-gray-100 text-gray-400 cursor-not-allowed"
              : "bg-purple-100 text-purple-700 hover:bg-purple-200"
          }
          transition-colors
          ${className}
        `}
        title={
          status === "unavailable"
            ? "CARTA is not available"
            : status === "checking"
            ? "Checking CARTA status..."
            : isOpening
            ? "Opening in CARTA..."
            : "Open in CARTA"
        }
        data-testid="carta-icon-button"
      >
        {isOpening ? (
          <span className="animate-spin">
            <CARTAIcon className={iconSizeClass} />
          </span>
        ) : (
          <CARTAIcon className={iconSizeClass} />
        )}
      </button>
    );
  }

  if (mode === "link") {
    return (
      <button
        type="button"
        onClick={handleOpenInCARTA}
        disabled={isDisabled}
        className={`
          inline-flex items-center gap-1
          ${
            isDisabled
              ? "text-gray-400 cursor-not-allowed"
              : "text-purple-600 hover:text-purple-800 hover:underline"
          }
          ${sizeClasses}
          ${className}
        `}
        data-testid="carta-link"
      >
        {showStatus && <StatusIndicator status={status} />}
        <span>{isOpening ? "Opening..." : "Open in CARTA"}</span>
        {!isDisabled && <ExternalLinkIcon className={iconSizeClass} />}
      </button>
    );
  }

  // Default: button mode
  return (
    <div className={`inline-flex items-center gap-2 ${className}`}>
      <button
        type="button"
        onClick={handleOpenInCARTA}
        disabled={isDisabled}
        className={`
          inline-flex items-center gap-2
          rounded-md font-medium
          transition-colors
          ${sizeClasses}
          ${
            isDisabled
              ? "bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
              : "bg-purple-600 text-white hover:bg-purple-700 active:bg-purple-800"
          }
        `}
        data-testid="carta-button"
      >
        <CARTAIcon className={iconSizeClass} />
        <span>{isOpening ? "Opening..." : "Open in CARTA"}</span>
        {!isDisabled && <ExternalLinkIcon className={iconSizeClass} />}
      </button>

      {showStatus && status !== "available" && (
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <StatusIndicator status={status} />
          {status === "unavailable" && (
            <button
              type="button"
              onClick={recheck}
              className="text-blue-600 hover:underline"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// SAMP Integration Component
// ============================================================================

export interface CARTASAMPIntegrationProps {
  /** Image file path */
  imagePath: string;
  /** SAMP hub status */
  isConnected: boolean;
  /** Send image via SAMP */
  onSendViaSAMP: (path: string) => void;
  /** Button size */
  size?: "sm" | "md" | "lg";
  /** Additional CSS class */
  className?: string;
}

/**
 * Send to CARTA via SAMP protocol
 */
export function CARTASAMPButton({
  imagePath,
  isConnected,
  onSendViaSAMP,
  size = "md",
  className = "",
}: CARTASAMPIntegrationProps) {
  const [isSending, setIsSending] = useState(false);

  const handleSend = useCallback(async () => {
    if (!isConnected || isSending) return;

    setIsSending(true);
    try {
      await onSendViaSAMP(imagePath);
    } finally {
      setIsSending(false);
    }
  }, [isConnected, isSending, imagePath, onSendViaSAMP]);

  const sizeClasses = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  }[size];

  const iconSizeClass = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5",
  }[size];

  const isDisabled = !isConnected || isSending;

  return (
    <button
      type="button"
      onClick={handleSend}
      disabled={isDisabled}
      className={`
        inline-flex items-center gap-2
        rounded-md font-medium
        transition-colors
        ${sizeClasses}
        ${
          isDisabled
            ? "bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
            : "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800"
        }
        ${className}
      `}
      title={
        !isConnected
          ? "Connect to SAMP hub first"
          : isSending
          ? "Sending to CARTA..."
          : "Send to CARTA via SAMP"
      }
      data-testid="carta-samp-button"
    >
      {/* SAMP icon - represents interoperability */}
      <svg
        className={iconSizeClass}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="18" cy="5" r="3" />
        <circle cx="6" cy="12" r="3" />
        <circle cx="18" cy="19" r="3" />
        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
        <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
      </svg>
      <span>
        {isSending
          ? "Sending..."
          : isConnected
          ? "Send via SAMP"
          : "SAMP Disconnected"}
      </span>
    </button>
  );
}

// ============================================================================
// Combined CARTA Actions Component
// ============================================================================

export interface CARTAActionsProps {
  /** Image ID */
  imageId: string;
  /** Image file path */
  imagePath: string;
  /** SAMP connection status */
  isSAMPConnected?: boolean;
  /** SAMP send handler */
  onSendViaSAMP?: (path: string) => void;
  /** Button size */
  size?: "sm" | "md" | "lg";
  /** Layout direction */
  direction?: "horizontal" | "vertical";
  /** Additional CSS class */
  className?: string;
}

/**
 * Combined CARTA actions - direct open and SAMP
 */
export function CARTAActions({
  imageId,
  imagePath,
  isSAMPConnected = false,
  onSendViaSAMP,
  size = "md",
  direction = "horizontal",
  className = "",
}: CARTAActionsProps) {
  return (
    <div
      className={`
        flex gap-2
        ${direction === "vertical" ? "flex-col" : "flex-row flex-wrap"}
        ${className}
      `}
      data-testid="carta-actions"
    >
      <CARTAIntegration
        imageId={imageId}
        imagePath={imagePath}
        size={size}
        showStatus={true}
      />

      {onSendViaSAMP && (
        <CARTASAMPButton
          imagePath={imagePath}
          isConnected={isSAMPConnected}
          onSendViaSAMP={onSendViaSAMP}
          size={size}
        />
      )}
    </div>
  );
}

export default CARTAIntegration;
