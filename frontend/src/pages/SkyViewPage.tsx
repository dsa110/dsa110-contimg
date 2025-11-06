/**
 * Sky View Page
 * JS9 FITS image viewer integration
 */
import { useState } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  Stack,
  Grid,
} from '@mui/material';
import ImageBrowser from '../components/Sky/ImageBrowser';
import SkyViewer from '../components/Sky/SkyViewer';
import type { ImageInfo } from '../api/types';

export default function SkyViewPage() {
  const [selectedImage, setSelectedImage] = useState<ImageInfo | null>(null);

  // Construct FITS URL for selected image
  const fitsUrl = selectedImage
    ? `/api/images/${selectedImage.id}/fits`
    : null;

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h3" gutterBottom sx={{ mb: 4 }}>
        Sky View
      </Typography>

      <Grid container spacing={3}>
        {/* Image Browser Sidebar */}
        <Grid item xs={12} md={4}>
          <ImageBrowser
            onSelectImage={setSelectedImage}
            selectedImageId={selectedImage?.id}
          />
        </Grid>

        {/* Main Image Display */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
              Image Display
            </Typography>
            
            {selectedImage && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  <strong>Image:</strong> {selectedImage.path.split('/').pop()}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Type:</strong> {selectedImage.type}
                  {selectedImage.pbcor && ' (PB Corrected)'}
                </Typography>
                {selectedImage.noise_jy && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>Noise:</strong> {(selectedImage.noise_jy * 1000).toFixed(2)} mJy
                  </Typography>
                )}
                {selectedImage.beam_major_arcsec && (
                  <Typography variant="body2" color="text.secondary">
                    <strong>Beam:</strong> {selectedImage.beam_major_arcsec.toFixed(1)}"
                  </Typography>
                )}
              </Box>
            )}

            <SkyViewer
              imagePath={fitsUrl}
              displayId="skyViewDisplay"
              height={600}
            />
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

