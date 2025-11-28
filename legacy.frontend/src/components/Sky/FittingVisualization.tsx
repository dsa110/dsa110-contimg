/**
 * Fitting Visualization Component
 * Displays fitted 2D model overlay on JS9 image
 */
import { useEffect, useRef } from "react";
import { Box, Typography, Chip, Paper } from "@mui/material";
import { logger } from "../../utils/logger";

declare global {
  interface Window {}
}

export interface FitResult {
  model: string;
  parameters: {
    amplitude: number;
    center: {
      x: number;
      y: number;
      ra?: number;
      dec?: number;
    };
    major_axis: number;
    minor_axis: number;
    pa: number;
    background: number;
    gamma?: number;
    alpha?: number;
  };
  statistics: {
    chi_squared: number;
    reduced_chi_squared: number;
    r_squared: number;
  };
  residuals: {
    mean: number;
    std: number;
    max: number;
  };
  center_wcs?: {
    ra: number;
    dec: number;
  };
}

interface FittingVisualizationProps {
  displayId: string;
  fitResult: FitResult | null;
  visible?: boolean;
  color?: string;
}

export default function FittingVisualization({
  displayId,
  fitResult,
  visible = true,
  color = "lime",
}: FittingVisualizationProps) {
  const overlayRef = useRef<any | null>(null);

  useEffect(() => {
    if (!visible || !fitResult || !window.JS9) {
      // Clear overlay if not visible
      if (overlayRef.current) {
        try {
          if (typeof overlayRef.current.remove === "function") {
            overlayRef.current.remove();
          }
        } catch (e) {
          // Ignore errors
        }
        overlayRef.current = null;
      }
      return;
    }

    try {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });

      if (!display?.im || !window.JS9 || typeof window.JS9.AddOverlay !== "function") {
        return;
      }

      // Clear existing overlay
      if (overlayRef.current) {
        try {
          if (typeof overlayRef.current.remove === "function") {
            overlayRef.current.remove();
          }
        } catch (e) {
          // Ignore errors
        }
      }

      const params = fitResult.parameters;
      const x = params.center.x;
      const y = params.center.y;

      // Draw ellipse representing the fitted model
      // Convert major/minor axes (FWHM) to radius for ellipse
      // For visualization, we'll use major and minor axes directly
      const major_radius = params.major_axis / 2;
      const minor_radius = params.minor_axis / 2;

      // JS9 ellipse overlay
      const overlay = window.JS9.AddOverlay(display.im.id, {
        type: "ellipse",
        x: x,
        y: y,
        a: major_radius,
        b: minor_radius,
        angle: params.pa,
        color: color,
        width: 2,
      });

      if (overlay) {
        overlayRef.current = overlay;
      }

      // Also draw center point
      const centerOverlay = window.JS9.AddOverlay(display.im.id, {
        type: "circle",
        x: x,
        y: y,
        radius: 3,
        color: color,
      });

      if (centerOverlay) {
        // Store both overlays (we'll manage them together)
        overlayRef.current = { ellipse: overlay, center: centerOverlay };
      }
    } catch (e) {
      logger.error("Error adding fitting visualization overlay:", e);
    }

    // Cleanup function
    return () => {
      if (overlayRef.current) {
        try {
          if (overlayRef.current.remove && typeof overlayRef.current.remove === "function") {
            overlayRef.current.remove();
          } else if (overlayRef.current.ellipse && overlayRef.current.center) {
            // Handle multiple overlays
            if (typeof overlayRef.current.ellipse.remove === "function") {
              overlayRef.current.ellipse.remove();
            }
            if (typeof overlayRef.current.center.remove === "function") {
              overlayRef.current.center.remove();
            }
          }
        } catch (e) {
          // Ignore cleanup errors
        }
        overlayRef.current = null;
      }
    };
  }, [displayId, fitResult, visible, color]);

  if (!fitResult) {
    return null;
  }

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        Fit Results ({fitResult.model})
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 1 }}>
        <Chip label={`Amplitude: ${fitResult.parameters.amplitude.toFixed(4)}`} size="small" />
        <Chip
          label={`Center: (${fitResult.parameters.center.x.toFixed(1)}, ${fitResult.parameters.center.y.toFixed(1)})`}
          size="small"
        />
        {fitResult.center_wcs && (
          <Chip
            label={`RA: ${fitResult.center_wcs.ra.toFixed(6)}°, Dec: ${fitResult.center_wcs.dec.toFixed(6)}°`}
            size="small"
          />
        )}
        <Chip label={`Major: ${fitResult.parameters.major_axis.toFixed(2)} px`} size="small" />
        <Chip label={`Minor: ${fitResult.parameters.minor_axis.toFixed(2)} px`} size="small" />
        <Chip label={`PA: ${fitResult.parameters.pa.toFixed(1)}°`} size="small" />
        <Chip label={`Background: ${fitResult.parameters.background.toFixed(4)}`} size="small" />
      </Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
        <Chip
          label={`χ²: ${fitResult.statistics.chi_squared.toFixed(4)}`}
          size="small"
          color="primary"
          variant="outlined"
        />
        <Chip
          label={`R²: ${fitResult.statistics.r_squared.toFixed(4)}`}
          size="small"
          color="success"
          variant="outlined"
        />
        {fitResult.statistics.reduced_chi_squared && (
          <Chip
            label={`Reduced χ²: ${fitResult.statistics.reduced_chi_squared.toFixed(4)}`}
            size="small"
            color="info"
            variant="outlined"
          />
        )}
        <Chip
          label={`Residuals: μ=${fitResult.residuals.mean.toFixed(4)}, σ=${fitResult.residuals.std.toFixed(4)}`}
          size="small"
          color="warning"
          variant="outlined"
        />
      </Box>
    </Paper>
  );
}
