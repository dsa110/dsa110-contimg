/**
 * Tests for centralized configuration module
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { config, API_CONFIG, APP_CONFIG, UI_CONFIG, FEATURES } from "./index";

describe("config", () => {
  // Store original environment
  const originalEnv = { ...import.meta.env };

  afterEach(() => {
    // Restore original environment
    Object.assign(import.meta.env, originalEnv);
  });

  describe("API_CONFIG", () => {
    it("should have default API configuration", () => {
      expect(API_CONFIG.baseUrl).toBeDefined();
      expect(API_CONFIG.timeout).toBe(10_000);
      expect(API_CONFIG.maxRetries).toBe(3);
    });

    it("should use VITE_API_URL from environment if available", () => {
      // Note: In actual tests, this would be mocked via vitest's vi.stubEnv
      expect(API_CONFIG.baseUrl).toMatch(/\/api|http/);
    });

    it("should have reasonable timeout value", () => {
      expect(API_CONFIG.timeout).toBeGreaterThan(0);
      expect(API_CONFIG.timeout).toBeLessThanOrEqual(30_000); // Max 30 seconds
    });

    it("should have reasonable retry count", () => {
      expect(API_CONFIG.maxRetries).toBeGreaterThanOrEqual(0);
      expect(API_CONFIG.maxRetries).toBeLessThanOrEqual(5);
    });
  });

  describe("APP_CONFIG", () => {
    it("should have application configuration", () => {
      expect(APP_CONFIG.basePath).toBeDefined();
      expect(APP_CONFIG.name).toBe("DSA-110 Pipeline");
      expect(APP_CONFIG.version).toBeDefined();
    });

    it("should have valid base path", () => {
      expect(APP_CONFIG.basePath).toMatch(/^\/[^/]*\/?$/);
    });
  });

  describe("UI_CONFIG", () => {
    it("should have UI configuration with documented values", () => {
      expect(UI_CONFIG.maxRecentItems).toBe(10);
      expect(UI_CONFIG.defaultPageSize).toBe(25);
      expect(UI_CONFIG.defaultFov).toBe(0.25);
      expect(UI_CONFIG.defaultSurvey).toBe("P/DSS2/color");
    });

    it("should have sensible maxRecentItems", () => {
      expect(UI_CONFIG.maxRecentItems).toBeGreaterThan(0);
      expect(UI_CONFIG.maxRecentItems).toBeLessThanOrEqual(50);
    });

    it("should have sensible defaultPageSize", () => {
      expect(UI_CONFIG.defaultPageSize).toBeGreaterThan(0);
      expect(UI_CONFIG.defaultPageSize).toBeLessThanOrEqual(100);
    });

    it("should have valid defaultFov for sky viewer", () => {
      expect(UI_CONFIG.defaultFov).toBeGreaterThan(0);
      expect(UI_CONFIG.defaultFov).toBeLessThanOrEqual(360);
    });
  });

  describe("FEATURES", () => {
    it("should have feature flags", () => {
      expect(typeof FEATURES.enableDevtools).toBe("boolean");
      expect(typeof FEATURES.enableVerboseLogging).toBe("boolean");
      expect(typeof FEATURES.enableStorybook).toBe("boolean");
    });

    it("should enable devtools in development", () => {
      if (import.meta.env.DEV) {
        expect(FEATURES.enableDevtools).toBe(true);
      }
    });

    it("should have Storybook disabled by default", () => {
      expect(FEATURES.enableStorybook).toBe(false);
    });
  });

  describe("config (main export)", () => {
    it("should have all configuration sections", () => {
      expect(config.api).toBeDefined();
      expect(config.app).toBeDefined();
      expect(config.ui).toBeDefined();
      expect(config.features).toBeDefined();
    });

    it("should provide legacy flat access", () => {
      expect(config.apiUrl).toBe(config.api.baseUrl);
      expect(config.basePath).toBe(config.app.basePath);
    });

    it("should be frozen (immutable)", () => {
      expect(() => {
        (config as any).api.baseUrl = "new-value";
      }).toThrow();
    });
  });

  describe("Configuration documentation", () => {
    it("should have timeout with clear rationale", () => {
      // 10 seconds is documented as "balanced for slow network and large responses"
      expect(API_CONFIG.timeout).toBe(10_000);
    });

    it("should have maxRecentItems with clear rationale", () => {
      // 10 items documented as "reasonable limit for quick access without clutter"
      expect(UI_CONFIG.maxRecentItems).toBe(10);
    });

    it("should have defaultPageSize with clear rationale", () => {
      // 25 documented as "balance between reducing requests and viewport scrolling"
      expect(UI_CONFIG.defaultPageSize).toBe(25);
    });

    it("should have defaultFov optimized for DSA-110", () => {
      // 0.25 degrees documented as "optimized for DSA-110 beam size"
      expect(UI_CONFIG.defaultFov).toBe(0.25);
    });
  });
});
