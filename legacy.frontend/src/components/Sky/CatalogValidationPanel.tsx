/**
 * CatalogValidationPanel Component - Display catalog validation results
 */
import { useState } from "react";
import {
  Box,
  Paper,
  Typography,
  Alert,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  CircularProgress,
  Stack,
  Divider,
} from "@mui/material";
import { CheckCircle, Error, Warning } from "@mui/icons-material";
import { useCatalogValidation, useRunCatalogValidation } from "../../api/queries";
import type { CatalogValidationResults } from "../../api/types";

interface CatalogValidationPanelProps {
  imageId: string | null;
  catalog?: "nvss" | "vlass";
}

export default function CatalogValidationPanel({
  imageId,
  catalog: initialCatalog = "nvss",
}: CatalogValidationPanelProps) {
  const [catalog, setCatalog] = useState<"nvss" | "vlass">(initialCatalog);
  const [validationType, setValidationType] = useState<
    "all" | "astrometry" | "flux_scale" | "source_counts"
  >("all");

  const {
    data: validationResults,
    isLoading,
    error,
  } = useCatalogValidation(imageId, catalog, validationType === "all" ? "all" : validationType);

  const runValidation = useRunCatalogValidation();

  const handleRunValidation = () => {
    if (!imageId) return;
    runValidation.mutate({
      imageId,
      catalog,
      validationTypes: ["astrometry", "flux_scale", "source_counts"],
    });
  };

  const renderValidationResult = (result: CatalogValidationResults | undefined, title: string) => {
    if (!result) return null;

    const statusColor = result.has_issues ? "error" : result.has_warnings ? "warning" : "success";
    const StatusIcon = result.has_issues ? Error : result.has_warnings ? Warning : CheckCircle;

    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
          <StatusIcon color={statusColor} sx={{ mr: 1 }} />
          <Typography variant="h6">{title}</Typography>
          <Chip
            label={result.has_issues ? "Issues" : result.has_warnings ? "Warnings" : "Pass"}
            color={statusColor}
            size="small"
            sx={{ ml: "auto" }}
          />
        </Box>

        <Stack spacing={1}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Matched: {result.n_matched} / {result.n_detected} detected, {result.n_catalog} catalog
              sources
            </Typography>
          </Box>

          {result.validation_type === "astrometry" && (
            <>
              {result.mean_offset_arcsec !== undefined && (
                <Typography variant="body2">
                  Mean Offset: {result.mean_offset_arcsec.toFixed(2)} arcsec
                </Typography>
              )}
              {result.rms_offset_arcsec !== undefined && (
                <Typography variant="body2">
                  RMS Offset: {result.rms_offset_arcsec.toFixed(2)} arcsec
                </Typography>
              )}
              {result.max_offset_arcsec !== undefined && (
                <Typography variant="body2">
                  Max Offset: {result.max_offset_arcsec.toFixed(2)} arcsec
                </Typography>
              )}
              {result.offset_ra_arcsec !== undefined && result.offset_dec_arcsec !== undefined && (
                <Typography variant="body2">
                  RA Offset: {result.offset_ra_arcsec.toFixed(2)} arcsec, Dec Offset:{" "}
                  {result.offset_dec_arcsec.toFixed(2)} arcsec
                </Typography>
              )}
            </>
          )}

          {result.validation_type === "flux_scale" && (
            <>
              {result.mean_flux_ratio !== undefined && (
                <Typography variant="body2">
                  Mean Flux Ratio: {result.mean_flux_ratio.toFixed(3)}
                </Typography>
              )}
              {result.rms_flux_ratio !== undefined && (
                <Typography variant="body2">
                  RMS Flux Ratio: {result.rms_flux_ratio.toFixed(3)}
                </Typography>
              )}
              {result.flux_scale_error !== undefined && (
                <Typography variant="body2">
                  Flux Scale Error: {(result.flux_scale_error * 100).toFixed(1)}%
                </Typography>
              )}
            </>
          )}

          {result.validation_type === "source_counts" && (
            <>
              {result.completeness !== undefined && (
                <Typography variant="body2">
                  Completeness: {(result.completeness * 100).toFixed(1)}%
                </Typography>
              )}
            </>
          )}

          {result.issues.length > 0 && (
            <Alert severity="error" sx={{ mt: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Issues:
              </Typography>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {result.issues.map((issue: string, idx: number) => (
                  <li key={idx}>
                    <Typography variant="body2">{issue}</Typography>
                  </li>
                ))}
              </ul>
            </Alert>
          )}

          {result.warnings.length > 0 && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Warnings:
              </Typography>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {result.warnings.map((warning: string, idx: number) => (
                  <li key={idx}>
                    <Typography variant="body2">{warning}</Typography>
                  </li>
                ))}
              </ul>
            </Alert>
          )}
        </Stack>
      </Paper>
    );
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Catalog Validation
      </Typography>

      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Catalog</InputLabel>
          <Select value={catalog} onChange={(e) => setCatalog(e.target.value as "nvss" | "vlass")}>
            <MenuItem value="nvss">NVSS</MenuItem>
            <MenuItem value="vlass">VLASS</MenuItem>
          </Select>
        </FormControl>

        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Validation Type</InputLabel>
          <Select
            value={validationType}
            onChange={(e) => setValidationType(e.target.value as typeof validationType)}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="astrometry">Astrometry</MenuItem>
            <MenuItem value="flux_scale">Flux Scale</MenuItem>
            <MenuItem value="source_counts">Source Counts</MenuItem>
          </Select>
        </FormControl>

        <Button
          variant="contained"
          onClick={handleRunValidation}
          disabled={!imageId || runValidation.isPending}
        >
          {runValidation.isPending ? <CircularProgress size={20} /> : "Run Validation"}
        </Button>
      </Stack>

      <Divider sx={{ my: 2 }} />

      {isLoading && (
        <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Error loading validation results:{" "}
          {error instanceof Error ? error.message : "Unknown error"}
        </Alert>
      )}

      {validationResults && (
        <>
          {validationType === "all" || validationType === "astrometry"
            ? renderValidationResult(validationResults.astrometry as any, "Astrometry Validation")
            : null}

          {validationType === "all" || validationType === "flux_scale"
            ? renderValidationResult(validationResults.flux_scale as any, "Flux Scale Validation")
            : null}

          {validationType === "all" || validationType === "source_counts"
            ? renderValidationResult(
                validationResults.source_counts as any,
                "Source Counts Validation"
              )
            : null}
        </>
      )}

      {!isLoading && !error && !validationResults && (
        <Alert severity="info">
          No validation results available. Click "Run Validation" to generate results.
        </Alert>
      )}
    </Box>
  );
}
