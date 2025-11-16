/**
 * Contour Overlay Component for JS9
 * Renders contour paths from CASA imview analysis as JS9 overlays
 */
import { useEffect, useRef } from "react";
import { logger } from "../../../utils/logger";

declare global {
  interface Window {
    JS9: any;
  }
}

interface ContourPath {
  x: number[];
  y: number[];
}

interface ContourLevel {
  level: number;
  paths: ContourPath[];
}

interface ContourData {
  contour_levels?: number[];
  contour_paths?: ContourLevel[];
  image_shape?: number[];
  data_range?: { min: number; max: number };
}

interface ContourOverlayProps {
  displayId: string;
  contourData: ContourData | null;
  visible?: boolean;
  color?: string;
  lineWidth?: number;
  opacity?: number;
}

/**
 * Get color for contour level based on value
 */
const getContourColor = (
  level: number,
  min: number,
  max: number,
  baseColor: string = "cyan"
): string => {
  // Normalize level to 0-1 range
  const normalized = (level - min) / (max - min);

  // Use different shades/intensities based on level
  // Higher levels get brighter colors
  const _intensity = Math.floor(128 + normalized * 127);

  // Convert hex color to RGB if needed
  if (baseColor.startsWith("#")) {
    const r = parseInt(baseColor.slice(1, 3), 16);
    const g = parseInt(baseColor.slice(3, 5), 16);
    const b = parseInt(baseColor.slice(5, 7), 16);

    // Blend with intensity
    const newR = Math.floor(r * (0.5 + normalized * 0.5));
    const newG = Math.floor(g * (0.5 + normalized * 0.5));
    const newB = Math.floor(b * (0.5 + normalized * 0.5));

    return `rgb(${newR}, ${newG}, ${newB})`;
  }

  return baseColor;
};

export default function ContourOverlay({
  displayId,
  contourData,
  visible = true,
  color = "cyan",
  lineWidth = 1,
  opacity = 0.8,
}: ContourOverlayProps) {
  const overlayRefs = useRef<any[]>([]);

  useEffect(() => {
    // Clear existing overlays
    overlayRefs.current.forEach((overlay) => {
      try {
        if (overlay && typeof overlay.remove === "function") {
          overlay.remove();
        }
      } catch (e) {
        // Ignore cleanup errors
      }
    });
    overlayRefs.current = [];

    if (!visible || !contourData || !window.JS9) {
      return;
    }

    try {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });

      if (!display?.im || typeof window.JS9.AddOverlay !== "function") {
        return;
      }

      const { contour_paths, data_range } = contourData;

      if (!contour_paths || contour_paths.length === 0) {
        logger.debug("No contour paths to render");
        return;
      }

      const min = data_range?.min ?? 0;
      const max = data_range?.max ?? 1;

      // Render each contour level
      contour_paths.forEach((levelData) => {
        const { level, paths } = levelData;

        // Get color for this level
        const levelColor = getContourColor(level, min, max, color);

        // Render each path in this level
        paths.forEach((path) => {
          const { x, y } = path;

          if (!x || !y || x.length === 0 || y.length === 0) {
            return;
          }

          // Draw contour as connected line segments
          // JS9 doesn't have a direct polyline overlay, so we draw line segments
          for (let i = 0; i < x.length - 1; i++) {
            try {
              const overlay = window.JS9.AddOverlay(display.im.id, {
                type: "line",
                x1: x[i],
                y1: y[i],
                x2: x[i + 1],
                y2: y[i + 1],
                color: levelColor,
                width: lineWidth,
                opacity: opacity,
              });

              if (overlay) {
                overlayRefs.current.push(overlay);
              }
            } catch (e) {
              logger.error("Error adding contour line segment:", e);
            }
          }
        });
      });

      logger.debug(`Rendered ${overlayRefs.current.length} contour line segments`);
    } catch (e) {
      logger.error("Error rendering contour overlay:", e);
    }

    // Cleanup function
    return () => {
      overlayRefs.current.forEach((overlay) => {
        try {
          if (overlay && typeof overlay.remove === "function") {
            overlay.remove();
          }
        } catch (e) {
          // Ignore cleanup errors
        }
      });
      overlayRefs.current = [];
    };
  }, [displayId, contourData, visible, color, lineWidth, opacity]);

  // Component doesn't render anything visible (overlays are drawn on JS9 canvas)
  return null;
}
