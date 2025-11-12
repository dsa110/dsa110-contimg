// Mermaid diagram zoom functionality
(function() {
    'use strict';
    
    // Wait for Mermaid diagrams to render
    function initZoom() {
        // Find all Mermaid containers
        const mermaidContainers = document.querySelectorAll('.mermaid');
        
        mermaidContainers.forEach(function(container) {
            // Skip if already initialized
            if (container.dataset.zoomInitialized === 'true') {
                return;
            }
            
            const svg = container.querySelector('svg');
            if (!svg || svg.tagName !== 'svg') {
                return;
            }
            
            // Mark as initialized
            container.dataset.zoomInitialized = 'true';
            
            // Create zoom wrapper
            const wrapper = document.createElement('div');
            wrapper.style.cssText = 'overflow: auto; max-width: 100%; max-height: 80vh; border: 1px solid #ddd; border-radius: 4px; padding: 10px; background: #fafafa; position: relative;';
            wrapper.className = 'mermaid-zoom-wrapper';
            
            // Store original transform
            let currentScale = 1;
            const minScale = 0.5;
            const maxScale = 3.0;
            const scaleStep = 0.2;
            
            // Create inner container for scaling
            const innerWrapper = document.createElement('div');
            innerWrapper.style.cssText = 'display: inline-block; transform-origin: top left; transition: transform 0.2s ease;';
            innerWrapper.appendChild(svg.cloneNode(true));
            
            // Remove original SVG
            svg.remove();
            
            // Wrap the inner container
            wrapper.appendChild(innerWrapper);
            
            // Insert wrapper before container, then move container content
            container.parentNode.insertBefore(wrapper, container);
            container.style.display = 'none';
            
            // Zoom functions
            function zoomIn() {
                if (currentScale < maxScale) {
                    currentScale = Math.min(currentScale + scaleStep, maxScale);
                    innerWrapper.style.transform = 'scale(' + currentScale + ')';
                    updateControls();
                }
            }
            
            function zoomOut() {
                if (currentScale > minScale) {
                    currentScale = Math.max(currentScale - scaleStep, minScale);
                    innerWrapper.style.transform = 'scale(' + currentScale + ')';
                    updateControls();
                }
            }
            
            function resetZoom() {
                currentScale = 1;
                innerWrapper.style.transform = 'scale(1)';
                wrapper.scrollTo({left: 0, top: 0, behavior: 'smooth'});
                updateControls();
            }
            
            function updateControls() {
                zoomInBtn.disabled = currentScale >= maxScale;
                zoomOutBtn.disabled = currentScale <= minScale;
                scaleDisplay.textContent = Math.round(currentScale * 100) + '%';
            }
            
            // Add zoom controls
            const controls = document.createElement('div');
            controls.style.cssText = 'text-align: center; margin-top: 8px; padding: 5px; background: white; border-top: 1px solid #ddd; font-size: 12px; color: #666; display: flex; justify-content: center; align-items: center; gap: 10px;';
            
            const zoomOutBtn = document.createElement('button');
            zoomOutBtn.textContent = '−';
            zoomOutBtn.style.cssText = 'cursor: pointer; padding: 4px 8px; border: 1px solid #ccc; background: white; border-radius: 3px; font-size: 16px;';
            zoomOutBtn.onclick = zoomOut;
            
            const scaleDisplay = document.createElement('span');
            scaleDisplay.textContent = '100%';
            scaleDisplay.style.cssText = 'min-width: 50px; font-weight: bold;';
            
            const zoomInBtn = document.createElement('button');
            zoomInBtn.textContent = '+';
            zoomInBtn.style.cssText = 'cursor: pointer; padding: 4px 8px; border: 1px solid #ccc; background: white; border-radius: 3px; font-size: 16px;';
            zoomInBtn.onclick = zoomIn;
            
            const resetBtn = document.createElement('button');
            resetBtn.textContent = 'Reset';
            resetBtn.style.cssText = 'cursor: pointer; padding: 4px 8px; border: 1px solid #ccc; background: white; border-radius: 3px; font-size: 12px; margin-left: 10px;';
            resetBtn.onclick = resetZoom;
            
            controls.appendChild(zoomOutBtn);
            controls.appendChild(scaleDisplay);
            controls.appendChild(zoomInBtn);
            controls.appendChild(resetBtn);
            wrapper.appendChild(controls);
            
            updateControls();
        });
    }
    
    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initZoom);
    } else {
        initZoom();
    }
    
    // Re-initialize after Mermaid renders (with delay for async rendering)
    setTimeout(initZoom, 1000);
    setTimeout(initZoom, 3000);
    setTimeout(initZoom, 5000);
    
    // Watch for new Mermaid diagrams (for dynamic content)
    const observer = new MutationObserver(function(mutations) {
        let shouldReinit = false;
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && (node.classList && node.classList.contains('mermaid') || node.querySelector && node.querySelector('.mermaid'))) {
                        shouldReinit = true;
                    }
                });
            }
        });
        if (shouldReinit) {
            setTimeout(initZoom, 500);
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
})();

