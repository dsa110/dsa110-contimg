/**
 * Pipeline Stage Performance Metrics Panel
 * Displays stage execution times, success rates, and throughput
 */

import React, { useEffect, useState } from "react";
import { Box, Grid } from "@mui/material";
import { Timer, CheckCircle, TrendingUp } from "@mui/icons-material";
import { TimeSeriesChart, type DataPoint } from "../charts/TimeSeriesChart";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";

interface StageMetrics {
  stage_name: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  avg_duration_seconds: number;
  p95_duration_seconds: number;
  throughput_per_hour: number;
  last_execution: string;
}

export const PipelineStageMetricsPanel: React.FC = () => {
  const [metricsHistory, setMetricsHistory] = useState<DataPoint[]>([]);

  const {
    data: stageMetrics,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["pipeline", "stages", "metrics"],
    queryFn: async () => {
      const response = await apiClient.get<StageMetrics[]>("/pipeline/stages/metrics?limit=100");
      return response.data;
    },
    refetchInterval: 15000,
  });

  useEffect(() => {
    if (stageMetrics && stageMetrics.length > 0) {
      const now = Date.now();
      const totalExecutions = stageMetrics.reduce((sum, s) => sum + s.total_executions, 0);
      const totalSuccess = stageMetrics.reduce((sum, s) => sum + s.successful_executions, 0);
      const avgDuration =
        stageMetrics.reduce((sum, s) => sum + s.avg_duration_seconds, 0) / stageMetrics.length;
      const p95Duration = Math.max(...stageMetrics.map((s) => s.p95_duration_seconds));
      const totalThroughput = stageMetrics.reduce((sum, s) => sum + s.throughput_per_hour, 0);
      const successRate = totalExecutions > 0 ? (totalSuccess / totalExecutions) * 100 : 100;

      const newPoint: DataPoint = {
        timestamp: now,
        formattedTime: new Date(now).toLocaleTimeString(),
        avg_duration: avgDuration,
        p95_duration: p95Duration,
        throughput: totalThroughput,
        success_rate: successRate,
        failed: stageMetrics.reduce((sum, s) => sum + s.failed_executions, 0),
      };

      setMetricsHistory((prev) => [...prev, newPoint].slice(-100));
    }
  }, [stageMetrics]);

  const currentValues =
    stageMetrics && stageMetrics.length > 0
      ? {
          avg_duration:
            stageMetrics.reduce((sum, s) => sum + s.avg_duration_seconds, 0) / stageMetrics.length,
          p95_duration: Math.max(...stageMetrics.map((s) => s.p95_duration_seconds)),
          throughput: stageMetrics.reduce((sum, s) => sum + s.throughput_per_hour, 0),
          success_rate:
            (stageMetrics.reduce((sum, s) => sum + s.successful_executions, 0) /
              stageMetrics.reduce((sum, s) => sum + s.total_executions, 1)) *
            100,
        }
      : {};

  const generateDurationDemo = () => {
    const time = Date.now() / 4000;
    const avgBase = 45 + Math.sin(time) * 15 + Math.random() * 10;
    const p95Base = avgBase * 2.5 + Math.random() * 20;
    return {
      avg_duration: Math.max(0, avgBase),
      p95_duration: Math.max(0, p95Base),
    };
  };

  const generateThroughputDemo = () => {
    const time = Date.now() / 5000;
    const throughputBase = 25 + Math.sin(time) * 10 + Math.random() * 5;
    return {
      throughput: Math.max(0, throughputBase),
    };
  };

  const generateSuccessRateDemo = () => {
    const time = Date.now() / 6000;
    const baseRate = 95 + Math.sin(time) * 3 + Math.random() * 2;
    const failed = Math.random() > 0.95 ? Math.floor(Math.random() * 3) : 0;
    return {
      success_rate: Math.max(85, Math.min(100, baseRate)),
      failed: failed,
    };
  };

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Stage Execution Time"
            icon={<Timer />}
            series={[
              {
                dataKey: "avg_duration",
                name: "Avg Duration",
                color: "#8884d8",
                unit: " s",
                strokeWidth: 2,
              },
              {
                dataKey: "p95_duration",
                name: "P95 Duration",
                color: "#ff9800",
                unit: " s",
                strokeWidth: 1,
                strokeDasharray: "5 5",
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 60, label: "Warning (60s)", color: "#ff9800", type: "warning" },
              { value: 120, label: "Critical (120s)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateDurationDemo}
            currentValues={{
              avg_duration: currentValues.avg_duration,
              p95_duration: currentValues.p95_duration || 0,
            }}
            height={300}
          />
        </Grid>

        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Pipeline Throughput"
            icon={<TrendingUp />}
            series={[
              {
                dataKey: "throughput",
                name: "Observations/Hour",
                color: "#82ca9d",
                unit: "/hr",
                strokeWidth: 2,
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 10, label: "Low (10/hr)", color: "#ff9800", type: "warning" },
              { value: 5, label: "Critical (5/hr)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateThroughputDemo}
            currentValues={{ throughput: currentValues.throughput || 0 }}
            height={300}
          />
        </Grid>

        <Grid size={{ xs: 12 }}>
          <TimeSeriesChart
            title="Success Rate & Failures"
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
                dataKey: "failed",
                name: "Failed Executions",
                color: "#ef5350",
                strokeWidth: 1,
                strokeDasharray: "5 5",
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 95, label: "Warning (95%)", color: "#ff9800", type: "warning" },
              { value: 90, label: "Critical (90%)", color: "#ef5350", type: "critical" },
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
