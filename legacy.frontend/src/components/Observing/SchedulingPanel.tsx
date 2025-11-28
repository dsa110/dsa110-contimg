/**
 * Scheduling Panel Component
 * Shows upcoming scans, elevation limits, and quick slewing commands
 */
import { useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  Stack,
  TextField,
  Alert,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  Schedule as ScheduleIcon,
  Refresh as RefreshIcon,
  Navigation as SlewIcon,
  Visibility as VisibilityIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

interface PointingHistoryItem {
  ra_deg: number;
  dec_deg: number;
  timestamp: number;
}

interface CalibratorMatch {
  name?: string;
  ra_deg?: number;
  dec_deg?: number;
  weighted_flux?: number;
  flux_jy?: number;
  sep_deg?: number;
  timestamp?: string;
}

interface SchedulingPanelProps {
  pointingHistory?: PointingHistoryItem[];
  calibratorMatches?: CalibratorMatch[];
}

// Calculate elevation from RA/Dec (simplified - assumes DSA-110 location)
function calculateElevation(_ra: number, dec: number): number {
  // DSA-110 location: ~37°N latitude
  const latitude = 37.0;
  const latRad = (latitude * Math.PI) / 180;
  const decRad = (dec * Math.PI) / 180;

  // Simplified elevation calculation at transit
  // For a more accurate calculation, we'd need LST and hour angle
  const sinAlt = Math.sin(latRad) * Math.sin(decRad) + Math.cos(latRad) * Math.cos(decRad);
  const elevation = (Math.asin(sinAlt) * 180) / Math.PI;

  return elevation;
}

// Get elevation constraints
function getElevationStatus(elevation: number): {
  status: "good" | "marginal" | "poor" | "unobservable";
  color: "success" | "warning" | "error" | "default";
  message: string;
} {
  if (elevation < 15) {
    return {
      status: "unobservable",
      color: "default",
      message: "Below horizon or too low",
    };
  } else if (elevation < 30) {
    return {
      status: "poor",
      color: "error",
      message: "Poor elevation (high airmass)",
    };
  } else if (elevation < 45) {
    return {
      status: "marginal",
      color: "warning",
      message: "Marginal elevation",
    };
  } else {
    return {
      status: "good",
      color: "success",
      message: "Good elevation",
    };
  }
}

export function SchedulingPanel({ pointingHistory, calibratorMatches }: SchedulingPanelProps) {
  const [targetRA, setTargetRA] = useState("");
  const [targetDec, setTargetDec] = useState("");
  const [slewStatus, setSlewStatus] = useState<string | null>(null);

  // Generate upcoming scans from calibrator matches
  const upcomingScans = useMemo(() => {
    if (!calibratorMatches || calibratorMatches.length === 0) return [];

    // Get unique calibrators and their observability
    const scans = calibratorMatches
      .slice(0, 10)
      .map((match: CalibratorMatch) => {
        const elevation = calculateElevation(match.ra_deg || 0, match.dec_deg || 0);
        const elevStatus = getElevationStatus(elevation);

        return {
          name: match.name || "Unknown",
          ra: match.ra_deg,
          dec: match.dec_deg,
          flux: match.weighted_flux || match.flux_jy || 0,
          separation: match.sep_deg,
          elevation,
          elevationStatus: elevStatus,
          timestamp: match.timestamp,
        };
      })
      .sort((a, b) => b.elevation - a.elevation); // Sort by elevation (highest first)

    return scans;
  }, [calibratorMatches]);

  // Get current pointing from most recent history
  const currentPointing = useMemo(() => {
    if (!pointingHistory || pointingHistory.length === 0) return null;
    const latest = pointingHistory[pointingHistory.length - 1];
    return {
      ra: latest.ra_deg,
      dec: latest.dec_deg,
      timestamp: latest.timestamp,
    };
  }, [pointingHistory]);

  const handleSlew = async () => {
    const ra = parseFloat(targetRA);
    const dec = parseFloat(targetDec);

    if (isNaN(ra) || isNaN(dec)) {
      setSlewStatus("Invalid coordinates");
      return;
    }

    if (ra < 0 || ra >= 360 || dec < -90 || dec > 90) {
      setSlewStatus("Coordinates out of range");
      return;
    }

    setSlewStatus("Slewing...");

    // In a real implementation, this would call the telescope control API
    // For now, we just simulate the slew
    setTimeout(() => {
      setSlewStatus(`Slew command sent to RA=${ra.toFixed(4)}°, Dec=${dec.toFixed(4)}°`);
      setTimeout(() => setSlewStatus(null), 5000);
    }, 1000);
  };

  return (
    <Stack spacing={2}>
      {/* Current Status */}
      <Card>
        <CardHeader
          title="Current Pointing"
          avatar={<SlewIcon />}
          action={
            <Tooltip title="Refresh">
              <IconButton size="small">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          }
        />
        <CardContent>
          {currentPointing ? (
            <Stack spacing={2}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Position
                </Typography>
                <Typography variant="h6">
                  RA: {currentPointing.ra.toFixed(4)}°, Dec: {currentPointing.dec.toFixed(4)}°
                </Typography>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Elevation
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography variant="body1">
                    {calculateElevation(currentPointing.ra, currentPointing.dec).toFixed(1)}°
                  </Typography>
                  <Chip
                    label={
                      getElevationStatus(
                        calculateElevation(currentPointing.ra, currentPointing.dec)
                      ).message
                    }
                    color={
                      getElevationStatus(
                        calculateElevation(currentPointing.ra, currentPointing.dec)
                      ).color
                    }
                    size="small"
                  />
                </Box>
              </Box>
            </Stack>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No current pointing data
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Quick Slew Control */}
      <Card>
        <CardHeader title="Quick Slew" avatar={<NavigationIcon />} />
        <CardContent>
          <Stack spacing={2}>
            <Box display="flex" gap={2}>
              <TextField
                label="RA (degrees)"
                value={targetRA}
                onChange={(e) => setTargetRA(e.target.value)}
                size="small"
                type="number"
                inputProps={{ min: 0, max: 360, step: 0.1 }}
                fullWidth
              />
              <TextField
                label="Dec (degrees)"
                value={targetDec}
                onChange={(e) => setTargetDec(e.target.value)}
                size="small"
                type="number"
                inputProps={{ min: -90, max: 90, step: 0.1 }}
                fullWidth
              />
            </Box>
            <Button
              variant="contained"
              onClick={handleSlew}
              disabled={!targetRA || !targetDec}
              startIcon={<SlewIcon />}
            >
              Send Slew Command
            </Button>
            {slewStatus && (
              <Alert severity={slewStatus.includes("Invalid") ? "error" : "info"}>
                {slewStatus}
              </Alert>
            )}
          </Stack>
        </CardContent>
      </Card>

      {/* Upcoming Scans / Observable Targets */}
      <Card>
        <CardHeader
          title="Observable Calibrators"
          avatar={<ScheduleIcon />}
          subheader="Sorted by elevation (best observing conditions first)"
        />
        <CardContent>
          {upcomingScans.length > 0 ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Calibrator</TableCell>
                    <TableCell align="right">RA (°)</TableCell>
                    <TableCell align="right">Dec (°)</TableCell>
                    <TableCell align="right">Elevation</TableCell>
                    <TableCell align="right">Flux (Jy)</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {upcomingScans.map((scan, idx) => (
                    <TableRow key={idx}>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {scan.name}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">{scan.ra?.toFixed(4) || "N/A"}</TableCell>
                      <TableCell align="right">{scan.dec?.toFixed(4) || "N/A"}</TableCell>
                      <TableCell align="right">
                        <Box display="flex" alignItems="center" gap={0.5}>
                          {scan.elevation.toFixed(1)}°
                          {scan.elevationStatus.status === "poor" && (
                            <WarningIcon fontSize="small" color="error" />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell align="right">{(scan.flux * 1000).toFixed(1)} mJy</TableCell>
                      <TableCell>
                        <Chip
                          label={scan.elevationStatus.message}
                          color={scan.elevationStatus.color}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          onClick={() => {
                            setTargetRA(scan.ra?.toFixed(4) || "");
                            setTargetDec(scan.dec?.toFixed(4) || "");
                          }}
                          disabled={scan.elevationStatus.status === "unobservable"}
                        >
                          Select
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Alert severity="info">No calibrator data available</Alert>
          )}
        </CardContent>
      </Card>

      {/* Elevation Limits Summary */}
      <Card>
        <CardHeader title="Observing Constraints" avatar={<VisibilityIcon />} />
        <CardContent>
          <Stack spacing={2}>
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Elevation Constraints
              </Typography>
              <Stack direction="row" spacing={1}>
                <Chip label="Optimal: > 45°" color="success" size="small" />
                <Chip label="Acceptable: 30-45°" color="warning" size="small" />
                <Chip label="Poor: 15-30°" color="error" size="small" />
                <Chip label="Unobservable: < 15°" size="small" />
              </Stack>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Current Observability
              </Typography>
              <Box>
                {upcomingScans.length > 0 && (
                  <>
                    <Typography variant="body2">
                      {upcomingScans.filter((s) => s.elevationStatus.status === "good").length}{" "}
                      targets in optimal range
                    </Typography>
                    <Typography variant="body2">
                      {upcomingScans.filter((s) => s.elevationStatus.status === "marginal").length}{" "}
                      targets in acceptable range
                    </Typography>
                    <Typography variant="body2">
                      {upcomingScans.filter((s) => s.elevationStatus.status === "poor").length}{" "}
                      targets in poor range
                    </Typography>
                  </>
                )}
              </Box>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}

// Fix import name
const NavigationIcon = SlewIcon;
