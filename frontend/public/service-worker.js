/**
 * Service Worker for Offline Support
 * Provides caching and offline functionality
 */

const SW_VERSION = "2025-02-17";
const CACHE_NAME = `dsa110-dashboard-${SW_VERSION}`;

// The scope is set when the worker is registered (e.g. http://host/ui/)
// We use it to derive absolute URLs for assets we want to cache.
const scopeUrl = new URL(self.registration?.scope ?? self.location.origin + "/");
const APP_ROOT_URL = scopeUrl.href.endsWith("/") ? scopeUrl.href : `${scopeUrl.href}/`;

const CORE_ASSETS = [APP_ROOT_URL];

function toAbsolute(path) {
  return new URL(path, scopeUrl).toString();
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(CORE_ASSETS))
      .catch((error) => {
        console.warn("[SW] Failed to pre-cache core assets", error);
      })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) =>
        Promise.all(
          cacheNames.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))
        )
      )
  );
  self.clients.claim();
});

function isNavigationRequest(request) {
  return (
    request.mode === "navigate" ||
    (request.destination === "document" &&
      request.method === "GET" &&
      request.headers.get("accept")?.includes("text/html"))
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;

  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);
  const isSameOrigin = url.origin === self.location.origin;

  if (!isSameOrigin) {
    return;
  }

  if (request.url.includes("/api/")) {
    return;
  }

  if (isNavigationRequest(request)) {
    event.respondWith(networkFirst(request));
    return;
  }

  event.respondWith(cacheFirst(request));
});

function networkFirst(request) {
  return fetch(request)
    .then((response) => {
      if (response && response.ok) {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
      }
      return response;
    })
    .catch(() => caches.match(request).then((cached) => cached || caches.match(toAbsolute("./"))));
}

function cacheFirst(request) {
  return caches.match(request).then((cachedResponse) => {
    if (cachedResponse) {
      return cachedResponse;
    }

    return fetch(request)
      .then((response) => {
        if (response && response.status === 200 && response.type === "basic") {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => {
        if (request.destination === "document") {
          return caches.match(toAbsolute("./"));
        }
        return new Response("Offline", {
          status: 503,
          statusText: "Service Unavailable",
        });
      });
  });
}

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
