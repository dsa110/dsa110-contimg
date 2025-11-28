import React, { useState } from "react";
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
  Chip,
  TablePagination,
  TextField,
  MenuItem,
  Paper,
} from "@mui/material";
import { History } from "@mui/icons-material";
import { alpha } from "@mui/material/styles";
import { formatDistanceToNow } from "date-fns";
import { usePipelineExecutions } from "../../api/queries";
import { SkeletonLoader } from "../SkeletonLoader";
import { EmptyState } from "../EmptyState";

export default function ExecutionHistory() {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [jobTypeFilter, setJobTypeFilter] = useState<string>("");

  const {
    data: executions,
    isLoading,
    error,
  } = usePipelineExecutions(
    statusFilter || undefined,
    jobTypeFilter || undefined,
    rowsPerPage,
    page * rowsPerPage
  );

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  if (isLoading) {
    return <SkeletonLoader variant="table" rows={5} columns={6} />;
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">Error loading execution history: {error.message}</Typography>
      </Box>
    );
  }

  if (!executions || executions.length === 0) {
    return (
      <EmptyState
        icon={<History sx={{ fontSize: 64, color: "text.secondary" }} />}
        title="No execution history"
        description="Execution history will appear here once pipeline workflows have been run. Start a new workflow from the Control page to generate execution records."
      />
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
          <TextField
            select
            label="Status"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(0);
            }}
            sx={{ minWidth: 150 }}
            size="small"
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
            <MenuItem value="running">Running</MenuItem>
            <MenuItem value="pending">Pending</MenuItem>
          </TextField>

          <TextField
            label="Job Type"
            value={jobTypeFilter}
            onChange={(e) => {
              setJobTypeFilter(e.target.value);
              setPage(0);
            }}
            sx={{ minWidth: 200 }}
            size="small"
          />
        </Box>

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
                <TableCell>ID</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Stages</TableCell>
                <TableCell>Started</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {executions.map((execution) => (
                <TableRow key={execution.id}>
                  <TableCell>{execution.id}</TableCell>
                  <TableCell>{execution.job_type}</TableCell>
                  <TableCell>
                    <Chip
                      label={execution.status}
                      size="small"
                      color={
                        execution.status === "completed"
                          ? "success"
                          : execution.status === "failed"
                            ? "error"
                            : execution.status === "running"
                              ? "primary"
                              : "default"
                      }
                    />
                  </TableCell>
                  <TableCell>
                    {execution.duration_seconds
                      ? `${(execution.duration_seconds / 60).toFixed(1)} min`
                      : "N/A"}
                  </TableCell>
                  <TableCell>
                    {execution.stages?.length || 0} stage
                    {execution.stages?.length !== 1 ? "s" : ""}
                  </TableCell>
                  <TableCell>
                    {execution.started_at
                      ? formatDistanceToNow(new Date(execution.started_at * 1000), {
                          addSuffix: true,
                        })
                      : "N/A"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={-1} // Total count not available from API
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="Rows per page:"
        />
      </CardContent>
    </Card>
  );
}
