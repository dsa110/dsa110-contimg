/**
 * Grafana-style time-series chart for monitoring Absurd queue depth.
 * Tracks queue depth over time with configurable alert thresholds.
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
  FormControlLabel,
  Switch,
} from "@mui/material";
import { useQueueStats } from "../api/absurdQueries";
import { alpha } from "@mui/material/styles";
import { TrendingUp, Warning, CheckCircle } from "@mui/icons-material";

interface DataPoint {
  timestamp: number;
  queueDepth: number;
  pending: number;
  claimed: number;
  formattedTime: string;
}

interface QueueDepthChartProps {
  queueName: string;
  warningThreshold?: number;
  criticalThreshold?: number;
  maxDataPoints?: number;
  updateInterval?: number;
}

type TimeRange = "15m" | "1h" | "6h" | "24h";

export const QueueDepthChart: React.FC<QueueDepthChartProps> = ({
  queueName,
  warningThreshold = 30,
  criticalThreshold = 50,
  maxDataPoints = 100,
  updateInterval = 15000, // 15 seconds default
}) => {
  const { data: queueStats, isLoading, error } = useQueueStats(queueName);
  const [dataPoints, setDataPoints] = useState<DataPoint[]>([]);
  const [timeRange, setTimeRange] = useState<TimeRange>("1h");
  const [demoMode, setDemoMode] = useState(false);
  const lastUpdateRef = useRef<number>(0);

  // Clear data when switching modes to avoid mixing real and demo data
  useEffect(() => {
    setDataPoints([]);
  }, [demoMode]);

  // Load persisted data from localStorage on mount
  useEffect(() => {
    const storageKey = "queue-depth-history-" + queueName;
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setDataPoints(parsed);
      } catch (error) {
        console.warn("Failed to load queue depth history:", error);
      }
    }
  }, [queueName]);

  // Demo Mode Data Generation
  useEffect(() => {
    if (!demoMode) return;

    const interval = setInterval(() => {
      const now = Date.now();
      // Generate a sine wave pattern with noise (faster oscillation for demo)
      const timeComponent = now / 5000; // Faster: ~31 second period
      const baseValue = 25 + Math.sin(timeComponent) * 15; // Oscillate between 10 and 40
      const noise = Math.random() * 10 - 5;
      const spike = Math.random() > 0.97 ? 20 : 0; // Occasional spikes (less frequent)

      const queueDepth = Math.max(0, Math.round(baseValue + noise + spike));
      const claimed = Math.min(queueDepth, Math.round(4 + Math.random() * 2)); // 4-6 active workers
      const pending = Math.max(0, queueDepth - claimed);

      const newPoint: DataPoint = {
        timestamp: now,
        queueDepth,
        pending,
        claimed,
        formattedTime: new Date(now).toLocaleTimeString(),
      };

      setDataPoints((prev) => {
        const updated = [...prev, newPoint].slice(-maxDataPoints);
        return updated;
      });
    }, 1000); // Update every second in demo mode for smooth visuals

    return () => clearInterval(interval);
  }, [demoMode, maxDataPoints]);

  // Real Data Collection (only when not in demo mode)
  useEffect(() => {
    if (demoMode) return;
    if (!queueStats) return;

    const now = Date.now();
    const timeSinceLastUpdate = now - lastUpdateRef.current;

    // Only add a new data point if enough time has passed
    if (timeSinceLastUpdate < updateInterval) return;

    lastUpdateRef.current = now;

    const queueDepth = (queueStats.pending || 0) + (queueStats.claimed || 0);
    const newPoint: DataPoint = {
      timestamp: now,
      queueDepth,
      pending: queueStats.pending || 0,
      claimed: queueStats.claimed || 0,
      formattedTime: new Date(now).toLocaleTimeString(),
    };

    setDataPoints((prev) => {
      const updated = [...prev, newPoint].slice(-maxDataPoints);
      // Persist to localStorage
      const storageKey = "queue-depth-history-" + queueName;
      localStorage.setItem(storageKey, JSON.stringify(updated));
      return updated;
    });
  }, [queueStats, updateInterval, maxDataPoints, queueName, demoMode]);

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

  const getCurrentValues = () => {
    if (demoMode && dataPoints.length > 0) {
      const last = dataPoints[dataPoints.length - 1];
      return {
        depth: last.queueDepth,
        pending: last.pending,
        active: last.claimed,
      };
    }
    return {
      depth: queueStats ? (queueStats.pending || 0) + (queueStats.claimed || 0) : 0,
      pending: queueStats?.pending || 0,
      active: queueStats?.claimed || 0,
    };
  };

  const current = getCurrentValues();

  // Determine current status based on thresholds
  const getStatus = () => {
    if (error && !demoMode) return { color: "error", label: "API ERROR", icon: <Warning /> };
    if (isLoading && dataPoints.length === 0 && !demoMode)
      return { color: "default", label: "CONNECTING", icon: <TrendingUp /> };

    // Check thresholds even in demo mode to demonstrate alert behavior
    if (current.depth >= criticalThreshold) {
      return { color: "error", label: demoMode ? "DEMO: CRITICAL" : "CRITICAL", icon: <Warning /> };
    }
    if (current.depth >= warningThreshold) {
      return { color: "warning", label: demoMode ? "DEMO: WARNING" : "WARNING", icon: <Warning /> };
    }
    return {
      color: "success",
      label: demoMode ? "DEMO: HEALTHY" : "HEALTHY",
      icon: <CheckCircle />,
    };
  };

  const status = getStatus();
  const errorMessage = error instanceof Error ? error.message : "Unknown error";

  // Custom tooltip
  interface TooltipProps {
    active?: boolean;
    payload?: Array<{ payload: DataPoint }>;
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
          <Typography variant="body2">
            <strong>Queue Depth:</strong> {data.queueDepth}
          </Typography>
          <Typography variant="body2" color="primary.main">
            Pending: {data.pending}
          </Typography>
          <Typography variant="body2" color="secondary.main">
            Claimed: {data.claimed}
          </Typography>
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
              <TrendingUp sx={{ mr: 1, verticalAlign: "middle" }} />
              Queue Depth Monitoring
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

        <Box sx={{ display: "flex", gap: 3, mb: 2 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Current Depth
            </Typography>
            <Typography variant="h4" color="primary.main">
              {current.depth}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Pending
            </Typography>
            <Typography variant="h4" color="text.primary">
              {current.pending}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Active
            </Typography>
            <Typography variant="h4" color="text.secondary">
              {current.active}
            </Typography>
          </Box>
        </Box>

        {!demoMode && error ? (
          <Box
            sx={{
              height: 300,
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
              {errorMessage.includes("404") ||
              errorMessage.includes("500") ||
              errorMessage.includes("503")
                ? "Absurd service is disabled or not running."
                : errorMessage}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 2 }}>
              Try enabling "Demo Mode" above to preview functionality.
            </Typography>
          </Box>
        ) : filteredData.length === 0 ? (
          <Box
            sx={{
              height: 300,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: (theme) => alpha(theme.palette.background.default, 0.5),
              borderRadius: 1,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              {isLoading && !demoMode
                ? "Connecting to service..."
                : "Collecting data... (updates every " + updateInterval / 1000 + "s)"}
            </Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={filteredData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#444" opacity={0.3} />
              <XAxis
                dataKey="formattedTime"
                tick={{ fill: "#888", fontSize: 11 }}
                tickFormatter={(value, index) => {
                  // Show fewer labels for readability
                  const totalTicks = filteredData.length;
                  const showEvery = Math.ceil(totalTicks / 8);
                  return index % showEvery === 0 ? value : "";
                }}
              />
              <YAxis tick={{ fill: "#888", fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} iconType="line" />

              {/* Alert threshold lines */}
              <ReferenceLine
                y={criticalThreshold}
                stroke="#f44336"
                strokeDasharray="5 5"
                strokeWidth={2}
                label={{
                  value: "Critical (" + criticalThreshold + ")",
                  fill: "#f44336",
                  fontSize: 11,
                  position: "right",
                }}
              />
              <ReferenceLine
                y={warningThreshold}
                stroke="#ff9800"
                strokeDasharray="5 5"
                strokeWidth={2}
                label={{
                  value: "Warning (" + warningThreshold + ")",
                  fill: "#ff9800",
                  fontSize: 11,
                  position: "right",
                }}
              />

              {/* Data lines */}
              <Line
                type="monotone"
                dataKey="queueDepth"
                stroke="#1976d2"
                strokeWidth={3}
                dot={false}
                name="Total Queue Depth"
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="pending"
                stroke="#9c27b0"
                strokeWidth={2}
                dot={false}
                name="Pending"
                strokeDasharray="3 3"
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="claimed"
                stroke="#4caf50"
                strokeWidth={2}
                dot={false}
                name="Claimed (Active)"
                strokeDasharray="3 3"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        <Typography variant="caption" color="text.secondary" display="block" mt={1}>
          {demoMode
            ? "Demo Mode Active: Simulating realistic workload"
            : `Updates every ${updateInterval / 1000} seconds • Showing last ${filteredData.length} of ${dataPoints.length} data points`}
        </Typography>
      </CardContent>
    </Card>
  );
};
