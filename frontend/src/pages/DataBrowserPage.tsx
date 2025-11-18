/**
 * Data Browser Page - Main data management interface
 */
import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Button,
  TextField,
  Stack,
} from "@mui/material";
import {
  CloudUpload,
  CloudDone,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Pending,
  Visibility,
  Storage as StorageIcon,
  FolderOpen,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useDataInstances, useUVH5Files, useESECandidates } from "../api/queries";
import PageBreadcrumbs from "../components/PageBreadcrumbs";
import type { DataInstance } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { SkeletonLoader } from "../components/SkeletonLoader";
import { alpha } from "@mui/material/styles";
import { QASnapshotCard } from "../components/QA/QASnapshotCard";

const DATA_TYPE_LABELS: Record<string, string> = {
  ms: "MS",
  calib_ms: "Calibrated MS",
  caltable: "Calibration Table",
  image: "Image",
  mosaic: "Mosaic",
  catalog: "Catalog",
  qa: "QA Report",
  metadata: "Metadata",
};

const STATUS_COLORS: Record<string, "default" | "primary" | "success" | "warning" | "error"> = {
  staging: "warning",
  published: "success",
};

const QA_STATUS_COLORS: Record<string, "default" | "success" | "warning" | "error"> = {
  passed: "success",
  failed: "error",
  warning: "warning",
  pending: "default",
};

function formatDate(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString();
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function DataBrowserPage() {
  const [tabValue, setTabValue] = useState(0);
  const [dataTypeFilter, setDataTypeFilter] = useState<string>("all");
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [subbandFilter, setSubbandFilter] = useState<string>("");
  const navigate = useNavigate();
  const { data: eseCandidates, isLoading: eseLoading, refetch: refetchESE } = useESECandidates();

  // Reset page when switching tabs or changing filter
  useEffect(() => {
    setPage(0);
  }, [tabValue, dataTypeFilter, searchQuery, subbandFilter]);

  // Fetch data for all tabs independently to ensure proper caching
  const incomingQuery = useUVH5Files(
    "/data/incoming",
    rowsPerPage,
    page * rowsPerPage,
    searchQuery || undefined,
    subbandFilter || undefined
  );

  const stagingQuery = useDataInstances(
    dataTypeFilter !== "all" ? dataTypeFilter : undefined,
    "staging",
    rowsPerPage,
    page * rowsPerPage
  );
  const publishedQuery = useDataInstances(
    dataTypeFilter !== "all" ? dataTypeFilter : undefined,
    "published",
    rowsPerPage,
    page * rowsPerPage
  );

  const handleViewDetails = (instance: DataInstance) => {
    navigate(`/data/${instance.data_type}/${instance.id}`);
  };

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ p: 3 }}>
        <Typography variant="h2" component="h2" gutterBottom>
          Data Browser
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Manage and browse all pipeline data products
        </Typography>

        <Paper sx={{ mb: 2 }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
            <Tab
              icon={<FolderOpen />}
              iconPosition="start"
              label="Incoming"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<CloudUpload />}
              iconPosition="start"
              label="Staging"
              sx={{ textTransform: "none" }}
            />
            <Tab
              icon={<CloudDone />}
              iconPosition="start"
              label="Published"
              sx={{ textTransform: "none" }}
            />
          </Tabs>
        </Paper>

        <Paper sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
            {tabValue === 0 ? (
              // Incoming tab filters
              <>
                <TextField
                  size="small"
                  label="Search files"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by filename or path..."
                  sx={{ minWidth: 250 }}
                />
                <FormControl size="small" sx={{ minWidth: 150 }}>
                  <InputLabel>Subband</InputLabel>
                  <Select
                    value={subbandFilter}
                    label="Subband"
                    onChange={(e) => setSubbandFilter(e.target.value)}
                  >
                    <MenuItem value="">All Subbands</MenuItem>
                    {Array.from({ length: 24 }, (_, i) => (
                      <MenuItem key={i} value={`sb${i}`}>
                        sb{i}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            ) : (
              // Staging/Published tab filters
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>Data Type</InputLabel>
                <Select
                  value={dataTypeFilter}
                  label="Data Type"
                  onChange={(e) => setDataTypeFilter(e.target.value)}
                >
                  <MenuItem value="all">All Types</MenuItem>
                  {Object.entries(DATA_TYPE_LABELS).map(([value, label]) => (
                    <MenuItem key={value} value={value}>
                      {label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </Box>
        </Paper>

        <TabPanel value={tabValue} index={0}>
          <IncomingDataTable
            files={incomingQuery.data?.items || []}
            total={incomingQuery.data?.total || 0}
            isLoading={incomingQuery.isLoading}
            error={incomingQuery.error}
            page={page}
            rowsPerPage={rowsPerPage}
            onPageChange={setPage}
            onRowsPerPageChange={setRowsPerPage}
          />
        </TabPanel>
        <TabPanel value={tabValue} index={1}>
          <DataTable
            instances={stagingQuery.data?.items || []}
            total={stagingQuery.data?.total || 0}
            isLoading={stagingQuery.isLoading}
            error={stagingQuery.error}
            onViewDetails={handleViewDetails}
            status="staging"
            page={page}
            rowsPerPage={rowsPerPage}
            onPageChange={setPage}
            onRowsPerPageChange={setRowsPerPage}
          />
        </TabPanel>
        <TabPanel value={tabValue} index={2}>
          <Stack spacing={2}>
            <QASnapshotCard
              data={eseCandidates}
              isLoading={eseLoading}
              onRefresh={refetchESE}
              onOpenQA={() => navigate("/qa")}
            />
            <DataTable
              instances={publishedQuery.data?.items || []}
              total={publishedQuery.data?.total || 0}
              isLoading={publishedQuery.isLoading}
              error={publishedQuery.error}
              onViewDetails={handleViewDetails}
              status="published"
              page={page}
              rowsPerPage={rowsPerPage}
              onPageChange={setPage}
              onRowsPerPageChange={setRowsPerPage}
            />
          </Stack>
        </TabPanel>
      </Box>
    </>
  );
}

interface DataTableProps {
  instances: DataInstance[];
  total: number;
  isLoading: boolean;
  error: Error | null;
  onViewDetails: (instance: DataInstance) => void;
  status: "staging" | "published";
  page: number;
  rowsPerPage: number;
  onPageChange: (page: number) => void;
  onRowsPerPageChange: (rowsPerPage: number) => void;
}

function DataTable({
  instances,
  total,
  isLoading,
  error,
  onViewDetails,
  status,
  page,
  rowsPerPage,
  onPageChange,
  onRowsPerPageChange,
}: DataTableProps) {
  if (error) {
    return <Alert severity="error">Failed to load data: {error.message}</Alert>;
  }

  if (isLoading) {
    return <SkeletonLoader variant="table" rows={5} columns={4} />;
  }

  if (instances.length === 0) {
    return (
      <EmptyState
        icon={<StorageIcon sx={{ fontSize: 64, color: "text.secondary" }} />}
        title={`No ${status} data found`}
        description="Data products will appear here once the pipeline processes observations. Check the pipeline status or start a new workflow to generate data."
        actions={[
          <Button
            key="pipeline"
            variant="contained"
            onClick={() => navigate("/pipeline-operations")}
          >
            View Pipeline
          </Button>,
          <Button key="control" variant="outlined" onClick={() => navigate("/pipeline-control")}>
            Start Processing
          </Button>,
        ]}
      />
    );
  }

  return (
    <TableContainer
      component={Paper}
      sx={{
        "& .MuiTable-root": {
          "& .MuiTableHead-root .MuiTableRow-root": {
            backgroundColor: "background.paper",
            "& .MuiTableCell-head": {
              fontWeight: 600,
              backgroundColor: "action.hover",
            },
          },
          "& .MuiTableBody-root .MuiTableRow-root": {
            "&:nth-of-type(even)": {
              backgroundColor: alpha("#fff", 0.02),
            },
            "&:hover": {
              backgroundColor: "action.hover",
              cursor: "pointer",
            },
            transition: "background-color 0.2s ease",
          },
        },
      }}
    >
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>QA Status</TableCell>
            <TableCell>Finalization</TableCell>
            <TableCell>Auto-Publish</TableCell>
            <TableCell>Created</TableCell>
            {status === "published" && <TableCell>Published</TableCell>}
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {instances.map((instance) => (
            <TableRow key={instance.id} hover>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {instance.id}
                </Typography>
              </TableCell>
              <TableCell>
                <Chip
                  label={DATA_TYPE_LABELS[instance.data_type] || instance.data_type}
                  size="small"
                  variant="outlined"
                />
              </TableCell>
              <TableCell>
                <Chip label={instance.status} color={STATUS_COLORS[instance.status]} size="small" />
              </TableCell>
              <TableCell>
                {instance.qa_status ? (
                  <Chip
                    label={instance.qa_status}
                    color={QA_STATUS_COLORS[instance.qa_status] || "default"}
                    size="small"
                    icon={
                      instance.qa_status === "passed" ? (
                        <CheckCircle fontSize="small" />
                      ) : instance.qa_status === "failed" ? (
                        <ErrorIcon fontSize="small" />
                      ) : instance.qa_status === "warning" ? (
                        <Warning fontSize="small" />
                      ) : (
                        <Pending fontSize="small" />
                      )
                    }
                  />
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    N/A
                  </Typography>
                )}
              </TableCell>
              <TableCell>
                <Chip
                  label={instance.finalization_status}
                  color={
                    instance.finalization_status === "finalized"
                      ? "success"
                      : instance.finalization_status === "failed"
                        ? "error"
                        : "default"
                  }
                  size="small"
                />
              </TableCell>
              <TableCell>
                {instance.auto_publish_enabled ? (
                  <Chip label="Enabled" color="success" size="small" />
                ) : (
                  <Chip label="Disabled" size="small" variant="outlined" />
                )}
              </TableCell>
              <TableCell>
                <Typography variant="body2">
                  {formatDate(parseInt(instance.created_at, 10))}
                </Typography>
              </TableCell>
              {status === "published" && (
                <TableCell>
                  {instance.published_at ? (
                    <Typography variant="body2">
                      {formatDate(parseInt(instance.published_at, 10))}
                    </Typography>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      N/A
                    </Typography>
                  )}
                </TableCell>
              )}
              <TableCell align="right">
                <Tooltip title="View Details">
                  <IconButton size="small" onClick={() => onViewDetails(instance)}>
                    <Visibility />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <TablePagination
        component="div"
        count={total}
        page={page}
        onPageChange={(_, newPage) => onPageChange(newPage)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => {
          onRowsPerPageChange(parseInt(e.target.value, 10));
          onPageChange(0); // Reset to first page when changing page size
        }}
        rowsPerPageOptions={[25, 50, 100]}
        labelRowsPerPage="Rows per page:"
      />
    </TableContainer>
  );
}

interface IncomingDataTableProps {
  files: Array<{
    path: string;
    timestamp: string | null;
    subband: string | null;
    size_mb: number | null;
  }>;
  total: number;
  isLoading: boolean;
  error: Error | null;
  page: number;
  rowsPerPage: number;
  onPageChange: (page: number) => void;
  onRowsPerPageChange: (rowsPerPage: number) => void;
}

function IncomingDataTable({
  files,
  total,
  isLoading,
  error,
  page,
  rowsPerPage,
  onPageChange,
  onRowsPerPageChange,
}: IncomingDataTableProps) {
  const formatDate = (timestamp: string | null) => {
    if (!timestamp) return "N/A";
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const formatSize = (sizeMb: number | null) => {
    if (sizeMb === null) return "N/A";
    if (sizeMb < 1024) {
      return `${sizeMb.toFixed(2)} MB`;
    }
    return `${(sizeMb / 1024).toFixed(2)} GB`;
  };

  if (error) {
    return <Alert severity="error">Failed to load incoming files: {error.message}</Alert>;
  }

  if (isLoading) {
    return <SkeletonLoader variant="table" rows={5} columns={4} />;
  }

  if (files.length === 0) {
    return (
      <EmptyState
        icon={<FolderOpen sx={{ fontSize: 64, color: "text.secondary" }} />}
        title="No incoming files found"
        description="No HDF5 files found in /data/incoming/. New observation files will appear here once they are received."
      />
    );
  }

  return (
    <TableContainer
      component={Paper}
      sx={{
        "& .MuiTable-root": {
          "& .MuiTableHead-root .MuiTableRow-root": {
            backgroundColor: "background.paper",
            "& .MuiTableCell-head": {
              fontWeight: 600,
              backgroundColor: "action.hover",
            },
          },
          "& .MuiTableBody-root .MuiTableRow-root": {
            "&:nth-of-type(even)": {
              backgroundColor: alpha("#fff", 0.02),
            },
            "&:hover": {
              backgroundColor: "action.hover",
              cursor: "pointer",
            },
            transition: "background-color 0.2s ease",
          },
        },
      }}
    >
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Filename</TableCell>
            <TableCell>Timestamp</TableCell>
            <TableCell>Subband</TableCell>
            <TableCell>Size</TableCell>
            <TableCell>Path</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {files.map((file) => (
            <TableRow key={file.path}>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {file.path.split("/").pop()}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2">{formatDate(file.timestamp)}</Typography>
              </TableCell>
              <TableCell>
                {file.subband ? (
                  <Chip label={file.subband} size="small" />
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    N/A
                  </Typography>
                )}
              </TableCell>
              <TableCell>
                <Typography variant="body2">{formatSize(file.size_mb)}</Typography>
              </TableCell>
              <TableCell>
                <Tooltip title={file.path}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontFamily: "monospace",
                      fontSize: "0.75rem",
                      color: "text.secondary",
                      maxWidth: 400,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {file.path}
                  </Typography>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <TablePagination
        component="div"
        count={total}
        page={page}
        onPageChange={(_, newPage) => onPageChange(newPage)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => {
          onRowsPerPageChange(parseInt(e.target.value, 10));
          onPageChange(0); // Reset to first page when changing page size
        }}
        rowsPerPageOptions={[25, 50, 100, 200]}
        labelRowsPerPage="Rows per page:"
      />
    </TableContainer>
  );
}
