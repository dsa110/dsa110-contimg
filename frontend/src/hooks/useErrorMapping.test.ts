import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import useErrorMapping from "./useErrorMapping";
import type { ErrorResponse } from "../types/errors";

describe("useErrorMapping", () => {
  describe("known error codes", () => {
    it("maps CAL_TABLE_MISSING correctly", () => {
      const errorResponse: ErrorResponse = {
        code: "CAL_TABLE_MISSING",
        http_status: 400,
        user_message: "Backend message",
        action: "Backend action",
        ref_id: "ref-1",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.user_message).toBe(
        "Calibration table not found for this Measurement Set"
      );
      expect(result.current.action).toBe("Re-run calibration or choose an existing table");
    });

    it("maps MS_NOT_FOUND correctly", () => {
      const errorResponse: ErrorResponse = {
        code: "MS_NOT_FOUND",
        http_status: 404,
        user_message: "Not found",
        action: "Check path",
        ref_id: "ref-2",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.user_message).toBe("Measurement Set not found");
      expect(result.current.action).toBe("Confirm path exists; rescan MS directory");
    });

    it("maps NETWORK_ERROR correctly", () => {
      const errorResponse: ErrorResponse = {
        code: "NETWORK_ERROR",
        http_status: 0,
        user_message: "Network failed",
        action: "Try again",
        ref_id: "ref-3",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.user_message).toBe("Unable to reach the server");
      expect(result.current.action).toBe("Check your connection and try again");
    });

    it("maps IMAGE_CLEAN_FAILED correctly", () => {
      const errorResponse: ErrorResponse = {
        code: "IMAGE_CLEAN_FAILED",
        http_status: 500,
        user_message: "Clean failed",
        action: "Retry",
        ref_id: "ref-4",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.user_message).toBe("Imaging step failed");
      expect(result.current.action).toBe("Check imaging parameters; retry");
    });
  });

  describe("unknown error codes", () => {
    it("returns default message for unknown error code", () => {
      const errorResponse: ErrorResponse = {
        code: "UNKNOWN_ERROR_XYZ",
        http_status: 500,
        user_message: "Something happened",
        action: "Do something",
        ref_id: "ref-5",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.user_message).toBe("An unexpected error occurred.");
      expect(result.current.action).toBe("Please try again later.");
    });

    it("returns default for empty string error code", () => {
      const errorResponse: ErrorResponse = {
        code: "",
        http_status: 500,
        user_message: "Error",
        action: "Action",
        ref_id: "ref-6",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.user_message).toBe("An unexpected error occurred.");
    });
  });

  describe("passthrough fields", () => {
    it("passes through details from error response", () => {
      const details = { path: "/data/test.ms", param: 42 };
      const errorResponse: ErrorResponse = {
        code: "MS_NOT_FOUND",
        http_status: 404,
        user_message: "Not found",
        action: "Check path",
        ref_id: "ref-7",
        details,
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.details).toEqual(details);
    });

    it("returns empty object when details is undefined", () => {
      const errorResponse: ErrorResponse = {
        code: "MS_NOT_FOUND",
        http_status: 404,
        user_message: "Not found",
        action: "Check path",
        ref_id: "ref-8",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.details).toEqual({});
    });

    it("passes through trace_id from error response", () => {
      const errorResponse: ErrorResponse = {
        code: "NETWORK_ERROR",
        http_status: 0,
        user_message: "Network failed",
        action: "Retry",
        ref_id: "ref-9",
        trace_id: "trace-abc-123",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.trace_id).toBe("trace-abc-123");
    });

    it("returns empty string when trace_id is undefined", () => {
      const errorResponse: ErrorResponse = {
        code: "NETWORK_ERROR",
        http_status: 0,
        user_message: "Network failed",
        action: "Retry",
        ref_id: "ref-10",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.trace_id).toBe("");
    });

    it("passes through doc_anchor from error response", () => {
      const errorResponse: ErrorResponse = {
        code: "RATE_LIMITED",
        http_status: 429,
        user_message: "Rate limited",
        action: "Wait",
        ref_id: "ref-11",
        doc_anchor: "rate-limiting-docs",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.doc_anchor).toBe("rate-limiting-docs");
    });

    it("returns empty string when doc_anchor is undefined", () => {
      const errorResponse: ErrorResponse = {
        code: "RATE_LIMITED",
        http_status: 429,
        user_message: "Rate limited",
        action: "Wait",
        ref_id: "ref-12",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current.doc_anchor).toBe("");
    });
  });

  describe("memoization", () => {
    it("returns same result object when errorResponse is unchanged", () => {
      const errorResponse: ErrorResponse = {
        code: "MS_NOT_FOUND",
        http_status: 404,
        user_message: "Not found",
        action: "Check",
        ref_id: "ref-13",
      };

      const { result, rerender } = renderHook(() => useErrorMapping(errorResponse));

      const firstResult = result.current;
      rerender();
      const secondResult = result.current;

      // useMemo should return the same object reference
      expect(firstResult).toBe(secondResult);
    });

    it("returns new result object when errorResponse changes", () => {
      const errorResponse1: ErrorResponse = {
        code: "MS_NOT_FOUND",
        http_status: 404,
        user_message: "Not found",
        action: "Check",
        ref_id: "ref-14",
      };

      const errorResponse2: ErrorResponse = {
        code: "NETWORK_ERROR",
        http_status: 0,
        user_message: "Network error",
        action: "Retry",
        ref_id: "ref-15",
      };

      const { result, rerender } = renderHook(({ error }) => useErrorMapping(error), {
        initialProps: { error: errorResponse1 },
      });

      const firstResult = result.current;
      rerender({ error: errorResponse2 });
      const secondResult = result.current;

      // Should be different objects with different messages
      expect(firstResult.user_message).toBe("Measurement Set not found");
      expect(secondResult.user_message).toBe("Unable to reach the server");
    });
  });

  describe("return shape", () => {
    it("returns all expected fields", () => {
      const errorResponse: ErrorResponse = {
        code: "CAL_APPLY_FAILED",
        http_status: 500,
        user_message: "Failed",
        action: "Retry",
        ref_id: "ref-16",
        details: { error: "timeout" },
        trace_id: "trace-xyz",
        doc_anchor: "cal-docs",
      };

      const { result } = renderHook(() => useErrorMapping(errorResponse));

      expect(result.current).toHaveProperty("user_message");
      expect(result.current).toHaveProperty("action");
      expect(result.current).toHaveProperty("details");
      expect(result.current).toHaveProperty("trace_id");
      expect(result.current).toHaveProperty("doc_anchor");
    });
  });
});
