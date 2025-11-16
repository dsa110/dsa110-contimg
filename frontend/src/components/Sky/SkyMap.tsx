/**
 * SkyMap Component
 * Interactive sky coverage map showing observed fields and telescope pointing
 */
import { useMemo, useState } from "react";
import {
  Paper,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Stack,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Divider,
} from "@mui/material";
import { PlotlyLazy } from "../PlotlyLazy";
import type { Data, Layout } from "../PlotlyLazy";
import { usePointingHistory } from "../../api/queries";
import { useImages } from "../../api/queries";
import type { ImageInfo } from "../../api/types";
import dayjs from "dayjs";

interface SkyMapProps {
  height?: number;
  historyDays?: number;
  showPointingHistory?: boolean;
  showObservedFields?: boolean;
}

interface SelectedField {
  image: ImageInfo;
  ra: number;
  dec: number;
}

export default function SkyMap({
  height = 600,
  historyDays = 7,
  showPointingHistory = true,
  showObservedFields = true,
}: SkyMapProps) {
  const [selectedField, setSelectedField] = useState<SelectedField | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Calculate MJD range for pointing history
  const { startMjd, endMjd } = useMemo(() => {
    if (!showPointingHistory) return { startMjd: 0, endMjd: 0 };
    const now = new Date();
    const startDate = new Date(now.getTime() - historyDays * 24 * 60 * 60 * 1000);
    // Convert to MJD (Unix epoch to MJD offset is 40587)
    const startMjd = startDate.getTime() / 86400000 + 40587;
    const endMjd = now.getTime() / 86400000 + 40587;
    return { startMjd, endMjd };
  }, [showPointingHistory, historyDays]);

  // Fetch pointing history
  const {
    data: historyResponse,
    isLoading: historyLoading,
    error: historyError,
  } = usePointingHistory(startMjd, endMjd);

  const historyData = historyResponse?.items || [];

  // Fetch images for observed fields
  // Use a reasonable limit and filter for images with coordinates
  const {
    data: imagesResponse,
    isLoading: imagesLoading,
    error: imagesError,
  } = useImages({
    limit: 1000, // Get up to 1000 images for coverage map
    offset: 0,
  });

  const images = imagesResponse?.items || [];

  // Filter images that have RA/Dec coordinates
  const fieldsWithCoords = useMemo(() => {
    return images.filter(
      (img) => img.center_ra_deg !== undefined && img.center_dec_deg !== undefined
    );
  }, [images]);

  // Prepare plot data
  const { plotData, layout } = useMemo(() => {
    const data: Data[] = [];

    // Add pointing history trail
    if (showPointingHistory && historyData.length > 0) {
      const ras = historyData.map((p) => p.ra_deg);
      const decs = historyData.map((p) => p.dec_deg);

      // Color code by observation time (normalize timestamps)
      const timestamps = historyData.map((p) => p.timestamp);
      const minTime = Math.min(...timestamps);
      const maxTime = Math.max(...timestamps);
      const timeRange = maxTime - minTime || 1;

      // Create color scale from blue (old) to red (recent)
      const colors = timestamps.map((ts) => {
        const normalized = (ts - minTime) / timeRange;
        // Interpolate from blue to red
        const r = Math.floor(255 * normalized);
        const b = Math.floor(255 * (1 - normalized));
        return `rgb(${r}, 100, ${b})`;
      });

      data.push({
        type: "scatter",
        mode: "lines",
        name: "Pointing History",
        x: ras,
        y: decs,
        line: {
          color: "rgba(144, 202, 249, 0.3)",
          width: 2,
        },
        hovertemplate: "RA: %{x:.2f}°<br>Dec: %{y:.2f}°<br>Time: %{customdata}<extra></extra>",
        customdata: timestamps.map((ts) => dayjs(ts * 1000).format("YYYY-MM-DD HH:mm:ss")),
        showlegend: true,
      });

      // Add colored markers for recent points
      const recentCount = Math.min(50, historyData.length);
      const recentStart = Math.max(0, historyData.length - recentCount);
      const recentRas = ras.slice(recentStart);
      const recentDecs = decs.slice(recentStart);
      const recentColors = colors.slice(recentStart);
      const recentTimestamps = timestamps.slice(recentStart);

      data.push({
        type: "scatter",
        mode: "markers",
        name: "Recent Pointing",
        x: recentRas,
        y: recentDecs,
        marker: {
          color: recentColors,
          size: 6,
          line: { color: "white", width: 1 },
        },
        hovertemplate: "RA: %{x:.2f}°<br>Dec: %{y:.2f}°<br>Time: %{customdata}<extra></extra>",
        customdata: recentTimestamps.map((ts) => dayjs(ts * 1000).format("YYYY-MM-DD HH:mm:ss")),
        showlegend: true,
      });
    }

    // Add observed fields (images)
    if (showObservedFields && fieldsWithCoords.length > 0) {
      const fieldRas = fieldsWithCoords.map((img) => img.center_ra_deg!);
      const fieldDecs = fieldsWithCoords.map((img) => img.center_dec_deg!);

      // Color code by observation time (created_at)
      const fieldTimes = fieldsWithCoords.map((img) => new Date(img.created_at).getTime());
      const minFieldTime = Math.min(...fieldTimes);
      const maxFieldTime = Math.max(...fieldTimes);
      const fieldTimeRange = maxFieldTime - minFieldTime || 1;

      // Create color scale from purple (old) to yellow (recent)
      const fieldColors = fieldTimes.map((time) => {
        const normalized = (time - minFieldTime) / fieldTimeRange;
        // Interpolate from purple to yellow
        const r = Math.floor(255 * normalized);
        const g = Math.floor(200 * normalized);
        const b = Math.floor(255 * (1 - normalized));
        return `rgb(${r}, ${g}, ${b})`;
      });

      // Size by noise level (lower noise = larger marker)
      const fieldSizes = fieldsWithCoords.map((img) => {
        if (img.noise_jy === undefined) return 8;
        // Invert noise: lower noise = larger size
        // Scale between 5 and 15 pixels
        const maxNoise = 0.01; // 10 mJy
        const normalizedNoise = Math.min(img.noise_jy / maxNoise, 1);
        return 5 + (1 - normalizedNoise) * 10;
      });

      data.push({
        type: "scatter",
        mode: "markers",
        name: "Observed Fields",
        x: fieldRas,
        y: fieldDecs,
        marker: {
          color: fieldColors,
          size: fieldSizes,
          line: { color: "white", width: 0.5 },
          opacity: 0.7,
        },
        hovertemplate:
          "Field: %{customdata[0]}<br>" +
          "RA: %{x:.2f}°<br>" +
          "Dec: %{y:.2f}°<br>" +
          "Noise: %{customdata[1]}<br>" +
          "Time: %{customdata[2]}<extra></extra>",
        customdata: fieldsWithCoords.map((img) => [
          img.path.split("/").pop() || "Unknown",
          img.noise_jy ? `${(img.noise_jy * 1000).toFixed(2)} mJy` : "N/A",
          dayjs(img.created_at).format("YYYY-MM-DD HH:mm:ss"),
          img.id, // Store image ID at index 3 for click handling
        ]),
        showlegend: true,
      });
    }

    // Create layout
    const plotLayout: Partial<Layout> = {
      title: {
        text: "Sky Coverage Map",
        font: { size: 18 },
      },
      xaxis: {
        title: { text: "Right Ascension (degrees)" },
        range: [0, 360],
        showgrid: true,
        gridcolor: "rgba(128, 128, 128, 0.2)",
        tickmode: "linear",
        tick0: 0,
        dtick: 30,
      },
      yaxis: {
        title: { text: "Declination (degrees)" },
        range: [-90, 90],
        showgrid: true,
        gridcolor: "rgba(128, 128, 128, 0.2)",
        tickmode: "linear",
        tick0: -90,
        dtick: 30,
      },
      plot_bgcolor: "#1e1e1e",
      paper_bgcolor: "#1e1e1e",
      font: { color: "#ffffff" },
      legend: {
        x: 0.02,
        y: 0.98,
        bgcolor: "rgba(0, 0, 0, 0.5)",
        bordercolor: "rgba(255, 255, 255, 0.2)",
        borderwidth: 1,
      },
      hovermode: "closest",
      height: height,
      margin: { l: 60, r: 20, t: 60, b: 60 },
    };

    return { plotData: data, layout: plotLayout };
  }, [historyData, fieldsWithCoords, showPointingHistory, showObservedFields, height]);

  // Handle plot click
  const handlePlotClick = (event: any) => {
    if (!event || !event.points || event.points.length === 0) return;

    const point = event.points[0];
    const pointData = point.data;

    // Check if clicked point is from observed fields
    if (
      pointData.name === "Observed Fields" &&
      point.customdata &&
      Array.isArray(point.customdata)
    ) {
      const imageId = point.customdata[3]; // Image ID stored at index 3
      const image = fieldsWithCoords.find((img) => img.id === imageId);

      if (image && image.center_ra_deg !== undefined && image.center_dec_deg !== undefined) {
        setSelectedField({
          image,
          ra: image.center_ra_deg ?? 0,
          dec: image.center_dec_deg ?? 0,
        });
        setDialogOpen(true);
      }
    }
  };

  const isLoading =
    (showPointingHistory && historyLoading) || (showObservedFields && imagesLoading);
  const hasError = historyError || imagesError;

  return (
    <>
      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Box>
            <Typography variant="h6" gutterBottom>
              Sky Coverage Map
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {showPointingHistory &&
                showObservedFields &&
                "Telescope pointing history and observed fields"}
              {showPointingHistory && !showObservedFields && "Telescope pointing history"}
              {!showPointingHistory && showObservedFields && "Observed fields"}
            </Typography>
          </Box>

          {hasError && (
            <Alert severity="warning">
              {historyError && "Failed to load pointing history. "}
              {imagesError && "Failed to load observed fields. "}
              Some data may be unavailable.
            </Alert>
          )}

          {isLoading ? (
            <Box
              display="flex"
              justifyContent="center"
              alignItems="center"
              minHeight={height}
              border="1px dashed rgba(255, 255, 255, 0.2)"
              borderRadius={1}
            >
              <Stack spacing={2} alignItems="center">
                <CircularProgress size={40} />
                <Typography color="text.secondary">Loading sky coverage data...</Typography>
              </Stack>
            </Box>
          ) : plotData.length > 0 ? (
            <>
              <Box>
                <Stack direction="row" spacing={2} flexWrap="wrap">
                  {showPointingHistory && historyData.length > 0 && (
                    <Chip
                      label={`${historyData.length} pointing measurements`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  )}
                  {showObservedFields && fieldsWithCoords.length > 0 && (
                    <Chip
                      label={`${fieldsWithCoords.length} observed fields`}
                      size="small"
                      color="secondary"
                      variant="outlined"
                    />
                  )}
                </Stack>
              </Box>

              <PlotlyLazy
                data={plotData}
                layout={layout}
                config={{
                  responsive: true,
                  displayModeBar: true,
                  modeBarButtonsToRemove: ["lasso2d", "select2d"],
                  displaylogo: false,
                }}
                style={{ width: "100%" }}
                onClick={handlePlotClick}
              />

              <Box>
                <Typography variant="caption" color="text.secondary">
                  {showPointingHistory &&
                    historyData.length > 0 &&
                    `Pointing history: Last ${historyDays} days. `}
                  {showObservedFields &&
                    fieldsWithCoords.length > 0 &&
                    `Click on observed field markers to view details. `}
                  Colors indicate observation time (blue/purple = older, red/yellow = recent).
                </Typography>
              </Box>
            </>
          ) : (
            <Box
              display="flex"
              justifyContent="center"
              alignItems="center"
              minHeight={height}
              border="1px dashed rgba(255, 255, 255, 0.2)"
              borderRadius={1}
            >
              <Typography color="text.secondary">No sky coverage data available</Typography>
            </Box>
          )}
        </Stack>
      </Paper>

      {/* Field Details Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Field Observation Details</DialogTitle>
        <DialogContent>
          {selectedField && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  Image Path
                </Typography>
                <Typography variant="body1" sx={{ fontFamily: "monospace", fontSize: "0.9rem" }}>
                  {selectedField.image.path}
                </Typography>
              </Box>

              <Divider />

              <Stack direction="row" spacing={4}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Right Ascension
                  </Typography>
                  <Typography variant="body1" fontWeight="bold">
                    {selectedField.ra.toFixed(4)}°
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Declination
                  </Typography>
                  <Typography variant="body1" fontWeight="bold">
                    {selectedField.dec.toFixed(4)}°
                  </Typography>
                </Box>
              </Stack>

              <Divider />

              <Stack direction="row" spacing={4}>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Observation Time
                  </Typography>
                  <Typography variant="body1">
                    {dayjs(selectedField.image.created_at).format("YYYY-MM-DD HH:mm:ss UTC")}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Image Type
                  </Typography>
                  <Typography variant="body1">{selectedField.image.type}</Typography>
                </Box>
              </Stack>

              {selectedField.image.noise_jy !== undefined && (
                <>
                  <Divider />
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Noise Level
                    </Typography>
                    <Typography variant="body1">
                      {(selectedField.image.noise_jy * 1000).toFixed(2)} mJy/beam
                    </Typography>
                  </Box>
                </>
              )}

              {selectedField.image.beam_major_arcsec !== undefined && (
                <>
                  <Divider />
                  <Stack direction="row" spacing={4}>
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        Beam Major Axis
                      </Typography>
                      <Typography variant="body1">
                        {selectedField.image.beam_major_arcsec.toFixed(1)}"
                      </Typography>
                    </Box>
                    {selectedField.image.beam_minor_arcsec !== undefined && (
                      <Box>
                        <Typography variant="subtitle2" color="text.secondary">
                          Beam Minor Axis
                        </Typography>
                        <Typography variant="body1">
                          {selectedField.image.beam_minor_arcsec.toFixed(1)}"
                        </Typography>
                      </Box>
                    )}
                  </Stack>
                </>
              )}

              {selectedField.image.image_size_deg !== undefined && (
                <>
                  <Divider />
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary">
                      Field Size
                    </Typography>
                    <Typography variant="body1">
                      {selectedField.image.image_size_deg.toFixed(3)}°
                    </Typography>
                  </Box>
                </>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
