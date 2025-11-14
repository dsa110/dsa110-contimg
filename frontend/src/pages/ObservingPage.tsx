/**
 * Observing Page
 * Real-time telescope status and observing plan
 */
import { useState, useMemo } from "react";
import {
  Container,
  Typography,
  Paper,
  Box,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Stack,
  Chip,
  Alert,
  Tabs,
  Tab,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import {
  RadioButtonChecked as PointIcon,
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
} from "@mui/icons-material";
import { usePointingHistory, usePipelineStatus } from "../api/queries";
import { apiClient } from "../api/client";
import { useQuery } from "@tanstack/react-query";
import PointingVisualization from "../components/PointingVisualization";
import { SkeletonLoader } from "../components/SkeletonLoader";
import Plot from "react-plotly.js";
import type { Data, Layout } from "plotly.js";
import dayjs from "dayjs";
import PageBreadcrumbs from "../components/PageBreadcrumbs";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

export default function ObservingPage() {
  const [tabValue, setTabValue] = useState(0);
  const { data: status } = usePipelineStatus();

  // Calculate MJD range for last 6 hours
  const { startMjd, endMjd } = useMemo(() => {
    const now = new Date();
    const startDate = new Date(now.getTime() - 6 * 60 * 60 * 1000);
    const startMjd = startDate.getTime() / 86400000 + 40587;
    const endMjd = now.getTime() / 86400000 + 40587;
    return { startMjd, endMjd };
  }, []);

  const {
    data: pointingHistory,
    isLoading: pointingLoading,
    error: pointingError,
  } = usePointingHistory(startMjd, endMjd);

  // Fetch recent calibrator matches
  const { data: calibratorMatches, isLoading: calibratorLoading } = useQuery({
    queryKey: ["calibrator-matches", "recent"],
    queryFn: async () => {
      const response = await apiClient.get("/api/calibrator_matches?limit=50&matched_only=true");
      return response.data;
    },
    refetchInterval: 60000, // Refresh every minute
  });

  const historyData = pointingHistory?.items || [];
  const calibratorData = calibratorMatches?.items || [];

  // Extract individual calibrator matches from groups
  const allCalibratorMatches = useMemo(() => {
    const matches: any[] = [];
    calibratorData.forEach((group: any) => {
      if (group.matches && Array.isArray(group.matches)) {
        group.matches.forEach((match: any) => {
          matches.push({
            ...match,
            timestamp: group.received_at || group.last_update,
            group_id: group.group_id,
          });
        });
      }
    });
    return matches;
  }, [calibratorData]);

  // Get current pointing from most recent history entry
  const currentPointing = useMemo(() => {
    if (historyData.length > 0) {
      const latest = historyData[historyData.length - 1];
      return {
        ra: latest.ra_deg,
        dec: latest.dec_deg,
        timestamp: latest.timestamp,
      };
    }
    return null;
  }, [historyData]);

  // Prepare calibrator flux vs elevation plot
  const calibratorPlotData = useMemo(() => {
    if (!allCalibratorMatches.length) return { data: [], layout: {} };

    const data: Data[] = [];
    const calibratorNames = new Set(allCalibratorMatches.map((m: any) => m.name).filter(Boolean));

    calibratorNames.forEach((name) => {
      const matches = allCalibratorMatches.filter((m: any) => m.name === name);
      if (matches.length > 1) {
        const times = matches.map((m: any) => new Date(m.timestamp || Date.now()));
        const fluxes = matches.map((m: any) => (m.weighted_flux || m.flux_jy || 0) * 1000); // Convert to mJy

        data.push({
          type: "scatter",
          mode: "lines+markers",
          name: name,
          x: times,
          y: fluxes,
          hovertemplate: `${name}<br>Flux: %{y:.2f} mJy<br>Time: %{x}<extra></extra>`,
        });
      }
    });

    const layout: Partial<Layout> = {
      title: "Calibrator Flux vs Time",
      xaxis: { title: "Time" },
      yaxis: { title: "Flux (mJy)" },
      hovermode: "closest",
      template: "plotly_dark",
    };

    return { data, layout };
  }, [allCalibratorMatches]);

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h2" component="h2" gutterBottom sx={{ mb: 4 }}>
          Observing Status
        </Typography>

        {pointingLoading && <SkeletonLoader variant="cards" rows={2} />}

        {pointingError && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            Unable to load pointing history. Some features may be unavailable.
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* Current Status Panel */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardHeader title="Current Status" avatar={<PointIcon />} />
              <CardContent>
                {currentPointing ? (
                  <Stack spacing={2}>
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Current Pointing
                      </Typography>
                      <Typography variant="h6">RA: {currentPointing.ra.toFixed(4)}°</Typography>
                      <Typography variant="h6">Dec: {currentPointing.dec.toFixed(4)}°</Typography>
                    </Box>
                    <Divider />
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Last Update
                      </Typography>
                      <Typography variant="body1">
                        {dayjs(currentPointing.timestamp).format("YYYY-MM-DD HH:mm:ss")}
                      </Typography>
                    </Box>
                    <Divider />
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Pipeline Status
                      </Typography>
                      <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                        <Chip
                          label={`Pending: ${status?.queue.pending || 0}`}
                          size="small"
                          color="warning"
                        />
                        <Chip
                          label={`In Progress: ${status?.queue.in_progress || 0}`}
                          size="small"
                          color="info"
                        />
                        <Chip
                          label={`Completed: ${status?.queue.completed || 0}`}
                          size="small"
                          color="success"
                        />
                      </Stack>
                    </Box>
                  </Stack>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No current pointing data available
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Calibrator Tracking */}
          <Grid item xs={12} md={8}>
            <Card>
              <CardHeader title="Calibrator Tracking" avatar={<ScheduleIcon />} />
              <CardContent>
                {calibratorLoading ? (
                  <SkeletonLoader variant="table" rows={3} columns={4} />
                ) : allCalibratorMatches.length > 0 ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Calibrator</TableCell>
                          <TableCell>RA (deg)</TableCell>
                          <TableCell>Dec (deg)</TableCell>
                          <TableCell>Flux (mJy)</TableCell>
                          <TableCell>Separation (°)</TableCell>
                          <TableCell>Last Seen</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {allCalibratorMatches.slice(0, 10).map((match: any, idx: number) => (
                          <TableRow key={idx}>
                            <TableCell>{match.name || "Unknown"}</TableCell>
                            <TableCell>{match.ra_deg?.toFixed(4) || "N/A"}</TableCell>
                            <TableCell>{match.dec_deg?.toFixed(4) || "N/A"}</TableCell>
                            <TableCell>
                              {(match.weighted_flux || match.flux_jy || 0) * 1000 > 0
                                ? ((match.weighted_flux || match.flux_jy) * 1000).toFixed(2)
                                : "N/A"}
                            </TableCell>
                            <TableCell>{match.sep_deg?.toFixed(3) || "N/A"}</TableCell>
                            <TableCell>
                              {match.timestamp
                                ? dayjs(match.timestamp).format("MM-DD HH:mm")
                                : "N/A"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No recent calibrator matches
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Pointing Visualization */}
          <Grid item xs={12}>
            <Card>
              <CardHeader title="Pointing History" />
              <CardContent>
                <PointingVisualization height={500} showHistory={true} historyDays={7} />
              </CardContent>
            </Card>
          </Grid>

          {/* Calibrator Flux Plot */}
          {calibratorPlotData.data.length > 0 && (
            <Grid item xs={12}>
              <Card>
                <CardHeader title="Calibrator Flux vs Time" avatar={<TrendingUpIcon />} />
                <CardContent>
                  <Plot
                    data={calibratorPlotData.data}
                    layout={calibratorPlotData.layout}
                    style={{ width: "100%", height: "400px" }}
                  />
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      </Container>
    </>
  );
}
