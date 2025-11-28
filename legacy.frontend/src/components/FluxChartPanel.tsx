/**
 * Flux Chart Panel
 * Plotly.js interactive time-series flux plots
 */
import { useMemo } from "react";
import { Paper, Typography, Box, Alert } from "@mui/material";
import { PlotlyLazy } from "./PlotlyLazy";
import type { Data, Layout } from "./PlotlyLazy";
import type { SourceTimeseries } from "../api/types";

interface FluxChartPanelProps {
  source: SourceTimeseries | null;
  height?: number;
}

export default function FluxChartPanel({ source, height = 400 }: FluxChartPanelProps) {
  const { plotData, layout } = useMemo(() => {
    if (!source || !source.flux_points || source.flux_points.length === 0) {
      return { plotData: [], layout: {} };
    }

    // Sort by time
    const sortedPoints = [...source.flux_points].sort(
      (a, b) => new Date(a.time).getTime() - new Date(b.time).getTime()
    );

    const times = sortedPoints.map((p) => p.time);
    const fluxes = sortedPoints.map((p) => p.flux_jy * 1000); // Convert to mJy
    const errors = sortedPoints.map((p) => p.flux_err_jy * 1000);

    const data: Data[] = [
      {
        type: "scatter",
        mode: "lines+markers" as any,
        name: "Flux Measurements",
        x: times,
        y: fluxes,
        error_y: {
          type: "data",
          array: errors,
          visible: true,
          color: "#90caf9",
        },
        marker: {
          color: "#90caf9",
          size: 6,
        },
        line: {
          color: "#90caf9",
          width: 1,
        },
      },
      {
        type: "scatter",
        mode: "lines",
        name: "Mean Flux",
        x: [times[0], times[times.length - 1]],
        y: [source.mean_flux_jy * 1000, source.mean_flux_jy * 1000],
        line: {
          color: "#4caf50",
          width: 2,
          dash: "dash",
        },
      },
    ];

    const plotLayout: Partial<Layout> = {
      title: source.source_id as any,
      xaxis: {
        title: "Observation Time (UTC)" as any,
        gridcolor: "#333",
        color: "#ffffff",
      },
      yaxis: {
        title: "Flux Density (mJy)" as any,
        gridcolor: "#333",
        color: "#ffffff",
      },
      paper_bgcolor: "#1e1e1e",
      plot_bgcolor: "#1e1e1e",
      font: {
        color: "#ffffff",
      },
      hovermode: "closest",
      showlegend: true,
      legend: {
        x: 1,
        xanchor: "right",
        y: 1,
        bgcolor: "rgba(30, 30, 30, 0.8)",
        bordercolor: "#666",
        borderwidth: 1,
      },
      margin: {
        l: 60,
        r: 20,
        t: 40,
        b: 60,
      },
    };

    return { plotData: data, layout: plotLayout };
  }, [source]);

  if (!source) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">Select a source to view flux timeseries</Alert>
      </Paper>
    );
  }

  if (source.flux_points.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="warning">No flux measurements available for this source</Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Box>
        <PlotlyLazy
          data={plotData}
          layout={{ ...layout, height, autosize: true }}
          config={{
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ["lasso2d", "select2d"],
            displaylogo: false,
          }}
          style={{ width: "100%" }}
        />
      </Box>

      <Box mt={2} display="flex" gap={3} flexWrap="wrap">
        <Box>
          <Typography variant="caption" color="text.secondary">
            Mean Flux
          </Typography>
          <Typography variant="body2">
            {(source.mean_flux_jy * 1000).toFixed(2)} ± {(source.std_flux_jy * 1000).toFixed(2)} mJy
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            χ²/ν
          </Typography>
          <Typography variant="body2" color={source.chi_sq_nu > 5 ? "error.main" : "text.primary"}>
            {source.chi_sq_nu.toFixed(2)}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Variability
          </Typography>
          <Typography variant="body2" color={source.is_variable ? "error.main" : "success.main"}>
            {source.is_variable ? "Variable" : "Stable"}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Observations
          </Typography>
          <Typography variant="body2">{source.flux_points.length} points</Typography>
        </Box>
      </Box>
    </Paper>
  );
}
