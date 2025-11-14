import React, { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Paper,
  Button,
} from "@mui/material";
import { EventNote } from "@mui/icons-material";
import { formatDistanceToNow } from "date-fns";
import { useEventStream, useEventTypes } from "../../api/queries";
import { SkeletonLoader } from "../SkeletonLoader";
import { EmptyState } from "../EmptyState";
import { alpha } from "@mui/material/styles";

export default function EventStream() {
  const [eventTypeFilter, setEventTypeFilter] = useState<string>("");
  const [limit, setLimit] = useState<number>(100);
  const [sinceMinutes, setSinceMinutes] = useState<number | undefined>(undefined);

  const {
    data: events,
    isLoading,
    error,
  } = useEventStream(eventTypeFilter || undefined, limit, sinceMinutes);
  const { data: eventTypes } = useEventTypes();

  const getEventTypeColor = (eventType: string) => {
    if (eventType.includes("error") || eventType.includes("failed")) return "error";
    if (eventType.includes("completed") || eventType.includes("solved")) return "success";
    if (eventType.includes("started") || eventType.includes("detected")) return "info";
    return "default";
  };

  if (error) {
    return (
      <Alert severity="error">
        Failed to load event stream: {error instanceof Error ? error.message : "Unknown error"}
      </Alert>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Event Stream
        </Typography>

        {/* Filters */}
        <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Event Type</InputLabel>
            <Select
              value={eventTypeFilter}
              label="Event Type"
              onChange={(e) => setEventTypeFilter(e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              {eventTypes?.event_types.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="Limit"
            type="number"
            value={limit}
            onChange={(e) => setLimit(parseInt(e.target.value) || 100)}
            sx={{ width: 120 }}
            inputProps={{ min: 1, max: 1000 }}
          />

          <TextField
            label="Since (minutes)"
            type="number"
            value={sinceMinutes || ""}
            onChange={(e) => setSinceMinutes(e.target.value ? parseInt(e.target.value) : undefined)}
            sx={{ width: 150 }}
            placeholder="All time"
            inputProps={{ min: 1 }}
          />
        </Box>

        {/* Event Table */}
        {isLoading ? (
          <SkeletonLoader variant="table" rows={5} columns={3} />
        ) : events && events.length > 0 ? (
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
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Event Type</TableCell>
                  <TableCell>Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {events.map((event, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      {formatDistanceToNow(new Date(event.timestamp_iso), {
                        addSuffix: true,
                      })}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={event.event_type}
                        color={getEventTypeColor(event.event_type)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
                        {JSON.stringify(
                          Object.fromEntries(
                            Object.entries(event).filter(
                              ([key]) => !["event_type", "timestamp", "timestamp_iso"].includes(key)
                            )
                          ),
                          null,
                          2
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <EmptyState
            icon={<EventNote sx={{ fontSize: 64, color: "text.secondary" }} />}
            title="No events found"
            description="Events are system notifications about pipeline activities, errors, and status changes. They will appear here as the pipeline processes data."
            actions={[
              <Button
                key="clear"
                variant="outlined"
                onClick={() => {
                  setEventTypeFilter("");
                  setSinceMinutes(undefined);
                }}
              >
                Clear Filters
              </Button>,
            ]}
          >
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Example event types:
              </Typography>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
                <Chip label="pipeline.started" size="small" />
                <Chip label="calibration.completed" size="small" />
                <Chip label="error.occurred" size="small" />
              </Box>
            </Box>
          </EmptyState>
        )}
      </CardContent>
    </Card>
  );
}
