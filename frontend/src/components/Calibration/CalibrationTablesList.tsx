import React from "react";
import { Box, Typography, Chip, IconButton, Tooltip } from "@mui/material";
import { Refresh as RefreshIcon } from "@mui/icons-material";
import GenericTable from "../GenericTable";
import type { TableColumn } from "../GenericTable";
import { useCalTables } from "../../api/queries";
import { formatDateTime } from "../../utils/dateUtils";

interface CalTableItem {
  name: string;
  path: string;
  type: string;
  ms_name: string;
  created_at: number;
  size_bytes: number;
}

export const CalibrationTablesList: React.FC = () => {
  const { data, isLoading, error, refetch } = useCalTables();

  const columns: TableColumn<CalTableItem>[] = [
    {
      field: "name",
      label: "Table Name",
      sortable: true,
    },
    {
      field: "type",
      label: "Type",
      sortable: true,
      render: (value) => (
        <Chip
          label={value}
          size="small"
          color={value === "B" ? "primary" : value === "G" ? "secondary" : "default"}
          variant="outlined"
        />
      ),
    },
    {
      field: "ms_name",
      label: "Measurement Set",
      sortable: true,
    },
    {
      field: "created_at",
      label: "Created",
      sortable: true,
      render: (value) => formatDateTime(value * 1000),
    },
    {
      field: "size_bytes",
      label: "Size",
      sortable: true,
      render: (value) => {
        const mb = value / (1024 * 1024);
        return `${mb.toFixed(2)} MB`;
      },
    },
  ];

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h6">Existing Calibration Tables</Typography>
        <Tooltip title="Refresh List">
          <IconButton onClick={() => refetch()}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <GenericTable<CalTableItem>
        apiEndpoint="/caltables" // Overridden by useCalTables
        columns={columns}
        data={data?.items || []}
        total={data?.total || 0}
        isLoading={isLoading}
        error={error}
        title=""
        searchable={true}
        disableFetch={true} // We use the hook above
      />
    </Box>
  );
};
