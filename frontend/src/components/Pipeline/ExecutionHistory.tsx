import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  CircularProgress,
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
} from '@mui/material';
import { formatDistanceToNow } from 'date-fns';
import { usePipelineExecutions } from '../../api/queries';

export default function ExecutionHistory() {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [jobTypeFilter, setJobTypeFilter] = useState<string>('');

  const { data: executions, isLoading, error } = usePipelineExecutions(
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
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
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
      <Box sx={{ p: 2 }}>
        <Typography>No execution history found</Typography>
      </Box>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
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

        <TableContainer>
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
                        execution.status === 'completed'
                          ? 'success'
                          : execution.status === 'failed'
                          ? 'error'
                          : execution.status === 'running'
                          ? 'primary'
                          : 'default'
                      }
                    />
                  </TableCell>
                  <TableCell>
                    {execution.duration_seconds
                      ? `${(execution.duration_seconds / 60).toFixed(1)} min`
                      : 'N/A'}
                  </TableCell>
                  <TableCell>
                    {execution.stages?.length || 0} stage{execution.stages?.length !== 1 ? 's' : ''}
                  </TableCell>
                  <TableCell>
                    {execution.started_at
                      ? formatDistanceToNow(new Date(execution.started_at * 1000), { addSuffix: true })
                      : 'N/A'}
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

