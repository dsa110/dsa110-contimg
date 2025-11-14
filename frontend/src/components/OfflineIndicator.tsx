/**
 * Offline Indicator Component
 * Shows when the application is offline
 */

import { Alert, Snackbar, Slide, SlideProps } from "@mui/material";
import { CloudOff, CloudDone } from "@mui/icons-material";
import { useOfflineDetection } from "../hooks/useOfflineDetection";

function SlideTransition(props: SlideProps) {
  return <Slide {...props} direction="down" />;
}

export function OfflineIndicator() {
  const { isOnline, wasOffline } = useOfflineDetection();

  return (
    <>
      {/* Offline notification */}
      <Snackbar
        open={!isOnline}
        TransitionComponent={SlideTransition}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        autoHideDuration={null}
      >
        <Alert severity="warning" icon={<CloudOff />} sx={{ minWidth: "300px" }}>
          You are currently offline. Some features may be unavailable.
        </Alert>
      </Snackbar>

      {/* Back online notification */}
      <Snackbar
        open={isOnline && wasOffline}
        TransitionComponent={SlideTransition}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        autoHideDuration={3000}
        onClose={() => {}}
      >
        <Alert severity="success" icon={<CloudDone />} sx={{ minWidth: "300px" }}>
          Connection restored. Syncing data...
        </Alert>
      </Snackbar>
    </>
  );
}
