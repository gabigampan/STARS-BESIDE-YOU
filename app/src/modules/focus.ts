// Paired fly-to for the comparison view. Both cameras move in one animation loop (same start, same
// end), look straight down at their point from a height that frames the caller's cell (or a
// 1-degree cell when no footprint is given), and the page layout makes room for #detail-panel
// while focused (CSS: body.is-focused). exitFocus() returns both cameras to the views they had.

import {
  Cartesian3,
  Color,
  Material,
  Math as CesiumMath,
  PolylineCollection,
  type PerspectiveFrustum,
} from 'cesium';
import { palette } from '../a11y/palette';
import { resetView, type Body, type BodyView, type Globes } from '../scene/globes';

/** A cell footprint in degrees (west/east longitude -180..180, east of west). */
export interface CellFootprint {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface FocusPoint {
  lat: number;
  lon: number;
  /** Footprint of the cell to outline and frame. Without it nothing is outlined and a 1-degree cell is framed. */
  cell?: CellFootprint;
}

export interface FocusOptions {
  /** Flight duration in ms (default 1000, capped at 1400). Ignored (instant) under reduced motion. */
  durationMs?: number;
  /** Share of the smaller canvas dimension the cell should span (default 0.4). */
  fill?: number;
  /**
   * Clock that drives the animation, in ms (default performance.now). Called once per frame; a
   * clock that advances a fixed step per call gives a frame-exact flight for tests and recordings.
   */
  timeSource?: () => number;
}

export interface FlightReport {
  /** Duration the flight was planned for, ms (0 when instant). */
  plannedMs: number;
  /** Animation time at which both cameras reached their targets, ms. */
  animationMs: number;
  /** Wall-clock time from the call to the promise resolving, ms (includes the layout change). */
  wallMs: number;
  completed: boolean;
}

export interface FocusApi {
  /** Fly both cameras at once to their points; resolves true when both arrive, false if interrupted. */
  focusPair(pair: { earth: FocusPoint; moon: FocusPoint }, options?: FocusOptions): Promise<boolean>;
  /** Return both cameras to the views they had before focusPair, and restore the layout. */
  exitFocus(options?: Pick<FocusOptions, 'durationMs' | 'timeSource'>): Promise<boolean>;
  isFocused(): boolean;
  /** Outline one cell on one body without the paired view (null removes it); focusPair and exitFocus replace it. */
  outline(body: Body, cell: CellFootprint | null): void;
  /** Timing of the last flight (for tests and tuning). */
  lastFlight(): FlightReport | null;
}

const KM_PER_DEG = { earth: 111.32, moon: (Math.PI * 1737.4) / 180 };
const MIN_HEIGHT_M = { earth: 2_000, moon: 2_500 };
const MAX_DURATION_MS = 1400;
const DEFAULT_DURATION_MS = 1000;

interface Pose {
  lon: number; // radians
  lat: number;
  height: number; // m
  heading: number;
  pitch: number;
  roll: number;
}

interface Saved {
  pose: Pose;
  atHome: boolean;
}

const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const shortest = (a: number, b: number) => {
  let d = (b - a) % CesiumMath.TWO_PI;
  if (d > Math.PI) d -= CesiumMath.TWO_PI;
  if (d < -Math.PI) d += CesiumMath.TWO_PI;
  return d;
};

function poseOf(view: BodyView): Pose {
  const c = view.scene.camera;
  const carto = view.ellipsoid.cartesianToCartographic(c.positionWC);
  return {
    lon: carto?.longitude ?? 0,
    lat: carto?.latitude ?? 0,
    height: carto?.height ?? view.radiusM,
    heading: c.heading,
    pitch: c.pitch,
    roll: c.roll,
  };
}

function applyPose(view: BodyView, p: Pose): void {
  view.scene.camera.setView({
    destination: Cartesian3.fromRadians(p.lon, p.lat, p.height, view.ellipsoid),
    orientation: { heading: p.heading, pitch: p.pitch, roll: p.roll },
  });
  view.scene.requestRender();
}

/** Pose at animation fraction e (0..1): great-circle path, log-height with an arc for long hops. */
function interpolate(a: Pose, b: Pose, e: number, radiusM: number): Pose {
  const unit = (lon: number, lat: number) =>
    new Cartesian3(Math.cos(lat) * Math.cos(lon), Math.cos(lat) * Math.sin(lon), Math.sin(lat));
  const ua = unit(a.lon, a.lat);
  const ub = unit(b.lon, b.lat);
  const angle = Cartesian3.angleBetween(ua, ub);
  let lon: number;
  let lat: number;
  if (angle < 1e-9) {
    lon = b.lon;
    lat = b.lat;
  } else {
    const s = Math.sin(angle);
    const wa = Math.sin((1 - e) * angle) / s;
    const wb = Math.sin(e * angle) / s;
    const x = ua.x * wa + ub.x * wb;
    const y = ua.y * wa + ub.y * wb;
    const z = ua.z * wa + ub.z * wb;
    lat = Math.atan2(z, Math.hypot(x, y));
    lon = Math.atan2(y, x);
  }
  const ha = Math.max(a.height, 1);
  const hb = Math.max(b.height, 1);
  let height = Math.exp(Math.log(ha) + (Math.log(hb) - Math.log(ha)) * e);
  const arc = radiusM * angle * 0.5 - Math.max(ha, hb);
  if (arc > 0) height += arc * Math.sin(Math.PI * e);
  return {
    lon,
    lat,
    height,
    heading: a.heading + shortest(a.heading, b.heading) * e,
    pitch: a.pitch + (b.pitch - a.pitch) * e,
    roll: a.roll + shortest(a.roll, b.roll) * e,
  };
}

class CellOutline {
  private readonly lines: PolylineCollection;

  constructor(private readonly view: BodyView) {
    this.lines = new PolylineCollection();
    view.scene.primitives.add(this.lines);
  }

  private last: CellFootprint | undefined;

  /** Draw again with the active palette (colour-blind mode switched). */
  redraw(): void {
    this.set(this.last);
  }

  set(cell: CellFootprint | undefined): void {
    this.last = cell;
    this.lines.removeAll();
    if (cell) {
      const lift = this.view.body === 'earth' ? 400 : 150;
      const steps = 24;
      const ring: number[] = [];
      const edge = (lon0: number, lat0: number, lon1: number, lat1: number) => {
        for (let i = 0; i < steps; i++) {
          const t = i / steps;
          ring.push(lon0 + (lon1 - lon0) * t, lat0 + (lat1 - lat0) * t, lift);
        }
      };
      const { west, south, east, north } = cell;
      edge(west, south, east, south);
      edge(east, south, east, north);
      edge(east, north, west, north);
      edge(west, north, west, south);
      ring.push(west, south, lift);
      const positions = Cartesian3.fromDegreesArrayHeights(ring, this.view.ellipsoid);
      // A soft dark underlay keeps the thin light line readable on bright ground (deserts, highlands).
      this.lines.add({
        positions,
        width: 4,
        material: Material.fromType('Color', { color: Color.fromBytes(0, 0, 0, 90) }),
      });
      this.lines.add({
        positions,
        width: 1.5,
        material: Material.fromType('Color', { color: Color.fromBytes(...palette().cellLine, 210) }),
      });
    }
    this.view.scene.requestRender();
  }
}

export class Focus implements FocusApi {
  private focused = false;
  private saved: Record<Body, Saved> | null = null;
  private outlines: Record<Body, CellOutline>;
  private flight: { cancel: () => void } | null = null;
  private report: FlightReport | null = null;

  constructor(
    private readonly globes: Globes,
    private readonly reducedMotion: () => boolean,
  ) {
    this.outlines = { earth: new CellOutline(globes.earth), moon: new CellOutline(globes.moon) };
    // Direct manipulation stops a running flight where it is.
    for (const v of [globes.earth, globes.moon]) {
      const stop = () => this.flight?.cancel();
      v.scene.canvas.addEventListener('pointerdown', stop);
      v.scene.canvas.addEventListener('wheel', stop, { passive: true });
    }
  }

  isFocused(): boolean {
    return this.focused;
  }

  lastFlight(): FlightReport | null {
    return this.report;
  }

  outline(body: Body, cell: CellFootprint | null): void {
    this.outlines[body].set(cell ?? undefined);
  }

  /** Redraw the cell outlines in the active palette. */
  repaint(): void {
    this.outlines.earth.redraw();
    this.outlines.moon.redraw();
  }

  focusPair(pair: { earth: FocusPoint; moon: FocusPoint }, options: FocusOptions = {}): Promise<boolean> {
    const t0 = performance.now();
    const { earth, moon } = this.globes;
    this.flight?.cancel();
    if (!this.focused) {
      this.saved = {
        earth: { pose: poseOf(earth), atHome: earth.atHome },
        moon: { pose: poseOf(moon), atHome: moon.atHome },
      };
    }
    this.focused = true;
    document.body.classList.add('is-focused');
    // The new canvas sizes must be known before choosing heights.
    this.settleLayout();
    const fill = Math.min(0.9, Math.max(0.1, options.fill ?? 0.4));
    const targets: Record<Body, Pose> = {
      earth: this.target(earth, pair.earth, fill),
      moon: this.target(moon, pair.moon, fill),
    };
    this.outlines.earth.set(pair.earth.cell);
    this.outlines.moon.set(pair.moon.cell);
    earth.atHome = false;
    moon.atHome = false;
    return this.fly(targets, options.durationMs, t0, options.timeSource);
  }

  exitFocus(options: Pick<FocusOptions, 'durationMs' | 'timeSource'> = {}): Promise<boolean> {
    if (!this.focused) return Promise.resolve(true);
    const t0 = performance.now();
    this.flight?.cancel();
    this.focused = false;
    document.body.classList.remove('is-focused');
    this.outlines.earth.set(undefined);
    this.outlines.moon.set(undefined);
    this.settleLayout();
    const saved = this.saved;
    this.saved = null;
    if (!saved) return Promise.resolve(true);
    const { earth, moon } = this.globes;
    // A view that was the home view goes back to the home view fitted to the restored pane size.
    const homeTarget = (v: BodyView, s: Saved): Pose => {
      if (!s.atHome) return s.pose;
      const before = poseOf(v);
      resetView(v, true);
      const home = poseOf(v);
      applyPose(v, before);
      return home;
    };
    const targets: Record<Body, Pose> = { earth: homeTarget(earth, saved.earth), moon: homeTarget(moon, saved.moon) };
    return this.fly(targets, options.durationMs, t0, options.timeSource).then((ok) => {
      if (ok) {
        earth.atHome = saved.earth.atHome;
        moon.atHome = saved.moon.atHome;
      }
      return ok;
    });
  }

  /** Apply the layout change now: reading the new pane sizes forces layout, and resize() updates the canvases and frustums. */
  private settleLayout(): void {
    for (const v of [this.globes.earth, this.globes.moon]) {
      v.widget.resize();
      v.scene.requestRender();
    }
  }

  /** Camera pose straight above the point, high enough that the cell spans `fill` of the smaller canvas side. */
  private target(view: BodyView, p: FocusPoint, fill: number): Pose {
    const body = view.body;
    const kmPerDeg = KM_PER_DEG[body];
    let extentKm = kmPerDeg; // one degree
    if (p.cell) {
      const ns = Math.abs(p.cell.north - p.cell.south) * kmPerDeg;
      const ew = Math.abs(p.cell.east - p.cell.west) * kmPerDeg * Math.cos(CesiumMath.toRadians(p.lat));
      extentKm = Math.max(ns, ew, kmPerDeg * 0.05);
    }
    const frustum = view.scene.camera.frustum as PerspectiveFrustum;
    const w = view.scene.canvas.clientWidth || 1;
    const h = view.scene.canvas.clientHeight || 1;
    const fov = frustum.fov ?? CesiumMath.toRadians(60);
    const halfSmall = Math.atan(Math.tan(fov / 2) * (Math.min(w, h) / Math.max(w, h)));
    const height = Math.max(MIN_HEIGHT_M[body], (extentKm * 1000) / fill / (2 * Math.tan(halfSmall)));
    return {
      lon: CesiumMath.toRadians(p.lon),
      lat: CesiumMath.toRadians(p.lat),
      height,
      heading: 0,
      pitch: -CesiumMath.PI_OVER_TWO,
      roll: 0,
    };
  }

  private fly(
    targets: Record<Body, Pose>,
    durationMs: number | undefined,
    t0: number,
    timeSource?: () => number,
  ): Promise<boolean> {
    const { earth, moon } = this.globes;
    earth.scene.camera.cancelFlight();
    moon.scene.camera.cancelFlight();
    const planned = this.reducedMotion() ? 0 : Math.min(MAX_DURATION_MS, Math.max(0, durationMs ?? DEFAULT_DURATION_MS));
    if (planned === 0) {
      applyPose(earth, targets.earth);
      applyPose(moon, targets.moon);
      this.report = { plannedMs: 0, animationMs: 0, wallMs: performance.now() - t0, completed: true };
      return Promise.resolve(true);
    }
    const starts: Record<Body, Pose> = { earth: poseOf(earth), moon: poseOf(moon) };
    // One clock for both cameras, started now. Each frame places both; the final pose is applied by
    // the first frame (or the timer) at or after the planned duration, so both arrive together.
    const clock = timeSource ?? (() => performance.now());
    return new Promise<boolean>((resolve) => {
      const start = clock();
      let raf = 0;
      let timer = 0;
      let done = false;
      const finish = (completed: boolean) => {
        if (done) return;
        done = true;
        cancelAnimationFrame(raf);
        window.clearTimeout(timer);
        this.flight = null;
        this.report = { plannedMs: planned, animationMs: last - start, wallMs: performance.now() - t0, completed };
        resolve(completed);
      };
      let last = start;
      const step = () => {
        if (done) return;
        last = clock();
        const t = Math.min(1, (last - start) / planned);
        if (t >= 1) {
          applyPose(earth, targets.earth);
          applyPose(moon, targets.moon);
          finish(true);
          return;
        }
        const e = easeInOut(t);
        applyPose(earth, interpolate(starts.earth, targets.earth, e, earth.radiusM));
        applyPose(moon, interpolate(starts.moon, targets.moon, e, moon.radiusM));
        raf = requestAnimationFrame(step);
      };
      this.flight = { cancel: () => finish(false) };
      if (!timeSource) timer = window.setTimeout(step, planned);
      raf = requestAnimationFrame(step);
    });
  }
}
