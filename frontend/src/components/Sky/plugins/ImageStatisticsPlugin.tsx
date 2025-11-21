/**
 * DSA Image Statistics Plugin for JS9
 * Displays real-time image statistics: peak flux, RMS noise, beam size, center coordinates, source count
 */
import { useEffect, useRef, useState, useCallback } from "react";
import {
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  CircularProgress,
  Alert,
} from "@mui/material";
import { logger } from "../../../utils/logger";
import { findDisplay, isJS9Available } from "../../../utils/js9";

declare global {
  interface Window {}
}

interface ImageStatistics {
  peakFlux: number | null;
  rmsNoise: number | null;
  beamMajorArcsec: number | null;
  beamMinorArcsec: number | null;
  beamPaDeg: number | null;
  centerRA: number | null;
  centerDec: number | null;
  sourceCount5Sigma: number | null;
  imageWidth: number | null;
  imageHeight: number | null;
}

interface ImageStatisticsPluginProps {
  displayId?: string;
  imageInfo?: {
    noise_jy?: number;
    beam_major_arcsec?: number;
    beam_minor_arcsec?: number;
    beam_pa_deg?: number;
  };
}

/**
 * Calculate image statistics from JS9 image data
 */
function calculateImageStatistics(
  imageId: string,
  imageInfo?: ImageStatisticsPluginProps["imageInfo"]
): ImageStatistics | null {
  try {
    if (!isJS9Available()) {
      return null;
    }

    // Get image data
    let imageData: any = null;
    try {
      imageData = window.JS9.GetImageData?.(imageId);
    } catch (e) {
      logger.debug("GetImageData failed:", e);
      return null;
    }

    if (!imageData || !imageData.data || !imageData.width || !imageData.height) {
      return null;
    }

    const { data, width, height } = imageData;
    const pixels: number[] = [];

    // Extract all valid pixel values
    for (let i = 0; i < data.length; i++) {
      const value = data[i];
      if (!isNaN(value) && isFinite(value)) {
        pixels.push(value);
      }
    }

    if (pixels.length === 0) {
      return null;
    }

    // Calculate peak flux
    const peakFlux = Math.max(...pixels);

    // Calculate RMS noise (standard deviation)
    const mean = pixels.reduce((sum, val) => sum + val, 0) / pixels.length;
    const variance = pixels.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / pixels.length;
    const rmsNoise = Math.sqrt(variance);

    // Get image center coordinates using WCS
    const centerX = width / 2;
    const centerY = height / 2;
    let centerRA: number | null = null;
    let centerDec: number | null = null;

    try {
      const wcs = window.JS9.GetWCS?.(imageId, centerX, centerY);
      if (wcs) {
        centerRA = wcs.ra ? wcs.ra / 15 : null; // Convert to degrees
        centerDec = wcs.dec || null;
      }
    } catch (e) {
      logger.debug("Error getting WCS:", e);
    }

    // Count sources above 5σ threshold
    // Use RMS noise * 5 as threshold
    const threshold5Sigma = rmsNoise * 5;
    const sourceCount5Sigma = pixels.filter((val) => val >= threshold5Sigma).length;

    // Get beam size from imageInfo or try to get from FITS header
    let beamMajorArcsec: number | null = imageInfo?.beam_major_arcsec || null;
    let beamMinorArcsec: number | null = imageInfo?.beam_minor_arcsec || null;
    let beamPaDeg: number | null = imageInfo?.beam_pa_deg || null;

    // Try to get from FITS header if not provided
    if (!beamMajorArcsec || !beamMinorArcsec) {
      try {
        const fitsHeader = window.JS9.GetFITSHeader?.(imageId);
        if (fitsHeader) {
          // Common FITS keywords for beam
          beamMajorArcsec = beamMajorArcsec || fitsHeader.BMAJ || fitsHeader.BEAM_MAJ || null;
          beamMinorArcsec = beamMinorArcsec || fitsHeader.BMIN || fitsHeader.BEAM_MIN || null;
          beamPaDeg = beamPaDeg || fitsHeader.BPA || fitsHeader.BEAM_PA || null;

          // Convert from degrees to arcsec if needed
          if (beamMajorArcsec && beamMajorArcsec < 1) {
            beamMajorArcsec = beamMajorArcsec * 3600;
          }
          if (beamMinorArcsec && beamMinorArcsec < 1) {
            beamMinorArcsec = beamMinorArcsec * 3600;
          }
        }
      } catch (e) {
        logger.debug("Error getting FITS header:", e);
      }
    }

    return {
      peakFlux,
      rmsNoise: imageInfo?.noise_jy || rmsNoise, // Prefer provided noise value
      beamMajorArcsec,
      beamMinorArcsec,
      beamPaDeg,
      centerRA,
      centerDec,
      sourceCount5Sigma,
      imageWidth: width,
      imageHeight: height,
    };
  } catch (error) {
    logger.error("Error calculating image statistics:", error);
    return null;
  }
}

/**
 * React component wrapper for the image statistics plugin
 */
export default function ImageStatisticsPlugin({
  displayId = "skyViewDisplay",
  imageInfo,
}: ImageStatisticsPluginProps) {
  const [stats, setStats] = useState<ImageStatistics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const lastImageIdRef = useRef<string | null>(null);

  // Update statistics function - memoized with useCallback
  const updateStatistics = useCallback(() => {
    try {
      if (!isJS9Available()) {
        setStats(null);
        setLoading(false);
        return;
      }

      const display = findDisplay(displayId);
      if (!display || !display.im) {
        setStats(null);
        setLoading(false);
        return;
      }

      const imageId = display.im.id;

      // Only recalculate if image changed
      if (lastImageIdRef.current === imageId) {
        return;
      }

      lastImageIdRef.current = imageId;
      setLoading(true);
      setError(null);

      // Calculate statistics
      const calculatedStats = calculateImageStatistics(imageId, imageInfo);

      if (calculatedStats) {
        setStats(calculatedStats);
        setError(null);
      } else {
        setError("Failed to calculate statistics");
      }
      setLoading(false);
    } catch (err: any) {
      logger.error("Error updating statistics:", err);
      setError(err.message || "Failed to update statistics");
      setLoading(false);
    }
  }, [displayId, imageInfo]);

  // Update statistics when image loads or changes
  useEffect(() => {
    if (!isJS9Available()) {
      // Wait for JS9 to be available
      const checkJS9 = setInterval(() => {
        if (isJS9Available()) {
          clearInterval(checkJS9);
          updateStatistics();
        }
      }, 100);

      const timeout = setTimeout(() => {
        clearInterval(checkJS9);
        if (!isJS9Available()) {
          setError("JS9 not available");
        }
      }, 10000);

      return () => {
        clearInterval(checkJS9);
        clearTimeout(timeout);
      };
    } else {
      updateStatistics();
    }
  }, [updateStatistics]);

  // Event handlers - memoized with useCallback to prevent unnecessary re-renders
  const handleImageDisplay = useCallback(() => {
    // Reset last image ID to force recalculation
    lastImageIdRef.current = null;

    // Small delay to ensure image is fully loaded
    setTimeout(() => {
      updateStatistics();
    }, 100);
  }, [updateStatistics]);

  const handlePanZoom = useCallback(() => {
    // Statistics don't change with pan/zoom, but we can update if needed
    // For now, we'll just ensure stats are still valid
  }, []);

  // Listen for image display events - REMOVED redundant polling
  // Events should be sufficient; polling was wasteful
  useEffect(() => {
    if (!isJS9Available()) return;

    // Register event listeners if available
    if (typeof window.JS9.AddEventListener === "function") {
      window.JS9.AddEventListener("displayimage", handleImageDisplay);
      window.JS9.AddEventListener("zoom", handlePanZoom);
      window.JS9.AddEventListener("pan", handlePanZoom);
    }

    return () => {
      if (isJS9Available() && typeof window.JS9.RemoveEventListener === "function") {
        window.JS9.RemoveEventListener("displayimage", handleImageDisplay);
        window.JS9.RemoveEventListener("zoom", handlePanZoom);
        window.JS9.RemoveEventListener("pan", handlePanZoom);
      }
    };
  }, [handleImageDisplay, handlePanZoom]);

  const formatValue = (value: number | null, unit: string = ""): string => {
    if (value === null || isNaN(value)) return "N/A";
    if (Math.abs(value) < 0.001) {
      return `${value.toExponential(3)} ${unit}`.trim();
    }
    return `${value.toFixed(3)} ${unit}`.trim();
  };

  const formatRA = (raDeg: number | null): string => {
    if (raDeg === null) return "N/A";
    const hours = raDeg / 15;
    const h = Math.floor(hours);
    const m = Math.floor((hours - h) * 60);
    const s = ((hours - h) * 60 - m) * 60;
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toFixed(1).padStart(4, "0")}`;
  };

  const formatDec = (decDeg: number | null): string => {
    if (decDeg === null) return "N/A";
    const sign = decDeg >= 0 ? "+" : "-";
    const absDec = Math.abs(decDeg);
    const d = Math.floor(absDec);
    const m = Math.floor((absDec - d) * 60);
    const s = ((absDec - d) * 60 - m) * 60;
    return `${sign}${d.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toFixed(1).padStart(4, "0")}`;
  };

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Image Statistics
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
          <CircularProgress size={24} />
        </Box>
      )}

      {stats ? (
        <Grid container spacing={2}>
          {/* Peak Flux */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Peak Flux
                </Typography>
                <Typography variant="h6">{formatValue(stats.peakFlux, "Jy/pixel")}</Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* RMS Noise */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  RMS Noise
                </Typography>
                <Typography variant="h6">{formatValue(stats.rmsNoise, "Jy")}</Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Beam Size */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Beam Size
                </Typography>
                <Typography variant="body1">
                  {stats.beamMajorArcsec !== null && stats.beamMinorArcsec !== null
                    ? `${formatValue(stats.beamMajorArcsec, "″")} × ${formatValue(stats.beamMinorArcsec, "″")}`
                    : "N/A"}
                </Typography>
                {stats.beamPaDeg !== null && (
                  <Typography variant="caption" color="text.secondary">
                    PA: {formatValue(stats.beamPaDeg, "°")}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Image Center */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Image Center
                </Typography>
                <Typography variant="body2" component="div">
                  <div>RA: {formatRA(stats.centerRA)}</div>
                  <div>Dec: {formatDec(stats.centerDec)}</div>
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Source Count */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Sources (≥5σ)
                </Typography>
                <Typography variant="h6">
                  {stats.sourceCount5Sigma !== null
                    ? stats.sourceCount5Sigma.toLocaleString()
                    : "N/A"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          {/* Image Dimensions */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Image Size
                </Typography>
                <Typography variant="body1">
                  {stats.imageWidth !== null && stats.imageHeight !== null
                    ? `${stats.imageWidth} × ${stats.imageHeight} px`
                    : "N/A"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      ) : !loading && !error ? (
        <Box sx={{ textAlign: "center", py: 3 }}>
          <Typography variant="body2" color="text.secondary">
            Load an image to display statistics
          </Typography>
        </Box>
      ) : null}
    </Paper>
  );
}
