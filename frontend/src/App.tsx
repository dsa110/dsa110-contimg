import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, CssBaseline, Box } from '@mui/material';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { darkTheme } from './theme/darkTheme';
import Navigation from './components/Navigation';
import DashboardPage from './pages/DashboardPage';
import ControlPage from './pages/ControlPage';
import MosaicGalleryPage from './pages/MosaicGalleryPage';
import SourceMonitoringPage from './pages/SourceMonitoringPage';
import SkyViewPage from './pages/SkyViewPage';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={darkTheme}>
        <CssBaseline />
        <BrowserRouter>
          <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <Navigation />
            <Box component="main" sx={{ flexGrow: 1 }}>
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/control" element={<ControlPage />} />
                <Route path="/mosaics" element={<MosaicGalleryPage />} />
                <Route path="/sources" element={<SourceMonitoringPage />} />
                <Route path="/sky" element={<SkyViewPage />} />
              </Routes>
            </Box>
          </Box>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
