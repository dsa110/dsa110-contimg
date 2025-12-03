/**
 * VOTable Exporter
 *
 * Utility for converting data to IVOA VOTable XML format.
 * Implements VOTable 1.4 specification.
 *
 * @see https://www.ivoa.net/documents/VOTable/
 */

import type {
  VOTableDocument,
  VOTableResource,
  VOTableTable,
  VOTableField,
  VOTableParam,
  VOTableCoordSys,
  VOTableInfo,
  VOTablePrimitiveValue,
  VOTableDataType,
  ColumnMapping,
} from "../types/vo";

// ============================================================================
// XML Utilities
// ============================================================================

/**
 * Escape special XML characters
 */
function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/**
 * Format a value for VOTable XML
 */
function formatValue(value: VOTablePrimitiveValue): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "number") {
    if (Number.isNaN(value)) {
      return "NaN";
    }
    if (!Number.isFinite(value)) {
      return value > 0 ? "Inf" : "-Inf";
    }
    return String(value);
  }
  return escapeXml(String(value));
}

/**
 * Create an XML attribute string
 */
function attr(name: string, value: string | number | undefined): string {
  if (value === undefined || value === "") {
    return "";
  }
  return ` ${name}="${escapeXml(String(value))}"`;
}

// ============================================================================
// VOTable XML Generation
// ============================================================================

/**
 * Generate FIELD element XML
 */
function generateFieldXml(field: VOTableField, indent: string = ""): string {
  const attrs = [
    attr("name", field.name),
    attr("datatype", field.datatype),
    attr("arraysize", field.arraysize),
    attr("unit", field.unit),
    attr("ucd", field.ucd),
    attr("ref", field.ref),
    attr("precision", field.precision),
    attr("width", field.width),
    attr("utype", field.utype),
  ].join("");

  if (field.description) {
    return `${indent}<FIELD${attrs}>
${indent}  <DESCRIPTION>${escapeXml(field.description)}</DESCRIPTION>
${indent}</FIELD>`;
  }
  return `${indent}<FIELD${attrs}/>`;
}

/**
 * Generate PARAM element XML
 */
function generateParamXml(param: VOTableParam, indent: string = ""): string {
  const attrs = [
    attr("name", param.name),
    attr("datatype", param.datatype),
    attr("value", formatValue(param.value)),
    attr("arraysize", param.arraysize),
    attr("unit", param.unit),
    attr("ucd", param.ucd),
    attr("utype", param.utype),
  ].join("");

  if (param.description) {
    return `${indent}<PARAM${attrs}>
${indent}  <DESCRIPTION>${escapeXml(param.description)}</DESCRIPTION>
${indent}</PARAM>`;
  }
  return `${indent}<PARAM${attrs}/>`;
}

/**
 * Generate COOSYS element XML
 */
function generateCoordSysXml(
  coordSys: VOTableCoordSys,
  indent: string = ""
): string {
  const attrs = [
    attr("ID", coordSys.id),
    attr("system", coordSys.system),
    attr("equinox", coordSys.equinox),
    attr("epoch", coordSys.epoch),
  ].join("");

  return `${indent}<COOSYS${attrs}/>`;
}

/**
 * Generate INFO element XML
 */
function generateInfoXml(info: VOTableInfo, indent: string = ""): string {
  const attrs = [attr("name", info.name), attr("value", info.value)].join("");
  return `${indent}<INFO${attrs}/>`;
}

/**
 * Generate TABLE element XML with data
 */
function generateTableXml(table: VOTableTable, indent: string = ""): string {
  const tableAttrs = [
    attr("name", table.name),
    attr("nrows", table.nrows ?? table.data.length),
    attr("utype", table.utype),
  ].join("");

  const lines: string[] = [];
  lines.push(`${indent}<TABLE${tableAttrs}>`);

  // Description
  if (table.description) {
    lines.push(
      `${indent}  <DESCRIPTION>${escapeXml(table.description)}</DESCRIPTION>`
    );
  }

  // Parameters
  if (table.params) {
    for (const param of table.params) {
      lines.push(generateParamXml(param, `${indent}  `));
    }
  }

  // Fields
  for (const field of table.fields) {
    lines.push(generateFieldXml(field, `${indent}  `));
  }

  // Data section
  lines.push(`${indent}  <DATA>`);
  lines.push(`${indent}    <TABLEDATA>`);

  // Rows
  const fieldNames = table.fields.map((f) => f.name);
  for (const row of table.data) {
    const cells = fieldNames
      .map((name) => {
        const value = row[name];
        return `<TD>${formatValue(value)}</TD>`;
      })
      .join("");
    lines.push(`${indent}      <TR>${cells}</TR>`);
  }

  lines.push(`${indent}    </TABLEDATA>`);
  lines.push(`${indent}  </DATA>`);
  lines.push(`${indent}</TABLE>`);

  return lines.join("\n");
}

/**
 * Generate RESOURCE element XML
 */
function generateResourceXml(
  resource: VOTableResource,
  indent: string = ""
): string {
  const resourceAttrs = [
    attr("name", resource.name),
    attr("type", resource.type),
    attr("ID", resource.id),
  ].join("");

  const lines: string[] = [];
  lines.push(`${indent}<RESOURCE${resourceAttrs}>`);

  // Description
  if (resource.description) {
    lines.push(
      `${indent}  <DESCRIPTION>${escapeXml(resource.description)}</DESCRIPTION>`
    );
  }

  // Info elements
  if (resource.infos) {
    for (const info of resource.infos) {
      lines.push(generateInfoXml(info, `${indent}  `));
    }
  }

  // Coordinate systems
  if (resource.coordSys) {
    for (const cs of resource.coordSys) {
      lines.push(generateCoordSysXml(cs, `${indent}  `));
    }
  }

  // Parameters
  if (resource.params) {
    for (const param of resource.params) {
      lines.push(generateParamXml(param, `${indent}  `));
    }
  }

  // Tables
  if (resource.tables) {
    for (const table of resource.tables) {
      lines.push(generateTableXml(table, `${indent}  `));
    }
  }

  lines.push(`${indent}</RESOURCE>`);

  return lines.join("\n");
}

/**
 * Generate complete VOTable XML document
 */
export function generateVOTableXml(doc: VOTableDocument): string {
  const version = doc.version || "1.4";
  const namespace =
    version === "1.4"
      ? "http://www.ivoa.net/xml/VOTable/v1.4"
      : version === "1.3"
      ? "http://www.ivoa.net/xml/VOTable/v1.3"
      : "http://www.ivoa.net/xml/VOTable/v1.2";

  const lines: string[] = [];

  // XML declaration
  lines.push('<?xml version="1.0" encoding="UTF-8"?>');

  // VOTable root element
  lines.push(`<VOTABLE version="${version}" xmlns="${namespace}">`);

  // Top-level description
  if (doc.description) {
    lines.push(`  <DESCRIPTION>${escapeXml(doc.description)}</DESCRIPTION>`);
  }

  // Resources
  for (const resource of doc.resources) {
    lines.push(generateResourceXml(resource, "  "));
  }

  lines.push("</VOTABLE>");

  return lines.join("\n");
}

// ============================================================================
// Data Conversion Utilities
// ============================================================================

/**
 * Infer VOTable datatype from JavaScript value
 */
export function inferDataType(value: unknown): VOTableDataType {
  if (value === null || value === undefined) {
    return "char";
  }
  if (typeof value === "boolean") {
    return "boolean";
  }
  if (typeof value === "number") {
    if (Number.isInteger(value)) {
      if (value >= -32768 && value <= 32767) {
        return "short";
      }
      if (value >= -2147483648 && value <= 2147483647) {
        return "int";
      }
      return "long";
    }
    return "double";
  }
  return "char";
}

/**
 * Default column mappings for source catalog data
 */
export const SOURCE_COLUMN_MAPPINGS: ColumnMapping[] = [
  {
    field: "id",
    votableName: "source_id",
    datatype: "char",
    arraysize: "*",
    ucd: "meta.id;src",
    description: "Unique source identifier",
  },
  {
    field: "ra",
    votableName: "ra",
    datatype: "double",
    unit: "deg",
    ucd: "pos.eq.ra;meta.main",
    description: "Right ascension (ICRS)",
  },
  {
    field: "dec",
    votableName: "dec",
    datatype: "double",
    unit: "deg",
    ucd: "pos.eq.dec;meta.main",
    description: "Declination (ICRS)",
  },
  {
    field: "ra_err",
    votableName: "ra_err",
    datatype: "float",
    unit: "arcsec",
    ucd: "stat.error;pos.eq.ra",
    description: "RA positional uncertainty",
  },
  {
    field: "dec_err",
    votableName: "dec_err",
    datatype: "float",
    unit: "arcsec",
    ucd: "stat.error;pos.eq.dec",
    description: "Dec positional uncertainty",
  },
  {
    field: "flux",
    votableName: "flux",
    datatype: "double",
    unit: "mJy",
    ucd: "phot.flux.density;em.radio",
    description: "Integrated flux density",
  },
  {
    field: "flux_err",
    votableName: "flux_err",
    datatype: "float",
    unit: "mJy",
    ucd: "stat.error;phot.flux.density",
    description: "Flux density uncertainty",
  },
  {
    field: "peak_flux",
    votableName: "peak_flux",
    datatype: "double",
    unit: "mJy/beam",
    ucd: "phot.flux.density;stat.max",
    description: "Peak flux density",
  },
  {
    field: "rms",
    votableName: "rms",
    datatype: "float",
    unit: "mJy/beam",
    ucd: "stat.stdev;phot.flux.density",
    description: "Local RMS noise",
  },
];

/**
 * Default column mappings for image metadata
 */
export const IMAGE_COLUMN_MAPPINGS: ColumnMapping[] = [
  {
    field: "id",
    votableName: "image_id",
    datatype: "char",
    arraysize: "*",
    ucd: "meta.id",
    description: "Unique image identifier",
  },
  {
    field: "obs_date",
    votableName: "obs_date",
    datatype: "char",
    arraysize: "*",
    ucd: "time.epoch",
    description: "Observation date/time",
  },
  {
    field: "ra_center",
    votableName: "ra_center",
    datatype: "double",
    unit: "deg",
    ucd: "pos.eq.ra",
    description: "Image center RA",
  },
  {
    field: "dec_center",
    votableName: "dec_center",
    datatype: "double",
    unit: "deg",
    ucd: "pos.eq.dec",
    description: "Image center Dec",
  },
  {
    field: "frequency",
    votableName: "frequency",
    datatype: "double",
    unit: "MHz",
    ucd: "em.freq",
    description: "Central frequency",
  },
  {
    field: "bandwidth",
    votableName: "bandwidth",
    datatype: "double",
    unit: "MHz",
    ucd: "em.freq;stat.width",
    description: "Bandwidth",
  },
];

/**
 * Convert array of data objects to VOTable document
 */
export function dataToVOTable(
  data: Record<string, unknown>[],
  options: {
    tableName?: string;
    resourceName?: string;
    description?: string;
    columnMappings?: ColumnMapping[];
    includeCoordSys?: boolean;
    infos?: VOTableInfo[];
  } = {}
): VOTableDocument {
  const {
    tableName = "results",
    resourceName = "DSA-110 Export",
    description,
    columnMappings,
    includeCoordSys = true,
    infos = [],
  } = options;

  // Determine fields from data or mappings
  let fields: VOTableField[];
  let tableData: Record<string, VOTablePrimitiveValue>[];

  if (columnMappings && columnMappings.length > 0) {
    // Use provided mappings
    fields = columnMappings.map((m) => ({
      name: m.votableName,
      datatype: m.datatype,
      unit: m.unit,
      ucd: m.ucd,
      description: m.description,
      arraysize: m.arraysize,
    }));

    // Transform data using mappings
    tableData = data.map((row) => {
      const transformed: Record<string, VOTablePrimitiveValue> = {};
      for (const mapping of columnMappings) {
        const value = row[mapping.field];
        transformed[mapping.votableName] = mapping.transform
          ? mapping.transform(value)
          : (value as VOTablePrimitiveValue);
      }
      return transformed;
    });
  } else {
    // Infer fields from first row
    if (data.length === 0) {
      fields = [];
      tableData = [];
    } else {
      const firstRow = data[0];
      fields = Object.keys(firstRow).map((key) => ({
        name: key,
        datatype: inferDataType(firstRow[key]),
        arraysize: typeof firstRow[key] === "string" ? "*" : undefined,
      }));

      tableData = data as Record<string, VOTablePrimitiveValue>[];
    }
  }

  // Build coordinate system if needed
  const coordSys: VOTableCoordSys[] = includeCoordSys
    ? [{ id: "ICRS", system: "ICRS", equinox: "J2000" }]
    : [];

  // Add standard info elements
  const allInfos: VOTableInfo[] = [
    { name: "QUERY_STATUS", value: "OK" },
    { name: "PROVIDER", value: "DSA-110 Pipeline" },
    { name: "TIMESTAMP", value: new Date().toISOString() },
    ...infos,
  ];

  // Build document
  const doc: VOTableDocument = {
    version: "1.4",
    description: description || `Data exported from DSA-110 Pipeline`,
    resources: [
      {
        name: resourceName,
        type: "results",
        description,
        infos: allInfos,
        coordSys,
        tables: [
          {
            name: tableName,
            description,
            fields,
            data: tableData,
          },
        ],
      },
    ],
  };

  return doc;
}

// ============================================================================
// Export Functions
// ============================================================================

/**
 * Export data to VOTable XML string
 */
export function exportToVOTable(
  data: Record<string, unknown>[],
  options?: Parameters<typeof dataToVOTable>[1]
): string {
  const doc = dataToVOTable(data, options);
  return generateVOTableXml(doc);
}

/**
 * Download data as VOTable file
 */
export function downloadVOTable(
  data: Record<string, unknown>[],
  filename: string = "export.vot",
  options?: Parameters<typeof dataToVOTable>[1]
): void {
  const xml = exportToVOTable(data, options);
  const blob = new Blob([xml], { type: "application/x-votable+xml" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename.endsWith(".vot") ? filename : `${filename}.vot`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

/**
 * Create a data URL for VOTable (for SAMP)
 */
export function createVOTableDataUrl(
  data: Record<string, unknown>[],
  options?: Parameters<typeof dataToVOTable>[1]
): string {
  const xml = exportToVOTable(data, options);
  return `data:application/x-votable+xml;base64,${btoa(xml)}`;
}
