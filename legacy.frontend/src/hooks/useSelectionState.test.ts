/**
 * Unit tests for selection state logic
 * This isolates the complex selection logic for easier testing
 */

import { describe, it, expect } from "vitest";
import { computeSelectedMS } from "../utils/selectionLogic";

describe("Selection State Logic", () => {
  describe("Adding items", () => {
    it("should select newly added item", () => {
      const result = computeSelectedMS(
        ["/data/ms1.ms", "/data/ms2.ms"],
        ["/data/ms1.ms"],
        "/data/ms1.ms"
      );
      expect(result).toBe("/data/ms2.ms");
    });

    it("should select first item when adding multiple items", () => {
      const result = computeSelectedMS(["/data/ms1.ms", "/data/ms2.ms", "/data/ms3.ms"], [], "");
      expect(result).toBe("/data/ms1.ms");
    });
  });

  describe("Removing items", () => {
    it("should keep selectedMS if still in list", () => {
      const result = computeSelectedMS(
        ["/data/ms1.ms"],
        ["/data/ms1.ms", "/data/ms2.ms"],
        "/data/ms1.ms"
      );
      expect(result).toBe("/data/ms1.ms");
    });

    it("should switch to first remaining item when selectedMS is removed", () => {
      const result = computeSelectedMS(
        ["/data/ms2.ms"],
        ["/data/ms1.ms", "/data/ms2.ms"],
        "/data/ms1.ms"
      );
      expect(result).toBe("/data/ms2.ms");
    });

    it("should clear selectedMS when all items removed", () => {
      const result = computeSelectedMS([], ["/data/ms1.ms"], "/data/ms1.ms");
      expect(result).toBe("");
    });
  });

  describe("Edge cases", () => {
    it("should handle empty initial selection", () => {
      const result = computeSelectedMS(["/data/ms1.ms"], [], "");
      expect(result).toBe("/data/ms1.ms");
    });

    it("should handle reordering with same items", () => {
      const result = computeSelectedMS(
        ["/data/ms2.ms", "/data/ms1.ms"],
        ["/data/ms1.ms", "/data/ms2.ms"],
        "/data/ms1.ms"
      );
      expect(result).toBe("/data/ms1.ms");
    });
  });
});
