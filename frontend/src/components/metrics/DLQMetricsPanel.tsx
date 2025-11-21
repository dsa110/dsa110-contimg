/**
 * Dead Letter Queue (DLQ) Metrics Panel
 * Displays DLQ depth, error rates, and retry statistics
 */

import React, { useEffect, useState } from "react";
import { Box } from "@mui/material";
import Grid from "@mui/material/Grid";
import { Error as ErrorIcon, TrendingUp } from "@mui/icons-material";
import { TimeSeriesChart, type DataPoint } from "../charts/TimeSeriesChart";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";

interface DLQStats {
  total_failures: number;
  pending_retries: number;
  retries_exhausted: number;
  recent_error_rate_per_hour: number;
  oldest_failure_age_hours?: number;
}

export const DLQMetricsPanel: React.FC = () => {
  const [metricsHistory, setMetricsHistory] = useState<DataPoint[]>([]);

  const {
    data: dlqStats,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["dlq", "stats"],
    queryFn: async () => {
      const response = await apiClient.get<DLQStats>("/operations/dlq/stats");
      return response.data;
    },
    refetchInterval: 10000,
  });

  // Collect metrics history
  useEffect(() => {
    if (dlqStats) {
      const now = Date.now();

      const newPoint: DataPoint = {
        timestamp: now,
        formattedTime: new Date(now).toLocaleTimeString(),
        total_failures: dlqStats.total_failures,
        pending_retries: dlqStats.pending_retries,
        exhausted: dlqStats.retries_exhausted,
        error_rate: dlqStats.recent_error_rate_per_hour,
      };

      setMetricsHistory((prev) => [...prev, newPoint].slice(-100));
    }
  }, [dlqStats]);

  const currentValues = dlqStats
    ? {
        total_failures: dlqStats.total_failures,
        pending_retries: dlqStats.pending_retries,
        exhausted: dlqStats.retries_exhausted,
        error_rate: dlqStats.recent_error_rate_per_hour,
      }
    : {};

  // Demo data generators
  const generateDLQDepthDemo = () => {
    const time = Date.now() / 8000;
    const totalBase = 20 + Math.sin(time) * 15 + Math.random() * 5;
    const total = Math.max(0, Math.round(totalBase));
    const pending = Math.round(total * 0.6);
    const exhausted = total - pending;
    return {
      total_failures: total,
      pending_retries: pending,
      exhausted: exhausted,
    };
  };

  const generateErrorRateDemo = () => {
    const time = Date.now() / 6000;
    const rateBase = 3 + Math.sin(time) * 2 + Math.random() * 1;
    const spike = Math.random() > 0.95 ? 5 : 0;
    return {
      error_rate: Math.max(0, rateBase + spike),
    };
  };

  return (
    <Box>
      <Grid container spacing={3}>
        {/* DLQ Depth Chart */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Dead Letter Queue Depth"
            icon={<ErrorIcon />}
            series={[
              {
                dataKey: "total_failures",
                name: "Total Failures",
                color: "#ef5350",
                strokeWidth: 2,
              },
              {
                dataKey: "pending_retries",
                name: "Pending Retries",
                color: "#ff9800",
                strokeWidth: 2,
              },
              {
                dataKey: "exhausted",
                name: "Retries Exhausted",
                color: "#f44336",
                strokeWidth: 1,
                strokeDasharray: "5 5",
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 20, label: "Warning (20)", color: "#ff9800", type: "warning" },
              { value: 50, label: "Critical (50)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateDLQDepthDemo}
            currentValues={{
              total_failures: currentValues.total_failures,
              pending_retries: currentValues.pending_retries,
            }}
            height={300}
          />
        </Grid>

        {/* Error Rate Chart */}
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Error Rate"
            icon={<TrendingUp />}
            series={[
              {
                dataKey: "error_rate",
                name: "Errors/Hour",
                color: "#ef5350",
                unit: "/hr",
                strokeWidth: 2,
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 5, label: "Warning (5/hr)", color: "#ff9800", type: "warning" },
              { value: 10, label: "Critical (10/hr)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateErrorRateDemo}
            currentValues={{ error_rate: currentValues.error_rate || 0 }}
            height={300}
          />
        </Grid>
      </Grid>
    </Box>
  );
};
