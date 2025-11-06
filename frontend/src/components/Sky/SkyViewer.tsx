/**
 * SkyViewer Component - JS9 FITS Image Viewer Integration
 */
import { useEffect, useRef, useState } from 'react';
import { Box, CircularProgress, Alert, Typography } from '@mui/material';

declare global {
  interface Window {
    JS9: any;
  }
}

interface SkyViewerProps {
  imagePath: string | null;
  displayId?: string;
  height?: number;
}

export default function SkyViewer({ 
  imagePath, 
  displayId = 'js9Display',
  height = 600 
}: SkyViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  // Initialize JS9 display
  useEffect(() => {
    if (!containerRef.current || initialized) return;

    // Wait for JS9 to be available
    if (!window.JS9) {
      // JS9 might not be loaded yet, wait a bit
      const checkJS9 = setInterval(() => {
        if (window.JS9) {
          clearInterval(checkJS9);
          initializeJS9();
        }
      }, 100);

      return () => clearInterval(checkJS9);
    }

    initializeJS9();

    function initializeJS9() {
      try {
        if (!containerRef.current) return;
        
        // Ensure div has the correct ID for JS9
        if (containerRef.current.id !== displayId) {
          containerRef.current.id = displayId;
        }
        
        // Initialize JS9 globally if needed (only once)
        if (typeof window.JS9.Init === 'function') {
          try {
            window.JS9.Init();
          } catch (initErr) {
            // JS9 may already be initialized, ignore error
            console.debug('JS9 Init:', initErr);
          }
        }
        
        // Add display using JS9 API
        try {
          window.JS9.AddDisplay({
            divID: displayId,
            display: displayId,
            width: '100%',
            height: `${height}px`,
          });
        } catch (addErr) {
          // Display may already exist, that's OK
          console.debug('JS9 AddDisplay:', addErr);
        }
        
        setInitialized(true);
      } catch (err) {
        console.error('JS9 initialization error:', err);
        setError('Failed to initialize JS9 display');
      }
    }
  }, [displayId, height, initialized]);

  // Load image when path changes
  useEffect(() => {
    if (!imagePath || !initialized || !window.JS9) return;

    setLoading(true);
    setError(null);

    try {
      // imagePath should be the full URL to the FITS file endpoint
      // e.g., /api/images/123/fits
      if (!imagePath) {
        setLoading(false);
        return;
      }

      // Load image into JS9 display
      window.JS9.Load(imagePath, {
        display: displayId,
        scale: 'linear',
        colormap: 'grey',
        onload: (im: any) => {
          console.log('FITS image loaded:', im);
          setLoading(false);
        },
        onerror: (err: any) => {
          console.error('JS9 load error:', err);
          setError(`Failed to load image: ${err.message || 'Unknown error'}`);
          setLoading(false);
        },
      });
    } catch (err: any) {
      console.error('Error loading image:', err);
      setError(`Error: ${err.message || 'Unknown error'}`);
      setLoading(false);
    }
  }, [imagePath, displayId, initialized]);

  return (
    <Box sx={{ position: 'relative', width: '100%', height: `${height}px` }}>
      <Box
        id={displayId}
        ref={containerRef}
        sx={{
          width: '100%',
          height: '100%',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          bgcolor: '#0a0a0a',
          position: 'relative',
        }}
      />
      
      {loading && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
          }}
        >
          <CircularProgress />
          <Typography variant="body2" color="text.secondary">
            Loading image...
          </Typography>
        </Box>
      )}

      {error && (
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            right: 16,
          }}
        >
          <Alert severity="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        </Box>
      )}

      {!imagePath && !loading && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            color: 'text.secondary',
          }}
        >
          <Typography variant="h6" gutterBottom>
            No image selected
          </Typography>
          <Typography variant="body2">
            Select an image from the browser to display
          </Typography>
        </Box>
      )}
    </Box>
  );
}

