// Every external endpoint the scene uses, in one place. All were checked from the build
// container on 2026-11-14 (HTTP 200 and an Access-Control-Allow-Origin header on tiles).

export const GIBS_WMTS_4326 = 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best';

export const EARTH_LAYERS = {
  /** GIBS "Blue Marble (MODIS)", matrix set 500m (levels 0-7), JPEG. */
  blueMarble: {
    id: 'BlueMarble_NextGeneration',
    matrixSet: '500m',
    maxLevel: 7,
    format: 'image/jpeg',
    ext: 'jpeg',
    time: undefined as string | undefined,
  },
  /** GIBS "Black Marble (VIIRS, Suomi NPP)", 2016 composite, matrix set 500m, PNG. */
  blackMarble: {
    id: 'VIIRS_Black_Marble',
    matrixSet: '500m',
    maxLevel: 7,
    format: 'image/png',
    ext: 'png',
    time: '2016-01-01' as string | undefined,
  },
  /** GIBS reference labels (country, city names), matrix set 15.625m (levels 0-12), PNG. */
  labels: {
    id: 'Reference_Labels_15m',
    matrixSet: '15.625m',
    maxLevel: 12,
    format: 'image/png',
    ext: 'png',
    time: undefined as string | undefined,
  },
} as const;

/**
 * EOX "Sentinel-2 cloudless layer for 2016" (layer s2cloudless, matrix set WGS84, 256 px tiles,
 * 2x1 tiles at level 0). Only the 2016 edition is CC BY 4.0 (stated in the layer abstract of
 * https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml); later years are not used.
 */
export const S2_CLOUDLESS = {
  url: 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless/default/WGS84/{z}/{y}/{x}.jpg',
  maxLevel: 13,
  /** The layer fades in below this camera height and is not requested above it. */
  showBelowHeightM: 1_300_000,
  fullBelowHeightM: 500_000,
} as const;

/**
 * NASA Moon Trek WMTS, LRO WAC global mosaic, equirectangular (EQ). Matrix set default028mm:
 * level 0 is 2x1 tiles of 256 px with top-left (-180, 90), i.e. Cesium's standard
 * GeographicTilingScheme; levels 0-8 exist (level 9 returns an HTML error page).
 */
export const MOON_TREK = {
  url: 'https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/default/default028mm/{z}/{y}/{x}.jpg',
  maxLevel: 8,
} as const;

export const IAU_FEATURES_URL = 'static/iau_moon_features.json';

export const EARTH_RADIUS_M = 6_371_000;
export const MOON_RADIUS_M = 1_737_400;

/** How long the loading screen waits before saying imagery is too slow. */
export const IMAGERY_TIMEOUT_MS = 90_000;
