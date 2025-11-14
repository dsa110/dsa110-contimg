/**
 * Profile Plot Component
 * Displays 1D spatial profiles extracted from images using Plotly.js
 */
import { useMemo } from "react";
import { Paper, Typography, Box, Alert, Chip } from "@mui/material";
import Plot from "react-plotly.js";
import type { Data, Layout } from "plotly.js";

export interface ProfileData {
  profile_type: string;
  distance: number[];
  flux: number[];
  error?: number[];
  coordinates: number[][];
  units: {
    distance: string;
    flux: string;
  };
  fit?: {
    model: string;
    parameters: Record<string, number>;
    statistics: {
      chi_squared: number;
      reduced_chi_squared: number;
      r_squared: number;
    };
    fitted_flux: number[];
    parameter_errors?: Record<string, number>;
  };
}

interface ProfilePlotProps {
  profileData: ProfileData | null;
  height?: number;
}

export default function ProfilePlot({
  profileData,
  height = 400,
  onExportPNG,
}: ProfilePlotProps & { onExportPNG?: () => void }) {
  const { plotData, layout, fitInfo } = useMemo(() => {
    if (!profileData || !profileData.distance || profileData.distance.length === 0) {
      return { plotData: [], layout: {}, fitInfo: null };
    }

    const data: Data[] = [];

    // Main profile data
    data.push({
      type: "scatter",
      mode: "lines+markers" as any,
      name: "Profile",
      x: profileData.distance,
      y: profileData.flux,
      error_y: profileData.error
        ? {
            type: "data",
            array: profileData.error,
            visible: true,
            color: "#90caf9",
          }
        : undefined,
      marker: {
        color: "#90caf9",
        size: 6,
      },
      line: {
        color: "#90caf9",
        width: 2,
      },
    });

    // Fitted model overlay if available
    if (profileData.fit && profileData.fit.fitted_flux) {
      data.push({
        type: "scatter",
        mode: "lines" as any,
        name: `${profileData.fit.model.charAt(0).toUpperCase() + profileData.fit.model.slice(1)} Fit`,
        x: profileData.distance,
        y: profileData.fit.fitted_flux,
        line: {
          color: "#4caf50",
          width: 2,
          dash: "dash",
        },
      });
    }

    const distanceUnit = profileData.units.distance || "arcsec";
    const fluxUnit = profileData.units.flux || "Jy/beam";

    const plotLayout: Partial<Layout> = {
      title:
        `${profileData.profile_type.charAt(0).toUpperCase() + profileData.profile_type.slice(1)} Profile` as any,
      xaxis: {
        title: `Distance (${distanceUnit})` as any,
        gridcolor: "#333",
        color: "#ffffff",
      },
      yaxis: {
        title: `Flux (${fluxUnit})` as any,
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
        x: 0.02,
        y: 0.98,
        bgcolor: "rgba(0,0,0,0.5)",
        bordercolor: "#666",
        borderwidth: 1,
      },
    };

    return {
      plotData: data,
      layout: plotLayout,
      fitInfo: profileData.fit || null,
    };
  }, [profileData]);

  if (!profileData) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Profile Plot
        </Typography>
        <Alert severity="info">
          No profile data available. Draw a profile on the image to extract data.
        </Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Profile Plot
      </Typography>
      <Box sx={{ mb: 2 }}>
        <Plot data={plotData} layout={layout} style={{ width: "100%", height: `${height}px` }} />
      </Box>
      {fitInfo && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Fit Parameters ({fitInfo.model})
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            {Object.entries(fitInfo.parameters).map(([key, value]) => (
              <Chip
                key={key}
                label={`${key}: ${value.toFixed(4)}`}
                size="small"
                variant="outlined"
              />
            ))}
          </Box>
          <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 1 }}>
            <Chip
              label={`χ²: ${fitInfo.statistics.chi_squared.toFixed(4)}`}
              size="small"
              color="primary"
              variant="outlined"
            />
            <Chip
              label={`R²: ${fitInfo.statistics.r_squared.toFixed(4)}`}
              size="small"
              color="success"
              variant="outlined"
            />
            {fitInfo.statistics.reduced_chi_squared && (
              <Chip
                label={`Reduced χ²: ${fitInfo.statistics.reduced_chi_squared.toFixed(4)}`}
                size="small"
                color="info"
                variant="outlined"
              />
            )}
          </Box>
        </Box>
      )}
    </Paper>
  );
}
