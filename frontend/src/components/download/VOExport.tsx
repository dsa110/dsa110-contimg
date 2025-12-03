/**
 * VO Export Components
 *
 * Components for exporting data in Virtual Observatory (VO) formats
 * including VOTable and SAMP integration.
 */
import { useState, useCallback } from "react";
import {
  useSAMPConnection,
  useSAMPClients,
  useSAMPMessaging,
} from "../../stores/sampStore";
import {
  downloadVOTable,
  createVOTableDataUrl,
  SOURCE_COLUMN_MAPPINGS,
  IMAGE_COLUMN_MAPPINGS,
} from "../../lib/votable";
import type {
  ExportFormat,
  ExportDataSelection,
  ColumnMapping,
} from "../../types/vo";

// ============================================================================
// Export Dialog Component
// ============================================================================

interface VOExportDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback to close the dialog */
  onClose: () => void;
  /** Data to export */
  data: Record<string, unknown>[];
  /** Type of data being exported */
  dataType: ExportDataSelection["dataType"];
  /** Optional custom title */
  title?: string;
  /** Optional custom description */
  description?: string;
}

/**
 * Dialog for configuring and executing VO exports
 */
export function VOExportDialog({
  isOpen,
  onClose,
  data,
  dataType,
  title,
  description,
}: VOExportDialogProps) {
  const [format, setFormat] = useState<ExportFormat>("votable");
  const [filename, setFilename] = useState(
    `${dataType}_export_${new Date().toISOString().split("T")[0]}`
  );
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const {
    isConnected,
    status: sampStatus,
    connect,
    disconnect,
  } = useSAMPConnection();
  const { clients } = useSAMPClients();
  const { sendTable } = useSAMPMessaging();

  // Get column mappings based on data type
  const getColumnMappings = useCallback((): ColumnMapping[] | undefined => {
    switch (dataType) {
      case "sources":
        return SOURCE_COLUMN_MAPPINGS;
      case "images":
        return IMAGE_COLUMN_MAPPINGS;
      default:
        return undefined;
    }
  }, [dataType]);

  // Handle download export
  const handleDownload = useCallback(async () => {
    setIsExporting(true);
    setExportError(null);

    try {
      const mappings = getColumnMappings();
      const filenameWithExt =
        format === "votable"
          ? filename.endsWith(".vot")
            ? filename
            : `${filename}.vot`
          : format === "csv"
          ? filename.endsWith(".csv")
            ? filename
            : `${filename}.csv`
          : `${filename}.json`;

      if (format === "votable") {
        downloadVOTable(data, filenameWithExt, {
          tableName: dataType,
          resourceName: title || `DSA-110 ${dataType}`,
          description,
          columnMappings: mappings,
        });
      } else if (format === "csv") {
        // Simple CSV export
        const headers = Object.keys(data[0] || {});
        const csvContent = [
          headers.join(","),
          ...data.map((row) =>
            headers
              .map((h) => {
                const val = row[h];
                if (val === null || val === undefined) return "";
                if (typeof val === "string" && val.includes(",")) {
                  return `"${val.replace(/"/g, '""')}"`;
                }
                return String(val);
              })
              .join(",")
          ),
        ].join("\n");

        const blob = new Blob([csvContent], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filenameWithExt;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } else {
        // JSON export
        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filenameWithExt;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }

      onClose();
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "Export failed");
    } finally {
      setIsExporting(false);
    }
  }, [
    data,
    dataType,
    filename,
    format,
    getColumnMappings,
    onClose,
    title,
    description,
  ]);

  // Handle SAMP export
  const handleSAMPExport = useCallback(async () => {
    if (!isConnected) {
      setExportError("Not connected to SAMP hub");
      return;
    }

    setIsExporting(true);
    setExportError(null);

    try {
      const mappings = getColumnMappings();
      const dataUrl = createVOTableDataUrl(data, {
        tableName: dataType,
        resourceName: title || `DSA-110 ${dataType}`,
        description,
        columnMappings: mappings,
      });

      const response = await sendTable(dataUrl, {
        name: title || `DSA-110 ${dataType}`,
        "table-id": `dsa110_${dataType}_${Date.now()}`,
      });

      if (!response.success) {
        throw new Error(response.error || "Failed to send table via SAMP");
      }

      onClose();
    } catch (error) {
      setExportError(
        error instanceof Error ? error.message : "SAMP export failed"
      );
    } finally {
      setIsExporting(false);
    }
  }, [
    data,
    dataType,
    getColumnMappings,
    isConnected,
    onClose,
    sendTable,
    title,
    description,
  ]);

  if (!isOpen) {
    return null;
  }

  const tableClients = clients.filter((c) =>
    c.subscriptions.includes("table.load.votable")
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />

      {/* Dialog */}
      <div
        className="relative w-full max-w-lg rounded-lg shadow-xl"
        style={{
          backgroundColor: "var(--color-bg-paper)",
          border: "1px solid var(--color-border)",
        }}
      >
        {/* Header */}
        <div
          className="px-6 py-4 border-b"
          style={{ borderColor: "var(--color-border)" }}
        >
          <h2
            className="text-lg font-semibold"
            style={{ color: "var(--color-text-primary)" }}
          >
            Export Data
          </h2>
          <p
            className="text-sm mt-1"
            style={{ color: "var(--color-text-secondary)" }}
          >
            Export {data.length} {dataType} records
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4">
          {/* Error message */}
          {exportError && (
            <div
              className="p-3 rounded-md text-sm"
              style={{
                backgroundColor: "var(--color-danger-bg)",
                color: "var(--color-danger)",
                border: "1px solid var(--color-danger)",
              }}
            >
              {exportError}
            </div>
          )}

          {/* Format selection */}
          <div>
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: "var(--color-text-primary)" }}
            >
              Export Format
            </label>
            <div className="flex gap-2">
              {(["votable", "csv", "json"] as ExportFormat[]).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFormat(f)}
                  className="px-4 py-2 rounded-md text-sm font-medium transition-colors"
                  style={{
                    backgroundColor:
                      format === f
                        ? "var(--color-primary)"
                        : "var(--color-bg-surface)",
                    color: format === f ? "white" : "var(--color-text-primary)",
                    border: `1px solid ${
                      format === f
                        ? "var(--color-primary)"
                        : "var(--color-border)"
                    }`,
                  }}
                >
                  {f.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Filename */}
          <div>
            <label
              htmlFor="filename"
              className="block text-sm font-medium mb-2"
              style={{ color: "var(--color-text-primary)" }}
            >
              Filename
            </label>
            <input
              id="filename"
              type="text"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              className="w-full px-3 py-2 rounded-md"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                border: "1px solid var(--color-border)",
                color: "var(--color-text-primary)",
              }}
            />
          </div>

          {/* SAMP Section */}
          {format === "votable" && (
            <div
              className="p-4 rounded-md"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                border: "1px solid var(--color-border)",
              }}
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3
                    className="text-sm font-medium"
                    style={{ color: "var(--color-text-primary)" }}
                  >
                    SAMP Integration
                  </h3>
                  <p
                    className="text-xs"
                    style={{ color: "var(--color-text-secondary)" }}
                  >
                    Send directly to astronomy applications
                  </p>
                </div>
                <SAMPStatusBadge status={sampStatus} />
              </div>

              {!isConnected ? (
                <button
                  type="button"
                  onClick={() => connect()}
                  className="w-full px-4 py-2 rounded-md text-sm font-medium transition-colors"
                  style={{
                    backgroundColor: "var(--color-bg-default)",
                    color: "var(--color-text-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  Connect to SAMP Hub
                </button>
              ) : (
                <div className="space-y-2">
                  <div
                    className="text-xs"
                    style={{ color: "var(--color-text-secondary)" }}
                  >
                    {tableClients.length > 0
                      ? `${tableClients.length} application(s) available:`
                      : "No applications accepting tables"}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {tableClients.map((client) => (
                      <span
                        key={client.id}
                        className="px-2 py-1 rounded text-xs"
                        style={{
                          backgroundColor: "var(--color-bg-default)",
                          color: "var(--color-text-primary)",
                        }}
                      >
                        {client.metadata["samp.name"]}
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <button
                      type="button"
                      onClick={handleSAMPExport}
                      disabled={isExporting || tableClients.length === 0}
                      className="flex-1 px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
                      style={{
                        backgroundColor: "var(--color-success)",
                        color: "white",
                      }}
                    >
                      {isExporting ? "Sending..." : "Send via SAMP"}
                    </button>
                    <button
                      type="button"
                      onClick={() => disconnect()}
                      className="px-3 py-2 rounded-md text-sm transition-colors"
                      style={{
                        backgroundColor: "var(--color-bg-default)",
                        color: "var(--color-text-secondary)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      Disconnect
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="px-6 py-4 border-t flex justify-end gap-3"
          style={{ borderColor: "var(--color-border)" }}
        >
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-md text-sm font-medium transition-colors"
            style={{
              backgroundColor: "var(--color-bg-surface)",
              color: "var(--color-text-primary)",
              border: "1px solid var(--color-border)",
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDownload}
            disabled={isExporting}
            className="px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
            style={{
              backgroundColor: "var(--color-primary)",
              color: "white",
            }}
          >
            {isExporting ? "Exporting..." : "Download"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// SAMP Status Badge
// ============================================================================

interface SAMPStatusBadgeProps {
  status: string;
}

function SAMPStatusBadge({ status }: SAMPStatusBadgeProps) {
  const getStatusStyle = () => {
    switch (status) {
      case "connected":
        return {
          backgroundColor: "var(--color-success-bg, #dcfce7)",
          color: "var(--color-success, #16a34a)",
        };
      case "connecting":
        return {
          backgroundColor: "var(--color-warning-bg, #fef3c7)",
          color: "var(--color-warning, #ca8a04)",
        };
      case "error":
        return {
          backgroundColor: "var(--color-danger-bg, #fee2e2)",
          color: "var(--color-danger, #dc2626)",
        };
      default:
        return {
          backgroundColor: "var(--color-bg-surface)",
          color: "var(--color-text-secondary)",
        };
    }
  };

  return (
    <span
      className="px-2 py-1 rounded text-xs font-medium"
      style={getStatusStyle()}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// ============================================================================
// Export Button Component
// ============================================================================

interface ExportButtonProps {
  /** Data to export */
  data: Record<string, unknown>[];
  /** Type of data */
  dataType: ExportDataSelection["dataType"];
  /** Button text */
  children?: React.ReactNode;
  /** Additional class name */
  className?: string;
  /** Disabled state */
  disabled?: boolean;
}

/**
 * Button that opens the export dialog
 */
export function ExportButton({
  data,
  dataType,
  children = "Export",
  className = "",
  disabled = false,
}: ExportButtonProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setIsDialogOpen(true)}
        disabled={disabled || data.length === 0}
        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 ${className}`}
        style={{
          backgroundColor: "var(--color-bg-surface)",
          color: "var(--color-text-primary)",
          border: "1px solid var(--color-border)",
        }}
      >
        <span className="flex items-center gap-2">
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
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          {children}
        </span>
      </button>

      <VOExportDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        data={data}
        dataType={dataType}
      />
    </>
  );
}

// ============================================================================
// Quick Export Menu
// ============================================================================

interface QuickExportMenuProps {
  /** Data to export */
  data: Record<string, unknown>[];
  /** Type of data */
  dataType: ExportDataSelection["dataType"];
}

/**
 * Dropdown menu for quick export actions
 */
export function QuickExportMenu({ data, dataType }: QuickExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleQuickExport = (format: ExportFormat) => {
    const filename = `${dataType}_${new Date().toISOString().split("T")[0]}`;
    const mappings =
      dataType === "sources"
        ? SOURCE_COLUMN_MAPPINGS
        : dataType === "images"
        ? IMAGE_COLUMN_MAPPINGS
        : undefined;

    if (format === "votable") {
      downloadVOTable(data, `${filename}.vot`, {
        tableName: dataType,
        columnMappings: mappings,
      });
    } else if (format === "csv") {
      const headers = Object.keys(data[0] || {});
      const csvContent = [
        headers.join(","),
        ...data.map((row) =>
          headers.map((h) => JSON.stringify(row[h] ?? "")).join(",")
        ),
      ].join("\n");

      const blob = new Blob([csvContent], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${filename}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } else {
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${filename}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }

    setIsOpen(false);
  };

  if (data.length === 0) {
    return null;
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-md transition-colors"
        style={{
          backgroundColor: "var(--color-bg-surface)",
          color: "var(--color-text-secondary)",
          border: "1px solid var(--color-border)",
        }}
        title="Export options"
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
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div
            className="absolute right-0 mt-2 w-48 rounded-md shadow-lg z-50"
            style={{
              backgroundColor: "var(--color-bg-paper)",
              border: "1px solid var(--color-border)",
            }}
          >
            <div className="py-1">
              <button
                type="button"
                onClick={() => handleQuickExport("votable")}
                className="w-full px-4 py-2 text-left text-sm hover:bg-opacity-50 transition-colors"
                style={{
                  color: "var(--color-text-primary)",
                  backgroundColor: "transparent",
                }}
              >
                Export as VOTable
              </button>
              <button
                type="button"
                onClick={() => handleQuickExport("csv")}
                className="w-full px-4 py-2 text-left text-sm hover:bg-opacity-50 transition-colors"
                style={{
                  color: "var(--color-text-primary)",
                  backgroundColor: "transparent",
                }}
              >
                Export as CSV
              </button>
              <button
                type="button"
                onClick={() => handleQuickExport("json")}
                className="w-full px-4 py-2 text-left text-sm hover:bg-opacity-50 transition-colors"
                style={{
                  color: "var(--color-text-primary)",
                  backgroundColor: "transparent",
                }}
              >
                Export as JSON
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
