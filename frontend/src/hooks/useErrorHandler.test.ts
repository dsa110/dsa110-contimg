import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import useErrorHandler from "./useErrorHandler";
import type { ErrorResponse } from "../types/errors";

describe("useErrorHandler", () => {
  describe("initial state", () => {
    it("returns null error initially", () => {
      const { result } = renderHook(() => useErrorHandler());
      expect(result.current.error).toBeNull();
    });

    it("returns handleError function", () => {
      const { result } = renderHook(() => useErrorHandler());
      expect(typeof result.current.handleError).toBe("function");
    });

    it("returns clearError function", () => {
      const { result } = renderHook(() => useErrorHandler());
      expect(typeof result.current.clearError).toBe("function");
    });
  });

  describe("handleError", () => {
    it("sets error state when called", () => {
      const { result } = renderHook(() => useErrorHandler());

      const errorResponse: ErrorResponse = {
        code: "MS_NOT_FOUND",
        http_status: 404,
        user_message: "Measurement Set not found",
        action: "Check the path",
        ref_id: "job-123",
      };

      act(() => {
        result.current.handleError(errorResponse);
      });

      expect(result.current.error).toEqual(errorResponse);
    });

    it("replaces previous error with new error", () => {
      const { result } = renderHook(() => useErrorHandler());

      const firstError: ErrorResponse = {
        code: "MS_NOT_FOUND",
        http_status: 404,
        user_message: "First error",
        action: "First action",
        ref_id: "ref-1",
      };

      const secondError: ErrorResponse = {
        code: "NETWORK_ERROR",
        http_status: 0,
        user_message: "Second error",
        action: "Second action",
        ref_id: "ref-2",
      };

      act(() => {
        result.current.handleError(firstError);
      });
      expect(result.current.error).toEqual(firstError);

      act(() => {
        result.current.handleError(secondError);
      });
      expect(result.current.error).toEqual(secondError);
    });

    it("preserves all ErrorResponse fields", () => {
      const { result } = renderHook(() => useErrorHandler());

      const fullError: ErrorResponse = {
        code: "CAL_TABLE_MISSING",
        http_status: 400,
        user_message: "Calibration missing",
        action: "Re-run calibration",
        ref_id: "job-456",
        details: { path: "/data/cal.table", scan: 5 },
        trace_id: "trace-abc-123",
        doc_anchor: "calibration_missing_table",
      };

      act(() => {
        result.current.handleError(fullError);
      });

      expect(result.current.error?.code).toBe("CAL_TABLE_MISSING");
      expect(result.current.error?.http_status).toBe(400);
      expect(result.current.error?.user_message).toBe("Calibration missing");
      expect(result.current.error?.action).toBe("Re-run calibration");
      expect(result.current.error?.ref_id).toBe("job-456");
      expect(result.current.error?.details).toEqual({ path: "/data/cal.table", scan: 5 });
      expect(result.current.error?.trace_id).toBe("trace-abc-123");
      expect(result.current.error?.doc_anchor).toBe("calibration_missing_table");
    });
  });

  describe("clearError", () => {
    it("clears error state when called", () => {
      const { result } = renderHook(() => useErrorHandler());

      const errorResponse: ErrorResponse = {
        code: "NETWORK_ERROR",
        http_status: 0,
        user_message: "Network error",
        action: "Retry",
        ref_id: "ref-1",
      };

      act(() => {
        result.current.handleError(errorResponse);
      });
      expect(result.current.error).not.toBeNull();

      act(() => {
        result.current.clearError();
      });
      expect(result.current.error).toBeNull();
    });

    it("is safe to call when no error is set", () => {
      const { result } = renderHook(() => useErrorHandler());

      expect(result.current.error).toBeNull();

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });

    it("can be called multiple times", () => {
      const { result } = renderHook(() => useErrorHandler());

      act(() => {
        result.current.clearError();
        result.current.clearError();
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe("function stability", () => {
    it("handleError maintains referential stability", () => {
      const { result, rerender } = renderHook(() => useErrorHandler());

      const handleError1 = result.current.handleError;
      rerender();
      const handleError2 = result.current.handleError;

      expect(handleError1).toBe(handleError2);
    });

    it("clearError maintains referential stability", () => {
      const { result, rerender } = renderHook(() => useErrorHandler());

      const clearError1 = result.current.clearError;
      rerender();
      const clearError2 = result.current.clearError;

      expect(clearError1).toBe(clearError2);
    });
  });

  describe("workflow scenarios", () => {
    it("handles error -> clear -> new error workflow", () => {
      const { result } = renderHook(() => useErrorHandler());

      const error1: ErrorResponse = {
        code: "ERROR_1",
        http_status: 400,
        user_message: "Error 1",
        action: "Action 1",
        ref_id: "ref-1",
      };

      const error2: ErrorResponse = {
        code: "ERROR_2",
        http_status: 500,
        user_message: "Error 2",
        action: "Action 2",
        ref_id: "ref-2",
      };

      // Set first error
      act(() => {
        result.current.handleError(error1);
      });
      expect(result.current.error?.code).toBe("ERROR_1");

      // Clear it
      act(() => {
        result.current.clearError();
      });
      expect(result.current.error).toBeNull();

      // Set second error
      act(() => {
        result.current.handleError(error2);
      });
      expect(result.current.error?.code).toBe("ERROR_2");
    });
  });
});
