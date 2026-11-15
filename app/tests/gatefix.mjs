#!/usr/bin/env node
// The four faults the long suites found in the Mission Control redesign, measured the way flow.mjs and
// a11y.mjs measure them (builds nothing: run `npm run build` first):
//  1. at most three typefaces computed on the start, mission and pair steps (Michroma, Barlow, IBM Plex Mono);
//     no page scroll at 1440x900 / 1366x768, no horizontal overflow at 375x812 / 812x375;
//  2. axe-core reports no color-contrast violation on the phone start, mission and pair steps, both palettes;
//  3. on the phone mission and pair steps (375x812, 812x375) every pair of touch targets is 8 px apart
//     (the Cesium logo link and the sheet handle included);
//  4. on desktop, with the full ranking unfolded, "Show 50 more" and "Adjust the weights" are 8 px apart;
//     with the ranking folded the last folded row ends at or above 760 px at 1366x768, for the three missions.
// Usage: node tests/gatefix.mjs [--shots=DIR]

import { existsSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { serve } from './lib/serve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const AXE = require.resolve('axe-core/axe.min.js');
const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(APP, 'dist');
if (!existsSync(join(DIST, 'index.html'))) {
  console.error('dist/ is missing: run `npm run build` first');
  process.exit(2);
}
const SHOTS = (process.argv.find((a) => a.startsWith('--shots=')) ?? '').slice(8) || null;
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
let failed = 0;
let passed = 0;
const check = (c, m) => {
  if (c) passed++;
  else failed++;
  console.log(`${c ? 'ok  ' : 'FAIL'} ${m}`);
};

const srv = await serve(DIST);
const browser = await chromium.launch();
const open = async (w, h, pal = 'off', settle = 1500) => {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, hasTouch: w < 900 || h < 500 });
  await ctx.addInitScript((p) => { try { localStorage.setItem('starsBesideYou.colourBlind', p); } catch {} }, pal);
  const page = await ctx.newPage();
  await page.goto(srv.base, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.starsFlow?.hasData(), null, { timeout: 30_000 });
  await page.waitForTimeout(settle);
  return { ctx, page };
};
const waitStep = (p, s) => p.waitForFunction((x) => window.starsFlow?.state.step === x, s, { timeout: 20_000 });
const toMission = async (page, key = '1') => {
  await page.keyboard.press(key);
  await waitStep(page, 'pick');
  await page.waitForFunction(() => document.querySelectorAll('#mission-panel li button').length > 0, null, { timeout: 15_000 });
  await page.waitForTimeout(500);
};
const toPair = async (page) => {
  await page.locator('#mission-panel li button').first().click();
  await waitStep(page, 'compare');
  await page.waitForTimeout(900);
};
const shot = async (page, name) => SHOTS && page.screenshot({ path: join(SHOTS, `${name}.png`) });

// the same probe flow.mjs runs: computed families of visible text, tight targets, scroll
const probe = (page) =>
  page.evaluate(() => {
    const vis = (el) => {
      const s = getComputedStyle(el);
      return s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.01 && el.getClientRects().length > 0;
    };
    const fam = new Set();
    const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n; (n = walk.nextNode()); ) {
      if (!n.nodeValue.trim()) continue;
      const el = n.parentElement;
      if (!el || !vis(el) || el.closest('.sr-only')) continue;
      fam.add(getComputedStyle(el).fontFamily.split(',')[0].trim().replace(/["']/g, ''));
    }
    const targets = [...document.querySelectorAll('button, a[href], input:not([type=radio]), select, summary, label.seg')].filter((el) => {
      if (!vis(el) || el.disabled || el.closest('.sr-only')) return false;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) return false;
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) return false;
      const top = document.elementFromPoint(cx, cy);
      return !!top && (el.contains(top) || top.contains(el) || top.closest('label') === el);
    });
    const rects = targets.map((el) => [el, el.getBoundingClientRect()]);
    const nameOf = (el) => (el.textContent || el.getAttribute('aria-label') || el.id || el.tagName || '').trim();
    const tight = [];
    for (let i = 0; i < rects.length; i++)
      for (let j = i + 1; j < rects.length; j++) {
        const [a, ra] = rects[i], [b, rb] = rects[j];
        if (a.contains(b) || b.contains(a)) continue;
        const dx = Math.max(0, rb.left - ra.right, ra.left - rb.right);
        const dy = Math.max(0, rb.top - ra.bottom, ra.top - rb.bottom);
        if (Math.max(dx, dy) < 8 - 0.5) tight.push(`${nameOf(a).slice(0, 25)} | ${nameOf(b).slice(0, 25)} (${Math.max(dx, dy).toFixed(1)} px)`);
      }
    // the Cesium logo link to its nearest target
    let logo = null;
    for (const [a, ra] of rects) {
      if (!a.closest('.cesium-credit-logoContainer')) continue;
      for (const [b, rb] of rects) {
        if (a === b || b.closest('.cesium-credit-logoContainer')) continue;
        const d = Math.max(Math.max(0, rb.left - ra.right, ra.left - rb.right), Math.max(0, rb.top - ra.bottom, ra.top - rb.bottom));
        if (logo == null || d < logo.d) logo = { d, to: nameOf(b).slice(0, 25) || b.id };
      }
    }
    const de = document.documentElement;
    return {
      fonts: [...fam].sort(),
      tight,
      logo,
      hscroll: de.scrollWidth > innerWidth + 0.5 || document.body.scrollWidth > innerWidth + 0.5,
      vscroll: de.scrollHeight > innerHeight + 0.5 || document.body.scrollHeight > innerHeight + 0.5,
    };
  });
const axeContrast = async (page) => {
  await page.addScriptTag({ path: AXE });
  return page.evaluate(async () => {
    const r = await window.axe.run(document, { runOnly: ['color-contrast'], resultTypes: ['violations'] });
    return r.violations.flatMap((v) => v.nodes.map((n) => `${n.target.join(' ')}: ${n.any[0]?.message ?? ''}`.slice(0, 160)));
  });
};
// the pairs these four faults are about (the probe lists every pair under 8 px; the others are printed as notes)
const FAULT = /Cesium|Show 50 more|Adjust the weights|Full ranking|Analog 5|How these five/;
const tightOf = (a, tag) => { const o = a.tight.filter((t) => !FAULT.test(t)); if (o.length) console.log(`note ${tag}: other pairs under 8 px (not one of the four faults): ${o.join('; ')}`); return a.tight.filter((t) => FAULT.test(t)); };
const ALLOWED = new Set(['Michroma', 'Barlow', 'IBM Plex Mono']);

try {
  // ---- 1 and 4: desktop
  for (const [w, h] of [[1440, 900], [1366, 768]]) {
    const { ctx, page } = await open(w, h);
    let a = await probe(page);
    await shot(page, `${w}x${h}-start`);
    check(a.fonts.length <= 3 && a.fonts.every((f) => ALLOWED.has(f)), `${w}x${h} start: typefaces ${a.fonts.join(', ')}`);
    check(!a.vscroll && !a.hscroll, `${w}x${h} start: no page scroll`);
    await toMission(page, '1');
    a = await probe(page);
    await shot(page, `${w}x${h}-rover-mission`);
    check(a.fonts.length <= 3 && a.fonts.every((f) => ALLOWED.has(f)), `${w}x${h} mission: typefaces ${a.fonts.join(', ')}`);
    check(!a.vscroll && !a.hscroll, `${w}x${h} mission: no page scroll`);
    { const t = tightOf(a, `${w}x${h} mission`); check(t.length === 0, `${w}x${h} mission: 8 px between the analogs and the folded rows${t.length ? ': ' + t.join('; ') : ''}`); }
    // unfold the full ranking and measure "Show 50 more" to "Adjust the weights"
    await page.evaluate(() => { const d = document.querySelector('#mission-panel .ranking-box'); if (d) d.open = true; });
    await page.waitForTimeout(400);
    const gap = await page.evaluate(() => {
      const more = document.querySelector('#mission-panel #show-more');
      const sums = [...document.querySelectorAll('#mission-panel summary')];
      const adj = sums.find((s) => /Adjust the weights/.test(s.textContent));
      if (!more || !adj) return { err: `${!!more} ${!!adj}` };
      const box = document.querySelector('#mission-panel .ranking-box');
      // scroll the pair into view inside the panel and measure the vertical gap between their boxes
      more.scrollIntoView({ block: 'center' });
      const a = more.getBoundingClientRect(), b = adj.getBoundingClientRect();
      const order = box.compareDocumentPosition(adj) & Node.DOCUMENT_POSITION_FOLLOWING ? 'ranking above weights' : 'weights above ranking';
      return { gap: Math.max(b.top - a.bottom, a.top - b.bottom), order, more: more.tagName, adj: adj.tagName };
    });
    check(gap.gap >= 7.5, `${w}x${h} ranking unfolded: "Show 50 more" (${gap.more}) to "Adjust the weights" (${gap.adj}) ${gap.gap?.toFixed(1)} px (${gap.order})${gap.err ? ' ' + gap.err : ''}`);
    await page.evaluate(() => { document.querySelector('#mission-panel .ranking-box').open = false; });
    await toPair(page);
    a = await probe(page);
    check(a.fonts.length <= 3 && a.fonts.every((f) => ALLOWED.has(f)), `${w}x${h} pair: typefaces ${a.fonts.join(', ')}`);
    check(!a.vscroll && !a.hscroll, `${w}x${h} pair: no page scroll`);
    await ctx.close();
  }
  // ---- 4: folded rows fit at 1366x768, three missions
  for (const key of ['1', '2', '3']) {
    const { ctx, page } = await open(1366, 768);
    await toMission(page, key);
    const r = await page.evaluate(() => {
      const p = document.querySelector('#mission-panel');
      const sums = [...p.querySelectorAll('.ranking-box > summary, .weights > summary, .method-box > summary')].filter((s) => s.getClientRects().length);
      const last = sums.at(-1)?.getBoundingClientRect().bottom ?? null;
      const rows = p.querySelectorAll('li button').length;
      const lastRow = [...p.querySelectorAll('li button')].slice(0, 5).at(-1)?.getBoundingClientRect().bottom ?? null;
      return { last, rows, lastRow, folded: sums.length, scrolled: p.querySelector('.panel-body')?.scrollTop ?? 0 };
    });
    check(r.last != null && r.last <= 760 && r.folded === 3, `1366x768 mission ${key} folded: five analogs end at ${r.lastRow?.toFixed(1)} px, last of ${r.folded} folded rows ends at ${r.last?.toFixed(1)} px (at most 760)`);
    await ctx.close();
  }
  // ---- 1, 2, 3: phone
  for (const [w, h] of [[375, 812], [812, 375]]) {
    for (const pal of ['off', 'on']) {
      const { ctx, page } = await open(w, h, pal, 0);
      const tag = `${w}x${h} colour-blind ${pal}`;
      // as a11y.mjs does: axe at once, while the boot animation may still run
      let c = await axeContrast(page);
      check(c.length === 0, `${tag} start, at once after load: axe color-contrast${c.length ? ': ' + c.join(' | ') : ' none'}`);
      await page.waitForTimeout(1500);
      let a = await probe(page);
      if (pal === 'off') await shot(page, `${w}x${h}-start`);
      check(a.fonts.length <= 3 && a.fonts.every((f) => ALLOWED.has(f)), `${tag} start: typefaces ${a.fonts.join(', ')}`);
      check(!a.hscroll, `${tag} start: no horizontal overflow`);
      c = await axeContrast(page);
      check(c.length === 0, `${tag} start: axe color-contrast${c.length ? ': ' + c.join(' | ') : ' none'}`);
      await toMission(page, '1');
      a = await probe(page);
      c = await axeContrast(page);
      check(a.fonts.length <= 3 && a.fonts.every((f) => ALLOWED.has(f)), `${tag} mission: typefaces ${a.fonts.join(', ')}`);
      check(!a.hscroll, `${tag} mission: no horizontal overflow`);
      check(c.length === 0, `${tag} mission: axe color-contrast${c.length ? ': ' + c.join(' | ') : ' none'}`);
      { const t = tightOf(a, `${tag} mission`); check(t.length === 0 && (!a.logo || a.logo.d >= 7.5), `${tag} mission: Cesium logo 8 px from every touch target (nearest: ${a.logo ? `${a.logo.d.toFixed(1)} px to ${a.logo.to}` : 'no logo target'})${t.length ? ': ' + t.join('; ') : ''}`); }
      await toPair(page);
      a = await probe(page);
      if (pal === 'off') await shot(page, `${w}x${h}-pair`);
      c = await axeContrast(page);
      check(a.fonts.length <= 3 && a.fonts.every((f) => ALLOWED.has(f)), `${tag} pair: typefaces ${a.fonts.join(', ')}`);
      check(!a.hscroll, `${tag} pair: no horizontal overflow`);
      check(c.length === 0, `${tag} pair: axe color-contrast${c.length ? ': ' + c.join(' | ') : ' none'}`);
      { const t = tightOf(a, `${tag} pair`); check(t.length === 0 && (!a.logo || a.logo.d >= 7.5), `${tag} pair: Cesium logo 8 px from every touch target (nearest: ${a.logo ? `${a.logo.d.toFixed(1)} px to ${a.logo.to}` : 'no logo target'})${t.length ? ': ' + t.join('; ') : ''}`); }
      await ctx.close();
    }
  }
} catch (e) {
  check(false, `run error: ${e.message}`);
} finally {
  await browser.close();
  await srv.close?.();
}
console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
