/**
 * MSW Server Configuration
 *
 * Sets up a mock server for testing that intercepts HTTP requests.
 * This provides contract-based testing - tests verify against
 * realistic API responses rather than mocking internal modules.
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
