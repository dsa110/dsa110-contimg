/**
 * ImageMetadata Component
 * Displays image metadata (beam, noise, WCS, observation info, cursor position)
 */
import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Divider,
} from '@mui/material';
import { logger } from '../../utils/logger';

declare global {
  interface Window {
    JS9: any;
  }
}

interface ImageMetadataProps {
  displayId?: string;
  imageInfo?: {
    path?: string;
    type?: string;
    noise_jy?: number;
    beam_major_arcsec?: number;
    beam_minor_arcsec?: number;
    beam_pa_deg?: number;
  };
}

interface CursorInfo {
  pixelX: number | null;
  pixelY: number | null;
  ra: number | null;
  dec: number | null;
  flux: number | null;
}

export default function ImageMetadata({ 
  displayId = 'js9Display',
  imageInfo 
}: ImageMetadataProps) {
  const [cursorInfo, setCursorInfo] = useState<CursorInfo>({
    pixelX: null,
    pixelY: null,
    ra: null,
    dec: null,
    flux: null,
  });

  // Track cursor position
  useEffect(() => {
    if (!window.JS9) return;

    const updateCursorInfo = () => {
      try {
        const display = window.JS9.displays?.find((d: any) => {
          const divId = d.id || d.display || d.divID;
          return divId === displayId;
        });
        
        if (!display?.im) {
          setCursorInfo({
            pixelX: null,
            pixelY: null,
            ra: null,
            dec: null,
            flux: null,
          });
          return;
        }

        // Get cursor position from JS9
        const im = display.im;
        const x = im.x || null;
        const y = im.y || null;
        
        if (x !== null && y !== null) {
          // Get WCS coordinates
          const wcs = window.JS9.GetWCS(im.id, x, y);
          const ra = wcs?.ra || null;
          const dec = wcs?.dec || null;
          
          // Get flux value at cursor
          const flux = window.JS9.GetVal(im.id, x, y);
          
          setCursorInfo({
            pixelX: Math.round(x),
            pixelY: Math.round(y),
            ra: ra ? ra / 15 : null, // Convert to degrees
            dec: dec || null,
            flux: flux !== null && !isNaN(flux) ? flux : null,
          });
        }
      } catch (e) {
        logger.debug('Error getting cursor info:', e);
      }
    };

    // Update cursor info periodically (JS9 doesn't have a cursor event)
    const interval = setInterval(updateCursorInfo, 100);
    return () => clearInterval(interval);
  }, [displayId]);

  const formatRA = (raDeg: number | null): string => {
    if (raDeg === null) return '--';
    const hours = raDeg / 15;
    const h = Math.floor(hours);
    const m = Math.floor((hours - h) * 60);
    const s = ((hours - h) * 60 - m) * 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toFixed(1).padStart(4, '0')}`;
  };

  const formatDec = (decDeg: number | null): string => {
    if (decDeg === null) return '--';
    const sign = decDeg >= 0 ? '+' : '-';
    const absDec = Math.abs(decDeg);
    const d = Math.floor(absDec);
    const m = Math.floor((absDec - d) * 60);
    const s = ((absDec - d) * 60 - m) * 60;
    return `${sign}${d.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toFixed(1).padStart(4, '0')}`;
  };

  const formatBeam = (): string => {
    if (!imageInfo?.beam_major_arcsec || !imageInfo?.beam_minor_arcsec) {
      return '--';
    }
    const major = imageInfo.beam_major_arcsec.toFixed(1);
    const minor = imageInfo.beam_minor_arcsec.toFixed(1);
    const pa = imageInfo.beam_pa_deg ? `${imageInfo.beam_pa_deg.toFixed(0)}°` : '';
    return `${major}" × ${minor}"${pa ? ` PA ${pa}` : ''}`;
  };

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        Image Information
      </Typography>
      
      <Divider sx={{ my: 1 }} />

      {/* Image Path */}
      {imageInfo?.path && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Image:</strong> {imageInfo.path.split('/').pop()}
          </Typography>
        </Box>
      )}

      {/* Image Type */}
      {imageInfo?.type && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Type:</strong> {imageInfo.type}
          </Typography>
        </Box>
      )}

      {/* Beam Parameters */}
      <Box sx={{ mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Beam:</strong> {formatBeam()}
        </Typography>
      </Box>

      {/* Noise Level */}
      {imageInfo?.noise_jy !== undefined && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Noise:</strong> {(imageInfo.noise_jy * 1000).toFixed(2)} mJy/beam
          </Typography>
        </Box>
      )}

      <Divider sx={{ my: 1 }} />

      {/* Cursor Position */}
      <Typography variant="subtitle2" gutterBottom>
        Cursor Position
      </Typography>
      <Box sx={{ mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Pixel:</strong> ({cursorInfo.pixelX ?? '--'}, {cursorInfo.pixelY ?? '--'})
        </Typography>
      </Box>
      <Box sx={{ mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>RA:</strong> {formatRA(cursorInfo.ra)}
        </Typography>
      </Box>
      <Box sx={{ mb: 1 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Dec:</strong> {formatDec(cursorInfo.dec)}
        </Typography>
      </Box>
      {cursorInfo.flux !== null && (
        <Box>
          <Typography variant="body2" color="text.secondary">
            <strong>Flux:</strong> {(cursorInfo.flux * 1000).toFixed(2)} mJy/beam
          </Typography>
        </Box>
      )}
    </Paper>
  );
}

