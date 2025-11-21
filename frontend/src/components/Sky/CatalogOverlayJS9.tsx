/**
 * CatalogOverlayJS9 Component
 * Overlays catalog sources on JS9 image viewer using JS9 overlay API
 */
import { useEffect, useRef, useState } from "react";
import { Box, Typography, CircularProgress } from "@mui/material";
import { useCatalogOverlayByCoords } from "../../api/queries";
import { logger } from "../../utils/logger";
import { findDisplay } from "../../utils/js9";

declare global {
  interface Window {}
}

interface CatalogOverlayJS9Props {
  displayId?: string;
  ra: number | null;
  dec: number | null;
  radius?: number;
  catalog?: string;
  visible?: boolean;
  onSourceClick?: (source: any) => void;
}

export default function CatalogOverlayJS9({
  displayId = "js9Display",
  ra,
  dec,
  radius = 1.5,
  catalog = "all",
  visible = true,
  onSourceClick,
}: CatalogOverlayJS9Props) {
  const overlayRef = useRef<any[]>([]);
  const [hoveredSource, setHoveredSource] = useState<any | null>(null);

  const {
    data: overlayData,
    isLoading,
    error,
  } = useCatalogOverlayByCoords(ra, dec, radius, catalog);

  // Render catalog sources as JS9 overlays
  useEffect(() => {
    if (!window.JS9 || !overlayData || !visible) {
      // Clear overlays if not visible
      if (overlayRef.current.length > 0) {
        overlayRef.current.forEach((overlay: any) => {
          try {
            if (overlay && typeof overlay.remove === "function") {
              overlay.remove();
            }
          } catch (e) {
            logger.debug("Error removing overlay:", e);
          }
        });
        overlayRef.current = [];
      }
      return;
    }

    try {
      const display = findDisplay(displayId);

      if (!display?.im) {
        return; // No image loaded
      }

      // Clear existing overlays
      overlayRef.current.forEach((overlay: any) => {
        try {
          if (overlay && typeof overlay.remove === "function") {
            overlay.remove();
          }
        } catch (e) {
          logger.debug("Error removing overlay:", e);
        }
      });
      overlayRef.current = [];

      // Add new overlays for each source
      overlayData.sources.forEach((source: any, idx: number) => {
        try {
          // Convert RA/Dec to pixel coordinates using JS9 WCS
          const wcs = window.JS9.GetWCS(display.im.id, source.ra_deg * 15, source.dec_deg);
          if (!wcs || wcs.x === undefined || wcs.y === undefined) {
            return; // Skip if conversion fails
          }

          const x = wcs.x;
          const y = wcs.y;

          // Create circle overlay
          const color = getCatalogColor(source.catalog_type);
          const radius = 5; // pixels

          // Use JS9's overlay API if available
          if (typeof window.JS9.AddOverlay === "function") {
            const overlay = window.JS9.AddOverlay(display.im.id, {
              type: "circle",
              x: x,
              y: y,
              radius: radius,
              color: color,
              width: 2,
              opacity: 0.7,
              label: source.source_id || `Source ${idx + 1}`,
            });

            if (overlay) {
              overlayRef.current.push(overlay);

              // Add click handler if provided
              if (onSourceClick) {
                overlay.onclick = () => onSourceClick(source);
              }
            }
          } else {
            // Fallback: use canvas overlay (simplified)
            // This would require more complex implementation
            logger.debug("JS9.AddOverlay not available, skipping overlay");
          }
        } catch (e) {
          logger.error("Error adding catalog overlay:", e);
        }
      });
    } catch (e) {
      logger.error("Error rendering catalog overlay:", e);
    }

    // Cleanup on unmount
    return () => {
      overlayRef.current.forEach((overlay: any) => {
        try {
          if (overlay && typeof overlay.remove === "function") {
            overlay.remove();
          }
        } catch (e) {
          logger.debug("Error cleaning up overlay:", e);
        }
      });
      overlayRef.current = [];
    };
  }, [displayId, overlayData, visible, onSourceClick]);

  const getCatalogColor = (catalogType: string): string => {
    switch (catalogType?.toLowerCase()) {
      case "nvss":
        return "#2196F3"; // Blue
      case "vlass":
        return "#4CAF50"; // Green
      case "first":
        return "#F44336"; // Red
      default:
        return "#FFC107"; // Amber
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ p: 1, display: "flex", alignItems: "center", gap: 1 }}>
        <CircularProgress size={16} />
        <Typography variant="body2" color="text.secondary">
          Loading catalog...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 1 }}>
        <Typography variant="body2" color="error">
          Error loading catalog: {error instanceof Error ? error.message : "Unknown error"}
        </Typography>
      </Box>
    );
  }

  if (!overlayData || overlayData.sources.length === 0) {
    return (
      <Box sx={{ p: 1 }}>
        <Typography variant="body2" color="text.secondary">
          No catalog sources found
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="body2" color="text.secondary">
        {overlayData.count} sources loaded
      </Typography>
    </Box>
  );
}
