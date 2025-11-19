/**
 * Calibration Quality Metrics Panel
 * Displays calibration solution quality, convergence, and flagging stats
 */

import React, { useEffect, useState } from "react";
import { Box, Grid } from "@mui/material";
import { Tune, CheckCircle, Flag } from "@mui/icons-material";
import { TimeSeriesChart, type DataPoint } from "../charts/TimeSeriesChart";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";

interface CalibrationQualityMetrics {
  total_calibrations: number;
  successful_calibrations: number;
  avg_solution_quality: number;
  avg_flagged_fraction: number;
  convergence_failures: number;
  recent_cal_time_avg_seconds: number;
  time_series?: Array<{
    timestamp: string;
    solution_quality: number;
    flagged_fraction: number;
    convergence_success: boolean;
  }>;
}

export const CalibrationQualityMetricsPanel: React.FC = () => {
  const [metricsHistory, setMetricsHistory] = useState<DataPoint[]>([]);

  const {
    data: calMetrics,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["monitoring", "calibration-quality", "metrics"],
    queryFn: async () => {
      const response = await apiClient.get<CalibrationQualityMetrics>(
        "/monitoring/calibration-quality/metrics?hours=24"
      );
      return response.data;
    },
    refetchInterval: 30000,
  });

  // Process time series data or collect current metrics
  useEffect(() => {
    if (calMetrics) {
      if (calMetrics.time_series && calMetrics.time_series.length > 0) {
        // Use backend time series if available
        const chartData = calMetrics.time_series.map((point) => ({
          timestamp: new Date(point.timestamp).getTime(),
          formattedTime: new Date(point.timestamp).toLocaleTimeString(),
          solution_quality: point.solution_quality,
          flagged_fraction: point.flagged_fraction * 100,
          convergence_failures: point.convergence_success ? 0 : 1,
        }));
        setMetricsHistory(chartData);
      } else {
        // Collect current metrics as time series
        const now = Date.now();
        const successRate =
          calMetrics.total_calibrations > 0
            ? (calMetrics.successful_calibrations / calMetrics.total_calibrations) * 100
            : 100;

        const newPoint: DataPoint = {
          timestamp: now,
          formattedTime: new Date(now).toLocaleTimeString(),
          solution_quality: calMetrics.avg_solution_quality,
          flagged_fraction: calMetrics.avg_flagged_fraction * 100,
          success_rate: successRate,
          convergence_failures: calMetrics.convergence_failures,
        };
        setMetricsHistory((prev) => [...prev, newPoint].slice(-100));
      }
    }
  }, [calMetrics]);

  const currentValues = calMetrics
    ? {
        solution_quality: calMetrics.avg_solution_quality,
        flagged_fraction: calMetrics.avg_flagged_fraction * 100,
        success_rate:
          calMetrics.total_calibrations > 0
            ? (calMetrics.successful_calibrations / calMetrics.total_calibrations) * 100
            : 100,
      }
    : {};

  // Demo data generators
  const generateSolutionQualityDemo = () => {
    const time = Date.now() / 4000;
    const qualityBase = 0.85 + Math.sin(time) * 0.1 + Math.random() * 0.05;
    return {
      solution_quality: Math.max(0.6, Math.min(1.0, qualityBase)),
    };
  };

  const generateFlaggingDemo = () => {
    const time = Date.now() / 5000;
    const flaggedBase = 15 + Math.sin(time) * 8 + Math.random() * 3;
    return {
      flagged_fraction: Math.max(0, Math.min(50, flaggedBase)),
    };
  };

  const generateSuccessRateDemo = () => {
    const time = Date.now() / 6000;
    const rateBase = 92 + Math.sin(time) * 5 + Math.random() * 3;
    const failures = Math.random() > 0.95 ? 1 : 0;
    return {
      success_rate: Math.max(80, Math.min(100, rateBase)),
      convergence_failures: failures,
    };
  };

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Solution Quality Chart */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Solution Quality"
            icon={<Tune />}
            series={[
              {
                dataKey: "solution_quality",
                name: "Solution Quality",
                color: "#8884d8",
                strokeWidth: 2,
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 0.8, label: "Warning (0.8)", color: "#ff9800", type: "warning" },
              { value: 0.6, label: "Critical (0.6)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateSolutionQualityDemo}
            currentValues={{ solution_quality: currentValues.solution_quality || 0 }}
            height={300}
          />
        </Grid>

        {/* Flagging Statistics Chart */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Data Flagging Rate"
            icon={<Flag />}
            series={[
              {
                dataKey: "flagged_fraction",
                name: "Flagged Data",
                color: "#ff9800",
                unit: "%",
                strokeWidth: 2,
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 30, label: "Warning (30%)", color: "#ff9800", type: "warning" },
              { value: 50, label: "Critical (50%)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateFlaggingDemo}
            currentValues={{ flagged_fraction: currentValues.flagged_fraction || 0 }}
            height={300}
          />
        </Grid>

        {/* Calibration Success Rate Chart */}
        <Grid size={12}>
          <TimeSeriesChart
            title="Calibration Success Rate"
            icon={<CheckCircle />}
            series={[
              {
                dataKey: "success_rate",
                name: "Success Rate",
                color: "#4caf50",
                unit: "%",
                strokeWidth: 2,
              },
              {
                dataKey: "convergence_failures",
                name: "Failures",
                color: "#ef5350",
                strokeWidth: 1,
                strokeDasharray: "5 5",
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 90, label: "Warning (90%)", color: "#ff9800", type: "warning" },
              { value: 80, label: "Critical (80%)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateSuccessRateDemo}
            currentValues={{ success_rate: currentValues.success_rate || 0 }}
            height={300}
          />
        </Grid>
      </Grid>
    </Box>
  );
};
