/**
 * Streaming Service Metrics Panel
 * Displays processing rate, queue stats, and resource usage
 */

import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";
import Grid from "@mui/material/Grid";
import { Speed, Memory, TrendingUp } from "@mui/icons-material";
import { TimeSeriesChart, type DataPoint } from "../charts/TimeSeriesChart";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";

interface StreamingMetrics {
  service_running: boolean;
  uptime_seconds?: number;
  cpu_percent?: number;
  memory_mb?: number;
  queue_stats?: Record<string, number>;
  processing_rate_per_hour?: number;
  queue_error?: string;
}

export const StreamingMetricsPanel: React.FC = () => {
  const [metricsHistory, setMetricsHistory] = useState<DataPoint[]>([]);

  const {
    data: metrics,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["streaming", "metrics"],
    queryFn: async () => {
      const response = await apiClient.get<StreamingMetrics>("/streaming/metrics");
      return response.data;
    },
    refetchInterval: 5000,
  });

  // Collect metrics history
  useEffect(() => {
    if (metrics && metrics.service_running) {
      const now = Date.now();
      const queueDepth = metrics.queue_stats
        ? Object.values(metrics.queue_stats).reduce((a, b) => a + b, 0)
        : 0;

      const newPoint: DataPoint = {
        timestamp: now,
        formattedTime: new Date(now).toLocaleTimeString(),
        processing_rate: metrics.processing_rate_per_hour || 0,
        queue_depth: queueDepth,
        cpu: metrics.cpu_percent || 0,
        memory: metrics.memory_mb || 0,
      };

      setMetricsHistory((prev) => [...prev, newPoint].slice(-100));
    }
  }, [metrics]);

  const currentValues = metrics
    ? {
        processing_rate: metrics.processing_rate_per_hour || 0,
        queue_depth: metrics.queue_stats
          ? Object.values(metrics.queue_stats).reduce((a, b) => a + b, 0)
          : 0,
        cpu: metrics.cpu_percent || 0,
        memory: metrics.memory_mb || 0,
      }
    : {};

  // Demo data generators
  const generateProcessingRateDemo = () => {
    const time = Date.now() / 4000;
    const rateBase = 150 + Math.sin(time) * 50 + Math.random() * 20;
    return {
      processing_rate: Math.max(0, rateBase),
    };
  };

  const generateQueueDepthDemo = () => {
    const time = Date.now() / 5000;
    const depthBase = 15 + Math.sin(time) * 10 + Math.random() * 5;
    return {
      queue_depth: Math.max(0, Math.round(depthBase)),
    };
  };

  const generateResourceDemo = () => {
    const time = Date.now() / 3000;
    return {
      cpu: Math.max(0, Math.min(100, 25 + Math.sin(time) * 15 + Math.random() * 5)),
      memory: Math.max(100, 800 + Math.sin(time * 0.8) * 200 + Math.random() * 50),
    };
  };

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Processing Rate Chart */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Processing Rate"
            icon={<Speed />}
            series={[
              {
                dataKey: "processing_rate",
                name: "Files/Hour",
                color: "#8884d8",
                unit: "/hr",
                strokeWidth: 2,
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 50, label: "Low (50/hr)", color: "#ff9800", type: "warning" },
              { value: 10, label: "Critical (10/hr)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateProcessingRateDemo}
            currentValues={{ processing_rate: currentValues.processing_rate || 0 }}
            height={300}
          />
        </Grid>

        {/* Queue Depth Chart */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Queue Depth"
            icon={<TrendingUp />}
            series={[
              { dataKey: "queue_depth", name: "Pending Files", color: "#82ca9d", strokeWidth: 2 },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 30, label: "Warning (30)", color: "#ff9800", type: "warning" },
              { value: 50, label: "Critical (50)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateQueueDepthDemo}
            currentValues={{ queue_depth: currentValues.queue_depth || 0 }}
            height={300}
          />
        </Grid>

        {/* Resource Usage Chart */}
        <Grid size={{ xs: 12 }}>
          <TimeSeriesChart
            title="Service Resource Usage"
            icon={<Memory />}
            series={[
              { dataKey: "cpu", name: "CPU", color: "#8884d8", unit: "%", strokeWidth: 2 },
              { dataKey: "memory", name: "Memory", color: "#82ca9d", unit: " MB", strokeWidth: 2 },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 70, label: "CPU Warning (70%)", color: "#ff9800", type: "warning" },
              { value: 90, label: "CPU Critical (90%)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateResourceDemo}
            currentValues={{ cpu: currentValues.cpu, memory: currentValues.memory || 0 }}
            height={300}
          />
        </Grid>
      </Grid>
    </Box>
  );
};
