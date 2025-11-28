/**
 * Image Detail Page
 *
 * VAST-inspired image detail page with three-column layout:
 * - Column 1: Image details and metadata
 * - Column 2: Sky visualization (Aladin Lite)
 * - Column 3: Comments/Annotations
 *
 * Full-width sections below:
 * - Measurements table (using GenericTable)
 * - Runs table (using GenericTable)
 *
 * Inspired by VAST's image_detail.html
 *
 * @module pages/ImageDetailPage
 */

import React, { useState } from "react";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import {
  Container,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Button,
  Stack,
  Divider,
  Collapse,
  IconButton,
  Alert,
  Tooltip,
  Snackbar,
} from "@mui/material";
import { SkeletonLoader } from "../components/SkeletonLoader";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Link as LinkIcon,
  Visibility as VisibilityIcon,
  ContentCopy as ContentCopyIcon,
} from "@mui/icons-material";
import { useImageDetail } from "../api/queries";
import GenericTable from "../components/GenericTable";
import type { TableColumn } from "../components/GenericTable";
import { formatRA, formatDec, copyToClipboard } from "../utils/coordinateUtils";
import CatalogValidationPanel from "../components/Sky/CatalogValidationPanel";

export default function ImageDetailPage() {
  const { imageId } = useParams<{ imageId: string }>();
  const navigate = useNavigate();
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    measurements: true,
    runs: false, // Hide runs section since n_runs is always 0
  });
  const [copyFeedback, setCopyFeedback] = useState(false);

  // Fetch image data
  const {
    data: image,
    isLoading: imageLoading,
    error: imageError,
  } = useImageDetail(imageId ? parseInt(imageId, 10) : null);
  const catalogImageId = imageId ?? (image && image.id ? String(image.id) : null);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleCopyCoordinates = () => {
    if (image && image.ra !== null && image.dec !== null) {
      const text = `RA: ${image.ra}, Dec: ${image.dec}`;
      copyToClipboard(text).then(() => setCopyFeedback(true));
    }
  };

  // Measurement columns for GenericTable
  const measurementColumns: TableColumn<any>[] = [
    {
      field: "name",
      label: "Name",
      sortable: true,
    },
    {
      field: "source_id",
      label: "Source ID",
      sortable: true,
      render: (value) => value || "N/A",
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
  ];

  if (imageLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <SkeletonLoader variant="cards" rows={4} />
      </Container>
    );
  }

  if (imageError || !image) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">
          Failed to load image details.{" "}
          {imageError instanceof Error ? imageError.message : "Unknown error"}
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
          <Typography variant="h1" component="h1">
            <strong>Image:</strong> {image.name}
          </Typography>
          <Stack direction="row" spacing={1}>
            {/* External links */}
            {image.ra !== null && image.dec !== null && (
              <Button
                size="small"
                variant="outlined"
                startIcon={<LinkIcon />}
                href={`https://simbad.u-strasbg.fr/simbad/sim-coo?Coord=${image.ra}d${image.dec}d`}
                target="_blank"
              >
                SIMBAD
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
              <CardHeader
                title="Details"
                action={
                  image.ra !== null &&
                  image.dec !== null && (
                    <Tooltip title="Copy Coordinates">
                      <IconButton onClick={handleCopyCoordinates} size="small">
                        <ContentCopyIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )
                }
              />
              <CardContent>
                <Typography variant="body2" paragraph>
                  <strong>Name:</strong> {image.name}
                </Typography>

                <Divider sx={{ my: 2 }} />

                {image.ra !== null && image.dec !== null && (
                  <>
                    <Typography variant="body2" paragraph>
                      <strong>Position:</strong>
                      <br />
                      {image.ra_hms || formatRA(image.ra)} {image.dec_dms || formatDec(image.dec)}
                      <br />
                      <strong>Decimal:</strong> {image.ra.toFixed(6)} {image.dec.toFixed(6)}
                    </Typography>
                  </>
                )}

                {image.l !== undefined &&
                  image.l !== null &&
                  image.b !== undefined &&
                  image.b !== null && (
                    <Typography variant="body2" paragraph>
                      <strong>Galactic:</strong> {image.l.toFixed(6)} {image.b.toFixed(6)}
                    </Typography>
                  )}

                {(image.beam_bmaj || image.beam_bmin || image.beam_bpa) && (
                  <>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="body2" paragraph>
                      <strong>Beam:</strong>
                      <br />
                      {image.beam_bmaj && `BMAJ: ${(image.beam_bmaj * 3600).toFixed(3)}&Prime;`}
                      <br />
                      {image.beam_bmin && `BMIN: ${(image.beam_bmin * 3600).toFixed(3)}&Prime;`}
                      <br />
                      {image.beam_bpa !== null &&
                        image.beam_bpa !== undefined &&
                        `BPA: ${image.beam_bpa.toFixed(2)}&deg;`}
                    </Typography>
                  </>
                )}

                {image.rms_median !== null && image.rms_median !== undefined && (
                  <>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="body2" paragraph>
                      <strong>RMS:</strong>
                      <br />
                      Median: {image.rms_median.toFixed(3)} mJy
                      <br />
                      {image.rms_min !== null &&
                        image.rms_min !== undefined &&
                        `Min: ${image.rms_min.toFixed(3)} mJy`}
                      <br />
                      {image.rms_max !== null &&
                        image.rms_max !== undefined &&
                        `Max: ${image.rms_max.toFixed(3)} mJy`}
                    </Typography>
                  </>
                )}

                {(image.frequency || image.bandwidth) && (
                  <>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="body2" paragraph>
                      {image.frequency && (
                        <>
                          <strong>Frequency:</strong> {image.frequency.toFixed(1)} MHz
                          <br />
                        </>
                      )}
                      {image.bandwidth && (
                        <>
                          <strong>Bandwidth:</strong> {image.bandwidth.toFixed(1)} MHz
                        </>
                      )}
                    </Typography>
                  </>
                )}

                <Divider sx={{ my: 2 }} />

                <Typography variant="body2" paragraph>
                  <strong>Measurements:</strong> {image.n_meas.toLocaleString()}
                  <br />
                  <strong>Runs:</strong> {image.n_runs.toLocaleString()}
                </Typography>

                {image.path && (
                  <>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="body2" paragraph>
                      <strong>Path:</strong>
                      <br />
                      <Box component="code" sx={{ fontSize: "0.75rem", wordBreak: "break-all" }}>
                        {image.path}
                      </Box>
                    </Typography>
                    <Button
                      variant="outlined"
                      startIcon={<VisibilityIcon />}
                      component={RouterLink}
                      to={`/carta?file=${encodeURIComponent(image.path)}`}
                      sx={{ mt: 1 }}
                      fullWidth
                    >
                      View in CARTA
                    </Button>
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

        {/* Catalog Validation */}
        <Box sx={{ mt: 3 }}>
          <Card>
            <CardHeader title="Catalog Validation" />
            <CardContent>
              <CatalogValidationPanel imageId={catalogImageId} />
            </CardContent>
          </Card>
        </Box>

        {/* Full-width: Measurements Table */}
        <Box sx={{ mt: 3 }}>
          <Card>
            <CardHeader
              title="Measurements"
              action={
                <IconButton onClick={() => toggleSection("measurements")}>
                  {expandedSections.measurements ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              }
            />
            <Collapse in={expandedSections.measurements}>
              <CardContent>
                <GenericTable<any>
                  apiEndpoint={`/images/${imageId}/measurements`}
                  columns={measurementColumns}
                  title=""
                  searchable={true}
                  exportable={true}
                  pageSize={25}
                  onRowClick={(row: any) => {
                    if (row.source_id) {
                      navigate(`/sources/${row.source_id}`);
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
