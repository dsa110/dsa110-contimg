/**
 * VizieR TAP service query utilities.
 * Provides cone search functionality for catalog overlays.
 */

import { CatalogDefinition } from "../constants/catalogDefinitions";

export interface CatalogSource {
  ra: number;
  dec: number;
  id: string;
  catalog: string;
  magnitude?: number;
  flux?: number;
  [key: string]: any;
}

export interface CatalogQueryResult {
  catalogId: string;
  sources: CatalogSource[];
  count: number;
  truncated: boolean;
  error?: string;
}

const VIZIER_TAP_URL = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync";
const MAX_RESULTS = 1000;

/**
 * Build an ADQL cone search query for a VizieR catalog.
 */
function buildConeSearchQuery(
  catalog: CatalogDefinition,
  ra: number,
  dec: number,
  radiusDeg: number
): string {
  // Determine the RA/Dec column names based on catalog
  // Most VizieR catalogs use RAJ2000/DEJ2000 or _RAJ2000/_DEJ2000
  const raCol = "RAJ2000";
  const decCol = "DEJ2000";

  return `
    SELECT TOP ${MAX_RESULTS} 
      ${raCol} as ra, 
      ${decCol} as dec,
      *
    FROM "${catalog.vizierTable}"
    WHERE 1=CONTAINS(
      POINT('ICRS', ${raCol}, ${decCol}),
      CIRCLE('ICRS', ${ra}, ${dec}, ${radiusDeg})
    )
  `.trim();
}

/**
 * Parse VOTable XML response from VizieR TAP service.
 */
function parseVOTableResponse(xml: string, catalogId: string): CatalogSource[] {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xml, "text/xml");

  // Check for errors
  const errorInfo = doc.querySelector("INFO[name='QUERY_STATUS'][value='ERROR']");
  if (errorInfo) {
    throw new Error(errorInfo.textContent || "Query failed");
  }

  // Get field definitions
  const fields = Array.from(doc.querySelectorAll("FIELD"));
  const fieldNames = fields.map((f) => f.getAttribute("name") || "");
  const raIndex = fieldNames.findIndex((n) => n.toLowerCase().includes("ra") || n === "ra");
  const decIndex = fieldNames.findIndex((n) => n.toLowerCase().includes("de") || n === "dec");

  if (raIndex === -1 || decIndex === -1) {
    console.warn(`Could not find RA/Dec columns for ${catalogId}`, fieldNames);
    return [];
  }

  // Parse table data
  const rows = doc.querySelectorAll("TR");
  const sources: CatalogSource[] = [];

  rows.forEach((row, idx) => {
    const cells = row.querySelectorAll("TD");
    if (cells.length > Math.max(raIndex, decIndex)) {
      const ra = parseFloat(cells[raIndex].textContent || "");
      const dec = parseFloat(cells[decIndex].textContent || "");

      if (!isNaN(ra) && !isNaN(dec)) {
        sources.push({
          ra,
          dec,
          id: `${catalogId}_${idx}`,
          catalog: catalogId,
        });
      }
    }
  });

  return sources;
}

/**
 * Query a single VizieR catalog with cone search.
 */
export async function queryCatalog(
  catalog: CatalogDefinition,
  ra: number,
  dec: number,
  radiusArcmin: number,
  signal?: AbortSignal
): Promise<CatalogQueryResult> {
  const radiusDeg = radiusArcmin / 60;

  try {
    const query = buildConeSearchQuery(catalog, ra, dec, radiusDeg);

    const params = new URLSearchParams({
      REQUEST: "doQuery",
      LANG: "ADQL",
      FORMAT: "votable",
      QUERY: query,
    });

    const response = await fetch(`${VIZIER_TAP_URL}?${params}`, {
      signal,
      headers: {
        Accept: "application/xml",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const xml = await response.text();
    const sources = parseVOTableResponse(xml, catalog.id);

    return {
      catalogId: catalog.id,
      sources,
      count: sources.length,
      truncated: sources.length >= MAX_RESULTS,
    };
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw err;
    }
    return {
      catalogId: catalog.id,
      sources: [],
      count: 0,
      truncated: false,
      error: err instanceof Error ? err.message : "Query failed",
    };
  }
}

/**
 * Query multiple catalogs in parallel.
 */
export async function queryMultipleCatalogs(
  catalogs: CatalogDefinition[],
  ra: number,
  dec: number,
  radiusArcmin: number,
  signal?: AbortSignal
): Promise<Map<string, CatalogQueryResult>> {
  const results = await Promise.all(
    catalogs.map((cat) => queryCatalog(cat, ra, dec, radiusArcmin, signal))
  );

  const resultMap = new Map<string, CatalogQueryResult>();
  results.forEach((result) => {
    resultMap.set(result.catalogId, result);
  });

  return resultMap;
}

/**
 * Cache for catalog query results.
 */
const queryCache = new Map<string, { result: CatalogQueryResult; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

/**
 * Query catalog with caching.
 */
export async function queryCatalogCached(
  catalog: CatalogDefinition,
  ra: number,
  dec: number,
  radiusArcmin: number,
  signal?: AbortSignal
): Promise<CatalogQueryResult> {
  // Round coordinates for cache key
  const cacheKey = `${catalog.id}:${ra.toFixed(4)}:${dec.toFixed(4)}:${radiusArcmin.toFixed(1)}`;

  const cached = queryCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.result;
  }

  const result = await queryCatalog(catalog, ra, dec, radiusArcmin, signal);

  if (!result.error) {
    queryCache.set(cacheKey, { result, timestamp: Date.now() });
  }

  return result;
}
