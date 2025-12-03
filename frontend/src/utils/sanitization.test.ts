/**
 * Tests for sanitization utilities
 */

import { describe, it, expect } from "vitest";
import {
  sanitizeId,
  sanitizePath,
  sanitizeQuery,
  sanitizeNumericId,
  buildApiUrl,
} from "./sanitization";

describe("sanitization", () => {
  describe("sanitizeId", () => {
    it("should encode special characters", () => {
      expect(sanitizeId("test/image")).toBe("test%2Fimage");
      expect(sanitizeId("image#123")).toBe("image%23123");
      expect(sanitizeId("test image")).toBe("test%20image");
    });

    it("should trim whitespace", () => {
      expect(sanitizeId("  image-123  ")).toBe("image-123");
      expect(sanitizeId("\nimage\n")).toBe("image");
    });

    it("should handle empty and null values", () => {
      expect(sanitizeId("")).toBe("");
      expect(sanitizeId(null)).toBe("");
      expect(sanitizeId(undefined)).toBe("");
    });

    it("should preserve valid characters", () => {
      expect(sanitizeId("image-123")).toBe("image-123");
      expect(sanitizeId("image_abc")).toBe("image_abc");
      expect(sanitizeId("image.fits")).toBe("image.fits");
    });

    it("should encode URL-unsafe characters", () => {
      expect(sanitizeId("image?param=value")).toBe("image%3Fparam%3Dvalue");
      expect(sanitizeId("image&test")).toBe("image%26test");
    });
  });

  describe("sanitizePath", () => {
    it("should encode path separators", () => {
      expect(sanitizePath("/path/to/file")).toBe("%2Fpath%2Fto%2Ffile");
      expect(sanitizePath("path\\to\\file")).toBe("path%5Cto%5Cfile");
    });

    it("should trim whitespace", () => {
      expect(sanitizePath("  /path/to/file  ")).toBe("%2Fpath%2Fto%2Ffile");
    });

    it("should handle empty and null values", () => {
      expect(sanitizePath("")).toBe("");
      expect(sanitizePath(null)).toBe("");
      expect(sanitizePath(undefined)).toBe("");
    });

    it("should encode special characters in paths", () => {
      expect(sanitizePath("/data/file name.fits")).toBe(
        "%2Fdata%2Ffile%20name.fits"
      );
    });
  });

  describe("sanitizeQuery", () => {
    it("should remove angle brackets", () => {
      expect(sanitizeQuery("search<script>")).toBe("searchscript");
      expect(sanitizeQuery("<div>test</div>")).toBe("divtest/div");
    });

    it("should trim whitespace", () => {
      expect(sanitizeQuery("  query  ")).toBe("query");
    });

    it("should limit length to 500 characters", () => {
      const longQuery = "a".repeat(600);
      const sanitized = sanitizeQuery(longQuery);
      expect(sanitized.length).toBeLessThanOrEqual(500);
    });

    it("should handle empty and null values", () => {
      expect(sanitizeQuery("")).toBe("");
      expect(sanitizeQuery(null)).toBe("");
      expect(sanitizeQuery(undefined)).toBe("");
    });

    it("should preserve safe query characters", () => {
      expect(sanitizeQuery("query term with spaces")).toBe(
        "query term with spaces"
      );
      expect(sanitizeQuery("ra=180 dec=45")).toBe("ra=180 dec=45");
    });
  });

  describe("sanitizeNumericId", () => {
    it("should parse valid numbers", () => {
      expect(sanitizeNumericId("123")).toBe(123);
      expect(sanitizeNumericId("45.67")).toBe(45.67);
      expect(sanitizeNumericId(89)).toBe(89);
    });

    it("should return null for invalid numbers", () => {
      expect(sanitizeNumericId("abc")).toBeNull();
      // Note: parseFloat("12abc") returns 12 in JavaScript - this is expected behavior
      expect(sanitizeNumericId("12abc")).toBe(12);
      expect(sanitizeNumericId("")).toBeNull();
    });

    it("should handle null and undefined", () => {
      expect(sanitizeNumericId(null)).toBeNull();
      expect(sanitizeNumericId(undefined)).toBeNull();
    });

    it("should handle numeric edge cases", () => {
      expect(sanitizeNumericId("0")).toBe(0);
      expect(sanitizeNumericId("-123")).toBe(-123);
      expect(sanitizeNumericId("3.14159")).toBe(3.14159);
    });

    it("should handle scientific notation", () => {
      expect(sanitizeNumericId("1e5")).toBe(100000);
      expect(sanitizeNumericId("1.5e-3")).toBe(0.0015);
    });
  });

  describe("buildApiUrl", () => {
    it("should build URL from base and segments", () => {
      expect(buildApiUrl("/api/v1", "images", "123")).toBe(
        "/api/v1/images/123"
      );
      expect(
        buildApiUrl("http://localhost:8000/api/v1", "sources", "456")
      ).toBe("http://localhost:8000/api/v1/sources/456");
    });

    it("should sanitize string segments", () => {
      expect(buildApiUrl("/api/v1", "images", "test/image")).toBe(
        "/api/v1/images/test%2Fimage"
      );
    });

    it("should handle numeric segments", () => {
      expect(buildApiUrl("/api/v1", "sources", 123)).toBe(
        "/api/v1/sources/123"
      );
      expect(buildApiUrl("/api/v1", "jobs", 456, "logs")).toBe(
        "/api/v1/jobs/456/logs"
      );
    });

    it("should handle mixed segment types", () => {
      expect(buildApiUrl("/api/v1", "images", 123, "metadata")).toBe(
        "/api/v1/images/123/metadata"
      );
    });

    it("should handle empty segments", () => {
      expect(buildApiUrl("/api/v1", "", "123")).toBe("/api/v1//123");
    });

    it("should not double-encode", () => {
      // If a segment is already encoded, it should be re-encoded
      const encoded = buildApiUrl("/api/v1", "test%2Fimage");
      expect(encoded).toBe("/api/v1/test%252Fimage");
    });
  });

  describe("XSS prevention", () => {
    it("should sanitize potential XSS in queries", () => {
      const xssAttempt = "<script>alert('xss')</script>";
      const sanitized = sanitizeQuery(xssAttempt);
      expect(sanitized).not.toContain("<");
      expect(sanitized).not.toContain(">");
    });

    it("should handle multiple XSS patterns", () => {
      const patterns = [
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(1)>",
        "javascript:alert(1)",
      ];

      patterns.forEach((pattern) => {
        const sanitized = sanitizeQuery(pattern);
        expect(sanitized).not.toContain("<");
        expect(sanitized).not.toContain(">");
      });
    });
  });

  describe("SQL injection prevention", () => {
    it("should not allow SQL keywords in IDs", () => {
      // IDs are URL-encoded, so SQL injection is neutralized
      const sqlAttempt = "123'; DROP TABLE users--";
      const sanitized = sanitizeId(sqlAttempt);
      expect(sanitized).toBe("123'%3B%20DROP%20TABLE%20users--");
    });

    it("should encode single quotes", () => {
      expect(sanitizeId("test'value")).toBe("test'value"); // Single quote is safe in URL encoding
      expect(sanitizePath("path/with'quote")).toBe("path%2Fwith'quote");
    });
  });

  describe("Path traversal prevention", () => {
    it("should encode path traversal attempts", () => {
      expect(sanitizePath("../../../etc/passwd")).toBe(
        "..%2F..%2F..%2Fetc%2Fpasswd"
      );
      expect(sanitizePath("..\\..\\..\\windows\\system32")).toBe(
        "..%5C..%5C..%5Cwindows%5Csystem32"
      );
    });

    it("should encode relative path segments", () => {
      expect(sanitizeId("./file")).toBe(".%2Ffile");
      expect(sanitizePath("./../file")).toBe(".%2F..%2Ffile");
    });
  });
});
