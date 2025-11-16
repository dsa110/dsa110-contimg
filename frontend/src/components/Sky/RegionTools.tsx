/**
 * RegionTools Component
 * Provides tools for drawing and managing regions on images
 */
import { useState } from "react";
import {
  Box,
  Button,
  ButtonGroup,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Typography,
  Tooltip,
} from "@mui/material";
import {
  RadioButtonUnchecked as CircleIcon,
  CropFree as RectangleIcon,
  ChangeHistory as PolygonIcon,
} from "@mui/icons-material";
import { logger } from "../../utils/logger";

declare global {
  interface Window {
    JS9: any;
  }
}

interface RegionToolsProps {
  displayId?: string;
  imagePath?: string | null;
  onRegionCreated?: (region: any) => void;
  onRegionDeleted?: (regionId: number) => void;
}

type DrawingMode = "none" | "circle" | "rectangle" | "polygon";

export default function RegionTools({
  displayId: _displayId = "js9Display",
  imagePath,
  onRegionCreated,
  onRegionDeleted: _onRegionDeleted,
}: RegionToolsProps) {
  const [drawingMode, setDrawingMode] = useState<DrawingMode>("none");
  const [nameDialogOpen, setNameDialogOpen] = useState(false);
  const [regionName, setRegionName] = useState("");
  const [pendingRegion, setPendingRegion] = useState<any>(null);

  const handleToolSelect = (mode: DrawingMode) => {
    if (mode === drawingMode) {
      setDrawingMode("none"); // Toggle off
    } else {
      setDrawingMode(mode);
    }
  };

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _handleRegionDrawn = (regionData: any) => {
    setPendingRegion(regionData);
    setNameDialogOpen(true);
  };

  const handleSaveRegion = async () => {
    if (!pendingRegion || !regionName.trim() || !imagePath) {
      return;
    }

    try {
      // Create region via API
      const regionData = {
        name: regionName.trim(),
        type: pendingRegion.type,
        coordinates: pendingRegion.coordinates,
        image_path: imagePath,
      };

      // Call API to create region
      const response = await fetch("/api/regions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(regionData),
      });

      if (!response.ok) {
        throw new Error("Failed to create region");
      }

      const result = await response.json();
      onRegionCreated?.(result.region);
      setNameDialogOpen(false);
      setRegionName("");
      setPendingRegion(null);
      setDrawingMode("none");
    } catch (e) {
      logger.error("Error saving region:", e);
      alert("Failed to save region. Please try again.");
    }
  };

  // Note: Actual drawing implementation would require JS9 event handlers
  // This is a simplified UI component - full implementation would need
  // mouse event handlers integrated with JS9 canvas

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        Region Tools
      </Typography>
      <ButtonGroup size="small" variant="outlined">
        <Tooltip title="Draw Circle">
          <Button
            variant={drawingMode === "circle" ? "contained" : "outlined"}
            onClick={() => handleToolSelect("circle")}
          >
            <CircleIcon />
          </Button>
        </Tooltip>
        <Tooltip title="Draw Rectangle">
          <Button
            variant={drawingMode === "rectangle" ? "contained" : "outlined"}
            onClick={() => handleToolSelect("rectangle")}
          >
            <RectangleIcon />
          </Button>
        </Tooltip>
        <Tooltip title="Draw Polygon">
          <Button
            variant={drawingMode === "polygon" ? "contained" : "outlined"}
            onClick={() => handleToolSelect("polygon")}
          >
            <PolygonIcon />
          </Button>
        </Tooltip>
      </ButtonGroup>

      {drawingMode !== "none" && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Click and drag on the image to draw a {drawingMode}
        </Typography>
      )}

      {/* Region Name Dialog */}
      <Dialog open={nameDialogOpen} onClose={() => setNameDialogOpen(false)}>
        <DialogTitle>Name Region</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Region Name"
            fullWidth
            value={regionName}
            onChange={(e) => setRegionName(e.target.value)}
            sx={{ mt: 1 }}
            placeholder="e.g., Reference Source 1"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setNameDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveRegion} variant="contained" disabled={!regionName.trim()}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
