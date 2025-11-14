import React from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { useEventStatistics } from "../../api/queries";

export default function EventStats() {
  const { data: stats, isLoading, error } = useEventStatistics();

  if (error) {
    return (
      <Alert severity="error">
        Failed to load event statistics: {error instanceof Error ? error.message : "Unknown error"}
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!stats) {
    return <Alert severity="info">No statistics available</Alert>;
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Event Statistics
        </Typography>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Total Events
                </Typography>
                <Typography variant="h4">{stats.total_events.toLocaleString()}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Events in History
                </Typography>
                <Typography variant="h4">{stats.events_in_history.toLocaleString()}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Last Minute
                </Typography>
                <Typography variant="h4">{stats.events_last_minute.toLocaleString()}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Last Hour
                </Typography>
                <Typography variant="h4">{stats.events_last_hour.toLocaleString()}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Events by Type */}
        <Typography variant="subtitle1" gutterBottom>
          Events by Type
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Event Type</TableCell>
                <TableCell align="right">Count</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(stats.events_per_type || {}).map(([type, count]) => (
                <TableRow key={type}>
                  <TableCell>
                    <Chip label={type} size="small" />
                  </TableCell>
                  <TableCell align="right">{count.toLocaleString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Subscribers */}
        {stats.subscribers && Object.keys(stats.subscribers).length > 0 && (
          <>
            <Typography variant="subtitle1" gutterBottom sx={{ mt: 3 }}>
              Subscribers
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Event Type</TableCell>
                    <TableCell align="right">Subscribers</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(stats.subscribers).map(([type, count]) => (
                    <TableRow key={type}>
                      <TableCell>
                        <Chip label={type} size="small" />
                      </TableCell>
                      <TableCell align="right">{count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </CardContent>
    </Card>
  );
}
