/**
 * Calibration QA Panel Component
 * Displays calibration quality metrics, bandpass plots, and quality indicators
 */

import {
  Paper,
  Typography,
  Box,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Stack,
} from "@mui/material";
import { CheckCircle, Warning, Error, Help } from "@mui/icons-material";
import { useState } from "react";
// import Plot from 'react-plotly.js'; // Unused for now
// import type { CalibrationQA } from '../api/types'; // Unused for now
import { useCalibrationQA, useBandpassPlots } from "../api/queries";

interface CalibrationQAPanelProps {
  msPath: string | null;
}

type QualityLevel = "excellent" | "good" | "marginal" | "poor" | "unknown";

function QualityIndicator({ quality }: { quality: QualityLevel }) {
  const config = {
    excellent: {
      color: "success" as const,
      icon: <CheckCircle />,
      label: "Excellent",
    },
    good: { color: "info" as const, icon: <CheckCircle />, label: "Good" },
    marginal: {
      color: "warning" as const,
      icon: <Warning />,
      label: "Marginal",
    },
    poor: { color: "error" as const, icon: <Error />, label: "Poor" },
    unknown: { color: "default" as const, icon: <Help />, label: "Unknown" },
  };

  const { color, icon, label } = config[quality] || config.unknown;

  return <Chip icon={icon} label={label} color={color} size="small" sx={{ fontWeight: "bold" }} />;
}

function MetricCard({
  label,
  value,
  unit,
  goodThreshold,
  warningThreshold,
}: {
  label: string;
  value: number | null | undefined;
  unit?: string;
  goodThreshold?: number;
  warningThreshold?: number;
}) {
  if (value === null || value === undefined) {
    return (
      <Box>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="body2">N/A</Typography>
      </Box>
    );
  }

  let color: "success" | "warning" | "error" | "default" = "default";
  if (goodThreshold !== undefined && value >= goodThreshold) {
    color = "success";
  } else if (warningThreshold !== undefined && value >= warningThreshold) {
    color = "warning";
  } else if (warningThreshold !== undefined) {
    color = "error";
  }

  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" color={color === "default" ? "text.primary" : `${color}.main`}>
        <strong>{value.toFixed(2)}</strong> {unit || ""}
      </Typography>
    </Box>
  );
}

export default function CalibrationQAPanel({ msPath }: CalibrationQAPanelProps) {
  const { data: qa, isLoading, error } = useCalibrationQA(msPath);
  const { data: bandpassPlots } = useBandpassPlots(msPath);
  const [tabValue, setTabValue] = useState(0);

  if (!msPath) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">Select a Measurement Set to view calibration QA</Alert>
      </Paper>
    );
  }

  if (isLoading) {
    return (
      <Paper sx={{ p: 3, textAlign: "center" }}>
        <CircularProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>
          Loading calibration QA...
        </Typography>
      </Paper>
    );
  }

  if (error || !qa) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="warning">
          {error ? "Failed to load calibration QA" : "No calibration QA data available"}
        </Alert>
      </Paper>
    );
  }

  const quality = (qa.overall_quality || "unknown") as QualityLevel;

  return (
    <Paper sx={{ p: 3 }}>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h6">Calibration Quality Assessment</Typography>
        <QualityIndicator quality={quality} />
      </Stack>

      <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ mb: 3 }}>
        <Tab label="Overview" />
        <Tab label="K-Calibration" />
        <Tab label="Bandpass" />
        <Tab label="G-Calibration" />
        <Tab label="Plots" />
      </Tabs>

      {tabValue === 0 && (
        <Grid container spacing={2}>
          <Grid item xs={12} {...({} as any)}>
            <Alert
              severity={
                quality === "poor" ? "error" : quality === "marginal" ? "warning" : "success"
              }
            >
              Overall Quality: <strong>{qa.overall_quality || "unknown"}</strong>
            </Alert>
          </Grid>

          <Grid item xs={12} sm={6} md={3} {...({} as any)}>
            <MetricCard
              label="Flagged Fraction"
              value={qa.flags_total}
              unit="%"
              goodThreshold={0.9}
              warningThreshold={0.7}
            />
          </Grid>

          {qa.k_metrics && (
            <>
              <Grid item xs={12} sm={6} md={3} {...({} as any)}>
                <MetricCard
                  label="K-Cal SNR"
                  value={qa.k_metrics.avg_snr}
                  goodThreshold={10}
                  warningThreshold={5}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3} {...({} as any)}>
                <MetricCard
                  label="K-Cal Flagged"
                  value={qa.k_metrics.flag_fraction}
                  unit="%"
                  goodThreshold={0.9}
                  warningThreshold={0.7}
                />
              </Grid>
            </>
          )}

          {qa.bp_metrics && (
            <>
              <Grid item xs={12} sm={6} md={3} {...({} as any)}>
                <MetricCard
                  label="BP Amplitude Mean"
                  value={qa.bp_metrics.amp_mean}
                  goodThreshold={0.9}
                  warningThreshold={0.7}
                />
              </Grid>
              <Grid item xs={12} sm={6} md={3} {...({} as any)}>
                <MetricCard
                  label="BP Amplitude Std"
                  value={qa.bp_metrics.amp_std}
                  goodThreshold={0.1}
                  warningThreshold={0.2}
                />
              </Grid>
            </>
          )}
        </Grid>
      )}

      {tabValue === 1 && qa.k_metrics && (
        <Box>
          <Typography variant="subtitle1" gutterBottom>
            K-Calibration Metrics
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} {...({} as any)}>
              <MetricCard
                label="Average SNR"
                value={qa.k_metrics.avg_snr}
                goodThreshold={10}
                warningThreshold={5}
              />
            </Grid>
            <Grid item xs={12} sm={6} {...({} as any)}>
              <MetricCard
                label="Flagged Fraction"
                value={qa.k_metrics.flag_fraction}
                unit="%"
                goodThreshold={0.9}
                warningThreshold={0.7}
              />
            </Grid>
          </Grid>
        </Box>
      )}

      {tabValue === 2 && qa.bp_metrics && (
        <Box>
          <Typography variant="subtitle1" gutterBottom>
            Bandpass Calibration Metrics
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} {...({} as any)}>
              <MetricCard
                label="Amplitude Mean"
                value={qa.bp_metrics.amp_mean}
                goodThreshold={0.9}
                warningThreshold={0.7}
              />
            </Grid>
            <Grid item xs={12} sm={6} {...({} as any)}>
              <MetricCard
                label="Amplitude Std Dev"
                value={qa.bp_metrics.amp_std}
                goodThreshold={0.1}
                warningThreshold={0.2}
              />
            </Grid>
            <Grid item xs={12} sm={6} {...({} as any)}>
              <MetricCard
                label="Flagged Fraction"
                value={qa.bp_metrics.flag_fraction}
                unit="%"
                goodThreshold={0.9}
                warningThreshold={0.7}
              />
            </Grid>
          </Grid>

          {qa.per_spw_stats && qa.per_spw_stats.length > 0 && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Per-SPW Statistics
              </Typography>
              <Box sx={{ maxHeight: "300px", overflow: "auto" }}>
                {qa.per_spw_stats.map((spw, idx) => (
                  <Box
                    key={idx}
                    sx={{
                      p: 1,
                      borderBottom: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Typography variant="caption">
                      SPW {spw.spw_id}: Flagged{" "}
                      {(
                        (((spw as any).flagged_count || 0) / ((spw as any).total_count || 1)) *
                        100
                      ).toFixed(1)}
                      %
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          )}
        </Box>
      )}

      {tabValue === 3 && qa.g_metrics && (
        <Box>
          <Typography variant="subtitle1" gutterBottom>
            G-Calibration Metrics
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} {...({} as any)}>
              <MetricCard
                label="Average SNR"
                value={(qa.g_metrics as any).avg_snr}
                goodThreshold={10}
                warningThreshold={5}
              />
            </Grid>
            <Grid item xs={12} sm={6} {...({} as any)}>
              <MetricCard
                label="Flagged Fraction"
                value={qa.g_metrics.flag_fraction}
                unit="%"
                goodThreshold={0.9}
                warningThreshold={0.7}
              />
            </Grid>
          </Grid>
        </Box>
      )}

      {tabValue === 4 && (
        <Box>
          <Typography variant="subtitle1" gutterBottom>
            Bandpass Plots
          </Typography>
          {bandpassPlots && bandpassPlots.plots && bandpassPlots.plots.length > 0 ? (
            <Grid container spacing={2}>
              {bandpassPlots.plots.map((plot, idx) => (
                <Grid item xs={12} sm={6} key={idx} {...({} as any)}>
                  <Box
                    component="img"
                    src={plot.url}
                    alt={plot.filename}
                    sx={{
                      width: "100%",
                      height: "auto",
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 1,
                    }}
                  />
                </Grid>
              ))}
            </Grid>
          ) : (
            <Alert severity="info">No bandpass plots available</Alert>
          )}
        </Box>
      )}
    </Paper>
  );
}
