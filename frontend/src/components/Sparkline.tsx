/**
 * Sparkline Component
 * Mini chart for trend visualization
 */
// import React from "react";
import { Box, useTheme } from "@mui/material";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  showArea?: boolean;
  strokeWidth?: number;
}

export function Sparkline({
  data,
  width = 100,
  height = 30,
  color,
  showArea = false,
  strokeWidth = 2,
}: SparklineProps) {
  const theme = useTheme();
  const defaultColor = color || theme.palette.primary.main;

  if (!data || data.length === 0) {
    return (
      <Box
        sx={{
          width,
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "text.secondary",
          fontSize: "0.75rem",
        }}
      >
        No data
      </Box>
    );
  }

  // Normalize data to fit within the chart area
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1; // Avoid division by zero

  const padding = 4;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const points = data.map((value, index) => {
    const x = padding + (index / (data.length - 1 || 1)) * chartWidth;
    const y = padding + chartHeight - ((value - min) / range) * chartHeight;
    return { x, y };
  });

  // Create path for line
  const linePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");

  // Create path for area (if enabled)
  const areaPath = showArea
    ? `${linePath} L ${points[points.length - 1].x} ${height - padding} L ${padding} ${height - padding} Z`
    : "";

  return (
    <Box
      component="svg"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      sx={{
        display: "block",
        overflow: "visible",
      }}
    >
      {/* Area fill (if enabled) */}
      {showArea && areaPath && <path d={areaPath} fill={defaultColor} fillOpacity={0.1} />}
      {/* Line */}
      <path
        d={linePath}
        fill="none"
        stroke={defaultColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Data points */}
      {points.map((point, index) => (
        <circle key={index} cx={point.x} cy={point.y} r={2} fill={defaultColor} />
      ))}
    </Box>
  );
}

/**
 * Metric with Sparkline
 * Combines a metric value with a trend sparkline
 */
interface MetricWithSparklineProps {
  label: string;
  value: string | number;
  trend?: number[];
  color?: "primary" | "success" | "warning" | "error" | "info";
  showTrend?: boolean;
}

export function MetricWithSparkline({
  label,
  value,
  trend,
  color = "primary",
  showTrend = true,
}: MetricWithSparklineProps) {
  const theme = useTheme();
  const colorValue = theme.palette[color]?.main || theme.palette.primary.main;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 0.5,
        p: 1.5,
        borderRadius: 1,
        border: `1px solid ${theme.palette.divider}`,
      }}
    >
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Box>
          <Box sx={{ fontSize: "0.75rem", color: "text.secondary", mb: 0.25 }}>{label}</Box>
          <Box sx={{ fontSize: "1.25rem", fontWeight: 600, color: colorValue }}>{value}</Box>
        </Box>
        {showTrend && trend && trend.length > 0 && (
          <Sparkline data={trend} width={80} height={24} color={colorValue} showArea />
        )}
      </Box>
    </Box>
  );
}
