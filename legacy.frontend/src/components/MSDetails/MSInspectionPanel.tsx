/**
 * MS Inspection Panel
 * Displays detailed MS metadata in a listobs-like format with CASA logs access
 */
import {
  Grid,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Stack,
  Alert,
  Box,
  Button,
  Tooltip,
  IconButton,
} from "@mui/material";
import {
  ExpandMore,
  Description as LogIcon,
  Assessment as StatsIcon,
  Refresh as RefreshIcon,
  ContentCopy as CopyIcon,
} from "@mui/icons-material";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../api/client";
import type { MSMetadata } from "../../api/types";

interface MSInspectionPanelProps {
  msPath?: string;
  metadata: MSMetadata | undefined;
}

export function MSInspectionPanel({ msPath, metadata }: MSInspectionPanelProps) {
  const [expandedLogs, setExpandedLogs] = useState(false);
  const [expandedListobs, setExpandedListobs] = useState(false);

  // Fetch CASA logs for this MS (if available)
  const {
    data: casaLogs,
    isLoading: logsLoading,
    refetch: refetchLogs,
  } = useQuery({
    queryKey: ["casa-logs", msPath],
    queryFn: async () => {
      if (!msPath) return null;
      try {
        const response = await apiClient.get(`/api/ms/${encodeURIComponent(msPath)}/logs`);
        return response.data;
      } catch (error) {
        // Logs may not exist for all MS
        return null;
      }
    },
    enabled: !!msPath && expandedLogs,
    retry: false,
  });

  // Fetch listobs-style output (if available)
  const {
    data: listobsOutput,
    isLoading: listobsLoading,
    refetch: refetchListobs,
  } = useQuery({
    queryKey: ["listobs", msPath],
    queryFn: async () => {
      if (!msPath) return null;
      try {
        const response = await apiClient.get(`/api/ms/${encodeURIComponent(msPath)}/listobs`);
        return response.data;
      } catch (error) {
        return null;
      }
    },
    enabled: !!msPath && expandedListobs,
    retry: false,
  });

  const handleCopyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

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
              <Grid
                size={{
                  xs: 12,
                  md: 6,
                }}
              >
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Imaging Backend
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  {metadata.imaging_backend || metadata.imager ? (
                    <>
                      <Chip
                        label={
                          metadata.imaging_backend === "wsclean"
                            ? "WSClean"
                            : metadata.imaging_backend === "tclean"
                              ? "tclean (CASA)"
                              : metadata.imager || "Unknown"
                        }
                        color={
                          metadata.imaging_backend === "wsclean"
                            ? "primary"
                            : metadata.imaging_backend === "tclean"
                              ? "secondary"
                              : "default"
                        }
                        size="small"
                      />
                      <Typography variant="caption" color="text.secondary">
                        {metadata.imaging_backend === "wsclean"
                          ? "Fast, efficient imaging"
                          : metadata.imaging_backend === "tclean"
                            ? "CASA-based imaging"
                            : ""}
                      </Typography>
                    </>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Not imaged yet
                    </Typography>
                  )}
                </Box>
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
      {/* CASA Logs Access */}
      {msPath && (
        <Grid size={12}>
          <Card>
            <CardHeader
              title="CASA Logs & Processing Output"
              avatar={<LogIcon />}
              action={
                expandedLogs && (
                  <Tooltip title="Refresh logs">
                    <IconButton onClick={() => refetchLogs()} size="small">
                      <RefreshIcon />
                    </IconButton>
                  </Tooltip>
                )
              }
            />
            <CardContent>
              <Accordion
                expanded={expandedLogs}
                onChange={(_, isExpanded) => setExpandedLogs(isExpanded)}
              >
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="body2">View CASA task logs</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {logsLoading ? (
                    <Typography variant="body2" color="text.secondary">
                      Loading logs...
                    </Typography>
                  ) : casaLogs ? (
                    <Box>
                      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
                        <Button
                          size="small"
                          startIcon={<CopyIcon />}
                          onClick={() => handleCopyToClipboard(casaLogs.content || casaLogs)}
                        >
                          Copy
                        </Button>
                      </Box>
                      <Box
                        sx={{
                          fontFamily: "monospace",
                          fontSize: "0.75rem",
                          bgcolor: "background.paper",
                          p: 2,
                          borderRadius: 1,
                          maxHeight: 400,
                          overflow: "auto",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-all",
                        }}
                      >
                        {casaLogs.content || casaLogs}
                      </Box>
                    </Box>
                  ) : (
                    <Alert severity="info">
                      No CASA logs available for this MS. Logs are generated during calibration and
                      imaging tasks.
                    </Alert>
                  )}
                </AccordionDetails>
              </Accordion>
            </CardContent>
          </Card>
        </Grid>
      )}

      {/* Listobs-style Output */}
      {msPath && (
        <Grid size={12}>
          <Card>
            <CardHeader
              title="Detailed MS Summary (listobs)"
              avatar={<StatsIcon />}
              action={
                expandedListobs && (
                  <Tooltip title="Refresh">
                    <IconButton onClick={() => refetchListobs()} size="small">
                      <RefreshIcon />
                    </IconButton>
                  </Tooltip>
                )
              }
            />
            <CardContent>
              <Accordion
                expanded={expandedListobs}
                onChange={(_, isExpanded) => setExpandedListobs(isExpanded)}
              >
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="body2">
                    View comprehensive listobs-style metadata summary
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {listobsLoading ? (
                    <Typography variant="body2" color="text.secondary">
                      Loading metadata...
                    </Typography>
                  ) : listobsOutput ? (
                    <Box>
                      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
                        <Button
                          size="small"
                          startIcon={<CopyIcon />}
                          onClick={() =>
                            handleCopyToClipboard(listobsOutput.content || listobsOutput)
                          }
                        >
                          Copy
                        </Button>
                      </Box>
                      <Box
                        sx={{
                          fontFamily: "monospace",
                          fontSize: "0.75rem",
                          bgcolor: "background.paper",
                          p: 2,
                          borderRadius: 1,
                          maxHeight: 500,
                          overflow: "auto",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {listobsOutput.content || listobsOutput}
                      </Box>
                    </Box>
                  ) : (
                    <Alert severity="info">
                      Listobs summary not available. This requires backend API support for
                      generating detailed MS metadata.
                    </Alert>
                  )}
                </AccordionDetails>
              </Accordion>
            </CardContent>
          </Card>
        </Grid>
      )}

      {/* Flagging Statistics */}
      {metadata.flagging_stats && (
        <Grid size={12}>
          <Card>
            <CardHeader title="Flagging & RFI Statistics" />
            <CardContent>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Total flagged:{" "}
                    {((metadata.flagging_stats.total_fraction ?? 0) * 100).toFixed(1)}%
                  </Typography>
                  {metadata.flagging_stats.rfi_percentage !== undefined && (
                    <Typography variant="body2" gutterBottom>
                      RFI detected: {metadata.flagging_stats.rfi_percentage.toFixed(1)}%
                    </Typography>
                  )}
                </Box>

                {/* AOFlagger Information */}
                {(metadata.flagging_stats.aoflagger_version ||
                  metadata.flagging_stats.aoflagger_strategy) && (
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      AOFlagger Configuration
                    </Typography>
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      {metadata.flagging_stats.aoflagger_version && (
                        <Chip
                          label={`Version ${metadata.flagging_stats.aoflagger_version}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                      {metadata.flagging_stats.aoflagger_strategy && (
                        <Chip
                          label={metadata.flagging_stats.aoflagger_strategy}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Box>
                )}
                {/* Per-Antenna Flagging */}
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

                {/* Baseline RFI Statistics */}
                {metadata.flagging_stats.baseline_rfi_stats &&
                  Object.keys(metadata.flagging_stats.baseline_rfi_stats).length > 0 && (
                    <Accordion>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Typography variant="body2">Baseline RFI Statistics</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <TableContainer>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Baseline</TableCell>
                                <TableCell align="right">RFI %</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {Object.entries(metadata.flagging_stats.baseline_rfi_stats)
                                .sort(([, a], [, b]) => (b as number) - (a as number))
                                .slice(0, 20)
                                .map(([baseline, rfi]) => (
                                  <TableRow key={baseline}>
                                    <TableCell>{baseline}</TableCell>
                                    <TableCell align="right">
                                      {((rfi as number) * 100).toFixed(1)}%
                                    </TableCell>
                                  </TableRow>
                                ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                        {Object.keys(metadata.flagging_stats.baseline_rfi_stats).length > 20 && (
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                            Showing top 20 most affected baselines
                          </Typography>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  )}

                {/* Frequency RFI Statistics */}
                {metadata.flagging_stats.frequency_rfi_stats &&
                  Object.keys(metadata.flagging_stats.frequency_rfi_stats).length > 0 && (
                    <Accordion>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Typography variant="body2">Frequency RFI Statistics</Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="caption" color="text.secondary" gutterBottom>
                          RFI contamination by frequency channel
                        </Typography>
                        <TableContainer>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Channel</TableCell>
                                <TableCell align="right">RFI %</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {Object.entries(metadata.flagging_stats.frequency_rfi_stats)
                                .sort(([, a], [, b]) => (b as number) - (a as number))
                                .slice(0, 15)
                                .map(([channel, rfi]) => (
                                  <TableRow key={channel}>
                                    <TableCell>Ch {channel}</TableCell>
                                    <TableCell align="right">
                                      {((rfi as number) * 100).toFixed(1)}%
                                    </TableCell>
                                  </TableRow>
                                ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                        {Object.keys(metadata.flagging_stats.frequency_rfi_stats).length > 15 && (
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                            Showing top 15 most affected channels
                          </Typography>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  )}
              </Stack>
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
