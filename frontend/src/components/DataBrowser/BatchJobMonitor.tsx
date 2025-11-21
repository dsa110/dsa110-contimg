import React from "react";
import { Chip } from "@mui/material";
import GenericTable from "../GenericTable";
import type { TableColumn } from "../GenericTable";
import { formatDateTime } from "../../utils/dateUtils";

interface BatchJobItem {
  id: number;
  job_type: string;
  status: string;
  item_count: number;
  processed_count: number;
  created_at: string;
}

export const BatchJobMonitor: React.FC = () => {
  const columns: TableColumn<BatchJobItem>[] = [
    {
      field: "id",
      label: "Job ID",
      sortable: true,
    },
    {
      field: "job_type",
      label: "Type",
      sortable: true,
      render: (value) => <Chip label={value as string} size="small" variant="outlined" />,
    },
    {
      field: "status",
      label: "Status",
      sortable: true,
      render: (value) => {
        let color: "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" =
          "default";
        if (value === "completed") color = "success";
        if (value === "failed") color = "error";
        if (value === "running") color = "info";
        if (value === "pending") color = "warning";
        return <Chip label={value as string} color={color} size="small" />;
      },
    },
    {
      field: "item_count",
      label: "Items",
      sortable: true,
    },
    {
      field: "processed_count",
      label: "Processed",
      sortable: true,
    },
    {
      field: "created_at",
      label: "Created",
      sortable: true,
      render: (value) => formatDateTime(value as string),
    },
  ];

  return (
    <GenericTable<BatchJobItem>
      apiEndpoint="/batch"
      columns={columns}
      title=""
      searchable={true}
      refreshInterval={5000}
      transformData={(data) => ({
        rows: data.jobs || [],
        total: data.total || 0,
      })}
    />
  );
};
