/**
 * GenericTable Component
 *
 * VAST-inspired reusable table component with:
 * - Server-side pagination
 * - Dynamic column configuration
 * - Search/filter functionality
 * - Export functionality (CSV, Excel)
 * - Column visibility toggle
 * - Sortable columns
 *
 * Inspired by VAST's generic_table.html and datatables-pipeline.js
 *
 * @module components/GenericTable
 */

import { useState, useMemo, useCallback } from "react";
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  TextField,
  InputAdornment,
  Stack,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Typography,
  Pagination,
  CircularProgress,
  Alert,
  Button,
} from "@mui/material";
import {
  Search as SearchIcon,
  Download as DownloadIcon,
  Visibility as VisibilityIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

export interface TableColumn<T = any> {
  /** Field name in the data object */
  field: string;
  /** Display label for the column */
  label: string;
  /** Whether column is sortable */
  sortable?: boolean;
  /** Whether column is searchable */
  searchable?: boolean;
  /** Custom render function */
  render?: (value: any, row: T) => React.ReactNode;
  /** Generate link URL for cell (makes cell clickable) */
  link?: (row: T) => string;
  /** Column width */
  width?: string | number;
  /** Alignment */
  align?: "left" | "center" | "right";
  /** Whether column is visible by default */
  defaultVisible?: boolean;
}

export interface GenericTableProps<T = any> {
  /** API endpoint for data fetching */
  apiEndpoint: string;
  /** Column definitions */
  columns: TableColumn<T>[];
  /** Table title */
  title?: string;
  /** Table description */
  description?: string;
  /** Whether search is enabled */
  searchable?: boolean;
  /** Whether export is enabled */
  exportable?: boolean;
  /** Whether columns can be toggled */
  columnToggleable?: boolean;
  /** Initial page size */
  pageSize?: number;
  /** Callback when row is clicked */
  onRowClick?: (row: T) => void;
  /** Additional query parameters */
  queryParams?: Record<string, string | number | boolean>;
  /** Custom data transformer */
  transformData?: (data: any) => { rows: T[]; total: number };
  /** Loading state override */
  loading?: boolean;
  /** Error state override */
  error?: Error | null;
  /** Refresh callback */
  onRefresh?: () => void;
}

type SortDirection = "asc" | "desc";

/**
 * Export data to CSV
 */
function exportToCSV<T>(data: T[], columns: TableColumn<T>[], filename: string) {
  const visibleColumns = columns.filter((col) => col.defaultVisible !== false);

  // CSV header
  const headers = visibleColumns.map((col) => col.label).join(",");

  // CSV rows
  const rows = data.map((row) => {
    return visibleColumns
      .map((col) => {
        const value = col.render
          ? col.render((row as any)[col.field], row)
          : (row as any)[col.field];
        // Escape commas and quotes
        const str = String(value ?? "").replace(/"/g, '""');
        return `"${str}"`;
      })
      .join(",");
  });

  const csv = [headers, ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * GenericTable Component
 */
export default function GenericTable<T = any>({
  apiEndpoint,
  columns,
  title,
  description,
  searchable = true,
  exportable = true,
  columnToggleable = true,
  pageSize = 25,
  onRowClick,
  queryParams = {},
  transformData,
  loading: loadingOverride,
  error: errorOverride,
  onRefresh,
}: GenericTableProps<T>) {
  const [page, setPage] = useState(1);
  const [searchText, setSearchText] = useState("");
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [columnVisibility, setColumnVisibility] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    columns.forEach((col) => {
      initial[col.field] = col.defaultVisible !== false;
    });
    return initial;
  });
  const [columnMenuAnchor, setColumnMenuAnchor] = useState<null | HTMLElement>(null);

  // Build query parameters
  const queryKey = useMemo(() => {
    const params: Record<string, string | number> = {
      page: page,
      page_size: pageSize,
      ...queryParams,
    };

    if (searchText && searchable) {
      params.search = searchText;
    }

    if (sortField) {
      params.ordering = sortDirection === "desc" ? `-${sortField}` : sortField;
    }

    return ["generic-table", apiEndpoint, params];
  }, [apiEndpoint, page, pageSize, searchText, sortField, sortDirection, queryParams, searchable]);

  // Fetch data
  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: async () => {
      const params = new URLSearchParams();
      Object.entries(queryKey[2] as Record<string, unknown>).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          params.append(key, String(value));
        }
      });

      const response = await apiClient.get(`${apiEndpoint}?${params.toString()}`);

      if (transformData) {
        return transformData(response.data);
      }

      // Default transformation: expect { results: T[], count: number }
      if (response.data.results && typeof response.data.count === "number") {
        return {
          rows: response.data.results,
          total: response.data.count,
        };
      }

      // Fallback: assume array
      if (Array.isArray(response.data)) {
        return {
          rows: response.data,
          total: response.data.length,
        };
      }

      return { rows: [], total: 0 };
    },
  });

  const loading = loadingOverride ?? isLoading;
  const errorState = errorOverride ?? error;
  const rows = data?.rows ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  // Visible columns
  const visibleColumns = useMemo(() => {
    return columns.filter((col) => columnVisibility[col.field] !== false);
  }, [columns, columnVisibility]);

  // Handle sort
  const handleSort = useCallback(
    (field: string) => {
      if (sortField === field) {
        setSortDirection(sortDirection === "asc" ? "desc" : "asc");
      } else {
        setSortField(field);
        setSortDirection("asc");
      }
      setPage(1);
    },
    [sortField, sortDirection]
  );

  // Handle column visibility toggle
  const handleColumnToggle = useCallback((field: string) => {
    setColumnVisibility((prev) => ({
      ...prev,
      [field]: !prev[field],
    }));
  }, []);

  // Handle export
  const handleExport = useCallback(() => {
    if (rows.length === 0) return;
    const filename = title?.toLowerCase().replace(/\s+/g, "_") || "table_export";
    exportToCSV(rows, columns, filename);
  }, [rows, columns, title]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    refetch();
    onRefresh?.();
  }, [refetch, onRefresh]);

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      {(title || description) && (
        <Box sx={{ mb: 3 }}>
          {title && (
            <Typography variant="h5" gutterBottom>
              {title}
            </Typography>
          )}
          {description && (
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
          )}
        </Box>
      )}

      {/* Toolbar */}
      <Stack direction="row" spacing={2} sx={{ mb: 2 }} alignItems="center">
        {searchable && (
          <TextField
            size="small"
            placeholder="Search..."
            value={searchText}
            onChange={(e) => {
              setSearchText(e.target.value);
              setPage(1);
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ flexGrow: 1, maxWidth: 400 }}
          />
        )}

        {exportable && (
          <Tooltip title="Export to CSV">
            <IconButton onClick={handleExport} disabled={rows.length === 0}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>
        )}

        {columnToggleable && (
          <>
            <Tooltip title="Toggle columns">
              <IconButton onClick={(e) => setColumnMenuAnchor(e.currentTarget)}>
                <VisibilityIcon />
              </IconButton>
            </Tooltip>
            <Menu
              anchorEl={columnMenuAnchor}
              open={Boolean(columnMenuAnchor)}
              onClose={() => setColumnMenuAnchor(null)}
            >
              {columns.map((col) => (
                <MenuItem key={col.field} dense>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={columnVisibility[col.field] !== false}
                        onChange={() => handleColumnToggle(col.field)}
                        size="small"
                      />
                    }
                    label={col.label}
                    sx={{ m: 0 }}
                  />
                </MenuItem>
              ))}
            </Menu>
          </>
        )}

        <Tooltip title="Refresh">
          <IconButton onClick={handleRefresh} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Stack>

      {/* Error State */}
      {errorState && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errorState.message || "Failed to load data"}
        </Alert>
      )}

      {/* Table */}
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              {visibleColumns.map((col) => (
                <TableCell key={col.field} width={col.width} align={col.align || "left"}>
                  {col.sortable !== false ? (
                    <TableSortLabel
                      active={sortField === col.field}
                      direction={sortField === col.field ? sortDirection : "asc"}
                      onClick={() => handleSort(col.field)}
                    >
                      {col.label}
                    </TableSortLabel>
                  ) : (
                    col.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={visibleColumns.length} align="center" sx={{ py: 4 }}>
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={visibleColumns.length} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">No data available</Typography>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row: any, idx: number) => (
                <TableRow
                  key={idx}
                  hover={!!onRowClick}
                  onClick={() => onRowClick?.(row)}
                  sx={{ cursor: onRowClick ? "pointer" : "default" }}
                >
                  {visibleColumns.map((col) => {
                    const value = (row as any)[col.field];
                    const cellContent = col.render ? col.render(value, row) : value;
                    const link = col.link ? col.link(row) : null;

                    return (
                      <TableCell key={col.field} align={col.align || "left"}>
                        {link ? (
                          <Button
                            component="a"
                            href={link}
                            onClick={(e) => {
                              e.stopPropagation();
                            }}
                            sx={{
                              textTransform: "none",
                              p: 0,
                              minWidth: "auto",
                            }}
                          >
                            {cellContent}
                          </Button>
                        ) : (
                          cellContent
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {totalPages > 1 && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, newPage) => setPage(newPage)}
            color="primary"
          />
        </Box>
      )}

      {/* Results count */}
      {total > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: "center" }}>
          Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total}{" "}
          results
        </Typography>
      )}
    </Paper>
  );
}
