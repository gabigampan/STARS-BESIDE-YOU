import '@fontsource/barlow/latin-400.css';
import '@fontsource/barlow/latin-500.css';
import '@fontsource/barlow-semi-condensed/latin-500.css';
import '@fontsource/barlow-semi-condensed/latin-600.css';
import '@fontsource/michroma/latin-400.css';
import '@fontsource/ibm-plex-mono/latin-400.css';
import '@fontsource/ibm-plex-mono/latin-500.css';
import 'cesium/Build/Cesium/Widgets/CesiumWidget/CesiumWidget.css';
import './styles.css';
import './flow/flow.css';
import './ui/mobileFold.css';
import './hud/hud.css';
import { setupHud } from './hud/hud';

import { bindGlobes, bindNoGlobes, globesApi, settleImagery } from './api';
import { IMAGERY_TIMEOUT_MS } from './config';
import { createGlobes, resetView } from './scene/globes';
import { applyIonUpgrade, ionEnabled } from './scene/ionUpgrade';
import { Beams } from './modules/beams';
import { Focus } from './modules/focus';
import { Markers } from './modules/markers';
import { Sunlight } from './modules/sunlight';
import { VideoDialog } from './modules/video';
import { LoadingScreen, setupCredits, setupResetButtons } from './ui/shell';
import { FlowApp } from './flow/app';
import { a11y, type A11y } from './a11y';
import { setupKeys } from './a11y/keys';
import { setupMobileFold } from './ui/mobileFold';

declare global {
  interface Window {
    /** The globes API, for the browser console and automated tests. */
    starsBesideYou?: typeof globesApi;
    /** The product flow (state, data store, actions), for the console and automated tests. */
    starsFlow?: FlowApp;
    /** The accessibility layer (switches, audio guide, palette), for the console and tests. */
    starsA11y?: A11y;
  }
}

const NO_GLOBES_MESSAGE =
  'This browser cannot show the 3D globes (WebGL is off). The missions, the five analogs, the pair details, the videos and the audio guide still work.';

function hasWebGL(): boolean {
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2') ?? c.getContext('webgl');
    gl?.getExtension('WEBGL_lose_context')?.loseContext(); // only a probe: give the context back
    return !!gl;
  } catch {
    return false;
  }
}

const CREDITS = () => [
  {
    source: 'Audio guide (19 recordings)',
    used: 'The spoken guide of the start screen, the three mission introductions and the five analogs shown for each mission (public/audio). Off by default; its text is always shown as a caption.',
    credit: 'Recorded by the Stars Beside You team (text to speech, American English voice); shipped unchanged, with SHA-256 checksums.',
    licence: "The team's own recordings for this project.",
    link: '',
  },
  {
    source: 'Colour-blind mode palette: Okabe-Ito colours',
    used: 'Every colour of the interface and of the globe overlays when "Colour-blind mode" is on; checked with the culori colour-vision-deficiency simulation (protanopia, deuteranopia, tritanopia).',
    credit: 'M. Okabe and K. Ito, "Color Universal Design (CUD): how to make figures and presentations that are friendly to colorblind people", J*Fly.',
    licence: 'Published colour values.',
    link: 'https://jfly.uni-koeln.de/color/',
  },
  ...(ionEnabled()
    ? [
        {
          source: 'Cesium ion (optional upgrade)',
          used: 'Cesium World Terrain, Bing Maps aerial imagery and Cesium Moon terrain when the deployment has an ion token.',
          credit: 'Cesium ion, Cesium GS, Inc.; Bing Maps aerial imagery, Earthstar Geographics SIO, © Microsoft Corporation (provider credits as returned by Cesium ion for asset 2).',
          licence: 'Cesium ion terms of service.',
          link: 'https://cesium.com/platform/cesium-ion/',
        },
      ]
    : []),
];

function main(): void {
  try {
    mainInner();
  } finally {
    // the Mission Control look's motion (src/hud/hud.ts), started once the synchronous start-up
    // (Cesium's two viewers) is done, so the boot is not spent behind it; the first paint follows
    setupHud(() => globesApi.prefersReducedMotion());
  }
}

function mainInner(): void {
  // the switches, caption and palette first: they are on every screen, even when the 3D view fails
  window.starsA11y = a11y();
  const loading = new LoadingScreen(IMAGERY_TIMEOUT_MS);
  const earthEl = document.getElementById('earth-globe') as HTMLElement;
  const moonEl = document.getElementById('moon-globe') as HTMLElement;
  let globes;
  try {
    // checked first, so Cesium never puts up its own error box next to ours
    if (!hasWebGL()) throw new Error('WebGL is off');
    globes = createGlobes(earthEl, moonEl, () => globesApi.prefersReducedMotion());
  } catch (err) {
    console.warn(`[globes] the 3D view could not start: ${err instanceof Error ? err.message : String(err)}`);
    for (const el of [earthEl, moonEl]) el.replaceChildren();
    loading.noGlobes(NO_GLOBES_MESSAGE);
    bindNoGlobes(new VideoDialog());
    window.starsBesideYou = globesApi;
    settleImagery('WebGL unavailable');
    setupCredits(CREDITS());
    return;
  }

  const reduced = () => globesApi.prefersReducedMotion();
  // Light first (it sets the home views to face the sunlit side), then the home views.
  const sunlight = new Sunlight(globes, reduced);
  sunlight.start();
  resetView(globes.earth, true);
  resetView(globes.moon, true);

  const setLabels = (visible: boolean) => {
    globes.earthImagery.labels.show = visible;
    globes.earth.scene.requestRender();
    globes.moonLabels.setEnabled(visible);
  };
  bindGlobes(globes, setLabels, {
    sunlight,
    markers: new Markers(globes),
    focus: new Focus(globes, reduced),
    beams: new Beams(globes, reduced),
    video: new VideoDialog(),
  });
  window.starsBesideYou = globesApi;

  globes.earth.onStatus((s) => loading.update('earth', s));
  globes.moon.onStatus((s) => loading.update('moon', s));
  void loading.finished.then((error) => {
    settleImagery(error);
    // the loading screen has closed: keyboard focus goes to the heading of the first screen
    if (!error && window.starsFlow?.state.step === 'choose' && (document.activeElement === document.body || !document.activeElement)) {
      (document.getElementById('intro-title') as HTMLElement | null)?.focus({ preventScroll: true });
    }
  });

  globes.moonLabels.load().catch((err: unknown) => {
    // Names are secondary: the Moon stays usable, and the reason is shown in the caption.
    console.warn(`[labels] lunar feature names unavailable: ${err instanceof Error ? err.message : String(err)}`);
  });

  setupCredits(CREDITS());
  // "Place names" is a switch of the header (src/a11y/index.ts), on by default
  window.starsA11y?.setPlaceNamesHandler(setLabels);
  setupResetButtons((body) => globesApi.resetView(body));

  // Keep the home view fitted when panes change size (rotation, window resize, stacked/side-by-side).
  let resizeTimer = 0;
  window.addEventListener('resize', () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      globes.earth.scene.requestRender();
      globes.moon.scene.requestRender();
      globes.moonLabels.update();
    }, 150);
  });

  if (ionEnabled()) void applyIonUpgrade(globes);
}

/** `?flow=off` leaves the bare scene (used by the interaction-module tests, which bring their own items). */
function startFlow(): void {
  if (new URLSearchParams(window.location.search).get('flow') === 'off') return;
  window.starsFlow = new FlowApp();
  setupKeys(window.starsFlow, a11y());
  setupMobileFold();
}

// Boot: the panels first (they need only the data bundle), then the globes once the start screen
// has its mission cards (or after 1.5 s), so a slow 3D start never holds the page.
window.starsA11y = a11y();
startFlow();
whenStartScreenShown(main);

function whenStartScreenShown(then: () => void): void {
  const t0 = performance.now();
  const tick = () => {
    const f = window.starsFlow;
    if (!f || f.hasData() || f.error() || performance.now() - t0 > 1500) window.setTimeout(then, 0);
    else requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
