// Result markers on both globes: one PointPrimitiveCollection per body (no entity per marker),
// a LabelCollection for the rank numbers of the top-ranked markers, and a ring plus label for
// the selected marker. Encoding (not colour alone): size and brightness grow with the score on a
// single warm-white light ramp; the top ranks carry their number; the selection gets a ring and its
// name. Far-side markers are hidden and markers near the limb fade, recomputed only when the
// camera moves. Picking is done on the CPU in screen space: the nearest marker within the pointer
// radius (at least 22 px, a 44 px target, for touch).

import {
  Cartesian2,
  Cartesian3,
  Color,
  HorizontalOrigin,
  LabelCollection,
  LabelStyle,
  Matrix4,
  NearFarScalar,
  Math as CesiumMath,
  PointPrimitiveCollection,
  SceneTransforms,
  VerticalOrigin,
  type Label,
  type PerspectiveFrustum,
  type PointPrimitive,
} from 'cesium';
import { palette } from '../a11y/palette';
import type { Body, BodyView, Globes } from '../scene/globes';

export type MarkerId = string | number;

export interface MarkerItem {
  id: MarkerId;
  /** Degrees, north positive. */
  lat: number;
  /** Degrees, east positive, -180..180. */
  lon: number;
  /** 0 (worst shown) to 1 (best). Values outside are clamped. */
  score: number;
  /** 1 = best. Markers with rank <= topLabels show the number. */
  rank?: number;
  /** Shown next to the selected (and hovered) marker, after the rank. */
  label?: string;
}

export interface MarkerOptions {
  /** How many of the best ranks carry their rank number. Default 10. */
  topLabels?: number;
}

export type PickSource = 'mouse' | 'touch' | 'pen' | 'keyboard';
export type PickListener = (body: Body, id: MarkerId, source: PickSource) => void;

export interface MarkerScreenState {
  /** CSS px relative to the body's canvas. */
  x: number;
  y: number;
  /** False on the far side or outside the canvas. */
  visible: boolean;
  /** 0..1 limb fade applied to the marker. */
  fade: number;
  /** Diameter in CSS px. */
  size: number;
}

export interface MarkersApi {
  /** Replace the markers of one body. Keeps the selection if its id is still present. */
  setMarkers(body: Body, items: readonly MarkerItem[], options?: MarkerOptions): void;
  clearMarkers(body: Body): void;
  /** Ring and label on one marker, or none (null). */
  setSelected(body: Body, id: MarkerId | null): void;
  selected(body: Body): MarkerId | null;
  /** Hover look on one marker (for example while its row in a list has keyboard focus), or none. */
  setHighlighted(body: Body, id: MarkerId | null): void;
  /** Called on click, tap, or activate(); returns an unsubscribe function. */
  onPick(listener: PickListener): () => void;
  /** Fire onPick for a marker from the keyboard (call it on Enter in the list of results). */
  activate(body: Body, id: MarkerId): void;
  /** When true (default), a pick also selects the marker. */
  setAutoSelect(on: boolean): void;
  count(body: Body): number;
  /** Where a marker is drawn now, or null if the id is unknown. */
  screenState(body: Body, id: MarkerId): MarkerScreenState | null;
}

// ---- encoding ----
// Single hue (warm white, ~40 degrees), varying in lightness and opacity: readable in greyscale and
// for every colour-vision type because only brightness and size carry the score.
// the score ramp, low to high, from the active palette (src/a11y/palette.ts)
const rampLow = () => { const c = palette().markerLow; return { r: c[0], g: c[1], b: c[2], a: c[3] }; };
const rampHigh = () => { const c = palette().markerHigh; return { r: c[0], g: c[1], b: c[2], a: c[3] }; };
const SIZE_MIN = 3;
const SIZE_MAX = 10;
const OUTLINE = Color.fromBytes(0, 0, 0, 110);
const HOVER_OUTLINE = Color.fromBytes(255, 255, 255, 235);
const ringColor = () => { const c = palette().ring; return Color.fromBytes(c[0], c[1], c[2], 255); };
const TEXT = Color.fromCssColorString('#F3EFE6');
const HALO = Color.fromBytes(0, 0, 0, 235);
const FONT = '"Barlow Semi Condensed", "Barlow", system-ui, sans-serif';
const NO_DEPTH = Number.POSITIVE_INFINITY;

const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : Number.isFinite(v) ? v : 0);
const smooth = (e0: number, e1: number, x: number) => {
  const t = clamp01((x - e0) / (e1 - e0));
  return t * t * (3 - 2 * t);
};

function baseColor(score: number): Color {
  const s = Math.pow(clamp01(score), 1.4);
  const LOW = rampLow();
  const HIGH = rampHigh();
  return new Color(
    (LOW.r + (HIGH.r - LOW.r) * s) / 255,
    (LOW.g + (HIGH.g - LOW.g) * s) / 255,
    (LOW.b + (HIGH.b - LOW.b) * s) / 255,
    LOW.a + (HIGH.a - LOW.a) * s,
  );
}
const sizeFor = (score: number) => SIZE_MIN + (SIZE_MAX - SIZE_MIN) * Math.pow(clamp01(score), 1.4);

function textFor(item: MarkerItem): string {
  if (item.rank != null && item.label) return `${item.rank}  ${item.label}`;
  if (item.label) return item.label;
  if (item.rank != null) return `Rank ${item.rank}`;
  return '';
}

interface Entry {
  item: MarkerItem;
  point: PointPrimitive;
  base: Color;
  size: number;
  /** Position scaled to the unit sphere of the body's ellipsoid (for the horizon test). */
  sx: number;
  sy: number;
  sz: number;
  fade: number;
  rankLabel?: Label;
}

class BodyMarkers {
  private readonly points: PointPrimitiveCollection;
  private readonly rankLabels: LabelCollection;
  private readonly overlay: PointPrimitiveCollection;
  private readonly overlayLabels: LabelCollection;
  private readonly ring: PointPrimitive;
  private readonly selLabel: Label;
  private readonly hoverLabel: Label;
  private entries: Entry[] = [];
  private byId = new Map<MarkerId, Entry>();
  private selectedId: MarkerId | null = null;
  private hoverId: MarkerId | null = null;
  private highlightId: MarkerId | null = null;
  private readonly lastView = new Matrix4();
  private dirty = true;
  /** Projected window positions, valid while projVersion === viewVersion. */
  private proj = new Float32Array(0);
  private projVersion = -1;
  private viewVersion = 0;
  private readonly scratchColor = new Color();
  private readonly scratchWin = new Cartesian2();
  private readonly scratchCam = new Cartesian3();
  /** Marker size factor for the globe's size on screen (0.5..1). */
  private sizeScale = 1;

  constructor(private readonly view: BodyView) {
    const scene = view.scene;
    this.points = new PointPrimitiveCollection();
    this.rankLabels = new LabelCollection({ scene });
    this.overlay = new PointPrimitiveCollection();
    this.overlayLabels = new LabelCollection({ scene });
    scene.primitives.add(this.points);
    scene.primitives.add(this.rankLabels);
    scene.primitives.add(this.overlay);
    scene.primitives.add(this.overlayLabels);
    this.ring = this.overlay.add({
      show: false,
      color: Color.TRANSPARENT,
      outlineColor: ringColor(),
      outlineWidth: 2,
      pixelSize: 22,
      disableDepthTestDistance: NO_DEPTH,
    });
    const labelOpts = {
      show: false,
      position: new Cartesian3(),
      font: `500 15px ${FONT}`,
      fillColor: TEXT,
      outlineColor: HALO,
      outlineWidth: 4,
      style: LabelStyle.FILL_AND_OUTLINE,
      horizontalOrigin: HorizontalOrigin.LEFT,
      verticalOrigin: VerticalOrigin.CENTER,
      pixelOffset: new Cartesian2(16, 0),
      disableDepthTestDistance: NO_DEPTH,
    };
    this.selLabel = this.overlayLabels.add(labelOpts);
    this.hoverLabel = this.overlayLabels.add(labelOpts);
    scene.preRender.addEventListener(() => this.update());
  }

  get scene() {
    return this.view.scene;
  }

  /** Rank label of an entry (top ranks only). */
  private addRankLabel(entry: Entry, topLabels: number): void {
    const item = entry.item;
    if (item.rank == null || item.rank < 1 || item.rank > topLabels) return;
    entry.rankLabel = this.rankLabels.add({
      position: entry.point.position,
      text: String(item.rank),
      font: `600 14px ${FONT}`,
      fillColor: TEXT,
      outlineColor: HALO,
      outlineWidth: 4,
      style: LabelStyle.FILL_AND_OUTLINE,
      horizontalOrigin: HorizontalOrigin.LEFT,
      verticalOrigin: VerticalOrigin.CENTER,
      pixelOffset: new Cartesian2(entry.size / 2 + 4, 0),
      disableDepthTestDistance: NO_DEPTH,
      // Slightly smaller when the camera is far, never below legibility.
      scaleByDistance: new NearFarScalar(1.0e6, 1.0, 4.0e7, 1.0),
    });
  }

  /**
   * Same set of ids with new scores or ranks (the weight sliders): restyle the existing points in
   * place instead of rebuilding thousands of primitives. Returns false when the ids differ.
   */
  private restyle(items: readonly MarkerItem[], topLabels: number): boolean {
    if (!this.entries.length || items.length !== this.entries.length) return false;
    for (const it of items) {
      const e = this.byId.get(it.id);
      if (!e || e.item.lat !== it.lat || e.item.lon !== it.lon || e.item.label !== it.label) return false;
    }
    this.rankLabels.removeAll();
    for (const it of items) {
      const entry = this.byId.get(it.id)!;
      entry.item = it;
      entry.base = baseColor(it.score);
      entry.size = sizeFor(it.score);
      entry.point.color = entry.base;
      entry.point.pixelSize = entry.size;
      entry.fade = -1; // the next update re-applies the limb fade to the new colour
      entry.rankLabel = undefined;
      this.addRankLabel(entry, topLabels);
    }
    this.invalidate();
    return true;
  }

  set(items: readonly MarkerItem[], topLabels: number): void {
    if (this.restyle(items, topLabels)) return;
    this.points.removeAll();
    this.rankLabels.removeAll();
    this.entries = [];
    this.byId = new Map();
    const ellipsoid = this.view.ellipsoid;
    // Best last, so the best markers draw on top.
    const sorted = [...items].filter((i) => Number.isFinite(i.lat) && Number.isFinite(i.lon));
    sorted.sort((a, b) => clamp01(a.score) - clamp01(b.score));
    const scaled = new Cartesian3();
    for (const item of sorted) {
      const position = Cartesian3.fromDegrees(item.lon, item.lat, 0, ellipsoid);
      const base = baseColor(item.score);
      const size = sizeFor(item.score);
      const point = this.points.add({
        position,
        color: base,
        pixelSize: size,
        outlineColor: OUTLINE,
        outlineWidth: 1,
        disableDepthTestDistance: NO_DEPTH,
      });
      ellipsoid.transformPositionToScaledSpace(position, scaled);
      const entry: Entry = { item, point, base, size, sx: scaled.x, sy: scaled.y, sz: scaled.z, fade: 1 };
      this.addRankLabel(entry, topLabels);
      this.entries.push(entry);
      this.byId.set(item.id, entry);
    }
    this.proj = new Float32Array(this.entries.length * 2);
    if (this.selectedId != null && !this.byId.has(this.selectedId)) this.selectedId = null;
    if (this.hoverId != null && !this.byId.has(this.hoverId)) this.hoverId = null;
    if (this.highlightId != null && !this.byId.has(this.highlightId)) this.highlightId = null;
    this.invalidate();
  }

  clear(): void {
    this.set([], 0);
    this.selectedId = null;
    this.hoverId = null;
    this.highlightId = null;
    this.invalidate();
  }

  count(): number {
    return this.entries.length;
  }

  select(id: MarkerId | null): void {
    this.selectedId = id != null && this.byId.has(id) ? id : null;
    this.invalidate();
  }

  selected(): MarkerId | null {
    return this.selectedId;
  }

  setHover(id: MarkerId | null): void {
    if (id === this.hoverId) return;
    this.hoverId = id;
    this.invalidate();
  }

  setHighlight(id: MarkerId | null): void {
    this.highlightId = id != null && this.byId.has(id) ? id : null;
    this.invalidate();
  }

  has(id: MarkerId): boolean {
    return this.byId.has(id);
  }

  private invalidate(): void {
    this.dirty = true;
    this.scene.requestRender();
  }

  /** Horizon test and limb fade, only when the camera moved or the markers changed. */
  private lastW = -1;
  private lastH = -1;

  private update(): void {
    const camera = this.scene.camera;
    // A resized canvas changes every screen position without moving the camera.
    const cw = this.scene.canvas.clientWidth;
    const ch = this.scene.canvas.clientHeight;
    const resized = cw !== this.lastW || ch !== this.lastH;
    this.lastW = cw;
    this.lastH = ch;
    const moved = resized || !Matrix4.equalsEpsilon(camera.viewMatrix, this.lastView, 1e-9);
    if (!moved && !this.dirty) return;
    Matrix4.clone(camera.viewMatrix, this.lastView);
    this.dirty = false;
    this.viewVersion++;
    const cam = this.view.ellipsoid.transformPositionToScaledSpace(camera.positionWC, this.scratchCam);
    // Markers shrink with the globe on screen (small panes, far cameras) so they never carpet it:
    // full size once the disc is ~320 px in radius, down to half size.
    const frustum = camera.frustum as PerspectiveFrustum;
    const dist = Cartesian3.magnitude(camera.positionWC);
    const fovy = frustum.fovy ?? CesiumMath.toRadians(45);
    const ratio = Math.min(0.999, this.view.radiusM / Math.max(dist, this.view.radiusM * 1.0001));
    const discPx = (Math.tan(Math.asin(ratio)) / Math.tan(fovy / 2)) * (this.scene.canvas.clientHeight / 2);
    const k = Math.min(1, Math.max(0.5, discPx / 320));
    if (Math.abs(k - this.sizeScale) > 0.01) this.sizeScale = k;
    const color = this.scratchColor;
    for (const e of this.entries) {
      // Cosine of the angle between the local vertical and the direction to the camera.
      const dx = cam.x - e.sx;
      const dy = cam.y - e.sy;
      const dz = cam.z - e.sz;
      const len = Math.sqrt(dx * dx + dy * dy + dz * dz) * Math.sqrt(e.sx * e.sx + e.sy * e.sy + e.sz * e.sz);
      const cos = len > 0 ? (dx * e.sx + dy * e.sy + dz * e.sz) / len : -1;
      const fade = cos <= 0 ? 0 : smooth(0, 0.2, cos);
      const show = fade > 0.02;
      if (e.point.show !== show) e.point.show = show;
      if (Math.abs(fade - e.fade) > 0.015 || (fade === 1 && e.fade !== 1)) {
        e.fade = fade;
        Color.clone(e.base, color);
        color.alpha = e.base.alpha * fade;
        e.point.color = color;
        if (e.rankLabel) {
          e.rankLabel.fillColor = Color.fromAlpha(TEXT, fade, color);
          e.rankLabel.outlineColor = Color.fromAlpha(HALO, HALO.alpha * fade, new Color());
        }
      }
      if (e.rankLabel) e.rankLabel.show = show && e.item.id !== this.selectedId && e.item.id !== this.activeHover();
    }
    this.updateOverlay();
  }

  private activeHover(): MarkerId | null {
    return this.hoverId ?? this.highlightId;
  }

  private updateOverlay(): void {
    // Hover look: bigger, white outline, and its label.
    const hover = this.activeHover();
    const k = this.sizeScale;
    for (const e of this.entries) {
      const isHover = e.item.id === hover;
      const size = Math.max(2.5, e.size * k) + (isHover ? 4 : 0);
      if (e.point.pixelSize !== size) e.point.pixelSize = size;
      const oc = isHover ? HOVER_OUTLINE : OUTLINE;
      if (!Color.equals(e.point.outlineColor, oc)) {
        e.point.outlineColor = oc;
        e.point.outlineWidth = isHover ? 2 : 1;
      }
    }
    const sel = this.selectedId != null ? this.byId.get(this.selectedId) : undefined;
    if (sel && sel.fade > 0.02) {
      this.ring.position = sel.point.position;
      this.ring.pixelSize = sel.point.pixelSize + 14;
      this.ring.outlineColor = Color.fromAlpha(ringColor(), sel.fade, this.ring.outlineColor);
      this.ring.show = true;
      const text = textFor(sel.item);
      this.selLabel.show = text !== '';
      if (text) {
        this.selLabel.text = text;
        this.selLabel.position = sel.point.position;
        this.selLabel.pixelOffset = new Cartesian2((sel.point.pixelSize + 14) / 2 + 6, 0);
        this.selLabel.fillColor = Color.fromAlpha(TEXT, sel.fade, new Color());
      }
    } else {
      this.ring.show = false;
      this.selLabel.show = false;
    }
    const hov = hover != null && hover !== this.selectedId ? this.byId.get(hover) : undefined;
    const htext = hov ? textFor(hov.item) : '';
    if (hov && htext && hov.fade > 0.02) {
      this.hoverLabel.text = htext;
      this.hoverLabel.position = hov.point.position;
      this.hoverLabel.pixelOffset = new Cartesian2(hov.point.pixelSize / 2 + 6, 0);
      this.hoverLabel.show = true;
    } else {
      this.hoverLabel.show = false;
    }
  }

  /** Window positions of all markers for the current camera (cached until it moves). */
  private project(): Float32Array {
    this.update(); // no-op unless the camera moved or the markers changed since the last frame
    if (this.projVersion === this.viewVersion) return this.proj;
    const proj = this.proj;
    for (let i = 0; i < this.entries.length; i++) {
      const e = this.entries[i] as Entry;
      let x = NaN;
      let y = NaN;
      if (e.point.show) {
        const w = SceneTransforms.worldToWindowCoordinates(this.scene, e.point.position, this.scratchWin);
        if (w) {
          x = w.x;
          y = w.y;
        }
      }
      proj[i * 2] = x;
      proj[i * 2 + 1] = y;
    }
    this.projVersion = this.viewVersion;
    return proj;
  }

  /** Nearest visible marker to (x, y) in canvas CSS px within `radius` px of its edge, or null. */
  nearest(x: number, y: number, radius: number): MarkerId | null {
    const proj = this.project();
    let best: Entry | null = null;
    let bestD = Number.POSITIVE_INFINITY;
    for (let i = 0; i < this.entries.length; i++) {
      const px = proj[i * 2] as number;
      if (Number.isNaN(px)) continue;
      const e = this.entries[i] as Entry;
      const dx = px - x;
      const dy = (proj[i * 2 + 1] as number) - y;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d <= radius + e.point.pixelSize / 2 && d < bestD) {
        bestD = d;
        best = e;
      }
    }
    return best ? best.item.id : null;
  }

  screenState(id: MarkerId): MarkerScreenState | null {
    const e = this.byId.get(id);
    if (!e) return null;
    this.update();
    const w = SceneTransforms.worldToWindowCoordinates(this.scene, e.point.position, new Cartesian2());
    const canvas = this.scene.canvas;
    const inCanvas = !!w && w.x >= 0 && w.y >= 0 && w.x <= canvas.clientWidth && w.y <= canvas.clientHeight;
    return {
      x: w ? w.x : NaN,
      y: w ? w.y : NaN,
      visible: e.point.show && inCanvas,
      fade: e.fade,
      size: e.point.pixelSize,
    };
  }
}

/** Builds the marker layers and their pointer handling; one instance for the page. */
export class Markers implements MarkersApi {
  private readonly layers: Record<Body, BodyMarkers>;
  private readonly listeners = new Set<PickListener>();
  private autoSelect = true;

  constructor(globes: Globes) {
    this.layers = { earth: new BodyMarkers(globes.earth), moon: new BodyMarkers(globes.moon) };
    for (const body of ['earth', 'moon'] as Body[]) this.bindPointer(body);
  }

  setMarkers(body: Body, items: readonly MarkerItem[], options: MarkerOptions = {}): void {
    this.layers[body].set(items, Math.max(0, Math.floor(options.topLabels ?? 10)));
  }

  clearMarkers(body: Body): void {
    this.layers[body].clear();
  }

  setSelected(body: Body, id: MarkerId | null): void {
    this.layers[body].select(id);
  }

  selected(body: Body): MarkerId | null {
    return this.layers[body].selected();
  }

  setHighlighted(body: Body, id: MarkerId | null): void {
    this.layers[body].setHighlight(id);
  }

  onPick(listener: PickListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  activate(body: Body, id: MarkerId): void {
    if (!this.layers[body].has(id)) return;
    this.emit(body, id, 'keyboard');
  }

  setAutoSelect(on: boolean): void {
    this.autoSelect = on;
  }

  count(body: Body): number {
    return this.layers[body].count();
  }

  screenState(body: Body, id: MarkerId): MarkerScreenState | null {
    return this.layers[body].screenState(id);
  }

  private emit(body: Body, id: MarkerId, source: PickSource): void {
    if (this.autoSelect) this.setSelected(body, id);
    this.listeners.forEach((l) => l(body, id, source));
  }

  private bindPointer(body: Body): void {
    const layer = this.layers[body];
    const canvas = layer.scene.canvas;
    const radiusFor = (type: string) => (type === 'mouse' ? 6 : 22);
    // Times come from the events themselves (timeStamp), not from when the handler runs: a slow
    // frame between pointerdown and pointerup must not turn a tap into a long press.
    let down: { x: number; y: number; t: number; id: number } | null = null;
    const local = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    };
    canvas.addEventListener('pointerdown', (e) => {
      if (!e.isPrimary || e.button > 0) return;
      const p = local(e);
      down = { ...p, t: e.timeStamp, id: e.pointerId };
    });
    canvas.addEventListener('pointerup', (e) => {
      const d = down;
      down = null;
      if (!d || d.id !== e.pointerId || layer.count() === 0) return;
      const p = local(e);
      if (Math.hypot(p.x - d.x, p.y - d.y) > 6 || e.timeStamp - d.t > 700) return; // a drag, not a tap
      const id = layer.nearest(p.x, p.y, radiusFor(e.pointerType));
      if (id != null) this.emit(body, id, (e.pointerType || 'mouse') as PickSource);
    });
    // Hover (mouse only): nearest marker under the pointer gets the hover look and the cursor turns into a hand.
    let pending: PointerEvent | null = null;
    canvas.addEventListener('pointermove', (e) => {
      if (e.pointerType !== 'mouse' || layer.count() === 0) return;
      if (e.buttons) {
        layer.setHover(null);
        return;
      }
      if (!pending) {
        requestAnimationFrame(() => {
          const ev = pending;
          pending = null;
          if (!ev) return;
          const p = local(ev);
          const id = layer.nearest(p.x, p.y, radiusFor('mouse'));
          layer.setHover(id);
          canvas.style.cursor = id != null ? 'pointer' : '';
        });
      }
      pending = e;
    });
    canvas.addEventListener('pointerleave', () => {
      layer.setHover(null);
      canvas.style.cursor = '';
    });
  }
}
