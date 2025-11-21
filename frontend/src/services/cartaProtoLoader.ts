/**
 * CARTA Protocol Buffer Loader
 *
 * Utility to load CARTA .proto files for full Protocol Buffer support.
 * Falls back to JSON encoding if .proto files are not available.
 */

import * as protobuf from "protobufjs";
import { logger } from "../utils/logger";

/**
 * Load CARTA Protocol Buffer definitions
 *
 * Attempts to load .proto files from various locations:
 * 1. From npm package (if installed)
 * 2. From local path
 * 3. From CDN/remote URL
 *
 * Falls back to JSON encoding if loading fails.
 */
export async function loadCARTAProtobuf(): Promise<protobuf.Root | null> {
  const possiblePaths = [
    // Option 1: npm package (if installed)
    "node_modules/@carta-protobuf/definitions/carta.proto",
    "node_modules/carta-protobuf/carta.proto",

    // Option 2: Local development paths
    "/data/dsa110-contimg/frontend/public/carta.proto",
    "/data/dsa110-contimg/frontend/src/proto/carta.proto",
    "./public/carta.proto",
    "./src/proto/carta.proto",

    // Option 3: Remote CDN (fallback)
    "https://raw.githubusercontent.com/CARTAvis/carta-protobuf/main/carta.proto",
  ];

  for (const path of possiblePaths) {
    try {
      logger.info(`Attempting to load CARTA proto from: ${path}`);
      const root = await protobuf.load(path);
      logger.info(`Successfully loaded CARTA Protocol Buffer definitions from: ${path}`);
      return root;
    } catch (error) {
      logger.debug(`Failed to load from ${path}:`, error);
      continue;
    }
  }

  logger.warn("Could not load CARTA .proto files from any location. Using JSON fallback encoding.");
  logger.info("To enable full Protocol Buffer support, download CARTA proto files:");
  logger.info("  Option 1: Clone carta-protobuf repository");
  logger.info("    git clone https://github.com/CARTAvis/carta-protobuf.git");
  logger.info("    cp carta-protobuf/carta.proto frontend/public/");
  logger.info("");
  logger.info("  Option 2: Install npm package (if available)");
  logger.info("    npm install @carta-protobuf/definitions");

  return null;
}

/**
 * Download CARTA proto files from GitHub
 *
 * Downloads the latest .proto files from the CARTA protobuf repository.
 */
export async function downloadCARTAProtoFiles(
  _outputDir: string = "/data/dsa110-contimg/frontend/public"
): Promise<boolean> {
  try {
    const protoUrl = "https://raw.githubusercontent.com/CARTAvis/carta-protobuf/main/carta.proto";

    logger.info(`Downloading CARTA proto file from: ${protoUrl}`);

    const response = await fetch(protoUrl);
    if (!response.ok) {
      throw new Error(`Failed to download: ${response.statusText}`);
    }

    const protoContent = await response.text();

    // In a browser environment, we can't write files directly
    // This would need to be done server-side or via a build script
    logger.info(`Downloaded ${protoContent.length} bytes of proto definitions`);
    logger.warn(
      "Browser environment: Cannot write files. Use a build script or server-side download."
    );

    return false;
  } catch (error) {
    logger.error("Failed to download CARTA proto files:", error);
    return false;
  }
}
