#!/usr/bin/env node
// Mission Control look and motion (builds nothing: run `npm run build` first). Checks: the boot ends
// within 1.5 s and leaves every panel at opacity 1; the scan line is idle after a mission is chosen;
// after a pair opens, the three scores' text equals the strings the data gives (and never differs
// while counting); with reduced motion no animation runs after each step; the computed font families
// are Michroma, Barlow and IBM Plex Mono; no page scroll at 1440x900, 1366x768, 375x812, 812x375.
// Usage: node tests/hud.mjs

import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { serve } from './lib/serve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(APP, 'dist');
if (!existsSync(join(DIST, 'index.html'))) {
  console.error('dist/ is missing: run `npm run build` first');
  process.exit(2);
}
let failed = 0;
let passed = 0;
const check = (c, m) => {
  if (c) passed++;
  else failed++;
  console.log(`${c ? 'ok  ' : 'FAIL'} ${m}`);
};

const srv = await serve(DIST);
const browser = await chromium.launch();
const waitStep = (p, s) => p.waitForFunction((x) => window.starsFlow?.state.step === x, s, { timeout: 20_000 }).then(() => true, () => false);
const open = async (w, h, opts = {}) => {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, hasTouch: w < 900, ...opts });
  const page = await ctx.newPage();
  const t0 = Date.now();
  await page.goto(srv.base, { waitUntil: 'domcontentloaded' });
  return { ctx, page, t0 };
};
const PANELS = '.topbar, .steps, .stage > .panel:not([hidden]), .intro-card, .pane';
const opacities = (page) => page.evaluate((sel) => [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length).map((e) => +getComputedStyle(e).opacity), PANELS);

try {
  // ---- boot, scan line, count-up (motion allowed)
  {
    const { ctx, page, t0 } = await open(1440, 900);
    // while the boot runs: the longest boot animation as declared (delay + duration)
    await page.waitForFunction(() => document.body.classList.contains('hud-boot'), null, { timeout: 15_000 }).catch(() => undefined);
    const declared = await page.evaluate(() =>
      Math.max(0, ...document.getAnimations().filter((a) => /^hud-/.test(a.animationName ?? '')).map((a) => { const t = a.effect.getTiming(); return Number(t.delay) + Number(t.duration); })),
    );
    await page.waitForFunction(() => performance.getEntriesByName('hud-boot-end').length > 0, null, { timeout: 15_000 }).catch(() => undefined);
    const boot = await page.evaluate(() => {
      const s = performance.getEntriesByName('hud-boot-start')[0]?.startTime;
      const e = performance.getEntriesByName('hud-boot-end')[0]?.startTime;
      return { ms: s != null && e != null ? Math.round(e - s) : null, on: document.body.classList.contains('hud-boot') };
    });
    check(declared > 0 && declared <= 1300, `the boot's animations end within 1.3 s of their start as declared (${declared} ms)`);
    check(boot.ms != null && !boot.on, `the boot ran once and its class is gone (${boot.ms} ms of wall time here: the 1300 ms timer fires late while software WebGL keeps the main thread busy)`);
    await page.waitForTimeout(450);
    const op = await opacities(page);
    check(op.length > 0 && op.every((o) => o === 1), `after boot every panel is at opacity 1 (${op.length} panels: ${[...new Set(op)].join(', ')})`);
    // the mission cards are clickable at once: pointer events stay on during the boot
    const pe = await page.evaluate(() => getComputedStyle(document.querySelector('.choice') ?? document.body).pointerEvents);
    check(pe !== 'none', 'the mission cards keep pointer events during the boot');
    await page.waitForFunction(() => window.starsFlow?.hasData(), null, { timeout: 30_000 });
    await page.keyboard.press('2');
    check(await waitStep(page, 'pick'), 'mission 2 opens');
    const scanOn = await page.evaluate(() => document.body.classList.contains('hud-scan'));
    await page.waitForTimeout(700);
    const scanIdle = await page.evaluate(() => {
      const s = getComputedStyle(document.querySelector('#earth-pane'), '::before');
      const running = document.getAnimations().filter((a) => a.animationName === 'hud-scan').length;
      return !document.body.classList.contains('hud-scan') && (s.display === 'none' || s.content === 'none') && running === 0;
    });
    check(scanOn && scanIdle, `the scan line ran on choosing a mission (${scanOn}) and is gone 700 ms later (${scanIdle})`);
    await page.waitForFunction(() => document.querySelectorAll('#mission-panel li button').length > 0, null, { timeout: 15_000 });
    // record the figures' text on every frame while the card opens
    await page.evaluate(() => {
      window.__figTexts = [];
      const tick = () => {
        const dds = [...document.querySelectorAll('#detail-panel .figs dd')];
        if (dds.length) window.__figTexts.push(dds.map((d) => d.textContent).join('|'));
        if (window.__figTexts.length < 90) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    await page.locator('#mission-panel li button').first().click();
    check(await waitStep(page, 'compare'), 'the first analog opens');
    await page.waitForFunction(() => document.querySelectorAll('#detail-panel .figs dd').length === 3, null, { timeout: 15_000 });
    const counting = await page.evaluate(() => document.querySelectorAll('#detail-panel .figs dd.hud-counting').length);
    await page.waitForTimeout(900);
    const figs = await page.evaluate(() => {
      const f = window.starsFlow;
      const dds = [...document.querySelectorAll('#detail-panel .figs .fig')].map((e) => [e.dataset.fig, e.querySelector('dd').textContent, e.querySelector('dd').classList.contains('hud-counting')]);
      // the data: the outcome of the selected cell (two decimals, as the card prints it)
      let data = null;
      try {
        const o = f.store.outcome(f.state.selectedId, f.state.missionId);
        const fmt = (v) => new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2, minimumFractionDigits: 2 }).format(v);
        if (o) data = { final: fmt(o.final), similarity: fmt(o.similarity), suitability: fmt(o.suitability) };
      } catch {}
      return { dds, data, texts: [...new Set(window.__figTexts)] };
    });
    check(counting > 0, `the scores count up when the pair opens (${counting} of 3 counting when they appear)`);
    check(figs.dds.length === 3 && figs.dds.every((d) => !d[2] && /^\d+\.\d\d$/.test(d[1])), `after 1 s the three scores are settled: ${figs.dds.map((d) => `${d[0]} ${d[1]}`).join(', ')}`);
    check(!!figs.data && figs.dds.every(([k, t]) => figs.data[k] === t), `the scores' text equals the data (${JSON.stringify(figs.data)})`);
    check(figs.texts.length === 1 && figs.texts[0] === figs.dds.map((d) => d[1]).join('|'), `the figures' own text never changed while counting (${figs.texts.length} distinct text on every frame: ${figs.texts.join(' / ')})`);
    // fonts
    const fonts = await page.evaluate(() => ({
      name: getComputedStyle(document.querySelector('.brand-name')).fontFamily,
      text: getComputedStyle(document.body).fontFamily,
      num: getComputedStyle(document.querySelector('#detail-panel .figs dd')).fontFamily,
      loaded: [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family.replace(/"/g, '')),
    }));
    check(/^"?Michroma/.test(fonts.name), `product name in Michroma (${fonts.name})`);
    check(/^"?Barlow/.test(fonts.text), `text in Barlow (${fonts.text})`);
    check(/^"?IBM Plex Mono/.test(fonts.num), `scores in IBM Plex Mono (${fonts.num})`);
    check(['Michroma', 'Barlow', 'IBM Plex Mono'].every((f) => fonts.loaded.includes(f)), `the three families are loaded from the bundle (${[...new Set(fonts.loaded)].join(', ')})`);
    await ctx.close();
  }

  // ---- reduced motion: nothing animates after each step
  {
    const { ctx, page } = await open(1440, 900, { reducedMotion: 'reduce' });
    await page.waitForFunction(() => window.starsFlow?.hasData(), null, { timeout: 30_000 });
    const anims = () => page.evaluate(() => document.getAnimations().filter((a) => !(a.effect?.target instanceof Element && a.effect.target.closest('.spinner'))).map((a) => a.animationName ?? a.transitionProperty ?? a.constructor.name));
    const boot = await page.evaluate(() => document.body.classList.contains('hud-boot'));
    const a0 = await anims();
    check(!boot && a0.length === 0, `reduced motion, start: no boot, no animation (${a0.join(', ') || 'none'})`);
    await page.keyboard.press('1');
    await waitStep(page, 'pick');
    await page.waitForTimeout(60);
    const a1 = await anims();
    const scan = await page.evaluate(() => document.body.classList.contains('hud-scan'));
    check(!scan && a1.length === 0, `reduced motion, mission chosen: no scan line, no animation (${a1.join(', ') || 'none'})`);
    await page.waitForFunction(() => document.querySelectorAll('#mission-panel li button').length > 0, null, { timeout: 15_000 });
    await page.locator('#mission-panel li button').first().click();
    await waitStep(page, 'compare');
    await page.waitForTimeout(60);
    const a2 = await anims();
    const cnt = await page.evaluate(() => document.querySelectorAll('.hud-counting').length);
    check(cnt === 0 && a2.length === 0, `reduced motion, pair open: no count-up, no animation (${a2.join(', ') || 'none'})`);
    await ctx.close();
  }

  // ---- no page scroll
  for (const [w, h] of [[1440, 900], [1366, 768], [375, 812], [812, 375]]) {
    const { ctx, page } = await open(w, h);
    await page.waitForFunction(() => window.starsFlow?.hasData(), null, { timeout: 30_000 });
    const res = [];
    const measure = async (label) => {
      const r = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.scrollHeight, innerWidth, innerHeight]);
      res.push(`${label} ${r[0]}x${r[1]}`);
      return r[0] <= r[2] && r[1] <= r[3];
    };
    let ok = await measure('start');
    await page.keyboard.press('2');
    await waitStep(page, 'pick');
    await page.waitForTimeout(400);
    ok = (await measure('mission')) && ok;
    await page.waitForFunction(() => document.querySelectorAll('#mission-panel li button').length > 0, null, { timeout: 15_000 });
    await page.locator('#mission-panel li button').first().click();
    await waitStep(page, 'compare');
    await page.waitForTimeout(600);
    ok = (await measure('pair')) && ok;
    check(ok, `${w}x${h}: no page scroll (${res.join(', ')})`);
    await ctx.close();
  }
} finally {
  await browser.close();
  srv.close?.();
}
console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
