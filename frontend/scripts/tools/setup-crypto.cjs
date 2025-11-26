/**
 * Crypto polyfill setup for Node.js v16 compatibility with Vite 6
 * This must run before Vite loads to ensure crypto.getRandomValues is available
 */
const { webcrypto } = require('node:crypto');

// Ensure Web Crypto API exists early for Vite startup
if (typeof globalThis.crypto === "undefined") {
  globalThis.crypto = webcrypto;
}

// Ensure getRandomValues is available (required by Vite)
if (globalThis.crypto && !globalThis.crypto.getRandomValues) {
  globalThis.crypto.getRandomValues = webcrypto.getRandomValues.bind(webcrypto);
}

// Export to ensure module is loaded
module.exports = {};

