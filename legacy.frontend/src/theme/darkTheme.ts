/**
 * Dark mode theme configuration for DSA-110 pipeline UI.
 * Optimized for astronomers working at night.
 */
import { createTheme } from "@mui/material/styles";

export const darkTheme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#0D1117",
      paper: "#161B22",
    },
    primary: {
      main: "#58A6FF",
      light: "#79C0FF",
      dark: "#1F6FEB",
    },
    secondary: {
      main: "#A5D6FF",
    },
    success: {
      main: "#3FB950",
      light: "#7EE787",
      dark: "#238636",
    },
    warning: {
      main: "#D29922",
      light: "#FFA657",
      dark: "#9E6A03",
    },
    error: {
      main: "#F85149",
      light: "#FF7B72",
      dark: "#DA3633",
    },
    info: {
      main: "#79C0FF",
    },
    text: {
      primary: "#C9D1D9",
      secondary: "#8B949E",
      disabled: "#6E7681",
    },
    divider: "#30363D",
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 600,
      fontSize: "2rem", // 32px
      lineHeight: 1.2,
      letterSpacing: "-0.02em",
    },
    h2: {
      fontWeight: 600,
      fontSize: "1.5rem", // 24px
      lineHeight: 1.3,
      letterSpacing: "-0.01em",
    },
    h3: {
      fontWeight: 600,
      fontSize: "1.25rem", // 20px
      lineHeight: 1.4,
    },
    h4: {
      fontWeight: 600,
      fontSize: "1.125rem", // 18px
      lineHeight: 1.4,
    },
    h5: {
      fontWeight: 600,
      fontSize: "1rem", // 16px
      lineHeight: 1.5,
    },
    h6: {
      fontWeight: 600,
      fontSize: "0.875rem", // 14px
      lineHeight: 1.5,
    },
    body1: {
      fontSize: "0.875rem", // 14px
      lineHeight: 1.5,
    },
    body2: {
      fontSize: "0.75rem", // 12px
      lineHeight: 1.5,
    },
    button: { textTransform: "none" }, // Don't uppercase buttons
  },
  spacing: 4, // 4px base unit for consistent spacing
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          borderRadius: 8,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
        },
      },
    },
  },
});
