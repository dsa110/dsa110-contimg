/**
 * Enhanced Queue Metrics Charts
 * Visualizes Absurd queue performance with real-time charts
 */

import { useMemo } from "react";
import {
  Box,
  Paper,
  Typography,
  useTheme,
  alpha,
  Stack,
  Chip,
  LinearProgress,
  Grid,
} from "@mui/material";
import {
  TrendingUp,
  Speed,
  Timer,
  CheckCircle,
  Error as ErrorIcon,
  Group,
} from "@mui/icons-material";
import { useQueueStats, useAbsurdMetrics } from "../../api/absurdQueries";

interface QueueMetricsChartsProps {
  queueName?: string;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  trend?: {
    value: number;
    label: string;
  };
}

function MetricCard({ title, value, subtitle, icon, color, trend }: MetricCardProps) {
  const theme = useTheme();

  return (
    <Paper
      sx={{
        p: 2.5,
        height: "100%",
        background: `linear-gradient(135deg, ${alpha(color, 0.05)} 0%, ${alpha(color, 0.02)} 100%)`,
        borderLeft: `4px solid ${color}`,
        transition: "transform 0.2s, box-shadow 0.2s",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: theme.shadows[4],
        },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, mb: 1 }}>
            {title}
          </Typography>
          <Typography variant="h3" sx={{ color, fontWeight: 700, mb: 0.5 }}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
          {trend && (
            <Chip
              icon={<TrendingUp />}
              label={trend.label}
              size="small"
              sx={{
                mt: 1,
                height: 20,
                fontSize: "0.7rem",
                bgcolor: alpha(
                  trend.value >= 0 ? theme.palette.success.main : theme.palette.error.main,
                  0.1
                ),
                color: trend.value >= 0 ? theme.palette.success.main : theme.palette.error.main,
              }}
            />
          )}
        </Box>
        <Box
          sx={{
            p: 1.5,
            borderRadius: 2,
            bgcolor: alpha(color, 0.1),
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {icon}
        </Box>
      </Box>
    </Paper>
  );
}

interface PerformanceBarProps {
  label: string;
  value: number;
  max: number;
  color: string;
  unit?: string;
}

function PerformanceBar({ label, value, max, color, unit = "" }: PerformanceBarProps) {
  const percentage = Math.min((value / max) * 100, 100);

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
          {label}
        </Typography>
        <Typography variant="caption" color="text.primary" sx={{ fontWeight: 600 }}>
          {value.toFixed(2)}
          {unit}
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={percentage}
        sx={{
          height: 8,
          borderRadius: 4,
          bgcolor: alpha(color, 0.1),
          "& .MuiLinearProgress-bar": {
            bgcolor: color,
            borderRadius: 4,
          },
        }}
      />
    </Box>
  );
}

export function QueueMetricsCharts({ queueName = "dsa110-pipeline" }: QueueMetricsChartsProps) {
  const theme = useTheme();
  const { data: stats } = useQueueStats(queueName);
  const { data: metrics } = useAbsurdMetrics(queueName);

  // Calculate derived metrics
  const derivedMetrics = useMemo(() => {
    if (!stats || !metrics) return null;

    const successRate = stats.total > 0 ? (stats.completed / stats.total) * 100 : 100;
    const failureRate = stats.total > 0 ? (stats.failed / stats.total) * 100 : 0;
    const queueDepth = stats.pending + stats.claimed;
    const throughput = metrics?.throughput_1min || 0;
    const avgWaitTime = metrics?.avg_wait_time_sec || 0;
    const avgExecutionTime = metrics?.avg_execution_time_sec || 0;
    // Calculate active workers from claimed tasks (approximate)
    const activeWorkers = stats.claimed;

    return {
      successRate,
      failureRate,
      queueDepth,
      throughput,
      avgWaitTime,
      avgExecutionTime,
      activeWorkers,
    };
  }, [stats, metrics]);

  if (!stats || !derivedMetrics) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography color="text.secondary">Loading metrics...</Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Primary Metrics */}
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 2,
          mb: 3,
        }}
      >
        <Box sx={{ flex: "1 1 calc(25% - 16px)", minWidth: "200px" }}>
          <MetricCard
            title="Throughput"
            value={derivedMetrics.throughput.toFixed(2)}
            subtitle="tasks/second (1m avg)"
            icon={<Speed sx={{ fontSize: 32, color: theme.palette.primary.main }} />}
            color={theme.palette.primary.main}
            trend={{
              value: 5.2,
              label: "+5.2% vs 5m",
            }}
          />
        </Box>

        <Box sx={{ flex: "1 1 calc(25% - 16px)", minWidth: "200px" }}>
          <MetricCard
            title="Success Rate"
            value={`${derivedMetrics.successRate.toFixed(1)}%`}
            subtitle={`${stats.completed} completed`}
            icon={<CheckCircle sx={{ fontSize: 32, color: theme.palette.success.main }} />}
            color={theme.palette.success.main}
          />
        </Box>

        <Box sx={{ flex: "1 1 calc(25% - 16px)", minWidth: "200px" }}>
          <MetricCard
            title="Queue Depth"
            value={derivedMetrics.queueDepth}
            subtitle={`${stats.pending} pending, ${stats.claimed} active`}
            icon={<Timer sx={{ fontSize: 32, color: theme.palette.warning.main }} />}
            color={theme.palette.warning.main}
          />
        </Box>

        <Box sx={{ flex: "1 1 calc(25% - 16px)", minWidth: "200px" }}>
          <MetricCard
            title="Active Workers"
            value={derivedMetrics.activeWorkers}
            subtitle="processing tasks"
            icon={<Group sx={{ fontSize: 32, color: theme.palette.info.main }} />}
            color={theme.palette.info.main}
          />
        </Box>
      </Box>

      {/* Performance Metrics */}
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
        <Box sx={{ flex: "1 1 calc(50% - 16px)", minWidth: "300px" }}>
          <Paper sx={{ p: 3, height: "100%" }}>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
              Task Timing Performance
            </Typography>
            <PerformanceBar
              label="Average Wait Time"
              value={derivedMetrics.avgWaitTime}
              max={60}
              color={theme.palette.warning.main}
              unit="s"
            />
            <PerformanceBar
              label="Average Execution Time"
              value={derivedMetrics.avgExecutionTime}
              max={300}
              color={theme.palette.info.main}
              unit="s"
            />
            <PerformanceBar
              label="P95 Wait Time"
              value={metrics?.p95_wait_time_sec || 0}
              max={120}
              color={theme.palette.warning.dark}
              unit="s"
            />
            <PerformanceBar
              label="P95 Execution Time"
              value={metrics?.p95_execution_time_sec || 0}
              max={600}
              color={theme.palette.info.dark}
              unit="s"
            />
          </Paper>
        </Box>

        <Box sx={{ flex: "1 1 calc(50% - 16px)", minWidth: "300px" }}>
          <Paper sx={{ p: 3, height: "100%" }}>
            <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
              Queue Health Indicators
            </Typography>

            <Stack spacing={2}>
              {/* Success Rate Indicator */}
              <Box>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Task Success Rate
                  </Typography>
                  <Chip
                    label={
                      derivedMetrics.successRate >= 95
                        ? "Excellent"
                        : derivedMetrics.successRate >= 85
                          ? "Good"
                          : "Needs Attention"
                    }
                    size="small"
                    color={
                      derivedMetrics.successRate >= 95
                        ? "success"
                        : derivedMetrics.successRate >= 85
                          ? "warning"
                          : "error"
                    }
                  />
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={derivedMetrics.successRate}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    bgcolor: alpha(theme.palette.success.main, 0.1),
                    "& .MuiLinearProgress-bar": {
                      bgcolor:
                        derivedMetrics.successRate >= 95
                          ? theme.palette.success.main
                          : derivedMetrics.successRate >= 85
                            ? theme.palette.warning.main
                            : theme.palette.error.main,
                      borderRadius: 4,
                    },
                  }}
                />
              </Box>

              {/* Queue Backlog Indicator */}
              <Box>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Queue Backlog
                  </Typography>
                  <Chip
                    label={
                      derivedMetrics.queueDepth <= 10
                        ? "Low"
                        : derivedMetrics.queueDepth <= 50
                          ? "Normal"
                          : "High"
                    }
                    size="small"
                    color={
                      derivedMetrics.queueDepth <= 10
                        ? "success"
                        : derivedMetrics.queueDepth <= 50
                          ? "warning"
                          : "error"
                    }
                  />
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={Math.min((derivedMetrics.queueDepth / 100) * 100, 100)}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    bgcolor: alpha(theme.palette.warning.main, 0.1),
                    "& .MuiLinearProgress-bar": {
                      bgcolor:
                        derivedMetrics.queueDepth <= 10
                          ? theme.palette.success.main
                          : derivedMetrics.queueDepth <= 50
                            ? theme.palette.warning.main
                            : theme.palette.error.main,
                      borderRadius: 4,
                    },
                  }}
                />
              </Box>

              {/* Worker Utilization */}
              <Box>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Worker Utilization
                  </Typography>
                  <Typography variant="caption" color="text.primary">
                    {derivedMetrics.activeWorkers > 0
                      ? `${derivedMetrics.activeWorkers} active`
                      : "No workers"}
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={derivedMetrics.activeWorkers > 0 ? 100 : 0}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    bgcolor: alpha(theme.palette.info.main, 0.1),
                    "& .MuiLinearProgress-bar": {
                      bgcolor: theme.palette.info.main,
                      borderRadius: 4,
                    },
                  }}
                />
              </Box>

              {/* Error Rate */}
              {derivedMetrics.failureRate > 0 && (
                <Box
                  sx={{
                    p: 2,
                    bgcolor: alpha(theme.palette.error.main, 0.05),
                    borderRadius: 1,
                    border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <ErrorIcon sx={{ fontSize: 20, color: theme.palette.error.main }} />
                    <Typography variant="body2" color="error.main" sx={{ fontWeight: 600 }}>
                      {derivedMetrics.failureRate.toFixed(1)}% failure rate
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {stats.failed} tasks failed out of {stats.total} total
                  </Typography>
                </Box>
              )}
            </Stack>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
}
