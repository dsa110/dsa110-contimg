/**
 * Light Curve Chart Component
 *
 * Displays photometry flux measurements over time using Plotly.
 * Features:
 * - Scatter plot with error bars
 * - Optional normalized flux overlay
 * - Interactive zoom/pan
 * - Export functionality
 *
 * @module components/LightCurveChart
 */

import React from "react";
import { Box, Typography, CircularProgress, Alert, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { PlotlyLazy } from "./PlotlyLazy";

export interface FluxPoint {
  mjd: number;
  time: string;
  flux_jy: number;
  flux_err_jy: number | null;
  image_id?: string | null;
}

export interface LightCurveData {
  source_id: string;
  ra_deg: number;
  dec_deg: number;
  flux_points: FluxPoint[];
  normalized_flux_points?: FluxPoint[] | null;
}

interface LightCurveChartProps {
  data: LightCurveData | null;
  isLoading?: boolean;
  error?: Error | null;
  height?: number | string;
}

/**
 * Interactive light curve chart with error bars
 */
export function LightCurveChart({
  data,
  isLoading = false,
  error = null,
  height = 350,
}: LightCurveChartProps) {
  const [showNormalized, setShowNormalized] = React.useState(false);

  // Handle loading state
  if (isLoading) {
    return (
      <Box
        sx={{
          height,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 2,
        }}
      >
        <CircularProgress size={40} />
        <Typography variant="body2" color="text.secondary">
          Loading light curve data...
        </Typography>
      </Box>
    );
  }

  // Handle error state
  if (error) {
    return (
      <Box sx={{ height, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Alert severity="error" sx={{ maxWidth: 400 }}>
          Failed to load light curve: {error.message}
        </Alert>
      </Box>
    );
  }

  // Handle no data state
  if (!data || !data.flux_points || data.flux_points.length === 0) {
    return (
      <Box
        sx={{
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "background.default",
        }}
      >
        <Typography color="text.secondary">
          No photometry measurements available for this source
        </Typography>
      </Box>
    );
  }

  // Determine which points to display
  const hasNormalized = data.normalized_flux_points && data.normalized_flux_points.length > 0;
  const points = showNormalized && hasNormalized ? data.normalized_flux_points! : data.flux_points;

  // Prepare data for Plotly
  const mjds = points.map((p) => p.mjd);
  const fluxes = points.map((p) => p.flux_jy);
  const errors = points.map((p) => p.flux_err_jy ?? 0);
  const times = points.map((p) => p.time);
  const hasErrors = errors.some((e) => e > 0);

  // Calculate statistics for annotations
  const meanFlux = fluxes.reduce((a, b) => a + b, 0) / fluxes.length;
  const stdFlux = Math.sqrt(
    fluxes.reduce((sum, f) => sum + Math.pow(f - meanFlux, 2), 0) / fluxes.length
  );

  // Plotly trace with error bars
  const trace: any = {
    x: mjds,
    y: fluxes,
    type: "scatter",
    mode: "markers",
    name: showNormalized ? "Normalized Flux" : "Flux",
    marker: {
      color: "#1976d2",
      size: 8,
      symbol: "circle",
    },
    hovertemplate:
      "<b>MJD:</b> %{x:.4f}<br>" +
      "<b>Time:</b> %{customdata}<br>" +
      `<b>${showNormalized ? "Norm. Flux" : "Flux"}:</b> %{y:.4f} Jy` +
      (hasErrors ? "<br><b>Error:</b> %{error_y.array:.4f} Jy" : "") +
      "<extra></extra>",
    customdata: times,
  };

  // Add error bars if available
  if (hasErrors) {
    trace.error_y = {
      type: "data",
      array: errors,
      visible: true,
      color: "#1976d2",
      thickness: 1.5,
      width: 3,
    };
  }

  // Mean line trace
  const meanTrace: any = {
    x: [Math.min(...mjds), Math.max(...mjds)],
    y: [meanFlux, meanFlux],
    type: "scatter",
    mode: "lines",
    name: `Mean (${meanFlux.toFixed(4)} Jy)`,
    line: {
      color: "#ff9800",
      dash: "dash",
      width: 2,
    },
    hoverinfo: "skip",
  };

  // Layout configuration
  const layout: any = {
    autosize: true,
    height: typeof height === "number" ? height : undefined,
    margin: { l: 60, r: 40, t: 40, b: 60 },
    xaxis: {
      title: {
        text: "MJD (Modified Julian Date)",
        font: { size: 12 },
      },
      tickformat: ".2f",
      showgrid: true,
      gridcolor: "rgba(0,0,0,0.1)",
    },
    yaxis: {
      title: {
        text: showNormalized ? "Normalized Flux" : "Flux Density (Jy)",
        font: { size: 12 },
      },
      tickformat: ".4f",
      showgrid: true,
      gridcolor: "rgba(0,0,0,0.1)",
    },
    showlegend: true,
    legend: {
      x: 0,
      y: 1.15,
      orientation: "h",
      font: { size: 10 },
    },
    hovermode: "closest",
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    annotations: [
      {
        x: 1,
        y: 1.12,
        xref: "paper",
        yref: "paper",
        text: `N=${points.length} | σ=${stdFlux.toFixed(4)} Jy`,
        showarrow: false,
        font: { size: 10, color: "gray" },
        xanchor: "right",
      },
    ],
  };

  // Config for Plotly
  const config = {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
    displaylogo: false,
    toImageButtonOptions: {
      format: "png",
      filename: `lightcurve_${data.source_id}`,
      height: 600,
      width: 1000,
      scale: 2,
    },
  };

  return (
    <Box sx={{ width: "100%" }}>
      {/* Toggle for normalized view */}
      {hasNormalized && (
        <Box sx={{ mb: 1, display: "flex", justifyContent: "flex-end" }}>
          <ToggleButtonGroup
            value={showNormalized ? "normalized" : "raw"}
            exclusive
            onChange={(_, value) => {
              if (value !== null) {
                setShowNormalized(value === "normalized");
              }
            }}
            size="small"
          >
            <ToggleButton value="raw">Raw Flux</ToggleButton>
            <ToggleButton value="normalized">Normalized</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      )}

      {/* Chart */}
      <PlotlyLazy
        data={[trace, meanTrace]}
        layout={layout}
        config={config}
        style={{ width: "100%", height: typeof height === "string" ? height : `${height}px` }}
      />
    </Box>
  );
}

export default LightCurveChart;
