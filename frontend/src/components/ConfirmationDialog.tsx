/**
 * Confirmation Dialog Component
 * For destructive actions and important confirmations
 */
// import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Box,
  Typography,
} from "@mui/material";
import { Warning, ErrorOutline, Info, CheckCircle } from "@mui/icons-material";

export type ConfirmationSeverity = "warning" | "error" | "info" | "success";

interface ConfirmationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  severity?: ConfirmationSeverity;
  confirmText?: string;
  cancelText?: string;
  loading?: boolean;
}

const severityConfig = {
  warning: {
    icon: Warning,
    color: "warning" as const,
    defaultConfirmText: "Continue",
  },
  error: {
    icon: ErrorOutline,
    color: "error" as const,
    defaultConfirmText: "Delete",
  },
  info: {
    icon: Info,
    color: "info" as const,
    defaultConfirmText: "Confirm",
  },
  success: {
    icon: CheckCircle,
    color: "success" as const,
    defaultConfirmText: "Confirm",
  },
};

export function ConfirmationDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  severity = "warning",
  confirmText,
  cancelText = "Cancel",
  loading = false,
}: ConfirmationDialogProps) {
  const config = severityConfig[severity];
  const Icon = config.icon;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
        },
      }}
    >
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Icon color={config.color} />
          <Typography variant="h6" component="span">
            {title}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mt: 1, fontSize: "0.875rem" }}>{message}</DialogContentText>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>
          {cancelText}
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          color={config.color}
          disabled={loading}
          autoFocus
        >
          {loading ? "Processing..." : confirmText || config.defaultConfirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
