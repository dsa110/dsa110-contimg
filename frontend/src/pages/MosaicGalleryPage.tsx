/**
 * Mosaic Gallery Page
 * Time-range query interface for hour-long mosaics
 */
import { useState } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  Button,
  Card,
  CardMedia,
  CardContent,
  CardActions,
  Alert,
  CircularProgress,
  Chip,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { Download, ImageSearch } from '@mui/icons-material';
import dayjs, { Dayjs } from 'dayjs';
import { useMosaicQuery, useCreateMosaic } from '../api/queries';
import type { Mosaic } from '../api/types';

export default function MosaicGalleryPage() {
  const [startTime, setStartTime] = useState<Dayjs | null>(dayjs().subtract(1, 'hour'));
  const [endTime, setEndTime] = useState<Dayjs | null>(dayjs());
  const [queryRequest, setQueryRequest] = useState<{ start_time: string; end_time: string } | null>(
    null
  );

  const { data, isLoading, error } = useMosaicQuery(queryRequest);
  const createMosaic = useCreateMosaic();

  const handleQuery = () => {
    if (startTime && endTime) {
      setQueryRequest({
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
      });
    }
  };

  const handleCreateMosaic = () => {
    if (startTime && endTime) {
      createMosaic.mutate({
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
      });
    }
  };

  const getMosaicStatus = (mosaic: Mosaic) => {
    switch (mosaic.status) {
      case 'completed':
        return { color: 'success' as const, label: 'Completed' };
      case 'in_progress':
        return { color: 'info' as const, label: 'In Progress' };
      case 'pending':
        return { color: 'warning' as const, label: 'Pending' };
      case 'failed':
        return { color: 'error' as const, label: 'Failed' };
      default:
        return { color: 'default' as const, label: mosaic.status };
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Typography variant="h3" gutterBottom sx={{ mb: 4 }}>
          Mosaic Gallery
        </Typography>

        {/* Query Interface */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h5" gutterBottom>
            Time Range Query
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Generate or query mosaics from ~hour-long observations
          </Typography>

          <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
            <DateTimePicker
              label="Start Time (UTC)"
              value={startTime}
              onChange={setStartTime}
              slotProps={{ textField: { size: 'small' } }}
            />
            <DateTimePicker
              label="End Time (UTC)"
              value={endTime}
              onChange={setEndTime}
              slotProps={{ textField: { size: 'small' } }}
            />
            <Button
              variant="contained"
              startIcon={<ImageSearch />}
              onClick={handleQuery}
              disabled={!startTime || !endTime}
            >
              Query Mosaics
            </Button>
            <Button
              variant="outlined"
              onClick={handleCreateMosaic}
              disabled={!startTime || !endTime || createMosaic.isPending}
            >
              {createMosaic.isPending ? 'Creating...' : 'Create New Mosaic'}
            </Button>
          </Box>

          {startTime && endTime && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Duration: {endTime.diff(startTime, 'minute')} minutes (
              {endTime.diff(startTime, 'hour', true).toFixed(2)} hours)
            </Alert>
          )}
        </Paper>

        {/* Results */}
        {isLoading && (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="warning">
            Mosaic query not available. This feature requires enhanced API endpoints.
          </Alert>
        )}

        {data && data.mosaics.length === 0 && queryRequest && (
          <Alert severity="info">
            No mosaics found for the selected time range. Try creating a new one!
          </Alert>
        )}

        {data && data.mosaics.length > 0 && (
          <>
            <Typography variant="h6" gutterBottom>
              Found {data.total} mosaic{data.total !== 1 ? 's' : ''}
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' }, gap: 3 }}>
              {data.mosaics.map((mosaic) => {
                const status = getMosaicStatus(mosaic);
                return (
                  <Box key={mosaic.id}>
                    <Card>
                      <CardMedia
                        component="div"
                        sx={{
                          height: 200,
                          bgcolor: '#1e1e1e',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {mosaic.thumbnail_path ? (
                          <img
                            src={mosaic.thumbnail_path}
                            alt={mosaic.name}
                            style={{ maxWidth: '100%', maxHeight: '100%' }}
                          />
                        ) : (
                          <Typography color="text.secondary">
                            Preview not available
                          </Typography>
                        )}
                      </CardMedia>
                      <CardContent>
                        <Box display="flex" justifyContent="space-between" alignItems="start" mb={1}>
                          <Typography variant="h6" component="div" noWrap>
                            {mosaic.name}
                          </Typography>
                          <Chip label={status.label} color={status.color} size="small" />
                        </Box>
                        <Typography variant="body2" color="text.secondary">
                          {new Date(mosaic.start_time).toLocaleString()} →<br />
                          {new Date(mosaic.end_time).toLocaleString()}
                        </Typography>
                        <Box mt={2} display="flex" gap={2} flexWrap="wrap">
                          <Chip
                            label={`${mosaic.source_count} sources`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`${(mosaic.noise_jy * 1000).toFixed(2)} mJy noise`}
                            size="small"
                            variant="outlined"
                          />
                          <Chip
                            label={`${mosaic.image_count} images`}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      </CardContent>
                      <CardActions>
                        <Button size="small" startIcon={<Download />}>
                          FITS
                        </Button>
                        <Button size="small" startIcon={<Download />}>
                          PNG
                        </Button>
                        <Button size="small">View</Button>
                      </CardActions>
                    </Card>
                  </Box>
                );
              })}
            </Box>
          </>
        )}
      </Container>
    </LocalizationProvider>
  );
}

