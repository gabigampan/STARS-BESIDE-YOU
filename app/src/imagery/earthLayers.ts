import { Credit, GeographicTilingScheme, ImageryLayer, UrlTemplateImageryProvider } from 'cesium';
import { EARTH_LAYERS, GIBS_WMTS_4326, S2_CLOUDLESS } from '../config';
import { GibsGeographicTilingScheme } from './gibsTilingScheme';

const GIBS_CREDIT = new Credit(
  '<a href="https://nasa-gibs.github.io/gibs-api-docs/" target="_blank" rel="noopener">NASA GIBS</a>',
  true,
);
const S2_CREDIT = new Credit(
  '<a href="https://s2maps.eu" target="_blank" rel="noopener">Sentinel-2 cloudless 2016</a> by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016), CC BY 4.0',
  true,
);

type GibsLayer = (typeof EARTH_LAYERS)[keyof typeof EARTH_LAYERS];

function gibsProvider(layer: GibsLayer): UrlTemplateImageryProvider {
  const timePart = layer.time ? `${layer.time}/` : '';
  return new UrlTemplateImageryProvider({
    url: `${GIBS_WMTS_4326}/${layer.id}/default/${timePart}${layer.matrixSet}/{z}/{y}/{x}.${layer.ext}`,
    tilingScheme: new GibsGeographicTilingScheme(),
    // 256 rather than the real 512: Cesium picks the level from tileWidth x level-0 tile count,
    // and 256 gives the closer match to GIBS's 0.5625 deg/px level 0 (as in NASA's own example).
    tileWidth: 256,
    tileHeight: 256,
    minimumLevel: 0,
    maximumLevel: layer.maxLevel,
    credit: GIBS_CREDIT,
    hasAlphaChannel: layer.ext === 'png',
  });
}

export interface EarthImagery {
  base: ImageryLayer;
  sharp: ImageryLayer;
  night: ImageryLayer;
  labels: ImageryLayer;
}

export function createEarthImagery(): EarthImagery {
  const base = new ImageryLayer(gibsProvider(EARTH_LAYERS.blueMarble), {
    // Blue Marble is a cloud-free composite; a touch less saturation keeps it photographic.
    saturation: 0.92,
    gamma: 1.0,
  });

  const sharp = new ImageryLayer(
    new UrlTemplateImageryProvider({
      url: S2_CLOUDLESS.url,
      tilingScheme: new GeographicTilingScheme({ numberOfLevelZeroTilesX: 2, numberOfLevelZeroTilesY: 1 }),
      maximumLevel: S2_CLOUDLESS.maxLevel,
      credit: S2_CREDIT,
    }),
    { show: false, alpha: 0, saturation: 0.95 },
  );

  // Night lights only where the Sun is down: invisible by day, fully shown at night.
  const night = new ImageryLayer(gibsProvider(EARTH_LAYERS.blackMarble), {
    dayAlpha: 0.0,
    nightAlpha: 1.0,
    brightness: 1.6,
    gamma: 1.1,
  });

  const labels = new ImageryLayer(gibsProvider(EARTH_LAYERS.labels), { alpha: 0.95 });

  return { base, sharp, night, labels };
}

/** Fade the Sentinel-2 layer in as the camera descends, and stop requesting it when high. */
export function updateSharpLayer(layer: ImageryLayer, cameraHeightM: number): boolean {
  const { showBelowHeightM, fullBelowHeightM } = S2_CLOUDLESS;
  const show = cameraHeightM < showBelowHeightM;
  const t = (showBelowHeightM - cameraHeightM) / (showBelowHeightM - fullBelowHeightM);
  const alpha = show ? Math.min(1, Math.max(0, t)) : 0;
  const changed = layer.show !== show || Math.abs(layer.alpha - alpha) > 0.01;
  layer.show = show;
  layer.alpha = alpha;
  return changed;
}
