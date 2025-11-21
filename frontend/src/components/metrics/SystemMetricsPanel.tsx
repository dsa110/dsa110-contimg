/**
 * System Metrics Monitoring Panel
 * Displays CPU, Memory, Disk, and Load metrics in Grafana-style time-series charts
 */

import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";
import Grid from "@mui/material/Grid";
import { Storage, Speed, TrendingUp } from "@mui/icons-material";
import { TimeSeriesChart, type DataPoint } from "../charts/TimeSeriesChart";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";

interface SystemMetrics {
  timestamp: number;
  cpu_percent: number;
  mem_percent: number;
  load_1: number;
  load_5: number;
  load_15: number;
  disk_usage: Array<{
    mount: string;
    total: number;
    used: number;
    free: number;
    percent: number;
  }>;
}

export const SystemMetricsPanel: React.FC = () => {
  const [metricsHistory, setMetricsHistory] = useState<DataPoint[]>([]);

  const {
    data: historyData,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["metrics", "system", "history"],
    queryFn: async () => {
      const response = await apiClient.get<SystemMetrics[]>("/metrics/system/history?limit=100");
      return response.data;
    },
    refetchInterval: 15000,
  });

  const { data: currentMetrics } = useQuery({
    queryKey: ["metrics", "system"],
    queryFn: async () => {
      const response = await apiClient.get<SystemMetrics>("/metrics/system");
      return response.data;
    },
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (historyData && historyData.length > 0) {
      const chartData: DataPoint[] = historyData.map((metric: SystemMetrics) => {
        const stageDisk = metric.disk_usage?.find((d: { mount: string }) => d.mount === "/stage");
        const dataDisk = metric.disk_usage?.find((d: { mount: string }) => d.mount === "/data");

        return {
          timestamp: metric.timestamp,
          formattedTime: new Date(metric.timestamp).toLocaleTimeString(),
          cpu: metric.cpu_percent,
          memory: metric.mem_percent,
          load1: metric.load_1,
          load5: metric.load_5,
          load15: metric.load_15,
          disk_stage: stageDisk?.percent || 0,
          disk_data: dataDisk?.percent || 0,
        };
      });
      setMetricsHistory(chartData);
    }
  }, [historyData]);

  const currentValues = currentMetrics
    ? {
        cpu: currentMetrics.cpu_percent,
        memory: currentMetrics.mem_percent,
        load1: currentMetrics.load_1,
        disk_stage:
          currentMetrics.disk_usage?.find((d: { mount: string }) => d.mount === "/stage")
            ?.percent || 0,
        disk_data:
          currentMetrics.disk_usage?.find((d: { mount: string }) => d.mount === "/data")?.percent ||
          0,
      }
    : {};

  const generateCpuMemoryDemo = () => {
    const time = Date.now() / 3000;
    const cpuBase = 45 + Math.sin(time) * 20 + Math.random() * 10;
    const memBase = 60 + Math.sin(time * 0.7) * 15 + Math.random() * 5;
    return {
      cpu: Math.max(0, Math.min(100, cpuBase)),
      memory: Math.max(0, Math.min(100, memBase)),
    };
  };

  const generateLoadDemo = () => {
    const time = Date.now() / 5000;
    const loadBase = 2.5 + Math.sin(time) * 1.5 + Math.random() * 0.5;
    return {
      load1: Math.max(0, loadBase),
      load5: Math.max(0, loadBase * 0.9),
      load15: Math.max(0, loadBase * 0.8),
    };
  };

  const generateDiskDemo = () => {
    const time = Date.now() / 10000;
    return {
      disk_stage: Math.max(20, Math.min(90, 55 + Math.sin(time) * 10 + Math.random() * 3)),
      disk_data: Math.max(30, Math.min(95, 65 + Math.sin(time * 1.2) * 8 + Math.random() * 2)),
    };
  };

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="CPU & Memory Usage"
            icon={<Speed />}
            series={[
              { dataKey: "cpu", name: "CPU", color: "#8884d8", unit: "%", strokeWidth: 2 },
              { dataKey: "memory", name: "Memory", color: "#82ca9d", unit: "%", strokeWidth: 2 },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 70, label: "Warning (70%)", color: "#ff9800", type: "warning" },
              { value: 85, label: "Critical (85%)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateCpuMemoryDemo}
            currentValues={{ cpu: currentValues.cpu || 0, memory: currentValues.memory || 0 }}
            height={300}
          />
        </Grid>

        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="System Load Average"
            icon={<TrendingUp />}
            series={[
              { dataKey: "load1", name: "1 min", color: "#8884d8", strokeWidth: 2 },
              {
                dataKey: "load5",
                name: "5 min",
                color: "#82ca9d",
                strokeWidth: 1,
                strokeDasharray: "5 5",
              },
              {
                dataKey: "load15",
                name: "15 min",
                color: "#ffc658",
                strokeWidth: 1,
                strokeDasharray: "5 5",
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 4, label: "Warning (4.0)", color: "#ff9800", type: "warning" },
              { value: 8, label: "Critical (8.0)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateLoadDemo}
            currentValues={{ load1: currentValues.load1 || 0 }}
            height={300}
          />
        </Grid>

        <Grid size={{ xs: 12 }}>
          <TimeSeriesChart
            title="Disk Usage"
            icon={<Storage />}
            series={[
              {
                dataKey: "disk_stage",
                name: "/stage (SSD)",
                color: "#8884d8",
                unit: "%",
                strokeWidth: 2,
              },
              {
                dataKey: "disk_data",
                name: "/data (HDD)",
                color: "#82ca9d",
                unit: "%",
                strokeWidth: 2,
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 80, label: "Warning (80%)", color: "#ff9800", type: "warning" },
              { value: 90, label: "Critical (90%)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateDiskDemo}
            currentValues={{
              disk_stage: currentValues.disk_stage || 0,
              disk_data: currentValues.disk_data || 0,
            }}
            height={300}
          />
        </Grid>
      </Grid>
    </Box>
  );
};
