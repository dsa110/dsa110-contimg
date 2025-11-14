import React from "react";
import {
  Box,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  LinearProgress,
  Paper,
} from "@mui/material";
import { Assessment } from "@mui/icons-material";
import { alpha } from "@mui/material/styles";
import { useStageMetrics } from "../../api/queries";
import { SkeletonLoader } from "../SkeletonLoader";
import { EmptyState } from "../EmptyState";

export default function StageMetrics() {
  const { data: metrics, isLoading, error } = useStageMetrics();

  if (isLoading) {
    return <SkeletonLoader variant="table" rows={5} columns={7} />;
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">Error loading stage metrics: {error.message}</Typography>
      </Box>
    );
  }

  if (!metrics || metrics.length === 0) {
    return (
      <EmptyState
        icon={<Assessment sx={{ fontSize: 64, color: "text.secondary" }} />}
        title="No stage metrics available"
        description="Stage performance metrics will appear here once pipeline stages have been executed. Run a workflow to generate metrics data."
      />
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Stage Performance Metrics
        </Typography>

        <TableContainer
          component={Paper}
          sx={{
            "& .MuiTable-root": {
              "& .MuiTableHead-root .MuiTableRow-root": {
                backgroundColor: "background.paper",
                "& .MuiTableCell-head": {
                  fontWeight: 600,
                  backgroundColor: "action.hover",
                },
              },
              "& .MuiTableBody-root .MuiTableRow-root": {
                "&:nth-of-type(even)": {
                  backgroundColor: alpha("#fff", 0.02),
                },
                "&:hover": {
                  backgroundColor: "action.hover",
                  cursor: "default",
                },
                transition: "background-color 0.2s ease",
              },
            },
          }}
        >
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Stage</TableCell>
                <TableCell align="right">Total Executions</TableCell>
                <TableCell align="right">Success Rate</TableCell>
                <TableCell align="right">Avg Duration</TableCell>
                <TableCell align="right">Min Duration</TableCell>
                <TableCell align="right">Max Duration</TableCell>
                <TableCell align="right">Avg Memory</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {metrics.map((metric) => {
                const successRate =
                  metric.total_executions > 0
                    ? (metric.successful_executions / metric.total_executions) * 100
                    : 0;

                return (
                  <TableRow key={metric.stage_name}>
                    <TableCell>
                      <Typography variant="body2">
                        {metric.stage_name.replace(/_/g, " ")}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">{metric.total_executions}</TableCell>
                    <TableCell align="right">
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "flex-end",
                          gap: 1,
                        }}
                      >
                        <Box sx={{ width: 60 }}>
                          <LinearProgress
                            variant="determinate"
                            value={successRate}
                            color={
                              successRate >= 90
                                ? "success"
                                : successRate >= 70
                                  ? "warning"
                                  : "error"
                            }
                            sx={{ height: 8, borderRadius: 1 }}
                          />
                        </Box>
                        <Typography variant="body2" sx={{ minWidth: 45 }}>
                          {successRate.toFixed(1)}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      {metric.average_duration_seconds.toFixed(1)}s
                    </TableCell>
                    <TableCell align="right">{metric.min_duration_seconds.toFixed(1)}s</TableCell>
                    <TableCell align="right">{metric.max_duration_seconds.toFixed(1)}s</TableCell>
                    <TableCell align="right">
                      {metric.average_memory_mb
                        ? `${metric.average_memory_mb.toFixed(1)} MB`
                        : "N/A"}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
}
