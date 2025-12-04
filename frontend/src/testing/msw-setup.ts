/**
 * MSW Pre-Setup
 * 
 * This file provides localStorage polyfill BEFORE MSW is imported.
 * It must be loaded before any other test setup files.
 * 
 * MSW 2.x's CookieStore class instantiates at module level and
 * requires localStorage to be a function-based Storage implementation.
 */

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

// Apply localStorage polyfill to globalThis
Object.defineProperty(globalThis, "localStorage", {
  value: createStorageMock(),
  writable: true,
  configurable: true,
});

export {};
