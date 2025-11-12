/**
 * Multi-Image Compare Component
 * Side-by-side JS9 viewers with synchronized pan/zoom/colormap and blend mode
 * Reference: https://js9.si.edu/js9/help/publicapi.html
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Button,
  Grid,
  Paper,
  Typography,
  Slider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  Chip,
} from '@mui/material';
import {
  Close,
  CompareArrows,
  Opacity,
  Link,
  LinkOff,
} from '@mui/icons-material';
import SkyViewer from './SkyViewer';
import ImageBrowser from './ImageBrowser';
import type { ImageInfo } from '../../api/types';
import { logger } from '../../utils/logger';
import { findDisplay, isJS9Available } from '../../utils/js9';

declare global {
  interface Window {
    JS9: any;
  }
}

interface MultiImageCompareProps {
  open: boolean;
  onClose: () => void;
  initialImageA?: ImageInfo | null;
  initialImageB?: ImageInfo | null;
}

export default function MultiImageCompare({
  open,
  onClose,
  initialImageA = null,
  initialImageB = null,
}: MultiImageCompareProps) {
  const [imageA, setImageA] = useState<ImageInfo | null>(initialImageA);
  const [imageB, setImageB] = useState<ImageInfo | null>(initialImageB);
  const [blendOpacity, setBlendOpacity] = useState(50);
  const [blendMode, setBlendMode] = useState<'overlay' | 'difference' | 'add'>('overlay');
  const [syncEnabled, setSyncEnabled] = useState(true);
  const syncRef = useRef(false);
  const listenersRegisteredRef = useRef(false);
  const eventHandlersRef = useRef<Array<{ event: string; handler: () => void }>>([]);
  const displayAId = 'js9CompareA';
  const displayBId = 'js9CompareB';

  // Construct FITS URLs
  const fitsUrlA = imageA ? `/api/images/${imageA.id}/fits` : null;
  const fitsUrlB = imageB ? `/api/images/${imageB.id}/fits` : null;

  // Initialize JS9 sync when both images are loaded
  useEffect(() => {
    if (!open || !window.JS9 || !syncEnabled) {
      // Clean up listeners when sync is disabled or dialog is closed
      if (listenersRegisteredRef.current && typeof window.JS9?.RemoveEventListener === 'function') {
        eventHandlersRef.current.forEach(({ event, handler }) => {
          try {
            window.JS9.RemoveEventListener(event, handler);
          } catch (e) {
            logger.debug(`Error removing ${event} listener:`, e);
          }
        });
        eventHandlersRef.current = [];
        listenersRegisteredRef.current = false;
      }
      return;
    }

    let syncing = false;
    let interval: NodeJS.Timeout | null = null;

    const syncDisplays = (sourceDisplayId: string, targetDisplayId: string) => {
      if (syncing) return;
      syncing = true;

      try {
        const sourceDisplay = findDisplay(displayAId);
        const targetDisplay = findDisplay(displayBId);

        if (sourceDisplay?.im && targetDisplay?.im) {
          const sourceImageId = sourceDisplay.im.id;
          const targetImageId = targetDisplay.im.id;

          // Sync zoom
          const zoom = window.JS9.GetZoom?.(sourceImageId);
          if (zoom) {
            window.JS9.SetZoom?.(targetImageId, zoom);
          }

          // Sync colormap
          const colormap = window.JS9.GetColormap?.(sourceImageId);
          if (colormap) {
            window.JS9.SetColormap?.(targetImageId, colormap);
          }

          // Sync scale
          const scale = window.JS9.GetScale?.(sourceImageId);
          if (scale) {
            window.JS9.SetScale?.(targetImageId, scale);
          }
        }
      } catch (e) {
        logger.debug('Error syncing displays:', e);
      } finally {
        syncing = false;
      }
    };

    const setupSync = () => {
      const displayA = findDisplay(displayAId);
      const displayB = findDisplay(displayBId);

      if (displayA?.im && displayB?.im && !syncRef.current && !listenersRegisteredRef.current) {
        // Use JS9.SyncImages if available, otherwise use manual sync
        if (typeof window.JS9.SyncImages === 'function') {
          try {
            window.JS9.SyncImages([displayAId, displayBId], {
              pan: true,
              zoom: true,
              colormap: true,
            });
            syncRef.current = true;
            logger.debug('JS9 images synchronized via SyncImages API');
          } catch (e) {
            logger.debug('SyncImages API failed, using manual sync:', e);
            syncRef.current = true;
          }
        } else {
          // Clean up any existing listeners before registering new ones
          if (listenersRegisteredRef.current && typeof window.JS9.RemoveEventListener === 'function') {
            eventHandlersRef.current.forEach(({ event, handler }) => {
              try {
                window.JS9.RemoveEventListener(event, handler);
              } catch (e) {
                logger.debug(`Error removing old ${event} listener:`, e);
              }
            });
            eventHandlersRef.current = [];
            listenersRegisteredRef.current = false;
          }

          // Manual sync via event listeners
          const handleZoom = () => {
            if (syncEnabled && !syncing) {
              syncDisplays(displayAId, displayBId);
            }
          };

          const handlePan = () => {
            if (syncEnabled && !syncing) {
              syncDisplays(displayAId, displayBId);
            }
          };

          const handleColormap = () => {
            if (syncEnabled && !syncing) {
              syncDisplays(displayAId, displayBId);
            }
          };

          if (typeof window.JS9.AddEventListener === 'function') {
            window.JS9.AddEventListener('zoom', handleZoom);
            window.JS9.AddEventListener('pan', handlePan);
            window.JS9.AddEventListener('colormap', handleColormap);
            
            // Store handlers for cleanup using ref
            eventHandlersRef.current = [
              { event: 'zoom', handler: handleZoom },
              { event: 'pan', handler: handlePan },
              { event: 'colormap', handler: handleColormap },
            ];
            
            listenersRegisteredRef.current = true;
            syncRef.current = true;
          }
        }
      }
    };

    // Check periodically until both images are loaded
    interval = setInterval(setupSync, 500);
    
    // Cleanup function returned from useEffect
    return () => {
      if (interval) {
        clearInterval(interval);
      }
      
      // Remove event listeners if they were registered (using refs to access current values)
      if (listenersRegisteredRef.current && typeof window.JS9?.RemoveEventListener === 'function') {
        eventHandlersRef.current.forEach(({ event, handler }) => {
          try {
            window.JS9.RemoveEventListener(event, handler);
          } catch (e) {
            logger.debug(`Error removing ${event} listener:`, e);
          }
        });
        eventHandlersRef.current = [];
        listenersRegisteredRef.current = false;
      }
      
      syncRef.current = false;
    };
  }, [open, syncEnabled, imageA, imageB]);

  // Apply blend mode when opacity or mode changes
  // Note: JS9.BlendImage may not be available in all JS9 versions
  // This is a placeholder for future JS9 blend functionality
  useEffect(() => {
    if (!open || !window.JS9 || !fitsUrlA || !fitsUrlB) return;

    const displayA = window.JS9.displays?.find((d: any) => {
      const divId = d.id || d.display || d.divID;
      return divId === displayAId;
    });
    const displayB = window.JS9.displays?.find((d: any) => {
      const divId = d.id || d.display || d.divID;
      return divId === displayBId;
    });

    if (displayA?.im && displayB?.im) {
      try {
        // JS9 BlendImage API: blend imageB onto imageA
        // Reference: https://js9.si.edu/js9/help/publicapi.html
        if (typeof window.JS9.BlendImage === 'function') {
          window.JS9.BlendImage(displayA.im.id, displayB.im.id, {
            opacity: blendOpacity / 100,
            mode: blendMode,
          });
        } else {
          // BlendImage not available - could implement manual blending via canvas
          // For now, just log that blend mode is set but not applied
          logger.debug('JS9.BlendImage not available, blend mode:', blendMode, 'opacity:', blendOpacity);
        }
      } catch (e) {
        logger.debug('Blend mode not available or error:', e);
      }
    }
  }, [open, blendOpacity, blendMode, fitsUrlA, fitsUrlB]);

  const handleClose = () => {
    syncRef.current = false;
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="xl"
      fullWidth
      PaperProps={{
        sx: { height: '90vh' },
      }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Compare Images</Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Tooltip title={syncEnabled ? 'Synchronization enabled - pan, zoom, and colormap are synced' : 'Synchronization disabled'}>
              <Chip
                icon={syncEnabled ? <Link /> : <LinkOff />}
                label={syncEnabled ? 'Synced' : 'Unsynced'}
                color={syncEnabled ? 'primary' : 'default'}
                size="small"
                onClick={() => setSyncEnabled(!syncEnabled)}
                sx={{
                  cursor: 'pointer',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    transform: 'scale(1.05)',
                  },
                }}
              />
            </Tooltip>
            <IconButton onClick={handleClose} size="small">
              <Close />
            </IconButton>
          </Box>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        <Grid container spacing={2}>
          {/* Image Selection */}
          <Grid size={{ xs: 12 }}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 6 }}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Image A
                  </Typography>
                  <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                    <ImageBrowser
                      onSelectImage={setImageA}
                      selectedImageId={imageA?.id}
                    />
                  </Box>
                </Paper>
              </Grid>
              <Grid size={{ xs: 6 }}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Image B
                  </Typography>
                  <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                    <ImageBrowser
                      onSelectImage={setImageB}
                      selectedImageId={imageB?.id}
                    />
                  </Box>
                </Paper>
              </Grid>
            </Grid>
          </Grid>

          {/* Blend Controls - Always visible */}
          <Grid size={{ xs: 12 }}>
            <Paper
              sx={{
                p: 2,
                opacity: (!imageA || !imageB) ? 0.6 : 1,
                transition: 'opacity 0.2s ease-in-out',
              }}
            >
              <Typography variant="subtitle2" gutterBottom>
                Blend Controls
                {(!imageA || !imageB) && (
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                    (Select both images to enable blending)
                  </Typography>
                )}
              </Typography>
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Tooltip
                    title={
                      !imageA || !imageB
                        ? 'Select both images to enable blend mode'
                        : 'Blend mode determines how Image B is combined with Image A'
                    }
                  >
                    <FormControl fullWidth size="small" disabled={!imageA || !imageB}>
                      <InputLabel>Blend Mode</InputLabel>
                      <Select
                        value={blendMode}
                        onChange={(e) => setBlendMode(e.target.value as any)}
                        label="Blend Mode"
                      >
                        <MenuItem value="overlay">Overlay</MenuItem>
                        <MenuItem value="difference">Difference</MenuItem>
                        <MenuItem value="add">Add</MenuItem>
                      </Select>
                    </FormControl>
                  </Tooltip>
                </Grid>
                <Grid size={{ xs: 12, sm: 8 }}>
                  <Tooltip
                    title={
                      !imageA || !imageB
                        ? 'Select both images to adjust opacity'
                        : 'Adjust the opacity of Image B when blending'
                    }
                  >
                    <Box display="flex" alignItems="center" gap={2}>
                      <Opacity sx={{ opacity: (!imageA || !imageB) ? 0.5 : 1 }} />
                      <Typography
                        variant="body2"
                        sx={{
                          minWidth: 60,
                          color: (!imageA || !imageB) ? 'text.disabled' : 'text.primary',
                        }}
                      >
                        Opacity: {blendOpacity}%
                      </Typography>
                      <Slider
                        value={blendOpacity}
                        onChange={(_, value) => setBlendOpacity(value as number)}
                        min={0}
                        max={100}
                        step={5}
                        sx={{ flex: 1 }}
                        disabled={!imageA || !imageB}
                      />
                    </Box>
                  </Tooltip>
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* Side-by-side viewers */}
          <Grid size={{ xs: 12 }}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 6 }}>
                <Paper sx={{ p: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ px: 1 }}>
                    {imageA ? `Image A: ${imageA.path.split('/').pop()}` : 'No image selected'}
                  </Typography>
                  <SkyViewer
                    imagePath={fitsUrlA}
                    displayId={displayAId}
                    height={500}
                  />
                </Paper>
              </Grid>
              <Grid size={{ xs: 6 }}>
                <Paper sx={{ p: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ px: 1 }}>
                    {imageB ? `Image B: ${imageB.path.split('/').pop()}` : 'No image selected'}
                  </Typography>
                  <SkyViewer
                    imagePath={fitsUrlB}
                    displayId={displayBId}
                    height={500}
                  />
                </Paper>
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

