/**
 * Control Page - Manual job execution interface
 * Refactored to use workflow components for better maintainability
 */
import { useState, useEffect } from "react";
import {
  Box,
  Paper,
  Typography,
  Chip,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import { ExpandMore } from "@mui/icons-material";
import { useMSList, useJobs, useMSMetadata, useCalibratorMatches } from "../api/queries";
import type { MSListEntry } from "../api/types";
import MSTable from "../components/MSTable";
import { computeSelectedMS } from "../utils/selectionLogic";
import { JobManagement } from "../components/workflows/JobManagement";
import { ConversionWorkflow } from "../components/workflows/ConversionWorkflow";
import { CalibrationWorkflow } from "../components/workflows/CalibrationWorkflow";
import { ImagingWorkflow } from "../components/workflows/ImagingWorkflow";
import { WorkflowTemplates } from "../components/workflows/WorkflowTemplates";
import PageBreadcrumbs from "../components/PageBreadcrumbs";

export default function ControlPage() {
  const [selectedMS, setSelectedMS] = useState("");
  const [selectedMSList, setSelectedMSList] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  // Queries
  const { data: msList, refetch: refetchMS } = useMSList({
    scan: true,
    scan_dir: "/scratch/dsa110-contimg/ms",
  });
  const { data: msMetadata } = useMSMetadata(selectedMS);
  const {
    data: calMatches,
    isLoading: calMatchesLoading,
    error: calMatchesError,
  } = useCalibratorMatches(selectedMS);
  const { refetch: refetchJobs } = useJobs();

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ctrl/Cmd + R to refresh (but prevent page reload)
      if ((e.ctrlKey || e.metaKey) && e.key === "r" && !e.shiftKey) {
        const target = e.target as HTMLElement;
        if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
          return; // Allow normal refresh
        }
        e.preventDefault();
        refetchMS();
        refetchJobs();
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [refetchMS, refetchJobs]);

  // Job creation callback
  const handleJobCreated = (jobId: number) => {
    setSelectedJobId(jobId);
    refetchJobs();
  };

  return (
    <>
      <PageBreadcrumbs />
      <Box sx={{ p: 3 }}>
        <Typography variant="h2" component="h2" gutterBottom>
          Control Panel
        </Typography>

        <Box sx={{ display: "flex", gap: 2 }}>
          {/* Left column - MS selection and workflows */}
          <Box sx={{ flex: 1 }}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Measurement Sets
              </Typography>
              <MSTable
                data={msList?.items || []}
                total={msList?.total}
                filtered={msList?.filtered}
                selected={selectedMSList}
                onSelectionChange={(paths: string[]) => {
                  const prevList = selectedMSList;
                  setSelectedMSList(paths);
                  const newSelectedMS = computeSelectedMS(paths, prevList, selectedMS);
                  setSelectedMS(newSelectedMS);
                }}
                onMSClick={(ms: MSListEntry) => {
                  setSelectedMS(ms.path);
                  setSelectedMSList((prev) => {
                    if (!prev.includes(ms.path)) {
                      return [...prev, ms.path];
                    }
                    return prev;
                  });
                  const metadataPanel = document.getElementById("ms-metadata-panel");
                  if (metadataPanel) {
                    metadataPanel.scrollIntoView({
                      behavior: "smooth",
                      block: "nearest",
                    });
                  }
                }}
                onRefresh={refetchMS}
              />

              {/* MS Metadata Panel */}
              {selectedMS && msMetadata && (
                <Box
                  id="ms-metadata-panel"
                  sx={{ mt: 2, p: 2, bgcolor: "#1e1e1e", borderRadius: 1 }}
                >
                  <Typography variant="subtitle2" gutterBottom sx={{ color: "#ffffff" }}>
                    MS Information
                  </Typography>
                  <Box
                    sx={{
                      fontSize: "0.75rem",
                      fontFamily: "monospace",
                      color: "#ffffff",
                    }}
                  >
                    {msMetadata.start_time && (
                      <Box sx={{ mb: 0.5 }}>
                        <strong>Time:</strong> {msMetadata.start_time} → {msMetadata.end_time} (
                        {msMetadata.duration_sec?.toFixed(1)}s)
                      </Box>
                    )}
                    {msMetadata.freq_min_ghz && (
                      <Box sx={{ mb: 0.5 }}>
                        <strong>Frequency:</strong> {msMetadata.freq_min_ghz.toFixed(3)} -{" "}
                        {msMetadata.freq_max_ghz?.toFixed(3)} GHz ({msMetadata.num_channels}{" "}
                        channels)
                      </Box>
                    )}
                    {msMetadata.fields && msMetadata.fields.length > 0 && (
                      <Box sx={{ mb: 0.5 }}>
                        <strong>Fields:</strong>{" "}
                        {msMetadata.fields
                          .map(
                            (f) =>
                              `${f.name} (RA: ${f.ra_deg.toFixed(4)}°, Dec: ${f.dec_deg.toFixed(4)}°)`
                          )
                          .join("; ")}
                      </Box>
                    )}
                    {msMetadata.num_fields !== undefined &&
                      !msMetadata.fields &&
                      msMetadata.field_names && (
                        <Box sx={{ mb: 0.5 }}>
                          <strong>Fields:</strong> {msMetadata.num_fields}{" "}
                          {msMetadata.field_names && `(${msMetadata.field_names.join(", ")})`}
                        </Box>
                      )}
                    {msMetadata.antennas && msMetadata.antennas.length > 0 && (
                      <Box sx={{ mb: 0.5 }}>
                        <strong>Antennas:</strong>{" "}
                        {msMetadata.antennas.map((a) => `${a.name} (${a.antenna_id})`).join(", ")}
                      </Box>
                    )}
                    {msMetadata.num_antennas !== undefined &&
                      (!msMetadata.antennas || msMetadata.antennas.length === 0) && (
                        <Box sx={{ mb: 0.5 }}>
                          <strong>Antennas:</strong> {msMetadata.num_antennas}
                        </Box>
                      )}
                    {msMetadata.flagging_stats && (
                      <Box sx={{ mb: 0.5 }}>
                        <strong>Flagging:</strong>{" "}
                        {(msMetadata.flagging_stats.total_fraction * 100).toFixed(1)}% flagged
                        {msMetadata.flagging_stats.per_antenna &&
                          Object.keys(msMetadata.flagging_stats.per_antenna).length > 0 && (
                            <Accordion sx={{ mt: 1, bgcolor: "#2e2e2e" }}>
                              <AccordionSummary expandIcon={<ExpandMore sx={{ color: "#fff" }} />}>
                                <Typography variant="caption" sx={{ color: "#aaa" }}>
                                  Per-antenna flagging breakdown
                                </Typography>
                              </AccordionSummary>
                              <AccordionDetails>
                                <Box sx={{ maxHeight: 200, overflow: "auto" }}>
                                  {msMetadata.antennas &&
                                    Object.entries(msMetadata.flagging_stats.per_antenna || {}).map(
                                      ([antId, frac]) => {
                                        const ant = msMetadata.antennas?.find(
                                          (a) => String(a.antenna_id) === antId
                                        );
                                        const flagPercent = ((frac as number) * 100).toFixed(1);
                                        const color =
                                          (frac as number) > 0.5
                                            ? "#f44336"
                                            : (frac as number) > 0.2
                                              ? "#ff9800"
                                              : "#4caf50";
                                        return (
                                          <Box
                                            key={antId}
                                            sx={{
                                              mb: 0.5,
                                              display: "flex",
                                              justifyContent: "space-between",
                                              alignItems: "center",
                                            }}
                                          >
                                            <Typography
                                              variant="caption"
                                              sx={{
                                                color: "#fff",
                                                fontSize: "0.7rem",
                                              }}
                                            >
                                              {ant ? `${ant.name} (${antId})` : `Antenna ${antId}`}
                                            </Typography>
                                            <Chip
                                              label={`${flagPercent}%`}
                                              size="small"
                                              sx={{
                                                height: 16,
                                                fontSize: "0.6rem",
                                                bgcolor: color,
                                                color: "#fff",
                                              }}
                                            />
                                          </Box>
                                        );
                                      }
                                    )}
                                </Box>
                              </AccordionDetails>
                            </Accordion>
                          )}
                        {msMetadata.flagging_stats.per_field &&
                          Object.keys(msMetadata.flagging_stats.per_field).length > 0 && (
                            <Accordion sx={{ mt: 1, bgcolor: "#2e2e2e" }}>
                              <AccordionSummary expandIcon={<ExpandMore sx={{ color: "#fff" }} />}>
                                <Typography variant="caption" sx={{ color: "#aaa" }}>
                                  Per-field flagging breakdown
                                </Typography>
                              </AccordionSummary>
                              <AccordionDetails>
                                <Box sx={{ maxHeight: 200, overflow: "auto" }}>
                                  {msMetadata.fields &&
                                    Object.entries(msMetadata.flagging_stats.per_field || {}).map(
                                      ([fieldId, frac]) => {
                                        const field = msMetadata.fields?.find(
                                          (f) => String(f.field_id) === fieldId
                                        );
                                        const flagPercent = ((frac as number) * 100).toFixed(1);
                                        const color =
                                          (frac as number) > 0.5
                                            ? "#f44336"
                                            : (frac as number) > 0.2
                                              ? "#ff9800"
                                              : "#4caf50";
                                        return (
                                          <Box
                                            key={fieldId}
                                            sx={{
                                              mb: 0.5,
                                              display: "flex",
                                              justifyContent: "space-between",
                                              alignItems: "center",
                                            }}
                                          >
                                            <Typography
                                              variant="caption"
                                              sx={{
                                                color: "#fff",
                                                fontSize: "0.7rem",
                                              }}
                                            >
                                              {field
                                                ? `${field.name} (Field ${fieldId})`
                                                : `Field ${fieldId}`}
                                            </Typography>
                                            <Chip
                                              label={`${flagPercent}%`}
                                              size="small"
                                              sx={{
                                                height: 16,
                                                fontSize: "0.6rem",
                                                bgcolor: color,
                                                color: "#fff",
                                              }}
                                            />
                                          </Box>
                                        );
                                      }
                                    )}
                                </Box>
                              </AccordionDetails>
                            </Accordion>
                          )}
                      </Box>
                    )}
                    {msMetadata.size_gb !== undefined && (
                      <Box sx={{ mb: 0.5 }}>
                        <strong>Size:</strong> {msMetadata.size_gb} GB
                      </Box>
                    )}
                    <Box sx={{ mb: 0.5 }}>
                      <strong>Columns:</strong> {msMetadata.data_columns.join(", ")}
                    </Box>
                    <Box>
                      <strong>Calibrated:</strong>
                      <Chip
                        label={msMetadata.calibrated ? "YES" : "NO"}
                        color={msMetadata.calibrated ? "success" : "default"}
                        size="small"
                        sx={{ ml: 1, height: 20, fontSize: "0.7rem" }}
                      />
                    </Box>
                  </Box>
                </Box>
              )}

              {/* Calibrator Match Display */}
              {selectedMS && selectedMSList.length === 1 && (
                <>
                  {calMatchesLoading && (
                    <Box sx={{ mt: 2, p: 2, bgcolor: "#1e1e1e", borderRadius: 1 }}>
                      <Typography variant="caption" sx={{ color: "#888" }}>
                        Searching for calibrators...
                      </Typography>
                    </Box>
                  )}
                  {(calMatchesError ||
                    (!calMatchesLoading && (!calMatches || calMatches.matches.length === 0))) && (
                    <Box
                      sx={{
                        mt: 2,
                        p: 1.5,
                        bgcolor: "#3e2723",
                        borderRadius: 1,
                        border: "1px solid #d32f2f",
                      }}
                    >
                      <Typography variant="caption" sx={{ color: "#ffccbc" }}>
                        {"\u2717"} No calibrators detected
                        {(() => {
                          const msEntry = msList?.items.find((ms) => ms.path === selectedMS);
                          if (msEntry?.has_calibrator) {
                            return " (but MS list indicates calibrator exists - API call may have failed)";
                          }
                          return " (pointing may not contain suitable source)";
                        })()}
                      </Typography>
                    </Box>
                  )}
                  {!calMatchesLoading &&
                    !calMatchesError &&
                    calMatches &&
                    calMatches.matches.length > 0 && (
                      <Box sx={{ mt: 2 }}>
                        {(() => {
                          const best = calMatches.matches[0];
                          const qualityColor =
                            {
                              excellent: "#4caf50",
                              good: "#8bc34a",
                              marginal: "#ff9800",
                              poor: "#f44336",
                            }[best.quality] || "#888";

                          return (
                            <>
                              <Box
                                sx={{
                                  p: 1.5,
                                  bgcolor: "#1e3a1e",
                                  borderRadius: 1,
                                  border: `2px solid ${qualityColor}`,
                                }}
                              >
                                <Typography
                                  variant="subtitle2"
                                  sx={{
                                    color: "#ffffff",
                                    mb: 1,
                                    fontWeight: "bold",
                                  }}
                                >
                                  {"\u2713"} Best Calibrator: {best.name}
                                </Typography>
                                <Box
                                  sx={{
                                    fontSize: "0.75rem",
                                    fontFamily: "monospace",
                                    color: "#ffffff",
                                  }}
                                >
                                  <Box sx={{ mb: 0.5 }}>
                                    <strong>Flux:</strong> {best.flux_jy.toFixed(2)} Jy |{" "}
                                    <strong>PB:</strong> {best.pb_response.toFixed(3)} |
                                    <Chip
                                      label={best.quality.toUpperCase()}
                                      size="small"
                                      sx={{
                                        ml: 1,
                                        height: 18,
                                        fontSize: "0.65rem",
                                        bgcolor: qualityColor,
                                        color: "#fff",
                                        fontWeight: "bold",
                                      }}
                                    />
                                  </Box>
                                  <Box sx={{ mb: 0.5 }}>
                                    <strong>Position:</strong> RA {best.ra_deg.toFixed(4)}° | Dec{" "}
                                    {best.dec_deg.toFixed(4)}°
                                  </Box>
                                  <Box>
                                    <strong>Separation:</strong> {best.sep_deg.toFixed(3)}° from
                                    meridian
                                  </Box>
                                </Box>
                              </Box>

                              {calMatches.matches.length > 1 && (
                                <Accordion sx={{ mt: 1, bgcolor: "#2e2e2e" }}>
                                  <AccordionSummary
                                    expandIcon={<ExpandMore sx={{ color: "#fff" }} />}
                                  >
                                    <Typography variant="caption" sx={{ color: "#aaa" }}>
                                      {calMatches.matches.length - 1} additional calibrator
                                      {calMatches.matches.length > 2 ? "s" : ""} found
                                    </Typography>
                                  </AccordionSummary>
                                  <AccordionDetails>
                                    <Box sx={{ maxHeight: 200, overflow: "auto" }}>
                                      {calMatches.matches.slice(1).map((match, idx) => {
                                        const qualityColor =
                                          {
                                            excellent: "#4caf50",
                                            good: "#8bc34a",
                                            marginal: "#ff9800",
                                            poor: "#f44336",
                                          }[match.quality] || "#888";
                                        return (
                                          <Box
                                            key={idx}
                                            sx={{
                                              mb: 1,
                                              p: 1,
                                              bgcolor: "#1e1e1e",
                                              borderRadius: 1,
                                              border: `1px solid ${qualityColor}`,
                                            }}
                                          >
                                            <Typography
                                              variant="caption"
                                              sx={{ color: "#fff", fontWeight: "bold" }}
                                            >
                                              {match.name}
                                            </Typography>
                                            <Box
                                              sx={{
                                                fontSize: "0.7rem",
                                                fontFamily: "monospace",
                                                color: "#aaa",
                                              }}
                                            >
                                              {match.flux_jy.toFixed(2)} Jy | PB{" "}
                                              {match.pb_response.toFixed(3)} |{" "}
                                              <Chip
                                                label={match.quality.toUpperCase()}
                                                size="small"
                                                sx={{
                                                  height: 16,
                                                  fontSize: "0.6rem",
                                                  bgcolor: qualityColor,
                                                  color: "#fff",
                                                }}
                                              />
                                            </Box>
                                          </Box>
                                        );
                                      })}
                                    </Box>
                                  </AccordionDetails>
                                </Accordion>
                              )}
                            </>
                          );
                        })()}
                      </Box>
                    )}
                </>
              )}
            </Paper>

            {/* Workflow Tabs */}
            <Paper sx={{ p: 2 }}>
              <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)}>
                <Tab label="Templates" />
                <Tab label="Convert" />
                <Tab label="Calibrate" />
                <Tab label="Image" />
              </Tabs>

              {/* Templates Tab */}
              {activeTab === 0 && (
                <WorkflowTemplates
                  onTemplateSelect={(template) => {
                    // Navigate to appropriate workflow based on template
                    if (template.category === "calibration") {
                      setActiveTab(2); // Calibrate tab
                    } else if (template.category === "imaging") {
                      setActiveTab(3); // Image tab
                    } else if (template.category === "mosaic") {
                      // Could navigate to mosaics page
                    }
                  }}
                />
              )}

              {/* Convert Tab */}
              {activeTab === 1 && (
                <ConversionWorkflow
                  selectedMS={selectedMS}
                  onJobCreated={handleJobCreated}
                  onRefreshJobs={refetchJobs}
                />
              )}

              {/* Calibrate Tab (includes Apply sub-tab) */}
              {activeTab === 2 && (
                <CalibrationWorkflow
                  selectedMS={selectedMS}
                  selectedMSList={selectedMSList}
                  onJobCreated={handleJobCreated}
                  onRefreshJobs={refetchJobs}
                />
              )}

              {/* Image Tab */}
              {activeTab === 3 && (
                <ImagingWorkflow
                  selectedMS={selectedMS}
                  onJobCreated={handleJobCreated}
                  onRefreshJobs={refetchJobs}
                />
              )}
            </Paper>
          </Box>

          {/* Right column - Job management */}
          <JobManagement selectedJobId={selectedJobId} onJobSelect={setSelectedJobId} />
        </Box>
      </Box>
    </>
  );
}
