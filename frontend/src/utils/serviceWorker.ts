/**
 * Service Worker Registration
 * Registers the service worker for offline support
 */

export function registerServiceWorker(): void {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("/service-worker.js")
        .then((registration) => {
          console.log("Service Worker registered:", registration.scope);

          // Check for updates periodically
          setInterval(() => {
            registration.update();
          }, 60000); // Check every minute

          // Handle updates
          registration.addEventListener("updatefound", () => {
            const newWorker = registration.installing;
            if (newWorker) {
              newWorker.addEventListener("statechange", () => {
                if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
                  // New service worker available
                  console.log("New service worker available");
                  // Optionally notify user to refresh
                }
              });
            }
          });
        })
        .catch((error) => {
          console.warn("Service Worker registration failed:", error);
        });
    });
  }
}

export function unregisterServiceWorker(): void {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready.then((registration) => {
      registration.unregister();
    });
  }
}
