/**
 * Source Monitoring Page
 * AG Grid table for per-source flux timeseries monitoring with advanced filtering
 */
import { useState, useMemo, useRef } from "react";
import {
  Container,
  Typography,
  Paper,
  Box,
  TextField,
  Button,
  Alert,
  AlertTitle,
  Stack,
  Chip,
  Collapse,
  Slider,
  FormControlLabel,
  Checkbox,
  Divider,
} from "@mui/material";
import {
  Search,
  ExpandMore,
  ExpandLess,
  Clear as ClearIcon,
  TableChart,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import Grid from "@mui/material/GridLegacy";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { useSourceSearch } from "../api/queries";
import type { SourceTimeseries, SourceSearchRequest } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import PageBreadcrumbs from "../components/PageBreadcrumbs";

// Constants
const DEFAULT_LIMIT = 100;
const ADVANCED_FILTER_LIMIT = 1000;
const DEFAULT_VARIABILITY_THRESHOLD = 5;
const DEC_RANGE = { min: -90, max: 90 };
const GRID_HEIGHT = 600;
const PAGINATION_PAGE_SIZE = 20;

export default function SourceMonitoringPage() {
  const navigate = useNavigate();
  const [sourceId, setSourceId] = useState("");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [variabilityThreshold, setVariabilityThreshold] = useState(DEFAULT_VARIABILITY_THRESHOLD);
  const [eseOnly, setEseOnly] = useState(false);
  const [decMin, setDecMin] = useState(DEC_RANGE.min);
  const [decMax, setDecMax] = useState(DEC_RANGE.max);
  const [searchRequest, setSearchRequest] = useState<SourceSearchRequest | null>(null);
  const gridRef = useRef<AgGridReact>(null);

  const { data, isLoading, error } = useSourceSearch(searchRequest);

  const handleSearch = () => {
    const request: SourceSearchRequest = {};

    if (sourceId.trim()) {
      request.source_id = sourceId.trim();
    } else if (!showAdvancedFilters) {
      // No source ID and no advanced filters - don't search
      setSearchRequest(null);
      return;
    }

    if (showAdvancedFilters) {
      request.limit = ADVANCED_FILTER_LIMIT; // Allow more results with filters
      request.variability_threshold = variabilityThreshold;
      request.ese_only = eseOnly;
      request.dec_min = decMin;
      request.dec_max = decMax;
    } else {
      request.limit = DEFAULT_LIMIT;
    }

    setSearchRequest(request);
  };

  const handleClearFilters = () => {
    setSourceId("");
    setVariabilityThreshold(DEFAULT_VARIABILITY_THRESHOLD);
    setEseOnly(false);
    setDecMin(DEC_RANGE.min);
    setDecMax(DEC_RANGE.max);
    setSearchRequest(null);
  };

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (sourceId.trim()) count++;
    if (variabilityThreshold !== DEFAULT_VARIABILITY_THRESHOLD) count++;
    if (eseOnly) count++;
    if (decMin !== DEC_RANGE.min || decMax !== DEC_RANGE.max) count++;
    return count;
  }, [sourceId, variabilityThreshold, eseOnly, decMin, decMax]);

  const columnDefs = useMemo<ColDef<SourceTimeseries>[]>(
    () => [
      {
        field: "source_id",
        headerName: "Source ID",
        width: 200,
        pinned: "left",
        cellStyle: { fontFamily: "monospace" },
        cellRenderer: (params: any) => (
          <span
            style={{
              cursor: "pointer",
              textDecoration: "underline",
              color: "#90caf9",
            }}
            onClick={() => navigate(`/sources/${encodeURIComponent(params.value)}`)}
          >
            {params.value}
          </span>
        ),
      },
      {
        field: "ra_deg",
        headerName: "RA (deg)",
        width: 120,
        valueFormatter: (params) => {
          if (params.value == null) return "—";
          return params.value.toFixed(5);
        },
      },
      {
        field: "dec_deg",
        headerName: "Dec (deg)",
        width: 120,
        valueFormatter: (params) => {
          if (params.value == null) return "—";
          return params.value.toFixed(5);
        },
      },
      {
        field: "catalog",
        headerName: "Catalog",
        width: 100,
      },
      {
        field: "mean_flux_jy",
        headerName: "Mean Flux (mJy)",
        width: 140,
        valueFormatter: (params) => {
          if (params.value == null) return "—";
          return (params.value * 1000).toFixed(2);
        },
      },
      {
        field: "std_flux_jy",
        headerName: "Std Dev (mJy)",
        width: 140,
        valueFormatter: (params) => {
          if (params.value == null) return "—";
          return (params.value * 1000).toFixed(2);
        },
      },
      {
        field: "chi_sq_nu",
        headerName: "χ²/ν",
        width: 100,
        valueFormatter: (params) => {
          if (params.value == null) return "—";
          return params.value.toFixed(2);
        },
        cellStyle: (params) => {
          if (params.value && params.value > 5) {
            return {
              backgroundColor: "rgba(244, 67, 54, 0.1)",
              color: "#f44336",
            };
          }
          return undefined;
        },
      },
      {
        field: "is_variable",
        headerName: "Variable?",
        width: 110,
        cellRenderer: (params: any) => (
          <span style={{ color: params.value ? "#f44336" : "#4caf50" }}>
            {params.value ? "✓ Yes" : "− No"}
          </span>
        ),
      },
      {
        field: "flux_points",
        headerName: "Observations",
        width: 130,
        valueFormatter: (params) => {
          if (params.value == null || !Array.isArray(params.value)) return "0 points";
          return `${params.value.length} points`;
        },
      },
    ],
    [navigate]
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      sortable: true,
      filter: true,
      resizable: true,
    }),
    []
  );

  return (
    <>
      <PageBreadcrumbs />
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h2" component="h2" gutterBottom sx={{ mb: 4 }}>
          Source Monitoring
        </Typography>

        {/* Search Interface */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Stack spacing={2}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Typography variant="h6">Search Sources</Typography>
              <Box display="flex" gap={1} alignItems="center">
                {activeFiltersCount > 0 && (
                  <Chip
                    label={`${activeFiltersCount} filter${activeFiltersCount > 1 ? "s" : ""}`}
                    size="small"
                    onDelete={handleClearFilters}
                    deleteIcon={<ClearIcon />}
                  />
                )}
                <Button
                  size="small"
                  startIcon={showAdvancedFilters ? <ExpandLess /> : <ExpandMore />}
                  onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                >
                  {showAdvancedFilters ? "Hide" : "Show"} Advanced Filters
                </Button>
              </Box>
            </Box>

            <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
              <TextField
                label="Source ID (e.g., NVSS J123456.7+420312)"
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                size="small"
                sx={{ flexGrow: 1, minWidth: 300 }}
              />
              <Button
                variant="contained"
                startIcon={<Search />}
                onClick={handleSearch}
                disabled={(!sourceId.trim() && !showAdvancedFilters) || isLoading}
              >
                Search
              </Button>
              {activeFiltersCount > 0 && (
                <Button variant="outlined" startIcon={<ClearIcon />} onClick={handleClearFilters}>
                  Clear
                </Button>
              )}
            </Box>

            {/* Advanced Filters */}
            <Collapse in={showAdvancedFilters}>
              <Divider sx={{ my: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" gutterBottom>
                    Variability Threshold (σ): {variabilityThreshold}
                  </Typography>
                  <Slider
                    value={variabilityThreshold}
                    onChange={(_, value) => setVariabilityThreshold(value as number)}
                    min={0}
                    max={10}
                    step={0.5}
                    marks={[
                      { value: 0, label: "0" },
                      { value: 5, label: "5" },
                      { value: 10, label: "10" },
                    ]}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2" gutterBottom>
                    Declination Range: {decMin.toFixed(1)}° to {decMax.toFixed(1)}°
                  </Typography>
                  <Box sx={{ px: 2 }}>
                    <Slider
                      value={[decMin, decMax]}
                      onChange={(_, value) => {
                        const [min, max] = value as number[];
                        setDecMin(min);
                        setDecMax(max);
                      }}
                      min={-90}
                      max={90}
                      step={1}
                      valueLabelDisplay="auto"
                    />
                  </Box>
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Checkbox checked={eseOnly} onChange={(e) => setEseOnly(e.target.checked)} />
                    }
                    label="Show only ESE candidates (>5σ variability)"
                  />
                </Grid>
              </Grid>
            </Collapse>
          </Stack>
        </Paper>

        {/* Results Table */}
        {error && (
          <Alert severity="error">
            <AlertTitle>Error loading sources</AlertTitle>
            {error instanceof Error
              ? error.message
              : "Source monitoring not available. This feature requires enhanced API endpoints."}
            {import.meta.env.MODE === "development" && (
              <Box
                component="pre"
                sx={{ fontSize: "0.75rem", marginTop: 1, whiteSpace: "pre-wrap" }}
              >
                {JSON.stringify(error, null, 2)}
              </Box>
            )}
          </Alert>
        )}

        {!error && (
          <Paper sx={{ p: 2 }}>
            <Box className="ag-theme-alpine-dark" sx={{ height: GRID_HEIGHT, width: "100%" }}>
              <AgGridReact
                ref={gridRef}
                rowData={data?.sources || []}
                columnDefs={columnDefs}
                defaultColDef={defaultColDef}
                pagination={true}
                paginationPageSize={PAGINATION_PAGE_SIZE}
                loading={isLoading}
                loadingOverlayComponent={() => (
                  <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                    <Typography>Loading sources...</Typography>
                  </Box>
                )}
                noRowsOverlayComponent={() => (
                  <Box sx={{ py: 8, px: 4 }}>
                    {searchRequest ? (
                      <EmptyState
                        icon={<TableChart sx={{ fontSize: 64, color: "text.secondary" }} />}
                        title="No sources found"
                        description="No sources match your search criteria. Try a different source ID or check the spelling."
                      />
                    ) : (
                      <EmptyState
                        icon={<TableChart sx={{ fontSize: 64, color: "text.secondary" }} />}
                        title="Search for sources"
                        description="Enter a source ID (e.g., NVSS J123456.7+420312) to search the catalog. You can also use advanced filters to find sources by coordinates, flux, or variability."
                      />
                    )}
                  </Box>
                )}
              />
            </Box>
          </Paper>
        )}
      </Container>
    </>
  );
}
