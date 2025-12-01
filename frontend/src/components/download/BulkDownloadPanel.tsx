import React, { useState, useCallback } from "react";

export interface DownloadItem {
  id: string;
  name: string;
  type?: string;
}

export interface BulkDownloadPanelProps {
  /** All available items for download */
  items: DownloadItem[];
  /** Currently selected item IDs */
  selectedIds: string[];
  /** Callback when selection changes */
  onSelectionChange: (ids: string[]) => void;
  /** Callback to trigger download */
  onDownload: (ids: string[], format: DownloadFormat) => Promise<void>;
  /** Custom class name */
  className?: string;
  /** Disable the panel */
  disabled?: boolean;
}

export type DownloadFormat = "fits" | "csv" | "zip" | "json";

const FORMAT_OPTIONS: { value: DownloadFormat; label: string }[] = [
  { value: "fits", label: "FITS" },
  { value: "csv", label: "CSV" },
  { value: "json", label: "JSON" },
  { value: "zip", label: "ZIP Archive" },
];

/**
 * Bulk download panel for selecting and exporting multiple items.
 */
const BulkDownloadPanel: React.FC<BulkDownloadPanelProps> = ({
  items,
  selectedIds,
  onSelectionChange,
  onDownload,
  className = "",
  disabled = false,
}) => {
  const [format, setFormat] = useState<DownloadFormat>("fits");
  const [isDownloading, setIsDownloading] = useState(false);

  const handleSelectAll = useCallback(() => {
    if (selectedIds.length === items.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(items.map((i) => i.id));
    }
  }, [items, selectedIds.length, onSelectionChange]);

  const handleToggleItem = useCallback(
    (id: string) => {
      if (selectedIds.includes(id)) {
        onSelectionChange(selectedIds.filter((i) => i !== id));
      } else {
        onSelectionChange([...selectedIds, id]);
      }
    },
    [selectedIds, onSelectionChange]
  );

  const handleDownload = useCallback(async () => {
    if (selectedIds.length === 0) return;

    setIsDownloading(true);
    try {
      await onDownload(selectedIds, format);
    } finally {
      setIsDownloading(false);
    }
  }, [selectedIds, format, onDownload]);

  const isAllSelected = selectedIds.length === items.length && items.length > 0;
  const isSomeSelected = selectedIds.length > 0 && selectedIds.length < items.length;

  return (
    <div className={`card ${className}`}>
      <div className="card-header flex items-center justify-between">
        <h4 className="text-lg font-semibold">Bulk Download</h4>
        <span className="text-sm text-gray-500">
          {selectedIds.length} of {items.length} selected
        </span>
      </div>

      <div className="card-body space-y-4">
        {/* Selection Controls */}
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isAllSelected}
              ref={(el) => {
                if (el) el.indeterminate = isSomeSelected;
              }}
              onChange={handleSelectAll}
              disabled={disabled || items.length === 0}
              className="w-4 h-4 text-vast-green rounded border-gray-300 focus:ring-vast-green"
            />
            <span className="text-sm">Select All</span>
          </label>

          {selectedIds.length > 0 && (
            <button
              onClick={() => onSelectionChange([])}
              className="text-sm text-gray-500 hover:text-red-500"
            >
              Clear selection
            </button>
          )}
        </div>

        {/* Format Selection */}
        <div className="form-group">
          <label className="form-label">Export Format</label>
          <div className="grid grid-cols-4 gap-2">
            {FORMAT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setFormat(opt.value)}
                disabled={disabled}
                className={`py-2 px-3 rounded-md text-sm font-medium transition-all ${
                  format === opt.value
                    ? "bg-vast-green text-white shadow-md"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Selected Items Preview */}
        {selectedIds.length > 0 && (
          <div className="bg-gray-50 rounded-lg p-3 max-h-40 overflow-y-auto">
            <p className="text-xs text-gray-500 mb-2">Selected items:</p>
            <div className="flex flex-wrap gap-1">
              {selectedIds.slice(0, 10).map((id) => {
                const item = items.find((i) => i.id === id);
                return (
                  <span key={id} className="badge badge-secondary flex items-center gap-1">
                    {item?.name || id}
                    <button
                      type="button"
                      onClick={() => handleToggleItem(id)}
                      className="hover:text-red-500"
                    >
                      ×
                    </button>
                  </span>
                );
              })}
              {selectedIds.length > 10 && (
                <span className="badge badge-info">+{selectedIds.length - 10} more</span>
              )}
            </div>
          </div>
        )}

        {/* Download Button */}
        <button
          onClick={handleDownload}
          disabled={disabled || selectedIds.length === 0 || isDownloading}
          className="btn btn-primary w-full"
        >
          {isDownloading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Preparing Download...
            </span>
          ) : (
            <>
              Download {selectedIds.length} item{selectedIds.length !== 1 ? "s" : ""} as{" "}
              {format.toUpperCase()}
            </>
          )}
        </button>

        {/* Format Info */}
        <div className="text-xs text-gray-500">
          {format === "fits" && "Download raw FITS files individually."}
          {format === "csv" && "Export metadata as CSV spreadsheet."}
          {format === "json" && "Export metadata as JSON."}
          {format === "zip" && "Download all files in a single ZIP archive."}
        </div>
      </div>
    </div>
  );
};

export default BulkDownloadPanel;
