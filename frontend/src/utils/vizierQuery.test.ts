import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock fetch for testing
const mockFetch = vi.fn();
global.fetch = mockFetch;

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
    it("should make a TAP request with correct parameters", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () =>
          Promise.resolve(`ra,dec,id
180.0,45.0,src1
180.1,45.1,src2`),
      });

      const result = await queryCatalog(mockCatalog, 180, 45, 0.1);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toContain("tapvizier.cds.unistra.fr");
      expect(options.method).toBe("POST");
      expect(options.body).toBeInstanceOf(FormData);
    });

    it("should parse CSV response correctly", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () =>
          Promise.resolve(`ra,dec,id,mag
180.0,45.0,src1,12.5
180.1,45.1,src2,14.2`),
      });

      const result = await queryCatalog(mockCatalog, 180, 45, 0.1);

      expect(result.sources).toHaveLength(2);
      expect(result.sources[0]).toMatchObject({
        ra: 180.0,
        dec: 45.0,
        id: expect.any(String),
        catalog: "test-catalog",
      });
    });

    it("should handle empty results", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve("ra,dec,id\n"),
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

    it("should detect truncated results", async () => {
      // Generate 1000 rows (the max limit)
      const rows = Array.from(
        { length: 1000 },
        (_, i) => `${180 + i * 0.001},${45 + i * 0.001},src${i}`
      );
      const csvData = `ra,dec,id\n${rows.join("\n")}`;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: () => Promise.resolve(csvData),
      });

      const result = await queryCatalog(mockCatalog, 180, 45, 1);

      expect(result.count).toBe(1000);
      expect(result.truncated).toBe(true);
    });
  });

  describe("queryMultipleCatalogs", () => {
    it("should query multiple catalogs with rate limiting", async () => {
      // Mock responses for two catalogs
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve("ra,dec,id\n180.0,45.0,src1"),
        })
        .mockResolvedValueOnce({
          ok: true,
          text: () => Promise.resolve("ra,dec,id\n180.1,45.1,src2"),
        });

      const catalogs = [
        { ...mockCatalog, id: "cat1" },
        { ...mockCatalog, id: "cat2" },
      ];

      const results = await queryMultipleCatalogs(catalogs, 180, 45, 0.1);

      expect(results).toHaveLength(2);
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });
});
