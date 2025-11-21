/**
 * Retry Button Component
 * Provides a retry UI for failed operations
 */

import { Button, CircularProgress } from "@mui/material";
import type { ButtonProps } from "@mui/material/Button";
import { Refresh } from "@mui/icons-material";
import { useState } from "react";

export interface RetryButtonProps extends Omit<ButtonProps, "onClick"> {
  onRetry: () => Promise<void> | void;
  retryLabel?: string;
  showLoading?: boolean;
}

export function RetryButton({
  onRetry,
  retryLabel = "Retry",
  showLoading = true,
  ...buttonProps
}: RetryButtonProps) {
  const [isRetrying, setIsRetrying] = useState(false);

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await onRetry();
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <Button
      {...buttonProps}
      onClick={handleRetry}
      disabled={isRetrying || buttonProps.disabled}
      startIcon={isRetrying && showLoading ? <CircularProgress size={16} /> : <Refresh />}
    >
      {isRetrying ? "Retrying..." : retryLabel}
    </Button>
  );
}
