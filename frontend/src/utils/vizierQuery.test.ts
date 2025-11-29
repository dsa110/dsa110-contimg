import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// We need to stub fetch before importing the module
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// Import after mocking
import { queryCatalog, queryMultipleCatalogs } from "./vizierQuery";
import { CatalogDefinition } from "../constants/catalogDefinitions";

describe("vizierQuery", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // Mock catalog matching production CatalogDefinition interface
  const mockCatalog: CatalogDefinition = {
    id: "test-catalog",
    name: "Test Catalog",
    vizierTable: "I/test",
    description: "A test catalog",
    raColumn: "RAJ2000",
    decColumn: "DEJ2000",
    color: "#ff0000",
    symbol: "circle",
    defaultEnabled: false,
  };

  describe("queryCatalog", () => {
    it("should make a TAP request to VizieR and parse results", async () => {
      // Mock VOTable XML response matching what VizieR actually returns
      // The ADQL query aliases columns as "ra" and "dec" (lowercase)
      const votableXml = `<?xml version="1.0" encoding="UTF-8"?>
<VOTABLE version="1.4" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
  <RESOURCE type="results">
    <TABLE>
      <FIELD name="ra" datatype="double" unit="deg"/>
      <FIELD name="dec" datatype="double" unit="deg"/>
      <FIELD name="RAJ2000" datatype="double" unit="deg"/>
      <FIELD name="DEJ2000" datatype="double" unit="deg"/>
      <DATA>
        <TABLEDATA>
          <TR><TD>180.0</TD><TD>45.0</TD><TD>180.0</TD><TD>45.0</TD></TR>
        </TABLEDATA>
      </DATA>
    </TABLE>
  </RESOURCE>
</VOTABLE>`;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(votableXml),
      });

      const result = await queryCatalog(mockCatalog, 180, 45, 0.1);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain("tapvizier.cds.unistra.fr");
      expect(url).toContain("ADQL");

      // Verify the source was parsed correctly
      expect(result.sources).toHaveLength(1);
      expect(result.sources[0].ra).toBe(180.0);
      expect(result.sources[0].dec).toBe(45.0);
      expect(result.sources[0].catalog).toBe("test-catalog");
      expect(result.count).toBe(1);
      expect(result.truncated).toBe(false);
    });

    it("should handle empty results", async () => {
      // Empty VOTable with proper structure but no data rows
      const emptyVotable = `<?xml version="1.0" encoding="UTF-8"?>
<VOTABLE version="1.4" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
  <RESOURCE type="results">
    <TABLE>
      <FIELD name="ra" datatype="double" unit="deg"/>
      <FIELD name="dec" datatype="double" unit="deg"/>
      <DATA>
        <TABLEDATA>
        </TABLEDATA>
      </DATA>
    </TABLE>
  </RESOURCE>
</VOTABLE>`;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(emptyVotable),
      });

      const result = await queryCatalog(mockCatalog, 180, 45, 0.1);

      expect(result.sources).toHaveLength(0);
      expect(result.count).toBe(0);
      expect(result.truncated).toBe(false);
      expect(result.error).toBeUndefined();
    });

    it("should handle network errors", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await queryCatalog(mockCatalog, 180, 45, 0.1);

      expect(result.sources).toHaveLength(0);
      expect(result.error).toBeDefined();
      expect(result.error).toContain("Network error");
    });

    it("should handle HTTP errors", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      });

      const result = await queryCatalog(mockCatalog, 180, 45, 0.1);

      expect(result.sources).toHaveLength(0);
      expect(result.error).toBeDefined();
    });
  });

  describe("queryMultipleCatalogs", () => {
    it("should return results for each catalog as a Map", async () => {
      // Mock VOTable XML response matching VizieR production format
      // Includes FIELD definitions with aliased column names from ADQL query
      const emptyVotable = `<?xml version="1.0" encoding="UTF-8"?>
<VOTABLE version="1.4" xmlns="http://www.ivoa.net/xml/VOTable/v1.3">
  <RESOURCE type="results">
    <TABLE>
      <FIELD name="ra" datatype="double" unit="deg"/>
      <FIELD name="dec" datatype="double" unit="deg"/>
      <DATA>
        <TABLEDATA></TABLEDATA>
      </DATA>
    </TABLE>
  </RESOURCE>
</VOTABLE>`;

      // Mock enough responses for both catalogs
      for (let i = 0; i < 4; i++) {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(emptyVotable),
        });
      }

      const catalogs: CatalogDefinition[] = [
        { ...mockCatalog, id: "cat1" },
        { ...mockCatalog, id: "cat2" },
      ];

      const results = await queryMultipleCatalogs(catalogs, 180, 45, 0.1);

      // Should return a Map with one entry per catalog
      expect(results).toBeInstanceOf(Map);
      expect(results.size).toBe(2);
      expect(results.has("cat1")).toBe(true);
      expect(results.has("cat2")).toBe(true);

      // Verify each result has the expected structure
      const cat1Result = results.get("cat1");
      expect(cat1Result?.catalogId).toBe("cat1");
      expect(cat1Result?.sources).toHaveLength(0);
      expect(cat1Result?.error).toBeUndefined();
    });
  });
});
