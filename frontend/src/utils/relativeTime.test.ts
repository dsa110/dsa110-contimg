import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { relativeTime } from "./relativeTime";

describe("relativeTime", () => {
  beforeEach(() => {
    // Fix the current time for consistent tests
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-06-15T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("just now / seconds", () => {
    it('returns "just now" for timestamps within 1 second', () => {
      const now = new Date().toISOString();
      expect(relativeTime(now)).toBe("just now");
    });

    it('returns "just now" for 1 second ago', () => {
      const oneSecondAgo = new Date(Date.now() - 1000).toISOString();
      expect(relativeTime(oneSecondAgo)).toBe("just now");
    });

    it("returns seconds ago for 2-59 seconds", () => {
      const thirtySecondsAgo = new Date(Date.now() - 30 * 1000).toISOString();
      expect(relativeTime(thirtySecondsAgo)).toBe("30 seconds ago");
    });
  });

  describe("minutes", () => {
    it('returns "1 minute ago" for 60-119 seconds', () => {
      const oneMinuteAgo = new Date(Date.now() - 60 * 1000).toISOString();
      expect(relativeTime(oneMinuteAgo)).toBe("1 minute ago");
    });

    it("returns plural minutes for 2+ minutes", () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      expect(relativeTime(fiveMinutesAgo)).toBe("5 minutes ago");
    });

    it("returns 59 minutes for just under an hour", () => {
      const fiftyNineMinutesAgo = new Date(Date.now() - 59 * 60 * 1000).toISOString();
      expect(relativeTime(fiftyNineMinutesAgo)).toBe("59 minutes ago");
    });
  });

  describe("hours", () => {
    it('returns "1 hour ago" for 1 hour', () => {
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
      expect(relativeTime(oneHourAgo)).toBe("1 hour ago");
    });

    it("returns plural hours for 2+ hours", () => {
      const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(threeHoursAgo)).toBe("3 hours ago");
    });

    it("returns 23 hours for just under a day", () => {
      const twentyThreeHoursAgo = new Date(Date.now() - 23 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(twentyThreeHoursAgo)).toBe("23 hours ago");
    });
  });

  describe("days", () => {
    it('returns "1 day ago" for 1 day', () => {
      const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(oneDayAgo)).toBe("1 day ago");
    });

    it("returns plural days for 2+ days", () => {
      const fiveDaysAgo = new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(fiveDaysAgo)).toBe("5 days ago");
    });

    it("returns days for up to ~30 days", () => {
      const twentyNineDaysAgo = new Date(Date.now() - 29 * 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(twentyNineDaysAgo)).toBe("29 days ago");
    });
  });

  describe("months", () => {
    it('returns "1 month ago" for ~30 days', () => {
      const oneMonthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(oneMonthAgo)).toBe("1 month ago");
    });

    it("returns plural months for 2+ months", () => {
      const threeMonthsAgo = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(threeMonthsAgo)).toBe("3 months ago");
    });

    it("returns months for up to ~11 months", () => {
      const elevenMonthsAgo = new Date(Date.now() - 330 * 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(elevenMonthsAgo)).toBe("11 months ago");
    });
  });

  describe("years", () => {
    it('returns "1 year ago" for ~365 days', () => {
      const oneYearAgo = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(oneYearAgo)).toBe("1 year ago");
    });

    it("returns plural years for 2+ years", () => {
      const threeYearsAgo = new Date(Date.now() - 3 * 365 * 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(threeYearsAgo)).toBe("3 years ago");
    });
  });

  describe("future dates", () => {
    it('returns "in the future" for future timestamps', () => {
      const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(tomorrow)).toBe("in the future");
    });

    it('returns "in the future" for timestamps 1 second in future', () => {
      const oneSecondFuture = new Date(Date.now() + 1000).toISOString();
      expect(relativeTime(oneSecondFuture)).toBe("in the future");
    });
  });

  describe("edge cases", () => {
    it("handles ISO string format", () => {
      const timestamp = "2024-06-15T11:59:00Z";
      expect(relativeTime(timestamp)).toBe("1 minute ago");
    });

    it("handles date string with timezone", () => {
      const timestamp = "2024-06-15T12:00:00+00:00";
      expect(relativeTime(timestamp)).toBe("just now");
    });

    it("handles very old dates", () => {
      const tenYearsAgo = new Date(Date.now() - 10 * 365 * 24 * 60 * 60 * 1000).toISOString();
      expect(relativeTime(tenYearsAgo)).toBe("10 years ago");
    });
  });
});
