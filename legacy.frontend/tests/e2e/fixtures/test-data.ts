/**
 * Test data fixtures for E2E tests
 */

export const testImageData = {
  sampleImageId: "test-image-001",
  sampleImagePath: "/api/images/test-image-001",
  sampleImageName: "test_image_2025-01-01T12:00:00.fits",
};

export const testSourceData = {
  sampleSourceId: "test-source-001",
  sampleSourceName: "Test Source 1",
  sampleRA: 180.0,
  sampleDec: 45.0,
};

export const testAPIPaths = {
  status: "/api/status",
  metrics: "/api/metrics/system",
  images: "/api/images",
  sources: "/api/sources/search",
  pointing: "/api/pointing/history",
  ese: "/api/ese/candidates",
};

export const testSelectors = {
  skyViewDisplay: "#skyViewDisplay",
  quickAnalysisPanel: '[data-testid="quick-analysis-panel"]',
  photometryPlugin: '[data-testid="photometry-plugin"]',
  imageBrowser: '[data-testid="image-browser"]',
  dashboardNav: '[data-testid="dashboard-nav"]',
};

export const testRoutes = {
  dashboard: "/dashboard",
  sky: "/sky",
  control: "/control",
  streaming: "/streaming",
  data: "/data",
  qa: "/qa",
  sources: "/sources",
  observing: "/observing",
  health: "/health",
};
