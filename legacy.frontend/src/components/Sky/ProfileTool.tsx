/**
 * Profile Tool Component
 * UI controls for drawing and extracting spatial profiles from JS9 images
 */
import { useState, useEffect, useRef } from "react";
import {
  Box,
  Paper,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import ProfilePlot from "./ProfilePlot";
import type { ProfileData } from "./ProfilePlot";
import { useProfileExtraction } from "../../api/queries";
import { logger } from "../../utils/logger";
import { findDisplay } from "../../utils/js9";

declare global {
  interface Window {}
}

interface ProfileToolProps {
  displayId: string;
  imageId: number | null;
  onProfileExtracted?: (profile: ProfileData) => void;
}

export default function ProfileTool({ displayId, imageId, onProfileExtracted }: ProfileToolProps) {
  const [profileType, setProfileType] = useState<"line" | "polyline" | "point">("line");
  const [fitModel, setFitModel] = useState<"none" | "gaussian" | "moffat">("none");
  const [coordinates, setCoordinates] = useState<number[][]>([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [radius, setRadius] = useState<number>(10.0);
  const [radiusDialogOpen, setRadiusDialogOpen] = useState(false);
  const overlayRef = useRef<any[]>([]);
  const clickHandlerRef = useRef<((e: MouseEvent) => void) | null>(null);

  const {
    data: profileData,
    isPending: isLoading,
    error,
    mutate: extractProfile,
  } = useProfileExtraction();

  // Clean up overlays when component unmounts or coordinates change
  useEffect(() => {
    return () => {
      clearOverlays();
    };
  }, []);

  const clearOverlays = () => {
    if (overlayRef.current.length > 0 && window.JS9) {
      overlayRef.current.forEach((overlay: any) => {
        try {
          if (overlay && typeof overlay.remove === "function") {
            overlay.remove();
          }
        } catch (e) {
          // Ignore errors
        }
      });
      overlayRef.current = [];
    }
  };

  const getJS9Display = () => {
    if (!window.JS9) return null;
    try {
      const display = findDisplay(displayId);
      return display?.im ? display : null;
    } catch (e) {
      logger.error("Error getting JS9 display:", e);
      return null;
    }
  };

  const pixelToWCS = (x: number, y: number): [number, number] | null => {
    const display = getJS9Display();
    if (!display?.im) return null;
    try {
      const wcs = window.JS9.GetWCS(display.im.id, x, y);
      if (wcs && wcs.ra !== undefined && wcs.dec !== undefined) {
        // JS9 returns RA in hours, convert to degrees
        return [wcs.ra * 15, wcs.dec];
      }
    } catch (e) {
      logger.error("Error converting pixel to WCS:", e);
    }
    return null;
  };

  const addOverlayLine = (
    x1: number,
    y1: number,
    x2: number,
    y2: number,
    color: string = "cyan"
  ) => {
    const display = getJS9Display();
    if (!display?.im || !window.JS9) return;

    try {
      // Use JS9's overlay API if available
      if (typeof window.JS9.AddOverlay === "function") {
        const overlay = window.JS9.AddOverlay(display.im.id, {
          type: "line",
          x1: x1,
          y1: y1,
          x2: x2,
          y2: y2,
          color: color,
          width: 2,
        });
        if (overlay) {
          overlayRef.current.push(overlay);
        }
      }
    } catch (e) {
      logger.error("Error adding overlay line:", e);
    }
  };

  const addOverlayPoint = (x: number, y: number, color: string = "cyan") => {
    const display = getJS9Display();
    if (!display?.im || !window.JS9) return;

    try {
      if (typeof window.JS9.AddOverlay === "function") {
        const overlay = window.JS9.AddOverlay(display.im.id, {
          type: "circle",
          x: x,
          y: y,
          radius: 3,
          color: color,
        });
        if (overlay) {
          overlayRef.current.push(overlay);
        }
      }
    } catch (e) {
      logger.error("Error adding overlay point:", e);
    }
  };

  const updateOverlays = () => {
    clearOverlays();
    if (coordinates.length === 0) return;

    const display = getJS9Display();
    if (!display?.im || !window.JS9) return;

    // Convert WCS coordinates back to pixels for visualization
    const pixelCoords: Array<[number, number]> = [];
    for (const coord of coordinates) {
      try {
        // JS9 GetWCS expects RA in degrees (like CatalogOverlayJS9 uses)
        // Our coordinates are stored in degrees [ra_deg, dec_deg]
        const wcs = window.JS9.GetWCS(display.im.id, coord[0] * 15, coord[1]);
        if (wcs && wcs.x !== undefined && wcs.y !== undefined) {
          pixelCoords.push([wcs.x, wcs.y]);
        }
      } catch (e) {
        logger.error("Error converting WCS to pixel for overlay:", e);
      }
    }

    if (pixelCoords.length === 0) return;

    // Draw points
    pixelCoords.forEach(([x, y]) => {
      addOverlayPoint(x, y);
    });

    // Draw lines connecting points
    if (profileType === "line" && pixelCoords.length >= 2) {
      addOverlayLine(pixelCoords[0][0], pixelCoords[0][1], pixelCoords[1][0], pixelCoords[1][1]);
    } else if (profileType === "polyline" && pixelCoords.length >= 2) {
      for (let i = 0; i < pixelCoords.length - 1; i++) {
        addOverlayLine(
          pixelCoords[i][0],
          pixelCoords[i][1],
          pixelCoords[i + 1][0],
          pixelCoords[i + 1][1]
        );
      }
    } else if (profileType === "point" && pixelCoords.length >= 1) {
      // Draw circle for point profile
      const [x, y] = pixelCoords[0];
      try {
        const display = getJS9Display();
        if (display?.im && window.JS9 && typeof window.JS9.AddOverlay === "function") {
          // Estimate radius in pixels (rough conversion)
          const pixelScale = Number(display.im.scale) || 1;
          const radiusPixels = (radius / 3600 / pixelScale) * 206265; // Rough conversion
          const overlay = window.JS9.AddOverlay(display.im.id, {
            type: "circle",
            x: x,
            y: y,
            radius: Math.max(radiusPixels, 5),
            color: "cyan",
            width: 1,
          });
          if (overlay) {
            overlayRef.current.push(overlay);
          }
        }
      } catch (e) {
        logger.error("Error adding point profile circle:", e);
      }
    }
  };

  useEffect(() => {
    updateOverlays();
  }, [coordinates, profileType, radius, displayId]);

  const handleStartDrawing = () => {
    if (!imageId) {
      alert("Please select an image first");
      return;
    }

    if (profileType === "point") {
      setRadiusDialogOpen(true);
      return;
    }

    setIsDrawing(true);
    setCoordinates([]);
    clearOverlays();

    // Attach click handler to JS9 canvas
    const display = getJS9Display();
    if (!display?.im) {
      alert("Image not loaded. Please wait for the image to load.");
      setIsDrawing(false);
      return;
    }

    const canvas = document.getElementById(displayId)?.querySelector("canvas");
    if (!canvas) {
      alert("JS9 canvas not found.");
      setIsDrawing(false);
      return;
    }

    const handleCanvasClick = (e: MouseEvent) => {
      if (!isDrawing) return;

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Convert pixel coordinates to image coordinates
      const display = getJS9Display();
      if (!display?.im) return;

      try {
        const imageCoords = window.JS9.Pix2Image(display.im.id, x, y);
        if (!imageCoords) return;

        const wcsCoords = pixelToWCS(imageCoords.x, imageCoords.y);
        if (!wcsCoords) return;

        setCoordinates((prev) => {
          const newCoords = [...prev, wcsCoords];

          // Auto-complete for line profile (2 points)
          if (profileType === "line" && newCoords.length >= 2) {
            setIsDrawing(false);
            if (clickHandlerRef.current) {
              canvas.removeEventListener("click", clickHandlerRef.current);
              clickHandlerRef.current = null;
            }
          }
          // Auto-complete for point profile (1 point)
          // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
          if ((profileType as string) === "point" && newCoords.length >= 1) {
            setIsDrawing(false);
            if (clickHandlerRef.current) {
              canvas.removeEventListener("click", clickHandlerRef.current);
              clickHandlerRef.current = null;
            }
          }

          return newCoords;
        });
      } catch (e) {
        logger.error("Error handling canvas click:", e);
      }
    };

    clickHandlerRef.current = handleCanvasClick;
    canvas.addEventListener("click", handleCanvasClick);

    // Instructions
    if (profileType === "line") {
      alert("Click two points on the image to define a line profile.");
    } else if (profileType === "polyline") {
      alert('Click multiple points on the image. Press "Extract Profile" when done.');
    }
  };

  const handleStopDrawing = () => {
    setIsDrawing(false);
    const display = getJS9Display();
    if (display?.im) {
      const canvas = document.getElementById(displayId)?.querySelector("canvas");
      if (canvas && clickHandlerRef.current) {
        canvas.removeEventListener("click", clickHandlerRef.current);
        clickHandlerRef.current = null;
      }
    }
  };

  const handlePointRadiusConfirm = () => {
    setRadiusDialogOpen(false);
    setIsDrawing(true);
    setCoordinates([]);
    clearOverlays();

    const display = getJS9Display();
    if (!display?.im) {
      alert("Image not loaded. Please wait for the image to load.");
      setIsDrawing(false);
      return;
    }

    const canvas = document.getElementById(displayId)?.querySelector("canvas");
    if (!canvas) {
      alert("JS9 canvas not found.");
      setIsDrawing(false);
      return;
    }

    const handleCanvasClick = (e: MouseEvent) => {
      if (!isDrawing) return;

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const display = getJS9Display();
      if (!display?.im) return;

      try {
        const imageCoords = window.JS9.Pix2Image(display.im.id, x, y);
        if (!imageCoords) return;

        const wcsCoords = pixelToWCS(imageCoords.x, imageCoords.y);
        if (!wcsCoords) return;

        setCoordinates([wcsCoords]);
        setIsDrawing(false);
        if (clickHandlerRef.current) {
          canvas.removeEventListener("click", clickHandlerRef.current);
          clickHandlerRef.current = null;
        }
      } catch (e) {
        logger.error("Error handling canvas click:", e);
      }
    };

    clickHandlerRef.current = handleCanvasClick;
    canvas.addEventListener("click", handleCanvasClick);
    alert("Click a point on the image to define the center of the radial profile.");
  };

  const handleExtractProfile = () => {
    if (!imageId) {
      alert("Please select an image first");
      return;
    }

    if (profileType === "point" && coordinates.length < 1) {
      alert("Please provide at least 1 coordinate for point profile");
      return;
    }

    if (profileType !== "point" && coordinates.length < 2) {
      alert(`Please provide at least 2 coordinates for ${profileType} profile`);
      return;
    }

    extractProfile({
      imageId,
      profileType,
      coordinates,
      coordinateSystem: "wcs",
      width: 1,
      radius: 10.0,
      fitModel: fitModel === "none" ? undefined : fitModel,
    });
  };

  const handleClearProfile = () => {
    setCoordinates([]);
    setIsDrawing(false);
    clearOverlays();
    handleStopDrawing();
  };

  const handleExportProfile = () => {
    if (!profileData) return;

    // Export as CSV
    const csvLines = ["Distance,Flux,Error"];
    for (let i = 0; i < profileData.distance.length; i++) {
      const dist = profileData.distance[i];
      const flux = profileData.flux[i];
      const error = profileData.error?.[i] || "";
      csvLines.push(`${dist},${flux},${error}`);
    }

    const csvContent = csvLines.join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `profile_${profileType}_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Call callback when profile is extracted
  if (profileData && onProfileExtracted) {
    onProfileExtracted(profileData as ProfileData);
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Spatial Profiler
      </Typography>

      <Box sx={{ mb: 2 }}>
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Profile Type</InputLabel>
          <Select
            value={profileType}
            label="Profile Type"
            onChange={(e) => {
              setProfileType(e.target.value as "line" | "polyline" | "point");
              setCoordinates([]);
            }}
          >
            <MenuItem value="line">Line</MenuItem>
            <MenuItem value="polyline">Polyline</MenuItem>
            <MenuItem value="point">Point (Radial)</MenuItem>
          </Select>
        </FormControl>

        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Fit Model</InputLabel>
          <Select
            value={fitModel}
            label="Fit Model"
            onChange={(e) => setFitModel(e.target.value as "none" | "gaussian" | "moffat")}
          >
            <MenuItem value="none">None</MenuItem>
            <MenuItem value="gaussian">Gaussian</MenuItem>
            <MenuItem value="moffat">Moffat</MenuItem>
          </Select>
        </FormControl>

        <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
          <Button
            variant={isDrawing ? "contained" : "outlined"}
            color={isDrawing ? "warning" : "primary"}
            onClick={isDrawing ? handleStopDrawing : handleStartDrawing}
            disabled={!imageId || isLoading}
            sx={{ flex: 1, minWidth: "120px" }}
          >
            {isDrawing ? "Stop Drawing" : "Draw Profile"}
          </Button>
          <Button
            variant="contained"
            onClick={handleExtractProfile}
            disabled={!imageId || coordinates.length === 0 || isLoading}
            sx={{ flex: 1, minWidth: "120px" }}
          >
            Extract Profile
          </Button>
          <Button
            variant="outlined"
            onClick={handleClearProfile}
            disabled={coordinates.length === 0 && !isDrawing}
            sx={{ flex: 1, minWidth: "120px" }}
          >
            Clear
          </Button>
        </Box>

        {isDrawing && (
          <Alert severity="info" sx={{ mb: 2 }}>
            {profileType === "line" && "Click two points on the image to define a line."}
            {profileType === "polyline" &&
              'Click multiple points on the image. Click "Extract Profile" when done.'}
            {profileType === "point" &&
              `Click a point on the image to define the center (radius: ${radius} arcsec).`}
          </Alert>
        )}

        {coordinates.length > 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            {coordinates.length} coordinate{coordinates.length !== 1 ? "s" : ""} defined
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Error extracting profile: {error instanceof Error ? error.message : "Unknown error"}
          </Alert>
        )}

        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
      </Box>

      {profileData && (
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, mb: 1 }}>
            <Button variant="outlined" size="small" onClick={handleExportProfile}>
              Export CSV
            </Button>
          </Box>
          <ProfilePlot profileData={profileData} />
        </Box>
      )}

      {!imageId && (
        <Alert severity="warning">Please select an image to extract profiles from.</Alert>
      )}

      {/* Radius Dialog for Point Profile */}
      <Dialog open={radiusDialogOpen} onClose={() => setRadiusDialogOpen(false)}>
        <DialogTitle>Set Radial Profile Radius</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Radius (arcseconds)"
            type="number"
            fullWidth
            value={radius}
            onChange={(e) => setRadius(parseFloat(e.target.value) || 10.0)}
            inputProps={{ min: 0.1, step: 0.1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRadiusDialogOpen(false)}>Cancel</Button>
          <Button onClick={handlePointRadiusConfirm}>Confirm</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
