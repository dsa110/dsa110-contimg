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

  const mockCatalog: CatalogDefinition = {
    id: "test-catalog",
    name: "Test Catalog",
    vizierTable: "I/test",
    description: "A test catalog",
    raColumn: "ra",
    decColumn: "dec",
  };

  describe("queryCatalog", () => {
    it("should make a TAP request to VizieR", async () => {
      // Mock VOTable XML response
      const votableXml = `<?xml version="1.0" encoding="UTF-8"?>
<VOTABLE version="1.4">
  <RESOURCE type="results">
    <TABLE>
      <FIELD name="ra" datatype="double"/>
      <FIELD name="dec" datatype="double"/>
      <DATA>
        <TABLEDATA>
          <TR><TD>180.0</TD><TD>45.0</TD></TR>
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
    });

    it("should handle empty results", async () => {
      const emptyVotable = `<?xml version="1.0" encoding="UTF-8"?>
<VOTABLE version="1.4">
  <RESOURCE type="results">
    <TABLE>
      <FIELD name="ra" datatype="double"/>
      <FIELD name="dec" datatype="double"/>
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
      // The rate limiter and async nature makes detailed testing complex
      // Just verify that the function returns a Map with expected structure
      const emptyVotable = `<?xml version="1.0"?>
<VOTABLE><RESOURCE type="results"><TABLE><DATA><TABLEDATA></TABLEDATA></DATA></TABLE></RESOURCE></VOTABLE>`;

      // Mock enough responses for potential retries
      for (let i = 0; i < 4; i++) {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve(emptyVotable),
        });
      }

      const catalogs = [
        { ...mockCatalog, id: "cat1" },
        { ...mockCatalog, id: "cat2" },
      ];

      const results = await queryMultipleCatalogs(catalogs, 180, 45, 0.1);

      // Should return a Map with one entry per catalog
      expect(results).toBeInstanceOf(Map);
      expect(results.size).toBe(2);
      expect(results.has("cat1")).toBe(true);
      expect(results.has("cat2")).toBe(true);
    });
  });
});
