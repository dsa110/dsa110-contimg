/**
 * QANotebookGenerator Component - Generate QA notebooks
 */
import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  CircularProgress,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  NoteAdd,
  CheckCircle,
  Error as ErrorIcon,
  Download,
  Description,
} from '@mui/icons-material';
import { useGenerateNotebook, useRunQA } from '../../api/queries';

interface QANotebookGeneratorProps {
  defaultMSPath?: string;
  defaultQARoot?: string;
}

export default function QANotebookGenerator({
  defaultMSPath = '',
  defaultQARoot = '/data/dsa110-contimg/state/qa',
}: QANotebookGeneratorProps) {
  const [msPath, setMSPath] = useState(defaultMSPath);
  const [qaRoot, setQARoot] = useState(defaultQARoot);
  const [outputPath, setOutputPath] = useState('');
  const [title, setTitle] = useState('');
  const [notebookType, setNotebookType] = useState<'qa' | 'fits' | 'ms'>('qa');
  const [generateNotebook, setGenerateNotebook] = useState(true);
  const [displaySummary, setDisplaySummary] = useState(false);

  const generateNotebookMutation = useGenerateNotebook();
  const runQAMutation = useRunQA();

  const handleGenerateNotebook = () => {
    if (!outputPath) {
      alert('Please specify an output path');
      return;
    }

    generateNotebookMutation.mutate({
      ms_path: msPath || undefined,
      qa_root: qaRoot || undefined,
      output_path: outputPath,
      title: title || undefined,
      notebook_type: notebookType,
    });
  };

  const handleRunQA = () => {
    if (!msPath) {
      alert('Please specify an MS path');
      return;
    }

    runQAMutation.mutate({
      ms_path: msPath,
      qa_root: qaRoot,
      generate_notebook: generateNotebook,
      display_summary: displaySummary,
    });
  };

  const downloadNotebook = (notebookPath: string) => {
    const encodedPath = encodeURIComponent(notebookPath);
    window.open(`/api/visualization/notebook/${encodedPath}`, '_blank');
  };

  const generateResult = generateNotebookMutation.data;
  const qaResult = runQAMutation.data;

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <NoteAdd />
        <Typography variant="h6">QA Notebook Generator</Typography>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <TextField
          label="MS Path"
          value={msPath}
          onChange={(e) => setMSPath(e.target.value)}
          placeholder="/data/dsa110-contimg/state/ms/science/2025-10-28/2025-10-28T13:55:53.ms"
          fullWidth
          size="small"
        />

        <TextField
          label="QA Root Directory"
          value={qaRoot}
          onChange={(e) => setQARoot(e.target.value)}
          fullWidth
          size="small"
        />

        <Divider />

        <Typography variant="subtitle2" sx={{ mt: 1 }}>
          Generate Notebook
        </Typography>

        <TextField
          label="Output Path"
          value={outputPath}
          onChange={(e) => setOutputPath(e.target.value)}
          placeholder="/data/dsa110-contimg/state/qa/reports/my_notebook.ipynb"
          fullWidth
          size="small"
          required
        />

        <TextField
          label="Title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          fullWidth
          size="small"
        />

        <FormControl fullWidth size="small">
          <InputLabel>Notebook Type</InputLabel>
          <Select
            value={notebookType}
            label="Notebook Type"
            onChange={(e) => setNotebookType(e.target.value as 'qa' | 'fits' | 'ms')}
          >
            <MenuItem value="qa">QA Report</MenuItem>
            <MenuItem value="fits">FITS Viewer</MenuItem>
            <MenuItem value="ms">MS Explorer</MenuItem>
          </Select>
        </FormControl>

        <Button
          variant="contained"
          onClick={handleGenerateNotebook}
          disabled={generateNotebookMutation.isPending || !outputPath}
          startIcon={
            generateNotebookMutation.isPending ? (
              <CircularProgress size={16} />
            ) : (
              <NoteAdd />
            )
          }
        >
          Generate Notebook
        </Button>

        {generateNotebookMutation.isError && (
          <Alert severity="error">
            Error generating notebook:{' '}
            {generateNotebookMutation.error instanceof Error
              ? generateNotebookMutation.error.message
              : 'Unknown error'}
          </Alert>
        )}

        {generateResult && (
          <Alert
            severity="success"
            action={
              <Button
                color="inherit"
                size="small"
                startIcon={<Download />}
                onClick={() => downloadNotebook(generateResult.notebook_path)}
              >
                Download
              </Button>
            }
          >
            Notebook generated successfully: {generateResult.notebook_path}
          </Alert>
        )}

        <Divider />

        <Typography variant="subtitle2" sx={{ mt: 1 }}>
          Run QA and Generate Notebook
        </Typography>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Generate Notebook</InputLabel>
            <Select
              value={generateNotebook ? 'yes' : 'no'}
              label="Generate Notebook"
              onChange={(e) => setGenerateNotebook(e.target.value === 'yes')}
            >
              <MenuItem value="yes">Yes</MenuItem>
              <MenuItem value="no">No</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Display Summary</InputLabel>
            <Select
              value={displaySummary ? 'yes' : 'no'}
              label="Display Summary"
              onChange={(e) => setDisplaySummary(e.target.value === 'yes')}
            >
              <MenuItem value="yes">Yes</MenuItem>
              <MenuItem value="no">No</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Button
          variant="contained"
          color="secondary"
          onClick={handleRunQA}
          disabled={runQAMutation.isPending || !msPath}
          startIcon={
            runQAMutation.isPending ? <CircularProgress size={16} /> : <Description />
          }
        >
          Run QA
        </Button>

        {runQAMutation.isError && (
          <Alert severity="error">
            Error running QA:{' '}
            {runQAMutation.error instanceof Error
              ? runQAMutation.error.message
              : 'Unknown error'}
          </Alert>
        )}

        {qaResult && (
          <Alert severity={qaResult.success ? 'success' : 'warning'}>
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>QA Run {qaResult.success ? 'Completed' : 'Failed'}</strong>
              </Typography>
              {qaResult.reasons && qaResult.reasons.length > 0 && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption">
                    <strong>Reasons:</strong>
                  </Typography>
                  <List dense>
                    {qaResult.reasons.map((reason, idx) => (
                      <ListItem key={idx}>
                        <ListItemIcon>
                          {qaResult.success ? (
                            <CheckCircle fontSize="small" color="success" />
                          ) : (
                            <ErrorIcon fontSize="small" color="error" />
                          )}
                        </ListItemIcon>
                        <ListItemText primary={reason} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
              {qaResult.artifacts && qaResult.artifacts.length > 0 && (
                <Box>
                  <Typography variant="caption" sx={{ display: 'block', mb: 0.5 }}>
                    <strong>Artifacts:</strong>
                  </Typography>
                  {qaResult.artifacts.map((artifact, idx) => (
                    <Chip
                      key={idx}
                      label={artifact.split('/').pop()}
                      size="small"
                      icon={<Description />}
                      onClick={() => downloadNotebook(artifact)}
                      sx={{ mr: 0.5, mb: 0.5, cursor: 'pointer' }}
                    />
                  ))}
                </Box>
              )}
            </Box>
          </Alert>
        )}
      </Box>
    </Paper>
  );
}

