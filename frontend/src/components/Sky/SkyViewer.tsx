/**
 * SkyViewer Component - JS9 FITS Image Viewer Integration
 * 
 * Refactored to use custom hooks for better separation of concerns:
 * - useJS9Initialization: Handles JS9 display initialization
 * - useJS9ImageLoader: Handles image loading and state management
 * - useJS9Resize: Handles display resizing
 * - useJS9ContentPreservation: Preserves JS9 content across React renders
 */
import { useEffect, useRef } from 'react';
import { Box, CircularProgress, Alert, Typography } from '@mui/material';
import { isJS9Available, findDisplay } from '../../utils/js9';
import { useJS9Safe } from '../../contexts/JS9Context';
import { useJS9Initialization } from './hooks/useJS9Initialization';
import { useJS9ImageLoader } from './hooks/useJS9ImageLoader';
import { useJS9Resize } from './hooks/useJS9Resize';
import { useJS9ContentPreservation } from './hooks/useJS9ContentPreservation';
import styles from './Sky.module.css';
import WCSDisplay from './WCSDisplay';

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
  // Use JS9 context if available (backward compatible)
  const js9Context = useJS9Safe();

  const containerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Use context's JS9 readiness if available, otherwise check directly
  const isJS9Ready = js9Context?.isJS9Ready ?? isJS9Available();
  
  // Use context's getDisplay if available, otherwise use utility
  const getDisplaySafe = (id: string) => {
    return js9Context?.getDisplay(id) ?? findDisplay(id);
  };

  // Initialize JS9 display
  const { initialized, error: initError } = useJS9Initialization({
    displayId,
    containerRef,
    height,
    isJS9Ready,
    getDisplaySafe,
    js9Context,
  });

  // Load images
  const { loading, error: loadError, imageLoadedRef } = useJS9ImageLoader({
    imagePath,
    displayId,
    initialized,
    isJS9Ready,
    timeoutRef,
    getDisplaySafe,
  });

  // Handle resizing
  useJS9Resize({
    displayId,
    containerRef,
    initialized,
    isJS9Ready,
    getDisplaySafe,
  });

  // Preserve JS9 content across React renders
  useJS9ContentPreservation({
    displayId,
    containerRef,
    initialized,
    isJS9Ready,
    imageLoadedRef,
    loading,
    getDisplaySafe,
  });

  // Combine errors from initialization and loading
  const error = initError || loadError;

  // Prevent JS9 from modifying page title
  useEffect(() => {
    const originalTitle = document.title;
    const titleObserver = new MutationObserver(() => {
      if (document.title !== originalTitle && document.title.includes(':')) {
        document.title = originalTitle;
      }
    });
    titleObserver.observe(document.querySelector('title') || document.head, {
      childList: true,
      subtree: true,
      characterData: true
    });
    return () => titleObserver.disconnect();
  }, []);

  return (
    <Box sx={{ position: 'relative', width: '100%', height: `${height}px` }}>
      <Box
        key={displayId}
        id={displayId}
        ref={containerRef}
        component="div"
        className={styles.JS9DisplayContainer}
        sx={{
          width: '100%',
          maxWidth: '100%',
          minWidth: '400px',
          height: `${height}px`,
          minHeight: `${height}px`,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          bgcolor: '#0a0a0a',
          position: 'relative',
          display: 'block',
          boxSizing: 'border-box',
          overflow: 'hidden',
        }}
        // Prevent React from clearing JS9 content on re-render
        onMouseEnter={() => {
          // Force JS9 to redraw if content was cleared
          if (imageLoadedRef.current && isJS9Ready) {
            const display = getDisplaySafe(displayId);
            if (display && display.im && isJS9Ready) {
              // Image is loaded, ensure it's displayed
              try {
                window.JS9.Load(display.im.id, { display: displayId });
              } catch (e) {
                // Ignore errors
              }
            }
          }
        }}
      />
      
      {/* WCS Coordinate Display Overlay */}
      <WCSDisplay displayId={displayId} />

      {loading && !imageLoadedRef.current && (
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
            zIndex: 1000,
            pointerEvents: 'none',
            '& + *': {
              // Hide any JS9 loading indicators that might appear
              '& .JS9Loading, & .js9-loading, & [class*="js9"][class*="load"]': {
                display: 'none !important',
              },
            },
          }}
        >
          <CircularProgress />
          <Typography variant="body2" color="text.secondary">
            Loading image...
          </Typography>
        </Box>
      )}
      
      {/* Hidden style tag to globally hide JS9 loading indicators and ensure canvas fills container */}
      <style>{`
        .JS9Loading,
        .js9-loading,
        [class*="js9"][class*="load"],
        [id*="js9"][id*="load"],
        .JS9 div[class*="load"],
        .JS9 div[id*="load"],
        .JS9 div[class*="spinner"],
        .JS9 div[class*="loader"],
        .JS9 div[style*="spinner"],
        .JS9 div[style*="loader"],
        #${displayId} div[class*="load"],
        #${displayId} div[class*="spinner"],
        #${displayId} div[class*="loader"],
        #${displayId} div[style*="spinner"],
        #${displayId} div[style*="loader"] {
          display: none !important;
          visibility: hidden !important;
          opacity: 0 !important;
          pointer-events: none !important;
        }
        #${displayId} canvas {
          width: 100% !important;
          max-width: 100% !important;
          height: auto !important;
        }
      `}</style>

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

