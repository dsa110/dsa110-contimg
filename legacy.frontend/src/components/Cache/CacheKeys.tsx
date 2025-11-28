import { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from "@mui/material";
import { Delete as DeleteIcon, Visibility as VisibilityIcon } from "@mui/icons-material";
import { useCacheKeys, useCacheKey } from "../../api/queries";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../../api/client";

export default function CacheKeys() {
  const [pattern, setPattern] = useState<string>("");
  const [limit, setLimit] = useState<number>(100);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [keyToDelete, setKeyToDelete] = useState<string | null>(null);

  const { data: keysData, isLoading, error } = useCacheKeys(pattern || undefined, limit);
  const { data: keyDetail } = useCacheKey(selectedKey || "");
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: async (key: string) => {
      await apiClient.delete(`/cache/keys/${encodeURIComponent(key)}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cache", "keys"] });
      queryClient.invalidateQueries({ queryKey: ["cache", "stats"] });
      setDeleteDialogOpen(false);
      setKeyToDelete(null);
    },
  });

  const handleDelete = (key: string) => {
    setKeyToDelete(key);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (keyToDelete) {
      deleteMutation.mutate(keyToDelete);
    }
  };

  if (error) {
    return (
      <Alert severity="error">
        Failed to load cache keys: {error instanceof Error ? error.message : "Unknown error"}
      </Alert>
    );
  }

  return (
    <>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Cache Keys
          </Typography>

          {/* Filters */}
          <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
            <TextField
              label="Filter Pattern"
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              placeholder="e.g., variability_stats:*"
              sx={{ flexGrow: 1 }}
              helperText="Use wildcards: * for any characters"
            />
            <TextField
              label="Limit"
              type="number"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value) || 100)}
              sx={{ width: 120 }}
              inputProps={{ min: 1, max: 1000 }}
            />
          </Box>

          {/* Keys Table */}
          {isLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Key</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {keysData && keysData.keys.length > 0 ? (
                    keysData.keys.map((keyInfo) => (
                      <TableRow key={keyInfo.key}>
                        <TableCell>
                          <Typography
                            variant="body2"
                            sx={{ fontFamily: "monospace", fontSize: "0.875rem" }}
                          >
                            {keyInfo.key}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {keyInfo.has_value ? (
                            <Chip label="Active" color="success" size="small" />
                          ) : (
                            <Chip label="Expired" color="default" size="small" />
                          )}
                        </TableCell>
                        <TableCell>
                          <IconButton
                            size="small"
                            onClick={() => setSelectedKey(keyInfo.key)}
                            title="View details"
                          >
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDelete(keyInfo.key)}
                            title="Delete"
                            color="error"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={3} align="center">
                        No cache keys found
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {keysData && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Showing {keysData.keys.length} of {keysData.total} keys
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Key Detail Dialog */}
      <Dialog open={!!selectedKey} onClose={() => setSelectedKey(null)} maxWidth="md" fullWidth>
        <DialogTitle>Cache Key Details</DialogTitle>
        <DialogContent>
          {keyDetail ? (
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Key:
              </Typography>
              <Typography variant="body2" sx={{ fontFamily: "monospace", mb: 2 }}>
                {keyDetail.key}
              </Typography>

              <Typography variant="subtitle2" gutterBottom>
                Value Type: {keyDetail.value_type}
              </Typography>
              <Typography variant="subtitle2" gutterBottom>
                Value Size: {keyDetail.value_size} bytes
              </Typography>

              <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
                Value:
              </Typography>
              <Box
                sx={{
                  p: 2,
                  bgcolor: "grey.100",
                  borderRadius: 1,
                  fontFamily: "monospace",
                  fontSize: "0.875rem",
                  maxHeight: 400,
                  overflow: "auto",
                }}
              >
                <pre>{JSON.stringify(keyDetail.value, null, 2)}</pre>
              </Box>
            </Box>
          ) : (
            <CircularProgress />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedKey(null)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Cache Key</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete the cache key "{keyToDelete}"?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={confirmDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
