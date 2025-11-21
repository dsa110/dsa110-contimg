/**
 * Generic Grafana-style time-series chart component.
 * Supports single or multiple series with configurable thresholds and time ranges.
 */

import React, { useEffect, useState, useRef } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Stack,
  ToggleButtonGroup,
  ToggleButton,
  Switch,
  FormControlLabel,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { TrendingUp, Warning, CheckCircle } from "@mui/icons-material";

export interface DataPoint {
  timestamp: number;
  formattedTime: string;
  [key: string]: number | string;
}

export interface SeriesConfig {
  dataKey: string;
  name: string;
  color: string;
  unit?: string;
  strokeWidth?: number;
  strokeDasharray?: string;
  hide?: boolean;
}

export interface ThresholdConfig {
  value: number;
  label: string;
  color: string;
  type: "warning" | "critical";
}

export interface TimeSeriesChartProps {
  title: string;
  icon?: React.ReactNode;
  series: SeriesConfig[];
  data: DataPoint[];
  loading?: boolean;
  error?: Error | null;
  thresholds?: ThresholdConfig[];
  defaultTimeRange?: TimeRange;
  enableDemoMode?: boolean;
  demoDataGenerator?: () => Partial<Record<string, number>>;
  updateInterval?: number;
  maxDataPoints?: number;
  height?: number;
  currentValues?: Record<string, number>;
}

export type TimeRange = "15m" | "1h" | "6h" | "24h";

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  title,
  icon = <TrendingUp />,
  series,
  data: externalData,
  loading = false,
  error = null,
  thresholds = [],
  defaultTimeRange = "1h",
  enableDemoMode = false,
  demoDataGenerator,
  updateInterval = 15000,
  maxDataPoints = 100,
  height = 300,
  currentValues = {},
}) => {
  const [dataPoints, setDataPoints] = useState<DataPoint[]>(externalData || []);
  const [timeRange, setTimeRange] = useState<TimeRange>(defaultTimeRange);
  const [demoMode, setDemoMode] = useState(false);
  const lastUpdateRef = useRef<number>(0);

  // Sync external data
  useEffect(() => {
    if (!demoMode && externalData && externalData.length > 0) {
      setDataPoints(externalData.slice(-maxDataPoints));
    }
  }, [externalData, demoMode, maxDataPoints]);

  // Clear data when switching modes
  useEffect(() => {
    if (demoMode) {
      setDataPoints([]);
    }
  }, [demoMode]);

  // Demo Mode Data Generation
  useEffect(() => {
    if (!demoMode || !demoDataGenerator) return;

    const interval = setInterval(() => {
      const now = Date.now();
      const timeSinceLastUpdate = now - lastUpdateRef.current;

      if (timeSinceLastUpdate < 1000) return;
      lastUpdateRef.current = now;

      const generatedData = demoDataGenerator();
      const newPoint: DataPoint = {
        timestamp: now,
        formattedTime: new Date(now).toLocaleTimeString(),
        ...generatedData,
      };

      setDataPoints((prev) => [...prev, newPoint].slice(-maxDataPoints));
    }, 1000);

    return () => clearInterval(interval);
  }, [demoMode, demoDataGenerator, maxDataPoints]);

  // Filter data points based on selected time range
  const getFilteredData = (): DataPoint[] => {
    const now = Date.now();
    const ranges: Record<TimeRange, number> = {
      "15m": 15 * 60 * 1000,
      "1h": 60 * 60 * 1000,
      "6h": 6 * 60 * 60 * 1000,
      "24h": 24 * 60 * 60 * 1000,
    };
    const cutoff = now - ranges[timeRange];
    return dataPoints.filter((point) => point.timestamp >= cutoff);
  };

  const filteredData = getFilteredData();

  // Determine status based on thresholds
  const getStatus = () => {
    if (error && !demoMode) {
      return { color: "error", label: "API ERROR", icon: <Warning /> };
    }
    if (loading && dataPoints.length === 0 && !demoMode) {
      return { color: "default", label: "CONNECTING", icon: <TrendingUp /> };
    }

    const criticalThreshold = thresholds.find((t) => t.type === "critical");
    const warningThreshold = thresholds.find((t) => t.type === "warning");

    const visibleSeries = series.filter((s) => !s.hide);
    for (const s of visibleSeries) {
      const value = currentValues[s.dataKey];
      if (value !== undefined) {
        if (criticalThreshold && value >= criticalThreshold.value) {
          return {
            color: "error",
            label: demoMode ? "DEMO: CRITICAL" : "CRITICAL",
            icon: <Warning />,
          };
        }
        if (warningThreshold && value >= warningThreshold.value) {
          return {
            color: "warning",
            label: demoMode ? "DEMO: WARNING" : "WARNING",
            icon: <Warning />,
          };
        }
      }
    }

    return {
      color: "success",
      label: demoMode ? "DEMO: HEALTHY" : "HEALTHY",
      icon: <CheckCircle />,
    };
  };

  const status = getStatus();
  const errorMessage = error instanceof Error ? error.message : "Unknown error";

  interface TooltipProps {
    active?: boolean;
    payload?: Array<{
      payload: DataPoint;
      dataKey: string;
      value: number;
      color: string;
      name: string;
    }>;
  }

  const CustomTooltip: React.FC<TooltipProps> = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;

    const data = payload[0].payload;
    return (
      <Card
        sx={{
          p: 1.5,
          minWidth: 200,
          bgcolor: "background.paper",
          border: 1,
          borderColor: "divider",
        }}
      >
        <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
          {new Date(data.timestamp).toLocaleString()}
        </Typography>
        <Stack spacing={0.5}>
          {payload.map((entry, index) => {
            const seriesConfig = series.find((s) => s.dataKey === entry.dataKey);
            const unit = seriesConfig?.unit || "";
            return (
              <Typography key={index} variant="body2" sx={{ color: entry.color }}>
                <strong>{entry.name}:</strong> {entry.value.toFixed(2)}
                {unit}
              </Typography>
            );
          })}
        </Stack>
      </Card>
    );
  };

  return (
    <Card
      sx={{
        height: "100%",
        bgcolor: (theme) => alpha(theme.palette.background.paper, 0.8),
        backdropFilter: "blur(10px)",
      }}
    >
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography variant="h6">
              {React.isValidElement(icon) &&
                React.cloneElement(icon as React.ReactElement, {
                  sx: { mr: 1, verticalAlign: "middle" },
                })}
              {title}
            </Typography>
            <Chip
              icon={status.icon}
              label={status.label}
              color={
                status.color as
                  | "default"
                  | "primary"
                  | "secondary"
                  | "error"
                  | "info"
                  | "success"
                  | "warning"
              }
              size="small"
            />
          </Stack>

          <Stack direction="row" spacing={2} alignItems="center">
            {enableDemoMode && demoDataGenerator && (
              <FormControlLabel
                control={
                  <Switch
                    checked={demoMode}
                    onChange={(e) => setDemoMode(e.target.checked)}
                    size="small"
                  />
                }
                label={<Typography variant="caption">Demo Mode</Typography>}
              />
            )}
            <ToggleButtonGroup
              value={timeRange}
              exclusive
              onChange={(_, newRange) => newRange && setTimeRange(newRange)}
              size="small"
            >
              <ToggleButton value="15m">15m</ToggleButton>
              <ToggleButton value="1h">1h</ToggleButton>
              <ToggleButton value="6h">6h</ToggleButton>
              <ToggleButton value="24h">24h</ToggleButton>
            </ToggleButtonGroup>
          </Stack>
        </Stack>

        {Object.keys(currentValues).length > 0 && (
          <Box sx={{ display: "flex", gap: 3, mb: 2, flexWrap: "wrap" }}>
            {series
              .filter((s) => !s.hide && currentValues[s.dataKey] !== undefined)
              .map((s) => (
                <Box key={s.dataKey}>
                  <Typography variant="caption" color="text.secondary">
                    {s.name}
                  </Typography>
                  <Typography variant="h4" sx={{ color: s.color }}>
                    {currentValues[s.dataKey]?.toFixed(1)}
                    {s.unit}
                  </Typography>
                </Box>
              ))}
          </Box>
        )}

        {!demoMode && error ? (
          <Box
            sx={{
              height,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: (theme) => alpha(theme.palette.error.main, 0.1),
              borderRadius: 1,
              p: 3,
            }}
          >
            <Warning color="error" sx={{ fontSize: 48, mb: 2 }} />
            <Typography variant="h6" color="error" gutterBottom>
              Connection Failed
            </Typography>
            <Typography variant="body2" color="text.secondary" align="center">
              {errorMessage}
            </Typography>
            {enableDemoMode && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 2 }}>
                Try enabling "Demo Mode" above to preview functionality.
              </Typography>
            )}
          </Box>
        ) : filteredData.length === 0 ? (
          <Box
            sx={{
              height,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: (theme) => alpha(theme.palette.background.default, 0.5),
              borderRadius: 1,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              {loading && !demoMode
                ? "Connecting to service..."
                : `Collecting data... (updates every ${updateInterval / 1000}s)`}
            </Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height={height}>
            <LineChart data={filteredData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#444" opacity={0.3} />
              <XAxis
                dataKey="formattedTime"
                tick={{ fill: "#888", fontSize: 11 }}
                interval="preserveStartEnd"
                minTickGap={30}
                angle={-30}
                textAnchor="end"
                height={40}
              />
              <YAxis tick={{ fill: "#888", fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} iconType="line" />

              {thresholds.map((threshold, idx) => (
                <ReferenceLine
                  key={idx}
                  y={threshold.value}
                  label={{
                    value: threshold.label,
                    position: threshold.type === "critical" ? "insideTopLeft" : "insideBottomLeft",
                    fill: threshold.color,
                    fontSize: 11,
                  }}
                  stroke={threshold.color}
                  strokeDasharray="3 3"
                />
              ))}

              {series
                .filter((s) => !s.hide)
                .map((s) => (
                  <Line
                    key={s.dataKey}
                    type="monotone"
                    dataKey={s.dataKey}
                    name={s.name}
                    stroke={s.color}
                    strokeWidth={s.strokeWidth || 2}
                    strokeDasharray={s.strokeDasharray}
                    dot={false}
                    isAnimationActive={false}
                  />
                ))}
            </LineChart>
          </ResponsiveContainer>
        )}

        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
          {demoMode
            ? "Demo Mode Active: Simulating realistic data"
            : `Updates every ${updateInterval / 1000} seconds • Showing last ${filteredData.length} of ${dataPoints.length} data points`}
        </Typography>
      </CardContent>
    </Card>
  );
};
