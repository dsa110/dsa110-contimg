/**
 * CatalogOverlay Component - Overlay catalog sources on images
 */
import { useMemo } from 'react';
import { Box, FormControl, InputLabel, Select, MenuItem, Switch, FormControlLabel, Slider, Typography } from '@mui/material';
import { useCatalogOverlay } from '../../api/queries';
import type { CatalogSource } from '../../api/types';

interface CatalogOverlayProps {
  imageId: string | null;
  catalog?: 'nvss' | 'vlass';
  showLabels?: boolean;
  color?: string;
  size?: number;
  opacity?: number;
  onSourceClick?: (source: CatalogSource) => void;
  minFluxJy?: number;
}

export default function CatalogOverlay({
  imageId,
  catalog = 'nvss',
  showLabels = false,
  color = '#00ff00',
  size = 4,
  opacity = 0.7,
  onSourceClick,
  minFluxJy,
}: CatalogOverlayProps) {
  const { data: overlayData, isLoading, error } = useCatalogOverlay(imageId, catalog, minFluxJy);

  const sources = useMemo(() => {
    if (!overlayData?.sources) return [];
    return overlayData.sources;
  }, [overlayData]);

  if (isLoading) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Loading catalog overlay...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="error">
          Error loading catalog overlay: {error instanceof Error ? error.message : 'Unknown error'}
        </Typography>
      </Box>
    );
  }

  if (!overlayData || sources.length === 0) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          No catalog sources found in field
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* This component renders overlay markers on an image canvas */}
      {/* The actual rendering would be done by the parent image viewer component */}
      {/* This component provides the data and controls */}
      <svg
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
      >
        {sources.map((source: CatalogSource, idx: number) => (
          <g key={idx}>
            <circle
              cx={source.x}
              cy={source.y}
              r={size}
              fill={color}
              stroke="white"
              strokeWidth={1}
              opacity={opacity}
              style={{ pointerEvents: 'all', cursor: onSourceClick ? 'pointer' : 'default' }}
              onClick={() => onSourceClick?.(source)}
            />
            {showLabels && (
              <text
                x={source.x + size + 2}
                y={source.y}
                fill="white"
                fontSize="10px"
                style={{ pointerEvents: 'none' }}
              >
                {source.name || `Source ${idx + 1}`}
              </text>
            )}
          </g>
        ))}
      </svg>
    </Box>
  );
}

/**
 * CatalogOverlayControls Component - Controls for catalog overlay
 */
interface CatalogOverlayControlsProps {
  catalog: 'nvss' | 'vlass';
  onCatalogChange: (catalog: 'nvss' | 'vlass') => void;
  showOverlay: boolean;
  onShowOverlayChange: (show: boolean) => void;
  opacity: number;
  onOpacityChange: (opacity: number) => void;
  size: number;
  onSizeChange: (size: number) => void;
  showLabels: boolean;
  onShowLabelsChange: (show: boolean) => void;
  minFluxJy?: number;
  onMinFluxJyChange?: (flux: number) => void;
}

export function CatalogOverlayControls({
  catalog,
  onCatalogChange,
  showOverlay,
  onShowOverlayChange,
  opacity,
  onOpacityChange,
  size,
  onSizeChange,
  showLabels,
  onShowLabelsChange,
  minFluxJy,
  onMinFluxJyChange,
}: CatalogOverlayControlsProps) {
  return (
    <Box sx={{ p: 2 }}>
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Catalog</InputLabel>
        <Select value={catalog} onChange={(e) => onCatalogChange(e.target.value as 'nvss' | 'vlass')}>
          <MenuItem value="nvss">NVSS</MenuItem>
          <MenuItem value="vlass">VLASS</MenuItem>
        </Select>
      </FormControl>

      <FormControlLabel
        control={
          <Switch checked={showOverlay} onChange={(e) => onShowOverlayChange(e.target.checked)} />
        }
        label="Show Catalog Overlay"
        sx={{ mb: 2 }}
      />

      {showOverlay && (
        <>
          <Typography gutterBottom>Opacity</Typography>
          <Slider
            value={opacity}
            onChange={(_, value) => onOpacityChange(value as number)}
            min={0}
            max={1}
            step={0.1}
            sx={{ mb: 2 }}
          />

          <Typography gutterBottom>Marker Size</Typography>
          <Slider
            value={size}
            onChange={(_, value) => onSizeChange(value as number)}
            min={1}
            max={20}
            step={1}
            sx={{ mb: 2 }}
          />

          <FormControlLabel
            control={
              <Switch checked={showLabels} onChange={(e) => onShowLabelsChange(e.target.checked)} />
            }
            label="Show Labels"
            sx={{ mb: 2 }}
          />

          {onMinFluxJyChange && (
            <>
              <Typography gutterBottom>
                Minimum Flux: {minFluxJy !== undefined ? `${minFluxJy.toFixed(3)} Jy` : 'None'}
              </Typography>
              <Slider
                value={minFluxJy || 0}
                onChange={(_, value) => onMinFluxJyChange(value as number)}
                min={0}
                max={1}
                step={0.01}
                sx={{ mb: 2 }}
              />
            </>
          )}
        </>
      )}
    </Box>
  );
}

