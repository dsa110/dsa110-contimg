/**
 * ImageBrowser Component - Browse and select images for SkyView
 */
import { useState } from 'react';
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
} from '@mui/material';
import { useImages } from '../../api/queries';
import type { ImageInfo, ImageFilters } from '../../api/types';
import dayjs from 'dayjs';

interface ImageBrowserProps {
  onSelectImage: (image: ImageInfo | null) => void;
  selectedImageId?: number;
}

export default function ImageBrowser({ onSelectImage, selectedImageId }: ImageBrowserProps) {
  const [filters, setFilters] = useState<ImageFilters>({
    limit: 50,
    offset: 0,
  });
  const [searchPath, setSearchPath] = useState('');

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

  return (
    <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" gutterBottom>
        Image Browser
      </Typography>

      {/* Filters */}
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
  );
}

