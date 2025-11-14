/**
 * CARTA Histogram Component
 *
 * Displays histogram data from CARTA region analysis.
 */

import { Box, Paper, Typography } from "@mui/material";
import { RegionHistogramData } from "../../services/cartaProtobuf";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface CARTAHistogramProps {
  histogramData?: RegionHistogramData;
  height?: string | number;
}

export default function CARTAHistogram({ histogramData, height = 300 }: CARTAHistogramProps) {
  // Prepare histogram data
  const chartData =
    histogramData && histogramData.counts
      ? histogramData.counts.map((count, idx) => {
          const binCenter = histogramData.firstBinCenter + idx * histogramData.binWidth;
          return {
            bin: binCenter.toFixed(2),
            count: count,
            binCenter: binCenter,
          };
        })
      : [];

  return (
    <Paper sx={{ height, display: "flex", flexDirection: "column", p: 2 }}>
      {histogramData ? (
        <>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Region Histogram
              {histogramData.regionId !== undefined && ` (Region ID: ${histogramData.regionId})`}
              {histogramData.fileId !== undefined && ` | File ID: ${histogramData.fileId}`}
              {histogramData.channel !== undefined && ` | Channel: ${histogramData.channel}`}
              {histogramData.stokes !== undefined && ` | Stokes: ${histogramData.stokes}`}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Mean: {histogramData.mean.toFixed(4)} | Std Dev: {histogramData.stdDev.toFixed(4)} |
              Bins: {histogramData.numBins}
            </Typography>
          </Box>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={height ? Number(height) - 100 : 200}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="bin"
                  label={{ value: "Value", position: "insideBottom", offset: -5 }}
                />
                <YAxis label={{ value: "Count", angle: -90, position: "insideLeft" }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" fill="#8884d8" name="Frequency" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
              }}
            >
              <Typography variant="body2" color="text.secondary">
                No histogram data available
              </Typography>
            </Box>
          )}
        </>
      ) : (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
          }}
        >
          <Typography variant="body2" color="text.secondary">
            No histogram data available. Select a region to view histogram.
          </Typography>
        </Box>
      )}
    </Paper>
  );
}
