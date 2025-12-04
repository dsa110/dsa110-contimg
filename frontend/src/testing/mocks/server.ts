/**
 * MSW Server Configuration
 *
 * Sets up a mock server for testing that intercepts HTTP requests.
 * This provides contract-based testing - tests verify against
 * realistic API responses rather than mocking internal modules.
 *
 * Note: MSW 2.x requires localStorage to be available at import time
 * for its internal CookieStore. The msw-setup.ts file ensures
 * localStorage is polyfilled before this module loads.
 */

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
