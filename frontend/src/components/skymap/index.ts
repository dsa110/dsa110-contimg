export { default as SkyCoverageMap } from "./SkyCoverageMap";
export type { SkyCoverageMapProps, Pointing, ConstellationOptions } from "./SkyCoverageMap";

export { CelestialMap } from "./CelestialMap";
export type {
  CelestialMapProps,
  CelestialMapConfig,
  CelestialMarker,
  StarConfig,
  DSOConfig,
  ConstellationConfig,
  LinesConfig,
} from "./CelestialMap";

// Utility exports for reusable sky map functions
export * from "./projectionUtils";
export * from "./gridUtils";
