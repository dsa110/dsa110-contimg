/**
 * CARTA Zoom and Pan Controller
 *
 * Handles zoom and pan interactions for the CARTA canvas viewer.
 */

export interface ZoomPanState {
  scale: number;
  offsetX: number;
  offsetY: number;
  minScale: number;
  maxScale: number;
}

export class CARTAZoomPan {
  private state: ZoomPanState;
  private canvas: HTMLCanvasElement;
  private isPanning: boolean = false;
  private lastPanX: number = 0;
  private lastPanY: number = 0;
  private onStateChange?: (state: ZoomPanState) => void;

  constructor(
    canvas: HTMLCanvasElement,
    initialState?: Partial<ZoomPanState>,
    onStateChange?: (state: ZoomPanState) => void
  ) {
    this.canvas = canvas;
    this.onStateChange = onStateChange;
    this.state = {
      scale: initialState?.scale ?? 1.0,
      offsetX: initialState?.offsetX ?? 0,
      offsetY: initialState?.offsetY ?? 0,
      minScale: initialState?.minScale ?? 0.1,
      maxScale: initialState?.maxScale ?? 10.0,
    };

    this.setupEventListeners();
  }

  /**
   * Setup mouse and touch event listeners
   */
  private setupEventListeners(): void {
    // Mouse events
    this.canvas.addEventListener("mousedown", this.handleMouseDown.bind(this));
    this.canvas.addEventListener("mousemove", this.handleMouseMove.bind(this));
    this.canvas.addEventListener("mouseup", this.handleMouseUp.bind(this));
    this.canvas.addEventListener("mouseleave", this.handleMouseUp.bind(this));
    this.canvas.addEventListener("wheel", this.handleWheel.bind(this));

    // Touch events
    this.canvas.addEventListener("touchstart", this.handleTouchStart.bind(this));
    this.canvas.addEventListener("touchmove", this.handleTouchMove.bind(this));
    this.canvas.addEventListener("touchend", this.handleTouchEnd.bind(this));

    // Prevent context menu on right click
    this.canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  }

  /**
   * Handle mouse down (start panning)
   */
  private handleMouseDown(e: MouseEvent): void {
    if (e.button === 0) {
      // Left mouse button
      this.isPanning = true;
      this.lastPanX = e.clientX;
      this.lastPanY = e.clientY;
      this.canvas.style.cursor = "grabbing";
    }
  }

  /**
   * Handle mouse move (panning)
   */
  private handleMouseMove(e: MouseEvent): void {
    if (this.isPanning) {
      const deltaX = e.clientX - this.lastPanX;
      const deltaY = e.clientY - this.lastPanY;

      this.state.offsetX += deltaX;
      this.state.offsetY += deltaY;

      this.lastPanX = e.clientX;
      this.lastPanY = e.clientY;

      this.notifyStateChange();
    }
  }

  /**
   * Handle mouse up (stop panning)
   */
  private handleMouseUp(): void {
    this.isPanning = false;
    this.canvas.style.cursor = "grab";
  }

  /**
   * Handle mouse wheel (zooming)
   */
  private handleWheel(e: WheelEvent): void {
    e.preventDefault();

    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Calculate zoom factor
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(
      this.state.minScale,
      Math.min(this.state.maxScale, this.state.scale * zoomFactor)
    );

    if (newScale !== this.state.scale) {
      // Zoom towards mouse position
      const scaleChange = newScale / this.state.scale;
      this.state.offsetX = mouseX - (mouseX - this.state.offsetX) * scaleChange;
      this.state.offsetY = mouseY - (mouseY - this.state.offsetY) * scaleChange;
      this.state.scale = newScale;

      this.notifyStateChange();
    }
  }

  /**
   * Handle touch start
   */
  private handleTouchStart(e: TouchEvent): void {
    if (e.touches.length === 1) {
      this.isPanning = true;
      this.lastPanX = e.touches[0].clientX;
      this.lastPanY = e.touches[0].clientY;
    }
  }

  /**
   * Handle touch move
   */
  private handleTouchMove(e: TouchEvent): void {
    if (e.touches.length === 1 && this.isPanning) {
      const deltaX = e.touches[0].clientX - this.lastPanX;
      const deltaY = e.touches[0].clientY - this.lastPanY;

      this.state.offsetX += deltaX;
      this.state.offsetY += deltaY;

      this.lastPanX = e.touches[0].clientX;
      this.lastPanY = e.touches[0].clientY;

      this.notifyStateChange();
    } else if (e.touches.length === 2) {
      // Pinch to zoom
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];

      const distance = Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY);

      // Store initial distance on first two-finger touch
      if (!this.lastPanX) {
        this.lastPanX = distance;
        return;
      }

      const scaleChange = distance / this.lastPanX;
      const newScale = Math.max(
        this.state.minScale,
        Math.min(this.state.maxScale, this.state.scale * scaleChange)
      );

      if (newScale !== this.state.scale) {
        this.state.scale = newScale;
        this.notifyStateChange();
      }

      this.lastPanX = distance;
    }
  }

  /**
   * Handle touch end
   */
  private handleTouchEnd(): void {
    this.isPanning = false;
    this.lastPanX = 0;
    this.lastPanY = 0;
  }

  /**
   * Zoom in
   */
  zoomIn(factor: number = 1.2): void {
    this.zoom(factor);
  }

  /**
   * Zoom out
   */
  zoomOut(factor: number = 0.8): void {
    this.zoom(factor);
  }

  /**
   * Zoom to specific scale
   */
  zoom(factor: number): void {
    const newScale = Math.max(
      this.state.minScale,
      Math.min(this.state.maxScale, this.state.scale * factor)
    );

    if (newScale !== this.state.scale) {
      // Zoom towards center
      const centerX = this.canvas.width / 2;
      const centerY = this.canvas.height / 2;
      const scaleChange = newScale / this.state.scale;
      this.state.offsetX = centerX - (centerX - this.state.offsetX) * scaleChange;
      this.state.offsetY = centerY - (centerY - this.state.offsetY) * scaleChange;
      this.state.scale = newScale;

      this.notifyStateChange();
    }
  }

  /**
   * Reset zoom and pan
   */
  reset(): void {
    this.state.scale = 1.0;
    this.state.offsetX = 0;
    this.state.offsetY = 0;
    this.notifyStateChange();
  }

  /**
   * Fit to canvas
   */
  fitToCanvas(imageWidth: number, imageHeight: number): void {
    const canvasWidth = this.canvas.width;
    const canvasHeight = this.canvas.height;

    const scaleX = canvasWidth / imageWidth;
    const scaleY = canvasHeight / imageHeight;
    const scale = Math.min(scaleX, scaleY);

    this.state.scale = scale;
    this.state.offsetX = (canvasWidth - imageWidth * scale) / 2;
    this.state.offsetY = (canvasHeight - imageHeight * scale) / 2;

    this.notifyStateChange();
  }

  /**
   * Get current state
   */
  getState(): ZoomPanState {
    return { ...this.state };
  }

  /**
   * Set state
   */
  setState(state: Partial<ZoomPanState>): void {
    this.state = { ...this.state, ...state };
    this.notifyStateChange();
  }

  /**
   * Apply transform to canvas context
   */
  applyTransform(ctx: CanvasRenderingContext2D): void {
    ctx.save();
    ctx.translate(this.state.offsetX, this.state.offsetY);
    ctx.scale(this.state.scale, this.state.scale);
  }

  /**
   * Restore canvas context
   */
  restoreTransform(ctx: CanvasRenderingContext2D): void {
    ctx.restore();
  }

  /**
   * Convert screen coordinates to image coordinates
   */
  screenToImage(screenX: number, screenY: number): { x: number; y: number } {
    const imageX = (screenX - this.state.offsetX) / this.state.scale;
    const imageY = (screenY - this.state.offsetY) / this.state.scale;
    return { x: imageX, y: imageY };
  }

  /**
   * Convert image coordinates to screen coordinates
   */
  imageToScreen(imageX: number, imageY: number): { x: number; y: number } {
    const screenX = imageX * this.state.scale + this.state.offsetX;
    const screenY = imageY * this.state.scale + this.state.offsetY;
    return { x: screenX, y: screenY };
  }

  /**
   * Notify state change
   */
  private notifyStateChange(): void {
    if (this.onStateChange) {
      this.onStateChange(this.getState());
    }
  }

  /**
   * Cleanup event listeners
   */
  destroy(): void {
    // Event listeners will be cleaned up when canvas is removed
    // But we can explicitly remove them if needed
    this.isPanning = false;
  }
}
