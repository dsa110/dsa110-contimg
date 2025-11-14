/**
 * CARTA WebSocket Client - Option 2: Full WebSocket integration
 *
 * This client connects to CARTA backend via WebSocket using Protocol Buffers.
 * Provides full integration with the dashboard while leveraging CARTA's
 * powerful visualization capabilities.
 */

import { logger } from "../utils/logger";
import * as protobuf from "protobufjs";
import {
  CARTAMessageType,
  getCARTAMessageTypeName,
  encodeHeader,
  decodeHeader,
  combineMessage,
  splitMessage,
} from "./cartaProtobuf";
import type {
  RegisterViewerRequest,
  RegisterViewerAck,
  OpenFileRequest,
  OpenFileAck,
  SetImageViewRequest,
  SetImageViewAck,
  FileInfoRequest,
  FileInfoResponse,
  SetRegionRequest,
  SetRegionAck,
  ErrorData,
} from "./cartaProtobuf";

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
  private requestIdCounter = 0;
  private pendingRequests: Map<
    number,
    { resolve: (value: any) => void; reject: (error: Error) => void }
  > = new Map();
  private root: protobuf.Root | null = null;

  constructor(config: CARTAConfig) {
    this.config = config;
    this.sessionId = config.sessionId || null;
    this.initializeProtobuf();
  }

  /**
   * Initialize Protocol Buffer definitions
   * Attempts to load actual .proto files, falls back to JSON encoding
   */
  private async initializeProtobuf(): Promise<void> {
    try {
      // Try to load CARTA .proto files
      const { loadCARTAProtobuf } = await import("./cartaProtoLoader");
      this.root = await loadCARTAProtobuf();

      if (this.root) {
        logger.info("CARTA Protocol Buffer definitions loaded successfully");
      } else {
        logger.info("Protocol Buffer support initialized (using JSON fallback)");
      }
    } catch (error) {
      logger.warn("Failed to load Protocol Buffer definitions, using JSON fallback:", error);
      this.root = null;
    }
  }

  /**
   * Generate next request ID
   */
  private getNextRequestId(): number {
    this.requestIdCounter = (this.requestIdCounter + 1) % 0xffffffff;
    return this.requestIdCounter;
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
    const requestId = this.getNextRequestId();
    const request: RegisterViewerRequest = {
      sessionId: this.sessionId || undefined,
      clientFeatureFlags: this.config.clientFeatureFlags || {},
    };

    logger.info("Registering CARTA viewer", { requestId, request });

    return new Promise((resolve, reject) => {
      // Set up handler for response
      const handler = (ack: RegisterViewerAck) => {
        this.offMessage(CARTAMessageType.REGISTER_VIEWER_ACK, handler);
        if (ack.success) {
          if (ack.sessionId) {
            this.sessionId = ack.sessionId;
          }
          logger.info("CARTA viewer registered successfully", { sessionId: this.sessionId });
          resolve();
        } else {
          reject(new Error(ack.message || "Failed to register viewer"));
        }
      };

      this.onMessage(CARTAMessageType.REGISTER_VIEWER_ACK, handler);

      // Send message
      this.sendProtobufMessage(CARTAMessageType.REGISTER_VIEWER, requestId, request).catch(
        (error) => {
          this.offMessage(CARTAMessageType.REGISTER_VIEWER_ACK, handler);
          reject(error);
        }
      );
    });
  }

  /**
   * Open a FITS file in CARTA
   */
  async openFile(filePath: string, fileId: number = 0, hdu: string = ""): Promise<OpenFileAck> {
    if (!this.isConnected) {
      throw new Error("CARTA client not connected");
    }

    const directory = this.getDirectory(filePath);
    const filename = this.getFilename(filePath);

    const requestId = this.getNextRequestId();
    const request: OpenFileRequest = {
      directory,
      file: filename,
      fileId,
      hdu: hdu || undefined,
    };

    logger.info("Opening file in CARTA", { filePath, directory, filename, requestId });

    return new Promise((resolve, reject) => {
      const handler = (ack: OpenFileAck) => {
        this.offMessage(CARTAMessageType.OPEN_FILE_ACK, handler);
        if (ack.success) {
          logger.info("File opened successfully", { fileId: ack.fileId });
          resolve(ack);
        } else {
          reject(new Error(ack.message || "Failed to open file"));
        }
      };

      this.onMessage(CARTAMessageType.OPEN_FILE_ACK, handler);

      this.sendProtobufMessage(CARTAMessageType.OPEN_FILE, requestId, request).catch((error) => {
        this.offMessage(CARTAMessageType.OPEN_FILE_ACK, handler);
        reject(error);
      });
    });
  }

  /**
   * Set image view parameters (channel, stokes, etc.)
   */
  async setImageView(params: SetImageViewRequest): Promise<SetImageViewAck> {
    if (!this.isConnected) {
      throw new Error("CARTA client not connected");
    }

    const requestId = this.getNextRequestId();
    const request: SetImageViewRequest = {
      fileId: params.fileId,
      channel: params.channel,
      stokes: params.stokes,
      xMin: params.xMin,
      xMax: params.xMax,
      yMin: params.yMin,
      yMax: params.yMax,
      mip: params.mip,
      compressionQuality: params.compressionQuality,
      compressionType: params.compressionType,
      nanHandling: params.nanHandling,
      customWcs: params.customWcs,
    };

    logger.info("Setting image view", { requestId, request });

    return new Promise((resolve, reject) => {
      const handler = (ack: SetImageViewAck) => {
        this.offMessage(CARTAMessageType.SET_IMAGE_VIEW_ACK, handler);
        if (ack.success) {
          resolve(ack);
        } else {
          reject(new Error(ack.message || "Failed to set image view"));
        }
      };

      this.onMessage(CARTAMessageType.SET_IMAGE_VIEW_ACK, handler);

      this.sendProtobufMessage(CARTAMessageType.SET_IMAGE_VIEW, requestId, request).catch(
        (error) => {
          this.offMessage(CARTAMessageType.SET_IMAGE_VIEW_ACK, handler);
          reject(error);
        }
      );
    });
  }

  /**
   * Create or update a region
   */
  async setRegion(request: SetRegionRequest): Promise<SetRegionAck> {
    if (!this.isConnected) {
      throw new Error("CARTA client not connected");
    }

    const requestId = this.getNextRequestId();

    logger.info("Setting region", { requestId, request });

    return new Promise((resolve, reject) => {
      const handler = (ack: SetRegionAck) => {
        this.offMessage(CARTAMessageType.SET_REGION_ACK, handler);
        if (ack.success) {
          resolve(ack);
        } else {
          reject(new Error(ack.message || "Failed to set region"));
        }
      };

      this.onMessage(CARTAMessageType.SET_REGION_ACK, handler);

      this.sendProtobufMessage(CARTAMessageType.SET_REGION, requestId, request).catch((error) => {
        this.offMessage(CARTAMessageType.SET_REGION_ACK, handler);
        reject(error);
      });
    });
  }

  /**
   * Request file information
   */
  async requestFileInfo(directory: string, file: string, hdu?: string): Promise<FileInfoResponse> {
    if (!this.isConnected) {
      throw new Error("CARTA client not connected");
    }

    const requestId = this.getNextRequestId();
    const request: FileInfoRequest = {
      directory,
      file,
      hdu: hdu || undefined,
    };

    logger.info("Requesting file info", { requestId, request });

    return new Promise((resolve, reject) => {
      const handler = (response: FileInfoResponse) => {
        this.offMessage(CARTAMessageType.FILE_INFO_RESPONSE, handler);
        if (response.success) {
          resolve(response);
        } else {
          reject(new Error(response.message || "Failed to get file info"));
        }
      };

      this.onMessage(CARTAMessageType.FILE_INFO_RESPONSE, handler);

      this.sendProtobufMessage(CARTAMessageType.FILE_INFO_REQUEST, requestId, request).catch(
        (error) => {
          this.offMessage(CARTAMessageType.FILE_INFO_RESPONSE, handler);
          reject(error);
        }
      );
    });
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
      let data: any;
      let messageType: CARTAMessageType;

      if (event.data instanceof ArrayBuffer) {
        // Protocol Buffer binary message
        const { header, payload } = splitMessage(event.data);
        const decodedHeader = decodeHeader(header);
        messageType = decodedHeader.messageType as CARTAMessageType;

        // Decode payload
        // For now, use JSON fallback if protobuf root is not loaded
        // In production, decode using actual protobuf definitions
        try {
          if (this.root) {
            // Decode using protobuf
            const MessageType = this.root.lookupType(
              `CARTA.${getCARTAMessageTypeName(messageType)}`
            );
            const message = MessageType.decode(new Uint8Array(payload));
            data = MessageType.toObject(message, { longs: String, enums: String, bytes: String });
          } else {
            // JSON fallback for development
            const textDecoder = new TextDecoder();
            const jsonText = textDecoder.decode(payload);
            data = JSON.parse(jsonText);
          }
        } catch (error) {
          logger.warn("Failed to decode message payload, using raw data:", error);
          data = { raw: true };
        }

        // Check for pending request
        if (decodedHeader.requestId > 0) {
          const pending = this.pendingRequests.get(decodedHeader.requestId);
          if (pending) {
            this.pendingRequests.delete(decodedHeader.requestId);
            pending.resolve(data);
            return;
          }
        }
      } else if (typeof event.data === "string") {
        // JSON message (fallback for development)
        try {
          data = JSON.parse(event.data);
          messageType = data.messageType || (data.type as CARTAMessageType);
        } catch {
          logger.warn("Received non-JSON text message:", event.data);
          return;
        }
      } else {
        logger.warn("Received unexpected message type:", typeof event.data);
        return;
      }

      // Handle error messages
      if (messageType === CARTAMessageType.ERROR_DATA) {
        const errorData = data as ErrorData;
        logger.error("CARTA error:", errorData);
        if (errorData.requestId) {
          const pending = this.pendingRequests.get(errorData.requestId);
          if (pending) {
            this.pendingRequests.delete(errorData.requestId);
            pending.reject(new Error(errorData.message));
            return;
          }
        }
      }

      // Call registered handlers
      const handlers = this.messageHandlers.get(messageType);
      if (handlers) {
        handlers.forEach((handler) => {
          try {
            handler(data);
          } catch (error) {
            logger.error(`Error in CARTA message handler for ${messageType}:`, error);
          }
        });
      } else {
        logger.debug(`No handlers registered for message type: ${messageType}`);
      }
    } catch (error) {
      logger.error("Failed to handle CARTA message:", error);
    }
  }

  /**
   * Send a Protocol Buffer message to CARTA backend
   */
  private async sendProtobufMessage(
    messageType: CARTAMessageType,
    requestId: number,
    payload: any
  ): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket not connected");
    }

    try {
      // Encode header
      const header = encodeHeader(messageType, requestId);

      // Encode payload
      let payloadBuffer: ArrayBuffer;
      if (this.root) {
        // Encode using protobuf
        const MessageType = this.root.lookupType(`CARTA.${getCARTAMessageTypeName(messageType)}`);
        const message = MessageType.create(payload);
        const encoded = MessageType.encode(message).finish();
        // encoded.buffer is ArrayBufferLike, ensure it's ArrayBuffer
        payloadBuffer = new Uint8Array(encoded).buffer;
      } else {
        // JSON fallback for development
        const jsonText = JSON.stringify(payload);
        const encoder = new TextEncoder();
        payloadBuffer = encoder.encode(jsonText).buffer;
      }

      // Combine header and payload
      const message = combineMessage(header, payloadBuffer);

      // Send message
      this.ws.send(message);
      logger.debug(
        `Sent CARTA message: ${getCARTAMessageTypeName(messageType)} (requestId: ${requestId})`
      );
    } catch (error) {
      logger.error("Failed to encode/send CARTA message:", error);
      throw error;
    }
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
