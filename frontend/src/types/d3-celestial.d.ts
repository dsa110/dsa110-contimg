/**
 * Type declarations for d3-celestial library
 * @see https://github.com/ofrohn/d3-celestial
 */

declare module "d3-celestial" {
  export interface CelestialConfig {
    /** Default width, 0 = full parent element width */
    width?: number;
    /** Map projection: aitoff, azimuthalEqualArea, azimuthalEquidistant, etc. */
    projection?: string;
    /** Coordinate transformation: equatorial, ecliptic, galactic, supergalactic */
    transform?: string;
    /** Initial center coordinates [longitude, latitude, orientation] in degrees */
    center?: [number, number, number] | null;
    /** Keep orientation angle the same as center[2] */
    orientationfixed?: boolean;
    /** Optional initial geographic position [lat, lon] in degrees */
    geopos?: [number, number] | null;
    /** On which coordinates to center the map */
    follow?: string;
    /** Initial zoom level 0...zoomextend */
    zoomlevel?: number | null;
    /** Maximum zoom level */
    zoomextend?: number;
    /** Sizes are increased with higher zoom-levels */
    adaptable?: boolean;
    /** Enable zooming and rotation with mousewheel and dragging */
    interactive?: boolean;
    /** Display form for interactive settings */
    form?: boolean;
    /** Display location settings */
    location?: boolean;
    /** Set visibility for each group of form fields */
    formFields?: {
      location?: boolean;
      general?: boolean;
      stars?: boolean;
      dsos?: boolean;
      constellations?: boolean;
      lines?: boolean;
      other?: boolean;
    };
    /** Calendar date range */
    daterange?: number[];
    /** ID of parent element */
    container?: string;
    /** Path/URL to data files */
    datapath?: string;
    /** Language for names (de, es, etc.) */
    lang?: string;
    /** Source of constellations and star names */
    culture?: string;

    /** Stars configuration */
    stars?: {
      show?: boolean;
      limit?: number;
      colors?: boolean;
      style?: { fill?: string; opacity?: number };
      designation?: boolean;
      designationType?: string;
      designationStyle?: {
        fill?: string;
        font?: string;
        align?: string;
        baseline?: string;
      };
      designationLimit?: number;
      propername?: boolean;
      propernameType?: string;
      propernameStyle?: {
        fill?: string;
        font?: string;
        align?: string;
        baseline?: string;
      };
      propernameLimit?: number;
      size?: number;
      exponent?: number;
    };

    /** Deep Sky Objects configuration */
    dsos?: {
      show?: boolean;
      limit?: number;
      colors?: boolean;
      style?: { fill?: string; stroke?: string; width?: number; opacity?: number };
      names?: boolean;
      namesType?: string;
      nameStyle?: {
        fill?: string;
        font?: string;
        align?: string;
        baseline?: string;
      };
      nameLimit?: number;
      size?: number | null;
      exponent?: number;
      data?: string;
    };

    /** Constellations configuration */
    constellations?: {
      names?: boolean;
      namesType?: string;
      nameStyle?: {
        fill?: string;
        align?: string;
        baseline?: string;
        font?: string | string[];
      };
      lines?: boolean;
      lineStyle?: { stroke?: string; width?: number; opacity?: number };
      bounds?: boolean;
      boundStyle?: {
        stroke?: string;
        width?: number;
        opacity?: number;
        dash?: number[];
      };
    };

    /** Milky Way configuration */
    mw?: {
      show?: boolean;
      style?: { fill?: string; opacity?: number };
    };

    /** Lines configuration (graticule, ecliptic, etc.) */
    lines?: {
      graticule?: {
        show?: boolean;
        stroke?: string;
        width?: number;
        opacity?: number;
        lon?: { pos?: string[]; fill?: string; font?: string };
        lat?: { pos?: string[]; fill?: string; font?: string };
      };
      equatorial?: { show?: boolean; stroke?: string; width?: number; opacity?: number };
      ecliptic?: { show?: boolean; stroke?: string; width?: number; opacity?: number };
      galactic?: { show?: boolean; stroke?: string; width?: number; opacity?: number };
      supergalactic?: { show?: boolean; stroke?: string; width?: number; opacity?: number };
    };

    /** Background configuration */
    background?: {
      fill?: string;
      opacity?: number;
      stroke?: string;
      width?: number;
    };

    /** Horizon configuration */
    horizon?: {
      show?: boolean;
      stroke?: string;
      width?: number;
      fill?: string;
      opacity?: number;
    };

    /** Daylight configuration */
    daylight?: {
      show?: boolean;
    };
  }

  export interface CelestialSource {
    ra: number;
    dec: number;
    mag?: number;
    name?: string;
    [key: string]: unknown;
  }

  export interface CelestialCatalog {
    add: (sources: CelestialSource[]) => void;
    clear: () => void;
    style: (style: Record<string, unknown>) => void;
  }

  export interface Celestial {
    version: string;
    container: unknown;
    data: unknown[];
    display: (config: CelestialConfig) => void;
    apply: (config: Partial<CelestialConfig>) => void;
    rotate: (config: { center: [number, number, number] }) => void;
    redraw: () => void;
    resize: (config?: { width?: number }) => void;
    clear: () => void;
    zoomBy: (factor: number) => void;
    add: (options: {
      type: string;
      callback: (error: unknown, json: unknown) => void;
      file?: string;
      filter?: unknown;
      save?: () => void;
      redraw?: () => void;
    }) => void;
    addCallback: (callback: () => void) => void;
    remove: (type: string) => void;
    projection: (proj: string) => unknown;
    container: HTMLElement | null;
  }

  const celestial: Celestial;
  export default celestial;
}

// Also declare it as a global since it attaches to window
declare global {
  interface Window {
    Celestial: import("d3-celestial").Celestial;
  }
}
