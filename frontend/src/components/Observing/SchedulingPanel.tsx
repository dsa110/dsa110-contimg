/**
 * Scheduling Panel Component
 * Real-time scheduling widgets for telescope operations
 */
import { useMemo } from "react";
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  Stack,
} from "@mui/material";
import Grid from "@mui/material/GridLegacy";
import { Send as SendIcon, CheckCircle, Warning, Error as ErrorIcon } from "@mui/icons-material";

interface PointingHistoryItem {
  ra_deg: number;
  dec_deg: number;
  mjd: number;
  timestamp?: string;
}

interface CalibratorMatch {
  name: string;
  ra_deg: number;
  dec_deg: number;
  separation_deg: number;
  flux_jy?: number;
}

interface SchedulingPanelProps {
  currentPointing?: PointingHistoryItem;
  upcomingScans?: Array<{
    target: string;
    start_time: string;
    duration_min: number;
  }>;
  calibrators?: CalibratorMatch[];
}

export function SchedulingPanel({
  currentPointing,
  upcomingScans = [],
  calibrators = [],
}: SchedulingPanelProps) {
  // Calculate elevation for current LST (simplified - would use real LST calculation)
  const calculateElevation = (ra: number, dec: number, _ra_current?: number) => {
    // Simplified elevation calculation assuming DSA-110 latitude ~37.23°N
    const lat = 37.23;
    const hour_angle = 0; // Would calculate from LST and RA
    const elevation =
      Math.asin(
        Math.sin((dec * Math.PI) / 180) * Math.sin((lat * Math.PI) / 180) +
          Math.cos((dec * Math.PI) / 180) *
            Math.cos((lat * Math.PI) / 180) *
            Math.cos((hour_angle * Math.PI) / 180)
      ) *
      (180 / Math.PI);
    return elevation;
  };

  const getElevationStatus = (elevation: number) => {
    if (elevation > 60)
      return { color: "success" as const, label: "Excellent", icon: <CheckCircle /> };
    if (elevation > 30) return { color: "warning" as const, label: "Good", icon: <Warning /> };
    return { color: "error" as const, label: "Low", icon: <ErrorIcon /> };
  };

  // Process upcoming scans
  const scanSummary = useMemo(() => {
    if (upcomingScans.length === 0) return null;
    const totalDuration = upcomingScans.reduce((sum, scan) => sum + scan.duration_min, 0);
    return {
      count: upcomingScans.length,
      totalDuration,
      nextTarget: upcomingScans[0]?.target,
      nextStart: upcomingScans[0]?.start_time,
    };
  }, [upcomingScans]);

  return (
    <Box>
      <Grid container spacing={2}>
        {/* Current Pointing Status */}
        <Grid item xs={12} md={6} {...({} as any)}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Current Pointing
              </Typography>
              {currentPointing ? (
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      RA / Dec (J2000)
                    </Typography>
                    <Typography variant="body1" sx={{ fontFamily: "monospace" }}>
                      {currentPointing.ra_deg.toFixed(4)}° / {currentPointing.dec_deg.toFixed(4)}°
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Elevation
                    </Typography>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="h5">
                        {calculateElevation(
                          currentPointing.ra_deg,
                          currentPointing.dec_deg
                        ).toFixed(1)}
                        °
                      </Typography>
                      <Chip
                        {...getElevationStatus(
                          calculateElevation(currentPointing.ra_deg, currentPointing.dec_deg)
                        )}
                        size="small"
                      />
                    </Box>
                  </Box>
                  {currentPointing.timestamp && (
                    <Typography variant="caption" color="text.secondary">
                      Updated: {new Date(currentPointing.timestamp).toLocaleString()}
                    </Typography>
                  )}
                </Stack>
              ) : (
                <Alert severity="info">No current pointing data available</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Slew Command */}
        <Grid item xs={12} md={6} {...({} as any)}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Slew Control
              </Typography>
              <Stack spacing={2}>
                <TextField label="Target RA (deg)" type="number" size="small" fullWidth />
                <TextField label="Target Dec (deg)" type="number" size="small" fullWidth />
                <Button variant="contained" startIcon={<SendIcon />} fullWidth>
                  Request Slew
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Upcoming Scans */}
        {scanSummary && (
          <Grid item xs={12} {...({} as any)}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Scheduled Observations
              </Typography>
              <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                <Chip label={`${scanSummary.count} scans`} color="primary" />
                <Chip label={`${scanSummary.totalDuration} min total`} />
                <Chip label={`Next: ${scanSummary.nextTarget}`} color="secondary" />
              </Stack>
              <Typography variant="caption" color="text.secondary">
                Starting at {scanSummary.nextStart}
              </Typography>
            </Paper>
          </Grid>
        )}

        {/* Observable Calibrators */}
        {calibrators.length > 0 && (
          <Grid item xs={12} {...({} as any)}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Observable Calibrators
                </Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Calibrator</TableCell>
                        <TableCell align="right">RA (deg)</TableCell>
                        <TableCell align="right">Dec (deg)</TableCell>
                        <TableCell align="right">Separation</TableCell>
                        <TableCell align="right">Flux (Jy)</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {calibrators.slice(0, 5).map((cal) => (
                        <TableRow key={cal.name}>
                          <TableCell>{cal.name}</TableCell>
                          <TableCell align="right">{cal.ra_deg.toFixed(2)}</TableCell>
                          <TableCell align="right">{cal.dec_deg.toFixed(2)}</TableCell>
                          <TableCell align="right">{cal.separation_deg.toFixed(1)}°</TableCell>
                          <TableCell align="right">
                            {cal.flux_jy ? cal.flux_jy.toFixed(1) : "—"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}
