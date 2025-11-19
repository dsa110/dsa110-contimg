/**
 * Source Detail Page
 *
 * VAST-inspired source detail page with three-column layout:
 * - Column 1: Source details and metadata
 * - Column 2: Sky visualization (Aladin Lite)
 * - Column 3: Comments/Annotations
 *
 * Full-width sections below:
 * - Light curve visualization
 * - Detections table (using GenericTable)
 * - Related sources table
 *
 * Inspired by VAST's source_detail.html
 *
 * @module pages/SourceDetailPage
 */

import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Container,
  Typography,
  Button,
  Stack,
  Chip,
  Divider,
  Collapse,
  IconButton,
  Alert,
  Card,
  CardContent,
  CardHeader,
  Tooltip,
  Snackbar,
} from "@mui/material";
import { SkeletonLoader } from "../components/SkeletonLoader";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Link as LinkIcon,
  ContentCopy as ContentCopyIcon,
} from "@mui/icons-material";
import { useSourceDetail } from "../api/queries";
import GenericTable from "../components/GenericTable";
import type { TableColumn } from "../components/GenericTable";
import { Box } from "@mui/material";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import { formatRA, formatDec, copyToClipboard } from "../utils/coordinateUtils";
import { formatDateTime } from "../utils/dateUtils";

export default function SourceDetailPage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const navigate = useNavigate();
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    lightCurve: true,
    detections: true,
    related: true,
  });
  const [copyFeedback, setCopyFeedback] = useState(false);

  // Fetch source data
  const {
    data: source,
    isLoading: sourceLoading,
    error: sourceError,
  } = useSourceDetail(sourceId || null);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleCopyCoordinates = () => {
    if (source) {
      const text = `RA: ${source.ra_deg}, Dec: ${source.dec_deg}`;
      copyToClipboard(text).then(() => setCopyFeedback(true));
    }
  };

  // Detection columns for GenericTable
  const detectionColumns: TableColumn<any>[] = [
    {
      field: "name",
      label: "Name",
      sortable: true,
    },
    {
      field: "ra",
      label: "RA (deg)",
      sortable: true,
      render: (value) => (value ? value.toFixed(6) : "N/A"),
    },
    {
      field: "dec",
      label: "Dec (deg)",
      sortable: true,
      render: (value) => (value ? value.toFixed(6) : "N/A"),
    },
    {
      field: "flux_peak",
      label: "Peak Flux (mJy/beam)",
      sortable: true,
      render: (value, row) => {
        if (!value) return "N/A";
        const err = row.flux_peak_err ? ` ± ${row.flux_peak_err.toFixed(3)}` : "";
        return `${value.toFixed(3)}${err}`;
      },
    },
    {
      field: "flux_int",
      label: "Int. Flux (mJy)",
      sortable: true,
      render: (value, row) => {
        if (!value) return "N/A";
        const err = row.flux_int_err ? ` ± ${row.flux_int_err.toFixed(3)}` : "";
        return `${value.toFixed(3)}${err}`;
      },
    },
    {
      field: "snr",
      label: "SNR",
      sortable: true,
      render: (value) => (value ? value.toFixed(2) : "N/A"),
    },
    {
      field: "forced",
      label: "Forced",
      sortable: true,
      render: (value) => (value ? "Yes" : "No"),
    },
    {
      field: "measured_at",
      label: "Date",
      sortable: true,
      render: (value) => formatDateTime(value),
    },
  ];

  if (sourceLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <SkeletonLoader variant="cards" rows={4} />
      </Container>
    );
  }

  if (sourceError || !source) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">
          Failed to load source details.{" "}
          {sourceError instanceof Error ? sourceError.message : "Unknown error"}
        </Alert>
      </Container>
    );
  }

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Page Header */}
        <Box
          sx={{
            mb: 4,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Box>
            <Typography variant="h4" gutterBottom>
              <strong>Source:</strong> {source.name}
            </Typography>
            {source.ese_probability && source.ese_probability > 0 && (
              <Chip
                label={`ESE Candidate (${(source.ese_probability * 100).toFixed(1)}%)`}
                color="warning"
                size="small"
                sx={{ mt: 1 }}
              />
            )}
            {source.new_source && (
              <Chip label="New Source" color="success" size="small" sx={{ mt: 1, ml: 1 }} />
            )}
          </Box>
          <Stack direction="row" spacing={1}>
            {/* External links */}
            <Button
              size="small"
              variant="outlined"
              startIcon={<LinkIcon />}
              href={`https://simbad.u-strasbg.fr/simbad/sim-coo?Coord=${source.ra_deg}d${source.dec_deg}d`}
              target="_blank"
            >
              SIMBAD
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<LinkIcon />}
              href={`https://ned.ipac.caltech.edu/conesearch?coordinates=${source.ra_deg}d%20${source.dec_deg}d`}
              target="_blank"
            >
              NED
            </Button>
          </Stack>
        </Box>

        {/* Three-Column Layout */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
            gap: 3,
          }}
        >
          {/* Column 1: Details */}
          <Box>
            <Card>
              <CardHeader
                title="Details"
                action={
                  <Tooltip title="Copy Coordinates">
                    <IconButton onClick={handleCopyCoordinates} size="small">
                      <ContentCopyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                }
              />
              <CardContent>
                <Typography variant="body2" paragraph>
                  <strong>Name:</strong> {source.name}
                </Typography>
                <Divider sx={{ my: 2 }} />

                <Typography variant="body2" paragraph>
                  <strong>Position:</strong>
                  <br />
                  {formatRA(source.ra_deg)} {formatDec(source.dec_deg)}
                  <br />
                  <strong>Decimal:</strong> {source.ra_deg.toFixed(6)} {source.dec_deg.toFixed(6)}
                </Typography>

                <Divider sx={{ my: 2 }} />

                <Typography variant="body2" paragraph>
                  <strong>Flux Statistics:</strong>
                  <br />
                  {source.mean_flux_jy && (
                    <>
                      Mean Flux: {(source.mean_flux_jy * 1000).toFixed(3)} mJy
                      <br />
                    </>
                  )}
                  {source.std_flux_jy && (
                    <>
                      Std Flux: {(source.std_flux_jy * 1000).toFixed(3)} mJy
                      <br />
                    </>
                  )}
                  {source.max_snr && (
                    <>
                      Max SNR: {source.max_snr.toFixed(2)}
                      <br />
                    </>
                  )}
                  {source.variability_metrics && (
                    <>
                      Variability (v): {source.variability_metrics.v.toFixed(3)}
                      <br />
                      Variability (η): {source.variability_metrics.eta.toFixed(3)}
                    </>
                  )}
                </Typography>

                <Divider sx={{ my: 2 }} />

                <Typography variant="body2" paragraph>
                  <strong>Measurements:</strong>
                  <br />
                  Total: {source.n_meas}
                  <br />
                  Forced: {source.n_meas_forced}
                </Typography>

                {source.ese_probability !== undefined && source.ese_probability > 0 && (
                  <>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="body2" paragraph>
                      <strong>ESE Metrics:</strong>
                      <br />
                      Probability: {(source.ese_probability * 100).toFixed(1)}%
                    </Typography>
                  </>
                )}
              </CardContent>
            </Card>
          </Box>

          {/* Column 2: Sky Visualization */}
          {/* Temporarily simplified until Aladin Lite is fully integrated */}
          <Box>
            <Card>
              <CardHeader title="Sky View" />
              <CardContent>
                <Box
                  sx={{
                    width: "100%",
                    height: "400px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    bgcolor: "background.default",
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                  }}
                >
                  <Button variant="contained" onClick={() => navigate("/sky")}>
                    Open Interactive Sky Map
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Box>

          {/* Column 3: Comments/Annotations */}
          <Box>
            <Card>
              <CardHeader title="Comments & Annotations" />
              <CardContent>
                <Alert severity="info">No comments yet.</Alert>
              </CardContent>
            </Card>
          </Box>
        </Box>

        {/* Full-width: Light Curve */}
        <Box sx={{ mt: 3 }}>
          <Card>
            <CardHeader
              title="Light Curve"
              action={
                <IconButton onClick={() => toggleSection("lightCurve")}>
                  {expandedSections.lightCurve ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              }
            />
            <Collapse in={expandedSections.lightCurve}>
              <CardContent>
                <Box
                  sx={{
                    height: "400px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    bgcolor: "background.default",
                  }}
                >
                  <Typography color="text.secondary">
                    Light curve visualization requires additional data
                  </Typography>
                </Box>
              </CardContent>
            </Collapse>
          </Card>
        </Box>

        {/* Full-width: Detections Table */}
        <Box sx={{ mt: 3 }}>
          <Card>
            <CardHeader
              title="Detections"
              action={
                <IconButton onClick={() => toggleSection("detections")}>
                  {expandedSections.detections ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              }
            />
            <Collapse in={expandedSections.detections}>
              <CardContent>
                <GenericTable<any>
                  apiEndpoint={`/api/sources/${sourceId}/detections`}
                  columns={detectionColumns}
                  title=""
                  searchable={true}
                  exportable={true}
                  pageSize={25}
                  onRowClick={(row) => {
                    if (row.image_id) {
                      navigate(`/images/${row.image_id}`);
                    }
                  }}
                  transformData={(data) => ({
                    rows: data.items || [],
                    total: data.total || 0,
                  })}
                />
              </CardContent>
            </Collapse>
          </Card>
        </Box>
      </Container>

      <Snackbar
        open={copyFeedback}
        autoHideDuration={2000}
        onClose={() => setCopyFeedback(false)}
        message="Coordinates copied to clipboard"
      />
    </>
  );
}
