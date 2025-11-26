/**
 * MetricsTimeSeriesChart - Time-series visualization for ABSURD metrics.
 *
 * Features:
 * - Historical throughput, success rate, and latency charts
 * - Configurable time range and resolution
 * - Real-time updates
 * - Interactive tooltips and legends
 * - Responsive design
 */

import React, { useMemo, useState } from "react";
import {
  Box,
  Paper,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  useTheme,
  alpha,
  Skeleton,
  Chip,
  Stack,
} from "@mui/material";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  ComposedChart,
  Bar,
} from "recharts";
import { format, parseISO } from "date-fns";
import { useMetricsHistory } from "../../api/absurdQueries";
import type { MetricsHistory } from "../../api/absurd";

interface MetricsTimeSeriesChartProps {
  queueName?: string;
}

// Time range options
const TIME_RANGES = [
  { label: "1h", value: 1, resolution: "5m" },
  { label: "6h", value: 6, resolution: "15m" },
  { label: "24h", value: 24, resolution: "1h" },
  { label: "7d", value: 168, resolution: "6h" },
] as const;

// Chart type options
type ChartType = "throughput" | "latency" | "success";

export function MetricsTimeSeriesChart({
  queueName = "dsa110-pipeline",
}: MetricsTimeSeriesChartProps) {
  const theme = useTheme();
  const [timeRange, setTimeRange] = useState<(typeof TIME_RANGES)[number]>(TIME_RANGES[2]); // Default 24h
  const [chartType, setChartType] = useState<ChartType>("throughput");

  const { data, isLoading, error } = useMetricsHistory(
    queueName,
    timeRange.value,
    timeRange.resolution
  );

  // Transform data for recharts
  const chartData = useMemo(() => {
    if (!data?.timestamps) return [];

    return data.timestamps.map((timestamp, index) => ({
      time: timestamp,
      timestamp: parseISO(timestamp),
      throughput: data.series.throughput[index] || 0,
      successRate: data.series.success_rate[index] || 0,
      avgLatency: data.series.avg_latency[index] || 0,
      p95Latency: data.series.p95_latency[index] || 0,
    }));
  }, [data]);

  // Format timestamp for display
  const formatTime = (timestamp: string) => {
    try {
      const date = parseISO(timestamp);
      if (timeRange.value <= 6) {
        return format(date, "HH:mm");
      } else if (timeRange.value <= 24) {
        return format(date, "HH:mm");
      } else {
        return format(date, "MM/dd HH:mm");
      }
    } catch {
      return timestamp;
    }
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;

    return (
      <Paper
        sx={{
          p: 1.5,
          bgcolor: alpha(theme.palette.background.paper, 0.95),
          border: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
          {formatTime(label)}
        </Typography>
        {payload.map((entry: any, index: number) => (
          <Box key={index} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                bgcolor: entry.color,
              }}
            />
            <Typography variant="body2">
              {entry.name}: {entry.value?.toFixed(2)}
              {entry.dataKey.includes("Rate") ? "%" : entry.dataKey.includes("Latency") ? "s" : ""}
            </Typography>
          </Box>
        ))}
      </Paper>
    );
  };

  // Render loading skeleton
  if (isLoading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Skeleton variant="text" width={200} height={32} sx={{ mb: 2 }} />
        <Skeleton variant="rectangular" height={300} />
      </Paper>
    );
  }

  // Render error state
  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography color="error">Failed to load metrics history</Typography>
      </Paper>
    );
  }

  // Render throughput chart
  const renderThroughputChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="throughputGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.3} />
            <stop offset="95%" stopColor={theme.palette.primary.main} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
        <XAxis
          dataKey="time"
          tickFormatter={formatTime}
          tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
          stroke={theme.palette.divider}
        />
        <YAxis
          tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
          stroke={theme.palette.divider}
          label={{
            value: "Tasks/period",
            angle: -90,
            position: "insideLeft",
            fill: theme.palette.text.secondary,
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Area
          type="monotone"
          dataKey="throughput"
          name="Throughput"
          stroke={theme.palette.primary.main}
          fill="url(#throughputGradient)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );

  // Render latency chart
  const renderLatencyChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
        <XAxis
          dataKey="time"
          tickFormatter={formatTime}
          tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
          stroke={theme.palette.divider}
        />
        <YAxis
          tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
          stroke={theme.palette.divider}
          label={{
            value: "Seconds",
            angle: -90,
            position: "insideLeft",
            fill: theme.palette.text.secondary,
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Bar
          dataKey="avgLatency"
          name="Avg Latency"
          fill={alpha(theme.palette.info.main, 0.6)}
          barSize={20}
        />
        <Line
          type="monotone"
          dataKey="p95Latency"
          name="P95 Latency"
          stroke={theme.palette.warning.main}
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );

  // Render success rate chart
  const renderSuccessChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
        <XAxis
          dataKey="time"
          tickFormatter={formatTime}
          tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
          stroke={theme.palette.divider}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
          stroke={theme.palette.divider}
          label={{
            value: "Success %",
            angle: -90,
            position: "insideLeft",
            fill: theme.palette.text.secondary,
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Line
          type="monotone"
          dataKey="successRate"
          name="Success Rate"
          stroke={theme.palette.success.main}
          strokeWidth={2}
          dot={false}
        />
        {/* Reference line at 95% */}
        <Line
          type="monotone"
          dataKey={() => 95}
          name="SLA Target (95%)"
          stroke={alpha(theme.palette.warning.main, 0.5)}
          strokeDasharray="5 5"
          strokeWidth={1}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
          flexWrap: "wrap",
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Historical Metrics
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {data?.timestamps?.length || 0} data points over {timeRange.label}
          </Typography>
        </Box>

        <Stack direction="row" spacing={2}>
          {/* Chart Type Selector */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Metric</InputLabel>
            <Select
              value={chartType}
              label="Metric"
              onChange={(e) => setChartType(e.target.value as ChartType)}
            >
              <MenuItem value="throughput">Throughput</MenuItem>
              <MenuItem value="latency">Latency</MenuItem>
              <MenuItem value="success">Success Rate</MenuItem>
            </Select>
          </FormControl>

          {/* Time Range Selector */}
          <ToggleButtonGroup
            value={timeRange.label}
            exclusive
            onChange={(_, value) => {
              const newRange = TIME_RANGES.find((r) => r.label === value);
              if (newRange) setTimeRange(newRange);
            }}
            size="small"
          >
            {TIME_RANGES.map((range) => (
              <ToggleButton key={range.label} value={range.label}>
                {range.label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Stack>
      </Box>

      {/* Summary Stats */}
      {chartData.length > 0 && (
        <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
          <Chip
            label={`Avg Throughput: ${(
              chartData.reduce((sum, d) => sum + d.throughput, 0) / chartData.length
            ).toFixed(1)}`}
            size="small"
            color="primary"
            variant="outlined"
          />
          <Chip
            label={`Avg Success: ${(
              chartData.reduce((sum, d) => sum + d.successRate, 0) / chartData.length
            ).toFixed(1)}%`}
            size="small"
            color="success"
            variant="outlined"
          />
          <Chip
            label={`Avg Latency: ${(
              chartData.reduce((sum, d) => sum + d.avgLatency, 0) / chartData.length
            ).toFixed(2)}s`}
            size="small"
            color="info"
            variant="outlined"
          />
        </Box>
      )}

      {/* Chart */}
      {chartData.length === 0 ? (
        <Box
          sx={{
            height: 300,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography color="text.secondary">No data available for selected time range</Typography>
        </Box>
      ) : (
        <>
          {chartType === "throughput" && renderThroughputChart()}
          {chartType === "latency" && renderLatencyChart()}
          {chartType === "success" && renderSuccessChart()}
        </>
      )}

      {/* Queue Info */}
      <Box sx={{ mt: 2, display: "flex", justifyContent: "flex-end" }}>
        <Typography variant="caption" color="text.secondary">
          Queue: {queueName} • Resolution: {timeRange.resolution}
        </Typography>
      </Box>
    </Paper>
  );
}

export default MetricsTimeSeriesChart;
