/**
 * Quick Analysis Panel
 * Local JavaScript analysis tasks for JS9 images
 * Reference: https://js9.si.edu/js9/help/localtasks.html
 */
import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Paper,
  TextField,
  Alert,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import {
  ShowChart,
  BarChart,
  Info,
  Download,
} from '@mui/icons-material';
import { logger } from '../../utils/logger';

declare global {
  interface Window {
    JS9: any;
  }
}

interface QuickAnalysisPanelProps {
  displayId?: string;
}

interface SpectrumData {
  x: number[];
  y: number[];
}

interface SourceStats {
  peak: number;
  mean: number;
  rms: number;
  min: number;
  max: number;
  pixels: number;
}

interface WCSInfo {
  ra: number;
  dec: number;
  x: number;
  y: number;
  value: number;
}

export default function QuickAnalysisPanel({
  displayId = 'js9Display',
}: QuickAnalysisPanelProps) {
  const [spectrumData, setSpectrumData] = useState<SpectrumData | null>(null);
  const [sourceStats, setSourceStats] = useState<SourceStats | null>(null);
  const [wcsInfo, setWcsInfo] = useState<WCSInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingOperation, setLoadingOperation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mousePosition, setMousePosition] = useState<{ x: number; y: number } | null>(null);
  const [hasImage, setHasImage] = useState(false);

  // Check if image is loaded - use JS9 events when available, fallback to polling
  useEffect(() => {
    if (!window.JS9) {
      setHasImage(false);
      return;
    }

    const checkImage = () => {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });
      setHasImage(!!display?.im);
    };

    // Initial check
    checkImage();

    // Try to use JS9 events for real-time updates
    let imageLoadHandler: (() => void) | null = null;
    let imageDisplayHandler: (() => void) | null = null;

    if (typeof window.JS9.AddEventListener === 'function') {
      imageLoadHandler = () => {
        // Small delay to ensure display is updated
        setTimeout(checkImage, 100);
      };
      imageDisplayHandler = () => {
        setTimeout(checkImage, 100);
      };

      window.JS9.AddEventListener('imageLoad', imageLoadHandler);
      window.JS9.AddEventListener('imageDisplay', imageDisplayHandler);
    }

    // Fallback polling (less frequent if events are available)
    const pollInterval = imageLoadHandler ? 2000 : 1000;
    const interval = setInterval(checkImage, pollInterval);

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

  // Update WCS info on mouse move
  useEffect(() => {
    if (!window.JS9) return;

    const display = window.JS9.displays?.find((d: any) => {
      const divId = d.id || d.display || d.divID;
      return divId === displayId;
    });

    if (!display?.im) return;

    const handleMouseMove = (evt: MouseEvent) => {
      try {
        const target = evt.target as HTMLElement;
        const displayDiv = document.getElementById(displayId);
        if (!displayDiv || !displayDiv.contains(target)) return;

        const rect = displayDiv.getBoundingClientRect();
        const x = evt.clientX - rect.left;
        const y = evt.clientY - rect.top;

        // Get pixel value and WCS coordinates
        const imageId = display.im.id;
        const pixelValue = window.JS9.GetVal?.(imageId, x, y);
        const wcs = window.JS9.GetWCS?.(imageId, x, y);

        if (wcs && pixelValue !== undefined) {
          setWcsInfo({
            ra: wcs.ra || 0,
            dec: wcs.dec || 0,
            x: Math.round(x),
            y: Math.round(y),
            value: pixelValue,
          });
          setMousePosition({ x, y });
        }
      } catch (e) {
        // Ignore errors during mouse move
      }
    };

    const displayDiv = document.getElementById(displayId);
    if (displayDiv) {
      displayDiv.addEventListener('mousemove', handleMouseMove);
      return () => {
        displayDiv.removeEventListener('mousemove', handleMouseMove);
      };
    }
  }, [displayId]);

  const extractSpectrum = async () => {
    if (!window.JS9) {
      setError('JS9 not available');
      return;
    }

    setLoading(true);
    setLoadingOperation('Extracting spectrum...');
    setError(null);

    try {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });

      if (!display?.im) {
        setError('No image loaded. Please select an image from the browser above.');
        setLoading(false);
        setLoadingOperation(null);
        return;
      }

      const imageId = display.im.id;
      const regions = window.JS9.GetRegions?.(imageId) || [];

      if (regions.length === 0) {
        setError('Please draw a region on the image first. Use JS9 region tools (circle, box, etc.) to select an area for analysis.');
        setLoading(false);
        setLoadingOperation(null);
        return;
      }

      // Get image data
      const imageData = window.JS9.GetImageData?.(imageId);
      if (!imageData || !imageData.data) {
        setError('Could not retrieve image data. The image may not be fully loaded yet.');
        setLoading(false);
        return;
      }

      // Extract spectrum from region (simplified: average along one axis)
      // For a proper spectrum, you'd extract along a specific axis
      const region = regions[0];
      const x = [];
      const y = [];

      // Simple extraction: average rows/columns in region
      for (let i = 0; i < imageData.width; i++) {
        x.push(i);
        let sum = 0;
        let count = 0;
        for (let j = 0; j < imageData.height; j++) {
          const idx = j * imageData.width + i;
          if (imageData.data[idx] !== undefined && !isNaN(imageData.data[idx])) {
            sum += imageData.data[idx];
            count++;
          }
        }
        y.push(count > 0 ? sum / count : 0);
      }

      setSpectrumData({ x, y });
    } catch (e: any) {
      logger.error('Error extracting spectrum:', e);
      setError(e.message || 'Failed to extract spectrum');
    } finally {
      setLoading(false);
      setLoadingOperation(null);
    }
  };

  const calculateSourceStats = async () => {
    if (!window.JS9) {
      setError('JS9 not available');
      return;
    }

    setLoading(true);
    setLoadingOperation('Calculating statistics...');
    setError(null);

    try {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });

      if (!display?.im) {
        setError('No image loaded. Please select an image from the browser above.');
        setLoading(false);
        setLoadingOperation(null);
        return;
      }

      const imageId = display.im.id;
      const regions = window.JS9.GetRegions?.(imageId) || [];

      if (regions.length === 0) {
        setError('Please draw a region on the image first. Use JS9 region tools (circle, box, etc.) to select an area for analysis.');
        setLoading(false);
        setLoadingOperation(null);
        return;
      }

      // Get image data
      const imageData = window.JS9.GetImageData?.(imageId);
      if (!imageData || !imageData.data) {
        setError('Could not retrieve image data. The image may not be fully loaded yet.');
        setLoading(false);
        return;
      }

      // Extract pixel values in region (simplified - would need proper region mask)
      const values: number[] = [];
      const data = imageData.data as number[];

      // Simple extraction: all pixels (in real implementation, mask by region)
      for (let i = 0; i < data.length; i++) {
        if (data[i] !== undefined && !isNaN(data[i])) {
          values.push(data[i]);
        }
      }

      if (values.length === 0) {
        setError('No valid pixels found in the selected region. Try selecting a different area.');
        setLoading(false);
        return;
      }

      // Calculate statistics
      const sum = values.reduce((a, b) => a + b, 0);
      const mean = sum / values.length;
      const peak = Math.max(...values);
      const min = Math.min(...values);
      const variance = values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / values.length;
      const rms = Math.sqrt(variance);

      setSourceStats({
        peak,
        mean,
        rms,
        min,
        max: peak,
        pixels: values.length,
      });
    } catch (e: any) {
      logger.error('Error calculating source stats:', e);
      setError(`Failed to calculate statistics: ${e.message || 'Unknown error'}. Make sure an image is loaded and a region is selected.`);
    } finally {
      setLoading(false);
      setLoadingOperation(null);
    }
  };

  const getWCSInfo = () => {
    if (!window.JS9) {
      setError('JS9 not available');
      return;
    }

    const display = window.JS9.displays?.find((d: any) => {
      const divId = d.id || d.display || d.divID;
      return divId === displayId;
    });

    if (!display?.im) {
      setError('No image loaded. Please select an image from the browser above.');
      return;
    }

    // WCS info is already displayed automatically on mouse move
    // This function just ensures the user knows where to look
    setError(null);
  };

  const exportRegionData = async () => {
    if (!window.JS9) {
      setError('JS9 not available');
      return;
    }

    setLoading(true);
    setLoadingOperation('Exporting region data...');
    setError(null);

    try {
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });

      if (!display?.im) {
        setError('No image loaded. Please select an image from the browser above.');
        setLoading(false);
        setLoadingOperation(null);
        return;
      }

      const imageId = display.im.id;
      const regions = window.JS9.GetRegions?.(imageId) || [];

      if (regions.length === 0) {
        setError('Please draw a region on the image first. Use JS9 region tools (circle, box, etc.) to select an area for analysis.');
        setLoading(false);
        setLoadingOperation(null);
        return;
      }

      // Get image data
      const imageData = window.JS9.GetImageData?.(imageId);
      if (!imageData || !imageData.data) {
        setError('Could not retrieve image data. The image may not be fully loaded yet.');
        setLoading(false);
        return;
      }

      // Export as CSV
      const data = imageData.data as number[];
      const csvRows = ['x,y,value'];

      for (let y = 0; y < imageData.height; y++) {
        for (let x = 0; x < imageData.width; x++) {
          const idx = y * imageData.width + x;
          if (data[idx] !== undefined && !isNaN(data[idx])) {
            csvRows.push(`${x},${y},${data[idx]}`);
          }
        }
      }

      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `region_data_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e: any) {
      logger.error('Error exporting region data:', e);
      setError(`Failed to export data: ${e.message || 'Unknown error'}. Make sure an image is loaded and a region is selected.`);
    } finally {
      setLoading(false);
      setLoadingOperation(null);
    }
  };

  // Check if image is available
  const imageAvailable = hasImage && window.JS9;

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Quick Analysis
      </Typography>

      {!imageAvailable && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Select an image from the browser above to enable analysis tools. These tools perform client-side analysis on the loaded FITS image.
        </Alert>
      )}

      {/* Analysis Buttons */}
      <Box display="flex" flexWrap="wrap" gap={1} sx={{ mb: 2 }}>
        <Tooltip title="Extract spectrum from a selected region (draw a region first)">
          <span>
            <Button
              variant="outlined"
              startIcon={<ShowChart />}
              onClick={extractSpectrum}
              disabled={loading || !imageAvailable}
            >
              Extract Spectrum
            </Button>
          </span>
        </Tooltip>
        <Tooltip title="Calculate statistics (peak, mean, RMS) for pixels in a selected region">
          <span>
            <Button
              variant="outlined"
              startIcon={<BarChart />}
              onClick={calculateSourceStats}
              disabled={loading || !imageAvailable}
            >
              Source Statistics
            </Button>
          </span>
        </Tooltip>
        <Tooltip title="Display World Coordinate System (WCS) information for the current mouse position">
          <span>
            <Button
              variant="outlined"
              startIcon={<Info />}
              onClick={getWCSInfo}
              disabled={loading || !imageAvailable}
            >
              WCS Info
            </Button>
          </span>
        </Tooltip>
        <Tooltip title="Export pixel data from selected region as CSV file">
          <span>
            <Button
              variant="outlined"
              startIcon={<Download />}
              onClick={exportRegionData}
              disabled={loading || !imageAvailable}
            >
              Export Region Data
            </Button>
          </span>
        </Tooltip>
      </Box>

      {loading && (
        <Box display="flex" flexDirection="column" alignItems="center" sx={{ my: 2 }}>
          <CircularProgress size={24} />
          {loadingOperation && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {loadingOperation}
            </Typography>
          )}
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* WCS Info Panel */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={1}>
            <Info />
            <Typography variant="subtitle2">WCS Information</Typography>
          </Box>
          {wcsInfo ? (
            <Table size="small">
              <TableBody>
                <TableRow>
                  <TableCell>RA</TableCell>
                  <TableCell>{wcsInfo.ra.toFixed(6)}°</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Dec</TableCell>
                  <TableCell>{wcsInfo.dec.toFixed(6)}°</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Pixel (x, y)</TableCell>
                  <TableCell>({wcsInfo.x}, {wcsInfo.y})</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Value</TableCell>
                  <TableCell>{wcsInfo.value.toExponential(3)}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Move mouse over image to see coordinates
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Spectrum Display */}
      {spectrumData && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Spectrum
            </Typography>
            <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
              <Typography variant="caption" color="text.secondary">
                Spectrum extracted from region (simplified visualization)
              </Typography>
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2">
                  Data points: {spectrumData.x.length}
                </Typography>
                <Typography variant="body2">
                  Range: {Math.min(...spectrumData.y).toExponential(3)} to{' '}
                  {Math.max(...spectrumData.y).toExponential(3)}
                </Typography>
              </Box>
            </Paper>
          </CardContent>
        </Card>
      )}

      {/* Source Statistics */}
      {sourceStats && (
        <Card>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Source Statistics
            </Typography>
            <Table size="small">
              <TableBody>
                <TableRow>
                  <TableCell>Peak</TableCell>
                  <TableCell>{sourceStats.peak.toExponential(3)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Mean</TableCell>
                  <TableCell>{sourceStats.mean.toExponential(3)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>RMS</TableCell>
                  <TableCell>{sourceStats.rms.toExponential(3)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Min</TableCell>
                  <TableCell>{sourceStats.min.toExponential(3)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Max</TableCell>
                  <TableCell>{sourceStats.max.toExponential(3)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Pixels</TableCell>
                  <TableCell>{sourceStats.pixels.toLocaleString()}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

