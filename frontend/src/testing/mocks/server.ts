/**
 * MSW Server Configuration
 *
 * Sets up a mock server for testing that intercepts HTTP requests.
 * This provides contract-based testing - tests verify against
 * realistic API responses rather than mocking internal modules.
 *
 * Note: MSW 2.x requires localStorage to be available at import time
 * for its internal CookieStore. We ensure it exists before importing.
 */

// Ensure localStorage polyfill exists for MSW's CookieStore
// jsdom may provide a partial localStorage that causes issues with MSW
const createStorageMock = (): Storage => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
    get length() {
      return Object.keys(store).length;
    },
  };
};

// Force localStorage to be a proper Storage implementation
// This fixes MSW 2.x CookieStore initialization issues with jsdom
if (
  typeof globalThis.localStorage === "undefined" ||
  typeof globalThis.localStorage?.getItem !== "function"
) {
  Object.defineProperty(globalThis, "localStorage", {
    value: createStorageMock(),
    writable: true,
    configurable: true,
  });
}

import { setupServer } from "msw/node";
import { defaultHandlers } from "./handlers";

/**
 * MSW server instance for tests.
 *
 * Usage in tests:
 *   import { server } from '../../testing/mocks/server';
 *
 *   beforeAll(() => server.listen());
 *   afterEach(() => server.resetHandlers());
 *   afterAll(() => server.close());
 *
 * To override handlers for specific tests:
 *   server.use(
 *     http.get('/api/endpoint', () => HttpResponse.json({ custom: 'data' }))
 *   );
 */
export const server = setupServer(...defaultHandlers);
