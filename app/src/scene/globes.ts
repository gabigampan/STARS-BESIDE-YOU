// Builds the two Cesium scenes (Earth and Moon) that share one clock and so one Sun.

import {
  Cartesian3,
  CesiumWidget,
  Clock,
  ClockStep,
  Color,
  DirectionalLight,
  Ellipsoid,
  ImageryLayer,
  JulianDate,
  Material,
  Math as CesiumMath,
  PerspectiveFrustum,
  Scene,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  SkyBox,
  SunLight,
} from 'cesium';
import { EARTH_RADIUS_M, MOON_RADIUS_M } from '../config';
import { createEarthImagery, updateSharpLayer, type EarthImagery } from '../imagery/earthLayers';
import { createMoonImagery } from '../imagery/moonLayers';
import { MoonLabels } from './moonLabels';
import { subsolarPointEarth, sunDirectionMoonFixed } from './sun';

export type Body = 'earth' | 'moon';

export interface ImageryStatus {
  /** True once the globe has drawn every tile it needs for the current view at least once. */
  ready: boolean;
  /** Set when base imagery failed; a sentence the user can act on. */
  error?: string;
}

export interface BodyView {
  body: Body;
  widget: CesiumWidget;
  scene: Scene;
  ellipsoid: Ellipsoid;
  radiusM: number;
  /** Centre of the home view. */
  home: { lat: number; lon: number };
  status: ImageryStatus;
  /** True while the camera is on the home view and the user has not moved it. */
  atHome: boolean;
  onStatus: (listener: (s: ImageryStatus) => void) => void;
}

export interface Globes {
  clock: Clock;
  earth: BodyView;
  moon: BodyView;
  earthImagery: EarthImagery;
  moonLabels: MoonLabels;
  /** Day/night shading on both globes: true = physical (Sun from the shared clock), false = even light. */
  setPhysicalLighting(on: boolean): void;
  physicalLighting(): boolean;
}

const RESOLUTION_CAP = 1.5;

function makeWidget(container: HTMLElement, clock: Clock, ellipsoid: Ellipsoid, isMoon: boolean): CesiumWidget {
  const dpr = window.devicePixelRatio || 1;
  const widget = new CesiumWidget(container, {
    clock,
    ellipsoid,
    baseLayer: false, // never fall back to ion imagery
    skyBox: SkyBox.createEarthSkyBox(), // Cesium's bundled Tycho-2 star map
    skyAtmosphere: isMoon ? false : undefined,
    requestRenderMode: true,
    maximumRenderTimeChange: 60, // re-light when simulated time moves a minute
    scene3DOnly: true,
    useBrowserRecommendedResolution: false,
    msaaSamples: 4,
    contextOptions: { webgl: { alpha: false, preserveDrawingBuffer: false, powerPreference: 'high-performance' } },
  });
  widget.resolutionScale = Math.min(dpr, RESOLUTION_CAP) / dpr;
  widget.scene.backgroundColor = Color.BLACK;
  // Free rotation in every direction (the Moon's poles matter for these missions).
  widget.scene.camera.constrainedAxis = undefined as unknown as Cartesian3;
  widget.scene.camera.percentageChanged = 0.02;
  return widget;
}

/** Camera height that fits a sphere of radius r in the canvas with a margin. */
export function fitHeight(scene: Scene, radiusM: number, margin = 1.18): number {
  const frustum = scene.camera.frustum as PerspectiveFrustum;
  const w = scene.canvas.clientWidth || 1;
  const h = scene.canvas.clientHeight || 1;
  const fov = frustum.fov ?? CesiumMath.toRadians(60);
  // Cesium's fov applies to the larger canvas dimension.
  const halfSmall = Math.atan(Math.tan(fov / 2) * (Math.min(w, h) / Math.max(w, h)));
  return (radiusM * margin) / Math.sin(halfSmall) - radiusM;
}

function trackImagery(view: BodyView, layer: ImageryLayer, sourceName: string, host: string): void {
  let ok = 0;
  let failed = 0;
  const listeners: ((s: ImageryStatus) => void)[] = [];
  view.onStatus = (l) => listeners.push(l);
  const emit = () => listeners.forEach((l) => l(view.status));

  const provider = layer.imageryProvider;
  const original = provider.requestImage.bind(provider);
  provider.requestImage = ((x: number, y: number, level: number, request?: unknown) => {
    const p = original(x, y, level, request as never);
    if (p) {
      Promise.resolve(p).then(
        () => {
          ok++;
        },
        () => undefined,
      );
    }
    return p;
  }) as typeof provider.requestImage;

  provider.errorEvent.addEventListener((err) => {
    failed++;
    if (!view.status.ready && failed >= 2 && ok === 0) {
      view.status.error =
        `${sourceName} did not load: ${host} refused or failed ${failed} tile requests ` +
        `(last: level ${err.level}, column ${err.x}, row ${err.y}). Check the network connection and reload.`;
      emit();
    }
  });

  // Ready once real imagery is on screen: every tile of the view loaded, or (on slow devices)
  // a few base tiles decoded and drawn for several frames. Detail keeps refining afterwards.
  const globe = view.scene.globe;
  let framesWithImagery = 0;
  view.scene.postRender.addEventListener(() => {
    if (view.status.ready || view.status.error) return;
    if (ok >= 4) framesWithImagery++;
    if ((globe.tilesLoaded && ok > 0) || framesWithImagery >= 4) {
      view.status.ready = true;
      emit();
    } else if (ok > 0) {
      view.scene.requestRender();
    }
  });
}

export function createGlobes(earthEl: HTMLElement, moonEl: HTMLElement, reducedMotion: () => boolean): Globes {
  const clock = new Clock({
    currentTime: startTime(),
    clockStep: ClockStep.SYSTEM_CLOCK_MULTIPLIER,
    multiplier: 1,
    shouldAnimate: true,
  });

  // ---------- Earth ----------
  const earthWidget = makeWidget(earthEl, clock, Ellipsoid.WGS84, false);
  const es = earthWidget.scene;
  const eg = es.globe;
  eg.enableLighting = true;
  eg.dynamicAtmosphereLighting = true;
  eg.dynamicAtmosphereLightingFromSun = true;
  eg.showGroundAtmosphere = true;
  eg.baseColor = Color.fromCssColorString('#0b1a2c');
  eg.maximumScreenSpaceError = 1.6;
  // Shading (and night lights) fade out below ~2,500 km altitude so close-ups always show daylight.
  eg.lightingFadeOutDistance = EARTH_RADIUS_M + 2_500_000;
  eg.lightingFadeInDistance = EARTH_RADIUS_M + 6_000_000;
  eg.nightFadeOutDistance = EARTH_RADIUS_M + 2_500_000;
  eg.nightFadeInDistance = EARTH_RADIUS_M + 6_000_000;
  es.light = new SunLight();
  es.fog.enabled = true;
  if (es.skyAtmosphere) {
    es.skyAtmosphere.show = true;
    es.skyAtmosphere.saturationShift = -0.08;
  }
  if (es.sun) es.sun.show = true;
  if (es.moon) es.moon.show = true;
  const earthImagery = createEarthImagery();
  es.imageryLayers.add(earthImagery.base);
  es.imageryLayers.add(earthImagery.sharp);
  es.imageryLayers.add(earthImagery.night);
  es.imageryLayers.add(earthImagery.labels);
  const ssc = es.screenSpaceCameraController;
  ssc.minimumZoomDistance = 400;
  ssc.maximumZoomDistance = 9.0e7;

  // ---------- Moon ----------
  const moonWidget = makeWidget(moonEl, clock, Ellipsoid.MOON, true);
  const ms = moonWidget.scene;
  const mg = ms.globe;
  mg.enableLighting = true;
  mg.showGroundAtmosphere = false;
  mg.dynamicAtmosphereLighting = false;
  mg.baseColor = Color.fromCssColorString('#1a1a1a');
  mg.maximumScreenSpaceError = 1.6;
  // Day/night shading stays on from far away and fades out close in, so any site can be inspected.
  mg.lightingFadeOutDistance = MOON_RADIUS_M + 650_000;
  mg.lightingFadeInDistance = MOON_RADIUS_M + 1_900_000;
  ms.fog.enabled = false;
  if (ms.sun) ms.sun.show = false; // Cesium places its Sun billboard in Earth's frame
  if (ms.moon) ms.moon.show = false;
  const moonLight = new DirectionalLight({ direction: new Cartesian3(-1, 0, 0), intensity: 1.0 });
  ms.light = moonLight;
  ms.imageryLayers.add(createMoonImagery());
  const mssc = ms.screenSpaceCameraController;
  mssc.minimumZoomDistance = 2_000;
  mssc.maximumZoomDistance = 3.0e7;

  // Airless body: a hard terminator and a dark night side (faded out close in, like the shading).
  const nightMaterial = new Material({
    fabric: {
      type: 'LunarNight',
      uniforms: { strength: 0.78 },
      source: `
        czm_material czm_getMaterial(czm_materialInput materialInput) {
          czm_material m = czm_getDefaultMaterial(materialInput);
          float d = dot(normalize(materialInput.normalEC), czm_lightDirectionEC);
          float dark = 1.0 - smoothstep(-0.015, 0.05, d);
          m.diffuse = vec3(0.0);
          m.alpha = dark * strength;
          return m;
        }`,
    },
    translucent: true,
  });
  mg.material = nightMaterial;

  let physical = true;

  // Sun direction for the Moon, in its body-fixed frame, from the shared clock.
  const sunDir = new Cartesian3();
  let lastLit: JulianDate | undefined;
  const relightMoon = (time: JulianDate) => {
    if (lastLit && Math.abs(JulianDate.secondsDifference(time, lastLit)) < 30) return;
    lastLit = JulianDate.clone(time, lastLit);
    sunDirectionMoonFixed(time, sunDir);
    moonLight.direction = Cartesian3.negate(sunDir, moonLight.direction);
    ms.requestRender();
  };
  relightMoon(clock.currentTime);
  clock.onTick.addEventListener((c) => relightMoon(c.currentTime));

  const moonLabels = new MoonLabels(ms);

  const earth: BodyView = {
    body: 'earth',
    widget: earthWidget,
    scene: es,
    ellipsoid: Ellipsoid.WGS84,
    radiusM: EARTH_RADIUS_M,
    // Home faces the daylit hemisphere (src/modules/sunlight.ts moves it when the light changes).
    home: earthHome(clock.currentTime),
    status: { ready: false },
    atHome: true,
    onStatus: () => undefined,
  };
  const moon: BodyView = {
    body: 'moon',
    widget: moonWidget,
    scene: ms,
    ellipsoid: Ellipsoid.MOON,
    radiusM: MOON_RADIUS_M,
    home: moonHome(clock.currentTime),
    status: { ready: false },
    atHome: true,
    onStatus: () => undefined,
  };
  trackImagery(earth, earthImagery.base, 'NASA GIBS Blue Marble imagery', 'gibs.earthdata.nasa.gov');
  trackImagery(moon, ms.imageryLayers.get(0), 'NASA Moon Trek LRO WAC imagery', 'trek.nasa.gov');

  // Per-camera updates: Sentinel-2 fade on Earth, night darkness and names on the Moon.
  const updateEarthCamera = () => {
    const h = es.camera.positionCartographic.height;
    let changed = updateSharpLayer(earthImagery.sharp, h);
    // Cesium applies nightAlpha without the distance fade; match it to the shading fade.
    const dist = Cartesian3.magnitude(es.camera.positionWC);
    const t = physical
      ? Math.min(1, Math.max(0, (dist - eg.lightingFadeOutDistance) / (eg.lightingFadeInDistance - eg.lightingFadeOutDistance)))
      : 0;
    if (Math.abs(earthImagery.night.nightAlpha - t) > 0.01) {
      earthImagery.night.nightAlpha = t;
      earthImagery.night.show = t > 0;
      changed = true;
    }
    if (changed) es.requestRender();
  };
  es.camera.changed.addEventListener(updateEarthCamera);
  es.camera.moveEnd.addEventListener(updateEarthCamera);

  const updateMoonCamera = () => {
    const dist = Cartesian3.magnitude(ms.camera.positionWC);
    const t = (dist - mg.lightingFadeOutDistance) / (mg.lightingFadeInDistance - mg.lightingFadeOutDistance);
    nightMaterial.uniforms.strength = physical ? 0.78 * Math.min(1, Math.max(0, t)) : 0;
    moonLabels.update();
  };
  ms.camera.changed.addEventListener(updateMoonCamera);
  ms.camera.moveEnd.addEventListener(updateMoonCamera);

  for (const view of [earth, moon]) {
    // Double click resets that globe.
    const handler = new ScreenSpaceEventHandler(view.scene.canvas);
    handler.setInputAction(() => resetView(view, reducedMotion()), ScreenSpaceEventType.LEFT_DOUBLE_CLICK);
    // Any direct manipulation leaves the home view; until then the home view follows pane resizes.
    const leave = () => (view.atHome = false);
    view.scene.canvas.addEventListener('pointerdown', leave);
    view.scene.canvas.addEventListener('wheel', leave, { passive: true });
    let lastSize = '';
    new ResizeObserver(() => {
      const size = `${view.scene.canvas.clientWidth}x${view.scene.canvas.clientHeight}`;
      if (size === lastSize) return;
      lastSize = size;
      if (view.atHome) resetView(view, true);
      else view.scene.requestRender();
    }).observe(view.widget.container);
  }

  const setPhysicalLighting = (on: boolean) => {
    physical = on;
    eg.enableLighting = on;
    eg.dynamicAtmosphereLighting = on;
    eg.dynamicAtmosphereLightingFromSun = on;
    mg.enableLighting = on;
    mg.material = on ? nightMaterial : undefined;
    updateEarthCamera();
    updateMoonCamera();
    es.requestRender();
    ms.requestRender();
  };

  return { clock, earth, moon, earthImagery, moonLabels, setPhysicalLighting, physicalLighting: () => physical };
}

/** Simulation start: now, or the ISO time in the page URL (?time=2026-11-24T12:00:00Z). */
function startTime(): JulianDate {
  const param = new URLSearchParams(window.location.search).get('time');
  if (param) {
    const ms = Date.parse(param);
    if (Number.isFinite(ms)) return JulianDate.fromDate(new Date(ms));
  }
  return JulianDate.now();
}

/**
 * Home view centre on Earth that faces the sunlit hemisphere: the sub-solar meridian, with the
 * latitude pulled 25 degrees north (most land is in the north) and kept within 25 degrees of the equator.
 */
export function earthHome(time: JulianDate): { lat: number; lon: number } {
  const sub = subsolarPointEarth(time);
  return { lat: Math.max(-25, Math.min(25, sub.lat + 25)), lon: sub.lon };
}

/** Home view centre on the Moon that faces the sunlit hemisphere: the sub-solar point (latitude kept within 30 degrees). */
export function moonHome(time: JulianDate): { lat: number; lon: number } {
  const d = sunDirectionMoonFixed(time, new Cartesian3());
  const lat = CesiumMath.toDegrees(Math.asin(Math.max(-1, Math.min(1, d.z))));
  const lon = CesiumMath.toDegrees(Math.atan2(d.y, d.x));
  return { lat: Math.max(-30, Math.min(30, lat)), lon };
}

export function homeDestination(view: BodyView): Cartesian3 {
  const h = fitHeight(view.scene, view.radiusM);
  return Cartesian3.fromDegrees(view.home.lon, view.home.lat, h, view.ellipsoid);
}

/** Put the camera back on the home view: body centred, north up. */
export function resetView(view: BodyView, instant: boolean): void {
  const camera = view.scene.camera;
  const destination = homeDestination(view);
  const orientation = { heading: 0, pitch: -CesiumMath.PI_OVER_TWO, roll: 0 };
  camera.cancelFlight();
  view.atHome = true;
  if (instant) {
    camera.setView({ destination, orientation });
  } else {
    camera.flyTo({ destination, orientation, duration: 1.2 });
  }
  view.scene.requestRender();
}
