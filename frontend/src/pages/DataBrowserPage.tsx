/**
 * Data Browser Page - Main data management interface
 */
import { useState } from 'react';
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
  Chip,
  IconButton,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  CloudUpload,
  CloudDone,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Pending,
  Visibility,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useDataInstances } from '../api/queries';
import type { DataInstance } from '../api/types';

const DATA_TYPE_LABELS: Record<string, string> = {
  ms: 'MS',
  calib_ms: 'Calibrated MS',
  caltable: 'Calibration Table',
  image: 'Image',
  mosaic: 'Mosaic',
  catalog: 'Catalog',
  qa: 'QA Report',
  metadata: 'Metadata',
};

const STATUS_COLORS: Record<string, 'default' | 'primary' | 'success' | 'warning' | 'error'> = {
  staging: 'warning',
  published: 'success',
};

const QA_STATUS_COLORS: Record<string, 'default' | 'success' | 'warning' | 'error'> = {
  passed: 'success',
  failed: 'error',
  warning: 'warning',
  pending: 'default',
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
  const [dataTypeFilter, setDataTypeFilter] = useState<string>('all');
  const navigate = useNavigate();

  // Fetch data based on tab (staging vs published)
  const status = tabValue === 0 ? 'staging' : 'published';
  const { data: instances, isLoading, error } = useDataInstances(
    dataTypeFilter !== 'all' ? dataTypeFilter : undefined,
    status
  );

  const filteredInstances = instances || [];

  const handleViewDetails = (instance: DataInstance) => {
    navigate(`/data/${instance.data_type}/${instance.id}`);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Data Browser
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Manage and browse all pipeline data products
      </Typography>

      <Paper sx={{ mb: 2 }}>
        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
          <Tab
            icon={<CloudUpload />}
            iconPosition="start"
            label="Staging"
            sx={{ textTransform: 'none' }}
          />
          <Tab
            icon={<CloudDone />}
            iconPosition="start"
            label="Published"
            sx={{ textTransform: 'none' }}
          />
        </Tabs>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
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
        </Box>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <DataTable
          instances={filteredInstances}
          isLoading={isLoading}
          error={error}
          onViewDetails={handleViewDetails}
          status="staging"
        />
      </TabPanel>
      <TabPanel value={tabValue} index={1}>
        <DataTable
          instances={filteredInstances}
          isLoading={isLoading}
          error={error}
          onViewDetails={handleViewDetails}
          status="published"
        />
      </TabPanel>
    </Box>
  );
}

interface DataTableProps {
  instances: DataInstance[];
  isLoading: boolean;
  error: Error | null;
  onViewDetails: (instance: DataInstance) => void;
  status: 'staging' | 'published';
}

function DataTable({ instances, isLoading, error, onViewDetails, status }: DataTableProps) {
  if (error) {
    return (
      <Alert severity="error">
        Failed to load data: {error.message}
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (instances.length === 0) {
    return (
      <Alert severity="info">
        No {status} data found. Data will appear here once it's created by the pipeline.
      </Alert>
    );
  }

  return (
    <TableContainer component={Paper}>
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
            {status === 'published' && <TableCell>Published</TableCell>}
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {instances.map((instance) => (
            <TableRow key={instance.id} hover>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
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
                <Chip
                  label={instance.status}
                  color={STATUS_COLORS[instance.status]}
                  size="small"
                />
              </TableCell>
              <TableCell>
                {instance.qa_status ? (
                  <Chip
                    label={instance.qa_status}
                    color={QA_STATUS_COLORS[instance.qa_status] || 'default'}
                    size="small"
                    icon={
                      instance.qa_status === 'passed' ? (
                        <CheckCircle fontSize="small" />
                      ) : instance.qa_status === 'failed' ? (
                        <ErrorIcon fontSize="small" />
                      ) : instance.qa_status === 'warning' ? (
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
                    instance.finalization_status === 'finalized'
                      ? 'success'
                      : instance.finalization_status === 'failed'
                      ? 'error'
                      : 'default'
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
                  {formatDate(instance.created_at)}
                </Typography>
              </TableCell>
              {status === 'published' && (
                <TableCell>
                  {instance.published_at ? (
                    <Typography variant="body2">
                      {formatDate(instance.published_at)}
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
                  <IconButton
                    size="small"
                    onClick={() => onViewDetails(instance)}
                  >
                    <Visibility />
                  </IconButton>
                </Tooltip>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
