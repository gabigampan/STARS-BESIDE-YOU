// IAU feature names on the Moon. Names appear by size as the camera approaches: maria and the
// largest basins from far away, craters when near. A greedy screen-space pass, largest feature
// first, keeps labels from piling up, and features on the far side are hidden.

import {
  Cartesian2,
  Cartesian3,
  Color,
  Ellipsoid,
  HorizontalOrigin,
  Label,
  LabelCollection,
  LabelStyle,
  Scene,
  SceneTransforms,
  VerticalOrigin,
} from 'cesium';
import { IAU_FEATURES_URL } from '../config';

type FeatureRow = [name: string, type: string, lat: number, lon: number, diameterKm: number];
interface FeatureFile {
  fields: string[];
  features: FeatureRow[];
}

interface Entry {
  label: Label;
  position: Cartesian3;
  scaledPosition: Cartesian3;
  diameterKm: number;
  /** Camera distance (m, from the feature) below which the name may show. */
  maxDistanceM: number;
  /** Approximate half-size of the label on screen in CSS px. */
  halfWidth: number;
  halfHeight: number;
  big: boolean;
}

const REGION_TYPES = new Set(['Mare', 'Oceanus', 'Lacus', 'Sinus', 'Palus', 'Planitia']);
const MAX_LABELS = 70;
const FONT_FAMILY = '"Barlow Semi Condensed", "Barlow", system-ui, sans-serif';

function visibilityDistance(type: string, diameterKm: number): number {
  // A feature is named once it would span roughly 1/25 of the view (craters) or when the camera
  // is within ~5 diameters of a large region. Maria and big basins are always named.
  if (REGION_TYPES.has(type) && diameterKm >= 300) return Number.POSITIVE_INFINITY;
  if (diameterKm >= 500) return Number.POSITIVE_INFINITY;
  const factor = REGION_TYPES.has(type) ? 9 : type === 'Crater' ? 20 : type === 'Mons' ? 8 : 5;
  return diameterKm * 1000 * factor;
}

export class MoonLabels {
  private readonly collection: LabelCollection;
  private readonly entries: Entry[] = [];
  private readonly ellipsoid = Ellipsoid.MOON;
  private enabled = true;
  private readonly scratchWin = new Cartesian2();
  private readonly scratchCam = new Cartesian3();
  private readonly scratchToCam = new Cartesian3();

  constructor(private readonly scene: Scene) {
    this.collection = new LabelCollection({ scene });
    scene.primitives.add(this.collection);
  }

  async load(url = IAU_FEATURES_URL): Promise<number> {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`IAU feature names (${url}) returned HTTP ${response.status}`);
    const data = (await response.json()) as FeatureFile;
    for (const [name, type, lat, lon, diameterKm] of data.features) {
      const big = REGION_TYPES.has(type) && diameterKm >= 300;
      const position = Cartesian3.fromDegrees(lon, lat, 0, this.ellipsoid);
      const fontPx = big ? 15 : 13;
      const text = name;
      const label = this.collection.add({
        position,
        text,
        font: `${big ? 500 : 400} ${fontPx}px ${FONT_FAMILY}`,
        fillColor: big ? Color.fromCssColorString('#E9E4D8') : Color.fromCssColorString('#D8D6D0'),
        outlineColor: Color.BLACK,
        outlineWidth: 4,
        style: LabelStyle.FILL_AND_OUTLINE,
        horizontalOrigin: HorizontalOrigin.CENTER,
        verticalOrigin: VerticalOrigin.CENTER,
        // Labels sit on the surface; the horizon test below hides far-side names, and depth
        // testing is off so limb names are not clipped by the sphere.
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        show: false,
      });
      this.entries.push({
        label,
        position,
        scaledPosition: this.ellipsoid.transformPositionToScaledSpace(position, new Cartesian3()),
        diameterKm,
        maxDistanceM: visibilityDistance(type, diameterKm),
        halfWidth: (text.length * fontPx * 0.5) / 2 + 4,
        halfHeight: fontPx * 0.7 + 3,
        big,
      });
    }
    // Rows are sorted by diameter (largest first) in the file; keep that order for priority.
    this.entries.sort((a, b) => b.diameterKm - a.diameterKm);
    this.update();
    return this.entries.length;
  }

  setEnabled(on: boolean): void {
    this.enabled = on;
    this.update();
  }

  /** Recompute which names are shown. Call when the camera moves. */
  update(): void {
    const scene = this.scene;
    const camera = scene.camera;
    const canvas = scene.canvas;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const placed: { x: number; y: number; hw: number; hh: number }[] = [];
    const camPos = Cartesian3.clone(camera.positionWC, this.scratchCam);
    const camScaled = this.ellipsoid.transformPositionToScaledSpace(camPos, new Cartesian3());

    let shown = 0;
    for (const e of this.entries) {
      let show = false;
      if (this.enabled && shown < MAX_LABELS) {
        // Horizon test in the ellipsoid's scaled space (exact for a sphere): the point faces the
        // camera when the vector to the camera is within 90 degrees of its surface normal.
        const toCam = Cartesian3.subtract(camScaled, e.scaledPosition, this.scratchToCam);
        const facing = Cartesian3.dot(toCam, e.scaledPosition);
        if (facing > 0.12 * Cartesian3.magnitude(toCam)) {
          const distance = Cartesian3.distance(camPos, e.position);
          if (distance < e.maxDistanceM) {
            const win = SceneTransforms.worldToWindowCoordinates(scene, e.position, this.scratchWin);
            const inside =
              win &&
              win.x - e.halfWidth >= 2 &&
              win.y - e.halfHeight >= 2 &&
              win.x + e.halfWidth <= width - 2 &&
              win.y + e.halfHeight <= height - 2;
            if (win && inside) {
              const collides = placed.some(
                (p) => Math.abs(p.x - win.x) < p.hw + e.halfWidth && Math.abs(p.y - win.y) < p.hh + e.halfHeight,
              );
              if (!collides) {
                placed.push({ x: win.x, y: win.y, hw: e.halfWidth, hh: e.halfHeight });
                show = true;
                shown++;
              }
            }
          }
        }
      }
      if (e.label.show !== show) e.label.show = show;
    }
    scene.requestRender();
  }
}
