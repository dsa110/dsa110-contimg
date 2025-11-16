/**
 * Lazy-loaded Plotly component wrapper
 *
 * This component dynamically imports Plotly to reduce initial bundle size.
 * Plotly is a large library (~4.7MB) that's only needed on specific pages.
 * By lazy loading it, we improve initial page load performance.
 */

import { lazy, Suspense } from "react";
import { Box, CircularProgress, Typography } from "@mui/material";

// Lazy load the Plot component
// react-plotly.js exports Plot as default, so React.lazy works directly
const Plot = lazy(() => import("react-plotly.js"));

// Re-export Plotly types
export type { Data, Layout } from "plotly.js";

interface PlotlyLazyProps {
  data: any;
  layout?: any;
  config?: any;
  style?: React.CSSProperties;
  className?: string;
  onInitialized?: (figure: any, graphDiv: HTMLElement) => void;
  onUpdate?: (figure: any, graphDiv: HTMLElement) => void;
  onRelayout?: (eventData: any) => void;
  revision?: number;
  [key: string]: any;
}

/**
 * Lazy-loaded Plotly component with loading fallback
 */
export function PlotlyLazy(props: PlotlyLazyProps) {
  return (
    <Suspense
      fallback={
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 200,
            gap: 2,
          }}
        >
          <CircularProgress size={40} />
          <Typography variant="body2" color="text.secondary">
            Loading chart...
          </Typography>
        </Box>
      }
    >
      <Plot {...(props as any)} />
    </Suspense>
  );
}

// Export the lazy component for direct use if needed
export const LazyPlot = Plot;
