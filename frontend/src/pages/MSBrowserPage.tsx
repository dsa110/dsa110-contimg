/**
 * Unified MS Browser Page
 * Comprehensive Measurement Set browser with inspection tools
 * Similar to CASA's listobs functionality
 */
import { useState, useMemo } from "react";
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Button,
  Stack,
  Alert,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  ExpandMore,
  Visibility,
  Assessment,
  Settings,
  CompareArrows,
  Download,
  Refresh,
  Info,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useMSList, useMSMetadata } from "../api/queries";
import MSTable from "../components/MSTable";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import type { MSListEntry, MSMetadata } from "../api/types";

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

function MSInspectionPanel({
  msPath,
  metadata,
}: {
  msPath: string;
  metadata: MSMetadata | undefined;
}) {
  if (!metadata) {
    return (
      <Alert severity="info">Select an MS to view inspection details (listobs-like summary)</Alert>
    );
  }

  return (
    <Grid container spacing={2}>
      {/* Overview */}
      <Grid size={12}>
        <Card>
          <CardHeader title="MS Overview" />
          <CardContent>
            <Grid container spacing={2}>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Time Range
                </Typography>
                <Typography variant="body1">
                  {metadata.start_time} → {metadata.end_time}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Duration: {metadata.duration_sec?.toFixed(1)}s
                </Typography>
              </Grid>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Frequency Coverage
                </Typography>
                <Typography variant="body1">
                  {metadata.freq_min_ghz?.toFixed(3)} - {metadata.freq_max_ghz?.toFixed(3)} GHz
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {metadata.num_channels} channels
                </Typography>
              </Grid>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Size
                </Typography>
                <Typography variant="body1">{metadata.size_gb?.toFixed(2) || "N/A"} GB</Typography>
              </Grid>
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Calibration Status
                </Typography>
                <Chip
                  label={metadata.calibrated ? "Calibrated" : "Uncalibrated"}
                  color={metadata.calibrated ? "success" : "default"}
                  size="small"
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Grid>
      {/* Antennas */}
      {metadata.antennas && metadata.antennas.length > 0 && (
        <Grid
          size={{
            xs: 12,
            md: 6,
          }}
        >
          <Card>
            <CardHeader title={`Antennas (${metadata.antennas.length})`} />
            <CardContent>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>ID</TableCell>
                      <TableCell>Name</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {metadata.antennas.map((ant) => (
                      <TableRow key={ant.antenna_id}>
                        <TableCell>{ant.antenna_id}</TableCell>
                        <TableCell>{ant.name}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      )}
      {/* Fields */}
      {metadata.fields && metadata.fields.length > 0 && (
        <Grid
          size={{
            xs: 12,
            md: 6,
          }}
        >
          <Card>
            <CardHeader title={`Fields (${metadata.fields.length})`} />
            <CardContent>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>ID</TableCell>
                      <TableCell>Name</TableCell>
                      <TableCell>RA (deg)</TableCell>
                      <TableCell>Dec (deg)</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {metadata.fields.map((field) => (
                      <TableRow key={field.field_id}>
                        <TableCell>{field.field_id}</TableCell>
                        <TableCell>{field.name}</TableCell>
                        <TableCell>{field.ra_deg.toFixed(4)}</TableCell>
                        <TableCell>{field.dec_deg.toFixed(4)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      )}
      {/* Flagging Statistics */}
      {metadata.flagging_stats && (
        <Grid size={12}>
          <Card>
            <CardHeader title="Flagging Statistics" />
            <CardContent>
              <Typography variant="body2" gutterBottom>
                Total flagged: {((metadata.flagging_stats.total_fraction ?? 0) * 100).toFixed(1)}%
              </Typography>
              {metadata.flagging_stats.per_antenna &&
                Object.keys(metadata.flagging_stats.per_antenna).length > 0 && (
                  <Accordion>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Typography variant="body2">Per-Antenna Flagging</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Antenna</TableCell>
                              <TableCell align="right">Flagged %</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {Object.entries(metadata.flagging_stats.per_antenna).map(
                              ([antId, frac]) => {
                                const ant = metadata.antennas?.find(
                                  (a) => String(a.antenna_id) === antId
                                );
                                return (
                                  <TableRow key={antId}>
                                    <TableCell>
                                      {ant ? `${ant.name} (${antId})` : `Antenna ${antId}`}
                                    </TableCell>
                                    <TableCell align="right">
                                      {((frac as number) * 100).toFixed(1)}%
                                    </TableCell>
                                  </TableRow>
                                );
                              }
                            )}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </AccordionDetails>
                  </Accordion>
                )}
            </CardContent>
          </Card>
        </Grid>
      )}
      {/* Data Columns */}
      {metadata.data_columns && metadata.data_columns.length > 0 && (
        <Grid size={12}>
          <Card>
            <CardHeader title="Data Columns" />
            <CardContent>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                {metadata.data_columns.map((col) => (
                  <Chip key={col} label={col} size="small" />
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      )}
    </Grid>
  );
}

export default function MSBrowserPage() {
  const navigate = useNavigate();
  const [selectedMS, setSelectedMS] = useState<string>("");
  const [tabValue, setTabValue] = useState(0);
  const [compareMS, setCompareMS] = useState<string>("");

  const { data: msList, refetch: refetchMS } = useMSList({
    scan: true,
    scan_dir: "/scratch/dsa110-contimg/ms",
  });
  const { data: msMetadata } = useMSMetadata(selectedMS);
  const { data: compareMetadata } = useMSMetadata(compareMS);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleMSSelect = (ms: MSListEntry) => {
    setSelectedMS(ms.path);
  };

  // Quick quality metrics
  const qualityMetrics = useMemo(() => {
    if (!msMetadata) return null;

    const metrics = {
      calibrated: msMetadata.calibrated,
      flaggingPercent: msMetadata.flagging_stats
        ? (msMetadata.flagging_stats.total_fraction ?? 0) * 100
        : 0,
      numAntennas: msMetadata.antennas?.length || msMetadata.num_antennas || 0,
      numFields: msMetadata.fields?.length || msMetadata.num_fields || 0,
      hasCalibrator: msList?.items.find((ms) => ms.path === selectedMS)?.has_calibrator || false,
    };

    return metrics;
  }, [msMetadata, msList, selectedMS]);

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
            Measurement Set Browser
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Unified MS browser with inspection tools (CASA listobs-like functionality)
          </Typography>
        </Box>

        {/* MS Selection */}
        <Paper sx={{ mb: 3 }}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
            <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
              <Typography variant="h6">Measurement Sets</Typography>
              <Stack direction="row" spacing={1}>
                <Tooltip title="Refresh MS list">
                  <IconButton onClick={() => refetchMS()} size="small">
                    <Refresh />
                  </IconButton>
                </Tooltip>
                {selectedMS && (
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<Visibility />}
                    onClick={() => navigate(`/data/ms/${encodeURIComponent(selectedMS)}`)}
                  >
                    View Details
                  </Button>
                )}
                {selectedMS && (
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<Settings />}
                    onClick={() => navigate("/calibration")}
                  >
                    Calibrate
                  </Button>
                )}
              </Stack>
            </Stack>
          </Box>
          <Box sx={{ p: 2 }}>
            <MSTable
              data={msList?.items || []}
              total={msList?.total}
              filtered={msList?.filtered}
              selected={selectedMS ? [selectedMS] : []}
              onSelectionChange={(paths) => {
                if (paths.length > 0) {
                  setSelectedMS(paths[0]);
                } else {
                  setSelectedMS("");
                }
              }}
              onMSClick={handleMSSelect}
              onRefresh={refetchMS}
            />
          </Box>
        </Paper>

        {/* Quick Quality Metrics */}
        {selectedMS && qualityMetrics && (
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid
              size={{
                xs: 12,
                sm: 6,
                md: 3,
              }}
            >
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary" gutterBottom>
                    Calibration Status
                  </Typography>
                  <Chip
                    label={qualityMetrics.calibrated ? "Calibrated" : "Uncalibrated"}
                    color={qualityMetrics.calibrated ? "success" : "default"}
                    size="small"
                  />
                </CardContent>
              </Card>
            </Grid>
            <Grid
              size={{
                xs: 12,
                sm: 6,
                md: 3,
              }}
            >
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary" gutterBottom>
                    Flagging
                  </Typography>
                  <Typography variant="h6">{qualityMetrics.flaggingPercent.toFixed(1)}%</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid
              size={{
                xs: 12,
                sm: 6,
                md: 3,
              }}
            >
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary" gutterBottom>
                    Antennas
                  </Typography>
                  <Typography variant="h6">{qualityMetrics.numAntennas}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid
              size={{
                xs: 12,
                sm: 6,
                md: 3,
              }}
            >
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary" gutterBottom>
                    Fields
                  </Typography>
                  <Typography variant="h6">{qualityMetrics.numFields}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Tabs: Inspection | Comparison | Related Products */}
        <Paper>
          <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
            <Tabs value={tabValue} onChange={handleTabChange}>
              <Tab label="MS Inspection" icon={<Info />} iconPosition="start" />
              <Tab label="MS Comparison" icon={<CompareArrows />} iconPosition="start" />
              <Tab label="Related Products" icon={<Assessment />} iconPosition="start" />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <Box sx={{ p: 3 }}>
              <MSInspectionPanel msPath={selectedMS} metadata={msMetadata} />
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Box sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Compare Measurement Sets
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Select two MSs to compare their properties side-by-side
              </Typography>
              <Grid container spacing={2}>
                <Grid
                  size={{
                    xs: 12,
                    md: 6,
                  }}
                >
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      MS 1
                    </Typography>
                    <MSTable
                      data={msList?.items || []}
                      total={msList?.total}
                      filtered={msList?.filtered}
                      selected={selectedMS ? [selectedMS] : []}
                      onSelectionChange={(paths) => {
                        if (paths.length > 0) {
                          setSelectedMS(paths[0]);
                        }
                      }}
                      onMSClick={handleMSSelect}
                      onRefresh={refetchMS}
                    />
                  </Paper>
                </Grid>
                <Grid
                  size={{
                    xs: 12,
                    md: 6,
                  }}
                >
                  <Paper sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      MS 2 (for comparison)
                    </Typography>
                    <MSTable
                      data={msList?.items || []}
                      total={msList?.total}
                      filtered={msList?.filtered}
                      selected={compareMS ? [compareMS] : []}
                      onSelectionChange={(paths) => {
                        if (paths.length > 0) {
                          setCompareMS(paths[0]);
                        }
                      }}
                      onMSClick={(ms) => setCompareMS(ms.path)}
                      onRefresh={refetchMS}
                    />
                  </Paper>
                </Grid>
                {selectedMS && compareMS && (
                  <Grid size={12}>
                    <Paper sx={{ p: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Comparison
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Property</TableCell>
                              <TableCell align="right">MS 1</TableCell>
                              <TableCell align="right">MS 2</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            <TableRow>
                              <TableCell>Calibrated</TableCell>
                              <TableCell align="right">
                                {msMetadata?.calibrated ? "Yes" : "No"}
                              </TableCell>
                              <TableCell align="right">
                                {compareMetadata?.calibrated ? "Yes" : "No"}
                              </TableCell>
                            </TableRow>
                            <TableRow>
                              <TableCell>Antennas</TableCell>
                              <TableCell align="right">
                                {msMetadata?.antennas?.length || msMetadata?.num_antennas || "N/A"}
                              </TableCell>
                              <TableCell align="right">
                                {compareMetadata?.antennas?.length ||
                                  compareMetadata?.num_antennas ||
                                  "N/A"}
                              </TableCell>
                            </TableRow>
                            <TableRow>
                              <TableCell>Fields</TableCell>
                              <TableCell align="right">
                                {msMetadata?.fields?.length || msMetadata?.num_fields || "N/A"}
                              </TableCell>
                              <TableCell align="right">
                                {compareMetadata?.fields?.length ||
                                  compareMetadata?.num_fields ||
                                  "N/A"}
                              </TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Paper>
                  </Grid>
                )}
              </Grid>
            </Box>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Box sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Related Products
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Products derived from this Measurement Set
              </Typography>
              {selectedMS ? (
                <Alert severity="info">
                  Related products (calibration tables, images, etc.) would be listed here. Navigate
                  to the Data Browser to see all related products.
                </Alert>
              ) : (
                <Alert severity="info">Select an MS to view related products</Alert>
              )}
            </Box>
          </TabPanel>
        </Paper>
      </Container>
    </>
  );
}
