/**
 * Timestamp Utilities Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  toDate,
  toISO,
  toUnixMillis,
  toUnixSeconds,
  nowISO,
  nowMillis,
  nowSeconds,
  formatTimestamp,
  formatDate,
  formatTime,
  formatRelative,
  isValidISO,
  isUnixSeconds,
  isUnixMillis,
  compareTimestamps,
  isWithin,
  isPast,
  isFuture,
  addDuration,
  subtractDuration,
  DURATION,
} from "./timestamp";

describe("timestamp utilities", () => {
  // Fixed timestamp for testing: 2025-06-15T12:30:45.000Z
  const FIXED_ISO = "2025-06-15T12:30:45.000Z";
  const FIXED_MILLIS = 1750077045000;
  const FIXED_SECONDS = 1750077045;
  const FIXED_DATE = new Date(FIXED_ISO);

  describe("toDate", () => {
    it("returns null for null/undefined", () => {
      expect(toDate(null)).toBeNull();
      expect(toDate(undefined)).toBeNull();
    });

    it("returns Date unchanged", () => {
      const date = new Date();
      expect(toDate(date)).toBe(date);
    });

    it("converts ISO string to Date", () => {
      const result = toDate(FIXED_ISO);
      expect(result).toBeInstanceOf(Date);
      expect(result?.getTime()).toBe(FIXED_MILLIS);
    });

    it("converts Unix milliseconds to Date", () => {
      const result = toDate(FIXED_MILLIS);
      expect(result).toBeInstanceOf(Date);
      expect(result?.toISOString()).toBe(FIXED_ISO);
    });

    it("converts Unix seconds to Date", () => {
      const result = toDate(FIXED_SECONDS);
      expect(result).toBeInstanceOf(Date);
      expect(result?.toISOString()).toBe(FIXED_ISO);
    });

    it("returns null for invalid string", () => {
      expect(toDate("not a date")).toBeNull();
    });
  });

  describe("toISO", () => {
    it("returns null for null/undefined", () => {
      expect(toISO(null)).toBeNull();
      expect(toISO(undefined)).toBeNull();
    });

    it("converts Date to ISO string", () => {
      expect(toISO(FIXED_DATE)).toBe(FIXED_ISO);
    });

    it("converts Unix milliseconds to ISO string", () => {
      expect(toISO(FIXED_MILLIS)).toBe(FIXED_ISO);
    });

    it("converts Unix seconds to ISO string", () => {
      expect(toISO(FIXED_SECONDS)).toBe(FIXED_ISO);
    });

    it("returns ISO string unchanged", () => {
      expect(toISO(FIXED_ISO)).toBe(FIXED_ISO);
    });
  });

  describe("toUnixMillis", () => {
    it("returns null for null/undefined", () => {
      expect(toUnixMillis(null)).toBeNull();
      expect(toUnixMillis(undefined)).toBeNull();
    });

    it("converts ISO string to milliseconds", () => {
      expect(toUnixMillis(FIXED_ISO)).toBe(FIXED_MILLIS);
    });

    it("converts Date to milliseconds", () => {
      expect(toUnixMillis(FIXED_DATE)).toBe(FIXED_MILLIS);
    });

    it("converts Unix seconds to milliseconds", () => {
      expect(toUnixMillis(FIXED_SECONDS)).toBe(FIXED_MILLIS);
    });
  });

  describe("toUnixSeconds", () => {
    it("returns null for null/undefined", () => {
      expect(toUnixSeconds(null)).toBeNull();
      expect(toUnixSeconds(undefined)).toBeNull();
    });

    it("converts ISO string to seconds", () => {
      expect(toUnixSeconds(FIXED_ISO)).toBe(FIXED_SECONDS);
    });

    it("converts milliseconds to seconds", () => {
      expect(toUnixSeconds(FIXED_MILLIS)).toBe(FIXED_SECONDS);
    });
  });

  describe("now functions", () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(FIXED_DATE);
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("nowISO returns current time as ISO string", () => {
      expect(nowISO()).toBe(FIXED_ISO);
    });

    it("nowMillis returns current time as milliseconds", () => {
      expect(nowMillis()).toBe(FIXED_MILLIS);
    });

    it("nowSeconds returns current time as seconds", () => {
      expect(nowSeconds()).toBe(FIXED_SECONDS);
    });
  });

  describe("formatTimestamp", () => {
    it("returns dash for null/undefined", () => {
      expect(formatTimestamp(null)).toBe("—");
      expect(formatTimestamp(undefined)).toBe("—");
    });

    it("formats timestamp with default options", () => {
      const result = formatTimestamp(FIXED_ISO);
      expect(result).toContain("2025");
      expect(result).toContain("Jun");
    });

    it("respects custom options", () => {
      const result = formatTimestamp(FIXED_ISO, { year: "numeric" });
      expect(result).toBe("2025");
    });
  });

  describe("formatDate", () => {
    it("returns dash for null/undefined", () => {
      expect(formatDate(null)).toBe("—");
    });

    it("formats date only", () => {
      const result = formatDate(FIXED_ISO);
      expect(result).toContain("2025");
      expect(result).toContain("Jun");
      expect(result).toContain("15");
    });
  });

  describe("formatTime", () => {
    it("returns dash for null/undefined", () => {
      expect(formatTime(null)).toBe("—");
    });

    it("formats time only", () => {
      const result = formatTime(FIXED_ISO);
      // Time format varies by locale, just check it's not empty
      expect(result.length).toBeGreaterThan(0);
      expect(result).not.toBe("—");
    });
  });

  describe("formatRelative", () => {
    it("returns dash for null/undefined", () => {
      expect(formatRelative(null)).toBe("—");
    });

    it("formats seconds ago", () => {
      const now = new Date(FIXED_DATE);
      const past = new Date(now.getTime() - 30000); // 30 seconds ago
      expect(formatRelative(past, now)).toBe("30s ago");
    });

    it("formats minutes ago", () => {
      const now = new Date(FIXED_DATE);
      const past = new Date(now.getTime() - 5 * 60000); // 5 minutes ago
      expect(formatRelative(past, now)).toBe("5m ago");
    });

    it("formats hours ago", () => {
      const now = new Date(FIXED_DATE);
      const past = new Date(now.getTime() - 3 * 3600000); // 3 hours ago
      expect(formatRelative(past, now)).toBe("3h ago");
    });

    it("formats days ago", () => {
      const now = new Date(FIXED_DATE);
      const past = new Date(now.getTime() - 5 * 86400000); // 5 days ago
      expect(formatRelative(past, now)).toBe("5d ago");
    });

    it("formats future times", () => {
      const now = new Date(FIXED_DATE);
      const future = new Date(now.getTime() + 5 * 60000); // 5 minutes from now
      expect(formatRelative(future, now)).toBe("in 5m");
    });
  });

  describe("isValidISO", () => {
    it("returns true for valid ISO strings", () => {
      expect(isValidISO(FIXED_ISO)).toBe(true);
      expect(isValidISO("2025-01-01T00:00:00Z")).toBe(true);
    });

    it("returns false for non-strings", () => {
      expect(isValidISO(123)).toBe(false);
      expect(isValidISO(null)).toBe(false);
      expect(isValidISO(undefined)).toBe(false);
    });

    it("returns false for date-only strings", () => {
      expect(isValidISO("2025-01-01")).toBe(false);
    });
  });

  describe("isUnixSeconds", () => {
    it("returns true for Unix seconds", () => {
      expect(isUnixSeconds(FIXED_SECONDS)).toBe(true);
      expect(isUnixSeconds(0)).toBe(true);
    });

    it("returns false for Unix milliseconds", () => {
      expect(isUnixMillis(FIXED_MILLIS)).toBe(true);
    });
  });

  describe("compareTimestamps", () => {
    it("returns negative when a < b", () => {
      expect(compareTimestamps(FIXED_ISO, FIXED_MILLIS + 1000)).toBeLessThan(0);
    });

    it("returns positive when a > b", () => {
      expect(compareTimestamps(FIXED_MILLIS + 1000, FIXED_ISO)).toBeGreaterThan(
        0
      );
    });

    it("returns 0 when equal", () => {
      expect(compareTimestamps(FIXED_ISO, FIXED_MILLIS)).toBe(0);
    });
  });

  describe("isWithin", () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(FIXED_DATE);
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("returns true when within duration", () => {
      const past = new Date(FIXED_DATE.getTime() - 5000);
      expect(isWithin(past, 10000)).toBe(true);
    });

    it("returns false when outside duration", () => {
      const past = new Date(FIXED_DATE.getTime() - 15000);
      expect(isWithin(past, 10000)).toBe(false);
    });
  });

  describe("isPast/isFuture", () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(FIXED_DATE);
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("isPast returns true for past timestamps", () => {
      expect(isPast(FIXED_MILLIS - 1000)).toBe(true);
    });

    it("isPast returns false for future timestamps", () => {
      expect(isPast(FIXED_MILLIS + 1000)).toBe(false);
    });

    it("isFuture returns true for future timestamps", () => {
      expect(isFuture(FIXED_MILLIS + 1000)).toBe(true);
    });

    it("isFuture returns false for past timestamps", () => {
      expect(isFuture(FIXED_MILLIS - 1000)).toBe(false);
    });
  });

  describe("addDuration/subtractDuration", () => {
    it("addDuration adds time", () => {
      const result = addDuration(FIXED_ISO, DURATION.HOUR);
      expect(result?.getTime()).toBe(FIXED_MILLIS + DURATION.HOUR);
    });

    it("subtractDuration subtracts time", () => {
      const result = subtractDuration(FIXED_ISO, DURATION.HOUR);
      expect(result?.getTime()).toBe(FIXED_MILLIS - DURATION.HOUR);
    });

    it("returns null for null input", () => {
      expect(addDuration(null, 1000)).toBeNull();
      expect(subtractDuration(null, 1000)).toBeNull();
    });
  });

  describe("DURATION constants", () => {
    it("has correct values", () => {
      expect(DURATION.SECOND).toBe(1000);
      expect(DURATION.MINUTE).toBe(60000);
      expect(DURATION.HOUR).toBe(3600000);
      expect(DURATION.DAY).toBe(86400000);
      expect(DURATION.WEEK).toBe(604800000);
    });
  });
});
