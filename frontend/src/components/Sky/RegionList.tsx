/**
 * RegionList Component
 * Displays and manages regions for the current image
 */
import { useState } from "react";
import {
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Typography,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
} from "@mui/material";
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from "@mui/icons-material";
import {
  useRegions,
  useDeleteRegion,
  useUpdateRegion,
} from "../../api/queries";
import { logger } from "../../utils/logger";

interface RegionListProps {
  imagePath?: string | null;
  onRegionSelect?: (region: any) => void;
  selectedRegionId?: number | null;
}

export default function RegionList({
  imagePath,
  onRegionSelect,
  selectedRegionId,
}: RegionListProps) {
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingRegion, setEditingRegion] = useState<any>(null);
  const [editName, setEditName] = useState("");
  const [hiddenRegions, setHiddenRegions] = useState<Set<number>>(new Set());

  const { data: regionsData, isLoading } = useRegions(imagePath);
  const deleteRegion = useDeleteRegion();
  const updateRegion = useUpdateRegion();

  const regions = regionsData?.regions || [];

  const handleDelete = async (regionId: number) => {
    if (!confirm("Delete this region?")) return;

    try {
      await deleteRegion.mutateAsync(regionId);
    } catch (e) {
      logger.error("Error deleting region:", e);
      alert("Failed to delete region");
    }
  };

  const handleEdit = (region: any) => {
    setEditingRegion(region);
    setEditName(region.name);
    setEditDialogOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editingRegion || !editName.trim()) return;

    try {
      await updateRegion.mutateAsync({
        regionId: editingRegion.id,
        regionData: { name: editName.trim() },
      });
      setEditDialogOpen(false);
      setEditingRegion(null);
      setEditName("");
    } catch (e) {
      logger.error("Error updating region:", e);
      alert("Failed to update region");
    }
  };

  const handleToggleVisibility = (regionId: number) => {
    const newHidden = new Set(hiddenRegions);
    if (newHidden.has(regionId)) {
      newHidden.delete(regionId);
    } else {
      newHidden.add(regionId);
    }
    setHiddenRegions(newHidden);
  };

  if (isLoading) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Loading regions...
        </Typography>
      </Paper>
    );
  }

  if (regions.length === 0) {
    return (
      <Paper sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          No regions defined for this image
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="subtitle2" gutterBottom>
        Regions ({regions.length})
      </Typography>
      <List dense>
        {regions.map((region: any) => (
          <ListItem
            key={region.id}
            onClick={() => onRegionSelect?.(region)}
            sx={{
              cursor: "pointer",
              opacity: hiddenRegions.has(region.id) ? 0.5 : 1,
              backgroundColor: selectedRegionId === region.id ? "action.selected" : "transparent",
            }}
          >
            <ListItemText
              primary={region.name}
              secondary={
                <Box sx={{ display: "flex", gap: 1, mt: 0.5 }}>
                  <Chip label={region.type} size="small" />
                  <Typography variant="caption" color="text.secondary">
                    {new Date(region.created_at * 1000).toLocaleDateString()}
                  </Typography>
                </Box>
              }
            />
            <ListItemSecondaryAction>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleToggleVisibility(region.id);
                }}
                title={hiddenRegions.has(region.id) ? "Show" : "Hide"}
              >
                {hiddenRegions.has(region.id) ? <VisibilityOffIcon /> : <VisibilityIcon />}
              </IconButton>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleEdit(region);
                }}
                title="Edit"
              >
                <EditIcon />
              </IconButton>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(region.id);
                }}
                title="Delete"
                color="error"
              >
                <DeleteIcon />
              </IconButton>
            </ListItemSecondaryAction>
          </ListItem>
        ))}
      </List>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)}>
        <DialogTitle>Edit Region</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Region Name"
            fullWidth
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveEdit} variant="contained" disabled={!editName.trim()}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
