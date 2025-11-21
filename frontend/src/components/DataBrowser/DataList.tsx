import React, { useState } from "react";
import { Box, Tabs, Tab, Chip, TextField, MenuItem, Stack } from "@mui/material";
import { useNavigate } from "react-router-dom";
import GenericTable from "../GenericTable";
import type { TableColumn } from "../GenericTable";
import { formatDateTime } from "../../utils/dateUtils";

// Define basic interfaces for the data items
interface ImageItem {
  id: number;
  name: string;
  image_type: string;
  center_ra_deg?: number;
  center_dec_deg?: number;
  noise_jy?: number;
  created_at: string;
}

interface MSItem {
  id: number;
  name: string;
  scan_id?: number;
  is_calibrated: boolean;
  has_calibrator: boolean;
  created_at: string;
}

export const DataList: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"images" | "ms">("images");
  const [timeRange, setTimeRange] = useState<"all" | "24h" | "7d" | "30d">("all");

  // Helper to get start date based on range
  const getStartDate = () => {
    if (timeRange === "all") return undefined;
    const now = new Date();
    if (timeRange === "24h") now.setHours(now.getHours() - 24);
    if (timeRange === "7d") now.setDate(now.getDate() - 7);
    if (timeRange === "30d") now.setDate(now.getDate() - 30);
    return now.toISOString();
  };

  // Columns for Images
  const imageColumns: TableColumn<ImageItem>[] = [
    {
      field: "name",
      label: "Name",
      sortable: true,
      link: (row) => `/images/${row.id}`,
    },
    {
      field: "image_type",
      label: "Type",
      sortable: true,
      render: (value) => <Chip label={value as string} size="small" variant="outlined" />,
    },
    {
      field: "center_ra_deg",
      label: "RA (deg)",
      sortable: true,
      render: (value) => (value ? (value as number).toFixed(4) : "N/A"),
    },
    {
      field: "center_dec_deg",
      label: "Dec (deg)",
      sortable: true,
      render: (value) => (value ? (value as number).toFixed(4) : "N/A"),
    },
    {
      field: "noise_jy",
      label: "Noise (mJy)",
      sortable: true,
      render: (value) => (value ? ((value as number) * 1000).toFixed(2) : "N/A"),
    },
    {
      field: "created_at",
      label: "Created At",
      sortable: true,
      render: (value) => formatDateTime(value as string),
    },
  ];

  // Columns for Measurement Sets
  const msColumns: TableColumn<MSItem>[] = [
    {
      field: "name",
      label: "Name",
      sortable: true,
    },
    {
      field: "scan_id",
      label: "Scan ID",
      sortable: true,
    },
    {
      field: "is_calibrated",
      label: "Calibrated",
      sortable: true,
      render: (value) => (
        <Chip label={value ? "Yes" : "No"} color={value ? "success" : "default"} size="small" />
      ),
    },
    {
      field: "has_calibrator",
      label: "Has Calibrator",
      sortable: true,
      render: (value) => (value ? "Yes" : "No"),
    },
    {
      field: "created_at",
      label: "Created At",
      sortable: true,
      render: (value) => formatDateTime(value as string),
    },
  ];

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
        <Tabs
          value={activeTab}
          onChange={(_, val) => setActiveTab(val)}
          aria-label="data type tabs"
        >
          <Tab label="Images" value="images" />
          <Tab label="Measurement Sets" value="ms" />
        </Tabs>

        <TextField
          select
          label="Time Range"
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value as "all" | "24h" | "7d" | "30d")}
          size="small"
          sx={{ minWidth: 150 }}
        >
          <MenuItem value="all">All Time</MenuItem>
          <MenuItem value="24h">Last 24 Hours</MenuItem>
          <MenuItem value="7d">Last 7 Days</MenuItem>
          <MenuItem value="30d">Last 30 Days</MenuItem>
        </TextField>
      </Stack>

      {activeTab === "images" && (
        <GenericTable<ImageItem>
          apiEndpoint="/images"
          columns={imageColumns}
          title=""
          searchable={true}
          exportable={true}
          queryParams={{ start_date: getStartDate() }}
          transformData={(data) => ({
            rows: data.items || [],
            total: data.total || 0,
          })}
          onRowClick={(row) => navigate(`/images/${row.id}`)}
        />
      )}

      {activeTab === "ms" && (
        <GenericTable<MSItem>
          apiEndpoint="/ms"
          columns={msColumns}
          title=""
          searchable={true}
          exportable={true}
          queryParams={{ start_date: getStartDate(), scan_dir: "/stage/dsa110-contimg/ms" }}
          transformData={(data) => ({
            rows: data.items || [],
            total: data.total || 0,
          })}
        />
      )}
    </Box>
  );
};
