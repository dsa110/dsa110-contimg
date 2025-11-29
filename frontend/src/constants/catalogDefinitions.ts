/**
 * Catalog definitions for VizieR overlay panel.
 * Colors and symbols are designed to be visually distinct.
 */

export interface CatalogDefinition {
  id: string;
  name: string;
  vizierTable: string;
  /** RA column name in VizieR table (defaults to RAJ2000) */
  raColumn?: string;
  /** Dec column name in VizieR table (defaults to DEJ2000) */
  decColumn?: string;
  color: string;
  symbol: "circle" | "square" | "diamond" | "triangle" | "star" | "plus" | "cross";
  description: string;
  defaultEnabled: boolean;
}

export const CATALOG_DEFINITIONS: CatalogDefinition[] = [
  {
    id: "gaia",
    name: "Gaia DR3",
    vizierTable: "I/355/gaiadr3",
    raColumn: "RA_ICRS",
    decColumn: "DE_ICRS",
    color: "#ff0000",
    symbol: "circle",
    description: "Gaia Data Release 3 - optical astrometry and photometry",
    defaultEnabled: false,
  },
  {
    id: "tess",
    name: "TESS TIC v8.2",
    vizierTable: "IV/39/tic82",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#db01fd",
    symbol: "diamond",
    description: "TESS Input Catalog - stars observed by TESS",
    defaultEnabled: false,
  },
  {
    id: "ps1",
    name: "Pan-STARRS DR1",
    vizierTable: "II/349/ps1",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#0066ff",
    symbol: "square",
    description: "Pan-STARRS1 Survey - optical photometry",
    defaultEnabled: false,
  },
  {
    id: "2mass",
    name: "2MASS",
    vizierTable: "II/246/out",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#ff9900",
    symbol: "triangle",
    description: "Two Micron All Sky Survey - near-infrared",
    defaultEnabled: false,
  },
  {
    id: "wise",
    name: "AllWISE",
    vizierTable: "II/328/allwise",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#00cc66",
    symbol: "star",
    description: "Wide-field Infrared Survey Explorer",
    defaultEnabled: false,
  },
  {
    id: "nvss",
    name: "NVSS",
    vizierTable: "VIII/65/nvss",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#00cccc",
    symbol: "plus",
    description: "NRAO VLA Sky Survey - 1.4 GHz radio",
    defaultEnabled: false,
  },
  {
    id: "first",
    name: "FIRST",
    vizierTable: "VIII/92/first14",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#cc00cc",
    symbol: "cross",
    description: "Faint Images of the Radio Sky at Twenty-cm",
    defaultEnabled: false,
  },
  {
    id: "sumss",
    name: "SUMSS",
    vizierTable: "VIII/81B/sumss212",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#ffcc00",
    symbol: "circle",
    description: "Sydney University Molonglo Sky Survey - 843 MHz",
    defaultEnabled: false,
  },
  {
    id: "racs",
    name: "RACS-Low",
    vizierTable: "J/other/PASA/38.58/gausscut",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#66ff66",
    symbol: "diamond",
    description: "Rapid ASKAP Continuum Survey - 887 MHz",
    defaultEnabled: false,
  },
  {
    id: "vlass",
    name: "VLASS",
    vizierTable: "J/ApJS/255/30/table1",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#ff6666",
    symbol: "square",
    description: "VLA Sky Survey - 3 GHz radio",
    defaultEnabled: false,
  },
  {
    id: "atnf",
    name: "ATNF Pulsars",
    vizierTable: "B/psr/psr",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#ffffff",
    symbol: "star",
    description: "Australia Telescope National Facility Pulsar Catalogue",
    defaultEnabled: false,
  },
];

export const getCatalogById = (id: string): CatalogDefinition | undefined => {
  return CATALOG_DEFINITIONS.find((c) => c.id === id);
};

export const getEnabledCatalogs = (): CatalogDefinition[] => {
  return CATALOG_DEFINITIONS.filter((c) => c.defaultEnabled);
};
