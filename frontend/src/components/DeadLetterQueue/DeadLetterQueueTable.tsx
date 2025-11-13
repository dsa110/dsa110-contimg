/**
 * Dead Letter Queue Table Component
 * Displays failed operations with retry/resolve capabilities
 */
import { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Alert,
  Stack,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  PlayArrow as RetryIcon,
  CheckCircle as ResolveIcon,
  Cancel as FailIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import {
  useDLQItems,
  useRetryDLQItem,
  useResolveDLQItem,
  useFailDLQItem,
} from '../../api/queries';
import type { DLQItem } from '../../api/types';

interface DeadLetterQueueTableProps {
  component?: string;
  status?: string;
  limit?: number;
}

export function DeadLetterQueueTable({
  component,
  status = 'pending',
  limit = 100,
}: DeadLetterQueueTableProps) {
  const [selectedItem, setSelectedItem] = useState<DLQItem | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogAction, setDialogAction] = useState<'retry' | 'resolve' | 'fail' | 'view' | null>(null);
  const [note, setNote] = useState('');

  const { data: items = [], isLoading, refetch } = useDLQItems(component, status, limit, 0);
  const retryMutation = useRetryDLQItem();
  const resolveMutation = useResolveDLQItem();
  const failMutation = useFailDLQItem();

  const handleAction = async (item: DLQItem, action: 'retry' | 'resolve' | 'fail') => {
    setSelectedItem(item);
    setDialogAction(action);
    setNote('');
    setDialogOpen(true);
  };

  const handleView = (item: DLQItem) => {
    setSelectedItem(item);
    setDialogAction('view');
    setNote('');
    setDialogOpen(true);
  };

  const handleConfirm = async () => {
    if (!selectedItem || !dialogAction) return;

    try {
      if (dialogAction === 'retry') {
        await retryMutation.mutateAsync({ itemId: selectedItem.id, note: note || undefined });
      } else if (dialogAction === 'resolve') {
        await resolveMutation.mutateAsync({ itemId: selectedItem.id, note: note || undefined });
      } else if (dialogAction === 'fail') {
        await failMutation.mutateAsync({ itemId: selectedItem.id, note: note || undefined });
      }
      setDialogOpen(false);
      setSelectedItem(null);
      setDialogAction(null);
      setNote('');
      refetch();
    } catch (error) {
      console.error('Failed to perform action:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'retrying':
        return 'info';
      case 'resolved':
        return 'success';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  if (isLoading) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Component</TableCell>
              <TableCell>Operation</TableCell>
              <TableCell>Error Type</TableCell>
              <TableCell>Error Message</TableCell>
              <TableCell>Retry Count</TableCell>
              <TableCell>Created At</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} align="center">
                  <Typography variant="body2" color="text.secondary">
                    No items found
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.id}</TableCell>
                  <TableCell>{item.component}</TableCell>
                  <TableCell>{item.operation}</TableCell>
                  <TableCell>
                    <Chip label={item.error_type} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Tooltip title={item.error_message}>
                      <Typography variant="body2" sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {item.error_message}
                      </Typography>
                    </Tooltip>
                  </TableCell>
                  <TableCell>{item.retry_count}</TableCell>
                  <TableCell>
                    {format(new Date(item.created_at * 1000), 'yyyy-MM-dd HH:mm:ss')}
                  </TableCell>
                  <TableCell>
                    <Chip label={item.status} color={getStatusColor(item.status) as any} size="small" />
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <Tooltip title="View Details">
                        <IconButton size="small" onClick={() => handleView(item)}>
                          <InfoIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {item.status === 'pending' && (
                        <>
                          <Tooltip title="Retry">
                            <IconButton size="small" onClick={() => handleAction(item, 'retry')}>
                              <RetryIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Resolve">
                            <IconButton size="small" onClick={() => handleAction(item, 'resolve')}>
                              <ResolveIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Mark as Failed">
                            <IconButton size="small" onClick={() => handleAction(item, 'fail')}>
                              <FailIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {dialogAction === 'view' && 'Item Details'}
          {dialogAction === 'retry' && 'Retry Failed Operation'}
          {dialogAction === 'resolve' && 'Resolve Item'}
          {dialogAction === 'fail' && 'Mark as Failed'}
        </DialogTitle>
        <DialogContent>
          {selectedItem && (
            <Stack spacing={2}>
              {dialogAction === 'view' ? (
                <>
                  <Box>
                    <Typography variant="subtitle2">Component</Typography>
                    <Typography>{selectedItem.component}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">Operation</Typography>
                    <Typography>{selectedItem.operation}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">Error Type</Typography>
                    <Typography>{selectedItem.error_type}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">Error Message</Typography>
                    <Alert severity="error">{selectedItem.error_message}</Alert>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">Context</Typography>
                    <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
                      <pre style={{ margin: 0, fontSize: '0.875rem' }}>
                        {JSON.stringify(selectedItem.context, null, 2)}
                      </pre>
                    </Paper>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">Retry Count</Typography>
                    <Typography>{selectedItem.retry_count}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">Created At</Typography>
                    <Typography>
                      {format(new Date(selectedItem.created_at * 1000), 'yyyy-MM-dd HH:mm:ss')}
                    </Typography>
                  </Box>
                </>
              ) : (
                <>
                  <Alert severity="info">
                    {dialogAction === 'retry' && 'This will mark the item as retrying and attempt to reprocess it.'}
                    {dialogAction === 'resolve' && 'This will mark the item as resolved (manually fixed).'}
                    {dialogAction === 'fail' && 'This will mark the item as permanently failed.'}
                  </Alert>
                  <TextField
                    label="Note (optional)"
                    multiline
                    rows={3}
                    fullWidth
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Add a note about this action..."
                  />
                </>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          {dialogAction !== 'view' && (
            <Button
              onClick={handleConfirm}
              variant="contained"
              disabled={retryMutation.isPending || resolveMutation.isPending || failMutation.isPending}
            >
              Confirm
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </>
  );
}

