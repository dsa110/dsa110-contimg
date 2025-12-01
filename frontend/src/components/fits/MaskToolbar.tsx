import React, { useState, useCallback } from "react";
import RegionToolbar, { Region, RegionFormat } from "./RegionToolbar";
import { logger } from "../../utils/logger";
import { config } from "../../config";

/**
 * Props for the MaskToolbar component.
 */
export interface MaskToolbarProps {
  /** The JS9 display ID to operate on */
  displayId: string;
  /** Image ID for saving masks to the backend */
  imageId: string;
  /** Callback when mask is saved */
  onMaskSaved?: (maskPath: string) => void;
  /** Callback when mask creation mode changes */
  onModeChange?: (isCreating: boolean) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Response from the mask save endpoint.
 */
interface MaskSaveResponse {
  id: string;
  path: string;
  format: string;
  region_count: number;
  created_at: string;
}

/**
 * Mask toolbar component for creating and saving clean masks.
 *
 * Extends RegionToolbar with backend integration for saving masks
 * that can be used during re-imaging.
 */
const MaskToolbar: React.FC<MaskToolbarProps> = ({
  displayId,
  imageId,
  onMaskSaved,
  onModeChange: _onModeChange,
  className = "",
}) => {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [lastSaved, setLastSaved] = useState<string | null>(null);

  /**
   * Convert regions to DS9 format string for backend.
   */
  const regionsToDS9 = useCallback((regions: Region[]): string => {
    const lines = [
      "# Region file format: DS9 version 4.1",
      'global color=green dashlist=8 3 width=1 font="helvetica 10 normal roman" select=1 highlite=1 dash=0 fixed=0 edit=1 move=1 delete=1 include=1 source=1',
      "image",
    ];

    for (const region of regions) {
      let line = "";

      switch (region.shape) {
        case "circle":
          line = `circle(${region.x},${region.y},${region.radius || 10})`;
          break;
        case "box":
          line = `box(${region.x},${region.y},${region.width || 20},${
            region.height || 20
          },0)`;
          break;
        case "ellipse":
          line = `ellipse(${region.x},${region.y},${region.width || 20},${
            region.height || 10
          },0)`;
          break;
        case "polygon":
          if (region.points && region.points.length > 0) {
            const coords = region.points.map((p) => `${p.x},${p.y}`).join(",");
            line = `polygon(${coords})`;
          }
          break;
        default:
          // Skip other shapes for masks
          continue;
      }

      if (line) {
        lines.push(line);
      }
    }

    return lines.join("\n");
  }, []);

  /**
   * Save mask regions to the backend.
   */
  const handleSaveMask = useCallback(
    async (regions: Region[], _format: RegionFormat) => {
      if (regions.length === 0) {
        setSaveError("No regions to save as mask");
        return;
      }

      setIsSaving(true);
      setSaveError(null);

      try {
        const ds9Content = regionsToDS9(regions);
        const encodedImageId = encodeURIComponent(imageId);

        const response = await fetch(
          `${config.api.baseUrl}/images/${encodedImageId}/masks`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              format: "ds9",
              regions: ds9Content,
            }),
          }
        );

        if (!response.ok) {
          const error = await response.text();
          throw new Error(error || `HTTP ${response.status}`);
        }

        const data: MaskSaveResponse = await response.json();
        setLastSaved(data.path);
        onMaskSaved?.(data.path);
        logger.info("Mask saved successfully", {
          path: data.path,
          regionCount: data.region_count,
        });
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to save mask";
        setSaveError(message);
        logger.error("Failed to save mask", { error: err });
      } finally {
        setIsSaving(false);
      }
    },
    [imageId, regionsToDS9, onMaskSaved]
  );

  return (
    <div className={`mask-toolbar ${className}`}>
      {/* Status banner */}
      {(saveError || lastSaved) && (
        <div
          className={`mb-2 px-3 py-1.5 rounded text-sm ${
            saveError
              ? "bg-red-100 text-red-700"
              : "bg-green-100 text-green-700"
          }`}
        >
          {saveError ? (
            <>
              <strong>Error:</strong> {saveError}
            </>
          ) : (
            <>
              <strong>Saved:</strong> {lastSaved?.split("/").pop()}
            </>
          )}
        </div>
      )}

      {/* Region toolbar */}
      <RegionToolbar
        displayId={displayId}
        onSave={handleSaveMask}
        className=""
        compact={false}
      />

      {/* Saving indicator */}
      {isSaving && (
        <div className="mt-2 flex items-center gap-2 text-sm text-gray-600">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Saving mask...
        </div>
      )}

      {/* Usage hint */}
      <div className="mt-2 text-xs text-gray-500">
        Draw regions to define clean mask areas. Saved masks can be used during
        re-imaging.
      </div>
    </div>
  );
};

export default MaskToolbar;
