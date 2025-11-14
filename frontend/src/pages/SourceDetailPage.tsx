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

import { useState } from "react";
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
} from "@mui/material";
import { SkeletonLoader } from "../components/SkeletonLoader";
import {
  ArrowBack as ArrowBackIcon,
  ArrowForward as ArrowForwardIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Link as LinkIcon,
} from "@mui/icons-material";
import { useSourceDetail } from "../api/queries";
import GenericTable from "../components/GenericTable";
import type { TableColumn } from "../components/GenericTable";
import { Box } from "@mui/material";

export default function SourceDetailPage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const navigate = useNavigate();
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    lightCurve: true,
    detections: true,
    related: true,
  });
  // Fetch source data
  const {
    data: source,
    isLoading: sourceLoading,
    error: sourceError,
  } = useSourceDetail(sourceId || null);

  // Fetch previous/next source IDs for navigation (placeholder)
  const navigationIds = { previousId: null, nextId: null };

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // Format coordinates
  const formatRA = (ra: number) => {
    const hours = Math.floor(ra / 15);
    const minutes = Math.floor((ra / 15 - hours) * 60);
    const seconds = ((ra / 15 - hours) * 60 - minutes) * 60;
    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toFixed(2).padStart(5, "0")}`;
  };

  const formatDec = (dec: number) => {
    const sign = dec >= 0 ? "+" : "-";
    const absDec = Math.abs(dec);
    const degrees = Math.floor(absDec);
    const minutes = Math.floor((absDec - degrees) * 60);
    const seconds = ((absDec - degrees) * 60 - minutes) * 60;
    return `${sign}${degrees.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toFixed(2).padStart(5, "0")}`;
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
      render: (value) => (value ? new Date(value).toLocaleString() : "N/A"),
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
          {/* Navigation */}
          {navigationIds?.previousId && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<ArrowBackIcon />}
              onClick={() => navigate(`/sources/${navigationIds.previousId}`)}
            >
              Previous
            </Button>
          )}
          {navigationIds?.nextId && (
            <Button
              size="small"
              variant="outlined"
              endIcon={<ArrowForwardIcon />}
              onClick={() => navigate(`/sources/${navigationIds.nextId}`)}
            >
              Next
            </Button>
          )}
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
            <CardHeader title="Details" />
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

        {/* Column 2: Sky Visualization (Aladin Lite) */}
        <Box>
          <Card>
            <CardHeader title="Sky View" />
            <CardContent>
              <Box
                id="aladin-lite-div"
                sx={{
                  width: "100%",
                  height: "400px",
                  border: "1px solid #ddd",
                  borderRadius: 1,
                }}
              >
                {/* Aladin Lite will be initialized here */}
                <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                  Aladin Lite integration coming soon
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Box>

        {/* Column 3: Comments/Annotations */}
        <Box>
          <Card>
            <CardHeader title="Comments & Annotations" />
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Comments system coming soon
              </Typography>
              {/* TODO: Add comments component */}
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
              <Box sx={{ height: "400px" }}>
                {/* TODO: Add Plotly light curve visualization */}
                <Typography variant="body2" color="text.secondary">
                  Light curve visualization coming soon
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

      {/* Full-width: Related Sources */}
      {/* TODO: Implement related sources when API endpoint is available */}
      {false && (
        <Box sx={{ mt: 3 }}>
          <Card>
            <CardHeader
              title="Related Sources"
              action={
                <IconButton onClick={() => toggleSection("related")}>
                  {expandedSections.related ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              }
            />
            <Collapse in={expandedSections.related}>
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  Related sources table coming soon
                </Typography>
                {/* TODO: Add related sources GenericTable */}
              </CardContent>
            </Collapse>
          </Card>
        </Box>
      )}
    </Container>
  );
}
