export { default as SkyCoverageMap } from "./SkyCoverageMap";
export type {
  SkyCoverageMapProps,
  Pointing,
  ConstellationOptions,
  SurveyFootprint,
} from "./SkyCoverageMap";
export { SURVEY_FOOTPRINTS } from "./SkyCoverageMap";

export { default as SkyCoverageMapSimple } from "./SkyCoverageMapSimple";
export type { SkyCoverageMapSimpleProps } from "./SkyCoverageMapSimple";

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
