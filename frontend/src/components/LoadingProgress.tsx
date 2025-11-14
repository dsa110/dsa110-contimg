import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { LinearProgress, Box } from "@mui/material";

/**
 * Loading progress indicator for route transitions
 * Shows a progress bar at the top of the page during navigation
 */
export function LoadingProgress() {
  const location = useLocation();
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Reset loading state on route change
    setLoading(true);
    setProgress(0);

    // Simulate progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(interval);
          return 90;
        }
        return prev + 10;
      });
    }, 50);

    // Complete progress after a short delay
    const timeout = setTimeout(() => {
      setProgress(100);
      setTimeout(() => {
        setLoading(false);
        setProgress(0);
      }, 200);
    }, 300);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [location.pathname]);

  if (!loading) {
    return null;
  }

  return (
    <Box
      sx={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        height: 3,
      }}
    >
      <LinearProgress
        variant="determinate"
        value={progress}
        sx={{
          height: 3,
          "& .MuiLinearProgress-bar": {
            transition: "transform 0.1s linear",
          },
        }}
      />
    </Box>
  );
}
