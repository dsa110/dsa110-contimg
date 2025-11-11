/**
 * WCSDisplay Component
 * Real-time WCS coordinate display overlay for JS9 viewer
 * Shows RA, Dec, pixel coordinates, and flux value at cursor position
 */
import { useState, useEffect, useRef } from 'react';
import { Paper, Typography, Box } from '@mui/material';
import { logger } from '../../utils/logger';

declare global {
  interface Window {
    JS9: any;
  }
}

interface WCSDisplayProps {
  displayId?: string;
}

interface WCSData {
  ra: number | null;
  dec: number | null;
  x: number | null;
  y: number | null;
  flux: number | null;
}

export default function WCSDisplay({ displayId = 'js9Display' }: WCSDisplayProps) {
  const [wcsData, setWcsData] = useState<WCSData>({
    ra: null,
    dec: null,
    x: null,
    y: null,
    flux: null,
  });
  const [visible, setVisible] = useState(false);
  const mouseMoveHandlerRef = useRef<((evt: MouseEvent) => void) | null>(null);
  const displayDivRef = useRef<HTMLElement | null>(null);

  // Format RA/Dec for display
  const formatRA = (ra: number | null): string => {
    if (ra === null || isNaN(ra)) return '--:--:--';
    // RA is typically in degrees, convert to hours:minutes:seconds
    // 1 hour = 15 degrees
    const hours = ra / 15.0;
    const h = Math.floor(hours);
    const minutes = (hours - h) * 60;
    const m = Math.floor(minutes);
    const s = (minutes - m) * 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toFixed(2).padStart(5, '0')}`;
  };

  const formatDec = (dec: number | null): string => {
    if (dec === null || isNaN(dec)) return '--:--:--';
    // Format as degrees:arcminutes:arcseconds
    const sign = dec >= 0 ? '+' : '-';
    const absDec = Math.abs(dec);
    const d = Math.floor(absDec);
    const m = Math.floor((absDec - d) * 60);
    const s = ((absDec - d) * 60 - m) * 60;
    return `${sign}${d.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toFixed(2).padStart(5, '0')}`;
  };

  const formatFlux = (flux: number | null): string => {
    if (flux === null || isNaN(flux)) return '--';
    if (Math.abs(flux) < 0.01) return flux.toExponential(3);
    return flux.toFixed(3);
  };

  // Register mouse move handler
  useEffect(() => {
    if (!window.JS9) {
      setVisible(false);
      return;
    }

    const display = window.JS9.displays?.find((d: any) => {
      const divId = d.id || d.display || d.divID;
      return divId === displayId;
    });

    if (!display?.im) {
      setVisible(false);
      return;
    }

    const displayDiv = document.getElementById(displayId);
    if (!displayDiv) {
      setVisible(false);
      return;
    }

    displayDivRef.current = displayDiv;
    setVisible(true);

    const handleMouseMove = (evt: MouseEvent) => {
      try {
        const target = evt.target as HTMLElement;
        if (!displayDivRef.current || !displayDivRef.current.contains(target)) {
          return;
        }

        const rect = displayDivRef.current.getBoundingClientRect();
        const x = evt.clientX - rect.left;
        const y = evt.clientY - rect.top;

        // Get image ID from display
        const imageId = display.im.id;

        // Get WCS coordinates using JS9 API
        let ra: number | null = null;
        let dec: number | null = null;

        // Try multiple methods to get WCS coordinates
        // Method 1: GetWCS (preferred)
        if (typeof window.JS9.GetWCS === 'function') {
          try {
            const wcs = window.JS9.GetWCS(imageId, x, y);
            if (wcs && typeof wcs.ra === 'number' && typeof wcs.dec === 'number') {
              ra = wcs.ra;
              dec = wcs.dec;
            }
          } catch (e) {
            logger.debug('GetWCS failed, trying fallback:', e);
          }
        }

        // Fallback: Try PixToWCS if GetWCS doesn't work
        if ((ra === null || dec === null) && typeof window.JS9.PixToWCS === 'function') {
          try {
            const wcs = window.JS9.PixToWCS(imageId, x, y);
            if (wcs && typeof wcs.ra === 'number' && typeof wcs.dec === 'number') {
              ra = wcs.ra;
              dec = wcs.dec;
            }
          } catch (e) {
            logger.debug('PixToWCS failed:', e);
          }
        }

        // Additional fallback: Try GetVal with WCS option
        if ((ra === null || dec === null) && typeof window.JS9.GetVal === 'function') {
          try {
            // Some JS9 versions return WCS in GetVal with options
            const result = window.JS9.GetVal(imageId, x, y, { wcs: true });
            if (result && typeof result.ra === 'number' && typeof result.dec === 'number') {
              ra = result.ra;
              dec = result.dec;
            }
          } catch (e) {
            // Ignore errors
          }
        }

        // Get pixel value (flux)
        let flux: number | null = null;
        if (typeof window.JS9.GetVal === 'function') {
          const pixelValue = window.JS9.GetVal(imageId, x, y);
          if (typeof pixelValue === 'number' && !isNaN(pixelValue)) {
            flux = pixelValue;
          }
        }

        // Update state
        setWcsData({
          ra,
          dec,
          x: Math.round(x),
          y: Math.round(y),
          flux,
        });
      } catch (e) {
        // Silently handle errors during mouse move
        logger.debug('Error updating WCS display:', e);
      }
    };

    // Register mouse move handler
    mouseMoveHandlerRef.current = handleMouseMove;
    displayDiv.addEventListener('mousemove', handleMouseMove);

    // Also handle mouse leave to clear display when cursor leaves
    const handleMouseLeave = () => {
      setWcsData({
        ra: null,
        dec: null,
        x: null,
        y: null,
        flux: null,
      });
    };

    displayDiv.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      if (displayDiv && mouseMoveHandlerRef.current) {
        displayDiv.removeEventListener('mousemove', mouseMoveHandlerRef.current);
        displayDiv.removeEventListener('mouseleave', handleMouseLeave);
      }
      mouseMoveHandlerRef.current = null;
      displayDivRef.current = null;
    };
  }, [displayId]);

  // Also listen for image changes to update visibility
  useEffect(() => {
    if (!window.JS9) {
      setVisible(false);
      return;
    }

    const checkImage = () => {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });
      setVisible(!!display?.im);
    };

    checkImage();

    // Listen for image load events
    let imageLoadHandler: (() => void) | null = null;
    let imageDisplayHandler: (() => void) | null = null;

    if (typeof window.JS9.AddEventListener === 'function') {
      imageLoadHandler = () => {
        setTimeout(checkImage, 100);
      };
      imageDisplayHandler = () => {
        setTimeout(checkImage, 100);
      };

      window.JS9.AddEventListener('imageLoad', imageLoadHandler);
      window.JS9.AddEventListener('imageDisplay', imageDisplayHandler);
    }

    // Fallback polling
    const interval = setInterval(checkImage, 1000);

    return () => {
      clearInterval(interval);
      if (imageLoadHandler && typeof window.JS9?.RemoveEventListener === 'function') {
        window.JS9.RemoveEventListener('imageLoad', imageLoadHandler);
      }
      if (imageDisplayHandler && typeof window.JS9?.RemoveEventListener === 'function') {
        window.JS9.RemoveEventListener('imageDisplay', imageDisplayHandler);
      }
    };
  }, [displayId]);

  if (!visible) {
    return null;
  }

  return (
    <Paper
      elevation={3}
      sx={{
        position: 'absolute',
        top: 8,
        right: 8,
        p: 1,
        minWidth: 180,
        maxWidth: 220,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        backdropFilter: 'blur(6px)',
        zIndex: 1100, // Above loading spinner (1000) but below dialogs (1300+)
        pointerEvents: 'none',
        border: '1px solid rgba(255, 255, 255, 0.15)',
        borderRadius: 1,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
      }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
        <Typography
          variant="caption"
          sx={{
            fontFamily: 'monospace',
            fontSize: '0.7rem',
            color: 'rgba(255, 255, 255, 0.95)',
            lineHeight: 1.3,
            whiteSpace: 'nowrap',
          }}
        >
          <Box component="span" sx={{ color: 'rgba(255, 255, 255, 0.65)', mr: 0.75, fontWeight: 500 }}>
            RA:
          </Box>
          {formatRA(wcsData.ra)}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            fontFamily: 'monospace',
            fontSize: '0.7rem',
            color: 'rgba(255, 255, 255, 0.95)',
            lineHeight: 1.3,
            whiteSpace: 'nowrap',
          }}
        >
          <Box component="span" sx={{ color: 'rgba(255, 255, 255, 0.65)', mr: 0.75, fontWeight: 500 }}>
            Dec:
          </Box>
          {formatDec(wcsData.dec)}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            fontFamily: 'monospace',
            fontSize: '0.7rem',
            color: 'rgba(255, 255, 255, 0.95)',
            lineHeight: 1.3,
            whiteSpace: 'nowrap',
          }}
        >
          <Box component="span" sx={{ color: 'rgba(255, 255, 255, 0.65)', mr: 0.75, fontWeight: 500 }}>
            Pixel:
          </Box>
          {wcsData.x !== null && wcsData.y !== null
            ? `(${wcsData.x}, ${wcsData.y})`
            : '(--, --)'}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            fontFamily: 'monospace',
            fontSize: '0.7rem',
            color: 'rgba(255, 255, 255, 0.95)',
            lineHeight: 1.3,
            whiteSpace: 'nowrap',
          }}
        >
          <Box component="span" sx={{ color: 'rgba(255, 255, 255, 0.65)', mr: 0.75, fontWeight: 500 }}>
            Flux:
          </Box>
          {formatFlux(wcsData.flux)}
        </Typography>
      </Box>
    </Paper>
  );
}

