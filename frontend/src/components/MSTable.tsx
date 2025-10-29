/**
 * MSTable Component
 * 
 * Advanced table for displaying Measurement Sets with:
 * - Search and filtering
 * - Sortable columns
 * - Status badges
 * - Multi-select for batch operations
 * - Pagination
 * 
 * @module components/MSTable
 */

import { useState, useMemo } from 'react';
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
  Checkbox,
  Chip,
  TextField,
  InputAdornment,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Pagination,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  Search as SearchIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import type { MSListEntry, MSListFilters } from '../api/types';

interface MSTableProps {
  /** Array of MS entries to display */
  data: MSListEntry[];
  /** Total count before filtering */
  total?: number;
  /** Filtered count */
  filtered?: number;
  /** Currently selected MS paths */
  selected: string[];
  /** Callback when selection changes */
  onSelectionChange: (selected: string[]) => void;
  /** Callback when an MS is clicked */
  onMSClick?: (ms: MSListEntry) => void;
  /** Callback when filters change */
  onFiltersChange?: (filters: MSListFilters) => void;
  /** Loading state */
  loading?: boolean;
  /** Callback to refresh data */
  onRefresh?: () => void;
}

type SortField = 'path' | 'start_time' | 'calibrator_name' | 'size_gb';
type SortDirection = 'asc' | 'desc';

/**
 * Get color for quality badge
 */
function getQualityColor(quality?: string): 'success' | 'warning' | 'error' | 'default' {
  switch (quality) {
    case 'excellent': return 'success';
    case 'good': return 'success';
    case 'marginal': return 'warning';
    case 'poor': return 'error';
    default: return 'default';
  }
}

/**
 * Format file size in GB
 */
function formatSize(sizeGb?: number): string {
  if (!sizeGb) return '-';
  return `${sizeGb.toFixed(1)} GB`;
}

/**
 * Format timestamp
 */
function formatTime(isoString?: string): string {
  if (!isoString) return '-';
  try {
    const date = new Date(isoString);
    return date.toISOString().replace('T', ' ').slice(0, 19);
  } catch {
    return isoString;
  }
}

/**
 * Extract filename from path
 */
function getFilename(path: string): string {
  const parts = path.split('/');
  return parts[parts.length - 1] || path;
}

export default function MSTable({
  data,
  total: _total = 0,
  filtered: _filtered = 0,
  selected,
  onSelectionChange,
  onMSClick,
  onFiltersChange: _onFiltersChange,
  loading = false,
  onRefresh,
}: MSTableProps) {
  // Local filter state
  const [searchText, setSearchText] = useState('');
  const [filterCalibrator, setFilterCalibrator] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('start_time');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [page, setPage] = useState(1);
  const [rowsPerPage] = useState(25);

  // Apply local filters and sorting
  const filteredAndSortedData = useMemo(() => {
    let result = [...data];

    // Search filter
    if (searchText) {
      const search = searchText.toLowerCase();
      result = result.filter(
        ms =>
          ms.path.toLowerCase().includes(search) ||
          ms.calibrator_name?.toLowerCase().includes(search)
      );
    }

    // Calibrator filter
    if (filterCalibrator !== 'all') {
      if (filterCalibrator === 'yes') {
        result = result.filter(ms => ms.has_calibrator);
      } else if (filterCalibrator === 'no') {
        result = result.filter(ms => !ms.has_calibrator);
      }
    }

    // Status filter
    if (filterStatus === 'calibrated') {
      result = result.filter(ms => ms.is_calibrated);
    } else if (filterStatus === 'imaged') {
      result = result.filter(ms => ms.is_imaged);
    } else if (filterStatus === 'uncalibrated') {
      result = result.filter(ms => !ms.is_calibrated);
    }

    // Sort
    result.sort((a, b) => {
      let aVal: any;
      let bVal: any;

      switch (sortField) {
        case 'path':
          aVal = a.path;
          bVal = b.path;
          break;
        case 'start_time':
          aVal = a.start_time || '';
          bVal = b.start_time || '';
          break;
        case 'calibrator_name':
          aVal = a.calibrator_name || '';
          bVal = b.calibrator_name || '';
          break;
        case 'size_gb':
          aVal = a.size_gb || 0;
          bVal = b.size_gb || 0;
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [data, searchText, filterCalibrator, filterStatus, sortField, sortDirection]);

  // Paginate
  const paginatedData = useMemo(() => {
    const start = (page - 1) * rowsPerPage;
    return filteredAndSortedData.slice(start, start + rowsPerPage);
  }, [filteredAndSortedData, page, rowsPerPage]);

  const pageCount = Math.ceil(filteredAndSortedData.length / rowsPerPage);

  // Selection handlers
  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      onSelectionChange(paginatedData.map(ms => ms.path));
    } else {
      onSelectionChange([]);
    }
  };

  const handleSelectOne = (path: string) => {
    const isSelected = selected.includes(path);
    if (isSelected) {
      onSelectionChange(selected.filter(p => p !== path));
    } else {
      onSelectionChange([...selected, path]);
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const isAllSelected = paginatedData.length > 0 && paginatedData.every(ms => selected.includes(ms.path));
  const isSomeSelected = paginatedData.some(ms => selected.includes(ms.path)) && !isAllSelected;

  return (
    <Box>
      {/* Filters and Search */}
      <Stack direction="row" spacing={2} sx={{ mb: 2 }} alignItems="center">
        <TextField
          size="small"
          placeholder="Search MS or calibrator..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
          sx={{ flexGrow: 1 }}
        />
        
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Calibrator</InputLabel>
          <Select
            value={filterCalibrator}
            onChange={(e) => setFilterCalibrator(e.target.value)}
            label="Calibrator"
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="yes">Has Calibrator</MenuItem>
            <MenuItem value="no">No Calibrator</MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            label="Status"
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="calibrated">Calibrated</MenuItem>
            <MenuItem value="imaged">Imaged</MenuItem>
            <MenuItem value="uncalibrated">Uncalibrated</MenuItem>
          </Select>
        </FormControl>

        {onRefresh && (
          <Tooltip title="Refresh">
            <IconButton onClick={onRefresh} size="small">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        )}
      </Stack>

      {/* Summary */}
      <Typography variant="caption" sx={{ display: 'block', mb: 1, color: 'text.secondary' }}>
        Showing {paginatedData.length} of {filteredAndSortedData.length} MS
        {selected.length > 0 && ` (${selected.length} selected)`}
      </Typography>

      {/* Table */}
      <TableContainer component={Paper} sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  indeterminate={isSomeSelected}
                  checked={isAllSelected}
                  onChange={handleSelectAll}
                  disabled={loading}
                />
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortField === 'path'}
                  direction={sortField === 'path' ? sortDirection : 'asc'}
                  onClick={() => handleSort('path')}
                >
                  MS Name
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortField === 'start_time'}
                  direction={sortField === 'start_time' ? sortDirection : 'asc'}
                  onClick={() => handleSort('start_time')}
                >
                  Time
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortField === 'calibrator_name'}
                  direction={sortField === 'calibrator_name' ? sortDirection : 'asc'}
                  onClick={() => handleSort('calibrator_name')}
                >
                  Calibrator
                </TableSortLabel>
              </TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Quality</TableCell>
              <TableCell align="right">
                <TableSortLabel
                  active={sortField === 'size_gb'}
                  direction={sortField === 'size_gb' ? sortDirection : 'asc'}
                  onClick={() => handleSort('size_gb')}
                >
                  Size
                </TableSortLabel>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedData.map((ms) => {
              const isSelected = selected.includes(ms.path);
              
              return (
                <TableRow
                  key={ms.path}
                  hover
                  onClick={() => onMSClick?.(ms)}
                  selected={isSelected}
                  sx={{ cursor: onMSClick ? 'pointer' : 'default' }}
                >
                  <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={isSelected}
                      onChange={() => handleSelectOne(ms.path)}
                    />
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                    {getFilename(ms.path)}
                  </TableCell>
                  <TableCell sx={{ fontSize: '0.75rem' }}>
                    {formatTime(ms.start_time)}
                  </TableCell>
                  <TableCell>
                    {ms.has_calibrator ? (
                      <Stack direction="row" spacing={0.5} alignItems="center">
                        <Tooltip title={`Quality: ${ms.calibrator_quality || 'unknown'}`}>
                          <Chip
                            label={ms.calibrator_name || 'Unknown'}
                            size="small"
                            color={getQualityColor(ms.calibrator_quality)}
                            sx={{ fontSize: '0.7rem', height: 20 }}
                          />
                        </Tooltip>
                      </Stack>
                    ) : (
                      <Chip
                        icon={<WarningIcon />}
                        label="None"
                        size="small"
                        color="default"
                        sx={{ fontSize: '0.7rem', height: 20 }}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5}>
                      {ms.is_calibrated && (
                        <Tooltip title={`Cal: ${ms.calibration_quality || 'unknown'}`}>
                          <Chip
                            icon={<CheckIcon />}
                            label="Cal"
                            size="small"
                            color="primary"
                            sx={{ fontSize: '0.65rem', height: 18 }}
                          />
                        </Tooltip>
                      )}
                      {ms.is_imaged && (
                        <Tooltip title={`Img: ${ms.image_quality || 'unknown'}`}>
                          <Chip
                            icon={<CheckIcon />}
                            label="Img"
                            size="small"
                            color="secondary"
                            sx={{ fontSize: '0.65rem', height: 18 }}
                          />
                        </Tooltip>
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    {ms.calibration_quality && (
                      <Chip
                        label={ms.calibration_quality}
                        size="small"
                        color={getQualityColor(ms.calibration_quality)}
                        sx={{ fontSize: '0.65rem', height: 18, mr: 0.5 }}
                      />
                    )}
                    {ms.image_quality && (
                      <Chip
                        label={ms.image_quality}
                        size="small"
                        color={getQualityColor(ms.image_quality)}
                        sx={{ fontSize: '0.65rem', height: 18 }}
                      />
                    )}
                  </TableCell>
                  <TableCell align="right" sx={{ fontSize: '0.75rem' }}>
                    {formatSize(ms.size_gb)}
                  </TableCell>
                </TableRow>
              );
            })}
            {paginatedData.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    {loading ? 'Loading...' : 'No MS files found'}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {pageCount > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <Pagination
            count={pageCount}
            page={page}
            onChange={(_, value) => setPage(value)}
            color="primary"
            showFirstButton
            showLastButton
          />
        </Box>
      )}
    </Box>
  );
}

