/**
 * CARTA Image Renderer
 *
 * Handles rendering of CARTA raster tiles to HTML5 canvas.
 * Supports image scaling, color mapping, and region overlays.
 */

import { logger } from "../../utils/logger";
import { RasterTileData, RasterTile, ImageBounds, Point } from "../../services/cartaProtobuf";

export interface RenderOptions {
  /** Color scale (linear, log, sqrt, etc.) */
  colorScale?: "linear" | "log" | "sqrt" | "asinh";
  /** Color map (e.g., "viridis", "gray", "hot", etc.) */
  colorMap?: string;
  /** Min/Max values for scaling */
  minValue?: number;
  maxValue?: number;
  /** Brightness adjustment */
  brightness?: number;
  /** Contrast adjustment */
  contrast?: number;
}

/**
 * CARTA Image Renderer
 */
export class CARTAImageRenderer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private imageData: ImageData | null = null;
  private tiles: Map<string, RasterTile> = new Map();
  private bounds: ImageBounds | null = null;
  private options: RenderOptions = {
    colorScale: "linear",
    colorMap: "gray",
    brightness: 1.0,
    contrast: 1.0,
  };

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Failed to get 2D rendering context");
    }
    this.ctx = context;
  }

  /**
   * Set render options
   */
  setOptions(options: Partial<RenderOptions>): void {
    this.options = { ...this.options, ...options };
    this.render();
  }

  /**
   * Update image bounds
   */
  setBounds(bounds: ImageBounds): void {
    this.bounds = bounds;
    this.resizeCanvas();
  }

  /**
   * Add or update a raster tile
   */
  async addTile(tile: RasterTile): Promise<void> {
    const key = `${tile.x}_${tile.y}_${tile.layer}`;
    this.tiles.set(key, tile);
    await this.render();
  }

  /**
   * Add multiple tiles from RasterTileData
   */
  async addTiles(tileData: RasterTileData): Promise<void> {
    if (tileData.imageBounds) {
      this.setBounds(tileData.imageBounds);
    }

    for (const tile of tileData.tiles) {
      await this.addTile(tile);
    }
  }

  /**
   * Clear all tiles
   */
  clear(): void {
    this.tiles.clear();
    this.bounds = null;
    this.imageData = null;
    this.ctx.fillStyle = "#1e1e1e";
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
  }

  /**
   * Resize canvas to match bounds
   */
  private resizeCanvas(): void {
    if (!this.bounds) {
      return;
    }

    const width = this.bounds.xMax - this.bounds.xMin;
    const height = this.bounds.yMax - this.bounds.yMin;

    // Set canvas size (maintain aspect ratio if needed)
    const container = this.canvas.parentElement;
    if (container) {
      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;

      // Calculate scale to fit container
      const scaleX = containerWidth / width;
      const scaleY = containerHeight / height;
      const scale = Math.min(scaleX, scaleY, 1); // Don't scale up

      this.canvas.width = width * scale;
      this.canvas.height = height * scale;
    } else {
      this.canvas.width = width;
      this.canvas.height = height;
    }
  }

  /**
   * Render tiles to canvas (async)
   */
  private async render(): Promise<void> {
    if (this.tiles.size === 0 || !this.bounds) {
      return;
    }

    const width = this.canvas.width;
    const height = this.canvas.height;

    // Create image data
    this.imageData = this.ctx.createImageData(width, height);

    // Render each tile (await all)
    const renderPromises = Array.from(this.tiles.values()).map((tile) => this.renderTile(tile));
    await Promise.all(renderPromises);

    // Apply color mapping and scaling
    this.applyColorMap();

    // Draw to canvas
    if (this.imageData) {
      this.ctx.putImageData(this.imageData, 0, 0);
    }
  }

  /**
   * Render a single tile (async)
   */
  private async renderTile(tile: RasterTile): Promise<void> {
    if (!this.imageData || !this.bounds) {
      return;
    }

    // Convert tile data to image
    const tileImage = await this.decodeTileData(tile);
    if (!tileImage) {
      return;
    }

    // Calculate position on canvas
    const scaleX = this.canvas.width / (this.bounds.xMax - this.bounds.xMin);
    const scaleY = this.canvas.height / (this.bounds.yMax - this.bounds.yMin);

    const canvasX = (tile.x - this.bounds.xMin) * scaleX;
    const canvasY = (tile.y - this.bounds.yMin) * scaleY;
    const canvasWidth = tile.width * scaleX;
    const canvasHeight = tile.height * scaleY;

    // Draw tile to image data
    for (let y = 0; y < tile.height && y + tile.y < this.bounds.yMax; y++) {
      for (let x = 0; x < tile.width && x + tile.x < this.bounds.xMax; x++) {
        const tileIndex = (y * tile.width + x) * 4;
        const r = tileImage[tileIndex];
        const g = tileImage[tileIndex + 1];
        const b = tileImage[tileIndex + 2];
        const a = tileImage[tileIndex + 3];

        const canvasXPos = Math.floor(canvasX + x * scaleX);
        const canvasYPos = Math.floor(canvasY + y * scaleY);

        if (
          canvasXPos >= 0 &&
          canvasXPos < this.canvas.width &&
          canvasYPos >= 0 &&
          canvasYPos < this.canvas.height
        ) {
          const canvasIndex = (canvasYPos * this.canvas.width + canvasXPos) * 4;
          this.imageData.data[canvasIndex] = r;
          this.imageData.data[canvasIndex + 1] = g;
          this.imageData.data[canvasIndex + 2] = b;
          this.imageData.data[canvasIndex + 3] = a;
        }
      }
    }
  }

  /**
   * Decode tile image data
   * Supports various compression types (JPEG, PNG, raw RGBA)
   * Note: For compressed formats, this returns a promise that resolves when decoding completes
   */
  private async decodeTileData(tile: RasterTile): Promise<Uint8Array | null> {
    try {
      let imageData: Uint8Array;

      if (tile.imageData instanceof ArrayBuffer) {
        imageData = new Uint8Array(tile.imageData);
      } else if (tile.imageData instanceof Uint8Array) {
        imageData = tile.imageData;
      } else {
        logger.warn("Unsupported tile image data type");
        return null;
      }

      // Check for compression type based on magic bytes
      // JPEG: FF D8 FF
      // PNG: 89 50 4E 47
      if (
        imageData.length >= 3 &&
        imageData[0] === 0xff &&
        imageData[1] === 0xd8 &&
        imageData[2] === 0xff
      ) {
        // JPEG compressed - decode using canvas
        return await this.decodeJPEG(imageData);
      } else if (
        imageData.length >= 4 &&
        imageData[0] === 0x89 &&
        imageData[1] === 0x50 &&
        imageData[2] === 0x4e &&
        imageData[3] === 0x47
      ) {
        // PNG compressed - decode using canvas
        return await this.decodePNG(imageData);
      } else {
        // Assume raw RGBA data
        return imageData;
      }
    } catch (error) {
      logger.error("Failed to decode tile data:", error);
      return null;
    }
  }

  /**
   * Decode JPEG image data (async)
   */
  private async decodeJPEG(jpegData: Uint8Array): Promise<Uint8Array | null> {
    try {
      // Create blob and load as image
      const blob = new Blob([jpegData], { type: "image/jpeg" });
      const url = URL.createObjectURL(blob);
      const img = new Image();

      return new Promise<Uint8Array | null>((resolve) => {
        img.onload = () => {
          // Create temporary canvas to extract pixel data
          const tempCanvas = document.createElement("canvas");
          tempCanvas.width = img.width;
          tempCanvas.height = img.height;
          const tempCtx = tempCanvas.getContext("2d");
          if (!tempCtx) {
            URL.revokeObjectURL(url);
            resolve(null);
            return;
          }

          tempCtx.drawImage(img, 0, 0);
          const imageData = tempCtx.getImageData(0, 0, img.width, img.height);
          URL.revokeObjectURL(url);
          resolve(new Uint8Array(imageData.data));
        };

        img.onerror = () => {
          URL.revokeObjectURL(url);
          logger.warn("Failed to decode JPEG image");
          resolve(null);
        };

        img.src = url;
      });
    } catch (error) {
      logger.error("Failed to decode JPEG:", error);
      return null;
    }
  }

  /**
   * Decode PNG image data (async)
   */
  private async decodePNG(pngData: Uint8Array): Promise<Uint8Array | null> {
    try {
      // Create blob and load as image
      const blob = new Blob([pngData], { type: "image/png" });
      const url = URL.createObjectURL(blob);
      const img = new Image();

      return new Promise<Uint8Array | null>((resolve) => {
        img.onload = () => {
          // Create temporary canvas to extract pixel data
          const tempCanvas = document.createElement("canvas");
          tempCanvas.width = img.width;
          tempCanvas.height = img.height;
          const tempCtx = tempCanvas.getContext("2d");
          if (!tempCtx) {
            URL.revokeObjectURL(url);
            resolve(null);
            return;
          }

          tempCtx.drawImage(img, 0, 0);
          const imageData = tempCtx.getImageData(0, 0, img.width, img.height);
          URL.revokeObjectURL(url);
          resolve(new Uint8Array(imageData.data));
        };

        img.onerror = () => {
          URL.revokeObjectURL(url);
          logger.warn("Failed to decode PNG image");
          resolve(null);
        };

        img.src = url;
      });
    } catch (error) {
      logger.error("Failed to decode PNG:", error);
      return null;
    }
  }

  /**
   * Apply color map and scaling to image data
   */
  private applyColorMap(): void {
    if (!this.imageData) {
      return;
    }

    const data = this.imageData.data;
    const { colorScale, colorMap, minValue, maxValue, brightness, contrast } = this.options;

    // Calculate min/max if not provided
    let min = minValue;
    let max = maxValue;
    if (min === undefined || max === undefined) {
      let dataMin = Infinity;
      let dataMax = -Infinity;
      for (let i = 0; i < data.length; i += 4) {
        const value = data[i]; // Use red channel as intensity
        if (value > 0) {
          dataMin = Math.min(dataMin, value);
          dataMax = Math.max(dataMax, value);
        }
      }
      min = minValue ?? dataMin;
      max = maxValue ?? dataMax;
    }

    // Apply scaling and color mapping
    for (let i = 0; i < data.length; i += 4) {
      let value = data[i] / 255.0; // Normalize to 0-1

      // Apply color scale
      if (colorScale === "log") {
        value = Math.log1p(value * (Math.E - 1));
      } else if (colorScale === "sqrt") {
        value = Math.sqrt(value);
      } else if (colorScale === "asinh") {
        value = Math.asinh(value * 10) / Math.asinh(10);
      }

      // Apply brightness and contrast
      value = (value - 0.5) * contrast + 0.5 + (brightness - 1.0) * 0.5;
      value = Math.max(0, Math.min(1, value));

      // Apply color map
      const color = this.getColorFromMap(value, colorMap || "gray");
      data[i] = color.r;
      data[i + 1] = color.g;
      data[i + 2] = color.b;
      // Alpha stays the same
    }
  }

  /**
   * Get color from color map
   */
  private getColorFromMap(value: number, colorMap: string): { r: number; g: number; b: number } {
    // Simple color map implementations
    switch (colorMap) {
      case "gray":
        const gray = Math.floor(value * 255);
        return { r: gray, g: gray, b: gray };
      case "hot":
        const hotR = Math.min(255, value * 3 * 255);
        const hotG = Math.min(255, Math.max(0, (value - 0.33) * 3 * 255));
        const hotB = Math.min(255, Math.max(0, (value - 0.66) * 3 * 255));
        return { r: hotR, g: hotG, b: hotB };
      case "viridis":
        // Simplified viridis approximation
        const viridisR = Math.floor(value * 255);
        const viridisG = Math.floor((1 - value) * 255);
        const viridisB = Math.floor(value * 255);
        return { r: viridisR, g: viridisG, b: viridisB };
      default:
        const gray2 = Math.floor(value * 255);
        return { r: gray2, g: gray2, b: gray2 };
    }
  }

  /**
   * Draw a region overlay
   */
  drawRegion(
    points: Point[],
    color: string = "#00ff00",
    lineWidth: number = 2,
    fill: boolean = false
  ): void {
    if (points.length === 0) {
      return;
    }

    this.ctx.strokeStyle = color;
    this.ctx.fillStyle = color + "40"; // Add transparency
    this.ctx.lineWidth = lineWidth;

    this.ctx.beginPath();
    this.ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      this.ctx.lineTo(points[i].x, points[i].y);
    }

    if (points.length > 2) {
      this.ctx.closePath();
      if (fill) {
        this.ctx.fill();
      }
    }

    this.ctx.stroke();
  }

  /**
   * Clear region overlays (re-render base image)
   */
  clearRegions(): void {
    this.render();
  }
}
