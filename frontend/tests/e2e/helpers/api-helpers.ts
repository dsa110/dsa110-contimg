import { Page, expect } from "@playwright/test";

/**
 * Helper functions for API testing and verification
 */

/**
 * Wait for a specific API request to complete
 */
export async function waitForAPIRequest(
  page: Page,
  urlPattern: string | RegExp,
  timeout = 10000
): Promise<void> {
  await page.waitForResponse(
    (response) => {
      const url = response.url();
      return typeof urlPattern === "string" ? url.includes(urlPattern) : urlPattern.test(url);
    },
    { timeout }
  );
}

/**
 * Verify API response contains expected data
 */
export async function verifyAPIResponseData(
  page: Page,
  urlPattern: string | RegExp,
  dataValidator: (data: any) => boolean,
  timeout = 10000
): Promise<boolean> {
  const response = await page
    .waitForResponse(
      (response) => {
        const url = response.url();
        return typeof urlPattern === "string" ? url.includes(urlPattern) : urlPattern.test(url);
      },
      { timeout }
    )
    .catch(() => null);

  if (!response) return false;

  try {
    const data = await response.json();
    return dataValidator(data);
  } catch {
    return false;
  }
}

/**
 * Check if API endpoint is accessible
 */
export async function checkAPIEndpoint(
  page: Page,
  endpoint: string,
  expectedStatus = 200
): Promise<boolean> {
  try {
    const response = await page.request.get(endpoint);
    return response.status() === expectedStatus;
  } catch {
    return false;
  }
}

/**
 * Monitor API requests during a test
 */
export class APIMonitor {
  private requests: Array<{ url: string; status: number; timestamp: number }> = [];

  constructor(private page: Page) {
    this.setupMonitoring();
  }

  private setupMonitoring(): void {
    this.page.on("response", (response) => {
      const url = response.url();
      // Only track API requests
      if (url.includes("/api/")) {
        this.requests.push({
          url,
          status: response.status(),
          timestamp: Date.now(),
        });
      }
    });
  }

  getRequests(): Array<{ url: string; status: number; timestamp: number }> {
    return [...this.requests];
  }

  getRequestsByPattern(
    pattern: string | RegExp
  ): Array<{ url: string; status: number; timestamp: number }> {
    return this.requests.filter((req) => {
      return typeof pattern === "string" ? req.url.includes(pattern) : pattern.test(req.url);
    });
  }

  getFailedRequests(): Array<{ url: string; status: number; timestamp: number }> {
    return this.requests.filter((req) => req.status >= 400);
  }

  clear(): void {
    this.requests = [];
  }

  waitForRequest(pattern: string | RegExp, timeout = 10000): Promise<void> {
    return this.page.waitForResponse(
      (response) => {
        const url = response.url();
        return typeof pattern === "string" ? url.includes(pattern) : pattern.test(url);
      },
      { timeout }
    );
  }
}
