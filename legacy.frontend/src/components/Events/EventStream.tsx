import { useState } from "react";
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
  CircularProgress,
  Alert,
} from "@mui/material";
import { formatDistanceToNow } from "date-fns";
import { useEventStream, useEventTypes } from "../../api/queries";

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
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Time</TableCell>
                  <TableCell>Event Type</TableCell>
                  <TableCell>Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {events && events.length > 0 ? (
                  events.map((event, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        {formatDistanceToNow(new Date(event.timestamp_iso), { addSuffix: true })}
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
                                ([key]) =>
                                  !["event_type", "timestamp", "timestamp_iso"].includes(key)
                              )
                            ),
                            null,
                            2
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={3} align="center">
                      No events found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>
    </Card>
  );
}
