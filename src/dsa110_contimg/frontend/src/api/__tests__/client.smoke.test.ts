import { describe, it, expect } from "vitest";
import { apiClient } from "../client";

describe("apiClient smoke", () => {
  it("is created with sensible defaults", () => {
    expect(apiClient).toBeTruthy();
    // timeout configured
    expect(apiClient.defaults.timeout).toBeGreaterThan(0);

    // baseURL should be a string ('' in test/prod, dev URL in dev)
    expect(typeof apiClient.defaults.baseURL).toBe("string");

    // Content-Type set to application/json via AxiosHeaders
    const headers: any = apiClient.defaults.headers as any;
    const contentType =
      typeof headers?.get === "function" ? headers.get("Content-Type") : headers?.["Content-Type"];
    expect(contentType).toBe("application/json");
  });
});
