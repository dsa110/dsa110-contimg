import { describe, it, expect } from "vitest";
import { mapErrorResponse } from "./errorMapper";
import { errorMappings } from "../constants/errorMappings";
import type { ErrorResponse, MappedError } from "../types/errors";

describe("mapErrorResponse", () => {
  describe("known error codes", () => {
    it("maps CAL_TABLE_MISSING to correct user message and action", () => {
      const result = mapErrorResponse({ code: "CAL_TABLE_MISSING" });
      expect(result.user_message).toBe("Calibration table not found for this Measurement Set");
      expect(result.action).toBe("Re-run calibration or choose an existing table");
      expect(result.severity).toBe("warn");
      expect(result.doc_anchor).toBe("calibration_missing_table");
    });

    it("maps IMAGE_CLEAN_FAILED to error severity", () => {
      const result = mapErrorResponse({ code: "IMAGE_CLEAN_FAILED" });
      expect(result.user_message).toBe("Imaging step failed");
      expect(result.action).toBe("Check imaging parameters; retry");
      expect(result.severity).toBe("error");
      expect(result.doc_anchor).toBe("imaging_tclean_failed");
    });

    it("maps MS_NOT_FOUND correctly", () => {
      const result = mapErrorResponse({ code: "MS_NOT_FOUND" });
      expect(result.user_message).toBe("Measurement Set not found");
      expect(result.action).toBe("Confirm path exists; rescan MS directory");
      expect(result.severity).toBe("error");
    });

    it("maps RATE_LIMITED to warn severity without doc_anchor", () => {
      const result = mapErrorResponse({ code: "RATE_LIMITED" });
      expect(result.user_message).toBe("Too many requests");
      expect(result.action).toBe("Wait and retry; reduce polling");
      expect(result.severity).toBe("warn");
      expect(result.doc_anchor).toBeUndefined();
    });

    it("maps ABSURD_DISABLED to info severity", () => {
      const result = mapErrorResponse({ code: "ABSURD_DISABLED" });
      expect(result.user_message).toBe("Task queue service is disabled");
      expect(result.severity).toBe("info");
    });

    it("maps NETWORK_ERROR correctly", () => {
      const result = mapErrorResponse({ code: "NETWORK_ERROR" });
      expect(result.user_message).toBe("Unable to reach the server");
      expect(result.action).toBe("Check your connection and try again");
      expect(result.severity).toBe("error");
    });

    it("maps all defined error codes", () => {
      // Test all codes in errorMappings are properly mapped
      Object.keys(errorMappings).forEach((code) => {
        const result = mapErrorResponse({ code });
        const expected = errorMappings[code];
        expect(result.user_message).toBe(expected.user_message);
        expect(result.action).toBe(expected.action);
        expect(result.severity).toBe(expected.severity);
      });
    });
  });

  describe("fallback behavior", () => {
    it("falls back to default message for unknown error code", () => {
      const result = mapErrorResponse({ code: "UNKNOWN_CODE_XYZ" });
      expect(result.user_message).toBe("Request failed");
      expect(result.action).toBe("Please try again later");
      expect(result.severity).toBe("error");
    });

    it("falls back when error response is empty", () => {
      const result = mapErrorResponse({});
      expect(result.user_message).toBe("Request failed");
      expect(result.action).toBe("Please try again later");
      expect(result.severity).toBe("error");
    });

    it("falls back when error response is undefined", () => {
      const result = mapErrorResponse(undefined);
      expect(result.user_message).toBe("Request failed");
      expect(result.action).toBe("Please try again later");
      expect(result.severity).toBe("error");
    });

    it("falls back when code is missing", () => {
      const result = mapErrorResponse({ ref_id: "some-ref" });
      expect(result.user_message).toBe("Request failed");
      expect(result.action).toBe("Please try again later");
    });
  });

  describe("passthrough fields", () => {
    it("passes through ref_id from error response", () => {
      const result = mapErrorResponse({
        code: "MS_NOT_FOUND",
        ref_id: "job-12345",
      });
      expect(result.ref_id).toBe("job-12345");
    });

    it("passes through trace_id from error response", () => {
      const result = mapErrorResponse({
        code: "IMAGE_CLEAN_FAILED",
        trace_id: "trace-abc-def",
      });
      expect(result.trace_id).toBe("trace-abc-def");
    });

    it("passes through details object from error response", () => {
      const details = { path: "/data/test.ms", param: 42 };
      const result = mapErrorResponse({
        code: "MS_NOT_FOUND",
        details,
      });
      expect(result.details).toEqual(details);
    });

    it("preserves all passthrough fields together", () => {
      const input: Partial<ErrorResponse> = {
        code: "VALIDATION_FAILED",
        ref_id: "ref-123",
        trace_id: "trace-456",
        details: { field: "ra_deg", issue: "out of range" },
      };
      const result = mapErrorResponse(input);
      expect(result.ref_id).toBe("ref-123");
      expect(result.trace_id).toBe("trace-456");
      expect(result.details).toEqual({ field: "ra_deg", issue: "out of range" });
    });
  });

  describe("doc_anchor handling", () => {
    it("uses mapped doc_anchor when error code has one", () => {
      const result = mapErrorResponse({
        code: "CAL_TABLE_MISSING",
        doc_anchor: "user-provided-anchor",
      });
      // Mapped anchor takes precedence
      expect(result.doc_anchor).toBe("calibration_missing_table");
    });

    it("uses error response doc_anchor when mapping has none", () => {
      const result = mapErrorResponse({
        code: "RATE_LIMITED",
        doc_anchor: "rate-limiting-docs",
      });
      // RATE_LIMITED has no doc_anchor in mapping, so use provided one
      expect(result.doc_anchor).toBe("rate-limiting-docs");
    });

    it("returns undefined doc_anchor when neither has one", () => {
      const result = mapErrorResponse({
        code: "RATE_LIMITED",
      });
      expect(result.doc_anchor).toBeUndefined();
    });

    it("returns undefined doc_anchor for unknown code without provided anchor", () => {
      const result = mapErrorResponse({
        code: "UNKNOWN_CODE",
      });
      expect(result.doc_anchor).toBeUndefined();
    });
  });

  describe("return type compliance", () => {
    it("returns a valid MappedError shape", () => {
      const result = mapErrorResponse({
        code: "MS_NOT_FOUND",
        ref_id: "ref-1",
        details: { path: "/data/test.ms" },
        trace_id: "trace-1",
        doc_anchor: "custom-anchor",
      });

      // Verify all MappedError fields are present
      expect(result).toHaveProperty("user_message");
      expect(result).toHaveProperty("action");
      expect(result).toHaveProperty("severity");
      expect(result).toHaveProperty("ref_id");
      expect(result).toHaveProperty("details");
      expect(result).toHaveProperty("trace_id");
      expect(result).toHaveProperty("doc_anchor");

      // Verify types
      expect(typeof result.user_message).toBe("string");
      expect(typeof result.action).toBe("string");
      expect(["info", "warn", "error"]).toContain(result.severity);
    });
  });
});
