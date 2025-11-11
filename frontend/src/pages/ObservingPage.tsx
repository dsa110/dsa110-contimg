/**
 * Observing Page
 * Real-time telescope status and observing plan
 */
import { useState, useMemo } from 'react';
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
  CircularProgress,
  Tabs,
  Tab,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  RadioButtonChecked as PointIcon,
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';
import { usePointingHistory, useCalibratorMatches, usePipelineStatus } from '../api/queries';
import PointingVisualization from '../components/PointingVisualization';
import Plot from 'react-plotly.js';
import type { Data, Layout } from 'plotly.js';
import dayjs from 'dayjs';

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
    const startMjd = (startDate.getTime() / 86400000) + 40587;
    const endMjd = (now.getTime() / 86400000) + 40587;
    return { startMjd, endMjd };
  }, []);

  const {
    data: pointingHistory,
    isLoading: pointingLoading,
    error: pointingError,
  } = usePointingHistory(startMjd, endMjd);

  const {
    data: calibratorMatches,
    isLoading: calibratorLoading,
  } = useCalibratorMatches(null, 'vla', 1.5);

  const historyData = pointingHistory?.items || [];
  const calibratorData = calibratorMatches?.items || [];

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
    if (!calibratorData.length) return { data: [], layout: {} };

    const data: Data[] = [];
    const calibratorNames = new Set(calibratorData.map((m: any) => m.name).filter(Boolean));

    calibratorNames.forEach((name) => {
      const matches = calibratorData.filter((m: any) => m.name === name);
      if (matches.length > 1) {
        const times = matches.map((m: any) => new Date(m.timestamp || Date.now()));
        const fluxes = matches.map((m: any) => m.flux_jy * 1000); // Convert to mJy
        const elevations = matches.map((m: any) => m.elevation_deg || 0);

        data.push({
          type: 'scatter',
          mode: 'lines+markers',
          name: name,
          x: times,
          y: fluxes,
          text: elevations.map((e) => `Elevation: ${e.toFixed(1)}°`),
          hovertemplate: `${name}<br>Flux: %{y:.2f} mJy<br>%{text}<extra></extra>`,
        });
      }
    });

    const layout: Partial<Layout> = {
      title: 'Calibrator Flux vs Time',
      xaxis: { title: 'Time' },
      yaxis: { title: 'Flux (mJy)' },
      hovermode: 'closest',
      template: 'plotly_dark',
    };

    return { data, layout };
  }, [calibratorData]);

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h3" gutterBottom sx={{ mb: 4 }}>
        Observing Status
      </Typography>

      {pointingLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {pointingError && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Unable to load pointing history. Some features may be unavailable.
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Current Status Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardHeader
              title="Current Status"
              avatar={<PointIcon />}
            />
            <CardContent>
              {currentPointing ? (
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Current Pointing
                    </Typography>
                    <Typography variant="h6">
                      RA: {currentPointing.ra.toFixed(4)}°
                    </Typography>
                    <Typography variant="h6">
                      Dec: {currentPointing.dec.toFixed(4)}°
                    </Typography>
                  </Box>
                  <Divider />
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Last Update
                    </Typography>
                    <Typography variant="body1">
                      {dayjs(currentPointing.timestamp).format('YYYY-MM-DD HH:mm:ss')}
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
            <CardHeader
              title="Calibrator Tracking"
              avatar={<ScheduleIcon />}
            />
            <CardContent>
              {calibratorLoading ? (
                <CircularProgress />
              ) : calibratorData.length > 0 ? (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Calibrator</TableCell>
                        <TableCell>RA (deg)</TableCell>
                        <TableCell>Dec (deg)</TableCell>
                        <TableCell>Flux (mJy)</TableCell>
                        <TableCell>Last Seen</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {calibratorData.slice(0, 10).map((match: any, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell>{match.name || 'Unknown'}</TableCell>
                          <TableCell>{match.ra_deg?.toFixed(4) || 'N/A'}</TableCell>
                          <TableCell>{match.dec_deg?.toFixed(4) || 'N/A'}</TableCell>
                          <TableCell>
                            {match.flux_jy ? (match.flux_jy * 1000).toFixed(2) : 'N/A'}
                          </TableCell>
                          <TableCell>
                            {match.timestamp
                              ? dayjs(match.timestamp).format('MM-DD HH:mm')
                              : 'N/A'}
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
              <CardHeader
                title="Calibrator Flux vs Time"
                avatar={<TrendingUpIcon />}
              />
              <CardContent>
                <Plot
                  data={calibratorPlotData.data}
                  layout={calibratorPlotData.layout}
                  style={{ width: '100%', height: '400px' }}
                />
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Container>
  );
}

