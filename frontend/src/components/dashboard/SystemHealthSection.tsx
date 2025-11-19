import React from "react";
import { Box, Typography, Button, Chip, Skeleton } from "@mui/material";
import { useNavigate } from "react-router-dom";
import CollapsibleSection from "../CollapsibleSection";
import { StatusIndicator } from "../StatusIndicator";
import { DASHBOARD_CONFIG } from "../../config/dashboard";
import { useMetricHistory } from "../../hooks/useMetricHistory";
import type { SystemMetrics, DiskInfo } from "../../api/types";
import { formatDateTime } from "../../utils/dateUtils";

// Define the health check record structure locally or export if used elsewhere
export type HealthCheckRecord = Record<string, { healthy: boolean; error?: string }>;

interface SystemHealthSectionProps {
  metrics?: SystemMetrics;
  healthSummary?: { checks?: unknown; timestamp?: number } | null;
  loading?: boolean;
}

export const SystemHealthSection: React.FC<SystemHealthSectionProps> = ({
  metrics,
  healthSummary,
  loading,
}) => {
  const navigate = useNavigate();

  // Track metric history for sparklines
  const cpuHistory = useMetricHistory(metrics?.cpu_percent);
  const memHistory = useMetricHistory(metrics?.mem_percent);
  const loadHistory = useMetricHistory(metrics?.load_1);

  // Use new disks array format - track both / (SSD) and /data/ (HDD)
  const ssdDisk = metrics?.disks?.find((d: DiskInfo) => d.mount_point.startsWith("/ (SSD)"));
  const hddDisk = metrics?.disks?.find((d: DiskInfo) => d.mount_point.startsWith("/data/"));
  const ssdDiskHistory = useMetricHistory(ssdDisk?.percent);
  const hddDiskHistory = useMetricHistory(hddDisk?.percent);

  const overallStatus = healthSummary ? (healthSummary as any).status : "unknown";
  const healthChecks = healthSummary ? (healthSummary as any).checks : {};
  const healthSummaryTimestamp = healthSummary
    ? new Date((healthSummary as any).timestamp * 1000)
    : null;

  return (
    <CollapsibleSection title="System Health" defaultExpanded={true} variant="outlined">
      <Box sx={{ mt: 2 }}>
        {loading ? (
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} variant="rectangular" width={200} height={100} />
            ))}
          </Box>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {/* Key Metrics - 2 Row Layout */}
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "repeat(2, 1fr)",
                  md: "repeat(3, 1fr)",
                },
                gap: 2,
              }}
            >
              <StatusIndicator
                label="CPU Usage"
                value={metrics?.cpu_percent || 0}
                thresholds={DASHBOARD_CONFIG.thresholds.cpu}
                unit="%"
                showTrend={cpuHistory.length > 1}
                previousValue={
                  cpuHistory.length > 1 ? cpuHistory[cpuHistory.length - 2] : undefined
                }
              />
              <StatusIndicator
                label="Memory Usage"
                value={metrics?.mem_percent || 0}
                thresholds={DASHBOARD_CONFIG.thresholds.memory}
                unit="%"
                showTrend={memHistory.length > 1}
                previousValue={
                  memHistory.length > 1 ? memHistory[memHistory.length - 2] : undefined
                }
              />
              <StatusIndicator
                label="SSD (root)"
                value={ssdDisk?.percent || 0}
                thresholds={DASHBOARD_CONFIG.thresholds.disk}
                unit="%"
                showTrend={ssdDiskHistory.length > 1}
                previousValue={
                  ssdDiskHistory.length > 1 ? ssdDiskHistory[ssdDiskHistory.length - 2] : undefined
                }
              />
              <StatusIndicator
                label="HDD (/data/)"
                value={hddDisk?.percent || 0}
                thresholds={DASHBOARD_CONFIG.thresholds.disk}
                unit="%"
                showTrend={hddDiskHistory.length > 1}
                previousValue={
                  hddDiskHistory.length > 1 ? hddDiskHistory[hddDiskHistory.length - 2] : undefined
                }
              />
              <StatusIndicator
                label="System Load"
                value={metrics?.load_1 || 0}
                thresholds={DASHBOARD_CONFIG.thresholds.load}
                unit=""
                showTrend={loadHistory.length > 1}
                previousValue={
                  loadHistory.length > 1 ? loadHistory[loadHistory.length - 2] : undefined
                }
              />
            </Box>

            {/* Timestamp and Footer */}
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderTop: "1px solid",
                borderColor: "divider",
                pt: 2,
              }}
            >
              <Typography variant="caption" color="text.secondary">
                Last updated: {formatDateTime(metrics?.ts || healthSummaryTimestamp)}
              </Typography>
              <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
                {overallStatus && (
                  <Chip
                    label={`Status: ${overallStatus.toUpperCase()}`}
                    color={
                      overallStatus === "healthy"
                        ? "success"
                        : overallStatus === "degraded"
                          ? "warning"
                          : "error"
                    }
                    size="small"
                  />
                )}
                <Button size="small" onClick={() => navigate("/health")}>
                  View Full Diagnostics
                </Button>
              </Box>
            </Box>
          </Box>
        )}
      </Box>
    </CollapsibleSection>
  );
};
