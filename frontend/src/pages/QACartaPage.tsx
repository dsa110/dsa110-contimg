/**
 * QA CARTA Page - CARTA-style QA visualization with Golden Layout
 * 
 * This page provides a flexible, dockable panel interface inspired by CARTA
 * for exploring QA data, viewing FITS files, browsing CASA tables, etc.
 */
import { useEffect, useRef, useState } from 'react';
import { Box, Typography, Alert } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import 'golden-layout/dist/css/goldenlayout-base.css';
import 'golden-layout/dist/css/themes/goldenlayout-dark-theme.css';
import './QACartaPage.css'; // Custom theme overrides to match MUI dark theme
import DirectoryBrowser from '../components/QA/DirectoryBrowser';
import FITSViewer from '../components/QA/FITSViewer';
import CasaTableViewer from '../components/QA/CasaTableViewer';

// Widget component registry
const WIDGET_COMPONENTS: Record<string, React.ComponentType<any>> = {
  DirectoryBrowser,
  FITSViewer,
  CasaTableViewer,
};

// Create a QueryClient for Golden Layout components
// Since they're rendered in separate React roots, they need their own provider
const widgetQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
});

// React wrapper for Golden Layout components
function WidgetWrapper({ 
  componentName, 
  props,
  onFileSelect,
}: { 
  componentName: string; 
  props?: any;
  onFileSelect?: (path: string, type: string) => void;
}) {
  const Component = WIDGET_COMPONENTS[componentName];
  if (!Component) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="error">Unknown widget: {componentName}</Typography>
      </Box>
    );
  }

  // Wrap component with QueryClientProvider since it's in a separate React root
  const componentContent = componentName === 'DirectoryBrowser' && onFileSelect
    ? <Component {...props} onSelectFile={onFileSelect} />
    : <Component {...props} />;

  return (
    <QueryClientProvider client={widgetQueryClient}>
      {componentContent}
    </QueryClientProvider>
  );
}

export default function QACartaPage() {
  const layoutRef = useRef<HTMLDivElement>(null);
  const goldenLayoutRef = useRef<any>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFITSPath, setSelectedFITSPath] = useState<string | null>(null);
  const [selectedTablePath, setSelectedTablePath] = useState<string | null>(null);
  const fitsViewerContainerRef = useRef<any>(null);
  const casaTableViewerContainerRef = useRef<any>(null);

  // Handle file selection from DirectoryBrowser
  const handleFileSelect = (path: string, type: string) => {
    if (type === 'fits') {
      setSelectedFITSPath(path);
      // Update FITS viewer component state
      if (fitsViewerContainerRef.current) {
        fitsViewerContainerRef.current.extendState({ fitsPath: path });
      }
    } else if (type === 'casatable') {
      setSelectedTablePath(path);
      // Update CASA table viewer component state
      if (casaTableViewerContainerRef.current) {
        casaTableViewerContainerRef.current.extendState({ tablePath: path });
      }
    }
  };

  useEffect(() => {
    if (!layoutRef.current || isInitialized) return;

    // Dynamically import Golden Layout to catch import errors
    import('golden-layout')
      .then((module) => {
        // GoldenLayout and ComponentContainer are named exports
        const GoldenLayout = (module as any).GoldenLayout;
        const ComponentContainer = (module as any).ComponentContainer;
        
        if (!GoldenLayout) {
          throw new Error(`GoldenLayout not found in module. Available exports: ${Object.keys(module).join(', ')}`);
        }
        
        if (!ComponentContainer) {
          throw new Error(`ComponentContainer not found in module. Available exports: ${Object.keys(module).join(', ')}`);
        }
        
        try {
          // Default layout configuration - Golden Layout v2+ uses 'root' with nested structure
          const config: any = {
            root: {
              type: 'row',
              content: [
                {
                  type: 'component',
                  componentType: 'DirectoryBrowser',
                  title: 'File Browser',
                  width: 25,
                  componentState: {
                    initialPath: '/data/dsa110-contimg/state',
                  },
                },
                {
                  type: 'column',
                  width: 75,
                  content: [
                    {
                      type: 'component',
                      componentType: 'FITSViewer',
                      title: 'FITS Viewer',
                      height: 50,
                      componentState: {
                        fitsPath: selectedFITSPath,
                      },
                    },
                    {
                      type: 'component',
                      componentType: 'CasaTableViewer',
                      title: 'CASA Table Viewer',
                      height: 50,
                      componentState: {
                        tablePath: selectedTablePath,
                      },
                    },
                  ],
                },
              ],
            },
          };
          
          console.log('Golden Layout config:', JSON.stringify(config, null, 2));

          // Component factory function
          const componentFactory = (componentName: string) => {
            return (container: any, componentState: any) => {
              const root = document.createElement('div');
              root.style.height = '100%';
              root.style.overflow = 'auto';
              container.getElement().append(root);
              
              import('react-dom/client').then(({ createRoot }) => {
                const reactRoot = createRoot(root);
                if (componentName === 'DirectoryBrowser') {
                  reactRoot.render(
                    <WidgetWrapper componentName="DirectoryBrowser" props={componentState} onFileSelect={handleFileSelect} />
                  );
                } else if (componentName === 'FITSViewer') {
                  fitsViewerContainerRef.current = container;
                  reactRoot.render(
                    <WidgetWrapper componentName="FITSViewer" props={{ ...componentState, fitsPath: componentState.fitsPath || selectedFITSPath }} />
                  );
                } else if (componentName === 'CasaTableViewer') {
                  casaTableViewerContainerRef.current = container;
                  reactRoot.render(
                    <WidgetWrapper componentName="CasaTableViewer" props={{ ...componentState, tablePath: componentState.tablePath || selectedTablePath }} />
                  );
                }
              });
            };
          };
          
          // CRITICAL: Create layout WITHOUT config first, register components, THEN load config
          console.log('Creating empty layout...');
          const layout = new GoldenLayout(layoutRef.current!);
          
          // Register components BEFORE loading config
          console.log('Registering components...');
          layout.registerComponentFactoryFunction('DirectoryBrowser', componentFactory('DirectoryBrowser'));
          layout.registerComponentFactoryFunction('FITSViewer', componentFactory('FITSViewer'));
          layout.registerComponentFactoryFunction('CasaTableViewer', componentFactory('CasaTableViewer'));
          
          // Now load the config - check for available methods
          console.log('Loading config...');
          if (typeof (layout as any).loadLayout === 'function') {
            (layout as any).loadLayout(config);
            console.log('Config loaded via loadLayout()');
          } else if (typeof (layout as any).loadState === 'function') {
            (layout as any).loadState(config);
            console.log('Config loaded via loadState()');
          } else if (typeof (layout as any).load === 'function') {
            (layout as any).load(config);
            console.log('Config loaded via load()');
          } else {
            // Fallback: try to manually add components using layout API
            console.warn('No load method found, trying manual component addition');
            try {
              const rootItem = (layout as any).root;
              if (rootItem && typeof rootItem.addChild === 'function') {
                // This is a fallback - may not work with v2 API
                console.log('Attempting manual component addition...');
              } else {
                throw new Error('No suitable method to load config found');
              }
            } catch (e) {
              console.error('Failed to load config:', e);
              throw e;
            }
          }

          // Layout should already be initialized with config from constructor
          // Check if components were actually created
          const rootElement = layoutRef.current?.querySelector('.lm_root');
          const hasChildren = rootElement && rootElement.children.length > 0;
          
          console.log('Layout initialized. Root has children:', hasChildren);
          
          if (!hasChildren) {
            console.warn('Layout created but no children found. Config may not have been processed correctly.');
            // Try to manually trigger layout update if method exists
            if (typeof (layout as any).updateSize === 'function') {
              (layout as any).updateSize();
            }
          }

          goldenLayoutRef.current = layout;
          setIsInitialized(true);
          setError(null);
        } catch (initError) {
          console.error('Failed to initialize Golden Layout:', initError);
          setError(`Initialization error: ${initError instanceof Error ? initError.message : String(initError)}`);
        }
      })
      .catch((importError) => {
        console.error('Failed to import Golden Layout:', importError);
        setError(`Import error: ${importError instanceof Error ? importError.message : String(importError)}`);
      });

    // Cleanup
    return () => {
      if (goldenLayoutRef.current) {
        try {
          goldenLayoutRef.current.destroy();
        } catch (e) {
          console.error('Error destroying Golden Layout:', e);
        }
        goldenLayoutRef.current = null;
      }
    };
  }, [isInitialized, selectedFITSPath, selectedTablePath]);

  return (
    <Box sx={{ height: 'calc(100vh - 64px)', width: '100%' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h5" gutterBottom>
          QA Visualization (CARTA Style)
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Drag panels to rearrange, resize, and customize your workspace
        </Typography>
      </Box>
      {error && (
        <Alert severity="error" sx={{ m: 2 }}>
          <strong>Error loading Golden Layout:</strong> {error}
          <br />
          Check browser console for details.
        </Alert>
      )}
      <Box
        ref={layoutRef}
        sx={{
          height: 'calc(100% - 100px)',
          width: '100%',
          position: 'relative',
        }}
      />
    </Box>
  );
}

