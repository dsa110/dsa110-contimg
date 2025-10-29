/**
 * Source Monitoring Page
 * AG Grid table for per-source flux timeseries monitoring
 */
import { useState, useMemo, useRef } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  TextField,
  Button,
  Alert,
} from '@mui/material';
import { Search } from '@mui/icons-material';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { useSourceSearch } from '../api/queries';
import type { SourceTimeseries } from '../api/types';

export default function SourceMonitoringPage() {
  const [sourceId, setSourceId] = useState('');
  const [searchRequest, setSearchRequest] = useState<{ source_id: string } | null>(null);
  const gridRef = useRef<AgGridReact>(null);

  const { data, isLoading, error } = useSourceSearch(searchRequest);

  const handleSearch = () => {
    if (sourceId.trim()) {
      setSearchRequest({ source_id: sourceId.trim() });
    }
  };

  const columnDefs = useMemo<ColDef<SourceTimeseries>[]>(
    () => [
      {
        field: 'source_id',
        headerName: 'Source ID',
        width: 200,
        pinned: 'left',
        cellStyle: { fontFamily: 'monospace' },
      },
      {
        field: 'ra_deg',
        headerName: 'RA (deg)',
        width: 120,
        valueFormatter: (params) => params.value?.toFixed(5),
      },
      {
        field: 'dec_deg',
        headerName: 'Dec (deg)',
        width: 120,
        valueFormatter: (params) => params.value?.toFixed(5),
      },
      {
        field: 'catalog',
        headerName: 'Catalog',
        width: 100,
      },
      {
        field: 'mean_flux_jy',
        headerName: 'Mean Flux (mJy)',
        width: 140,
        valueFormatter: (params) => (params.value * 1000).toFixed(2),
      },
      {
        field: 'std_flux_jy',
        headerName: 'Std Dev (mJy)',
        width: 140,
        valueFormatter: (params) => (params.value * 1000).toFixed(2),
      },
      {
        field: 'chi_sq_nu',
        headerName: 'χ²/ν',
        width: 100,
        valueFormatter: (params) => params.value?.toFixed(2),
        cellStyle: (params) => {
          if (params.value && params.value > 5) {
            return { backgroundColor: 'rgba(244, 67, 54, 0.1)', color: '#f44336' };
          }
          return undefined;
        },
      },
      {
        field: 'is_variable',
        headerName: 'Variable?',
        width: 110,
        cellRenderer: (params: any) => (
          <span style={{ color: params.value ? '#f44336' : '#4caf50' }}>
            {params.value ? '✓ Yes' : '− No'}
          </span>
        ),
      },
      {
        field: 'flux_points',
        headerName: 'Observations',
        width: 130,
        valueFormatter: (params) => `${params.value?.length || 0} points`,
      },
    ],
    []
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
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h3" gutterBottom sx={{ mb: 4 }}>
        Source Monitoring
      </Typography>

      {/* Search Interface */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Search Sources
        </Typography>
        <Box display="flex" gap={2} alignItems="center">
          <TextField
            label="Source ID (e.g., NVSS J123456.7+420312)"
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            size="small"
            sx={{ flexGrow: 1, maxWidth: 400 }}
          />
          <Button
            variant="contained"
            startIcon={<Search />}
            onClick={handleSearch}
            disabled={!sourceId.trim()}
          >
            Search
          </Button>
        </Box>
      </Paper>

      {/* Results Table */}
      {error && (
        <Alert severity="warning">
          Source monitoring not available. This feature requires enhanced API endpoints.
        </Alert>
      )}

      {!error && (
        <Paper sx={{ p: 2 }}>
          <Box
            className="ag-theme-alpine-dark"
            sx={{ height: 600, width: '100%' }}
          >
            <AgGridReact
              ref={gridRef}
              rowData={data?.sources || []}
              columnDefs={columnDefs}
              defaultColDef={defaultColDef}
              pagination={true}
              paginationPageSize={20}
              loading={isLoading}
              loadingOverlayComponent={() => (
                <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                  <Typography>Loading sources...</Typography>
                </Box>
              )}
              noRowsOverlayComponent={() => (
                <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                  <Typography color="text.secondary">
                    {searchRequest ? 'No sources found' : 'Enter a source ID to search'}
                  </Typography>
                </Box>
              )}
            />
          </Box>
        </Paper>
      )}
    </Container>
  );
}

