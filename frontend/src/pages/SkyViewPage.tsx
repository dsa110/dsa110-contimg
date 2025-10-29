/**
 * Sky View Page
 * JS9/Aladin Lite integration for FITS image display
 */
import { useState } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  Button,
  Alert,
  TextField,
  Card,
  CardContent,
  Stack,
} from '@mui/material';
import { ImageSearch, Layers } from '@mui/icons-material';

export default function SkyViewPage() {
  const [imagePath, setImagePath] = useState('');
  const [coordinates, setCoordinates] = useState({ ra: '', dec: '' });

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h3" gutterBottom sx={{ mb: 4 }}>
        Sky View
      </Typography>

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
        {/* Control Panel */}
        <Box sx={{ width: { xs: '100%', md: '300px' } }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Image Controls
            </Typography>

            <Box display="flex" flexDirection="column" gap={2} mt={2}>
              <TextField
                label="RA (degrees)"
                value={coordinates.ra}
                onChange={(e) => setCoordinates({ ...coordinates, ra: e.target.value })}
                size="small"
                type="number"
              />
              <TextField
                label="Dec (degrees)"
                value={coordinates.dec}
                onChange={(e) => setCoordinates({ ...coordinates, dec: e.target.value })}
                size="small"
                type="number"
              />
              <Button variant="contained" startIcon={<ImageSearch />} fullWidth>
                Go To Coordinates
              </Button>

              <Box sx={{ borderTop: 1, borderColor: 'divider', pt: 2, mt: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Image Selection
                </Typography>
                <TextField
                  label="Image Path"
                  value={imagePath}
                  onChange={(e) => setImagePath(e.target.value)}
                  size="small"
                  fullWidth
                  sx={{ mb: 1 }}
                />
                <Button variant="outlined" startIcon={<Layers />} fullWidth>
                  Load Image
                </Button>
              </Box>
            </Box>

            <Card sx={{ mt: 3, bgcolor: 'background.default' }}>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Image Info
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  No image loaded
                </Typography>
              </CardContent>
            </Card>
          </Paper>
        </Box>

        {/* Main Display */}
        <Box sx={{ flexGrow: 1 }}>
          <Paper sx={{ p: 3, minHeight: 600 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              <Typography variant="body2" fontWeight="bold" gutterBottom>
                JS9/Aladin Lite Integration Placeholder
              </Typography>
              <Typography variant="body2">
                This view will display FITS images using JS9 or Aladin Lite for interactive
                visualization. Features include:
              </Typography>
              <Box component="ul" sx={{ mt: 1, mb: 0 }}>
                <li>Pan and zoom controls</li>
                <li>Colormap adjustments</li>
                <li>Source overlay from catalogs</li>
                <li>Coordinate grid display</li>
                <li>Region selection tools</li>
              </Box>
            </Alert>

            <Box
              sx={{
                height: 500,
                bgcolor: '#0a0a0a',
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
              }}
            >
              <Box textAlign="center">
                <Layers sx={{ fontSize: 60, color: 'text.disabled', mb: 2 }} />
                <Typography color="text.secondary" variant="h6">
                  Sky View Display Area
                </Typography>
                <Typography color="text.secondary" variant="body2" sx={{ mt: 1 }}>
                  Load an image or navigate to coordinates to begin
                </Typography>
              </Box>
            </Box>

            <Box mt={2} display="flex" gap={2} justifyContent="space-between">
              <Box display="flex" gap={1}>
                <Button size="small" variant="outlined">
                  Zoom In
                </Button>
                <Button size="small" variant="outlined">
                  Zoom Out
                </Button>
                <Button size="small" variant="outlined">
                  Reset
                </Button>
              </Box>
              <Box display="flex" gap={1}>
                <Button size="small" variant="outlined">
                  Catalog Overlay
                </Button>
                <Button size="small" variant="outlined">
                  Grid
                </Button>
                <Button size="small" variant="outlined">
                  Colormap
                </Button>
              </Box>
            </Box>
          </Paper>
        </Box>
      </Stack>

      {/* Implementation Notes */}
      <Alert severity="warning" sx={{ mt: 3 }}>
        <Typography variant="body2" fontWeight="bold">
          Implementation Note:
        </Typography>
        <Typography variant="body2">
          To fully integrate JS9 or Aladin Lite, you'll need to:
        </Typography>
        <Box component="ol" sx={{ mt: 1, mb: 0, pl: 2 }}>
          <li>
            Install JS9: <code>npm install js9</code> or include via CDN in index.html
          </li>
          <li>
            Or use Aladin Lite: Include script tag in public/index.html and create React wrapper
          </li>
          <li>Add FITS file serving endpoint to backend API</li>
          <li>Configure CORS for external catalog queries</li>
        </Box>
      </Alert>
    </Container>
  );
}

