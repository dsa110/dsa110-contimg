/**
 * ImageBrowser Component - Browse and select images for SkyView
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  CircularProgress,
  Alert,
  Stack,
  Divider,
  Slider,
  FormControlLabel,
  Checkbox,
  Collapse,
  IconButton,
  Button,
} from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { useSearchParams } from 'react-router-dom';
import { useImages } from '../../api/queries';
import type { ImageInfo, ImageFilters } from '../../api/types';
import dayjs, { Dayjs } from 'dayjs';

interface ImageBrowserProps {
  onSelectImage: (image: ImageInfo | null) => void;
  selectedImageId?: number;
}

export default function ImageBrowser({ onSelectImage, selectedImageId }: ImageBrowserProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  
  // Parse URL params to initialize filters
  const getInitialFilters = (): ImageFilters => {
    const filters: ImageFilters = {
      limit: parseInt(searchParams.get('limit') || '50', 10),
      offset: parseInt(searchParams.get('offset') || '0', 10),
    };
    
    if (searchParams.get('ms_path')) filters.ms_path = searchParams.get('ms_path') || undefined;
    if (searchParams.get('image_type')) filters.image_type = searchParams.get('image_type') || undefined;
    if (searchParams.get('pbcor')) filters.pbcor = searchParams.get('pbcor') === 'true';
    if (searchParams.get('start_date')) filters.start_date = searchParams.get('start_date') || undefined;
    if (searchParams.get('end_date')) filters.end_date = searchParams.get('end_date') || undefined;
    if (searchParams.get('dec_min')) filters.dec_min = parseFloat(searchParams.get('dec_min') || '');
    if (searchParams.get('dec_max')) filters.dec_max = parseFloat(searchParams.get('dec_max') || '');
    if (searchParams.get('noise_max')) filters.noise_max = parseFloat(searchParams.get('noise_max') || '');
    if (searchParams.get('has_calibrator')) filters.has_calibrator = searchParams.get('has_calibrator') === 'true';
    
    return filters;
  };

  const [filters, setFilters] = useState<ImageFilters>(getInitialFilters);
  const [searchPath, setSearchPath] = useState(searchParams.get('ms_path') || '');
  const [startDate, setStartDate] = useState<Dayjs | null>(
    searchParams.get('start_date') ? dayjs(searchParams.get('start_date')) : null
  );
  const [endDate, setEndDate] = useState<Dayjs | null>(
    searchParams.get('end_date') ? dayjs(searchParams.get('end_date')) : null
  );
  const [decRange, setDecRange] = useState<[number, number]>([
    searchParams.get('dec_min') ? parseFloat(searchParams.get('dec_min')!) : -90,
    searchParams.get('dec_max') ? parseFloat(searchParams.get('dec_max')!) : 90,
  ]);
  const [noiseMax, setNoiseMax] = useState<string>(
    searchParams.get('noise_max') 
      ? (parseFloat(searchParams.get('noise_max')!) * 1000).toString() // Convert Jy to mJy for display
      : ''
  );
  const [hasCalibrator, setHasCalibrator] = useState<boolean>(
    searchParams.get('has_calibrator') === 'true'
  );

  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    
    if (filters.limit && filters.limit !== 50) params.set('limit', filters.limit.toString());
    if (filters.offset && filters.offset !== 0) params.set('offset', filters.offset.toString());
    if (filters.ms_path) params.set('ms_path', filters.ms_path);
    if (filters.image_type) params.set('image_type', filters.image_type);
    if (filters.pbcor !== undefined) params.set('pbcor', filters.pbcor.toString());
    if (filters.start_date) params.set('start_date', filters.start_date);
    if (filters.end_date) params.set('end_date', filters.end_date);
    if (filters.dec_min !== undefined) params.set('dec_min', filters.dec_min.toString());
    if (filters.dec_max !== undefined) params.set('dec_max', filters.dec_max.toString());
    if (filters.noise_max !== undefined) params.set('noise_max', filters.noise_max.toString());
    if (filters.has_calibrator !== undefined) params.set('has_calibrator', filters.has_calibrator.toString());
    
    setSearchParams(params, { replace: true });
  }, [filters, setSearchParams]);

  const { data, isLoading, error } = useImages(filters);

  const handleImageClick = (image: ImageInfo) => {
    onSelectImage(image);
  };

  const handleFilterChange = (key: keyof ImageFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value, offset: 0 }));
  };

  const handleSearch = () => {
    setFilters((prev) => ({
      ...prev,
      ms_path: searchPath || undefined,
      offset: 0,
    }));
  };

  const handleStartDateChange = (date: Dayjs | null) => {
    setStartDate(date);
    handleFilterChange('start_date', date ? date.toISOString() : undefined);
  };

  const handleEndDateChange = (date: Dayjs | null) => {
    setEndDate(date);
    handleFilterChange('end_date', date ? date.toISOString() : undefined);
  };

  const handleDecRangeChange = useCallback(
    (_event: Event | React.SyntheticEvent, newValue: number | number[]) => {
      const range = newValue as [number, number];
      setDecRange(range);
      handleFilterChange('dec_min', range[0]);
      handleFilterChange('dec_max', range[1]);
    },
    [handleFilterChange]
  );

  const handleNoiseMaxChange = (value: string) => {
    setNoiseMax(value);
    // Convert mJy to Jy for API (API expects Jy)
    const numValue = value ? parseFloat(value) / 1000 : undefined;
    handleFilterChange('noise_max', numValue);
  };

  const handleCalibratorChange = (checked: boolean) => {
    setHasCalibrator(checked);
    handleFilterChange('has_calibrator', checked || undefined);
  };

  const handleClearFilters = useCallback(() => {
    setStartDate(null);
    setEndDate(null);
    setDecRange([-90, 90]);
    setNoiseMax('');
    setHasCalibrator(false);
    setFilters({ limit: 50, offset: 0 });
    setSearchPath('');
  }, []);

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6">
            Image Browser
          </Typography>
          <IconButton
            size="small"
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            aria-label="toggle advanced filters"
          >
            {showAdvancedFilters ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>

        {/* Basic Filters */}
        <Stack spacing={2} sx={{ mb: 2 }}>
          <TextField
            label="Search MS Path"
            value={searchPath}
            onChange={(e) => setSearchPath(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            size="small"
            fullWidth
          />

          <FormControl fullWidth size="small">
            <InputLabel>Image Type</InputLabel>
            <Select
              value={filters.image_type || ''}
              onChange={(e) => handleFilterChange('image_type', e.target.value || undefined)}
              label="Image Type"
            >
              <MenuItem value="">All Types</MenuItem>
              <MenuItem value="image">Image</MenuItem>
              <MenuItem value="pbcor">PB Corrected</MenuItem>
              <MenuItem value="residual">Residual</MenuItem>
              <MenuItem value="psf">PSF</MenuItem>
              <MenuItem value="pb">Primary Beam</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth size="small">
            <InputLabel>PB Corrected</InputLabel>
            <Select
              value={filters.pbcor === undefined ? '' : filters.pbcor.toString()}
              onChange={(e) => 
                handleFilterChange('pbcor', e.target.value === '' ? undefined : e.target.value === 'true')
              }
              label="PB Corrected"
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="true">Yes</MenuItem>
              <MenuItem value="false">No</MenuItem>
            </Select>
          </FormControl>
        </Stack>

        {/* Advanced Filters */}
        <Collapse in={showAdvancedFilters}>
          <Stack spacing={2} sx={{ mb: 2 }}>
            <Divider />
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="subtitle2" color="text.secondary">
                Advanced Filters
              </Typography>
              <Button size="small" onClick={handleClearFilters} variant="outlined">
                Clear All
              </Button>
            </Box>

            {/* Date Range */}
            <DateTimePicker
              label="Start Date (UTC)"
              value={startDate}
              onChange={handleStartDateChange}
              slotProps={{ textField: { size: 'small', fullWidth: true } }}
            />
            <DateTimePicker
              label="End Date (UTC)"
              value={endDate}
              onChange={handleEndDateChange}
              slotProps={{ textField: { size: 'small', fullWidth: true } }}
            />

            {/* Declination Range */}
            <Box>
              <Typography variant="caption" color="text.secondary" gutterBottom>
                Declination Range: {decRange[0].toFixed(1)}° to {decRange[1].toFixed(1)}°
              </Typography>
              <Slider
                value={decRange}
                onChange={handleDecRangeChange}
                min={-90}
                max={90}
                step={0.1}
                valueLabelDisplay="auto"
                valueLabelFormat={(value) => `${value.toFixed(1)}°`}
                marks={[
                  { value: -90, label: '-90°' },
                  { value: 0, label: '0°' },
                  { value: 90, label: '90°' },
                ]}
              />
            </Box>

            {/* Quality Threshold (Noise Level) */}
            <TextField
              label="Max Noise Level (mJy)"
              type="number"
              value={noiseMax}
              onChange={(e) => handleNoiseMaxChange(e.target.value)}
              size="small"
              fullWidth
              inputProps={{ step: 0.1, min: 0 }}
              helperText="Leave empty for no limit"
            />

            {/* Calibrator Detected Flag */}
            <FormControlLabel
              control={
                <Checkbox
                  checked={hasCalibrator}
                  onChange={(e) => handleCalibratorChange(e.target.checked)}
                />
              }
              label="Has Calibrator Detected"
            />
          </Stack>
        </Collapse>

      <Divider sx={{ my: 1 }} />

      {/* Image List */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress size={24} />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load images
          </Alert>
        )}

        {data && data.items.length === 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            No images found
          </Alert>
        )}

        {data && data.items.length > 0 && (
          <>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              {data.total} image{data.total !== 1 ? 's' : ''} found
            </Typography>
            <List dense>
              {data.items.map((image) => (
                <ListItem key={image.id} disablePadding>
                  <ListItemButton
                    selected={selectedImageId === image.id}
                    onClick={() => handleImageClick(image)}
                    sx={{
                      '&.Mui-selected': {
                        bgcolor: 'primary.main',
                        color: 'primary.contrastText',
                        '&:hover': {
                          bgcolor: 'primary.dark',
                        },
                      },
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box component="span" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" component="span" noWrap sx={{ flexGrow: 1 }}>
                            {image.path.split('/').pop()}
                          </Typography>
                          <Chip
                            label={image.type}
                            size="small"
                            sx={{ height: 20, fontSize: '0.65rem' }}
                          />
                          {image.pbcor && (
                            <Chip
                              label="PB"
                              size="small"
                              color="success"
                              sx={{ height: 20, fontSize: '0.65rem' }}
                            />
                          )}
                        </Box>
                      }
                      secondary={
                        <>
                          <Typography variant="caption" component="span" display="block">
                            {dayjs(image.created_at).format('YYYY-MM-DD HH:mm:ss')}
                          </Typography>
                          {image.noise_jy && (
                            <Typography variant="caption" component="span" display="block" color="text.secondary">
                              Noise: {(image.noise_jy * 1000).toFixed(2)} mJy
                            </Typography>
                          )}
                          {image.beam_major_arcsec && (
                            <Typography variant="caption" component="span" display="block" color="text.secondary">
                              Beam: {image.beam_major_arcsec.toFixed(1)}"
                            </Typography>
                          )}
                        </>
                      }
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </>
        )}
      </Box>
    </Paper>
    </LocalizationProvider>
  );
}

