/**
 * Error Analytics Dashboard
 * Displays error statistics and trends
 */

import { useState } from "react";
import {
  Container,
  Typography,
  Box,
  Grid,
  Card,
  CardContent,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import { ErrorOutline, TrendingUp, TrendingDown, Warning, CheckCircle } from "@mui/icons-material";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import { SkeletonLoader } from "../components/SkeletonLoader";

interface ErrorStats {
  total_errors: number;
  errors_by_type: Record<string, number>;
  errors_by_status: Record<string, number>;
  recent_errors: Array<{
    id: string;
    type: string;
    message: string;
    timestamp: string;
    status_code?: number;
    retryable: boolean;
  }>;
  error_rate: {
    current: number;
    previous: number;
    trend: "up" | "down" | "stable";
  };
}

export default function ErrorAnalyticsPage() {
  const [timeRange, setTimeRange] = useState<"24h" | "7d" | "30d">("24h");

  const { data: stats, isLoading } = useQuery<ErrorStats>({
    queryKey: ["error-analytics", timeRange],
    queryFn: async () => {
      const response = await apiClient.get<ErrorStats>(`/operations/error-analytics`, {
        params: { time_range: timeRange },
      });
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return <SkeletonLoader />;
  }

  if (!stats) {
    return (
      <Container>
        <Alert severity="info">No error analytics data available.</Alert>
      </Container>
    );
  }

  const errorRateChange = stats.error_rate.current - stats.error_rate.previous;
  const errorRatePercent = stats.error_rate.previous
    ? ((errorRateChange / stats.error_rate.previous) * 100).toFixed(1)
    : "0";

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Error Analytics
      </Typography>

      <Box sx={{ mb: 3 }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Time Range</InputLabel>
          <Select
            value={timeRange}
            label="Time Range"
            onChange={(e) => setTimeRange(e.target.value as "24h" | "7d" | "30d")}
          >
            <MenuItem value="24h">Last 24 Hours</MenuItem>
            <MenuItem value="7d">Last 7 Days</MenuItem>
            <MenuItem value="30d">Last 30 Days</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <Grid container spacing={3}>
        {/* Total Errors */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Errors
              </Typography>
              <Typography variant="h4">{stats.total_errors}</Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Error Rate */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Error Rate
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography variant="h4">{stats.error_rate.current.toFixed(2)}%</Typography>
                {stats.error_rate.trend === "up" ? (
                  <TrendingUp color="error" />
                ) : stats.error_rate.trend === "down" ? (
                  <TrendingDown color="success" />
                ) : null}
              </Box>
              <Typography variant="caption" color="text.secondary">
                {errorRateChange >= 0 ? "+" : ""}
                {errorRatePercent}% from previous period
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Errors by Type */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Errors by Type
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 2 }}>
                {Object.entries(stats.errors_by_type).map(([type, count]) => (
                  <Chip
                    key={type}
                    label={`${type}: ${count}`}
                    color={type === "network" ? "error" : type === "server" ? "warning" : "default"}
                    icon={<ErrorOutline />}
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Errors by Status */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Errors by Status Code
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 2 }}>
                {Object.entries(stats.errors_by_status).map(([status, count]) => {
                  const statusNum = parseInt(status);
                  const color =
                    statusNum >= 500
                      ? "error"
                      : statusNum >= 400
                        ? "warning"
                        : statusNum >= 300
                          ? "info"
                          : "default";
                  return <Chip key={status} label={`${status}: ${count}`} color={color} />;
                })}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Errors Table */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Errors
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Time</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Message</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Retryable</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {stats.recent_errors.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center">
                          <Box sx={{ py: 2 }}>
                            <CheckCircle color="success" sx={{ mb: 1 }} />
                            <Typography>No recent errors</Typography>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ) : (
                      stats.recent_errors.map((error) => (
                        <TableRow key={error.id}>
                          <TableCell>{new Date(error.timestamp).toLocaleString()}</TableCell>
                          <TableCell>
                            <Chip
                              label={error.type}
                              size="small"
                              color={
                                error.type === "network"
                                  ? "error"
                                  : error.type === "server"
                                    ? "warning"
                                    : "default"
                              }
                            />
                          </TableCell>
                          <TableCell>{error.message}</TableCell>
                          <TableCell>
                            {error.status_code ? (
                              <Chip
                                label={error.status_code}
                                size="small"
                                color={error.status_code >= 500 ? "error" : "warning"}
                              />
                            ) : (
                              "-"
                            )}
                          </TableCell>
                          <TableCell>
                            {error.retryable ? (
                              <Chip label="Yes" size="small" color="info" />
                            ) : (
                              <Chip label="No" size="small" />
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
}
