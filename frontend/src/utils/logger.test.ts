/**
 * Tests for logger utility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { logger } from "./logger";

describe("logger", () => {
  // Mock console methods
  let consoleDebugSpy: ReturnType<typeof vi.spyOn>;
  let consoleInfoSpy: ReturnType<typeof vi.spyOn>;
  let consoleWarnSpy: ReturnType<typeof vi.spyOn>;
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    consoleDebugSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
    consoleInfoSpy = vi.spyOn(console, "info").mockImplementation(() => {});
    consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("debug", () => {
    it("should log debug messages with DEBUG prefix", () => {
      logger.debug("Test message");

      if (import.meta.env.DEV) {
        expect(consoleDebugSpy).toHaveBeenCalledWith("[DEBUG] Test message");
      }
    });

    it("should format context as JSON", () => {
      logger.debug("Test message", { key: "value", count: 42 });

      if (import.meta.env.DEV) {
        expect(consoleDebugSpy).toHaveBeenCalledWith(
          expect.stringContaining("[DEBUG] Test message")
        );
        expect(consoleDebugSpy).toHaveBeenCalledWith(
          expect.stringContaining('{"key":"value","count":42}')
        );
      }
    });

    it("should not log in production mode", () => {
      // This test is environment-dependent
      if (!import.meta.env.DEV) {
        logger.debug("Test message");
        expect(consoleDebugSpy).not.toHaveBeenCalled();
      }
    });
  });

  describe("info", () => {
    it("should log info messages with INFO prefix", () => {
      logger.info("Test message");

      if (import.meta.env.DEV) {
        expect(consoleInfoSpy).toHaveBeenCalledWith("[INFO] Test message");
      }
    });

    it("should format context as JSON", () => {
      logger.info("Test message", { status: "success" });

      if (import.meta.env.DEV) {
        expect(consoleInfoSpy).toHaveBeenCalledWith(expect.stringContaining("[INFO] Test message"));
        expect(consoleInfoSpy).toHaveBeenCalledWith(
          expect.stringContaining('{"status":"success"}')
        );
      }
    });
  });

  describe("warn", () => {
    it("should always log warnings", () => {
      logger.warn("Warning message");
      expect(consoleWarnSpy).toHaveBeenCalledWith("[WARN] Warning message");
    });

    it("should format context as JSON", () => {
      logger.warn("Warning message", { code: "WARN_001" });
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining("[WARN] Warning message")
      );
      expect(consoleWarnSpy).toHaveBeenCalledWith(expect.stringContaining('{"code":"WARN_001"}'));
    });
  });

  describe("error", () => {
    it("should always log errors", () => {
      logger.error("Error message");
      expect(consoleErrorSpy).toHaveBeenCalledWith("[ERROR] Error message");
    });

    it("should handle Error objects", () => {
      const error = new Error("Test error");
      logger.error("Error occurred", error);

      expect(consoleErrorSpy).toHaveBeenCalledWith("[ERROR] Error occurred", error);
    });

    it("should format context as JSON", () => {
      logger.error("Error message", { code: "ERR_001", severity: "high" });
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining("[ERROR] Error message")
      );
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining('{"code":"ERR_001","severity":"high"}')
      );
    });
  });

  describe("context formatting", () => {
    it("should handle empty context", () => {
      logger.warn("Message");
      expect(consoleWarnSpy).toHaveBeenCalledWith("[WARN] Message");
    });

    it("should handle nested objects in context", () => {
      logger.warn("Message", { nested: { key: "value" } });
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('{"nested":{"key":"value"}}')
      );
    });

    it("should handle arrays in context", () => {
      logger.warn("Message", { items: [1, 2, 3] });
      expect(consoleWarnSpy).toHaveBeenCalledWith(expect.stringContaining('{"items":[1,2,3]}'));
    });
  });

  describe("environment-aware logging", () => {
    it("should suppress debug logs in production", () => {
      // This verifies the isEnabled logic
      if (!import.meta.env.DEV) {
        logger.debug("Should not appear");
        logger.info("Should not appear");
        expect(consoleDebugSpy).not.toHaveBeenCalled();
        expect(consoleInfoSpy).not.toHaveBeenCalled();
      }
    });

    it("should always show warnings and errors", () => {
      logger.warn("Warning");
      logger.error("Error");

      expect(consoleWarnSpy).toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalled();
    });
  });
});
