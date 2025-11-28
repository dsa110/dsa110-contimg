/**
 * Image Fitting Tool Component
 * UI controls for fitting 2D models (Gaussian, Moffat) to sources in images
 */
import { useState } from "react";
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
  Switch,
  FormControlLabel,
} from "@mui/material";
import FittingVisualization from "./FittingVisualization";
import type { FitResult } from "./FittingVisualization";
import { useImageFitting } from "../../api/queries";
import { useRegions } from "../../api/queries";

interface ImageFittingToolProps {
  displayId: string;
  imageId: number | null;
  imagePath?: string;
  onFitComplete?: (fitResult: FitResult) => void;
}

export default function ImageFittingTool({
  displayId,
  imageId,
  imagePath,
  onFitComplete,
}: ImageFittingToolProps) {
  const [model, setModel] = useState<"gaussian" | "moffat">("gaussian");
  const [regionId, setRegionId] = useState<number | null>(null);
  const [fitBackground, setFitBackground] = useState(true);
  const [showFit, setShowFit] = useState(true);

  const { data: fitResult, isPending: isLoading, error, mutate: performFit } = useImageFitting();

  // Get regions for this image
  const { data: regionsData } = useRegions(imagePath);

  const handleFit = () => {
    if (!imageId) {
      alert("Please select an image first");
      return;
    }

    performFit({
      imageId,
      model,
      regionId: regionId || undefined,
      fitBackground,
    });
  };

  const handleClearFit = () => {
    setShowFit(false);
    // The overlay will be cleared by FittingVisualization when showFit is false
  };

  // Call callback when fit completes
  if (fitResult && onFitComplete) {
    onFitComplete(fitResult);
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Image Fitting
      </Typography>

      <Box sx={{ mb: 2 }}>
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Model</InputLabel>
          <Select
            value={model}
            label="Model"
            onChange={(e) => setModel(e.target.value as "gaussian" | "moffat")}
          >
            <MenuItem value="gaussian">Gaussian</MenuItem>
            <MenuItem value="moffat">Moffat</MenuItem>
          </Select>
        </FormControl>

        {regionsData && regionsData.regions && regionsData.regions.length > 0 && (
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Region (Optional)</InputLabel>
            <Select
              value={regionId || ""}
              label="Region (Optional)"
              onChange={(e) => setRegionId(e.target.value ? Number(e.target.value) : null)}
            >
              <MenuItem value="">None (Fit entire image)</MenuItem>
              {regionsData.regions.map((region: any) => (
                <MenuItem key={region.id} value={region.id}>
                  {region.name} ({region.type})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}

        <FormControlLabel
          control={
            <Switch checked={fitBackground} onChange={(e) => setFitBackground(e.target.checked)} />
          }
          label="Fit Background"
          sx={{ mb: 2 }}
        />

        <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
          <Button
            variant="contained"
            onClick={handleFit}
            disabled={!imageId || isLoading}
            fullWidth
          >
            Fit Model
          </Button>
          <Button variant="outlined" onClick={handleClearFit} disabled={!fitResult} fullWidth>
            Clear Fit
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Error fitting model: {error instanceof Error ? error.message : "Unknown error"}
          </Alert>
        )}

        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", mb: 2 }}>
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ ml: 2 }}>
              Fitting model...
            </Typography>
          </Box>
        )}
      </Box>

      {fitResult && (
        <>
          <FormControlLabel
            control={<Switch checked={showFit} onChange={(e) => setShowFit(e.target.checked)} />}
            label="Show Fit Overlay"
            sx={{ mb: 2 }}
          />
          <FittingVisualization displayId={displayId} fitResult={fitResult} visible={showFit} />
        </>
      )}

      {!imageId && <Alert severity="warning">Please select an image to fit models to.</Alert>}
    </Paper>
  );
}
