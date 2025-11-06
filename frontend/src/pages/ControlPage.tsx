/**
 * Control Page - Manual job execution interface
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Tabs,
  Tab,
  Stack,
  FormControlLabel,
  Checkbox,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  RadioGroup,
  Radio,
  Divider,
  Alert,
  Tooltip,
  CircularProgress,
  Snackbar,
} from '@mui/material';
import {
  PlayArrow,
  Refresh,
  ExpandMore,
} from '@mui/icons-material';
import {
  useMSList,
  useJobs,
  useCreateCalibrateJob,
  useCreateApplyJob,
  useCreateImageJob,
  useCreateConvertJob,
  useUVH5Files,
  useMSMetadata,
  useCalibratorMatches,
  useExistingCalTables,
  useCalTables, 
  useCreateWorkflowJob,
  useValidateCalTable,
} from '../api/queries';
import type { JobParams, ConversionJobParams, CalibrateJobParams, MSListEntry } from '../api/types';
import MSTable from '../components/MSTable';
import { computeSelectedMS } from '../utils/selectionLogic';

export default function ControlPage() {
  const [selectedMS, setSelectedMS] = useState('');
  const [selectedMSList, setSelectedMSList] = useState<string[]>([]);  // Multi-select for batch ops
  const [activeTab, setActiveTab] = useState(0);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [logContent, setLogContent] = useState('');
  
  // Error state for user-facing error messages
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorSnackbarOpen, setErrorSnackbarOpen] = useState(false);
  
  // Compatibility check state
  const [compatibilityChecks, setCompatibilityChecks] = useState<Record<string, {
    is_compatible: boolean;
    issues: string[];
    warnings: string[];
  }>>({});
  const validateCalTable = useValidateCalTable();
  
  // Form states
  const [calibParams, setCalibParams] = useState<CalibrateJobParams>({
    field: '',
    refant: '103',
    solve_delay: true,
    solve_bandpass: true,
    solve_gains: true,
    gain_solint: 'inf',
    gain_calmode: 'ap',
    auto_fields: true,
    min_pb: 0.5,
    do_flagging: false,
    use_existing_tables: 'auto',
    existing_k_table: undefined,
    existing_bp_table: undefined,
    existing_g_table: undefined,
  });
  
  const [applyParams, setApplyParams] = useState<JobParams>({
    gaintables: [],
  });
  
  const [imageParams, setImageParams] = useState<JobParams>({
    gridder: 'wproject',
    wprojplanes: -1,
    datacolumn: 'corrected',
    quick: false,
    skip_fits: true,
  });
  
  const [convertParams, setConvertParams] = useState<ConversionJobParams>({
    input_dir: '/data/incoming',
    output_dir: '/scratch/dsa110-contimg/ms',
    start_time: '',
    end_time: '',
    writer: 'auto',
    stage_to_tmpfs: true,
    max_workers: 4,
  });

  // Queries and mutations
  const { data: msList, refetch: refetchMS } = useMSList();
  const { data: jobsList, refetch: refetchJobs } = useJobs();
  const calibrateMutation = useCreateCalibrateJob();
  const applyMutation = useCreateApplyJob();
  const imageMutation = useCreateImageJob();
  const convertMutation = useCreateConvertJob();
  
  // Data hooks - always called at top level
  const { data: msMetadata } = useMSMetadata(selectedMS);
  const { data: calMatches, isLoading: calMatchesLoading, error: calMatchesError } = useCalibratorMatches(selectedMS);
  const { data: existingTables } = useExistingCalTables(selectedMS);
  const { data: calTables } = useCalTables();
  const { data: uvh5Files } = useUVH5Files(convertParams.input_dir);
  const workflowMutation = useCreateWorkflowJob();
  
  // Clear compatibility checks when MS changes
  useEffect(() => {
    setCompatibilityChecks({});
  }, [selectedMS]);
  
  // Workflow params state
  const [workflowParams, setWorkflowParams] = useState({
    start_time: '',
    end_time: '',
  });

  // SSE for job logs
  const eventSourceRef = useRef<EventSource | null>(null);
  
  // Helper function to extract error message from API error
  const getErrorMessage = (error: any): string => {
    if (error?.response?.data?.detail) {
      return typeof error.response.data.detail === 'string' 
        ? error.response.data.detail 
        : JSON.stringify(error.response.data.detail);
    }
    if (error?.response?.data?.message) {
      return error.response.data.message;
    }
    if (error?.message) {
      return error.message;
    }
    return 'An unknown error occurred';
  };
  
  // Store handlers in refs to avoid recreating the keyboard shortcuts effect
  const handleCalibrateSubmitRef = useRef<() => void>();
  const handleApplySubmitRef = useRef<() => void>();
  const handleImageSubmitRef = useRef<() => void>();
  const handleConvertSubmitRef = useRef<() => void>();

  // Handlers with error handling - wrapped in useCallback to prevent unnecessary re-renders
  const handleCalibrateSubmit = useCallback(() => {
    if (!selectedMS) return;
    setErrorMessage(null);
    calibrateMutation.mutate(
      { ms_path: selectedMS, params: calibParams },
      {
        onSuccess: (job) => {
          setSelectedJobId(job.id);
          setLogContent('');
          refetchJobs();
        },
        onError: (error: any) => {
          const message = `Calibration failed: ${getErrorMessage(error)}`;
          setErrorMessage(message);
          setErrorSnackbarOpen(true);
        },
      }
    );
  }, [selectedMS, calibParams, calibrateMutation, refetchJobs]);
  
  const handleApplySubmit = useCallback(() => {
    if (!selectedMS) return;
    setErrorMessage(null);
    applyMutation.mutate(
      { ms_path: selectedMS, params: applyParams },
      {
        onSuccess: (job) => {
          setSelectedJobId(job.id);
          setLogContent('');
          refetchJobs();
        },
        onError: (error: any) => {
          const message = `Apply calibration failed: ${getErrorMessage(error)}`;
          setErrorMessage(message);
          setErrorSnackbarOpen(true);
        },
      }
    );
  }, [selectedMS, applyParams, applyMutation, refetchJobs]);
  
  const handleImageSubmit = useCallback(() => {
    if (!selectedMS) return;
    setErrorMessage(null);
    imageMutation.mutate(
      { ms_path: selectedMS, params: imageParams },
      {
        onSuccess: (job) => {
          setSelectedJobId(job.id);
          setLogContent('');
          refetchJobs();
        },
        onError: (error: any) => {
          const message = `Imaging failed: ${getErrorMessage(error)}`;
          setErrorMessage(message);
          setErrorSnackbarOpen(true);
        },
      }
    );
  }, [selectedMS, imageParams, imageMutation, refetchJobs]);
  
  const handleConvertSubmit = useCallback(() => {
    setErrorMessage(null);
    convertMutation.mutate(
      { params: convertParams },
      {
        onSuccess: (job) => {
          setSelectedJobId(job.id);
          setLogContent('');
          refetchJobs();
        },
        onError: (error: any) => {
          const message = `Conversion failed: ${getErrorMessage(error)}`;
          setErrorMessage(message);
          setErrorSnackbarOpen(true);
        },
      }
    );
  }, [convertParams, convertMutation, refetchJobs]);

  // Update refs whenever handlers change
  handleCalibrateSubmitRef.current = handleCalibrateSubmit;
  handleApplySubmitRef.current = handleApplySubmit;
  handleImageSubmitRef.current = handleImageSubmit;
  handleConvertSubmitRef.current = handleConvertSubmit;
  
  const handleWorkflowSubmit = () => {
    if (!workflowParams.start_time || !workflowParams.end_time) return;
    setErrorMessage(null);
    workflowMutation.mutate(
      { params: workflowParams },
      {
        onSuccess: (job) => {
          setSelectedJobId(job.id);
          setLogContent('');
          refetchJobs();
        },
        onError: (error: any) => {
          const message = `Workflow failed: ${getErrorMessage(error)}`;
          setErrorMessage(message);
          setErrorSnackbarOpen(true);
        },
      }
    );
  };
  
  useEffect(() => {
    // Clean up any existing EventSource connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    if (selectedJobId !== null) {
      // Use relative URL to leverage Vite proxy configuration
      // In Docker, Vite proxy handles /api -> backend service
      const url = `/api/jobs/id/${selectedJobId}/logs`;
      const eventSource = new EventSource(url);
      
      eventSource.onmessage = (event) => {
        setLogContent((prev) => prev + event.data);
      };
      
      eventSource.onerror = () => {
        eventSource.close();
        eventSourceRef.current = null;
      };
      
      eventSourceRef.current = eventSource;
      
      return () => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      };
    } else {
      // Clear log content when no job is selected
      setLogContent('');
    }
  }, [selectedJobId]);
  
  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Ctrl/Cmd + Enter to run current tab's action
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        if (activeTab === 0) {
          if (!convertParams.start_time || !convertParams.end_time || convertMutation.isPending) return;
          handleConvertSubmitRef.current?.();
        } else if (activeTab === 1) {
          if (!selectedMS || selectedMSList.length !== 1 || calibrateMutation.isPending || (!calibParams.solve_delay && !calibParams.solve_bandpass && !calibParams.solve_gains)) return;
          handleCalibrateSubmitRef.current?.();
        } else if (activeTab === 2) {
          if (!selectedMS || !applyParams.gaintables?.length || applyMutation.isPending) return;
          handleApplySubmitRef.current?.();
        } else if (activeTab === 3) {
          if (!selectedMS || imageMutation.isPending) return;
          handleImageSubmitRef.current?.();
        }
      }
      // Ctrl/Cmd + R to refresh (but prevent page reload)
      if ((e.ctrlKey || e.metaKey) && e.key === 'r' && !e.shiftKey) {
        // Only prevent if we're in a form field (to allow normal refresh elsewhere)
        const target = e.target as HTMLElement;
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
          return; // Allow normal refresh
        }
        e.preventDefault();
        refetchMS();
        refetchJobs();
      }
    };
    
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [
    activeTab,
    // Only include specific values from params objects, not the entire objects
    convertParams.start_time,
    convertParams.end_time,
    calibParams.solve_delay,
    calibParams.solve_bandpass,
    calibParams.solve_gains,
    applyParams.gaintables?.length,
    selectedMS,
    selectedMSList,
    convertMutation.isPending,
    calibrateMutation.isPending,
    applyMutation.isPending,
    imageMutation.isPending,
    // Handlers are accessed via refs, so they don't need to be in the dependency array
    // This prevents the effect from re-running when handlers are recreated
    refetchMS,
    refetchJobs,
  ]);
  
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Control Panel
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 2 }}>
        {/* Left column - Job controls */}
        <Box sx={{ flex: 1 }}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>Measurement Sets</Typography>
            <MSTable
              data={msList?.items || []}
              total={msList?.total}
              filtered={msList?.filtered}
              selected={selectedMSList}
              onSelectionChange={(paths: string[]) => {
                // Capture previous selection before updating (avoid stale closure)
                const prevList = selectedMSList;
                
                // Update selectedMSList
                setSelectedMSList(paths);
                
                // Update selectedMS using pure function (easier to test and debug)
                const newSelectedMS = computeSelectedMS(paths, prevList, selectedMS);
                setSelectedMS(newSelectedMS);
              }}
              onMSClick={(ms: MSListEntry) => {
                // Always set selectedMS when clicking an MS row
                setSelectedMS(ms.path);
                // Also update selectedMSList to include this MS if not already selected
                // Use functional update to avoid stale closure
                setSelectedMSList(prev => {
                  if (!prev.includes(ms.path)) {
                    return [...prev, ms.path];
                  }
                  return prev;
                });
                // Scroll to metadata panel
                const metadataPanel = document.getElementById('ms-metadata-panel');
                if (metadataPanel) {
                  metadataPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
              }}
              onRefresh={refetchMS}
            />
            
            {/* MS Metadata Panel */}
            {selectedMS && msMetadata && (
              <Box id="ms-metadata-panel" sx={{ mt: 2, p: 2, bgcolor: '#1e1e1e', borderRadius: 1 }}>
                <Typography variant="subtitle2" gutterBottom sx={{ color: '#ffffff' }}>
                  MS Information
            </Typography>
                <Box sx={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#ffffff' }}>
                  {msMetadata.start_time && (
                    <Box sx={{ mb: 0.5 }}>
                      <strong>Time:</strong> {msMetadata.start_time} → {msMetadata.end_time} ({msMetadata.duration_sec?.toFixed(1)}s)
                    </Box>
                  )}
                  {msMetadata.freq_min_ghz && (
                    <Box sx={{ mb: 0.5 }}>
                      <strong>Frequency:</strong> {msMetadata.freq_min_ghz.toFixed(3)} - {msMetadata.freq_max_ghz?.toFixed(3)} GHz ({msMetadata.num_channels} channels)
                    </Box>
                  )}
                  {msMetadata.fields && msMetadata.fields.length > 0 && (
                    <Box sx={{ mb: 0.5 }}>
                      <strong>Fields:</strong> {msMetadata.fields.map(f => 
                        `${f.name} (RA: ${f.ra_deg.toFixed(4)}°, Dec: ${f.dec_deg.toFixed(4)}°)`
                      ).join('; ')}
                    </Box>
                  )}
                  {msMetadata.num_fields !== undefined && !msMetadata.fields && msMetadata.field_names && (
                    <Box sx={{ mb: 0.5 }}>
                      <strong>Fields:</strong> {msMetadata.num_fields} {msMetadata.field_names && `(${msMetadata.field_names.join(', ')})`}
                    </Box>
                  )}
                  {msMetadata.antennas && msMetadata.antennas.length > 0 && (
                    <Box sx={{ mb: 0.5 }}>
                      <strong>Antennas:</strong> {msMetadata.antennas.map(a => `${a.name} (${a.antenna_id})`).join(', ')}
                    </Box>
                  )}
                  {msMetadata.num_antennas !== undefined && (!msMetadata.antennas || msMetadata.antennas.length === 0) && (
                    <Box sx={{ mb: 0.5 }}>
                      <strong>Antennas:</strong> {msMetadata.num_antennas}
                    </Box>
                  )}
                  {msMetadata.flagging_stats && (
                    <Box sx={{ mb: 0.5 }}>
                      <strong>Flagging:</strong> {(msMetadata.flagging_stats.total_fraction * 100).toFixed(1)}% flagged
                      {msMetadata.flagging_stats.per_antenna && Object.keys(msMetadata.flagging_stats.per_antenna).length > 0 && (
                        <Accordion sx={{ mt: 1, bgcolor: '#2e2e2e' }}>
                          <AccordionSummary expandIcon={<ExpandMore sx={{ color: '#fff' }} />}>
                            <Typography variant="caption" sx={{ color: '#aaa' }}>
                              Per-antenna flagging breakdown
                            </Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                              {msMetadata.antennas && Object.entries(msMetadata.flagging_stats.per_antenna || {}).map(([antId, frac]) => {
                                const ant = msMetadata.antennas?.find(a => String(a.antenna_id) === antId);
                                const flagPercent = (frac as number * 100).toFixed(1);
                                const color = (frac as number) > 0.5 ? '#f44336' : (frac as number) > 0.2 ? '#ff9800' : '#4caf50';
                                return (
                                  <Box key={antId} sx={{ mb: 0.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.7rem' }}>
                                      {ant ? `${ant.name} (${antId})` : `Antenna ${antId}`}
                                    </Typography>
                                    <Chip 
                                      label={`${flagPercent}%`}
                                      size="small"
                                      sx={{ 
                                        height: 16, 
                                        fontSize: '0.6rem',
                                        bgcolor: color,
                                        color: '#fff'
                                      }}
                                    />
                                  </Box>
                                );
                              })}
                            </Box>
                          </AccordionDetails>
                        </Accordion>
                      )}
                      {msMetadata.flagging_stats.per_field && Object.keys(msMetadata.flagging_stats.per_field).length > 0 && (
                        <Accordion sx={{ mt: 1, bgcolor: '#2e2e2e' }}>
                          <AccordionSummary expandIcon={<ExpandMore sx={{ color: '#fff' }} />}>
                            <Typography variant="caption" sx={{ color: '#aaa' }}>
                              Per-field flagging breakdown
                            </Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <Box sx={{ maxHeight: 200, overflow: 'auto' }}>
                              {msMetadata.fields && Object.entries(msMetadata.flagging_stats.per_field || {}).map(([fieldId, frac]) => {
                                const field = msMetadata.fields?.find(f => String(f.field_id) === fieldId);
                                const flagPercent = (frac as number * 100).toFixed(1);
                                const color = (frac as number) > 0.5 ? '#f44336' : (frac as number) > 0.2 ? '#ff9800' : '#4caf50';
                                return (
                                  <Box key={fieldId} sx={{ mb: 0.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="caption" sx={{ color: '#fff', fontSize: '0.7rem' }}>
                                      {field ? `${field.name} (Field ${fieldId})` : `Field ${fieldId}`}
                                    </Typography>
                                    <Chip 
                                      label={`${flagPercent}%`}
                                      size="small"
                                      sx={{ 
                                        height: 16, 
                                        fontSize: '0.6rem',
                                        bgcolor: color,
                                        color: '#fff'
                                      }}
                                    />
                                  </Box>
                                );
                              })}
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
                    <strong>Columns:</strong> {msMetadata.data_columns.join(', ')}
                  </Box>
                  <Box>
                    <strong>Calibrated:</strong> 
                    <Chip 
                      label={msMetadata.calibrated ? 'YES' : 'NO'} 
                      color={msMetadata.calibrated ? 'success' : 'default'}
                      size="small"
                      sx={{ ml: 1, height: 20, fontSize: '0.7rem' }}
                    />
                  </Box>
                </Box>
              </Box>
            )}
            
            {/* Calibrator Match Display */}
            {selectedMS && selectedMSList.length === 1 && (
              <>
                {calMatchesLoading && (
                  <Box sx={{ mt: 2, p: 2, bgcolor: '#1e1e1e', borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ color: '#888' }}>
                      Searching for calibrators...
                    </Typography>
                  </Box>
                )}
                {(calMatchesError || (!calMatchesLoading && (!calMatches || calMatches.matches.length === 0))) && (
                  <Box sx={{ mt: 2, p: 1.5, bgcolor: '#3e2723', borderRadius: 1, border: '1px solid #d32f2f' }}>
                    <Typography variant="caption" sx={{ color: '#ffccbc' }}>
                      {'\u2717'} No calibrators detected
                      {(() => {
                        const msEntry = msList?.items.find(ms => ms.path === selectedMS);
                        if (msEntry?.has_calibrator) {
                          return ' (but MS list indicates calibrator exists - API call may have failed)';
                        }
                        return ' (pointing may not contain suitable source)';
                      })()}
                    </Typography>
                  </Box>
                )}
                {!calMatchesLoading && !calMatchesError && calMatches && calMatches.matches.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    {(() => {
                      const best = calMatches.matches[0];
                      const qualityColor = {
                        excellent: '#4caf50',
                        good: '#8bc34a',
                        marginal: '#ff9800',
                        poor: '#f44336'
                      }[best.quality] || '#888';
                      
                      return (
                        <>
                          <Box sx={{ p: 1.5, bgcolor: '#1e3a1e', borderRadius: 1, border: `2px solid ${qualityColor}` }}>
                            <Typography variant="subtitle2" sx={{ color: '#ffffff', mb: 1, fontWeight: 'bold' }}>
                              {'\u2713'} Best Calibrator: {best.name}
                            </Typography>
                            <Box sx={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#ffffff' }}>
                              <Box sx={{ mb: 0.5 }}>
                                <strong>Flux:</strong> {best.flux_jy.toFixed(2)} Jy | <strong>PB:</strong> {best.pb_response.toFixed(3)} | 
                                <Chip 
                                  label={best.quality.toUpperCase()} 
                                  size="small"
                                  sx={{ 
                                    ml: 1, 
                                    height: 18, 
                                    fontSize: '0.65rem', 
                                    bgcolor: qualityColor,
                                    color: '#fff',
                                    fontWeight: 'bold'
                                  }}
                                />
                              </Box>
                              <Box sx={{ mb: 0.5 }}>
                                <strong>Position:</strong> RA {best.ra_deg.toFixed(4)}° | Dec {best.dec_deg.toFixed(4)}°
                              </Box>
                              <Box>
                                <strong>Separation:</strong> {best.sep_deg.toFixed(3)}° from meridian
                              </Box>
                            </Box>
                          </Box>
                          
                          {calMatches.matches.length > 1 && (
                            <Accordion sx={{ mt: 1, bgcolor: '#2e2e2e' }}>
                              <AccordionSummary expandIcon={<ExpandMore sx={{ color: '#fff' }} />}>
                                <Typography variant="caption" sx={{ color: '#aaa' }}>
                                  Show {calMatches.matches.length - 1} more calibrator{calMatches.matches.length > 2 ? 's' : ''}
                                </Typography>
                              </AccordionSummary>
                              <AccordionDetails>
                                {calMatches.matches.slice(1).map((m, i) => (
                                  <Box key={i} sx={{ mb: 1, p: 1, bgcolor: '#1e1e1e', borderRadius: 1, fontSize: '0.7rem', color: '#ccc' }}>
                                    <strong>{m.name}</strong> - {m.flux_jy.toFixed(2)} Jy (PB: {m.pb_response.toFixed(3)}, {m.quality})
                                  </Box>
                                ))}
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
          
          {/* Workflow Banner */}
          <Paper sx={{ 
            p: 2, 
            mb: 2, 
            background: 'linear-gradient(135deg, #1565c0 0%, #0d47a1 100%)', 
            color: 'white',
            border: '2px solid #1976d2',
          }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
              Quick Pipeline Workflow
            </Typography>
            <Typography variant="body2" sx={{ mb: 2, opacity: 0.9 }}>
              Convert → Calibrate → Image in one click
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center">
              <TextField
                label="Start Time"
                value={workflowParams.start_time}
                onChange={(e) => setWorkflowParams({...workflowParams, start_time: e.target.value})}
                size="small"
                placeholder="YYYY-MM-DD HH:MM:SS"
                sx={{ 
                  bgcolor: 'white', 
                  borderRadius: 1,
                  '& .MuiInputBase-root': { color: '#000' },
                  '& .MuiInputLabel-root': { color: '#666' },
                }}
              />
              <TextField
                label="End Time"
                value={workflowParams.end_time}
                onChange={(e) => setWorkflowParams({...workflowParams, end_time: e.target.value})}
                size="small"
                placeholder="YYYY-MM-DD HH:MM:SS"
                sx={{ 
                  bgcolor: 'white', 
                  borderRadius: 1,
                  '& .MuiInputBase-root': { color: '#000' },
                  '& .MuiInputLabel-root': { color: '#666' },
                }}
              />
              <Tooltip
                title={
                  !workflowParams.start_time || !workflowParams.end_time
                    ? 'Enter start and end times to run the full pipeline'
                    : workflowMutation.isPending
                    ? 'Pipeline workflow in progress...'
                    : 'Run full pipeline workflow (Ctrl/Cmd + Enter)'
                }
              >
                <span>
                  <Button
                    variant="contained"
                    startIcon={workflowMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                    onClick={handleWorkflowSubmit}
                    disabled={!workflowParams.start_time || !workflowParams.end_time || workflowMutation.isPending}
                    sx={{ 
                      bgcolor: '#fff', 
                      color: '#1565c0',
                      '&:hover': { bgcolor: '#f5f5f5' },
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {workflowMutation.isPending ? 'Running...' : 'Run Full Pipeline'}
                  </Button>
                </span>
              </Tooltip>
            </Stack>
          </Paper>
          
          <Paper sx={{ p: 2 }}>
            <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)}>
              <Tab label="Convert" />
              <Tab label="Calibrate" />
              <Tab label="Apply" />
              <Tab label="Image" />
            </Tabs>
            
            {/* Convert Tab */}
            {activeTab === 0 && (
              <Box sx={{ mt: 2 }}>
                {selectedMS && msMetadata && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      An MS is currently selected: <strong>{selectedMS.split('/').pop()}</strong>
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      Switch to the <strong>Calibrate</strong> tab to use this MS for calibration.
                    </Typography>
                    {msMetadata.start_time && msMetadata.end_time && (
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => {
                          setConvertParams({
                            ...convertParams,
                            start_time: msMetadata.start_time || '',
                            end_time: msMetadata.end_time || '',
                          });
                        }}
                        sx={{ mt: 1 }}
                      >
                        Use this MS's time range for conversion
                      </Button>
                    )}
                  </Alert>
                )}
                <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                  Convert UVH5 files to Measurement Set format:
                </Typography>
                
                <Typography variant="subtitle2" gutterBottom>
                  Time Range
                </Typography>
                <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                  <TextField
                    fullWidth
                    label="Start Time"
                    value={convertParams.start_time}
                    onChange={(e) => setConvertParams({ ...convertParams, start_time: e.target.value })}
                    size="small"
                    placeholder="YYYY-MM-DD HH:MM:SS"
                  />
                  <TextField
                    fullWidth
                    label="End Time"
                    value={convertParams.end_time}
                    onChange={(e) => setConvertParams({ ...convertParams, end_time: e.target.value })}
                    size="small"
                    placeholder="YYYY-MM-DD HH:MM:SS"
                  />
                </Stack>
                
                <Typography variant="subtitle2" gutterBottom>
                  Directories
                </Typography>
                <TextField
                  fullWidth
                  label="Input Directory"
                  value={convertParams.input_dir}
                  onChange={(e) => setConvertParams({ ...convertParams, input_dir: e.target.value })}
                  sx={{ mb: 2 }}
                  size="small"
                />
                <TextField
                  fullWidth
                  label="Output Directory"
                  value={convertParams.output_dir}
                  onChange={(e) => setConvertParams({ ...convertParams, output_dir: e.target.value })}
                  sx={{ mb: 2 }}
                  size="small"
                />
                
                <FormControl fullWidth sx={{ mb: 2 }} size="small">
                  <InputLabel>Writer Type</InputLabel>
                  <Select
                    value={convertParams.writer}
                    onChange={(e) => setConvertParams({ ...convertParams, writer: e.target.value })}
                    label="Writer Type"
                  >
                    <MenuItem value="auto">Auto (recommended)</MenuItem>
                    <MenuItem value="sequential">Sequential</MenuItem>
                    <MenuItem value="parallel">Parallel</MenuItem>
                    <MenuItem value="dask">Dask</MenuItem>
                  </Select>
                </FormControl>
                
                <FormControlLabel
                  control={
                    <Checkbox 
                      checked={convertParams.stage_to_tmpfs} 
                      onChange={(e) => setConvertParams({...convertParams, stage_to_tmpfs: e.target.checked})}
                    />
                  }
                  label="Stage to tmpfs (faster but uses RAM)"
                  sx={{ mb: 2 }}
                />
                
                <TextField
                  fullWidth
                  label="Max Workers"
                  type="number"
                  value={convertParams.max_workers}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (!isNaN(val) && val >= 1 && val <= 16) {
                      setConvertParams({ ...convertParams, max_workers: val });
                    }
                  }}
                  sx={{ mb: 2 }}
                  size="small"
                  inputProps={{ min: 1, max: 16 }}
                />
                
                {/* UVH5 File List */}
                {uvh5Files && uvh5Files.items.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Available UVH5 Files ({uvh5Files.items.length})
                    </Typography>
                    <Box sx={{ 
                      maxHeight: 200, 
                      overflow: 'auto', 
                      bgcolor: '#1e1e1e', 
                      p: 1, 
                      borderRadius: 1,
                      fontFamily: 'monospace',
                      fontSize: '0.7rem'
                    }}>
                      {uvh5Files.items.map((file) => (
                        <Box key={file.path} sx={{ color: '#ffffff', mb: 0.3 }}>
                          {file.path.split('/').pop()} ({file.size_mb?.toFixed(1)} MB)
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}
                
                <Tooltip
                  title={
                    !convertParams.start_time || !convertParams.end_time
                      ? 'Enter start and end times to run conversion'
                      : convertMutation.isPending
                      ? 'Conversion job in progress...'
                      : 'Run conversion (Ctrl/Cmd + Enter)'
                  }
                >
                  <span>
                    <Button
                      variant="contained"
                      startIcon={convertMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                      onClick={handleConvertSubmit}
                      disabled={!convertParams.start_time || !convertParams.end_time || convertMutation.isPending}
                      fullWidth
                    >
                      {convertMutation.isPending ? 'Running...' : 'Run Conversion'}
                    </Button>
                  </span>
                </Tooltip>
              </Box>
            )}
            
            {/* Calibrate Tab */}
            {activeTab === 1 && (
              <Box sx={{ mt: 2 }}>
                {!selectedMS && (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    Please select an MS from the table above to calibrate.
                  </Alert>
                )}
                {selectedMS && selectedMSList.length > 1 && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                      Multiple MSs selected ({selectedMSList.length})
                    </Typography>
                    <Typography variant="body2">
                      Only one MS can be calibrated at a time. Please deselect other MSs, keeping only one selected.
                    </Typography>
                  </Alert>
                )}
                {selectedMS && selectedMSList.length === 1 && (
                  <Alert severity="success" sx={{ mb: 2 }}>
                    <Typography variant="body2">
                      Selected MS: <strong>{selectedMS.split('/').pop()}</strong>
                    </Typography>
                    {msMetadata && msMetadata.start_time && (
                      <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                        Time range: {msMetadata.start_time} → {msMetadata.end_time}
                      </Typography>
                    )}
                  </Alert>
                )}
                <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                  Generates calibration tables from a calibrator observation:
                </Typography>
                
                <Typography variant="subtitle2" gutterBottom>
                  Calibration Tables to Generate
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <FormControlLabel
                    control={
                      <Checkbox 
                        checked={calibParams.solve_delay} 
                        onChange={(e) => setCalibParams({...calibParams, solve_delay: e.target.checked})}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">K (Delay calibration)</Typography>
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          Antenna-based delays
                        </Typography>
                      </Box>
                    }
                  />
                  <FormControlLabel
                    control={
                      <Checkbox 
                        checked={calibParams.solve_bandpass} 
                        onChange={(e) => setCalibParams({...calibParams, solve_bandpass: e.target.checked})}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">BP (Bandpass calibration)</Typography>
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          Frequency response per antenna
                        </Typography>
                      </Box>
                    }
                  />
                  <FormControlLabel
                    control={
                      <Checkbox 
                        checked={calibParams.solve_gains} 
                        onChange={(e) => setCalibParams({...calibParams, solve_gains: e.target.checked})}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">G (Gain calibration)</Typography>
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          Time-variable complex gains
                        </Typography>
                      </Box>
                    }
                  />
                </Box>
                
                <Typography variant="subtitle2" gutterBottom>
                  Basic Parameters
                </Typography>
                <TextField
                  fullWidth
                  label="Field ID"
                  value={calibParams.field || ''}
                  onChange={(e) => setCalibParams({ ...calibParams, field: e.target.value })}
                  sx={{ mb: 2 }}
                  size="small"
                  helperText="Leave empty for auto-detect from catalog"
                />
                {selectedMS && (
                  <>
                    {!msMetadata || !msMetadata.antennas || msMetadata.antennas.length === 0 ? (
                <TextField
                  fullWidth
                  label="Reference Antenna"
                  value={calibParams.refant || ''}
                  onChange={(e) => setCalibParams({ ...calibParams, refant: e.target.value })}
                  sx={{ mb: 2 }}
                        size="small"
                        helperText="Reference antenna ID (e.g., 103)"
                      />
                    ) : (
                      (() => {
                        const refantValid = !calibParams.refant || 
                          msMetadata.antennas.some(a => 
                            String(a.antenna_id) === calibParams.refant || a.name === calibParams.refant
                          );
                        
                        return (
                          <FormControl fullWidth sx={{ mb: 2 }} size="small">
                            <InputLabel>Reference Antenna</InputLabel>
                            <Select
                              value={calibParams.refant || ''}
                              onChange={(e) => setCalibParams({ ...calibParams, refant: e.target.value })}
                              label="Reference Antenna"
                              error={!refantValid}
                            >
                              {msMetadata.antennas.map((ant) => (
                                <MenuItem key={ant.antenna_id} value={String(ant.antenna_id)}>
                                  {ant.name} ({ant.antenna_id})
                                </MenuItem>
                              ))}
                            </Select>
                            {!refantValid && calibParams.refant && (
                              <Typography variant="caption" sx={{ color: 'error.main', mt: 0.5, display: 'block' }}>
                                Warning: Antenna "{calibParams.refant}" not found in MS
                              </Typography>
                            )}
                            {refantValid && (
                              <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5, display: 'block' }}>
                                Select reference antenna from {msMetadata.antennas.length} available antennas
                              </Typography>
                            )}
                          </FormControl>
                        );
                      })()
                    )}
                  </>
                )}
                
                <Divider sx={{ my: 2 }} />
                
                {/* Existing Tables Section */}
                <Typography variant="subtitle2" gutterBottom>
                  Existing Calibration Tables
                </Typography>
                
                {selectedMS && !existingTables && (
                  <Box sx={{ mb: 2, p: 1.5, bgcolor: '#2e2e2e', borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ color: '#888' }}>
                      Loading existing tables...
                    </Typography>
                  </Box>
                )}
                {selectedMS && existingTables && (!existingTables.has_k && !existingTables.has_bp && !existingTables.has_g) && (
                  <Box sx={{ mb: 2, p: 1.5, bgcolor: '#2e2e2e', borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ color: '#888' }}>
                      No existing calibration tables found for this MS
                    </Typography>
                  </Box>
                )}
                {selectedMS && existingTables && (existingTables.has_k || existingTables.has_bp || existingTables.has_g) && (
                  <Box sx={{ mb: 2 }}>
                    <RadioGroup
                      value={calibParams.use_existing_tables || 'auto'}
                      onChange={(e) => setCalibParams({
                        ...calibParams, 
                        use_existing_tables: e.target.value as 'auto' | 'manual' | 'none'
                      })}
                    >
                      <FormControlLabel value="auto" control={<Radio size="small" />} label="Auto-select (use latest)" />
                      <FormControlLabel value="manual" control={<Radio size="small" />} label="Manual select" />
                      <FormControlLabel value="none" control={<Radio size="small" />} label="Don't use existing tables" />
                    </RadioGroup>
                    
                    {calibParams.use_existing_tables === 'auto' && (
                      <Box sx={{ mt: 1, p: 1.5, bgcolor: '#1e3a1e', borderRadius: 1 }}>
                        <Typography variant="caption" sx={{ color: '#4caf50', fontWeight: 'bold', display: 'block', mb: 1 }}>
                          Found existing tables (will use latest if needed):
                        </Typography>
                        <Box sx={{ fontSize: '0.7rem', fontFamily: 'monospace', color: '#ffffff' }}>
                          {existingTables.has_k && existingTables.k_tables.length > 0 && (
                            <Box sx={{ mb: 0.5 }}>
                              {'\u2713'} K: {existingTables.k_tables[0].filename} 
                              ({existingTables.k_tables[0].age_hours.toFixed(1)}h ago)
                            </Box>
                          )}
                          {existingTables.has_bp && existingTables.bp_tables.length > 0 && (
                            <Box sx={{ mb: 0.5 }}>
                              {'\u2713'} BP: {existingTables.bp_tables[0].filename} 
                              ({existingTables.bp_tables[0].age_hours.toFixed(1)}h ago)
                            </Box>
                          )}
                          {existingTables.has_g && existingTables.g_tables.length > 0 && (
                            <Box sx={{ mb: 0.5 }}>
                              {'\u2713'} G: {existingTables.g_tables[0].filename} 
                              ({existingTables.g_tables[0].age_hours.toFixed(1)}h ago)
                            </Box>
                          )}
                        </Box>
                      </Box>
                    )}
                    
                    {calibParams.use_existing_tables === 'manual' && (
                        <Box sx={{ mt: 1 }}>
                          {existingTables.k_tables.length > 0 && (
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="caption" sx={{ fontWeight: 'bold' }}>K (Delay) Tables:</Typography>
                              <RadioGroup
                                value={calibParams.existing_k_table || 'none'}
                                onChange={(e) => {
                                  const newValue = e.target.value === 'none' ? undefined : e.target.value;
                                  setCalibParams({...calibParams, existing_k_table: newValue});
                                  
                                  // Validate compatibility when a table is selected
                                  if (newValue && selectedMS) {
                                    validateCalTable.mutate(
                                      { msPath: selectedMS, caltablePath: newValue },
                                      {
                                        onSuccess: (result) => {
                                          setCompatibilityChecks(prev => ({
                                            ...prev,
                                            [newValue]: result
                                          }));
                                        }
                                      }
                                    );
                                  }
                                }}
                              >
                                {existingTables.k_tables.map((table) => {
                                  const compat = compatibilityChecks[table.path];
                                  const isSelected = calibParams.existing_k_table === table.path;
                                  
                                  return (
                                    <Box key={table.path}>
                                      <FormControlLabel
                                        value={table.path}
                                        control={<Radio size="small" />}
                                        label={
                                          <Box>
                                            <Typography variant="caption">
                                              {table.filename} ({table.size_mb.toFixed(1)} MB, {table.age_hours.toFixed(1)}h ago)
                                            </Typography>
                                            {isSelected && compat && (
                                              <Box sx={{ mt: 0.5 }}>
                                                {compat.is_compatible ? (
                                                  <Chip 
                                                    label="✓ Compatible" 
                                                    size="small" 
                                                    color="success"
                                                    sx={{ height: 16, fontSize: '0.6rem' }}
                                                  />
                                                ) : (
                                                  <Chip 
                                                    label="✗ Incompatible" 
                                                    size="small" 
                                                    color="error"
                                                    sx={{ height: 16, fontSize: '0.6rem' }}
                                                  />
                                                )}
                                              </Box>
                                            )}
                                          </Box>
                                        }
                                      />
                                      {isSelected && compat && (
                                        <Box sx={{ ml: 4, mb: 1 }}>
                                          {compat.issues.length > 0 && (
                                            <Box sx={{ mt: 0.5 }}>
                                              {compat.issues.map((issue: string, idx: number) => (
                                                <Typography key={idx} variant="caption" sx={{ color: 'error.main', display: 'block', fontSize: '0.65rem' }}>
                                                  ⚠ {issue}
                                                </Typography>
                                              ))}
                                            </Box>
                                          )}
                                          {compat.warnings.length > 0 && (
                                            <Box sx={{ mt: 0.5 }}>
                                              {compat.warnings.map((warning: string, idx: number) => (
                                                <Typography key={idx} variant="caption" sx={{ color: 'warning.main', display: 'block', fontSize: '0.65rem' }}>
                                                  ⚠ {warning}
                                                </Typography>
                                              ))}
                                            </Box>
                                          )}
                                          {compat.is_compatible && compat.issues.length === 0 && compat.warnings.length === 0 && (
                                            <Typography variant="caption" sx={{ color: 'success.main', display: 'block', fontSize: '0.65rem' }}>
                                              ✓ All compatibility checks passed
                                            </Typography>
                                          )}
                                        </Box>
                                      )}
                                    </Box>
                                  );
                                })}
                                <FormControlLabel value="none" control={<Radio size="small" />} label={<Typography variant="caption">None</Typography>} />
                              </RadioGroup>
                            </Box>
                          )}
                          
                          {existingTables.bp_tables.length > 0 && (
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="caption" sx={{ fontWeight: 'bold' }}>BP (Bandpass) Tables:</Typography>
                              <RadioGroup
                                value={calibParams.existing_bp_table || 'none'}
                                onChange={(e) => {
                                  const newValue = e.target.value === 'none' ? undefined : e.target.value;
                                  setCalibParams({...calibParams, existing_bp_table: newValue});
                                  
                                  // Validate compatibility when a table is selected
                                  if (newValue && selectedMS) {
                                    validateCalTable.mutate(
                                      { msPath: selectedMS, caltablePath: newValue },
                                      {
                                        onSuccess: (result) => {
                                          setCompatibilityChecks(prev => ({
                                            ...prev,
                                            [newValue]: result
                                          }));
                                        }
                                      }
                                    );
                                  }
                                }}
                              >
                                {existingTables.bp_tables.map((table) => {
                                  const compat = compatibilityChecks[table.path];
                                  const isSelected = calibParams.existing_bp_table === table.path;
                                  
                                  return (
                                    <Box key={table.path}>
                                      <FormControlLabel
                                        value={table.path}
                                        control={<Radio size="small" />}
                                        label={
                                          <Box>
                                            <Typography variant="caption">
                                              {table.filename} ({table.size_mb.toFixed(1)} MB, {table.age_hours.toFixed(1)}h ago)
                                            </Typography>
                                            {isSelected && compat && (
                                              <Box sx={{ mt: 0.5 }}>
                                                {compat.is_compatible ? (
                                                  <Chip 
                                                    label="✓ Compatible" 
                                                    size="small" 
                                                    color="success"
                                                    sx={{ height: 16, fontSize: '0.6rem' }}
                                                  />
                                                ) : (
                                                  <Chip 
                                                    label="✗ Incompatible" 
                                                    size="small" 
                                                    color="error"
                                                    sx={{ height: 16, fontSize: '0.6rem' }}
                                                  />
                                                )}
                                              </Box>
                                            )}
                                          </Box>
                                        }
                                      />
                                      {isSelected && compat && (
                                        <Box sx={{ ml: 4, mb: 1 }}>
                                          {compat.issues.length > 0 && (
                                            <Box sx={{ mt: 0.5 }}>
                                              {compat.issues.map((issue: string, idx: number) => (
                                                <Typography key={idx} variant="caption" sx={{ color: 'error.main', display: 'block', fontSize: '0.65rem' }}>
                                                  ⚠ {issue}
                                                </Typography>
                                              ))}
                                            </Box>
                                          )}
                                          {compat.warnings.length > 0 && (
                                            <Box sx={{ mt: 0.5 }}>
                                              {compat.warnings.map((warning: string, idx: number) => (
                                                <Typography key={idx} variant="caption" sx={{ color: 'warning.main', display: 'block', fontSize: '0.65rem' }}>
                                                  ⚠ {warning}
                                                </Typography>
                                              ))}
                                            </Box>
                                          )}
                                          {compat.is_compatible && compat.issues.length === 0 && compat.warnings.length === 0 && (
                                            <Typography variant="caption" sx={{ color: 'success.main', display: 'block', fontSize: '0.65rem' }}>
                                              ✓ All compatibility checks passed
                                            </Typography>
                                          )}
                                        </Box>
                                      )}
                                    </Box>
                                  );
                                })}
                                <FormControlLabel value="none" control={<Radio size="small" />} label={<Typography variant="caption">None</Typography>} />
                              </RadioGroup>
                            </Box>
                          )}
                          
                          {existingTables.g_tables.length > 0 && (
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="caption" sx={{ fontWeight: 'bold' }}>G (Gain) Tables:</Typography>
                              <RadioGroup
                                value={calibParams.existing_g_table || 'none'}
                                onChange={(e) => {
                                  const newValue = e.target.value === 'none' ? undefined : e.target.value;
                                  setCalibParams({...calibParams, existing_g_table: newValue});
                                  
                                  // Validate compatibility when a table is selected
                                  if (newValue && selectedMS) {
                                    validateCalTable.mutate(
                                      { msPath: selectedMS, caltablePath: newValue },
                                      {
                                        onSuccess: (result) => {
                                          setCompatibilityChecks(prev => ({
                                            ...prev,
                                            [newValue]: result
                                          }));
                                        }
                                      }
                                    );
                                  }
                                }}
                              >
                                {existingTables.g_tables.map((table) => {
                                  const compat = compatibilityChecks[table.path];
                                  const isSelected = calibParams.existing_g_table === table.path;
                                  
                                  return (
                                    <Box key={table.path}>
                                      <FormControlLabel
                                        value={table.path}
                                        control={<Radio size="small" />}
                                        label={
                                          <Box>
                                            <Typography variant="caption">
                                              {table.filename} ({table.size_mb.toFixed(1)} MB, {table.age_hours.toFixed(1)}h ago)
                                            </Typography>
                                            {isSelected && compat && (
                                              <Box sx={{ mt: 0.5 }}>
                                                {compat.is_compatible ? (
                                                  <Chip 
                                                    label="✓ Compatible" 
                                                    size="small" 
                                                    color="success"
                                                    sx={{ height: 16, fontSize: '0.6rem' }}
                                                  />
                                                ) : (
                                                  <Chip 
                                                    label="✗ Incompatible" 
                                                    size="small" 
                                                    color="error"
                                                    sx={{ height: 16, fontSize: '0.6rem' }}
                                                  />
                                                )}
                                              </Box>
                                            )}
                                          </Box>
                                        }
                                      />
                                      {isSelected && compat && (
                                        <Box sx={{ ml: 4, mb: 1 }}>
                                          {compat.issues.length > 0 && (
                                            <Box sx={{ mt: 0.5 }}>
                                              {compat.issues.map((issue: string, idx: number) => (
                                                <Typography key={idx} variant="caption" sx={{ color: 'error.main', display: 'block', fontSize: '0.65rem' }}>
                                                  ⚠ {issue}
                                                </Typography>
                                              ))}
                                            </Box>
                                          )}
                                          {compat.warnings.length > 0 && (
                                            <Box sx={{ mt: 0.5 }}>
                                              {compat.warnings.map((warning: string, idx: number) => (
                                                <Typography key={idx} variant="caption" sx={{ color: 'warning.main', display: 'block', fontSize: '0.65rem' }}>
                                                  ⚠ {warning}
                                                </Typography>
                                              ))}
                                            </Box>
                                          )}
                                          {compat.is_compatible && compat.issues.length === 0 && compat.warnings.length === 0 && (
                                            <Typography variant="caption" sx={{ color: 'success.main', display: 'block', fontSize: '0.65rem' }}>
                                              ✓ All compatibility checks passed
                                            </Typography>
                                          )}
                                        </Box>
                                      )}
                                    </Box>
                                  );
                                })}
                                <FormControlLabel value="none" control={<Radio size="small" />} label={<Typography variant="caption">None</Typography>} />
                              </RadioGroup>
                            </Box>
                          )}
                        </Box>
                      )}
                    </Box>
                  )}
                
                <Divider sx={{ my: 2 }} />
                
                <Accordion sx={{ mb: 2 }}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography variant="subtitle2">Advanced Options</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <TextField
                      fullWidth
                      label="Gain Solution Interval"
                      value={calibParams.gain_solint || 'inf'}
                      onChange={(e) => setCalibParams({ ...calibParams, gain_solint: e.target.value })}
                      sx={{ mb: 2 }}
                      size="small"
                      helperText="e.g., 'inf', '60s', '10min'"
                    />
                    <FormControl fullWidth sx={{ mb: 2 }} size="small">
                      <InputLabel>Gain Cal Mode</InputLabel>
                      <Select
                        value={calibParams.gain_calmode || 'ap'}
                        onChange={(e) => setCalibParams({ ...calibParams, gain_calmode: e.target.value as 'ap' | 'p' | 'a' })}
                        label="Gain Cal Mode"
                      >
                        <MenuItem value="ap">Amp + Phase</MenuItem>
                        <MenuItem value="p">Phase only</MenuItem>
                        <MenuItem value="a">Amp only</MenuItem>
                      </Select>
                    </FormControl>
                    <TextField
                      fullWidth
                      label="Minimum PB Response"
                      type="number"
                      value={calibParams.min_pb || 0.5}
                      onChange={(e) => {
                        const val = parseFloat(e.target.value);
                        if (!isNaN(val) && val >= 0 && val <= 1) {
                          setCalibParams({ ...calibParams, min_pb: val });
                        }
                      }}
                      sx={{ mb: 2 }}
                      size="small"
                      helperText="0.0 - 1.0 (higher = stricter field selection)"
                      inputProps={{ min: 0, max: 1, step: 0.1 }}
                    />
                    <FormControlLabel
                      control={
                        <Checkbox 
                          checked={calibParams.do_flagging || false} 
                          onChange={(e) => setCalibParams({...calibParams, do_flagging: e.target.checked})}
                        />
                      }
                      label="Enable pre-calibration flagging"
                    />
                  </AccordionDetails>
                </Accordion>
                
                <Tooltip
                  title={
                    !selectedMS
                      ? 'Select a measurement set first'
                      : selectedMSList.length !== 1
                      ? 'Select exactly one measurement set'
                      : (!calibParams.solve_delay && !calibParams.solve_bandpass && !calibParams.solve_gains)
                      ? 'Select at least one calibration table type (K, BP, or G)'
                      : calibrateMutation.isPending
                      ? 'Calibration job in progress...'
                      : 'Run calibration (Ctrl/Cmd + Enter)'
                  }
                >
                  <span>
                    <Button
                      variant="contained"
                      startIcon={calibrateMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                      onClick={handleCalibrateSubmit}
                      disabled={!selectedMS || selectedMSList.length !== 1 || calibrateMutation.isPending || (!calibParams.solve_delay && !calibParams.solve_bandpass && !calibParams.solve_gains)}
                      fullWidth
                    >
                      {calibrateMutation.isPending ? 'Running...' : 'Run Calibration'}
                    </Button>
                  </span>
                </Tooltip>
                {(!calibParams.solve_delay && !calibParams.solve_bandpass && !calibParams.solve_gains) && (
                  <Typography variant="caption" sx={{ color: 'error.main', mt: 1, display: 'block' }}>
                    Select at least one calibration table type
                  </Typography>
                )}
              </Box>
            )}
            
            {/* Apply Tab */}
            {activeTab === 2 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                  Apply existing calibration tables to the selected MS:
                </Typography>
                <Box sx={{ 
                  mb: 2, 
                  p: 1.5, 
                  bgcolor: '#1e1e1e', 
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  fontSize: '0.75rem',
                  color: '#ffffff'
                }}>
                  <Box>Clears existing calibration, then applies K, BP, and G tables to CORRECTED_DATA column</Box>
                </Box>
                
                <Typography variant="subtitle2" gutterBottom>
                  Calibration Tables
                </Typography>
                <TextField
                  fullWidth
                  label="Gaintables (comma-separated paths)"
                  value={applyParams.gaintables?.join(',') || ''}
                  onChange={(e) =>
                    setApplyParams({
                      ...applyParams,
                      gaintables: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  multiline
                  rows={3}
                  sx={{ mb: 2 }}
                  size="small"
                  helperText="Enter full paths to .kcal, .bpcal, .gpcal tables"
                />
                
                {/* Cal Table Browser */}
                {calTables && calTables.items.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Available Calibration Tables (click to add)
                    </Typography>
                    <Box sx={{ maxHeight: 200, overflow: 'auto', border: '1px solid #444', borderRadius: 1, p: 1 }}>
                      {calTables.items.map((table) => (
                        <Box
                          key={table.path}
                          onClick={() => {
                            const current = applyParams.gaintables || [];
                            if (!current.includes(table.path)) {
                              setApplyParams({
                                ...applyParams,
                                gaintables: [...current, table.path],
                              });
                            }
                          }}
                          sx={{
                            p: 0.5,
                            mb: 0.5,
                            bgcolor: '#2e2e2e',
                            borderRadius: 1,
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            fontFamily: 'monospace',
                            '&:hover': { bgcolor: '#3e3e3e' },
                          }}
                        >
                          <Chip label={table.table_type} size="small" sx={{ mr: 1, height: 18, fontSize: '0.65rem' }} />
                          {table.filename} ({table.size_mb.toFixed(1)} MB)
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}
                
                <Tooltip
                  title={
                    !selectedMS
                      ? 'Select a measurement set first'
                      : !applyParams.gaintables?.length
                      ? 'Enter at least one calibration table path'
                      : applyMutation.isPending
                      ? 'Apply calibration job in progress...'
                      : 'Apply calibration tables (Ctrl/Cmd + Enter)'
                  }
                >
                  <span>
                    <Button
                      variant="contained"
                      startIcon={applyMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                      onClick={handleApplySubmit}
                      disabled={!selectedMS || !applyParams.gaintables?.length || applyMutation.isPending}
                      fullWidth
                    >
                      {applyMutation.isPending ? 'Running...' : 'Apply Calibration'}
                    </Button>
                  </span>
                </Tooltip>
              </Box>
            )}
            
            {/* Image Tab */}
            {activeTab === 3 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
                  Image the selected MS using CASA tclean:
                </Typography>
                <Box sx={{ 
                  mb: 2, 
                  p: 1.5, 
                  bgcolor: '#1e1e1e', 
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  fontSize: '0.75rem',
                  color: '#ffffff'
                }}>
                  <Box sx={{ mb: 0.5 }}>• Auto-detects pixel size and image dimensions</Box>
                  <Box sx={{ mb: 0.5 }}>• Uses w-projection for wide-field imaging</Box>
                  <Box>• Outputs .image, .residual, .psf, and optionally .fits</Box>
                </Box>
                
                <Typography variant="subtitle2" gutterBottom>
                  Imaging Parameters
                </Typography>
                <FormControl fullWidth sx={{ mb: 2 }} size="small">
                  <InputLabel>Gridder</InputLabel>
                  <Select
                    value={imageParams.gridder}
                    onChange={(e) => setImageParams({ ...imageParams, gridder: e.target.value })}
                    label="Gridder"
                  >
                    <MenuItem value="wproject">W-projection (recommended)</MenuItem>
                    <MenuItem value="standard">Standard</MenuItem>
                    <MenuItem value="widefield">Widefield</MenuItem>
                  </Select>
                </FormControl>
                
                <TextField
                  fullWidth
                  label="W-projection planes"
                  type="number"
                  value={imageParams.wprojplanes}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (!isNaN(val) && val >= -1) {
                      setImageParams({ ...imageParams, wprojplanes: val });
                    }
                  }}
                  sx={{ mb: 2 }}
                  size="small"
                  helperText="-1 for auto, or specify number of planes"
                />
                
                <FormControl fullWidth sx={{ mb: 2 }} size="small">
                  <InputLabel>Data Column</InputLabel>
                  <Select
                    value={imageParams.datacolumn}
                    onChange={(e) => setImageParams({ ...imageParams, datacolumn: e.target.value })}
                    label="Data Column"
                  >
                    <MenuItem value="corrected">CORRECTED_DATA (after calibration)</MenuItem>
                    <MenuItem value="data">DATA (raw visibilities)</MenuItem>
                  </Select>
                </FormControl>
                
                {selectedMS && msMetadata && (
                  <>
                    {(() => {
                      const hasCorrectedData = msMetadata.data_columns.includes('CORRECTED_DATA');
                      const usingDataColumn = imageParams.datacolumn === 'data';
                      
                      if (hasCorrectedData && usingDataColumn) {
                        return (
                          <Box sx={{ mb: 2, p: 1.5, bgcolor: '#3e2723', borderRadius: 1, border: '1px solid #ff9800' }}>
                            <Typography variant="caption" sx={{ color: '#ffccbc', fontWeight: 'bold' }}>
                              Warning: CORRECTED_DATA column exists but you're imaging DATA column. 
                              Consider using CORRECTED_DATA for calibrated data.
                            </Typography>
                          </Box>
                        );
                      }
                      
                      if (!hasCorrectedData && !usingDataColumn) {
                        return (
                          <Box sx={{ mb: 2, p: 1.5, bgcolor: '#3e2723', borderRadius: 1, border: '1px solid #d32f2f' }}>
                            <Typography variant="caption" sx={{ color: '#ffccbc', fontWeight: 'bold' }}>
                              Error: CORRECTED_DATA column does not exist. Please apply calibration first or use DATA column.
                            </Typography>
                          </Box>
                        );
                      }
                      
                      return null;
                    })()}
                  </>
                )}
                
                <FormControlLabel
                  control={
                    <Checkbox 
                      checked={imageParams.quick || false} 
                      onChange={(e) => setImageParams({...imageParams, quick: e.target.checked})}
                    />
                  }
                  label="Quick mode (fewer iterations)"
                  sx={{ mb: 1 }}
                />
                
                <FormControlLabel
                  control={
                    <Checkbox 
                      checked={imageParams.skip_fits !== false} 
                      onChange={(e) => setImageParams({...imageParams, skip_fits: e.target.checked})}
                    />
                  }
                  label="Skip FITS export (faster)"
                  sx={{ mb: 2 }}
                />
                
                <Tooltip
                  title={
                    !selectedMS
                      ? 'Select a measurement set first'
                      : imageMutation.isPending
                      ? 'Imaging job in progress...'
                      : 'Create image (Ctrl/Cmd + Enter)'
                  }
                >
                  <span>
                    <Button
                      variant="contained"
                      startIcon={imageMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <PlayArrow />}
                      onClick={handleImageSubmit}
                      disabled={!selectedMS || imageMutation.isPending}
                      fullWidth
                    >
                      {imageMutation.isPending ? 'Running...' : 'Create Image'}
                    </Button>
                  </span>
                </Tooltip>
              </Box>
            )}
          </Paper>
        </Box>
        
        {/* Right column - Job logs and status */}
        <Box sx={{ flex: 1 }}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Recent Jobs</Typography>
              <Button
                startIcon={<Refresh />}
                onClick={() => refetchJobs()}
                size="small"
              >
                Refresh
              </Button>
            </Box>
            <TableContainer sx={{ maxHeight: 300 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>MS</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {jobsList?.items.slice(0, 10).map((job) => (
                    <TableRow
                      key={job.id}
                      hover
                      onClick={() => {
                        setSelectedJobId(job.id);
                        setLogContent('');
                      }}
                      sx={{ cursor: 'pointer', bgcolor: selectedJobId === job.id ? 'action.selected' : 'inherit' }}
                    >
                      <TableCell>{job.id}</TableCell>
                      <TableCell>{job.type}</TableCell>
                      <TableCell>
                        <Chip
                          label={job.status}
                          size="small"
                          color={
                            job.status === 'done' ? 'success' :
                            job.status === 'failed' ? 'error' :
                            job.status === 'running' ? 'primary' : 'default'
                          }
                        />
                      </TableCell>
                      <TableCell sx={{ fontSize: '0.7rem', fontFamily: 'monospace' }}>
                        {job.ms_path ? job.ms_path.split('/').pop() : '-'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
          
          {/* Error Alert */}
          {errorMessage && (
            <Alert 
              severity="error" 
              onClose={() => {
                setErrorMessage(null);
                setErrorSnackbarOpen(false);
              }}
              sx={{ mb: 2 }}
            >
              {errorMessage}
            </Alert>
          )}
          
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Job Logs
              {selectedJobId !== null && ` (Job #${selectedJobId})`}
            </Typography>
            <Box
              sx={{
                height: 400,
                overflow: 'auto',
                bgcolor: '#1e1e1e',
                p: 2,
                borderRadius: 1,
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                color: '#00ff00',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {logContent || (selectedJobId === null ? 'Select a job to view logs' : 'No logs yet...')}
        </Box>
          </Paper>
        </Box>
      </Box>
      
      {/* Error Snackbar */}
      <Snackbar
        open={errorSnackbarOpen}
        autoHideDuration={6000}
        onClose={() => setErrorSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={() => setErrorSnackbarOpen(false)} 
          severity="error" 
          sx={{ width: '100%' }}
        >
          {errorMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}
