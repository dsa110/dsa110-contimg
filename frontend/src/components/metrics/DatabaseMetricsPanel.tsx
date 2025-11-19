/**
 * Database Performance Metrics Panel
 * Displays query performance, connection pool, and database growth
 */

import React, { useEffect, useState } from "react";
import { Box, Grid } from "@mui/material";
import { Storage, Speed, TrendingUp } from "@mui/icons-material";
import { TimeSeriesChart, type DataPoint } from "../charts/TimeSeriesChart";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";

interface DatabaseMetrics {
  query_count: number;
  avg_query_time_ms: number;
  slow_queries: number;
  connection_pool_size: number;
  active_connections: number;
  database_size_mb: number;
  largest_table: string;
  largest_table_size_mb: number;
}

export const DatabaseMetricsPanel: React.FC = () => {
  const [metricsHistory, setMetricsHistory] = useState<DataPoint[]>([]);

  const {
    data: metrics,
    error,
    isLoading,
  } = useQuery({
    queryKey: ["metrics", "database"],
    queryFn: async () => {
      const response = await apiClient.get<DatabaseMetrics>("/metrics/database");
      return response.data;
    },
    refetchInterval: 10000,
  });

  useEffect(() => {
    if (metrics) {
      const now = Date.now();
      const newPoint: DataPoint = {
        timestamp: now,
        formattedTime: new Date(now).toLocaleTimeString(),
        avg_query_time: metrics.avg_query_time_ms,
        slow_queries: metrics.slow_queries,
        active_connections: metrics.active_connections,
        pool_utilization: (metrics.active_connections / metrics.connection_pool_size) * 100,
        db_size: metrics.database_size_mb,
      };
      setMetricsHistory((prev) => [...prev, newPoint].slice(-100));
    }
  }, [metrics]);

  const currentValues = metrics
    ? {
        avg_query_time: metrics.avg_query_time_ms,
        slow_queries: metrics.slow_queries,
        active_connections: metrics.active_connections,
        pool_utilization: (metrics.active_connections / metrics.connection_pool_size) * 100,
        db_size: metrics.database_size_mb,
      }
    : {};

  const generateQueryPerformanceDemo = () => {
    const time = Date.now() / 4000;
    const avgTime = 15 + Math.sin(time) * 10 + Math.random() * 5;
    const spike = Math.random() > 0.98 ? 30 : 0;
    return {
      avg_query_time: Math.max(0, avgTime + spike),
      slow_queries: Math.random() > 0.9 ? Math.floor(Math.random() * 5) : 0,
    };
  };

  const generateConnectionDemo = () => {
    const time = Date.now() / 5000;
    const baseConnections = 8 + Math.sin(time) * 4 + Math.random() * 2;
    const connections = Math.max(0, Math.round(baseConnections));
    return {
      active_connections: connections,
      pool_utilization: (connections / 20) * 100,
    };
  };

  const generateDbSizeDemo = () => {
    const baseSize = 1500 + (Date.now() / 100000000) * 10;
    return {
      db_size: baseSize + Math.random() * 5,
    };
  };

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Query Performance"
            icon={<Speed />}
            series={[
              {
                dataKey: "avg_query_time",
                name: "Avg Query Time",
                color: "#8884d8",
                unit: " ms",
                strokeWidth: 2,
              },
              {
                dataKey: "slow_queries",
                name: "Slow Queries",
                color: "#ef5350",
                strokeWidth: 1,
                strokeDasharray: "5 5",
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 50, label: "Warning (50ms)", color: "#ff9800", type: "warning" },
              { value: 100, label: "Critical (100ms)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateQueryPerformanceDemo}
            currentValues={{ avg_query_time: currentValues.avg_query_time || 0 }}
            height={300}
          />
        </Grid>

        <Grid size={{ xs: 12, lg: 6 }}>
          <TimeSeriesChart
            title="Connection Pool Usage"
            icon={<TrendingUp />}
            series={[
              {
                dataKey: "active_connections",
                name: "Active Connections",
                color: "#8884d8",
                strokeWidth: 2,
              },
              {
                dataKey: "pool_utilization",
                name: "Pool Utilization",
                color: "#82ca9d",
                unit: "%",
                strokeWidth: 1,
                strokeDasharray: "5 5",
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 15, label: "Warning (15)", color: "#ff9800", type: "warning" },
              { value: 18, label: "Critical (18)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateConnectionDemo}
            currentValues={{ active_connections: currentValues.active_connections || 0 }}
            height={300}
          />
        </Grid>

        <Grid size={{ xs: 12 }}>
          <TimeSeriesChart
            title="Database Size Growth"
            icon={<Storage />}
            series={[
              {
                dataKey: "db_size",
                name: "Database Size",
                color: "#8884d8",
                unit: " MB",
                strokeWidth: 2,
              },
            ]}
            data={metricsHistory}
            loading={isLoading}
            error={error as Error}
            thresholds={[
              { value: 5000, label: "Warning (5 GB)", color: "#ff9800", type: "warning" },
              { value: 10000, label: "Critical (10 GB)", color: "#ef5350", type: "critical" },
            ]}
            enableDemoMode={true}
            demoDataGenerator={generateDbSizeDemo}
            currentValues={{ db_size: currentValues.db_size || 0 }}
            height={300}
          />
        </Grid>
      </Grid>
    </Box>
  );
};
