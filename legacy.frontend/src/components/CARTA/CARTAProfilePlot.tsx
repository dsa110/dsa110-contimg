/**
 * CARTA Profile Plot Component
 *
 * Displays spatial or spectral profiles from CARTA data.
 */

import { Box, Paper, Typography, Tabs, Tab } from "@mui/material";
import { useState } from "react";
import type { SpatialProfileData, SpectralProfileData } from "../../services/cartaProtobuf";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface CARTAProfilePlotProps {
  spatialProfile?: SpatialProfileData;
  spectralProfile?: SpectralProfileData;
  height?: string | number;
}

export default function CARTAProfilePlot({
  spatialProfile,
  spectralProfile,
  height = 300,
}: CARTAProfilePlotProps) {
  const [tab, setTab] = useState<"spatial" | "spectral">(spatialProfile ? "spatial" : "spectral");

  // Prepare spatial profile data
  const spatialData =
    spatialProfile && spatialProfile.values
      ? spatialProfile.values.map((value, idx) => ({
          index: spatialProfile.start + idx,
          value: value,
          coordinate: spatialProfile.coordinates?.[idx] ?? spatialProfile.start + idx,
        }))
      : [];

  // Prepare spectral profile data
  const spectralData =
    spectralProfile && spectralProfile.profiles
      ? spectralProfile.profiles.map((profile) => ({
          coordinate: profile.coordinate,
          value: profile.value,
        }))
      : [];

  return (
    <Paper sx={{ height, display: "flex", flexDirection: "column" }}>
      <Tabs value={tab} onChange={(_, v) => setTab(v)}>
        {spatialProfile && <Tab label="Spatial Profile" value="spatial" />}
        {spectralProfile && <Tab label="Spectral Profile" value="spectral" />}
      </Tabs>

      <Box sx={{ flex: 1, p: 2 }}>
        {tab === "spatial" && spatialProfile && (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Spatial Profile
              {spatialProfile.fileId !== undefined && ` (File ID: ${spatialProfile.fileId})`}
              {spatialProfile.channel !== undefined && ` | Channel: ${spatialProfile.channel}`}
              {spatialProfile.stokes !== undefined && ` | Stokes: ${spatialProfile.stokes}`}
            </Typography>
            {spatialData.length > 0 ? (
              <ResponsiveContainer width="100%" height={height ? Number(height) - 100 : 200}>
                <LineChart data={spatialData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="coordinate"
                    label={{ value: "Position", position: "insideBottom", offset: -5 }}
                  />
                  <YAxis label={{ value: "Intensity", angle: -90, position: "insideLeft" }} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#8884d8"
                    strokeWidth={2}
                    dot={false}
                    name="Intensity"
                  />
                </LineChart>
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
                  No spatial profile data available
                </Typography>
              </Box>
            )}
          </Box>
        )}

        {tab === "spectral" && spectralProfile && (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Spectral Profile
              {spectralProfile.fileId !== undefined && ` (File ID: ${spectralProfile.fileId})`}
              {spectralProfile.stokes !== undefined && ` | Stokes: ${spectralProfile.stokes}`}
              {spectralProfile.progress !== undefined &&
                ` | Progress: ${spectralProfile.progress}%`}
            </Typography>
            {spectralData.length > 0 ? (
              <ResponsiveContainer width="100%" height={height ? Number(height) - 100 : 200}>
                <LineChart data={spectralData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="coordinate"
                    label={{ value: "Frequency/Channel", position: "insideBottom", offset: -5 }}
                  />
                  <YAxis label={{ value: "Intensity", angle: -90, position: "insideLeft" }} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#82ca9d"
                    strokeWidth={2}
                    dot={false}
                    name="Intensity"
                  />
                </LineChart>
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
                  No spectral profile data available
                </Typography>
              </Box>
            )}
          </Box>
        )}

        {!spatialProfile && !spectralProfile && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
            }}
          >
            <Typography variant="body2" color="text.secondary">
              No profile data available. Select a region to view profiles.
            </Typography>
          </Box>
        )}
      </Box>
    </Paper>
  );
}
