#!/usr/bin/env node
// No-WebGL and non-blocking loading test (builds nothing: run `npm run build` first). Serves dist/ as
// the other tests do and checks, in Chromium launched WITHOUT WebGL: one short message about the
// globes, no Cesium error panel, no unhandled console error, and the whole flow without globes
// (mission 1 by key: the five analogs and their heading; key 1: the pair panel; Escape twice; mission 2
// by click: its pair; Escape twice). Then, WITH WebGL at 1440x900: within 2 s of load the three
// mission cards are visible and clickable while the globes may still load, no element covering more
// than half of the viewport carries a loading message, and "Stars Beside You" is on screen once.
// Usage: node tests/nowebgl.mjs     Screenshots: $SHOTS_DIR/sliceC (default below).

import { existsSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { serve } from './lib/serve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(APP, 'dist');
const SHOTS = process.env.SHOTS_DIR ? join(process.env.SHOTS_DIR, 'sliceC') : join(APP, 'tests', 'shots', 'sliceC');
mkdirSync(SHOTS, { recursive: true });

const failures = [];
const ok = (m) => console.log(`ok   ${m}`);
const fail = (m) => {
  failures.push(m);
  console.log(`FAIL ${m}`);
};
const check = (c, m) => (c ? ok(m) : fail(m));

if (!existsSync(join(DIST, 'index.html'))) {
  console.error('dist/ is missing: run `npm run build` first');
  process.exit(2);
}
const srv = await serve(DIST);
// remote imagery is not needed here: the no-WebGL run never asks for it, the WebGL run may still be loading
const GLOBE_MSG = /cannot show the 3D globes/i;

// Watch for errors: console errors and uncaught page errors.
function watch(page) {
  const errors = [];
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text());
  });
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  return errors;
}

const visibleIntroCards = (page) =>
  page.evaluate(() =>
    [...document.querySelectorAll('#intro .choice')].filter((c) => {
      const r = c.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return false;
      const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return !!top && c.contains(top); // nothing covers it: a click lands on it
    }).length,
  );

const step = (page) => page.evaluate(() => window.starsFlow?.state.step);
const waitStep = (page, s) => page.waitForFunction((x) => window.starsFlow?.state.step === x, s, { timeout: 15_000 }).then(() => true, () => false);

// ---------- 1. without WebGL ----------
{
  // --disable-3d-apis removes WebGL from the renderer: getContext('webgl'/'webgl2') returns null
  const browser = await chromium.launch({ args: ['--disable-gpu', '--disable-3d-apis'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = watch(page);
  await page.goto(srv.base);
  const gl = await page.evaluate(() => {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  });
  check(!gl, `WebGL is really off in this browser (--disable-gpu --disable-3d-apis): getContext returned ${gl ? 'a context' : 'null'}`);
  await page.waitForFunction(() => window.starsFlow?.hasData(), null, { timeout: 30_000 });
  await page.waitForTimeout(500);

  const msgs = await page.evaluate((src) => {
    const re = new RegExp(src, 'i');
    const vis = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && !el.closest('[hidden], .sr-only');
    };
    // the innermost visible elements whose own text mentions the globes / WebGL
    const all = [...document.body.querySelectorAll('*')].filter((el) => vis(el) && [...el.childNodes].some((n) => n.nodeType === 3 && /WebGL|3D globes|3D view/i.test(n.nodeValue)));
    return {
      count: all.length,
      texts: all.map((el) => el.textContent.trim()),
      ours: all.filter((el) => re.test(el.textContent)).length,
      cesium: [...document.querySelectorAll('.cesium-widget-errorPanel')].filter(vis).length,
      dialogs: document.querySelectorAll('dialog[open]').length,
      stack: /\bat\s+\S+\s+\(|Error:\s|stack/i.test(document.body.innerText),
    };
  }, GLOBE_MSG.source);
  check(msgs.count === 1 && msgs.ours === 1, `exactly one message about the globes: ${JSON.stringify(msgs.texts)}`);
  check(msgs.cesium === 0, `no Cesium error panel visible (${msgs.cesium})`);
  check(msgs.dialogs === 0 && !msgs.stack, 'no second dialog and no stack text');
  check((await visibleIntroCards(page)) === 3, 'the three mission cards are visible and clickable');
  await page.screenshot({ path: join(SHOTS, 'nowebgl-start-1440.png') });

  // mission 1 by key
  await page.keyboard.press('1');
  check(await waitStep(page, 'pick'), 'key 1 opens the Rover mission');
  await page.waitForFunction(() => !!document.getElementById('top5-title'), null, { timeout: 15_000 }).catch(() => undefined);
  const r1 = await page.evaluate(() => ({
    n: document.getElementById('top5-title')?.closest('section')?.querySelectorAll('li button').length ?? 0,
    head: document.getElementById('top5-title')?.textContent.trim() ?? '',
    loading: /\bLoading\b/.test(document.getElementById('mission-panel').innerText) || !!document.querySelector('#intro [aria-busy="true"]'),
  }));
  check(r1.n === 5, `Rover: five analogs listed (${r1.n})`);
  check(r1.head === 'Five of the 254 sites tied at the top of our model', `Rover heading: "${r1.head}"`);
  check(!r1.loading, 'Rover: nothing left on "Loading"');
  await page.screenshot({ path: join(SHOTS, 'nowebgl-rover-1440.png') });

  await page.keyboard.press('1');
  check(await waitStep(page, 'compare'), 'key 1 again opens the pair panel');
  const d1 = await page.evaluate(() => {
    const d = document.getElementById('detail-panel');
    return !d.hidden && d.innerText.trim().length > 40;
  });
  check(d1, 'the pair panel is shown with its content');
  await page.keyboard.press('Escape');
  check(await waitStep(page, 'pick'), 'Escape: back to the Rover mission');
  await page.keyboard.press('Escape');
  check(await waitStep(page, 'choose'), 'Escape: back to the start screen');

  // mission 2 by click, its one pair by click
  await page.locator('#intro .choice').nth(1).click();
  check(await waitStep(page, 'pick'), 'a click opens mission 2');
  await page.waitForFunction(() => !!document.getElementById('top5-title'), null, { timeout: 15_000 }).catch(() => undefined);
  const five2 = page.locator('#mission-panel section:has(#top5-title) li button');
  const np = await five2.count();
  check(np >= 1, `mission 2: its analogs are listed (${np}), heading "${await page.locator('#top5-title').textContent().catch(() => '')}"`);
  if (np) {
    await five2.first().click();
    check(await waitStep(page, 'compare'), 'mission 2: a click on its first pair opens the pair panel');
    check(await page.evaluate(() => !document.getElementById('detail-panel').hidden), 'mission 2: the pair panel is shown');
    await page.keyboard.press('Escape');
    check(await waitStep(page, 'pick'), 'mission 2: Escape back to the mission');
  }
  await page.keyboard.press('Escape');
  check(await waitStep(page, 'choose'), 'mission 2: Escape back to the start screen');

  // the video (step 4 of mission 1) still opens without globes; the audio guide switch answers
  check(await page.evaluate(() => window.starsBesideYou?.hasGlobes() === false), 'the globes API reports no globes');
  await page.keyboard.press('1');
  await waitStep(page, 'pick');
  await page.keyboard.press('1');
  await waitStep(page, 'compare');
  await page.evaluate(() => window.starsFlow.goToStep('video'));
  const vid = await page.waitForFunction(() => !!document.querySelector('dialog[open] video'), null, { timeout: 10_000 }).then(() => true, () => false);
  check(vid, 'the mission video dialog opens');
  await page.keyboard.press('Escape');
  check(await page.waitForFunction(() => !document.querySelector('dialog[open]'), null, { timeout: 5000 }).then(() => true, () => false), 'Escape closes the video');
  const audio = page.locator('#switches button, #switches [role="switch"], #switches input').filter({ hasText: /Audio guide/i });
  if (await audio.count()) {
    await audio.first().click();
    const on = await page.evaluate(() => [...document.querySelectorAll('#switches [aria-checked], #switches [aria-pressed]')].some((e) => /Audio guide/i.test(e.textContent) && /true/.test(e.getAttribute('aria-checked') ?? e.getAttribute('aria-pressed'))));
    check(on, 'the audio guide switch turns on');
    await audio.first().click();
  } else console.log('info the audio guide switch was not found by its label');
  check(await page.evaluate(() => !document.getElementById('loading-retry')?.checkVisibility()), 'no Retry shown when nothing failed');

  check(errors.length === 0, `no console error (${errors.length})${errors.length ? `: ${errors.slice(0, 3).join(' | ')}` : ''}`);
  await browser.close();
}

// ---------- 2. with WebGL: loading does not block ----------
{
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = watch(page);
  const t0 = Date.now();
  await page.goto(srv.base, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.querySelectorAll('#intro .choice').length === 3, null, { timeout: 2000 }).catch(() => undefined);
  const dt = Date.now() - t0;
  const cards = await visibleIntroCards(page);
  check(cards === 3 && dt <= 2000, `the three mission cards are visible and clickable ${dt} ms after load (${cards})`);
  const cover = await page.evaluate(() => {
    const area = innerWidth * innerHeight;
    return [...document.body.querySelectorAll('*')]
      .filter((el) => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width * r.height > area / 2 && s.visibility !== 'hidden' && s.display !== 'none' && /loading/i.test(el.innerText ?? '') && !el.querySelector('#intro, header');
      })
      .map((el) => el.id || el.className);
  });
  check(cover.length === 0, `no element over half the viewport carries a loading message (${JSON.stringify(cover)})`);
  check(await page.evaluate(() => !document.getElementById('loading-retry')?.checkVisibility()), 'no Retry shown while the globes load');
  const name = await page.evaluate(() => (document.body.innerText.match(/Stars Beside You/g) ?? []).length);
  check(name === 1, `"Stars Beside You" appears once on screen (${name})`);
  await page.waitForTimeout(Math.max(0, 1000 - (Date.now() - t0)));
  await page.screenshot({ path: join(SHOTS, 'webgl-1s-1440.png') });
  await page.waitForTimeout(Math.max(0, 12_000 - (Date.now() - t0)));
  await page.screenshot({ path: join(SHOTS, 'webgl-12s-1440.png') });
  const st = await page.evaluate(() => ({ earth: !document.getElementById('earth-status').hidden, moon: !document.getElementById('moon-status').hidden }));
  console.log(`info at 12 s the loading lines still shown: Earth ${st.earth}, Moon ${st.moon}`);
  check(errors.length === 0, `no console error with WebGL (${errors.length})${errors.length ? `: ${errors.slice(0, 3).join(' | ')}` : ''}`);
  await browser.close();
}

await srv.close();
console.log(failures.length ? `\n${failures.length} failure(s)` : '\nall checks passed');
process.exit(failures.length ? 1 : 0);
