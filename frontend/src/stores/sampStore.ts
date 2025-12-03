/**
 * SAMP Client Store
 *
 * Zustand store for managing SAMP (Simple Application Messaging Protocol)
 * connections and message passing with astronomy applications.
 *
 * @see https://www.ivoa.net/documents/SAMP/
 */

import { create } from "zustand";
import type {
  SAMPConnectionState,
  SAMPClientInfo,
  SAMPClientMetadata,
  SAMPMessage,
  SAMPMType,
  SAMPSendOptions,
  SAMPResponse,
  SAMPTableLoadParams,
  SAMPImageLoadParams,
} from "../types/vo";

// ============================================================================
// SAMP Hub Connection
// ============================================================================

/**
 * Default SAMP Web Profile hub URL
 */
const DEFAULT_HUB_URL = "http://localhost:21012/";

/**
 * DSA-110 Pipeline client metadata
 * Reserved for real SAMP implementation
 */
const _CLIENT_METADATA: SAMPClientMetadata = {
  "samp.name": "DSA-110 Pipeline",
  "samp.description.text":
    "DSA-110 Continuum Imaging Pipeline web interface for browsing radio continuum survey data",
  "samp.icon.url": "", // Can be set to an actual icon URL
  "samp.documentation.url": "https://github.com/dsa110/dsa110-contimg",
  "author.name": "DSA-110 Team",
  "author.affiliation": "Caltech",
};

/**
 * MTypes that DSA-110 Pipeline subscribes to
 * Reserved for real SAMP implementation
 */
const _SUBSCRIBED_MTYPES: SAMPMType[] = [
  "samp.app.ping",
  "samp.hub.event.shutdown",
  "samp.hub.event.register",
  "samp.hub.event.unregister",
  "coord.pointAt.sky",
  "table.highlight.row",
];

// ============================================================================
// Store Types
// ============================================================================

interface SAMPActions {
  /** Connect to SAMP hub */
  connect: (hubUrl?: string) => Promise<void>;
  /** Disconnect from SAMP hub */
  disconnect: () => void;
  /** Send a message to SAMP hub */
  sendMessage: (
    message: SAMPMessage,
    options?: SAMPSendOptions
  ) => Promise<SAMPResponse>;
  /** Send VOTable to connected applications */
  sendTable: (
    url: string,
    params?: Partial<SAMPTableLoadParams>,
    options?: SAMPSendOptions
  ) => Promise<SAMPResponse>;
  /** Send FITS image to connected applications */
  sendImage: (
    url: string,
    params?: Partial<SAMPImageLoadParams>,
    options?: SAMPSendOptions
  ) => Promise<SAMPResponse>;
  /** Point at sky coordinates */
  pointAtSky: (
    ra: number,
    dec: number,
    options?: SAMPSendOptions
  ) => Promise<SAMPResponse>;
  /** Update client list */
  refreshClients: () => Promise<void>;
  /** Handle incoming message */
  handleMessage: (mtype: SAMPMType, params: Record<string, unknown>) => void;
  /** Set connection error */
  setError: (error: string | null) => void;
}

type SAMPStore = SAMPConnectionState & SAMPActions;

// ============================================================================
// Mock SAMP Implementation
// ============================================================================

/**
 * Note: Full SAMP implementation requires either:
 * 1. A SAMP Web Profile hub running locally (sampy, jsamp, etc.)
 * 2. Browser extension for SAMP support
 *
 * This is a mock implementation that simulates SAMP behavior for development.
 * In production, integrate with actual SAMP library like samp.js
 */

let mockConnected = false;
let mockClientId = "";
const _mockClients: SAMPClientInfo[] = [];

/**
 * Simulate SAMP hub connection
 */
async function mockConnect(_hubUrl: string): Promise<string> {
  // Simulate connection delay
  await new Promise((resolve) => setTimeout(resolve, 500));

  // Check if hub is available (mock always fails in web browser without hub)
  // In real implementation, this would try to connect to the hub
  const hubAvailable = false; // Set to true to simulate successful connection

  if (!hubAvailable) {
    throw new Error(
      "SAMP hub not found. Please start a SAMP hub (e.g., TOPCAT, Aladin, or standalone hub)"
    );
  }

  mockConnected = true;
  mockClientId = `dsa110_${Date.now()}`;
  return mockClientId;
}

/**
 * Simulate sending SAMP message
 */
async function mockSendMessage(
  _message: SAMPMessage,
  _targetClient?: string | null
): Promise<SAMPResponse> {
  if (!mockConnected) {
    return { success: false, error: "Not connected to SAMP hub" };
  }

  // Simulate message delay
  await new Promise((resolve) => setTimeout(resolve, 200));

  // Mock successful response
  return {
    success: true,
    value: { status: "ok" },
  };
}

/**
 * Simulate getting client list
 */
async function mockGetClients(): Promise<SAMPClientInfo[]> {
  if (!mockConnected) {
    return [];
  }

  // Return mock clients
  return [
    {
      id: "topcat_1",
      metadata: {
        "samp.name": "TOPCAT",
        "samp.description.text": "Tool for OPerations on Catalogues And Tables",
      },
      subscriptions: ["table.load.votable", "table.highlight.row"],
      isActive: true,
    },
    {
      id: "aladin_1",
      metadata: {
        "samp.name": "Aladin",
        "samp.description.text": "Interactive sky atlas",
      },
      subscriptions: [
        "table.load.votable",
        "image.load.fits",
        "coord.pointAt.sky",
      ],
      isActive: true,
    },
  ];
}

// ============================================================================
// Store Implementation
// ============================================================================

export const useSAMPStore = create<SAMPStore>((set, get) => ({
  // Initial state
  status: "disconnected",
  hubProfile: "web",
  clientId: undefined,
  hubUrl: undefined,
  clients: [],
  error: undefined,
  lastConnected: undefined,

  // Actions
  connect: async (hubUrl = DEFAULT_HUB_URL) => {
    set({ status: "connecting", error: undefined });

    try {
      const clientId = await mockConnect(hubUrl);

      // Register metadata
      // In real implementation: hub.declareMetadata(CLIENT_METADATA)

      // Subscribe to messages
      // In real implementation: hub.declareSubscriptions(SUBSCRIBED_MTYPES)

      // Get client list
      const clients = await mockGetClients();

      set({
        status: "connected",
        clientId,
        hubUrl,
        clients,
        lastConnected: new Date().toISOString(),
        error: undefined,
      });
    } catch (error) {
      set({
        status: "error",
        error: error instanceof Error ? error.message : "Connection failed",
        clientId: undefined,
        hubUrl: undefined,
      });
    }
  },

  disconnect: () => {
    mockConnected = false;
    mockClientId = "";

    set({
      status: "disconnected",
      clientId: undefined,
      hubUrl: undefined,
      clients: [],
      error: undefined,
    });
  },

  sendMessage: async (message, options) => {
    const { status } = get();

    if (status !== "connected") {
      return { success: false, error: "Not connected to SAMP hub" };
    }

    try {
      const response = await mockSendMessage(message, options?.targetClient);

      if (options?.onResponse) {
        options.onResponse(response);
      }

      return response;
    } catch (error) {
      const errorResponse: SAMPResponse = {
        success: false,
        error: error instanceof Error ? error.message : "Send failed",
      };

      if (options?.onResponse) {
        options.onResponse(errorResponse);
      }

      return errorResponse;
    }
  },

  sendTable: async (url, params, options) => {
    const { sendMessage } = get();

    const message: SAMPMessage = {
      mtype: "table.load.votable",
      params: {
        url,
        "table-id": params?.["table-id"],
        name: params?.name,
      },
    };

    return sendMessage(message, options);
  },

  sendImage: async (url, params, options) => {
    const { sendMessage } = get();

    const message: SAMPMessage = {
      mtype: "image.load.fits",
      params: {
        url,
        "image-id": params?.["image-id"],
        name: params?.name,
      },
    };

    return sendMessage(message, options);
  },

  pointAtSky: async (ra, dec, options) => {
    const { sendMessage } = get();

    const message: SAMPMessage = {
      mtype: "coord.pointAt.sky",
      params: {
        ra: String(ra),
        dec: String(dec),
      },
    };

    return sendMessage(message, options);
  },

  refreshClients: async () => {
    const { status } = get();

    if (status !== "connected") {
      return;
    }

    try {
      const clients = await mockGetClients();
      set({ clients });
    } catch (error) {
      console.error("Failed to refresh SAMP clients:", error);
    }
  },

  handleMessage: (mtype, params) => {
    // Handle incoming SAMP messages
    switch (mtype) {
      case "samp.hub.event.shutdown":
        get().disconnect();
        break;

      case "samp.hub.event.register":
      case "samp.hub.event.unregister":
        get().refreshClients();
        break;

      case "coord.pointAt.sky":
        // TODO: Emit event for UI to handle coordinate pointing
        // For now, silently acknowledge
        void params; // Reference to silence unused warning
        break;

      case "table.highlight.row":
        // TODO: Emit event to highlight a row in a table
        void params;
        break;

      default:
        // Unknown message types are silently ignored
        void params;
    }
  },

  setError: (error) => {
    set({ error: error ?? undefined });
  },
}));

// ============================================================================
// Hooks
// ============================================================================

/**
 * Hook for SAMP connection status
 */
export function useSAMPConnection() {
  return useSAMPStore((state) => ({
    status: state.status,
    isConnected: state.status === "connected",
    isConnecting: state.status === "connecting",
    error: state.error,
    hubUrl: state.hubUrl,
    clientId: state.clientId,
    connect: state.connect,
    disconnect: state.disconnect,
  }));
}

/**
 * Hook for SAMP client list
 */
export function useSAMPClients() {
  return useSAMPStore((state) => ({
    clients: state.clients,
    refreshClients: state.refreshClients,
  }));
}

/**
 * Hook for SAMP messaging
 */
export function useSAMPMessaging() {
  return useSAMPStore((state) => ({
    sendMessage: state.sendMessage,
    sendTable: state.sendTable,
    sendImage: state.sendImage,
    pointAtSky: state.pointAtSky,
  }));
}

/**
 * Get clients that support a specific MType
 */
export function getClientsForMType(
  clients: SAMPClientInfo[],
  mtype: SAMPMType
): SAMPClientInfo[] {
  return clients.filter(
    (client) => client.isActive && client.subscriptions.includes(mtype)
  );
}

/**
 * Check if any connected client supports the given MType
 */
export function canSendMType(
  clients: SAMPClientInfo[],
  mtype: SAMPMType
): boolean {
  return getClientsForMType(clients, mtype).length > 0;
}
