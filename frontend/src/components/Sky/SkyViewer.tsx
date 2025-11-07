/**
 * SkyViewer Component - JS9 FITS Image Viewer Integration
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Box, CircularProgress, Alert, Typography } from '@mui/material';

declare global {
  interface Window {
    JS9: any;
  }
}

interface SkyViewerProps {
  imagePath: string | null;
  displayId?: string;
  height?: number;
}

export default function SkyViewer({ 
  imagePath, 
  displayId = 'js9Display',
  height = 600 
}: SkyViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imageLoadedRef = useRef(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  // Initialize JS9 display (only once)
  useEffect(() => {
    if (!containerRef.current) return;
    
    // Check if JS9 display already exists for this div
    if (window.JS9) {
      const existingDisplay = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });
      if (existingDisplay) {
        console.debug('JS9 display already exists for:', displayId);
        setInitialized(true);
        return;
      }
      
      // Disable JS9's internal loading indicator to avoid duplicate spinners
      try {
        // Try multiple methods to disable JS9's loading indicator
        if (typeof window.JS9.SetOptions === 'function') {
          window.JS9.SetOptions({ loadImage: false });
        }
        // Also try setting it as a global option
        if (window.JS9.opts) {
          window.JS9.opts.loadImage = false;
        }
        // Hide JS9's loading indicator via CSS if it exists
        const js9LoadingElements = document.querySelectorAll('.JS9Loading, .js9-loading, [class*="js9"][class*="load"]');
        js9LoadingElements.forEach((el: any) => {
          if (el.style) {
            el.style.display = 'none';
          }
        });
      } catch (e) {
        console.debug('Could not disable JS9 loading indicator:', e);
      }
    }
    
    if (initialized) return;

    // Wait for JS9 to be available
    if (!window.JS9) {
      // JS9 might not be loaded yet, wait a bit
      const checkJS9 = setInterval(() => {
        if (window.JS9) {
          clearInterval(checkJS9);
          // Check again if display exists
          const existingDisplay = window.JS9.displays?.find((d: any) => {
            const divId = d.id || d.display || d.divID;
            return divId === displayId;
          });
          if (!existingDisplay) {
            initializeJS9();
          } else {
            setInitialized(true);
          }
        }
      }, 100);

      return () => clearInterval(checkJS9);
    }

    initializeJS9();

    function initializeJS9() {
      try {
        if (!containerRef.current) return;
        
        // Ensure div has the correct ID for JS9
        if (containerRef.current.id !== displayId) {
          containerRef.current.id = displayId;
        }
        
        // Wait for div to have proper dimensions before initializing JS9
        const checkDimensions = setInterval(() => {
          if (containerRef.current) {
            const rect = containerRef.current.getBoundingClientRect();
            // Ensure div has minimum dimensions (at least 100px width, 100px height)
            if (rect.width >= 100 && rect.height >= 100) {
              clearInterval(checkDimensions);
              doInitialize();
            }
          }
        }, 100);
        
        // Timeout after 5 seconds
        setTimeout(() => {
          clearInterval(checkDimensions);
          // Try to initialize anyway
          doInitialize();
        }, 5000);
        
        function doInitialize() {
          if (!containerRef.current) return;
          
          // Ensure div has explicit dimensions
          const rect = containerRef.current.getBoundingClientRect();
          if (rect.width < 100) {
            containerRef.current.style.width = '100%';
            containerRef.current.style.minWidth = '400px';
          }
          if (rect.height < 100) {
            containerRef.current.style.height = `${height}px`;
          }
          
                 // Initialize JS9 globally if needed (only once)
                 if (typeof window.JS9.Init === 'function') {
                   try {
                     // Initialize with loadImage disabled to prevent duplicate spinners
                     window.JS9.Init({ loadImage: false });
                   } catch (initErr) {
                     // JS9 may already be initialized, try to set options instead
                     try {
                       if (typeof window.JS9.SetOptions === 'function') {
                         window.JS9.SetOptions({ loadImage: false });
                       }
                     } catch (optErr) {
                       console.debug('JS9 Init and SetOptions failed:', initErr, optErr);
                     }
                   }
                 }
          
          // Register the div with JS9 using AddDivs
          // This tells JS9 about the div so it can create a display when loading images
          if (typeof window.JS9.AddDivs === 'function') {
            try {
              window.JS9.AddDivs(displayId);
              console.debug('JS9 div registered:', displayId);
            } catch (addDivsErr) {
              console.debug('JS9 AddDivs:', addDivsErr);
              // Continue anyway - JS9 might auto-detect the div
            }
          }
          
          setInitialized(true);
        }
      } catch (err) {
        console.error('JS9 initialization error:', err);
        setError('Failed to initialize JS9 display');
      }
    }
  }, [displayId, height]); // Removed 'initialized' from deps to prevent re-initialization

  // Preserve JS9 content after React renders using useLayoutEffect
  // Only restore if we're not currently loading a new image
  useLayoutEffect(() => {
    if (!containerRef.current || !initialized || !window.JS9 || !imageLoadedRef.current || loading) return;
    
    const div = containerRef.current;
    const display = window.JS9.displays?.find((d: any) => {
      const divId = d.id || d.display || d.divID;
      return divId === displayId;
    });
    
    // If JS9 has an image loaded but the div is empty, restore it
    // Only restore if we have a valid image and we're not loading a new one
    if (display && display.im && div.children.length === 0 && imagePath) {
      console.debug('Restoring JS9 display after React render');
      // Use requestAnimationFrame to ensure this happens after React's render
      requestAnimationFrame(() => {
        try {
          // Reload the image into the display using the current imagePath
          // This ensures we restore the correct image, not an old one
          if (imagePath) {
            window.JS9.Load(imagePath, { divID: displayId });
          }
        } catch (e) {
          console.debug('Failed to restore JS9 display:', e);
        }
      });
    }
  }, [displayId, initialized, loading, imagePath]);

  // Monitor div for React clearing JS9 content and restore if needed
  useEffect(() => {
    if (!containerRef.current || !initialized || !window.JS9) return;
    
    const div = containerRef.current;
    
    const observer = new MutationObserver(() => {
      // If React cleared the content but JS9 has an image loaded, restore it
      // Only restore if we're not currently loading a new image
      if (div.children.length === 0 && imageLoadedRef.current && !loading && window.JS9 && imagePath) {
        const display = window.JS9.displays?.find((d: any) => {
          const divId = d.id || d.display || d.divID;
          return divId === displayId;
        });
        if (display && display.im) {
          console.debug('React cleared JS9 content, restoring...');
          // Force JS9 to redraw using the current imagePath to ensure we restore the correct image
          setTimeout(() => {
            try {
              if (imagePath) {
                window.JS9.Load(imagePath, { divID: displayId });
              }
            } catch (e) {
              console.debug('Failed to restore JS9 display:', e);
            }
          }, 100);
        }
      }
    });
    
    observer.observe(div, {
      childList: true,
      subtree: true,
      attributes: false,
    });
    
    return () => observer.disconnect();
  }, [displayId, initialized, loading, imagePath]);

  // Load image when path changes
  useEffect(() => {
    if (!imagePath || !initialized || !window.JS9) {
      // Reset state when imagePath is cleared
      if (!imagePath) {
        imageLoadedRef.current = false;
        setLoading(false);
        setError(null);
      }
      return;
    }

    setLoading(true);
    setError(null);
    imageLoadedRef.current = false;

    // Define variables outside try/catch so they're accessible everywhere
    let hideInterval: NodeJS.Timeout | null = null;
    let observer: MutationObserver | null = null;
    let targetDiv: HTMLElement | null = null;
    
    const hideJS9Loading = () => {
        // Try multiple selectors to catch JS9 loading indicators
        const selectors = [
          '.JS9Loading',
          '.js9-loading',
          '[class*="js9"][class*="load"]',
          '[id*="js9"][id*="load"]',
          '[class*="JS9"][class*="Load"]',
          'div[class*="spinner"]',
          'div[class*="loader"]',
          'div[class*="loading"]',
          '.JS9 div[style*="spinner"]',
          '.JS9 div[style*="loader"]',
          '.JS9 div[style*="loading"]',
        ];
        
        selectors.forEach(selector => {
          try {
            const elements = document.querySelectorAll(selector);
            elements.forEach((el: any) => {
              if (el && el.style) {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.style.opacity = '0';
                el.style.pointerEvents = 'none';
              }
            });
          } catch (e) {
            // Ignore selector errors
          }
        });
        
        // Also check inside the target div specifically - hide ANY element that might be a spinner
        if (targetDiv) {
          const allChildren = targetDiv.querySelectorAll('*');
          allChildren.forEach((el: any) => {
            if (el && el.style) {
              const className = (el.className || '').toString();
              const id = (el.id || '').toString();
              const style = el.getAttribute('style') || '';
              const tagName = (el.tagName || '').toLowerCase();
              
              // Check if this looks like a loading indicator
              const isSpinner = 
                className.toLowerCase().includes('load') ||
                className.toLowerCase().includes('spinner') ||
                className.toLowerCase().includes('loader') ||
                id.toLowerCase().includes('load') ||
                id.toLowerCase().includes('spinner') ||
                style.toLowerCase().includes('spinner') ||
                style.toLowerCase().includes('loader') ||
                style.toLowerCase().includes('rotate') ||
                // Check for animated elements (common in spinners)
                (el.getAttribute('class') && el.getAttribute('class').includes('animate')) ||
                // Check for SVG spinners
                (tagName === 'svg' && (className.includes('spin') || id.includes('spin'))) ||
                // Check for circular/rotating elements
                (style.includes('animation') && (style.includes('spin') || style.includes('rotate')));
              
              if (isSpinner) {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.style.opacity = '0';
                el.style.pointerEvents = 'none';
              }
            }
          });
          
          // Also hide any direct children that are not the canvas (JS9 uses canvas for images)
          // If there's a div that's not a canvas and not our loading box, it might be JS9's spinner
          Array.from(targetDiv.children).forEach((child: any) => {
            if (child && child.tagName && child.tagName.toLowerCase() !== 'canvas') {
              // Check if it's not our React loading box
              const isOurSpinner = child.querySelector && child.querySelector('.MuiCircularProgress-root');
              if (!isOurSpinner && child.style) {
                // This might be JS9's spinner - hide it
                const rect = child.getBoundingClientRect();
                // If it's a small element in the center, it's likely a spinner
                if (rect.width < 100 && rect.height < 100) {
                  child.style.display = 'none';
                  child.style.visibility = 'hidden';
                  child.style.opacity = '0';
                }
              }
            }
          });
        }
      };
    
    // Cleanup interval and observer when loading completes
    const cleanupInterval = () => {
      if (hideInterval) {
        clearInterval(hideInterval);
        hideInterval = null;
      }
      if (observer) {
        observer.disconnect();
        observer = null;
      }
    };
    
    try {
      // Load image into JS9 display
      // Ensure the div exists and is visible before loading
      targetDiv = document.getElementById(displayId);
      if (!targetDiv) {
        setError(`Display div with id "${displayId}" not found`);
        setLoading(false);
        return;
      }
      
      // Hide immediately and set up interval to catch dynamically created elements
      hideJS9Loading();
      hideInterval = setInterval(hideJS9Loading, 50); // Check more frequently
      
      // Also use MutationObserver to catch elements as they're added
      observer = new MutationObserver(() => {
        hideJS9Loading();
      });
      
      if (targetDiv) {
        observer.observe(targetDiv, {
          childList: true,
          subtree: true,
          attributes: true,
          attributeFilter: ['class', 'id', 'style'],
        });
      }

      // Clear any existing image from the display before loading a new one
      const display = window.JS9.displays?.find((d: any) => {
        const divId = d.id || d.display || d.divID;
        return divId === displayId;
      });
      
      if (display && display.im) {
        // Close the existing image to clear the display
        try {
          const oldImageId = display.im.id;
          window.JS9.CloseImage(oldImageId);
          // Also try to remove the image from JS9's internal cache
          if (window.JS9.images && window.JS9.images[oldImageId]) {
            delete window.JS9.images[oldImageId];
          }
        } catch (e) {
          // Ignore errors when closing - image might not exist
          console.debug('Error closing previous image:', e);
        }
      }
      
      // Don't clear the div - JS9 manages its own DOM
      // Clearing can interfere with JS9's canvas rendering
      
      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      
      // Small delay to ensure any previous operations complete
      const loadTimeout = setTimeout(() => {
        // Double-check that imagePath hasn't changed (component might have unmounted or path changed)
        if (!imagePath || !window.JS9) {
          setLoading(false);
          return;
        }
        
        // Add a cache-busting parameter to ensure JS9 treats this as a new image
        // This prevents JS9 from using a cached version of a previously loaded image
        const cacheBuster = `?t=${Date.now()}`;
        const imageUrlWithCacheBuster = imagePath.includes('?') 
          ? `${imagePath}&_cb=${Date.now()}`
          : `${imagePath}${cacheBuster}`;
        
        // Close any existing image in this display first
        const existingDisplay = window.JS9.displays?.find((d: any) => {
          const divId = d.id || d.display || d.divID;
          return divId === displayId;
        });
        
        if (existingDisplay && existingDisplay.im) {
          try {
            window.JS9.CloseImage(existingDisplay.im.id);
          } catch (e) {
            console.debug('Error closing existing image:', e);
          }
        }
        
        // JS9.Load with divID should automatically create a display in that div
        // Use a small delay after closing to ensure cleanup
        timeoutRef.current = setTimeout(() => {
          if (!imagePath || !window.JS9) {
            setLoading(false);
            return;
          }
          
          try {
            window.JS9.Load(imageUrlWithCacheBuster, {
              divID: displayId,
              scale: 'linear',
              colormap: 'grey',
              onload: (im: any) => {
                console.log('FITS image loaded:', im, 'Display:', displayId);
                imageLoadedRef.current = true;
                setLoading(false);
                cleanupInterval();
                hideJS9Loading();
                // Force JS9 to display the image in the correct div
                try {
                  // Use SetDisplay to ensure the image is shown in the correct display
                  if (typeof window.JS9.SetDisplay === 'function') {
                    window.JS9.SetDisplay(displayId, im.id);
                  }
                  // Verify the image is in the correct display
                  const display = window.JS9.displays?.find((d: any) => {
                    const divId = d.id || d.display || d.divID;
                    return divId === displayId;
                  });
                  if (display && display.im && display.im.id === im.id) {
                    console.log('Image confirmed in display:', displayId);
                  } else {
                    console.warn('Image loaded but not in expected display, attempting to fix...');
                    // Try to move the image to the correct display
                    if (typeof window.JS9.SetDisplay === 'function') {
                      window.JS9.SetDisplay(displayId, im.id);
                    }
                  }
                } catch (e) {
                  console.debug('Error verifying display:', e);
                }
              },
              onerror: (err: any) => {
                console.error('JS9 load error:', err);
                setError(`Failed to load image: ${err.message || 'Unknown error'}`);
                setLoading(false);
                imageLoadedRef.current = false;
                cleanupInterval();
                hideJS9Loading();
              },
            });
          } catch (loadErr: any) {
            // If divID doesn't work, try without specifying display
            console.warn('JS9.Load with divID failed, trying without display parameter:', loadErr);
            try {
              window.JS9.Load(imageUrlWithCacheBuster, {
                scale: 'linear',
                colormap: 'grey',
                onload: (im: any) => {
                  console.log('FITS image loaded (fallback):', im);
                  imageLoadedRef.current = true;
                  setLoading(false);
                  cleanupInterval();
                  hideJS9Loading();
                  // Try to move to correct display after loading
                  try {
                    if (typeof window.JS9.SetDisplay === 'function') {
                      window.JS9.SetDisplay(displayId, im.id);
                    }
                  } catch (e) {
                    console.debug('Error setting display (fallback):', e);
                  }
                },
                onerror: (err: any) => {
                  console.error('JS9 load error (fallback):', err);
                  setError(`Failed to load image: ${err.message || 'Unknown error'}`);
                  setLoading(false);
                  imageLoadedRef.current = false;
                  cleanupInterval();
                  hideJS9Loading();
                },
              });
            } catch (fallbackErr: any) {
              setError(`Failed to load image: ${fallbackErr.message || 'Unknown error'}`);
              setLoading(false);
              imageLoadedRef.current = false;
              cleanupInterval();
              hideJS9Loading();
            }
          }
        }, 100); // Small delay after closing to ensure cleanup
      }, 50); // Small delay to ensure cleanup completes
      
      // Cleanup function to cancel timeout if imagePath changes or component unmounts
      return () => {
        clearTimeout(loadTimeout);
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        cleanupInterval();
        hideJS9Loading();
      };
    } catch (err: any) {
      console.error('Error loading image:', err);
      setError(`Error: ${err.message || 'Unknown error'}`);
      setLoading(false);
      imageLoadedRef.current = false;
      cleanupInterval();
      hideJS9Loading();
    }
  }, [imagePath, displayId, initialized]);

  return (
    <Box sx={{ position: 'relative', width: '100%', height: `${height}px` }}>
      <Box
        key={displayId}
        id={displayId}
        ref={containerRef}
        component="div"
        sx={{
          width: '100%',
          minWidth: '400px',
          height: `${height}px`,
          minHeight: `${height}px`,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          bgcolor: '#0a0a0a',
          position: 'relative',
          display: 'block',
          boxSizing: 'border-box',
          overflow: 'hidden',
        }}
        // Prevent React from clearing JS9 content on re-render
        onMouseEnter={() => {
          // Force JS9 to redraw if content was cleared
          if (imageLoadedRef.current && window.JS9) {
            const display = window.JS9.displays?.find((d: any) => d.id === displayId || d.display === displayId);
            if (display && display.im) {
              // Image is loaded, ensure it's displayed
              try {
                window.JS9.Load(display.im.id, { display: displayId });
              } catch (e) {
                // Ignore errors
              }
            }
          }
        }}
      />
      
      {loading && !imageLoadedRef.current && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            zIndex: 1000,
            pointerEvents: 'none',
            '& + *': {
              // Hide any JS9 loading indicators that might appear
              '& .JS9Loading, & .js9-loading, & [class*="js9"][class*="load"]': {
                display: 'none !important',
              },
            },
          }}
        >
          <CircularProgress />
          <Typography variant="body2" color="text.secondary">
            Loading image...
          </Typography>
        </Box>
      )}
      
      {/* Hidden style tag to globally hide JS9 loading indicators */}
      <style>{`
        .JS9Loading,
        .js9-loading,
        [class*="js9"][class*="load"],
        [id*="js9"][id*="load"],
        .JS9 div[class*="load"],
        .JS9 div[id*="load"],
        .JS9 div[class*="spinner"],
        .JS9 div[class*="loader"],
        .JS9 div[style*="spinner"],
        .JS9 div[style*="loader"],
        #${displayId} div[class*="load"],
        #${displayId} div[class*="spinner"],
        #${displayId} div[class*="loader"],
        #${displayId} div[style*="spinner"],
        #${displayId} div[style*="loader"] {
          display: none !important;
          visibility: hidden !important;
          opacity: 0 !important;
          pointer-events: none !important;
        }
      `}</style>

      {error && (
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            left: 16,
            right: 16,
          }}
        >
          <Alert severity="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        </Box>
      )}

      {!imagePath && !loading && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            color: 'text.secondary',
          }}
        >
          <Typography variant="h6" gutterBottom>
            No image selected
          </Typography>
          <Typography variant="body2">
            Select an image from the browser to display
          </Typography>
        </Box>
      )}
    </Box>
  );
}

