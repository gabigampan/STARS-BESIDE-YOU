#!/usr/bin/env node
// Phone overlap check (builds nothing: run `npm run build` first). Serves dist/ as the other tests do
// and, at six phone sizes (and 1366x768), in each state (start; each mission with its sheet unfolded;
// one pair of each mission, then with "More details" open; the options sheet open; the audio guide on),
// collects the visible text-bearing elements (their own text's line boxes) of the header, options sheet, handle, panels and globe
// labels, and reports: boxes of two texts that intersect by more than 1 px both ways (neither contains
// the other), texts that stick out of their scroll container horizontally, and texts cut without an
// ellipsis. Exit code 1 when anything is found.
// Usage: node tests/overlap.mjs [--shots]     Screenshots of failing states: $SHOTS_DIR/overlap

import { existsSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { serve } from './lib/serve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(APP, 'dist');
const SHOTS = process.env.SHOTS_DIR ? join(process.env.SHOTS_DIR, 'overlap') : join(APP, 'tests', 'shots', 'overlap');
mkdirSync(SHOTS, { recursive: true });
if (!existsSync(join(DIST, 'index.html'))) {
  console.error('dist/ is missing: run `npm run build` first');
  process.exit(2);
}

// OVERLAP_SIZES="320x568,375x812" and OVERLAP_STATES="start,mission,pair,more,options,audio" narrow the run;
// OVERLAP_WAIT (ms, default 700) is the fixed pause per state (no tile is waited for).
const SIZES = process.env.OVERLAP_SIZES
  ? process.env.OVERLAP_SIZES.split(',').map((x) => x.trim().split('x').map(Number))
  : [[320, 568], [360, 640], [375, 812], [414, 896], [812, 375], [667, 375], [1366, 768]];
const STATES = new Set((process.env.OVERLAP_STATES ?? 'start,mission,pair,more,options,audio').split(',').map((x) => x.trim()));
const WAIT = Number(process.env.OVERLAP_WAIT ?? 700);
const srv = await serve(DIST);
const browser = await chromium.launch();

// runs in the page: the problems of the current state
function scan() {
  const SCOPE = '.topbar, #mf-sheet, #mf-handle, .panel, #intro, .pane, #guide-caption, #steps';
  const roots = [...document.querySelectorAll(SCOPE)];
  const vw = innerWidth, vh = innerHeight;
  const shown = (el) => {
    if (el.closest('[hidden], .sr-only, details:not([open]) > :not(summary)')) return false;
    for (let e = el; e; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false;
    }
    return true;
  };
  // the box clipped by every ancestor that clips its overflow, and by the viewport
  const clipped = (el) => {
    const r = el.getBoundingClientRect();
    let [l, t, rr, b] = [r.left, r.top, r.right, r.bottom];
    for (let e = el.parentElement; e; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.overflowX !== 'visible' || s.overflowY !== 'visible') {
        const c = e.getBoundingClientRect();
        l = Math.max(l, c.left); t = Math.max(t, c.top); rr = Math.min(rr, c.right); b = Math.min(b, c.bottom);
      }
    }
    l = Math.max(l, 0); t = Math.max(t, 0); rr = Math.min(rr, vw); b = Math.min(b, vh);
    return rr - l > 1 && b - t > 1 ? { l, t, r: rr, b } : null;
  };
  // covered when the element on top at the box's centre is neither it nor related to it (labels that
  // ignore the pointer are probed with the pointer turned on for a moment)
  const covered = (el, box) => {
    const x = (box.l + box.r) / 2, y = (box.t + box.b) / 2;
    const pe = el.style.pointerEvents;
    el.style.setProperty('pointer-events', 'auto', 'important');
    const top = document.elementFromPoint(x, y);
    el.style.pointerEvents = pe;
    return !!top && !(top === el || el.contains(top) || top.contains(el));
  };
  // the line boxes of the element's own text (an inline element over two lines is not a rectangle)
  const textRects = (el, box) => {
    const out = [];
    for (const n of el.childNodes) {
      if (n.nodeType !== 3 || !n.nodeValue.trim()) continue;
      const rg = document.createRange();
      rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) {
        const l = Math.max(r.left, box.l), t = Math.max(r.top, box.t), rr = Math.min(r.right, box.r), b = Math.min(r.bottom, box.b);
        if (rr - l > 1 && b - t > 1) out.push({ l, t, r: rr, b });
      }
    }
    return out;
  };
  const name = (el) => {
    const cls = typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).join('.') : '';
    return `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${cls} "${el.textContent.replace(/\s+/g, ' ').trim().slice(0, 40)}"`;
  };
  const seen = new Set();
  const items = [];
  for (const root of roots) {
    for (const el of [root, ...root.querySelectorAll('*')]) {
      if (seen.has(el)) continue;
      seen.add(el);
      if (el.matches('svg, svg *, script, style')) continue;
      const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.nodeValue.trim());
      if (!own) continue;
      if (!shown(el)) continue;
      const box = clipped(el);
      if (!box || covered(el, box)) continue;
      const rects = textRects(el, box);
      if (rects.length) items.push({ el, box, rects });
    }
  }
  const overlaps = [];
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      const a = items[i], b = items[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      let hit = null;
      for (const p of a.rects) for (const q of b.rects) {
        const w = Math.min(p.r, q.r) - Math.max(p.l, q.l);
        const hgt = Math.min(p.b, q.b) - Math.max(p.t, q.t);
        if (w > 1 && hgt > 1) hit = `${w.toFixed(0)}x${hgt.toFixed(0)}`;
      }
      if (hit) overlaps.push(`${name(a.el)}  x  ${name(b.el)}  (${hit})`);
    }
  }
  const outside = [];
  const cut = [];
  for (const { el } of items) {
    const r = el.getBoundingClientRect();
    for (let e = el.parentElement; e; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (['auto', 'scroll', 'hidden', 'clip'].includes(s.overflowX)) {
        const c = e.getBoundingClientRect();
        if (r.left < c.left - 1 || r.right > c.right + 1) outside.push(`${name(el)} in ${name(e).split(' ')[0]} (${r.left.toFixed(0)}..${r.right.toFixed(0)} vs ${c.left.toFixed(0)}..${c.right.toFixed(0)})`);
        break;
      }
    }
    if (r.right > vw + 1 || r.left < -1) outside.push(`${name(el)} outside the viewport (${r.left.toFixed(0)}..${r.right.toFixed(0)})`);
    const s = getComputedStyle(el);
    if (el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0 && s.textOverflow !== 'ellipsis' && s.overflowX !== 'visible')
      cut.push(`${name(el)} (${el.scrollWidth} > ${el.clientWidth})`);
  }
  return { n: items.length, overlaps, outside, cut };
}

const waitStep = (page, s) => page.waitForFunction((x) => window.starsFlow?.state.step === x, s, { timeout: 20_000 }).then(() => true, () => false);
const settle = (page) => page.waitForTimeout(WAIT);
const unfold = async (page) => {
  await page.evaluate(() => {
    if (document.body.classList.contains('mf-folded')) document.getElementById('mf-handle')?.click();
  });
  await settle(page);
};
const toStart = async (page) => {
  for (let i = 0; i < 4 && (await page.evaluate(() => window.starsFlow?.state.step)) !== 'choose'; i++) {
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
  }
};

const total = {};
let bad = 0;
for (const [w, hgt] of SIZES) {
  const key = `${w}x${hgt}`;
  total[key] = { overlaps: 0, outside: 0, cut: 0 };
  const ctx = await browser.newContext({ viewport: { width: w, height: hgt }, deviceScaleFactor: 1, hasTouch: w < 900, isMobile: false });
  const page = await ctx.newPage();
  await page.goto(srv.base, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.starsFlow?.hasData(), null, { timeout: 30_000 });
  await settle(page);
  const states = [];
  const record = async (label) => {
    const kind = label === 'start' ? 'start' : label.endsWith('more') ? 'more' : label.endsWith('pair') ? 'pair' : label.startsWith('mission') ? 'mission' : label.startsWith('options') ? 'options' : 'audio';
    if (!STATES.has(kind)) return;
    const r = await page.evaluate(scan);
    const n = r.overlaps.length + r.outside.length + r.cut.length;
    total[key].overlaps += r.overlaps.length;
    total[key].outside += r.outside.length;
    total[key].cut += r.cut.length;
    states.push(label);
    if (n) {
      bad += n;
      console.log(`FAIL ${key} ${label}: ${r.overlaps.length} overlaps, ${r.outside.length} outside, ${r.cut.length} cut (${r.n} texts)`);
      for (const x of [...r.overlaps, ...r.outside, ...r.cut]) console.log(`       ${x}`);
      await page.screenshot({ path: join(SHOTS, `${key}-${label.replace(/\W+/g, '-')}.png`) });
    } else console.log(`ok   ${key} ${label} (${r.n} texts)`);
  };

  await record('start');
  for (const m of ['1', '2', '3']) {
    await toStart(page);
    await page.keyboard.press(m);
    if (!(await waitStep(page, 'pick'))) {
      console.log(`FAIL ${key} mission ${m} did not open`);
      bad++;
      continue;
    }
    await page.waitForFunction(() => document.querySelectorAll('#mission-panel li button').length > 0, null, { timeout: 15_000 }).catch(() => undefined);
    await unfold(page);
    await record(`mission ${m}`);
    await page.locator('#mission-panel li button').first().click().catch(() => page.keyboard.press('1'));
    if (!(await waitStep(page, 'compare'))) {
      console.log(`FAIL ${key} mission ${m}: the pair did not open`);
      bad++;
      continue;
    }
    await settle(page);
    await unfold(page);
    await record(`mission ${m} pair`);
    await page.evaluate(() => {
      const d = document.querySelector('#detail-panel details.more-details');
      if (d) d.open = true;
    });
    await settle(page);
    await record(`mission ${m} pair more`);
  }
  await toStart(page);
  if (await page.evaluate(() => document.body.classList.contains('mf-phone'))) {
    await page.click('#mf-options');
    await settle(page);
    await record('options open');
    await page.click('#mf-options');
  }
  if (STATES.has('audio')) await page.evaluate(() => {
    const s = document.getElementById('switch-audio');
    if (s && s.getAttribute('aria-checked') !== 'true') s.click();
  });
  if (STATES.has('audio')) await page.waitForTimeout(1200);
  await record('audio guide on');
  await ctx.close();
}
console.log('\nper size:', JSON.stringify(total));
await browser.close();
await srv.close?.();
console.log(bad ? `\n${bad} problem(s)` : '\nno overlaps, nothing outside, nothing cut');
process.exit(bad ? 1 : 0);
