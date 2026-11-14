// The small typed API the next frontend stage calls. Everything else in src/scene is internal.
//
//   import { globesApi } from './api';
//   await globesApi.ready;
//   await globesApi.flyTo('moon', -43.3, -11.2, 400, 2);
//   const p = globesApi.toCanvas('earth', 40.4, -3.7);   // { x, y } in CSS px, or null
//   const off = globesApi.onCameraMove((body) => ...);  // returns an unsubscribe function

import { Cartesian2, Cartesian3, Math as CesiumMath, SceneTransforms, type CesiumWidget, type Scene } from 'cesium';
import { resetView, type Body, type BodyView, type Globes } from './scene/globes';
import type { BeamsApi } from './modules/beams';
import type { FocusApi } from './modules/focus';
import type { MarkersApi } from './modules/markers';
import type { SunlightApi } from './modules/sunlight';
import type { VideoApi } from './modules/video';

export type { Body } from './scene/globes';
export type { Beam, BeamEnd, BeamsApi, LatLon } from './modules/beams';
export type { CellFootprint, FlightReport, FocusApi, FocusOptions, FocusPoint } from './modules/focus';
export type { MarkerId, MarkerItem, MarkerOptions, MarkerScreenState, MarkersApi, PickListener, PickSource } from './modules/markers';
export type { SunlightApi, SunlightChoice, SunlightMode } from './modules/sunlight';
export type { VideoApi, VideoSource, VideoSpec, VideoTrack } from './modules/video';

export interface CanvasPoint {
  /** CSS pixels from the left edge of that body's canvas. */
  x: number;
  /** CSS pixels from the top edge of that body's canvas. */
  y: number;
  /** False when the point faces the camera but lies outside the visible canvas. */
  inView: boolean;
}

export type CameraMoveListener = (body: Body) => void;

export interface GlobesApi {
  /** Resolves once both globes exist (not necessarily with imagery drawn). */
  readonly ready: Promise<void>;
  /** Resolves when both globes have drawn their first imagery. Rejects with the user-facing message on failure. */
  readonly imageryReady: Promise<void>;
  /**
   * Fly the camera of `body` to look straight down at (lat, lon) from `heightKm` above the surface.
   * Latitude/longitude in degrees, longitude east in -180..180. Resolves true when the flight
   * completes, false if it was cancelled. Instant when the user prefers reduced motion.
   */
  flyTo(body: Body, lat: number, lon: number, heightKm: number, durationSeconds?: number): Promise<boolean>;
  /** Canvas position of (lat, lon, height m) on `body`, or null when it is on the far side. */
  toCanvas(body: Body, lat: number, lon: number, heightM?: number): CanvasPoint | null;
  /** Reset one body (or both) to its home view. */
  resetView(body?: Body): void;
  /** The Cesium widget (viewer) of a body. */
  viewer(body: Body): CesiumWidget;
  /** The Cesium scene of a body. */
  scene(body: Body): Scene;
  /** Called whenever either camera moves (throttled by Cesium's camera.percentageChanged and on move end). */
  onCameraMove(listener: CameraMoveListener): () => void;
  /** Show or hide place names on both globes. */
  setLabelsVisible(visible: boolean): void;
  /** True while the user asks for reduced motion (flights become instant). */
  prefersReducedMotion(): boolean;

  /** Sunlight and time (header control): 'full-moon' (default), 'now', 'even'. */
  readonly sunlight: SunlightApi;
  /** Result markers on both globes. */
  readonly markers: MarkersApi;
  /** Paired fly-to for the comparison view. */
  readonly focus: FocusApi;
  /** Light beams between Earth points and their lunar twins. */
  readonly beams: BeamsApi;
  /** Mission video dialog. */
  readonly video: VideoApi;
}

export interface Modules {
  sunlight: SunlightApi;
  markers: MarkersApi;
  focus: FocusApi;
  beams: BeamsApi;
  video: VideoApi;
}
let modules: Modules | undefined;
function mod<K extends keyof Modules>(key: K): Modules[K] {
  if (!modules) throw new Error(`globesApi.${key} used before the globes were created; await globesApi.ready`);
  return modules[key];
}

const scratch = new Cartesian2();

let resolveReady!: () => void;
let resolveImagery!: () => void;
let rejectImagery!: (e: Error) => void;
const ready = new Promise<void>((r) => (resolveReady = r));
const imageryReady = new Promise<void>((res, rej) => {
  resolveImagery = res;
  rejectImagery = rej;
});
imageryReady.catch(() => undefined); // the loading screen reports failures; avoid unhandled rejections

let globes: Globes | undefined;
let labelsSetter: (v: boolean) => void = () => undefined;
const listeners = new Set<CameraMoveListener>();
const reducedQuery = typeof window !== 'undefined' ? window.matchMedia('(prefers-reduced-motion: reduce)') : undefined;

function view(body: Body): BodyView {
  if (!globes) throw new Error('globesApi used before the globes were created; await globesApi.ready');
  return body === 'earth' ? globes.earth : globes.moon;
}

export const globesApi: GlobesApi = {
  ready,
  imageryReady,

  flyTo(body, lat, lon, heightKm, durationSeconds = 2) {
    const v = view(body);
    const camera = v.scene.camera;
    const destination = Cartesian3.fromDegrees(lon, lat, heightKm * 1000, v.ellipsoid);
    const orientation = { heading: 0, pitch: -CesiumMath.PI_OVER_TWO, roll: 0 };
    camera.cancelFlight();
    v.atHome = false;
    if (this.prefersReducedMotion() || durationSeconds <= 0) {
      camera.setView({ destination, orientation });
      v.scene.requestRender();
      return Promise.resolve(true);
    }
    return new Promise<boolean>((resolve) => {
      camera.flyTo({
        destination,
        orientation,
        duration: durationSeconds,
        complete: () => resolve(true),
        cancel: () => resolve(false),
      });
      v.scene.requestRender();
    });
  },

  toCanvas(body, lat, lon, heightM = 0) {
    const v = view(body);
    const scene = v.scene;
    const ellipsoid = v.ellipsoid;
    const position = Cartesian3.fromDegrees(lon, lat, heightM, ellipsoid);
    // Horizon test in the ellipsoid's scaled space (exact for a sphere).
    const cam = ellipsoid.transformPositionToScaledSpace(scene.camera.positionWC, new Cartesian3());
    const pt = ellipsoid.transformPositionToScaledSpace(position, new Cartesian3());
    const toCam = Cartesian3.subtract(cam, pt, new Cartesian3());
    if (Cartesian3.dot(toCam, pt) <= 0) return null;
    const win = SceneTransforms.worldToWindowCoordinates(scene, position, scratch);
    if (!win) return null;
    const w = scene.canvas.clientWidth;
    const h = scene.canvas.clientHeight;
    return { x: win.x, y: win.y, inView: win.x >= 0 && win.y >= 0 && win.x <= w && win.y <= h };
  },

  resetView(body) {
    const instant = this.prefersReducedMotion();
    if (!body || body === 'earth') resetView(view('earth'), instant);
    if (!body || body === 'moon') resetView(view('moon'), instant);
  },

  viewer: (body) => view(body).widget,
  scene: (body) => view(body).scene,

  onCameraMove(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  setLabelsVisible(visible) {
    labelsSetter(visible);
  },

  prefersReducedMotion() {
    return reducedQuery?.matches ?? false;
  },

  get sunlight() {
    return mod('sunlight');
  },
  get markers() {
    return mod('markers');
  },
  get focus() {
    return mod('focus');
  },
  get beams() {
    return mod('beams');
  },
  get video() {
    return mod('video');
  },
};

/** Internal: called once by main.ts after the scenes are built. */
export function bindGlobes(g: Globes, setLabels: (v: boolean) => void, m: Modules): void {
  globes = g;
  labelsSetter = setLabels;
  modules = m;
  for (const v of [g.earth, g.moon]) {
    const fire = () => listeners.forEach((l) => l(v.body));
    v.scene.camera.changed.addEventListener(fire);
    v.scene.camera.moveEnd.addEventListener(fire);
  }
  resolveReady();
}

/** Internal: called by main.ts when the loading screen resolves. */
export function settleImagery(error?: string): void {
  if (error) rejectImagery(new Error(error));
  else resolveImagery();
}
