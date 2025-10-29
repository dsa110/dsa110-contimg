/**
 * Control Page - Manual job execution interface
 */
import { useState, useEffect, useRef } from 'react';
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
} from '../api/queries';
import type { JobParams, ConversionJobParams, CalibrateJobParams } from '../api/types';

export default function ControlPage() {
  const [selectedMS, setSelectedMS] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [logContent, setLogContent] = useState('');
  
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

  // SSE for job logs
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (selectedJobId !== null) {
      const url = `http://localhost:8000/api/jobs/id/${selectedJobId}/logs`;
      const eventSource = new EventSource(url);
      
      eventSource.onmessage = (event) => {
        setLogContent((prev) => prev + event.data);
      };

      eventSource.onerror = () => {
        eventSource.close();
      };

      eventSourceRef.current = eventSource;

      return () => {
        eventSource.close();
      };
    }
  }, [selectedJobId]);

  // Handlers
  const handleCalibrateSubmit = () => {
    if (!selectedMS) return;
    calibrateMutation.mutate(
      { ms_path: selectedMS, params: calibParams },
      {
        onSuccess: (job) => {
          setSelectedJobId(job.id);
          setLogContent('');
          refetchJobs();
        },
      }
    );
  };

  const handleApplySubmit = () => {
    if (!selectedMS) return;
    applyMutation.mutate(
      { ms_path: selectedMS, params: applyParams },
      {
        onSuccess: (job) => {
          setSelectedJobId(job.id);
          setLogContent('');
          refetchJobs();
        },
      }
    );
  };

  const handleImageSubmit = () => {
    if (!selectedMS) return;
    imageMutation.mutate(
      { ms_path: selectedMS, params: imageParams },
      {
        onSuccess: (job) => {
          setSelectedJobId(job.id);
          setLogContent('');
          refetchJobs();
        },
      }
    );
  };

  const handleConvertSubmit = () => {
    convertMutation.mutate(
      { params: convertParams },
      {
        onSuccess: (job) => {
          setSelectedJobId(job.id);
          setLogContent('');
          refetchJobs();
        },
      }
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Control Panel
      </Typography>
      
      <Box sx={{ display: 'flex', gap: 2 }}>
        {/* Left column - Job controls */}
        <Box sx={{ flex: 1 }}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Select Measurement Set</Typography>
              <Button
                startIcon={<Refresh />}
                onClick={() => refetchMS()}
                size="small"
              >
                Refresh
              </Button>
            </Box>
            <FormControl fullWidth>
              <InputLabel>MS File</InputLabel>
              <Select
                value={selectedMS}
                onChange={(e) => setSelectedMS(e.target.value)}
                label="MS File"
              >
                {msList?.items.map((ms) => (
                  <MenuItem key={ms.path} value={ms.path}>
                    {ms.path}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            {/* MS Metadata Panel */}
            {selectedMS && (() => {
              const { data: msMetadata } = useMSMetadata(selectedMS);
              if (!msMetadata) return null;
              
              return (
                <Box sx={{ mt: 2, p: 2, bgcolor: '#1e1e1e', borderRadius: 1 }}>
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
                    {msMetadata.num_fields !== undefined && (
                      <Box sx={{ mb: 0.5 }}>
                        <strong>Fields:</strong> {msMetadata.num_fields} {msMetadata.field_names && `(${msMetadata.field_names.join(', ')})`}
                      </Box>
                    )}
                    {msMetadata.num_antennas !== undefined && (
                      <Box sx={{ mb: 0.5 }}>
                        <strong>Antennas:</strong> {msMetadata.num_antennas}
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
              );
            })()}
            
            {/* Calibrator Match Display */}
            {selectedMS && (() => {
              const { data: calMatches, isLoading, error } = useCalibratorMatches(selectedMS);
              
              if (isLoading) {
                return (
                  <Box sx={{ mt: 2, p: 2, bgcolor: '#1e1e1e', borderRadius: 1 }}>
                    <Typography variant="caption" sx={{ color: '#888' }}>
                      Searching for calibrators...
                    </Typography>
                  </Box>
                );
              }
              
              if (error || !calMatches || calMatches.matches.length === 0) {
                return (
                  <Box sx={{ mt: 2, p: 1.5, bgcolor: '#3e2723', borderRadius: 1, border: '1px solid #d32f2f' }}>
                    <Typography variant="caption" sx={{ color: '#ffccbc' }}>
                      {'\u2717'} No calibrators detected (pointing may not contain suitable source)
                    </Typography>
                  </Box>
                );
              }
              
              const best = calMatches.matches[0];
              const qualityColor = {
                excellent: '#4caf50',
                good: '#8bc34a',
                marginal: '#ff9800',
                poor: '#f44336'
              }[best.quality] || '#888';
              
              return (
                <Box sx={{ mt: 2 }}>
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
                </Box>
              );
            })()}
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
            {(() => {
              const workflowMutation = useCreateWorkflowJob();
              const [workflowParams, setWorkflowParams] = useState({
                start_time: '',
                end_time: '',
              });
              
              return (
                <>
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
                    <Button
                      variant="contained"
                      startIcon={<PlayArrow />}
                      onClick={() => {
                        if (workflowParams.start_time && workflowParams.end_time) {
                          workflowMutation.mutate(
                            { params: workflowParams },
                            {
                              onSuccess: (job) => {
                                setSelectedJobId(job.id);
                                setLogContent('');
                                refetchJobs();
                              },
                            }
                          );
                        }
                      }}
                      disabled={!workflowParams.start_time || !workflowParams.end_time || workflowMutation.isPending}
                      sx={{ 
                        bgcolor: '#fff', 
                        color: '#1565c0',
                        '&:hover': { bgcolor: '#f5f5f5' },
                        whiteSpace: 'nowrap',
                      }}
                    >
                      Run Full Pipeline
                    </Button>
                  </Stack>
                </>
              );
            })()}
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
                  onChange={(e) => setConvertParams({ ...convertParams, max_workers: parseInt(e.target.value) })}
                  sx={{ mb: 2 }}
                  size="small"
                  inputProps={{ min: 1, max: 16 }}
                />
                
                {/* UVH5 File List */}
                {(() => {
                  const { data: uvh5Files } = useUVH5Files(convertParams.input_dir);
                  
                  if (uvh5Files && uvh5Files.items.length > 0) {
                    return (
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
                          {uvh5Files.items.map((file, idx) => (
                            <Box key={idx} sx={{ color: '#ffffff', mb: 0.3 }}>
                              {file.path.split('/').pop()} ({file.size_mb?.toFixed(1)} MB)
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    );
                  }
                  return null;
                })()}
                
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={handleConvertSubmit}
                  disabled={!convertParams.start_time || !convertParams.end_time || convertMutation.isPending}
                  fullWidth
                >
                  Run Conversion
                </Button>
              </Box>
            )}
            
            {/* Calibrate Tab */}
            {activeTab === 1 && (
              <Box sx={{ mt: 2 }}>
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
                <TextField
                  fullWidth
                  label="Reference Antenna"
                  value={calibParams.refant || ''}
                  onChange={(e) => setCalibParams({ ...calibParams, refant: e.target.value })}
                  sx={{ mb: 2 }}
                  size="small"
                  helperText="Reference antenna ID (default: 103)"
                />
                
                <Divider sx={{ my: 2 }} />
                
                {/* Existing Tables Section */}
                <Typography variant="subtitle2" gutterBottom>
                  Existing Calibration Tables
                </Typography>
                
                {selectedMS && (() => {
                  const { data: existingTables } = useExistingCalTables(selectedMS);
                  
                  if (!existingTables || (!existingTables.has_k && !existingTables.has_bp && !existingTables.has_g)) {
                    return (
                      <Box sx={{ mb: 2, p: 1.5, bgcolor: '#2e2e2e', borderRadius: 1 }}>
                        <Typography variant="caption" sx={{ color: '#888' }}>
                          No existing calibration tables found for this MS
                        </Typography>
                      </Box>
                    );
                  }
                  
                  return (
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
                            {existingTables.has_k && (
                              <Box sx={{ mb: 0.5 }}>
                                {'\u2713'} K: {existingTables.k_tables[0].filename} 
                                ({existingTables.k_tables[0].age_hours.toFixed(1)}h ago)
                              </Box>
                            )}
                            {existingTables.has_bp && (
                              <Box sx={{ mb: 0.5 }}>
                                {'\u2713'} BP: {existingTables.bp_tables[0].filename} 
                                ({existingTables.bp_tables[0].age_hours.toFixed(1)}h ago)
                              </Box>
                            )}
                            {existingTables.has_g && (
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
                                onChange={(e) => setCalibParams({...calibParams, existing_k_table: e.target.value === 'none' ? undefined : e.target.value})}
                              >
                                {existingTables.k_tables.map((table) => (
                                  <FormControlLabel
                                    key={table.path}
                                    value={table.path}
                                    control={<Radio size="small" />}
                                    label={
                                      <Typography variant="caption">
                                        {table.filename} ({table.size_mb.toFixed(1)} MB, {table.age_hours.toFixed(1)}h ago)
                                      </Typography>
                                    }
                                  />
                                ))}
                                <FormControlLabel value="none" control={<Radio size="small" />} label={<Typography variant="caption">None</Typography>} />
                              </RadioGroup>
                            </Box>
                          )}
                          
                          {existingTables.bp_tables.length > 0 && (
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="caption" sx={{ fontWeight: 'bold' }}>BP (Bandpass) Tables:</Typography>
                              <RadioGroup
                                value={calibParams.existing_bp_table || 'none'}
                                onChange={(e) => setCalibParams({...calibParams, existing_bp_table: e.target.value === 'none' ? undefined : e.target.value})}
                              >
                                {existingTables.bp_tables.map((table) => (
                                  <FormControlLabel
                                    key={table.path}
                                    value={table.path}
                                    control={<Radio size="small" />}
                                    label={
                                      <Typography variant="caption">
                                        {table.filename} ({table.size_mb.toFixed(1)} MB, {table.age_hours.toFixed(1)}h ago)
                                      </Typography>
                                    }
                                  />
                                ))}
                                <FormControlLabel value="none" control={<Radio size="small" />} label={<Typography variant="caption">None</Typography>} />
                              </RadioGroup>
                            </Box>
                          )}
                          
                          {existingTables.g_tables.length > 0 && (
                            <Box sx={{ mb: 2 }}>
                              <Typography variant="caption" sx={{ fontWeight: 'bold' }}>G (Gain) Tables:</Typography>
                              <RadioGroup
                                value={calibParams.existing_g_table || 'none'}
                                onChange={(e) => setCalibParams({...calibParams, existing_g_table: e.target.value === 'none' ? undefined : e.target.value})}
                              >
                                {existingTables.g_tables.map((table) => (
                                  <FormControlLabel
                                    key={table.path}
                                    value={table.path}
                                    control={<Radio size="small" />}
                                    label={
                                      <Typography variant="caption">
                                        {table.filename} ({table.size_mb.toFixed(1)} MB, {table.age_hours.toFixed(1)}h ago)
                                      </Typography>
                                    }
                                  />
                                ))}
                                <FormControlLabel value="none" control={<Radio size="small" />} label={<Typography variant="caption">None</Typography>} />
                              </RadioGroup>
                            </Box>
                          )}
                        </Box>
                      )}
                    </Box>
                  );
                })()}
                
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
                      onChange={(e) => setCalibParams({ ...calibParams, min_pb: parseFloat(e.target.value) })}
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
                
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={handleCalibrateSubmit}
                  disabled={!selectedMS || calibrateMutation.isPending || (!calibParams.solve_delay && !calibParams.solve_bandpass && !calibParams.solve_gains)}
                  fullWidth
                >
                  Run Calibration
                </Button>
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
                {(() => {
                  const { data: calTables } = useCalTables();
                  if (!calTables || calTables.items.length === 0) return null;
                  
                  return (
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
                  );
                })()}
                
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={handleApplySubmit}
                  disabled={!selectedMS || !applyParams.gaintables?.length || applyMutation.isPending}
                  fullWidth
                >
                  Apply Calibration
                </Button>
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
                  onChange={(e) => setImageParams({ ...imageParams, wprojplanes: parseInt(e.target.value) })}
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
                
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={handleImageSubmit}
                  disabled={!selectedMS || imageMutation.isPending}
                  fullWidth
                >
                  Create Image
                </Button>
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
    </Box>
  );
}
