/**
 * CARTA Protocol Buffer Message Definitions
 *
 * This module defines TypeScript interfaces for CARTA messages based on
 * the CARTA Interface Control Document (ICD).
 *
 * CARTA messages consist of an 8-byte header followed by a protobuf payload:
 * - Header: 16-bit message type, 16-bit ICD version, 32-bit request ID
 * - Payload: Protocol Buffer encoded message
 */

/**
 * CARTA Message Header Structure
 * 8 bytes total:
 * - message_type: uint16 (2 bytes) - Message type identifier
 * - icd_version: uint16 (2 bytes) - Interface Control Document version
 * - request_id: uint32 (4 bytes) - Unique request identifier
 */
export interface CARTAMessageHeader {
  messageType: number;
  icdVersion: number;
  requestId: number;
}

/**
 * CARTA Message Types (from CARTA ICD)
 * These correspond to the message_type field in the header
 */
export const CARTAMessageType = {
  REGISTER_VIEWER: 0,
  FILE_LIST_REQUEST: 1,
  FILE_INFO_REQUEST: 2,
  OPEN_FILE: 3,
  SET_IMAGE_VIEW: 4,
  SET_REGION: 5,
  REGISTER_VIEWER_ACK: 100,
  FILE_LIST_RESPONSE: 101,
  FILE_INFO_RESPONSE: 102,
  OPEN_FILE_ACK: 103,
  SET_IMAGE_VIEW_ACK: 104,
  SET_REGION_ACK: 105,
  RASTER_TILE_DATA: 200,
  REGION_HISTOGRAM_DATA: 201,
  SPATIAL_PROFILE_DATA: 202,
  SPECTRAL_PROFILE_DATA: 203,
  ERROR_DATA: 300,
} as const;

export type CARTAMessageType = (typeof CARTAMessageType)[keyof typeof CARTAMessageType];

/**
 * Get the message type name from a numeric value
 */
export function getCARTAMessageTypeName(value: CARTAMessageType): string {
  const entry = Object.entries(CARTAMessageType).find(([, v]) => v === value);
  return entry ? entry[0] : `UNKNOWN_${value}`;
}

/**
 * CARTA ICD Version
 * Current version as of CARTA v3.0+
 */
export const CARTA_ICD_VERSION = 25;

/**
 * Register Viewer Request
 */
export interface RegisterViewerRequest {
  sessionId?: string;
  clientFeatureFlags?: Record<string, boolean>;
  apiKey?: string;
}

/**
 * Register Viewer Acknowledgment
 */
export interface RegisterViewerAck {
  success: boolean;
  sessionId?: string;
  message?: string;
  serverFeatureFlags?: Record<string, boolean>;
}

/**
 * File Info Request
 */
export interface FileInfoRequest {
  directory: string;
  file: string;
  hdu?: string;
}

/**
 * File Info Response
 */
export interface FileInfoResponse {
  success: boolean;
  fileInfo?: FileInfo;
  message?: string;
}

/**
 * File Information
 */
export interface FileInfo {
  name: string;
  type: string;
  size: number;
  hduList: string[];
  headerEntries: HeaderEntry[];
  dimensions: number[];
  dataType: string;
  coordinateType?: string;
  projection?: string;
  wcsInfo?: WCSInfo;
}

/**
 * FITS Header Entry
 */
export interface HeaderEntry {
  name: string;
  value: string | number;
  comment?: string;
}

/**
 * WCS (World Coordinate System) Information
 */
export interface WCSInfo {
  crval: number[];
  crpix: number[];
  cdelt: number[];
  ctype: string[];
  cunit?: string[];
  naxis: number[];
}

/**
 * Open File Request
 */
export interface OpenFileRequest {
  directory: string;
  file: string;
  fileId: number;
  hdu?: string;
  fileType?: string;
}

/**
 * Open File Acknowledgment
 */
export interface OpenFileAck {
  success: boolean;
  fileId?: number;
  fileInfo?: FileInfo;
  message?: string;
}

/**
 * Set Image View Request
 */
export interface SetImageViewRequest {
  fileId: number;
  channel?: number;
  stokes?: number;
  xMin?: number;
  xMax?: number;
  yMin?: number;
  yMax?: number;
  mip?: number;
  compressionQuality?: number;
  compressionType?: number;
  nanHandling?: number;
  customWcs?: boolean;
}

/**
 * Set Image View Acknowledgment
 */
export interface SetImageViewAck {
  success: boolean;
  fileId?: number;
  imageBounds?: ImageBounds;
  message?: string;
}

/**
 * Image Bounds
 */
export interface ImageBounds {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
  zMin: number;
  zMax: number;
}

/**
 * Raster Tile Data
 */
export interface RasterTileData {
  fileId: number;
  channel: number;
  stokes: number;
  compressionType: number;
  compressionQuality: number;
  tiles: RasterTile[];
  imageBounds?: ImageBounds;
}

/**
 * Raster Tile
 */
export interface RasterTile {
  x: number;
  y: number;
  layer: number;
  width: number;
  height: number;
  imageData: ArrayBuffer | Uint8Array;
}

/**
 * Set Region Request
 */
export interface SetRegionRequest {
  fileId: number;
  regionId: number;
  regionType: RegionType;
  controlPoints: Point[];
  rotation?: number;
}

/**
 * Region Type
 */
export const RegionType = {
  POINT: 0,
  LINE: 1,
  POLYGON: 2,
  ELLIPSE: 3,
  RECTANGLE: 4,
  ANNULUS: 5,
} as const;

export type RegionType = (typeof RegionType)[keyof typeof RegionType];

/**
 * Point (2D coordinate)
 */
export interface Point {
  x: number;
  y: number;
}

/**
 * Set Region Acknowledgment
 */
export interface SetRegionAck {
  success: boolean;
  regionId?: number;
  message?: string;
}

/**
 * Region Histogram Data
 */
export interface RegionHistogramData {
  regionId: number;
  fileId: number;
  channel: number;
  stokes: number;
  numBins: number;
  firstBinCenter: number;
  binWidth: number;
  mean: number;
  stdDev: number;
  counts: number[];
}

/**
 * Spatial Profile Data
 */
export interface SpatialProfileData {
  fileId: number;
  regionId: number;
  channel: number;
  stokes: number;
  start: number;
  end: number;
  values: number[];
  coordinates?: number[];
}

/**
 * Spectral Profile Data
 */
export interface SpectralProfileData {
  fileId: number;
  regionId: number;
  stokes: number;
  progress: number;
  profiles: SpectralProfile[];
}

/**
 * Spectral Profile
 */
export interface SpectralProfile {
  coordinate: number;
  value: number;
}

/**
 * Error Data
 */
export interface ErrorData {
  errorType: number;
  message: string;
  requestId?: number;
}

/**
 * Message Encoding/Decoding Utilities
 */

/**
 * Encode a CARTA message header
 */
export function encodeHeader(
  messageType: CARTAMessageType,
  requestId: number,
  icdVersion: number = CARTA_ICD_VERSION
): ArrayBuffer {
  const buffer = new ArrayBuffer(8);
  const view = new DataView(buffer);

  view.setUint16(0, messageType, true); // little-endian
  view.setUint16(2, icdVersion, true);
  view.setUint32(4, requestId, true);

  return buffer;
}

/**
 * Decode a CARTA message header
 */
export function decodeHeader(buffer: ArrayBuffer): CARTAMessageHeader {
  const view = new DataView(buffer);

  return {
    messageType: view.getUint16(0, true),
    icdVersion: view.getUint16(2, true),
    requestId: view.getUint32(4, true),
  };
}

/**
 * Combine header and payload into a complete CARTA message
 */
export function combineMessage(header: ArrayBuffer, payload: ArrayBuffer): ArrayBuffer {
  const combined = new ArrayBuffer(header.byteLength + payload.byteLength);
  const combinedView = new Uint8Array(combined);
  const headerView = new Uint8Array(header);
  const payloadView = new Uint8Array(payload);

  combinedView.set(headerView, 0);
  combinedView.set(payloadView, header.byteLength);

  return combined;
}

/**
 * Split a CARTA message into header and payload
 */
export function splitMessage(message: ArrayBuffer): {
  header: ArrayBuffer;
  payload: ArrayBuffer;
} {
  const header = message.slice(0, 8);
  const payload = message.slice(8);

  return { header, payload };
}
