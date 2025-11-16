/**
 * WebSocket/SSE client for real-time updates
 */

import { logger } from "../utils/logger";

export type MessageHandler = (data: any) => void;

export interface WebSocketClientOptions {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  useSSE?: boolean; // Use Server-Sent Events instead of WebSocket
}

export class WebSocketClient {
  private url: string;
  private ws: WebSocket | EventSource | null = null;
  private reconnectInterval: number;
  private maxReconnectAttempts: number;
  private reconnectAttempts = 0;
  private useSSE: boolean;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isConnected = false;

  constructor(options: WebSocketClientOptions) {
    this.url = options.url;
    this.reconnectInterval = options.reconnectInterval || 3000;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
    this.useSSE = options.useSSE || false;
  }

  /**
   * Connect to the server
   */
  connect(): void {
    if (this.isConnecting || this.isConnected) {
      return;
    }

    this.isConnecting = true;

    try {
      if (this.useSSE) {
        this.connectSSE();
      } else {
        this.connectWebSocket();
      }
    } catch (error) {
      logger.error("Failed to connect:", error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  /**
   * Connect using WebSocket
   */
  private connectWebSocket(): void {
    const wsUrl = this.url.replace(/^http/, "ws");

    // Validate WebSocket URL before attempting connection
    if (!wsUrl || (!wsUrl.startsWith("ws://") && !wsUrl.startsWith("wss://"))) {
      logger.error("Invalid WebSocket URL:", wsUrl);
      this.isConnecting = false;
      this.scheduleReconnect();
      return;
    }

    logger.info(`Attempting WebSocket connection to: ${wsUrl}`);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      logger.info("WebSocket connected", { url: wsUrl });
      this.isConnecting = false;
      this.isConnected = true;
      this.reconnectAttempts = 0;

      // Send ping to keep connection alive
      this.startPingInterval();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        logger.warn("Failed to parse WebSocket message:", error);
      }
    };

    this.ws.onerror = (error) => {
      // WebSocket error events don't provide detailed information,
      // but we can log the connection state and URL for diagnostics
      const errorInfo: Record<string, unknown> = {
        url: wsUrl,
        readyState: this.ws?.readyState,
        readyStateText: this.getReadyStateText(this.ws?.readyState),
        reconnectAttempt: this.reconnectAttempts,
      };

      // Try to extract any available error information
      if (error && typeof error === "object") {
        if ("message" in error) {
          errorInfo.message = (error as { message: string }).message;
        }
        if ("type" in error) {
          errorInfo.type = (error as { type: string }).type;
        }
      }

      logger.error("WebSocket error:", errorInfo);
      this.isConnecting = false;
      this.isConnected = false;
    };

    this.ws.onclose = (event) => {
      // The onclose event provides more diagnostic information than onerror
      const closeInfo: Record<string, unknown> = {
        url: wsUrl,
        code: event.code,
        reason: event.reason || "No reason provided",
        wasClean: event.wasClean,
        reconnectAttempt: this.reconnectAttempts,
      };

      // Add human-readable close code description
      closeInfo.codeDescription = this.getCloseCodeDescription(event.code);

      if (event.wasClean) {
        logger.info("WebSocket closed cleanly", closeInfo);
      } else {
        logger.error("WebSocket connection closed unexpectedly", closeInfo);
      }

      this.isConnecting = false;
      this.isConnected = false;
      this.stopPingInterval();
      this.scheduleReconnect();
    };
  }

  /**
   * Get human-readable ready state text
   */
  private getReadyStateText(readyState: number | undefined): string {
    if (readyState === undefined) return "UNKNOWN";
    const states: Record<number, string> = {
      0: "CONNECTING",
      1: "OPEN",
      2: "CLOSING",
      3: "CLOSED",
    };
    return states[readyState] || `UNKNOWN(${readyState})`;
  }

  /**
   * Get human-readable close code description
   */
  private getCloseCodeDescription(code: number): string {
    const codes: Record<number, string> = {
      1000: "Normal Closure",
      1001: "Going Away",
      1002: "Protocol Error",
      1003: "Unsupported Data",
      1004: "Reserved",
      1005: "No Status Received",
      1006: "Abnormal Closure",
      1007: "Invalid Frame Payload Data",
      1008: "Policy Violation",
      1009: "Message Too Big",
      1010: "Mandatory Extension",
      1011: "Internal Server Error",
      1012: "Service Restart",
      1013: "Try Again Later",
      1014: "Bad Gateway",
      1015: "TLS Handshake",
    };

    // Check for reserved ranges
    if (code >= 1000 && code <= 1015) {
      return codes[code] || `Reserved(${code})`;
    } else if (code >= 1016 && code <= 2999) {
      return `Reserved for WebSocket standard(${code})`;
    } else if (code >= 3000 && code <= 3999) {
      return `Reserved for libraries and frameworks(${code})`;
    } else if (code >= 4000 && code <= 4999) {
      return `Reserved for applications(${code})`;
    }

    return `Unknown close code(${code})`;
  }

  /**
   * Connect using Server-Sent Events
   */
  private connectSSE(): void {
    const sseUrl = this.url.replace(/\/ws\//, "/sse/");
    this.ws = new EventSource(sseUrl);

    (this.ws as EventSource).onopen = () => {
      logger.info("SSE connected");
      this.isConnecting = false;
      this.isConnected = true;
      this.reconnectAttempts = 0;
    };

    (this.ws as EventSource).onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        logger.warn("Failed to parse SSE message:", error);
      }
    };

    (this.ws as EventSource).onerror = (error) => {
      logger.error("SSE error:", error);
      this.isConnecting = false;
      this.isConnected = false;
      this.scheduleReconnect();
    };
  }

  /**
   * Handle incoming message
   */
  private handleMessage(data: any): void {
    const type = data.type || "message";
    const handlers = this.handlers.get(type);

    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (error) {
          logger.error("Error in message handler:", error);
        }
      });
    }

    // Also call 'message' handlers for all messages
    const messageHandlers = this.handlers.get("message");
    if (messageHandlers && type !== "message") {
      messageHandlers.forEach((handler) => {
        try {
          handler(data);
        } catch (error) {
          logger.error("Error in message handler:", error);
        }
      });
    }
  }

  /**
   * Subscribe to a message type
   */
  on(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.handlers.get(type);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.handlers.delete(type);
        }
      }
    };
  }

  /**
   * Schedule reconnection
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.error("Max reconnection attempts reached");
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      30000 // Max 30 seconds
    );

    logger.info(`Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  /**
   * Start ping interval for WebSocket
   */
  private pingInterval: NodeJS.Timeout | null = null;

  private startPingInterval(): void {
    if (this.pingInterval) {
      return;
    }

    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws instanceof WebSocket && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send("ping");
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Disconnect from the server
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopPingInterval();

    if (this.ws) {
      if (this.ws instanceof WebSocket) {
        this.ws.close();
      } else if (this.ws instanceof EventSource) {
        this.ws.close();
      }
      this.ws = null;
    }

    this.isConnecting = false;
    this.isConnected = false;
    this.reconnectAttempts = 0;
  }

  /**
   * Check if connected
   */
  get connected(): boolean {
    return this.isConnected;
  }
}

/**
 * Create a WebSocket client instance
 */
export function createWebSocketClient(options: WebSocketClientOptions): WebSocketClient {
  return new WebSocketClient(options);
}
