import { Credit, Ellipsoid, GeographicTilingScheme, ImageryLayer, UrlTemplateImageryProvider } from 'cesium';
import { MOON_TREK } from '../config';

const TREK_CREDIT = new Credit(
  '<a href="https://trek.nasa.gov/moon/" target="_blank" rel="noopener">NASA Moon Trek</a>: LRO WAC global mosaic (NASA/GSFC/Arizona State University)',
  true,
);

export function createMoonImagery(): ImageryLayer {
  const provider = new UrlTemplateImageryProvider({
    url: MOON_TREK.url,
    // default028mm: 2 x 1 tiles of 256 px at level 0, top-left (-180, 90), longitude east.
    tilingScheme: new GeographicTilingScheme({
      ellipsoid: Ellipsoid.MOON,
      numberOfLevelZeroTilesX: 2,
      numberOfLevelZeroTilesY: 1,
    }),
    tileWidth: 256,
    tileHeight: 256,
    maximumLevel: MOON_TREK.maxLevel,
    credit: TREK_CREDIT,
  });
  return new ImageryLayer(provider, { gamma: 1.05 });
}
