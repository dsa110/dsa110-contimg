/**
 * Virtual Observatory (VO) Export Types
 *
 * Types for IVOA standard exports (VOTable, SAMP protocol).
 * Based on IVOA standards: https://www.ivoa.net/documents/
 */

// ============================================================================
// VOTable Types (IVOA VOTable 1.4 spec)
// ============================================================================

/**
 * VOTable data types (based on IVOA VOTable schema)
 */
export type VOTableDataType =
  | "boolean"
  | "bit"
  | "unsignedByte"
  | "short"
  | "int"
  | "long"
  | "char"
  | "unicodeChar"
  | "float"
  | "double"
  | "floatComplex"
  | "doubleComplex";

/**
 * VOTable primitive types for TypeScript mapping
 */
export type VOTablePrimitiveValue =
  | string
  | number
  | boolean
  | null
  | undefined;

/**
 * VOTable field definition
 */
export interface VOTableField {
  /** Field name (ID in VOTable) */
  name: string;
  /** Human-readable description */
  description?: string;
  /** VOTable datatype */
  datatype: VOTableDataType;
  /** Array size (e.g., "*" for variable, "3" for fixed) */
  arraysize?: string;
  /** Unit of the value (IVOA units) */
  unit?: string;
  /** UCD (Unified Content Descriptor) */
  ucd?: string;
  /** Reference to coordinate system */
  ref?: string;
  /** Precision for display */
  precision?: string;
  /** Display width */
  width?: number;
  /** UType (data model reference) */
  utype?: string;
}

/**
 * VOTable parameter (similar to field but single value)
 */
export interface VOTableParam extends VOTableField {
  /** The value of the parameter */
  value: VOTablePrimitiveValue;
}

/**
 * VOTable coordinate system definition
 */
export interface VOTableCoordSys {
  /** System ID */
  id: string;
  /** Coordinate system type */
  system?: "ICRS" | "FK5" | "FK4" | "galactic" | "supergalactic" | "ecliptic";
  /** Equinox (e.g., "J2000" or "B1950") */
  equinox?: string;
  /** Epoch of observation */
  epoch?: string;
}

/**
 * VOTable resource (container for tables and other elements)
 */
export interface VOTableResource {
  /** Resource name */
  name?: string;
  /** Resource type */
  type?: "results" | "meta";
  /** Description */
  description?: string;
  /** Resource identifier */
  id?: string;
  /** Parameters */
  params?: VOTableParam[];
  /** Coordinate systems */
  coordSys?: VOTableCoordSys[];
  /** Tables within this resource */
  tables?: VOTableTable[];
  /** Info elements */
  infos?: VOTableInfo[];
}

/**
 * VOTable info element
 */
export interface VOTableInfo {
  /** Info name */
  name: string;
  /** Info value */
  value: string;
  /** Info ID */
  id?: string;
}

/**
 * VOTable table definition
 */
export interface VOTableTable {
  /** Table name */
  name?: string;
  /** Table description */
  description?: string;
  /** Table ID */
  id?: string;
  /** UType reference */
  utype?: string;
  /** Number of rows (optional, for metadata) */
  nrows?: number;
  /** Field definitions */
  fields: VOTableField[];
  /** Parameters */
  params?: VOTableParam[];
  /** Table data (array of row objects) */
  data: Record<string, VOTablePrimitiveValue>[];
}

/**
 * Complete VOTable document
 */
export interface VOTableDocument {
  /** VOTable version */
  version?: "1.4" | "1.3" | "1.2";
  /** Top-level description */
  description?: string;
  /** Resources */
  resources: VOTableResource[];
}

// ============================================================================
// Export Configuration Types
// ============================================================================

/**
 * Data selection for export
 */
export interface ExportDataSelection {
  /** Type of data being exported */
  dataType: "sources" | "images" | "jobs" | "custom";
  /** Optional array of specific IDs to export */
  ids?: string[];
  /** Filter criteria */
  filters?: Record<string, unknown>;
  /** Columns to include (all if not specified) */
  columns?: string[];
  /** Maximum number of rows */
  limit?: number;
  /** Offset for pagination */
  offset?: number;
}

/**
 * VOTable export options
 */
export interface VOTableExportOptions {
  /** Data to export */
  selection: ExportDataSelection;
  /** VOTable version to output */
  version?: "1.4" | "1.3";
  /** Whether to include coordinate system definitions */
  includeCoordSys?: boolean;
  /** Whether to include UCDs */
  includeUCDs?: boolean;
  /** Custom table name */
  tableName?: string;
  /** Custom resource name */
  resourceName?: string;
  /** Additional info elements */
  infos?: VOTableInfo[];
  /** File name for download */
  filename?: string;
}

/**
 * Export format options
 */
export type ExportFormat = "votable" | "csv" | "json" | "fits";

/**
 * General export configuration
 */
export interface ExportConfig {
  /** Export format */
  format: ExportFormat;
  /** Data selection */
  selection: ExportDataSelection;
  /** Format-specific options */
  options?: VOTableExportOptions | Record<string, unknown>;
  /** Whether to send via SAMP instead of download */
  useSAMP?: boolean;
}

// ============================================================================
// SAMP Types (Simple Application Messaging Protocol)
// ============================================================================

/**
 * SAMP connection status
 */
export type SAMPConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

/**
 * SAMP hub profile type
 */
export type SAMPHubProfile = "standard" | "web";

/**
 * SAMP message types (MTypes)
 * Based on SAMP MType vocabulary
 */
export type SAMPMType =
  // Table messages
  | "table.load.votable"
  | "table.load.fits"
  | "table.highlight.row"
  | "table.select.rowList"
  // Image messages
  | "image.load.fits"
  // Coordinate messages
  | "coord.pointAt.sky"
  // Coverage messages
  | "coverage.load.moc"
  // Generic messages
  | "samp.app.ping"
  | "samp.hub.event.shutdown"
  | "samp.hub.event.register"
  | "samp.hub.event.unregister"
  | "samp.hub.event.subscriptions"
  | "samp.hub.event.metadata";

/**
 * SAMP client metadata
 */
export interface SAMPClientMetadata {
  /** Human-readable client name */
  "samp.name": string;
  /** Description of the client */
  "samp.description.text"?: string;
  /** Client icon URL */
  "samp.icon.url"?: string;
  /** Client documentation URL */
  "samp.documentation.url"?: string;
  /** Client author information */
  "author.name"?: string;
  /** Client affiliation */
  "author.affiliation"?: string;
  /** Custom metadata */
  [key: string]: string | undefined;
}

/**
 * SAMP subscription declaration
 */
export interface SAMPSubscription {
  /** MType pattern to subscribe to */
  mtype: string;
  /** Whether to receive broadcasts */
  broadcast?: boolean;
}

/**
 * SAMP message payload
 */
export interface SAMPMessage {
  /** Message type */
  mtype: SAMPMType;
  /** Message parameters */
  params: Record<string, string | number | boolean | string[] | undefined>;
}

/**
 * Common SAMP message parameters for VOTable loading
 */
export interface SAMPTableLoadParams {
  /** URL of the VOTable to load */
  url: string;
  /** Table identifier */
  "table-id"?: string;
  /** Human-readable name */
  name?: string;
}

/**
 * SAMP message parameters for FITS image loading
 */
export interface SAMPImageLoadParams {
  /** URL of the FITS file */
  url: string;
  /** Image identifier */
  "image-id"?: string;
  /** Human-readable name */
  name?: string;
}

/**
 * SAMP message parameters for coordinate pointing
 */
export interface SAMPCoordPointParams {
  /** Right Ascension in degrees */
  ra: string;
  /** Declination in degrees */
  dec: string;
}

/**
 * Registered SAMP client info
 */
export interface SAMPClientInfo {
  /** Client ID assigned by hub */
  id: string;
  /** Client metadata */
  metadata: SAMPClientMetadata;
  /** Subscribed message types */
  subscriptions: string[];
  /** Whether client is currently active */
  isActive: boolean;
}

/**
 * SAMP connection state
 */
export interface SAMPConnectionState {
  /** Connection status */
  status: SAMPConnectionStatus;
  /** Hub profile being used */
  hubProfile: SAMPHubProfile;
  /** Client ID (when connected) */
  clientId?: string;
  /** Connected hub URL */
  hubUrl?: string;
  /** List of registered clients */
  clients: SAMPClientInfo[];
  /** Error message if connection failed */
  error?: string;
  /** Last successful connection time */
  lastConnected?: string;
}

/**
 * SAMP send options
 */
export interface SAMPSendOptions {
  /** Target client ID (null for broadcast) */
  targetClient?: string | null;
  /** Callback for async response */
  onResponse?: (response: SAMPResponse) => void;
  /** Timeout in milliseconds */
  timeout?: number;
}

/**
 * SAMP response from a message
 */
export interface SAMPResponse {
  /** Whether the message was handled successfully */
  success: boolean;
  /** Response value if successful */
  value?: Record<string, unknown>;
  /** Error message if failed */
  error?: string;
  /** Client that sent the response */
  senderId?: string;
}

// ============================================================================
// UCD (Unified Content Descriptor) Mappings
// ============================================================================

/**
 * Common UCDs for astronomy data
 * Based on IVOA UCD1+ vocabulary
 */
export const COMMON_UCDS = {
  // Position
  RA: "pos.eq.ra",
  DEC: "pos.eq.dec",
  GLON: "pos.galactic.lon",
  GLAT: "pos.galactic.lat",
  POSITION_ERROR: "stat.error;pos.eq",

  // Photometry
  FLUX: "phot.flux",
  FLUX_DENSITY: "phot.flux.density",
  MAGNITUDE: "phot.mag",
  FLUX_ERROR: "stat.error;phot.flux",

  // Source properties
  SOURCE_ID: "meta.id;src",
  SOURCE_NAME: "meta.id;meta.main",
  REDSHIFT: "src.redshift",
  CLASSIFICATION: "src.class",

  // Time
  TIME: "time.epoch",
  TIME_START: "time.start",
  TIME_END: "time.end",
  EXPOSURE: "time.duration;obs.exposure",

  // Spectral
  FREQUENCY: "em.freq",
  WAVELENGTH: "em.wl",
  ENERGY: "em.energy",
  BANDWIDTH: "em.freq;stat.width",

  // Observational
  OBSERVATION_ID: "meta.id;obs",
  INSTRUMENT: "meta.id;instr",
  TELESCOPE: "meta.id;instr.tel",

  // Image
  IMAGE_ID: "meta.id;meta.image",
  IMAGE_TITLE: "meta.title;meta.image",
  PIXEL_SCALE: "pos.wcs.scale",
} as const;

export type CommonUCD = (typeof COMMON_UCDS)[keyof typeof COMMON_UCDS];

/**
 * Field to UCD mapping for DSA-110 data
 */
export const DSA110_UCD_MAPPINGS: Record<string, string> = {
  // Source fields
  source_id: COMMON_UCDS.SOURCE_ID,
  ra: COMMON_UCDS.RA,
  dec: COMMON_UCDS.DEC,
  ra_err: COMMON_UCDS.POSITION_ERROR,
  dec_err: COMMON_UCDS.POSITION_ERROR,
  flux: COMMON_UCDS.FLUX,
  flux_err: COMMON_UCDS.FLUX_ERROR,
  peak_flux: "phot.flux;stat.max",
  rms: "stat.stdev;phot.flux",

  // Image fields
  image_id: COMMON_UCDS.IMAGE_ID,
  obs_date: COMMON_UCDS.TIME,
  integration_time: COMMON_UCDS.EXPOSURE,
  frequency: COMMON_UCDS.FREQUENCY,
  bandwidth: COMMON_UCDS.BANDWIDTH,

  // Common metadata
  created_at: "time.creation",
  updated_at: "time.modification",
};

// ============================================================================
// Column Mapping Types
// ============================================================================

/**
 * Mapping from internal field names to VOTable fields
 */
export interface ColumnMapping {
  /** Internal field name */
  field: string;
  /** VOTable field name */
  votableName: string;
  /** VOTable datatype */
  datatype: VOTableDataType;
  /** Array size (e.g., "*" for variable, "3" for fixed) */
  arraysize?: string;
  /** Unit */
  unit?: string;
  /** UCD */
  ucd?: string;
  /** Description */
  description?: string;
  /** Transform function to apply to values */
  transform?: (value: unknown) => VOTablePrimitiveValue;
}

/**
 * Column configuration for different data types
 */
export type ColumnMappingConfig = {
  [dataType in ExportDataSelection["dataType"]]?: ColumnMapping[];
};
