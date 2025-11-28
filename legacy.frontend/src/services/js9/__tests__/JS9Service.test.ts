/**
 * JS9Service Unit Tests
 *
 * Tests all JS9Service methods with mocked JS9 API
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { JS9Service } from "../JS9Service";

// Mock logger
vi.mock("../../../utils/logger", () => ({
  logger: {
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

declare global {
  interface Window {
    JS9: any;
  }
}

describe("JS9Service", () => {
  let service: JS9Service;
  let mockJS9: any;

  beforeEach(() => {
    service = new JS9Service();

    // Setup mock JS9
    mockJS9 = {
      Load: vi.fn(),
      Init: vi.fn(),
      SetOptions: vi.fn(),
      AddDivs: vi.fn(),
      CloseImage: vi.fn(),
      ResizeDisplay: vi.fn(),
      SetDisplay: vi.fn(),
      InstallDir: vi.fn((path: string) => `/ui/js9/${path}`),
      displays: [],
      images: {},
      opts: {},
    };

    (global as any).window = {
      JS9: mockJS9,
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
    delete (global as any).window;
  });

  describe("isAvailable", () => {
    it("should return true when JS9 is fully loaded", () => {
      expect(service.isAvailable()).toBe(true);
    });

    it("should return false when JS9 is not available", () => {
      delete (global as any).window;
      expect(service.isAvailable()).toBe(false);
    });

    it("should return false when JS9.Load is not a function", () => {
      mockJS9.Load = undefined;
      expect(service.isAvailable()).toBe(false);
    });
  });

  describe("getDisplays", () => {
    it("should return empty array when no displays exist", () => {
      expect(service.getDisplays()).toEqual([]);
    });

    it("should return all displays", () => {
      mockJS9.displays = [{ id: "display1" }, { id: "display2" }];
      expect(service.getDisplays()).toHaveLength(2);
    });

    it("should return empty array when JS9 is not available", () => {
      delete (global as any).window;
      expect(service.getDisplays()).toEqual([]);
    });
  });

  describe("findDisplay", () => {
    it("should find display by id", () => {
      mockJS9.displays = [{ id: "display1" }, { id: "display2" }];
      expect(service.findDisplay("display1")).toEqual({ id: "display1" });
    });

    it("should find display by display property", () => {
      mockJS9.displays = [{ display: "display1" }];
      expect(service.findDisplay("display1")).toEqual({ display: "display1" });
    });

    it("should find display by divID property", () => {
      mockJS9.displays = [{ divID: "display1" }];
      expect(service.findDisplay("display1")).toEqual({ divID: "display1" });
    });

    it("should return null when display not found", () => {
      mockJS9.displays = [{ id: "display1" }];
      expect(service.findDisplay("display2")).toBeNull();
    });
  });

  describe("getImageId", () => {
    it("should return image ID when display has image", () => {
      mockJS9.displays = [{ id: "display1", im: { id: "image1" } }];
      expect(service.getImageId("display1")).toBe("image1");
    });

    it("should return null when display has no image", () => {
      mockJS9.displays = [{ id: "display1" }];
      expect(service.getImageId("display1")).toBeNull();
    });

    it("should return null when display not found", () => {
      expect(service.getImageId("nonexistent")).toBeNull();
    });
  });

  describe("hasImage", () => {
    it("should return true when display has image", () => {
      mockJS9.displays = [{ id: "display1", im: { id: "image1" } }];
      expect(service.hasImage("display1")).toBe(true);
    });

    it("should return false when display has no image", () => {
      mockJS9.displays = [{ id: "display1" }];
      expect(service.hasImage("display1")).toBe(false);
    });
  });

  describe("init", () => {
    it("should initialize JS9 with options", () => {
      const options = { loadImage: false };
      service.init(options);
      expect(mockJS9.Init).toHaveBeenCalledWith(options);
    });

    it("should throw error when JS9 is not available", () => {
      delete (global as any).window;
      expect(() => service.init()).toThrow("JS9 is not available");
    });

    it("should handle Init errors gracefully", () => {
      mockJS9.Init = vi.fn(() => {
        throw new Error("Init failed");
      });
      expect(() => service.init()).toThrow();
    });
  });

  describe("setOptions", () => {
    it("should set JS9 options", () => {
      const options = { loadImage: false };
      service.setOptions(options);
      expect(mockJS9.SetOptions).toHaveBeenCalledWith(options);
    });

    it("should fallback to opts when SetOptions fails", () => {
      mockJS9.SetOptions = vi.fn(() => {
        throw new Error("SetOptions failed");
      });
      const options = { loadImage: false };
      service.setOptions(options);
      expect(mockJS9.opts.loadImage).toBe(false);
    });

    it("should throw error when JS9 is not available", () => {
      delete (global as any).window;
      expect(() => service.setOptions({})).toThrow("JS9 is not available");
    });
  });

  describe("addDivs", () => {
    it("should register div with JS9", () => {
      service.addDivs("display1");
      expect(mockJS9.AddDivs).toHaveBeenCalledWith("display1");
    });

    it("should handle AddDivs errors gracefully", () => {
      mockJS9.AddDivs = vi.fn(() => {
        throw new Error("AddDivs failed");
      });
      // Should not throw, just log
      expect(() => service.addDivs("display1")).not.toThrow();
    });

    it("should throw error when JS9 is not available", () => {
      delete (global as any).window;
      expect(() => service.addDivs("display1")).toThrow("JS9 is not available");
    });
  });

  describe("loadImage", () => {
    it("should load image with options", () => {
      const options = { divID: "display1", scale: "linear" };
      service.loadImage("image.fits", options);
      expect(mockJS9.Load).toHaveBeenCalledWith("image.fits", options);
    });

    it("should throw error when JS9 is not available", () => {
      delete (global as any).window;
      expect(() => service.loadImage("image.fits")).toThrow("JS9 is not available");
    });

    it("should throw error when Load is not available", () => {
      mockJS9.Load = undefined;
      // When Load is undefined, isAvailable() returns false, so we get "JS9 is not available"
      expect(() => service.loadImage("image.fits")).toThrow("JS9 is not available");
    });

    it("should propagate Load errors", () => {
      mockJS9.Load = vi.fn(() => {
        throw new Error("Load failed");
      });
      expect(() => service.loadImage("image.fits")).toThrow("Load failed");
    });
  });

  describe("closeImage", () => {
    it("should close image and remove from cache", () => {
      mockJS9.images = { image1: { id: "image1" } };
      service.closeImage("image1");
      expect(mockJS9.CloseImage).toHaveBeenCalledWith("image1");
      expect(mockJS9.images.image1).toBeUndefined();
    });

    it("should handle CloseImage errors gracefully", () => {
      mockJS9.CloseImage = vi.fn(() => {
        throw new Error("CloseImage failed");
      });
      // Should not throw, just log
      expect(() => service.closeImage("image1")).not.toThrow();
    });

    it("should handle missing images gracefully", () => {
      service.closeImage("nonexistent");
      expect(mockJS9.CloseImage).toHaveBeenCalledWith("nonexistent");
    });
  });

  describe("resizeDisplay", () => {
    it("should resize display", () => {
      service.resizeDisplay("display1");
      expect(mockJS9.ResizeDisplay).toHaveBeenCalledWith("display1");
    });

    it("should handle ResizeDisplay errors gracefully", () => {
      mockJS9.ResizeDisplay = vi.fn(() => {
        throw new Error("ResizeDisplay failed");
      });
      // Should not throw, just log
      expect(() => service.resizeDisplay("display1")).not.toThrow();
    });

    it("should return early when JS9 is not available", () => {
      delete (global as any).window;
      expect(() => service.resizeDisplay("display1")).not.toThrow();
    });
  });

  describe("setDisplay", () => {
    it("should set active display", () => {
      service.setDisplay("display1", "image1");
      expect(mockJS9.SetDisplay).toHaveBeenCalledWith("display1", "image1");
    });

    it("should handle SetDisplay errors gracefully", () => {
      mockJS9.SetDisplay = vi.fn(() => {
        throw new Error("SetDisplay failed");
      });
      // Should not throw, just log
      expect(() => service.setDisplay("display1", "image1")).not.toThrow();
    });
  });

  describe("getInstallDir", () => {
    it("should return InstallDir function when available", () => {
      const fn = service.getInstallDir();
      expect(typeof fn).toBe("function");
    });

    it("should return null when InstallDir is not available", () => {
      mockJS9.InstallDir = undefined;
      expect(service.getInstallDir()).toBeNull();
    });
  });

  describe("getOptions", () => {
    it("should return JS9 options", () => {
      mockJS9.opts = { loadImage: false };
      expect(service.getOptions()).toEqual({ loadImage: false });
    });

    it("should return null when opts not available", () => {
      mockJS9.opts = undefined;
      expect(service.getOptions()).toBeNull();
    });
  });

  describe("getImages", () => {
    it("should return images cache", () => {
      mockJS9.images = { image1: { id: "image1" } };
      expect(service.getImages()).toEqual({ image1: { id: "image1" } });
    });

    it("should return null when images not available", () => {
      mockJS9.images = undefined;
      expect(service.getImages()).toBeNull();
    });
  });
});
