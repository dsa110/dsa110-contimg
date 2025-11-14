/**
 * Job Management Component
 * Displays recent jobs and job logs
 */
import { useState, useEffect, useRef } from "react";
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from "@mui/material";
import { Refresh } from "@mui/icons-material";
import { useJobs } from "../../api/queries";
import type { JobList } from "../../api/types";

interface JobManagementProps {
  selectedJobId: number | null;
  onJobSelect: (jobId: number | null) => void;
}

export function JobManagement({ selectedJobId, onJobSelect }: JobManagementProps) {
  const [logContent, setLogContent] = useState("");
  const { data: jobsList, refetch: refetchJobs } = useJobs();
  const eventSourceRef = useRef<EventSource | null>(null);

  // Stream job logs when a job is selected
  useEffect(() => {
    if (selectedJobId !== null) {
      // Close existing connection if any
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // Create new EventSource for streaming logs
      const url = `/api/jobs/id/${selectedJobId}/logs`;
      const eventSource = new EventSource(url);

      eventSource.onmessage = (event) => {
        setLogContent((prev) => prev + event.data);
      };

      eventSource.onerror = () => {
        eventSource.close();
        eventSourceRef.current = null;
      };

      eventSourceRef.current = eventSource;

      return () => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      };
    } else {
      // Clear log content when no job is selected
      setLogContent("");
    }
  }, [selectedJobId]);

  const handleJobClick = (job: any) => {
    onJobSelect(job.id);
    setLogContent("");
  };

  return (
    <Box sx={{ flex: 1 }}>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
          }}
        >
          <Typography variant="h6">Recent Jobs</Typography>
          <Button startIcon={<Refresh />} onClick={() => refetchJobs()} size="small">
            Refresh
          </Button>
        </Box>
        <TableContainer sx={{ maxHeight: 300 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>MS</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobsList?.items.slice(0, 10).map((job: any) => (
                <TableRow
                  key={job.id}
                  hover
                  onClick={() => handleJobClick(job)}
                  sx={{
                    cursor: "pointer",
                    bgcolor: selectedJobId === job.id ? "action.selected" : "inherit",
                  }}
                >
                  <TableCell>{job.id}</TableCell>
                  <TableCell>{job.type}</TableCell>
                  <TableCell>
                    <Chip
                      label={job.status}
                      size="small"
                      color={
                        job.status === "done"
                          ? "success"
                          : job.status === "failed"
                            ? "error"
                            : job.status === "running"
                              ? "primary"
                              : "default"
                      }
                    />
                  </TableCell>
                  <TableCell sx={{ fontSize: "0.7rem", fontFamily: "monospace" }}>
                    {job.ms_path ? job.ms_path.split("/").pop() : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Job Logs */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Job Logs
          {selectedJobId !== null && ` (Job #${selectedJobId})`}
        </Typography>
        <Box
          sx={{
            height: 400,
            overflow: "auto",
            bgcolor: "#1e1e1e",
            p: 2,
            borderRadius: 1,
            fontFamily: "monospace",
            fontSize: "0.75rem",
            color: "#00ff00",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {logContent || (selectedJobId === null ? "Select a job to view logs" : "No logs yet...")}
        </Box>
      </Paper>
    </Box>
  );
}
