import '@fontsource/barlow/latin-400.css';
import '@fontsource/barlow/latin-500.css';
import '@fontsource/barlow-semi-condensed/latin-500.css';
import '@fontsource/barlow-semi-condensed/latin-600.css';
import 'cesium/Build/Cesium/Widgets/CesiumWidget/CesiumWidget.css';
import './styles.css';
import './flow/flow.css';

import { bindGlobes, globesApi, settleImagery } from './api';
import { IMAGERY_TIMEOUT_MS } from './config';
import { createGlobes, resetView } from './scene/globes';
import { applyIonUpgrade, ionEnabled } from './scene/ionUpgrade';
import { Beams } from './modules/beams';
import { Focus } from './modules/focus';
import { Markers } from './modules/markers';
import { Sunlight, bindSunlightControl } from './modules/sunlight';
import { VideoDialog } from './modules/video';
import { LoadingScreen, setupCredits, setupLabelsToggle, setupResetButtons, setupViewMenu } from './ui/shell';
import { FlowApp } from './flow/app';
import { a11y, type A11y } from './a11y';
import { setupKeys } from './a11y/keys';

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

function main(): void {
  // the switches, caption and palette first: they are on every screen, even when the 3D view fails
  window.starsA11y = a11y();
  const loading = new LoadingScreen(IMAGERY_TIMEOUT_MS);
  let globes;
  try {
    globes = createGlobes(
      document.getElementById('earth-globe') as HTMLElement,
      document.getElementById('moon-globe') as HTMLElement,
      () => globesApi.prefersReducedMotion(),
    );
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    loading.fail(`The 3D view could not start: ${reason}. This browser or device may not support WebGL 2 or WebGL.`);
    settleImagery('WebGL unavailable');
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
  void loading.finished.then((error) => settleImagery(error));

  globes.moonLabels.load().catch((err: unknown) => {
    // Names are secondary: the Moon stays usable, and the reason is shown in the caption.
    const note = document.querySelector('#moon-pane .pane-note');
    if (note) note.textContent = `Feature names unavailable (${err instanceof Error ? err.message : String(err)})`;
  });

  setupCredits(
    ionEnabled()
      ? [
          {
            source: 'Cesium ion (optional upgrade)',
            used: 'Cesium World Terrain, Bing Maps aerial imagery and Cesium Moon terrain when the deployment has an ion token.',
            credit: 'Cesium ion; imagery credits are shown on the globe.',
            licence: 'Cesium ion terms of service.',
            link: 'https://cesium.com/platform/cesium-ion/',
          },
        ]
      : [],
  );
  setupLabelsToggle(setLabels);
  setupViewMenu();
  setupResetButtons((body) => globesApi.resetView(body));
  bindSunlightControl(sunlight);

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
}

main();
startFlow();
