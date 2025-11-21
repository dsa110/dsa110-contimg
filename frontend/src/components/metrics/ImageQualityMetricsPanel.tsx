/**
 * Image Quality Metrics Panel
 * Displays mosaic quality metrics: RMS noise, dynamic range, artifacts
 */

import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";
import Grid from "@mui/material/Grid";
import { Image, Insights, Warning } from "@mui/icons-material";
import { TimeSeriesChart, type DataPoint } from "../charts/TimeSeriesChart";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";

interface ImageQualityMetrics {
  total_mosaics: number;
  avg_rms_noise_mjy: number;
  avg_dynamic_range: number;
  artifacts_detected: number;
  flagged_antennas_avg: number;
  recent_failures: number;
  time_series?: Array<{
    timestamp: string;
    rms_noise: number;
    dynamic_range: number;
    artifacts: number;
  }>;
}

export const ImageQualityMetricsPanel: React.FC = () => {
  const [metricsHistory, setMetricsHistory] = useState<DataPoint[]>([]);

  const {
    data: qualityMetrics,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["monitoring", "mosaic-quality", "metrics"],
    queryFn: async () => {
      const response = await apiClient.get<ImageQualityMetrics>(
        "/monitoring/mosaic-quality/metrics?hours=24"
      );
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Process time series data or collect current metrics
  useEffect(() => {
    if (qualityMetrics) {
      if (qualityMetrics.time_series && qualityMetrics.time_series.length > 0) {
        // Use backend time series if available
        const chartData = qualityMetrics.time_series.map((point) => ({
          timestamp: new Date(point.timestamp).getTime(),
          formattedTime: new Date(point.timestamp).toLocaleTimeString(),
          rms_noise: point.rms_noise,
          dynamic_range: point.dynamic_range,
          artifacts: point.artifacts,
        }));
        setMetricsHistory(chartData);
      } else {
        // Collect current metrics as time series
        const now = Date.now();
        const newPoint: DataPoint = {
          timestamp: now,
          formattedTime: new Date(now).toLocaleTimeString(),
          rms_noise: qualityMetrics.avg_rms_noise_mjy,
          dynamic_range: qualityMetrics.avg_dynamic_range,
          artifacts: qualityMetrics.artifacts_detected,
        };
        setMetricsHistory((prev) => [...prev, newPoint].slice(-100));
      }
    }
  }, [qualityMetrics]);

  const currentValues = qualityMetrics
    ? {
        rms_noise: qualityMetrics.avg_rms_noise_mjy,
        dynamic_range: qualityMetrics.avg_dynamic_range,
        artifacts: qualityMetrics.artifacts_detected,
      }
    : {};

  // Demo data generators
  const generateRMSNoiseDemo = () => {
    const time = Date.now() / 4000;
    const noiseBase = 0.8 + Math.sin(time) * 0.2 + Math.random() * 0.1;
    return {
      rms_noise: Math.max(0.3, noiseBase),
    };
  };

  const generateDynamicRangeDemo = () => {
    const time = Date.now() / 5000;
    const rangeBase = 45 + Math.sin(time) * 10 + Math.random() * 3;
    return {
      dynamic_range: Math.max(20, rangeBase),
    };
  };

  const generateArtifactsDemo = () => {
    const spike = Math.random() > 0.95 ? Math.floor(Math.random() * 5) : 0;
    return {
      artifacts: Math.random() > 0.8 ? 1 + spike : spike,
    };
  };

  return (
    <Box>
      <Grid container spacing={3}>
        {/* RMS Noise Chart */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="RMS Noise Level"
            icon={<Image />}
            series={[
              {
                dataKey: "rms_noise",
                name: "RMS Noise",
                color: "#8884d8",
                unit: " mJy",
                strokeWidth: 2,
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 1.0, label: "Warning (1.0 mJy)", color: "#ff9800", type: "warning" },
              { value: 1.5, label: "Critical (1.5 mJy)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateRMSNoiseDemo}
            currentValues={{ rms_noise: currentValues.rms_noise || 0 }}
            height={300}
          />
        </Grid>

        {/* Dynamic Range Chart */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Dynamic Range"
            icon={<Insights />}
            series={[
              { dataKey: "dynamic_range", name: "Dynamic Range", color: "#82ca9d", strokeWidth: 2 },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 30, label: "Low (30)", color: "#ff9800", type: "warning" },
              { value: 20, label: "Critical (20)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateDynamicRangeDemo}
            currentValues={{ dynamic_range: currentValues.dynamic_range || 0 }}
            height={300}
          />
        </Grid>

        {/* Artifacts Detection Chart */}
        <Grid size={{ xs: 12 }}>
          <TimeSeriesChart
            title="Artifacts Detected"
            icon={<Warning />}
            series={[{ dataKey: "artifacts", name: "Artifacts", color: "#ef5350", strokeWidth: 2 }]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 3, label: "Warning (3)", color: "#ff9800", type: "warning" },
              { value: 5, label: "Critical (5)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateArtifactsDemo}
            currentValues={{ artifacts: currentValues.artifacts || 0 }}
            height={300}
          />
        </Grid>
      </Grid>
    </Box>
  );
};
