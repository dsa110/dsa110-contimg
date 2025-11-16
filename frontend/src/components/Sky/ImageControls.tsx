/**
 * ImageControls Component
 * Provides controls for JS9 image viewer (zoom, colormap, grid, coordinates)
 */
import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Button,
  ButtonGroup,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Tooltip,
} from "@mui/material";
import {
  ZoomIn,
  ZoomOut,
  FitScreen,
  GridOn,
  GridOff,
  LocationOn,
} from "@mui/icons-material";
import { logger } from "../../utils/logger";
import { findDisplay, isJS9Available } from "../../utils/js9";
import { useJS9Safe } from "../../contexts/JS9Context";
// import styles from "./Sky.module.css";

declare global {
  interface Window {
    JS9: any;
  }
}

interface ImageControlsProps {
  displayId?: string;
  onImageLoad?: (imagePath: string) => void;
}

export default function ImageControls({
  displayId = "js9Display",
  onImageLoad,
}: ImageControlsProps) {
  // Use JS9 context if available (backward compatible)
  const js9Context = useJS9Safe();
  const isJS9Ready = js9Context?.isJS9Ready ?? isJS9Available();
  const getDisplaySafe = (id: string) => js9Context?.getDisplay(id) ?? findDisplay(id);

  const [colormap, setColormap] = useState("grey");
  const [gridVisible, setGridVisible] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [coordDialogOpen, setCoordDialogOpen] = useState(false);
  const [raInput, setRaInput] = useState("");
  const [decInput, setDecInput] = useState("");

  // Update zoom level - use zoom event instead of polling
  const updateZoom = useCallback(() => {
    try {
      if (!isJS9Ready) return;
      const display = getDisplaySafe(displayId);
      if (display?.im) {
        const currentZoom = window.JS9.GetZoom?.(display.im.id) || 1;
        setZoomLevel(currentZoom);
      }
    } catch (e) {
      logger.debug("Error getting zoom level:", e);
    }
  }, [displayId, isJS9Ready, getDisplaySafe]);

  // Listen for zoom events instead of polling
  useEffect(() => {
    if (!isJS9Ready) return;

    // Initial zoom level
    updateZoom();

    // Listen for zoom events
    if (typeof window.JS9.AddEventListener === "function") {
      window.JS9.AddEventListener("zoom", updateZoom);
    }

    return () => {
      if (isJS9Ready && typeof window.JS9.RemoveEventListener === "function") {
        window.JS9.RemoveEventListener("zoom", updateZoom);
      }
    };
  }, [updateZoom]);

  const handleZoomIn = useCallback(() => {
    if (!isJS9Ready) return;
    try {
      const display = getDisplaySafe(displayId);
      if (display?.im) {
        const currentZoom = window.JS9.GetZoom?.(display.im.id) || 1;
        window.JS9.SetZoom?.(display.im.id, currentZoom * 1.5);
        // Zoom event will update zoomLevel
      }
    } catch (e) {
      logger.error("Error zooming in:", e);
    }
  }, [displayId]);

  const handleZoomOut = useCallback(() => {
    if (!isJS9Ready) return;
    try {
      const display = getDisplaySafe(displayId);
      if (display?.im) {
        const currentZoom = window.JS9.GetZoom?.(display.im.id) || 1;
        window.JS9.SetZoom?.(display.im.id, currentZoom / 1.5);
        // Zoom event will update zoomLevel
      }
    } catch (e) {
      logger.error("Error zooming out:", e);
    }
  }, [displayId, isJS9Ready, getDisplaySafe]);

  const handleZoomReset = useCallback(() => {
    if (!isJS9Ready) return;
    try {
      const display = getDisplaySafe(displayId);
      if (display?.im) {
        window.JS9.SetZoom?.(display.im.id, "fit");
        // Zoom event will update zoomLevel
      }
    } catch (e) {
      logger.error("Error resetting zoom:", e);
    }
  }, [displayId, isJS9Ready, getDisplaySafe]);

  const handleColormapChange = useCallback(
    (newColormap: string) => {
      if (!isJS9Ready) return;
      setColormap(newColormap);
      try {
        const display = getDisplaySafe(displayId);
        if (display?.im) {
          window.JS9.SetColormap?.(display.im.id, newColormap);
          // Store preference
          localStorage.setItem("js9_colormap", newColormap);
        }
      } catch (e) {
        logger.error("Error changing colormap:", e);
      }
    },
    [displayId]
  );

  const handleGridToggle = useCallback(() => {
    if (!isJS9Ready) return;
    const newGridVisible = !gridVisible;
    setGridVisible(newGridVisible);
    try {
      const display = getDisplaySafe(displayId);
      if (display?.im) {
        if (newGridVisible) {
          window.JS9.SetGrid?.(display.im.id, true);
        } else {
          window.JS9.SetGrid?.(display.im.id, false);
        }
      }
    } catch (e) {
      logger.error("Error toggling grid:", e);
    }
  }, [displayId, gridVisible, isJS9Ready, getDisplaySafe]);

  const handleGoToCoordinates = () => {
    setCoordDialogOpen(true);
  };

  const handleCoordSubmit = () => {
    if (!window.JS9 || !raInput || !decInput) return;

    try {
      // Parse RA/Dec input (accept various formats)
      const ra = parseCoordinate(raInput, "ra");
      const dec = parseCoordinate(decInput, "dec");

      if (ra === null || dec === null) {
        alert('Invalid coordinate format. Please use format like "12:34:56.7" or "188.5"');
        return;
      }

      const display = getDisplaySafe(displayId);
      if (display?.im) {
        // Convert RA/Dec to pixel coordinates and pan
        window.JS9.SetPan(display.im.id, ra, dec);
        setCoordDialogOpen(false);
        setRaInput("");
        setDecInput("");
      }
    } catch (e) {
      logger.error("Error going to coordinates:", e);
      alert("Error navigating to coordinates. Please check the format.");
    }
  };

  // Parse coordinate string (RA or Dec) to degrees
  const parseCoordinate = (coord: string, type: "ra" | "dec"): number | null => {
    try {
      // Try decimal degrees first
      const decimal = parseFloat(coord);
      if (!isNaN(decimal)) {
        return decimal;
      }

      // Try sexagesimal format (HH:MM:SS or DD:MM:SS)
      const parts = coord.split(":").map((p) => parseFloat(p.trim()));
      if (parts.length === 3 && parts.every((p) => !isNaN(p))) {
        if (type === "ra") {
          // RA: hours to degrees
          return (parts[0] + parts[1] / 60 + parts[2] / 3600) * 15;
        } else {
          // Dec: degrees
          const sign = coord.trim().startsWith("-") ? -1 : 1;
          return sign * (Math.abs(parts[0]) + parts[1] / 60 + parts[2] / 3600);
        }
      }

      return null;
    } catch (e) {
      return null;
    }
  };

  // Hide JS9 default menubar and integrate controls into dashboard
  // Note: JS9 keeps recreating menubar, so polling is necessary
  useEffect(() => {
    if (!isJS9Ready) return;

    const hideJS9Menubar = () => {
      // Hide JS9 menubar elements
      const selectors = [
        ".JS9Menubar",
        ".js9-menubar",
        ".JS9 .JS9Menubar",
        ".JS9 .js9-menubar",
        '[class*="JS9Menubar"]',
        '[class*="js9-menubar"]',
      ];

      selectors.forEach((selector) => {
        try {
          const elements = document.querySelectorAll(selector);
          elements.forEach((el: any) => {
            if (el && el.style) {
              el.style.display = "none";
              el.style.visibility = "hidden";
              el.style.height = "0";
              el.style.overflow = "hidden";
            }
          });
        } catch (e) {
          // Ignore selector errors
        }
      });
    };

    // Hide immediately and set up interval
    hideJS9Menubar();
    const interval = setInterval(hideJS9Menubar, 500);

    return () => clearInterval(interval);
  }, []);

  // Load saved colormap preference
  useEffect(() => {
    const savedColormap = localStorage.getItem("js9_colormap");
    if (savedColormap) {
      setColormap(savedColormap);
      handleColormapChange(savedColormap);
    }
  }, []);

  return (
    <Box
      sx={{
        display: "flex",
        gap: 1,
        flexWrap: "wrap",
        alignItems: "center",
        mb: 2,
      }}
    >
      {/* Zoom Controls */}
      <ButtonGroup size="small" variant="outlined">
        <Tooltip title="Zoom out (reduce magnification)">
          <Button onClick={handleZoomOut}>
            <ZoomOut />
          </Button>
        </Tooltip>
        <Tooltip title="Fit image to display size">
          <Button onClick={handleZoomReset}>
            <FitScreen />
          </Button>
        </Tooltip>
        <Tooltip title="Zoom in (increase magnification)">
          <Button onClick={handleZoomIn}>
            <ZoomIn />
          </Button>
        </Tooltip>
      </ButtonGroup>

      {/* Zoom Level Display */}
      <Tooltip title="Current zoom level">
        <Typography variant="body2" sx={{ minWidth: "70px", fontWeight: "medium" }}>
          Zoom: {zoomLevel.toFixed(1)}x
        </Typography>
      </Tooltip>

      {/* Colormap Selector */}
      <Tooltip title="Select color scheme for image display">
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Colormap</InputLabel>
          <Select
            value={colormap}
            label="Colormap"
            onChange={(e) => handleColormapChange(e.target.value)}
          >
            <MenuItem value="grey">Grey</MenuItem>
            <MenuItem value="hot">Hot</MenuItem>
            <MenuItem value="cool">Cool</MenuItem>
            <MenuItem value="rainbow">Rainbow</MenuItem>
            <MenuItem value="red">Red</MenuItem>
            <MenuItem value="green">Green</MenuItem>
            <MenuItem value="blue">Blue</MenuItem>
          </Select>
        </FormControl>
      </Tooltip>

      {/* Grid Toggle */}
      <Tooltip title={gridVisible ? "Hide coordinate grid" : "Show coordinate grid"}>
        <Button
          size="small"
          variant={gridVisible ? "contained" : "outlined"}
          onClick={handleGridToggle}
        >
          {gridVisible ? <GridOn /> : <GridOff />}
        </Button>
      </Tooltip>

      {/* Go To Coordinates */}
      <Tooltip title="Navigate to specific RA/Dec coordinates">
        <Button
          size="small"
          variant="outlined"
          onClick={handleGoToCoordinates}
          startIcon={<LocationOn />}
        >
          Go To
        </Button>
      </Tooltip>

      {/* Coordinate Dialog */}
      <Dialog open={coordDialogOpen} onClose={() => setCoordDialogOpen(false)}>
        <DialogTitle>Go To Coordinates</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Enter coordinates in decimal degrees (e.g., 188.5) or sexagesimal format (e.g.,
            12:34:56.7)
          </Typography>
          <TextField
            label="RA (degrees or HH:MM:SS)"
            value={raInput}
            onChange={(e) => setRaInput(e.target.value)}
            fullWidth
            sx={{ mb: 2 }}
            placeholder="12:34:56.7 or 188.5"
          />
          <TextField
            label="Dec (degrees or DD:MM:SS)"
            value={decInput}
            onChange={(e) => setDecInput(e.target.value)}
            fullWidth
            placeholder="+42:03:12 or 42.05"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCoordDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCoordSubmit} variant="contained">
            Go
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
