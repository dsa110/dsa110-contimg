/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  fetchWithRetry,
  parseExternalServiceError,
  DEFAULT_EXTERNAL_RETRY_CONFIG,
  RATE_LIMITED_RETRY_CONFIG,
} from "./fetchWithRetry";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("fetchWithRetry", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns response on first successful attempt", async () => {
    const mockResponse = new Response(JSON.stringify({ data: "test" }), {
      status: 200,
      statusText: "OK",
    });
    mockFetch.mockResolvedValueOnce(mockResponse);

    const response = await fetchWithRetry("https://example.com/api");

    expect(response).toBe(mockResponse);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("retries on 500 status and succeeds", async () => {
    const failResponse = new Response(null, { status: 500, statusText: "Server Error" });
    const successResponse = new Response(JSON.stringify({ data: "test" }), {
      status: 200,
      statusText: "OK",
    });

    mockFetch.mockResolvedValueOnce(failResponse).mockResolvedValueOnce(successResponse);

    const fetchPromise = fetchWithRetry("https://example.com/api", {}, { maxRetries: 2 });

    // Fast-forward through the retry delay
    await vi.advanceTimersByTimeAsync(2000);

    const response = await fetchPromise;

    expect(response).toBe(successResponse);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("retries on 429 (rate limit) status", async () => {
    const rateLimitResponse = new Response(null, {
      status: 429,
      statusText: "Too Many Requests",
    });
    const successResponse = new Response(JSON.stringify({ data: "test" }), {
      status: 200,
      statusText: "OK",
    });

    mockFetch.mockResolvedValueOnce(rateLimitResponse).mockResolvedValueOnce(successResponse);

    const fetchPromise = fetchWithRetry("https://example.com/api", {}, { maxRetries: 2 });

    await vi.advanceTimersByTimeAsync(3000);

    const response = await fetchPromise;

    expect(response).toBe(successResponse);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("retries on network error and succeeds", async () => {
    const networkError = new TypeError("Failed to fetch");
    const successResponse = new Response(JSON.stringify({ data: "test" }), {
      status: 200,
      statusText: "OK",
    });

    mockFetch.mockRejectedValueOnce(networkError).mockResolvedValueOnce(successResponse);

    const fetchPromise = fetchWithRetry("https://example.com/api", {}, { maxRetries: 2 });

    await vi.advanceTimersByTimeAsync(3000);

    const response = await fetchPromise;

    expect(response).toBe(successResponse);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("throws after exhausting all retries", async () => {
    const failResponse = new Response(null, { status: 503, statusText: "Service Unavailable" });

    mockFetch.mockResolvedValue(failResponse);

    const fetchPromise = fetchWithRetry(
      "https://example.com/api",
      {},
      { maxRetries: 2, baseDelayMs: 100, maxDelayMs: 500 }
    );

    // Fast-forward through all retry delays
    await vi.advanceTimersByTimeAsync(10000);

    await expect(fetchPromise).rejects.toThrow(/failed after 3 attempts/);
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it("does not retry on 400 client errors", async () => {
    const badRequestResponse = new Response(null, { status: 400, statusText: "Bad Request" });

    mockFetch.mockResolvedValueOnce(badRequestResponse);

    const response = await fetchWithRetry("https://example.com/api", {}, { maxRetries: 3 });

    expect(response.status).toBe(400);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("respects abort signal", async () => {
    const controller = new AbortController();

    mockFetch.mockImplementation(async (_url, options) => {
      if (options?.signal?.aborted) {
        throw new DOMException("Aborted", "AbortError");
      }
      // Simulate slow response
      await new Promise((resolve) => setTimeout(resolve, 5000));
      return new Response(JSON.stringify({ data: "test" }), { status: 200 });
    });

    const fetchPromise = fetchWithRetry(
      "https://example.com/api",
      { signal: controller.signal },
      { maxRetries: 2 }
    );

    // Abort immediately
    controller.abort();

    // Advance timers to allow abort to propagate
    await vi.advanceTimersByTimeAsync(100);

    await expect(fetchPromise).rejects.toThrow("Aborted");
  });

  it("passes custom headers to fetch", async () => {
    const successResponse = new Response(JSON.stringify({ data: "test" }), {
      status: 200,
      statusText: "OK",
    });
    mockFetch.mockResolvedValueOnce(successResponse);

    await fetchWithRetry(
      "https://example.com/api",
      {
        headers: {
          Accept: "application/xml",
          "X-Custom": "value",
        },
      },
      { maxRetries: 1 }
    );

    expect(mockFetch).toHaveBeenCalledWith(
      "https://example.com/api",
      expect.objectContaining({
        headers: {
          Accept: "application/xml",
          "X-Custom": "value",
        },
      })
    );
  });

  it("respects Retry-After header for 429 responses", async () => {
    const headers = new Headers();
    headers.set("Retry-After", "5");

    const rateLimitResponse = new Response(null, {
      status: 429,
      statusText: "Too Many Requests",
      headers,
    });
    const successResponse = new Response(JSON.stringify({ data: "test" }), {
      status: 200,
      statusText: "OK",
    });

    mockFetch.mockResolvedValueOnce(rateLimitResponse).mockResolvedValueOnce(successResponse);

    const fetchPromise = fetchWithRetry(
      "https://example.com/api",
      {},
      { maxRetries: 2, baseDelayMs: 100 } // Small base delay to verify Retry-After is used
    );

    // Advance by 5 seconds (the Retry-After value)
    await vi.advanceTimersByTimeAsync(5000);

    const response = await fetchPromise;

    expect(response).toBe(successResponse);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });
});

describe("parseExternalServiceError", () => {
  it("handles abort errors", () => {
    const error = new DOMException("Aborted", "AbortError");
    expect(parseExternalServiceError(error, "TestService")).toBe("Request was cancelled");
  });

  it("handles timeout errors", () => {
    const error = new Error("Request timeout after 30000ms");
    expect(parseExternalServiceError(error, "VizieR")).toBe(
      "VizieR is taking too long to respond. Please try again."
    );
  });

  it("handles network/CORS errors", () => {
    const error = new Error("Failed to fetch");
    expect(parseExternalServiceError(error, "Sesame")).toBe(
      "Could not connect to Sesame. The service may be down or blocked by CORS."
    );
  });

  it("handles rate limit (429) errors", () => {
    const error = new Error("HTTP 429 Too Many Requests");
    expect(parseExternalServiceError(error, "VizieR")).toBe(
      "VizieR rate limit exceeded. Please wait a moment and try again."
    );
  });

  it("handles service unavailable (503) errors", () => {
    const error = new Error("HTTP 503 Service Unavailable");
    expect(parseExternalServiceError(error, "SIMBAD")).toBe(
      "SIMBAD is temporarily unavailable. Please try again later."
    );
  });

  it("handles generic errors", () => {
    const error = new Error("Something went wrong");
    expect(parseExternalServiceError(error, "TestService")).toBe("Something went wrong");
  });

  it("handles non-Error objects", () => {
    expect(parseExternalServiceError("string error", "TestService")).toBe(
      "An unexpected error occurred with TestService"
    );
  });
});

describe("config presets", () => {
  it("DEFAULT_EXTERNAL_RETRY_CONFIG has reasonable defaults", () => {
    expect(DEFAULT_EXTERNAL_RETRY_CONFIG.maxRetries).toBe(3);
    expect(DEFAULT_EXTERNAL_RETRY_CONFIG.baseDelayMs).toBe(1000);
    expect(DEFAULT_EXTERNAL_RETRY_CONFIG.timeoutMs).toBe(30000);
    expect(DEFAULT_EXTERNAL_RETRY_CONFIG.retryStatusCodes).toContain(503);
    expect(DEFAULT_EXTERNAL_RETRY_CONFIG.retryStatusCodes).toContain(429);
  });

  it("RATE_LIMITED_RETRY_CONFIG is more conservative", () => {
    expect(RATE_LIMITED_RETRY_CONFIG.maxRetries).toBeLessThan(
      DEFAULT_EXTERNAL_RETRY_CONFIG.maxRetries
    );
    expect(RATE_LIMITED_RETRY_CONFIG.baseDelayMs).toBeGreaterThan(
      DEFAULT_EXTERNAL_RETRY_CONFIG.baseDelayMs
    );
    expect(RATE_LIMITED_RETRY_CONFIG.backoffMultiplier).toBeGreaterThan(
      DEFAULT_EXTERNAL_RETRY_CONFIG.backoffMultiplier
    );
  });
});
