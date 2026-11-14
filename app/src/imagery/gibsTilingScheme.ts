// Tiling scheme for NASA GIBS EPSG:4326 tile matrix sets.
//
// GIBS geographic tiles are 512 px wide with their top-left corner at (-180, 90). Level 0 of the
// 500m and 15.625m sets is 2 x 1 tiles of 0.5625 degrees per pixel, so a tile spans 288 degrees
// and the grid overhangs the globe to the east and south; each level halves the pixel size.
// Cesium's GeographicTilingScheme assumes 2 x 1 tiles that exactly cover the globe, which would
// stretch the imagery, so this scheme reports the real tile extents.
// Adapted from nasa-gibs/gibs-web-examples (examples/cesium/gibs.js, Apache License 2.0).

import { Cartographic, GeographicTilingScheme, Math as CesiumMath, Rectangle, Cartesian2 } from 'cesium';

const TILE_PIXELS = 512;
/** Radians per pixel at level 0 (0.5625 degrees). */
const LEVEL0_RESOLUTION = CesiumMath.toRadians(0.5625);

export class GibsGeographicTilingScheme extends GeographicTilingScheme {
  constructor() {
    super({ numberOfLevelZeroTilesX: 2, numberOfLevelZeroTilesY: 1 });
  }

  private static tileSpan(level: number): number {
    return (LEVEL0_RESOLUTION / 2 ** level) * TILE_PIXELS;
  }

  override getNumberOfXTilesAtLevel(level: number): number {
    return Math.ceil(CesiumMath.TWO_PI / GibsGeographicTilingScheme.tileSpan(level) - 1e-9);
  }

  override getNumberOfYTilesAtLevel(level: number): number {
    return Math.ceil(Math.PI / GibsGeographicTilingScheme.tileSpan(level) - 1e-9);
  }

  override tileXYToRectangle(x: number, y: number, level: number, result?: Rectangle): Rectangle {
    const span = GibsGeographicTilingScheme.tileSpan(level);
    const r = result ?? new Rectangle();
    r.west = -Math.PI + x * span;
    r.east = -Math.PI + (x + 1) * span;
    r.north = CesiumMath.PI_OVER_TWO - y * span;
    r.south = CesiumMath.PI_OVER_TWO - (y + 1) * span;
    return r;
  }

  override tileXYToNativeRectangle(x: number, y: number, level: number, result?: Rectangle): Rectangle {
    const r = this.tileXYToRectangle(x, y, level, result);
    r.west = CesiumMath.toDegrees(r.west);
    r.east = CesiumMath.toDegrees(r.east);
    r.north = CesiumMath.toDegrees(r.north);
    r.south = CesiumMath.toDegrees(r.south);
    return r;
  }

  // Cesium's declared return type omits undefined, but its own schemes return undefined outside.
  override positionToTileXY(position: Cartographic, level: number, result?: Cartesian2): Cartesian2 {
    if (!Rectangle.contains(this.rectangle, position)) return undefined as unknown as Cartesian2;
    const span = GibsGeographicTilingScheme.tileSpan(level);
    const xTiles = this.getNumberOfXTilesAtLevel(level);
    const yTiles = this.getNumberOfYTilesAtLevel(level);
    let x = Math.floor((position.longitude + Math.PI) / span);
    let y = Math.floor((CesiumMath.PI_OVER_TWO - position.latitude) / span);
    x = Math.min(Math.max(x, 0), xTiles - 1);
    y = Math.min(Math.max(y, 0), yTiles - 1);
    const out = result ?? new Cartesian2();
    out.x = x;
    out.y = y;
    return out;
  }
}
