/**
 * CARTA WebSocket Client - Option 2: Full WebSocket integration
 *
 * This client connects to CARTA backend via WebSocket using Protocol Buffers.
 * Provides full integration with the dashboard while leveraging CARTA's
 * powerful visualization capabilities.
 */

import { logger } from "../utils/logger";

export interface CARTAConfig {
  /** CARTA backend WebSocket URL (e.g., "ws://localhost:9002") */
  backendUrl: string;
  /** Optional session ID for reconnection */
  sessionId?: string;
  /** Client feature flags */
  clientFeatureFlags?: Record<string, boolean>;
}

export interface CARTAFileInfo {
  name: string;
  directory: string;
  size: number;
  hduList: string[];
}

export interface CARTARegion {
  id: string;
  type: "point" | "line" | "polygon" | "ellipse" | "rectangle";
  controlPoints: Array<{ x: number; y: number }>;
}

export type CARTAMessageType =
  | "REGISTER_VIEWER"
  | "OPEN_FILE"
  | "SET_IMAGE_VIEW"
  | "SET_REGION"
  | "FILE_INFO"
  | "REGISTER_VIEWER_ACK"
  | "OPEN_FILE_ACK";

export type CARTAMessageHandler = (message: any) => void;

/**
 * CARTA WebSocket Client
 *
 * Connects to CARTA backend and handles Protocol Buffer message encoding/decoding.
 * Note: Full implementation requires CARTA protobuf definitions.
 */
export class CARTAClient {
  private config: CARTAConfig;
  private ws: WebSocket | null = null;
  private messageHandlers: Map<CARTAMessageType, Set<CARTAMessageHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectInterval = 3000;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isConnected = false;
  private sessionId: string | null = null;

  constructor(config: CARTAConfig) {
    this.config = config;
    this.sessionId = config.sessionId || null;
  }

  /**
   * Connect to CARTA backend
   */
  async connect(): Promise<void> {
    if (this.isConnecting || this.isConnected) {
      logger.warn("CARTA client already connecting or connected");
      return;
    }

    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        const wsUrl = this.config.backendUrl.replace(/^http/, "ws");
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          logger.info("CARTA WebSocket connected");
          this.isConnecting = false;
          this.isConnected = true;
          this.reconnectAttempts = 0;

          // Register viewer with CARTA backend
          this.registerViewer()
            .then(() => {
              resolve();
            })
            .catch(reject);
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onerror = (error) => {
          logger.error("CARTA WebSocket error:", error);
          this.isConnecting = false;
          if (!this.isConnected) {
            reject(new Error("WebSocket connection failed"));
          }
        };

        this.ws.onclose = () => {
          logger.info("CARTA WebSocket closed");
          this.isConnected = false;
          this.isConnecting = false;

          // Attempt reconnection if not manually closed
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };
      } catch (error) {
        this.isConnecting = false;
        logger.error("Failed to create CARTA WebSocket:", error);
        reject(error);
      }
    });
  }

  /**
   * Register viewer with CARTA backend
   * This is the first message sent after connection
   */
  private async registerViewer(): Promise<void> {
    // TODO: Implement Protocol Buffer message encoding
    // This requires CARTA's protobuf definitions
    // For now, we'll use a placeholder structure

    const message = {
      type: "REGISTER_VIEWER",
      sessionId: this.sessionId || "",
      clientFeatureFlags: this.config.clientFeatureFlags || {},
    };

    logger.info("Registering CARTA viewer", message);
    // await this.sendMessage(message);
  }

  /**
   * Open a FITS file in CARTA
   */
  async openFile(filePath: string, fileId: number = 0, hdu: string = ""): Promise<void> {
    if (!this.isConnected) {
      throw new Error("CARTA client not connected");
    }

    const directory = this.getDirectory(filePath);
    const filename = this.getFilename(filePath);

    const message = {
      type: "OPEN_FILE",
      directory,
      file: filename,
      fileId,
      hdu,
    };

    logger.info("Opening file in CARTA", { filePath, directory, filename });
    // await this.sendMessage(message);
  }

  /**
   * Set image view parameters (channel, stokes, etc.)
   */
  async setImageView(params: {
    fileId: number;
    channel?: number;
    stokes?: number;
    requiredTiles?: any;
  }): Promise<void> {
    if (!this.isConnected) {
      throw new Error("CARTA client not connected");
    }

    const message = {
      type: "SET_IMAGE_VIEW",
      ...params,
    };

    // await this.sendMessage(message);
  }

  /**
   * Create or update a region
   */
  async setRegion(region: CARTARegion): Promise<void> {
    if (!this.isConnected) {
      throw new Error("CARTA client not connected");
    }

    const message = {
      type: "SET_REGION",
      region,
    };

    // await this.sendMessage(message);
  }

  /**
   * Register a message handler
   */
  onMessage(messageType: CARTAMessageType, handler: CARTAMessageHandler): void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, new Set());
    }
    this.messageHandlers.get(messageType)!.add(handler);
  }

  /**
   * Remove a message handler
   */
  offMessage(messageType: CARTAMessageType, handler: CARTAMessageHandler): void {
    this.messageHandlers.get(messageType)?.delete(handler);
  }

  /**
   * Handle incoming WebSocket message
   */
  private handleMessage(event: MessageEvent): void {
    try {
      // TODO: Decode Protocol Buffer message
      // For now, we'll assume JSON format for development
      // In production, this should decode protobuf messages

      let data: any;
      if (event.data instanceof ArrayBuffer) {
        // Protocol Buffer binary data
        // TODO: Decode using protobuf library
        logger.debug("Received binary message from CARTA");
        return;
      } else if (typeof event.data === "string") {
        try {
          data = JSON.parse(event.data);
        } catch {
          // Not JSON, might be text message
          data = { type: "TEXT", content: event.data };
        }
      } else {
        data = event.data;
      }

      const messageType = data.type as CARTAMessageType;
      if (messageType) {
        const handlers = this.messageHandlers.get(messageType);
        if (handlers) {
          handlers.forEach((handler) => {
            try {
              handler(data);
            } catch (error) {
              logger.error(`Error in CARTA message handler for ${messageType}:`, error);
            }
          });
        }
      }

      // Also call generic handlers
      const allHandlers = this.messageHandlers.get("REGISTER_VIEWER" as CARTAMessageType); // Use a generic type
      // This is a placeholder - in real implementation, you'd have a generic handler
    } catch (error) {
      logger.error("Failed to handle CARTA message:", error);
    }
  }

  /**
   * Send a message to CARTA backend
   */
  private async sendMessage(message: any): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket not connected");
    }

    // TODO: Encode as Protocol Buffer
    // For now, send as JSON for development
    const jsonMessage = JSON.stringify(message);
    this.ws.send(jsonMessage);
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return;
    }

    this.reconnectAttempts++;
    logger.info(
      `Scheduling CARTA reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      if (!this.isConnected && !this.isConnecting) {
        this.connect().catch((error) => {
          logger.error("CARTA reconnection failed:", error);
        });
      }
    }, this.reconnectInterval);
  }

  /**
   * Disconnect from CARTA backend
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.isConnected = false;
    this.isConnecting = false;
    this.messageHandlers.clear();
  }

  /**
   * Check if client is connected
   */
  isClientConnected(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get current session ID
   */
  getSessionId(): string | null {
    return this.sessionId;
  }

  // Helper methods
  private getDirectory(filePath: string): string {
    const parts = filePath.split("/");
    parts.pop();
    return parts.join("/") || "/";
  }

  private getFilename(filePath: string): string {
    const parts = filePath.split("/");
    return parts[parts.length - 1] || filePath;
  }
}
