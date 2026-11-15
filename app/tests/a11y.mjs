#!/usr/bin/env node
// Accessibility layer test (npm run test:a11y): the keyboard guide, the audio guide and both
// switches, the colour-blind palette, and axe-core on every screen in both palettes.
//
// No audio file is created by this test. The logic checks replace the media element's load, play
// and pause with an instrumented stand-in injected before the app starts (it records every request,
// reports itself as playing until paused or ended, and can be told to fail); one check plays a real
// track of public/audio with the browser's own player. Missing files are simulated by answering 404.
//
// Runs on the shipped bundle and on the no-twin fixture (tests/lib/fixtures.mjs), at 1440x900 and
// 375x812. Usage: npm run build && npm run test:a11y

import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import * as FX from './lib/fixtures.mjs';
import { serve } from './lib/serve.mjs';
import { PALETTES } from '../src/a11y/palette.ts';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const culori = require('culori');
const AXE = require.resolve('axe-core/axe.min.js');

const APP = FX.APP;
const DIST = join(APP, 'dist');
const AUDIO = join(APP, 'public/audio');
const SHOTS = join(FX.SHOTS_DIR, 'a11y');
mkdirSync(SHOTS, { recursive: true });
const T = 240_000;

const failures = [];
const notes = [];
const ok = (m) => console.log(`ok   ${m}`);
const fail = (m) => {
  failures.push(m);
  console.log(`FAIL ${m}`);
};
const check = (c, m) => (c ? ok(m) : fail(m));
const note = (m) => {
  notes.push(m);
  console.log(`note ${m}`);
};

// ---------------------------------------------------------------- files (no browser)

const tracks = JSON.parse(readFileSync(join(AUDIO, 'tracks.json'), 'utf8'));
const transcripts = JSON.parse(readFileSync(join(AUDIO, 'transcripts.json'), 'utf8'));
const top5 = JSON.parse(readFileSync(join(APP, '../docs/AUDIO_TOP5.json'), 'utf8'));
const sums = Object.fromEntries(
  readFileSync(join(AUDIO, 'SHA256SUMS.txt'), 'utf8')
    .split('\n')
    .filter(Boolean)
    .map((l) => {
      const m = /^([0-9a-f]{64})\s+\*?(.+)$/.exec(l.trim());
      return m ? [m[2].replace(/^.*\//, ''), m[1]] : [l, ''];
    }),
);
{
  const files = tracks.tracks.map((t) => t.file);
  check(files.length === 19 && new Set(files).size === 19, `tracks.json lists 19 distinct tracks (${files.length})`);
  const expected = ['00_welcome.mp3', 'm1_rover.mp3', 'm2_solar.mp3', 'm3_base.mp3', ...['rover', 'solar', 'base'].flatMap((p) => [1, 2, 3, 4, 5].map((n) => `${p}_${n}.mp3`))];
  check(expected.every((f) => files.includes(f)), 'tracks.json names exactly the 19 delivered files');
  check(files.every((f) => existsSync(join(AUDIO, f))), 'every file named in tracks.json exists in public/audio');
  check(files.every((f) => typeof transcripts[f] === 'string' && transcripts[f].length > 20), 'every track has its caption in transcripts.json');
  const bad = files.filter((f) => createHash('sha256').update(readFileSync(join(AUDIO, f))).digest('hex') !== sums[f]);
  check(bad.length === 0, `the 19 MP3 files match SHA256SUMS.txt${bad.length ? ` (differ: ${bad.join(', ')})` : ''}`);
  check(!tracks.tracks.some((t) => 'caption' in t || 'text' in t), 'tracks.json holds no caption text (transcripts.json is the only source)');
  const pref = { rover: 'rover', solar: 'solar', lunar_base: 'base' };
  let agree = true;
  for (const [m, v] of Object.entries(top5.missions)) {
    v.pairs.forEach((p, i) => {
      // entry n of the file (in order) is track <mission>_n; its "rank" field is the place in the full ranking
      const t = tracks.tracks.find((x) => x.step === 'pair' && x.mission === m && x.rank === i + 1);
      if (!t || t.file !== `${pref[m]}_${i + 1}.mp3` || t.earth_cell_id !== p.earth_cell_id || t.moon_cell_id !== p.moon_cell_id) agree = false;
    });
  }
  check(agree, 'tracks.json pair tracks agree with docs/AUDIO_TOP5.json (entry n of each mission = track <mission>_n, same cell ids)');
}

// ---------------------------------------------------------------- colours (no browser)

const contrast = (a, b) => culori.wcagContrast(a, b);
const BG = ['#000000', '#0d0f13'];
const sims = {
  protanopia: culori.filterDeficiencyProt(1),
  deuteranopia: culori.filterDeficiencyDeuter(1),
  tritanopia: culori.filterDeficiencyTrit(1),
};
const dE = culori.differenceCiede2000();
const DE_MIN = 10; // CIEDE2000 distance two colours that must be told apart keep under every simulation
const rgbHex = (c) => culori.formatHex({ mode: 'rgb', r: c[0] / 255, g: c[1] / 255, b: c[2] / 255 });
const colourReport = {};
for (const [name, p] of Object.entries(PALETTES)) {
  const css = p.css;
  const texts = [
    ['text', css['--text']],
    ['dim text', css['--text-dim']],
    ['accent', css['--sodium']],
    ['danger', css['--danger']],
  ];
  const rows = [];
  for (const [label, c] of texts) for (const bg of BG) rows.push([`${label} on ${bg}`, contrast(c, bg)]);
  rows.push(['text on accent button', contrast(css['--on-accent'], css['--sodium'])]);
  rows.push(['text on accent hover', contrast(css['--on-accent'], css['--accent-hover'])]);
  const worst = rows.reduce((a, b) => (b[1] < a[1] ? b : a));
  check(worst[1] >= 4.5, `${name} palette: text contrast at least 4.5:1 (lowest ${worst[1].toFixed(2)}:1, ${worst[0]})`);
  // colours that must be told apart: states, ramp ends, overlays against each other
  const pairs = [
    ['accent vs danger', css['--sodium'], css['--danger']],
    ['ramp low vs high', rgbHex(p.markerLow), rgbHex(p.markerHigh)],
    ['selection ring vs ramp high', rgbHex(p.ring), rgbHex(p.markerHigh)],
    ['zone outline vs beam', rgbHex(p.zoneLine), rgbHex(p.beam)],
    ['switch on vs switch off', css['--switch-on'], css['--text-dim']],
  ];
  const res = [];
  for (const [label, a, b] of pairs) {
    const per = Object.fromEntries(Object.entries(sims).map(([k, f]) => [k, dE(f(a), f(b))]));
    per.normal = dE(a, b);
    res.push({ label, ...per });
  }
  colourReport[name] = { contrast: rows, distinct: res };
  const minOf = (r) => Math.min(r.normal, r.protanopia, r.deuteranopia, r.tritanopia);
  const lowest = res.reduce((a, b) => (minOf(b) < minOf(a) ? b : a));
  const line = res.map((r) => `${r.label}: ${minOf(r).toFixed(1)}`).join('; ');
  if (name === 'cvd') check(minOf(lowest) >= DE_MIN, `cvd palette: every pair stays apart by CIEDE2000 >= ${DE_MIN} under protanopia, deuteranopia and tritanopia (${line})`);
  else note(`standard palette, lowest CIEDE2000 under the three simulations: ${line} (the standard palette relies on text and icons; the colour-blind mode is the safe one)`);
}

// ---------------------------------------------------------------- browser

// The instrumented media stand-in (injected before the app starts).
const STAND_IN = () => {
  const st = new WeakMap();
  const S = (el) => {
    let s = st.get(el);
    if (!s) st.set(el, (s = { paused: true, t: 0, ended: false }));
    return s;
  };
  const all = new Set();
  const M = (window.__media = { log: [], fail: false, block: false, maxPlaying: 0, all });
  const count = () => [...all].filter((e) => !S(e).paused).length;
  const proto = HTMLMediaElement.prototype;
  Object.defineProperty(proto, 'paused', { configurable: true, get() { return S(this).paused; } });
  Object.defineProperty(proto, 'ended', { configurable: true, get() { return S(this).ended; } });
  Object.defineProperty(proto, 'currentTime', {
    configurable: true,
    get() { return S(this).t; },
    set(v) { S(this).t = v; if (v === 0) M.log.push({ op: 'reset', src: this.getAttribute('src') }); },
  });
  proto.load = function () { const s = S(this); s.paused = true; s.t = 0; M.log.push({ op: 'load', src: this.getAttribute('src') }); };
  proto.pause = function () { const s = S(this); if (!s.paused) { s.paused = true; this.dispatchEvent(new Event('pause')); } M.log.push({ op: 'pause', src: this.getAttribute('src') }); };
  proto.play = function () {
    all.add(this);
    M.log.push({ op: 'play', src: this.getAttribute('src') });
    if (M.fail) return Promise.reject(new DOMException('stand-in failure', 'NotSupportedError'));
    if (M.block) return Promise.reject(new DOMException('stand-in refusal', 'NotAllowedError'));
    const s = S(this);
    s.paused = false;
    s.ended = false;
    M.maxPlaying = Math.max(M.maxPlaying, count());
    this.dispatchEvent(new Event('playing'));
    return Promise.resolve();
  };
  M.endCurrent = () => { for (const e of all) if (!S(e).paused) { S(e).paused = true; S(e).ended = true; e.dispatchEvent(new Event('ended')); } };
  M.sample = () => { M.maxPlaying = Math.max(M.maxPlaying, count()); return count(); };
  setInterval(M.sample, 4);
};

async function openPage(browser, base, { size, storage = null, standIn = true, block = [], init = null, touch = false, keepPending = false } = {}) {
  const ctx = await browser.newContext({ viewport: size, deviceScaleFactor: 1, hasTouch: touch, isMobile: touch });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    const t = m.text();
    if (/Failed to load resource|net::ERR|404/.test(t)) return; // the browser's own network line, not the app
    errors.push(t);
  });
  const audioRequests = [];
  page.on('request', (r) => {
    if (/\/audio\/[^/]+\.mp3/.test(r.url())) audioRequests.push(r.url());
  });
  // the logic checks run with no track awaiting a new recording (the pending block sets its own list)
  if (!keepPending) await page.route('**/audio/pending.json', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"pending_rerecord": []}' }));
  for (const b of block) await page.route(b, (r) => r.fulfill({ status: 404, body: 'not found' }));
  if (storage) await page.addInitScript((s) => { for (const [k, v] of Object.entries(s)) localStorage.setItem(k, v); }, storage);
  if (standIn) await page.addInitScript(STAND_IN);
  if (init) await page.addInitScript(init);
  await page.goto(base, { timeout: T });
  await page.waitForFunction(() => window.starsFlow?.hasData() && window.starsA11y, null, { timeout: T });
  await page.evaluate(() => window.starsA11y.guide.ready);
  return { page, ctx, errors, audioRequests };
}

const step = (page) => page.evaluate(() => window.starsFlow.state.step);
const waitStep = (page, s) => page.waitForFunction((x) => window.starsFlow.state.step === x && !window.starsFlow.loading(), s, { timeout: T });
const press = async (page, key) => {
  await page.keyboard.press(key);
  await page.waitForTimeout(60);
};
const focusIsHeading = (page) =>
  page.waitForFunction(() => /^H[1-3]$/.test(document.activeElement?.tagName ?? ''), null, { timeout: 60000 }).then(() => true, () => false);
const media = (page) => page.evaluate(() => ({ log: window.__media.log.slice(), max: window.__media.maxPlaying, now: window.__media.sample() }));
const plays = (log) => log.filter((e) => e.op === 'play').map((e) => (e.src ?? '').replace(/^.*\//, ''));
const guide = (page) =>
  page.evaluate(() => {
    const c = document.getElementById('guide-caption');
    return { state: c.dataset.state, source: c.dataset.source, words: c.querySelector('.caption-state')?.textContent, text: c.querySelector('.caption-text')?.textContent, file: window.starsA11y.guide.current()?.track?.file ?? null };
  });

async function axeScreen(page, label) {
  await page.addScriptTag({ path: AXE });
  const r = await page.evaluate(async () => {
    // the globes are WebGL canvases with their own credit lines; the rest of the page is checked
    const res = await window.axe.run(document, { resultTypes: ['violations'] });
    return res.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.slice(0, 3).map((n) => n.target.join(' ')).join(' | ')}`);
  });
  check(r.length === 0, `axe-core: no violations on ${label}${r.length ? `: ${r.join('; ')}` : ''}`);
}

async function switchChecks(page, label) {
  const s = await page.evaluate(() =>
    [...document.querySelectorAll('[role="switch"]')].map((el) => {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      // distance to the nearest other interactive control in the header
      const others = [...document.querySelectorAll('header button, header input, header a, header [role="switch"]')].filter((o) => o !== el && !el.contains(o) && o.getClientRects().length && getComputedStyle(o).visibility !== 'hidden');
      let gap = Infinity;
      for (const o of others) {
        const q = o.getBoundingClientRect();
        if (q.width === 0 || q.height === 0) continue;
        if (o.closest('label')?.querySelector('input') === o) continue;
        const dx = Math.max(0, Math.max(q.left - r.right, r.left - q.right));
        const dy = Math.max(0, Math.max(q.top - r.bottom, r.top - q.bottom));
        gap = Math.min(gap, Math.hypot(dx, dy));
      }
      return {
        name: document.getElementById(el.getAttribute('aria-labelledby') ?? '')?.textContent ?? el.getAttribute('aria-label'),
        checked: el.getAttribute('aria-checked'),
        words: el.querySelector('.switch-state')?.textContent,
        w: r.width,
        h: r.height,
        gap,
        visible: r.width > 0 && r.top >= 0 && r.bottom <= window.innerHeight && r.left >= 0 && r.right <= window.innerWidth && cs.visibility !== 'hidden' && cs.display !== 'none',
        inHeader: !!el.closest('header'),
      };
    }),
  );
  const names = s.map((x) => x.name).join(', ');
  check(s.length === 2 && s[0].name === 'Audio guide' && s[1].name === 'Colour-blind mode', `${label}: exactly two switches, "Audio guide" and "Colour-blind mode" (${names})`);
  check(s.every((x) => x.visible && x.inHeader), `${label}: both switches visible in the header`);
  check(s.every((x) => x.w >= 44 && x.h >= 44), `${label}: both switches at least 44 x 44 px (${s.map((x) => `${x.w.toFixed(0)}x${x.h.toFixed(0)}`).join(', ')})`);
  check(s.every((x) => x.gap >= 8), `${label}: 8 px or more to the neighbouring controls (${s.map((x) => x.gap.toFixed(1)).join(', ')} px)`);
  check(s.every((x) => (x.checked === 'true' ? x.words === 'On' : x.words === 'Off')), `${label}: state in words beside each switch matches aria-checked`);
  const sc = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  check(sc[0] <= sc[1], `${label}: no horizontal scroll (${sc[0]} <= ${sc[1]} px)`);
  const cap = await page.evaluate(() => { const c = document.getElementById('guide-caption'); const r = c.getBoundingClientRect(); const b = c.querySelector('.caption-repeat').getBoundingClientRect(); return r.height > 0 && r.bottom <= window.innerHeight && b.width >= 44 && b.height >= 44 && b.right <= window.innerWidth; });
  check(cap, `${label}: the caption with its Repeat control (44 px or more) fits on screen`);
  return s;
}

async function run(browser, base, variant, size, full) {
  const tag = `${variant} ${size.width}x${size.height}`;
  console.log(`\n# ${tag}`);
  const twins = variant === 'shipped';

  // ---- defaults, switches on every screen, Tab + Space, persistence
  {
    const { page, ctx, errors, audioRequests } = await openPage(browser, base, { size });
    let s = await switchChecks(page, `${tag} start screen`);
    check(s.every((x) => x.checked === 'false'), `${tag}: both switches off by default with empty storage`);
    // Tab to the audio switch, Space toggles it, Enter toggles it back
    await page.evaluate(() => document.body.focus());
    let found = false;
    for (let i = 0; i < 60 && !found; i++) {
      await page.keyboard.press('Tab');
      found = await page.evaluate(() => document.activeElement?.id === 'switch-audio');
    }
    check(found, `${tag}: the Audio guide switch is reached with Tab`);
    const ring = await page.evaluate(() => { const cs = getComputedStyle(document.activeElement); return cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2; });
    check(ring, `${tag}: keyboard focus on the switch is visible (outline of 2 px or more)`);
    await page.keyboard.press('Space');
    const a1 = await page.evaluate(() => document.getElementById('switch-audio').getAttribute('aria-checked'));
    await page.keyboard.press('Enter');
    const a2 = await page.evaluate(() => document.getElementById('switch-audio').getAttribute('aria-checked'));
    check(a1 === 'true' && a2 === 'false', `${tag}: Space turns the Audio guide on, Enter turns it off (aria-checked ${a1}, then ${a2})`);
    await page.keyboard.press('Tab');
    const onPal = await page.evaluate(() => document.activeElement?.id === 'switch-palette');
    await page.keyboard.press('Space');
    const p1 = await page.evaluate(() => [document.getElementById('switch-palette').getAttribute('aria-checked'), document.documentElement.dataset.palette, getComputedStyle(document.documentElement).getPropertyValue('--sodium').trim()]);
    check(onPal && p1[0] === 'true' && p1[1] === 'cvd' && p1[2].toUpperCase() === PALETTES.cvd.css['--sodium'], `${tag}: Tab reaches Colour-blind mode; Space switches the whole palette at once (${p1.join(', ')})`);
    // both on, reload: remembered
    await page.evaluate(() => document.querySelector('#switch-audio').click());
    await page.reload({ timeout: T });
    await page.waitForFunction(() => window.starsFlow?.hasData() && window.starsA11y, null, { timeout: T });
    const after = await page.evaluate(() => [document.getElementById('switch-audio').getAttribute('aria-checked'), document.getElementById('switch-palette').getAttribute('aria-checked'), document.documentElement.dataset.palette]);
    check(after[0] === 'true' && after[1] === 'true' && after[2] === 'cvd', `${tag}: both switches remembered across a reload (${after.join(', ')})`);
    // every screen
    await page.evaluate(() => window.starsA11y.audioSwitch.set(false));
    await press(page, '1');
    await waitStep(page, 'pick');
    await switchChecks(page, `${tag} mission screen`);
    await press(page, '1');
    await waitStep(page, 'compare');
    await page.waitForTimeout(300);
    await switchChecks(page, `${tag} pair screen`);
    check(errors.length === 0, `${tag}: no page error${errors.length ? `: ${errors.slice(0, 3).join(' | ')}` : ''}`);
    check(audioRequests.length === 0, `${tag}: with the Audio guide off no audio file was requested (${audioRequests.length})`);
    await ctx.close();
  }

  // ---- storage blocked: the page still works, switches default off
  if (full) {
    const ctx = await browser.newContext({ viewport: size });
    const page = await ctx.newPage();
    await page.addInitScript(() => {
      Object.defineProperty(window, 'localStorage', { configurable: true, get() { throw new DOMException('blocked', 'SecurityError'); } });
    });
    const errs = [];
    page.on('pageerror', (e) => errs.push(String(e)));
    await page.goto(base, { timeout: T });
    await page.waitForFunction(() => window.starsFlow?.hasData() && window.starsA11y, null, { timeout: T });
    await page.evaluate(() => document.querySelector('#switch-palette').click());
    const r = await page.evaluate(() => [document.getElementById('switch-palette').getAttribute('aria-checked'), document.documentElement.dataset.palette]);
    check(errs.length === 0 && r[0] === 'true' && r[1] === 'cvd', `${tag}: without localStorage the switches still work (${r.join(', ')}; ${errs.length} errors)`);
    await ctx.close();
  }

  // ---- keyboard: 1-3, 1-5, Escape at each step, focus to headings, live region, modifiers, search field
  {
    const { page, ctx } = await openPage(browser, base, { size });
    const offered = await page.evaluate(() => window.starsFlow.store.offeredMissions().map((m) => m.id));
    const hints = await page.evaluate(() => [...document.querySelectorAll('#intro .choice')].map((b) => b.querySelector('.choice-key')?.textContent ?? ''));
    check(hints.length === offered.length && hints.every((t, i) => t.includes(`Press ${i + 1}`)), `${tag}: each mission choice shows its key ("Press 1" ...) (${hints.join(' / ')})`);
    for (let i = 0; i < offered.length; i++) {
      await press(page, String(i + 1));
      await waitStep(page, 'pick');
      const mid = await page.evaluate(() => window.starsFlow.state.missionId);
      const live = await page.waitForFunction(() => document.getElementById('flow-status').textContent.length > 10, null, { timeout: 10000 }).then(() => true, () => false);
      const fh = await focusIsHeading(page);
      const fwhere = await page.evaluate(() => `${document.activeElement?.tagName}.${document.activeElement?.className}`);
      check(mid === offered[i] && fh && live, `${tag}: key ${i + 1} opens ${offered[i]} (${mid}); focus on the step heading (${fwhere}); the live region announces it (${live})`);
      const top = await page.evaluate(() => [...document.querySelectorAll('.top5-btn')].map((b) => ({ rank: Number(b.dataset.rank), overall: Number(b.dataset.overall), id: Number(b.dataset.id), text: b.innerText, w: b.getBoundingClientRect().width, h: b.getBoundingClientRect().height })));
      // the bundle's five (missions.json top5.ids, revision 7), else ranks 1 to 5
      const spec = await page.evaluate((m) => { const ms = window.starsFlow.store.mission(m); return { ids: ms.top5?.ids ?? window.starsFlow.store.ranked(m).filter((p) => p.rank != null && p.rank <= 5).sort((a, b) => a.rank - b.rank).map((p) => p.id), rule: ms.top5?.rule ?? null }; }, mid);
      check(top.length === 5 && top.every((b, k) => b.rank === k + 1 && b.id === spec.ids[k]), `${tag} ${mid}: five numbered buttons, the bundle's five in its order (${spec.ids.join(', ')})`);
      check(top.every((b) => (b.overall !== b.rank ? b.text.includes(`Number ${b.overall} in the full list`) : !/in the full list/.test(b.text))), `${tag} ${mid}: a button whose pair ranks elsewhere in the full list says "Number N in the full list"`);
      if (spec.rule) check(await page.evaluate((r) => [...document.querySelectorAll('.top5 [data-text="top5.rule"]')].some((e) => e.textContent === r), spec.rule), `${tag} ${mid}: the rule of the five is shown under them, verbatim`);
      const notesOk = await page.evaluate((m) => {
        const st = window.starsFlow.store;
        // each note is shown where the bundle says (its text verbatim, file and column names left out)
        const top = st.notesFor('top5', m).every((n) => document.querySelector(`.top5 .bundle-note[data-text="${n.key}"]`));
        const card = st.notesFor('mission_card', m).every((n) => document.querySelector(`#mission-panel .card-notes .bundle-note[data-text="${n.key}"]`));
        return top && card;
      }, mid);
      check(notesOk, `${tag} ${mid}: every bundle note marked for the five and the mission card is shown there, verbatim`);
      check(top.every((b) => b.h >= 44 && /Final score/.test(b.text)), `${tag} ${mid}: each top-five button is at least 44 px high and shows the final score`);
      if (twins) check(top.every((b) => /Lunar twin/.test(b.text)), `${tag} ${mid}: each top-five button names its lunar twin`);
      // the team lead's ruling: never "the best" about the five
      const bestWords = await page.evaluate(() => (document.body.innerText.match(/five best|the best (?:five|analogs?|sites|places|pairs)/gi) ?? []).length + [...document.querySelectorAll('[aria-label]')].filter((e) => /five best|the best (?:five|analogs?|sites|places|pairs)/i.test(e.getAttribute('aria-label'))).length);
      check(bestWords === 0, `${tag} ${mid}: no "five best" or "the best" anywhere on the mission screen (${bestWords})`);
      const head5 = await page.evaluate(() => document.getElementById('top5-title')?.textContent ?? '');
      check(/^Five of the /.test(head5) && !/best/i.test(head5), `${tag} ${mid}: the five's heading says what the bundle says ("${head5}")`);
      const firstInPanel = await page.evaluate(() => { const s = document.querySelector('#mission-panel .panel-sec'); return s?.classList.contains('top5'); });
      check(firstInPanel, `${tag} ${mid}: the five best analogs are the first section of the mission panel`);
      const k = (i % 5) + 1;
      await press(page, String(k));
      await waitStep(page, 'compare');
      const sel = await page.evaluate(() => window.starsFlow.state.selectedId);
      check(sel === top[k - 1].id && (await focusIsHeading(page)), `${tag} ${mid}: key ${k} opens analog ${k}; focus on its heading`);
      await press(page, 'Escape');
      await waitStep(page, 'pick');
      const back = await page.waitForFunction((id) => document.activeElement?.closest?.(`.rank-row[data-id="${id}"]`) || /^H[1-3]$/.test(document.activeElement?.tagName ?? ''), top[k - 1].id, { timeout: 60000 }).then(() => true, () => false);
      check((await step(page)) === 'pick' && back, `${tag} ${mid}: Escape goes back from the pair to the mission; focus returns to the pair's row in the list`);
      await press(page, 'Escape');
      await waitStep(page, 'choose');
      check((await focusIsHeading(page)), `${tag} ${mid}: Escape goes back from the mission to the start; focus on its heading`);
    }
    // a modifier never fires a shortcut
    await page.keyboard.press('Control+1');
    await page.keyboard.press('Alt+2');
    await page.waitForTimeout(200);
    check((await step(page)) === 'choose', `${tag}: Ctrl+1 and Alt+2 do nothing`);
    // inside the search field the keys type
    await press(page, '1');
    await waitStep(page, 'pick');
    await page.focus('#rank-search');
    await page.keyboard.type('23');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(200);
    const typed = await page.evaluate(() => [document.getElementById('rank-search')?.value ?? null, window.starsFlow.state.step]);
    check(typed[1] === 'pick' && typed[0] !== null, `${tag}: keys typed in the search field do not fire shortcuts (step ${typed[1]})`);
    // a slider keeps its keys
    const sl = await page.$('#mission-panel input[type="range"]');
    if (sl) {
      await page.evaluate(() => { const d = document.querySelector('#mission-panel details.weights'); if (d) d.open = true; });
      await sl.focus();
      await page.keyboard.press('3');
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);
      check((await step(page)) === 'pick', `${tag}: keys on a slider do not fire shortcuts`);
    }
    // Escape closes a dialog first
    await page.evaluate(() => document.body.focus());
    await page.evaluate(() => document.querySelector('#keys-button').click());
    const listed = await page.evaluate(() => document.getElementById('keys-dialog').open && /Escape|Esc/.test(document.getElementById('keys-body').innerText));
    await page.keyboard.press('Escape');
    await page.waitForTimeout(150);
    const r = await page.evaluate(() => [document.getElementById('keys-dialog').open, window.starsFlow.state.step]);
    check(listed && r[0] === false && r[1] === 'pick', `${tag}: the shortcuts list opens from the header; Escape closes it first and stays on the step`);
    // no rule identifier anywhere in Data and limits (only the bundle's plain-English descriptions)
    await page.evaluate(() => document.getElementById('credits-button').click());
    const ids = await page.evaluate(() => (document.getElementById('credits-body').innerText.match(/\b(repo_global_mean|zone_twin|real_value_tolerance|percentile_and_real_tolerance|per_mission)\b/g) ?? []));
    check(ids.length === 0, `${tag}: Data and limits shows no rule identifier (${ids.join(', ') || 'none'})`);
    await page.keyboard.press('Escape');
    await page.screenshot({ path: join(SHOTS, `${variant}-${size.width}-mission.png`) });
    await ctx.close();
  }

  // ---- audio guide with the stand-in: the track of each step, one at a time, R repeats
  {
    const { page, ctx, errors } = await openPage(browser, base, { size, storage: { 'starsBesideYou.audioGuide': 'on' } });
    await page.waitForFunction(() => window.__media.log.some((e) => e.op === 'play'), null, { timeout: 10000 }).catch(() => undefined);
    let m = await media(page);
    check(plays(m.log)[0] === '00_welcome.mp3', `${tag}: guide on: the welcome track starts on the start screen (${plays(m.log).join(', ') || 'none'})`);
    let g = await guide(page);
    check(g.text === transcripts['00_welcome.mp3'] && g.words === 'Playing', `${tag}: the caption shows the welcome transcript exactly, state "Playing"`);
    // which missions have their five recordings matching the bundle's five (introduction offered only then)
    const matchInfo = await page.evaluate(async () => {
      const f = window.starsFlow;
      const out = [];
      const ms = f.store.offeredMissions();
      for (let i = 0; i < ms.length; i++) {
        await f.store.loadMission(ms[i].id);
        await f.store.loadTwins().catch(() => undefined);
        out.push({ key: i + 1, id: ms[i].id, match: f.recordedFiveMatch(ms[i]) });
      }
      return out;
    });
    note(`${tag}: recordings matching the bundle's five: ${matchInfo.map((x) => `${x.id} ${x.match ? 'yes' : 'no'}`).join(', ')}`);
    const introFile = (id) => tracks.tracks.find((t) => t.step === 'mission' && t.mission === id)?.file;
    const mm = matchInfo.find((x) => x.match);
    const nomatch = matchInfo.find((x) => !x.match);
    if (nomatch) {
      await press(page, String(nomatch.key));
      await waitStep(page, 'pick');
      const gg = await guide(page);
      check(gg.file === null && gg.source === 'screen' && !plays((await media(page)).log).includes(introFile(nomatch.id)), `${tag}: ${nomatch.id}: its recordings do not match the bundle's five, so no introduction plays; the caption is built from the screen`);
      await press(page, 'Escape');
      await waitStep(page, 'choose');
    }
    if (mm) {
      await press(page, String(mm.key));
      await waitStep(page, 'pick');
      m = await media(page);
      const lastPlays = plays(m.log);
      check(lastPlays[lastPlays.length - 1] === introFile(mm.id), `${tag}: choosing ${mm.id} starts its introduction (${lastPlays.slice(-1)})`);
      const idx = m.log.findLastIndex((e) => e.op === 'play');
      const before = m.log.slice(0, idx);
      const lastWelcome = before.findLastIndex((e) => e.op === 'play');
      const between = before.slice(lastWelcome + 1).map((e) => e.op);
      check(between.includes('pause') && between.includes('reset'), `${tag}: starting a track pauses and resets the previous one first (${between.join(' ')})`);
      const pairFile = tracks.tracks.find((t) => t.step === 'pair' && t.mission === mm.id && t.rank === 1)?.file;
      await page.keyboard.press('1');
      // at once: the introduction stops and the pair's track starts, before the panel has its data
      await page.waitForTimeout(300);
      const quick = await page.evaluate(() => ({ title: window.starsA11y.guide.current()?.title, last: window.__media.log.filter((e) => e.op === 'play').map((e) => (e.src ?? '').replace(/^.*\//, '')).pop() }));
      check(quick.title === 'Analog 1' && quick.last === pairFile, `${tag}: within 300 ms of key 1 the guide is on analog 1 and its track has started (${quick.title}, ${quick.last})`);
      await waitStep(page, 'compare');
      g = await guide(page);
      check(g.file === pairFile && g.text === transcripts[pairFile], `${tag}: analog 1 plays the track recorded for that pair, with its transcript (${g.file})`);
      const n0 = plays((await media(page)).log).filter((f) => f === pairFile).length;
      await press(page, 'r');
      const n1 = plays((await media(page)).log).filter((f) => f === pairFile).length;
      check(n1 === n0 + 1, `${tag}: R repeats the current track from the start`);
      // a mission video opened while a track plays: the guide falls silent, keeps its caption, and does
      // not restart by itself (not while the video is open, not after it closes) until R
      {
        const audioNow = () => page.evaluate(() => [...document.querySelectorAll('audio')].filter((a) => !a.paused).length);
        const before = await audioNow();
        const viaButton = await page.evaluate(() => { const b = document.getElementById('start-mission'); if (b) b.click(); return !!b; });
        if (!viaButton) await page.evaluate(() => { void window.starsBesideYou.video.openVideo({ title: 'test video', sources: [{ src: 'media/none.mp4', type: '' }] }); });
        await page.waitForFunction(() => window.starsBesideYou.video.isOpen(), null, { timeout: 5000 }).catch(() => undefined);
        const open = await page.evaluate(() => window.starsBesideYou.video.isOpen());
        const during = await audioNow();
        const gv = await guide(page);
        await page.waitForTimeout(1000);
        const later = await audioNow();
        check(before === 1 && open && during === 0 && later === 0, `${tag}: with the guide on and a track playing (${before}), opening the mission video (${viaButton ? 'Start the mission' : 'video API'}) leaves zero playing audio elements (${during} at once, ${later} after 1 s)`);
        check(gv.file === pairFile && gv.text === transcripts[pairFile] && gv.words === 'Paused', `${tag}: the guide's caption stays visible under the video, state "${gv.words}"`);
        await page.evaluate(() => window.starsBesideYou.video.closeVideo());
        await page.waitForTimeout(500);
        const closed = await audioNow();
        const n2 = plays((await media(page)).log).filter((f) => f === pairFile).length;
        check(closed === 0 && n2 === n1, `${tag}: after the video closes the guide stays silent until R (${closed} playing, ${n2 - n1} new starts)`);
        await press(page, 'r');
        const n3 = plays((await media(page)).log).filter((f) => f === pairFile).length;
        check(n3 === n2 + 1 && (await audioNow()) === 1, `${tag}: after the video, R plays the track again from the start`);
      }
      await page.evaluate(() => window.__media.endCurrent());
      await page.waitForTimeout(50);
      check((await guide(page)).words === 'Finished', `${tag}: at the end of a track the caption says "Finished"`);
      // the whole caption is shown while the guide is on (unfolded, reachable)
      const cap = await page.evaluate(() => { const c = document.getElementById('guide-caption'); const t = c.querySelector('.caption-text'); const cs = getComputedStyle(t); return { exp: c.dataset.expanded, fits: t.scrollHeight <= t.clientHeight + 1 || (cs.overflowY === 'auto' && t.tabIndex === 0), btn: c.querySelector('.caption-more')?.getAttribute('aria-expanded') }; });
      check(cap.exp === 'true' && cap.fits && cap.btn === 'true', `${tag}: with the guide on, the whole caption is shown (unfolded; a long one scrolls in a focusable box)`);
      // a pair that is not the recorded one plays nothing and shows a caption from the screen
      const sixth = await page.evaluate(() => window.starsFlow.ranking().find((r) => r.rank === 6)?.id);
      const c0 = plays((await media(page)).log).length;
      await page.evaluate((id) => window.starsFlow.select(id), sixth);
      await page.waitForFunction(() => window.starsA11y.guide.current()?.title === 'Rank 6', null, { timeout: 60000 }).catch(() => undefined);
      g = await guide(page);
      const c1 = plays((await media(page)).log).length;
      check(c1 === c0 && g.file === null && g.source === 'screen' && /Rank 6/.test(g.text ?? ''), `${tag}: a pair without a recording plays nothing; its caption is built from the data on screen`);
      await press(page, 'Escape');
      await waitStep(page, 'pick');
    }
    // rapid key presses: never two tracks at once
    await page.evaluate(() => (window.__media.maxPlaying = 0));
    const seq = twins ? ['Escape', '2', '3', 'Escape', '1', '2', 'Escape', 'Escape', '3', '1', 'r', 'Escape', 'Escape', '2', 'r', 'r'] : ['Escape', '2', 'Escape', '3', 'r', 'Escape', '1', 'r'];
    for (const k of seq) await page.keyboard.press(k);
    await page.waitForTimeout(1500);
    m = await media(page);
    check(m.max <= 1, `${tag}: during rapid key presses at most one track was playing at any moment (max ${m.max})`);
    // switch off: everything stops at once
    await page.evaluate(() => document.querySelector('#switch-audio').click());
    m = await media(page);
    check(m.now === 0 && (await guide(page)).state === 'text-only', `${tag}: switching the guide off stops the sound at once; caption "Text only"`);
    // a failing track: caption with the text-only wording, no error on screen (on a step that has a track)
    await page.evaluate(() => window.starsFlow.changeMission());
    await waitStep(page, 'choose');
    await page.evaluate(() => (window.__media.fail = true));
    await page.evaluate(() => document.querySelector('#switch-audio').click());
    await page.waitForTimeout(200);
    g = await guide(page);
    const alerts = await page.evaluate(() => document.querySelectorAll('[role="alert"]').length);
    check(g.words === 'Audio not available: text shown' && (g.text ?? '').length > 20 && alerts === 0, `${tag}: a track that fails to play shows "${g.words}" with its caption and no error on screen`);
    // the browser refuses to start sound: "Press R to play"
    await page.evaluate(() => { window.__media.fail = false; window.__media.block = true; });
    await press(page, 'r');
    g = await guide(page);
    check(g.words === 'Press R to play', `${tag}: when the browser refuses to start sound, the caption says "Press R to play" (${g.words})`);
    check(errors.length === 0, `${tag}: no application error in the console${errors.length ? `: ${errors.slice(0, 3).join(' | ')}` : ''}`);
    await ctx.close();
  }

  // ---- pending.json: a track awaiting a new recording is text only, no request
  if (full) {
    const { page, ctx, errors } = await openPage(browser, base, { size, storage: { 'starsBesideYou.audioGuide': 'on' } });
    const intro = tracks.tracks.find((t) => t.step === 'mission' && t.mission === 'lunar_base')?.file;
    await page.route('**/audio/pending.json', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ pending_rerecord: [intro], note: 'test' }) }));
    await page.reload({ timeout: T });
    await page.waitForFunction(() => window.starsFlow?.hasData() && window.starsA11y, null, { timeout: T });
    await page.evaluate(() => window.starsA11y.guide.ready);
    const k = await page.evaluate(() => window.starsFlow.store.offeredMissions().findIndex((m) => m.id === 'lunar_base') + 1);
    await press(page, String(k));
    await waitStep(page, 'pick');
    await press(page, 'r');
    const g = await guide(page);
    const asked = plays((await media(page)).log).includes(intro);
    check(g.words === 'Text only: new recording pending' && g.text === transcripts[intro] && !asked, `${tag}: a track listed in pending.json shows its caption, "${g.words}", and is never requested (even with R)`);
    check(errors.length === 0, `${tag}: no error with pending.json`);
    await ctx.close();
  }

  // ---- first screen and header layout
  {
    const { page, ctx } = await openPage(browser, base, { size });
    await page.evaluate(() => (document.getElementById('loading').hidden = true));
    const r = await page.evaluate(() => ({ choices: [...document.querySelectorAll('#intro .choice')].map((c) => c.getBoundingClientRect().bottom), h: window.innerHeight, header: document.querySelector('header').getBoundingClientRect().height }));
    if (size.width >= 900) check(r.choices.length > 0 && r.choices.every((b) => b <= r.h), `${tag}: the purpose and all mission choices are in the first screen without scrolling (lowest ${Math.round(Math.max(...r.choices))} of ${r.h} px)`);
    if (size.width >= 1280) check(r.header < 100, `${tag}: the header stays on one row (${Math.round(r.header)} px)`);
    // the caption is unfolded by default (never clipped); "Show less" folds it and "Full text" unfolds it again
    const st0 = await page.evaluate(() => { const c = document.getElementById('guide-caption'); const t = c.querySelector('.caption-text'); return [c.dataset.expanded, t.scrollHeight <= t.clientHeight + 1]; });
    const landscape = size.height < 500 && size.width > size.height;
    if (!landscape) check(st0[0] === 'true' && st0[1], `${tag}: the caption shows its whole text by default`);
    await page.evaluate(() => document.querySelector('#guide-caption .caption-more').click());
    const st1 = await page.evaluate(() => [document.getElementById('guide-caption').dataset.expanded, document.querySelector('#guide-caption .caption-more').textContent]);
    await page.evaluate(() => document.querySelector('#guide-caption .caption-more').click());
    const st2 = await page.evaluate(() => { const c = document.getElementById('guide-caption'); const t = c.querySelector('.caption-text'); return [c.dataset.expanded, t.scrollHeight <= t.clientHeight + 1]; });
    check(st1[0] !== st2[0] && (st2[0] === 'true' ? st2[1] : st1[0] === 'true'), `${tag}: the caption control folds and unfolds it, and unfolded it shows the whole text`);
    await ctx.close();
  }

  // ---- files unavailable: 404 on the MP3 files (real player), and separately on transcripts.json
  if (full) {
    const { page, ctx, errors } = await openPage(browser, base, { size, standIn: false, storage: { 'starsBesideYou.audioGuide': 'on' }, block: ['**/audio/*.mp3'] });
    const kb = await page.evaluate(() => window.starsFlow.store.offeredMissions().findIndex((m) => m.id === 'lunar_base') + 1);
    await press(page, String(kb));
    await waitStep(page, 'pick');
    await page.waitForFunction(() => ['unavailable', 'press-r'].includes(document.getElementById('guide-caption').dataset.state), null, { timeout: 20000 }).catch(() => undefined);
    const g = await guide(page);
    const visibleError = await page.evaluate(() => [...document.querySelectorAll('[role="alert"], .alert')].filter((e) => e.getClientRects().length).length);
    check(g.words === 'Audio not available: text shown' && g.text === transcripts['m3_base.mp3'] && visibleError === 0, `${tag}: with the MP3 files missing (404) the caption shows the transcript and "${g.words}", no error on screen`);
    check(errors.length === 0, `${tag}: missing MP3 files leave no application error in the console${errors.length ? `: ${errors.join(' | ')}` : ''}`);
    await ctx.close();
  }
  if (full) {
    const { page, ctx, errors } = await openPage(browser, base, { size, storage: { 'starsBesideYou.audioGuide': 'on' }, block: ['**/audio/transcripts.json'] });
    await press(page, '1');
    await waitStep(page, 'pick');
    const g = await guide(page);
    const name = await page.evaluate(() => document.querySelector('#mission-panel .panel-title')?.textContent ?? '');
    check(g.source === 'screen' && (g.text ?? '').includes(name.replace(/ mission$/, '')) && (g.text ?? '').length > 40, `${tag}: without transcripts.json the caption is built from the data on screen`);
    check(errors.length === 0, `${tag}: no application error without transcripts.json`);
    await ctx.close();
  }

  // ---- one real track through the browser's own player
  if (full && twins) {
    const ctx = await browser.newContext({ viewport: size });
    const page = await ctx.newPage();
    await page.addInitScript(() => localStorage.setItem('starsBesideYou.audioGuide', 'on'));
    await page.route('**/audio/pending.json', (r) => r.fulfill({ status: 200, contentType: 'application/json', body: '{"pending_rerecord": []}' }));
    await page.goto(base, { timeout: T });
    await page.waitForFunction(() => window.starsFlow?.hasData() && window.starsA11y, null, { timeout: T });
    const kr = await page.evaluate(() => window.starsFlow.store.offeredMissions().findIndex((m) => m.id === 'lunar_base') + 1);
    await page.keyboard.press(String(kr));
    const playing = await page
      .waitForFunction(() => { const a = document.getElementById('guide-audio'); return a && !a.paused && a.currentTime > 0.2 && a.duration > 20; }, null, { timeout: 30000 })
      .then(() => true, () => false);
    const info = await page.evaluate(() => { const a = document.getElementById('guide-audio'); return { src: a.currentSrc.replace(/^.*\//, ''), duration: a.duration, state: document.getElementById('guide-caption').dataset.state }; });
    check(playing, `${tag}: a real track loads and plays in the browser (${info.src}, ${Number.isFinite(info.duration) ? info.duration.toFixed(1) : '?'} s, caption ${info.state})`);
    await ctx.close();
  }

  // ---- reviewer findings: Lunar base meaning text, percentile differences as printed, singular counts
  if (full && twins) {
    const { page, ctx } = await openPage(browser, base, { size });
    await page.evaluate(() => window.starsFlow.chooseMission('lunar_base'));
    await waitStep(page, 'pick');
    const want = await page.evaluate(() => window.starsFlow.store.similarity.texts?.similarity_meaning_lunar_base?.text ?? null);
    const ids = await page.evaluate(() => window.starsFlow.ranking().filter((r) => r.final != null).slice(0, 25).map((r) => r.id));
    let badMeaning = 0, badDiff = 0, rows = 0;
    for (const id of ids) {
      await page.evaluate((x) => window.starsFlow.select(x), id);
      await page.waitForFunction((x) => document.getElementById('detail-panel').dataset.cell === String(x) && document.querySelector('#detail-panel .pair-var'), id, { timeout: 60000 });
      const r = await page.evaluate(() => ({
        meanings: [...document.querySelectorAll('#detail-panel [data-note="meaning"]')].map((e) => e.textContent.trim()),
        lunar: document.querySelector('#detail-panel .lunar')?.textContent ?? '',
        pct: [...document.querySelectorAll('#detail-panel .pair-var')].map((v) => ['earth', 'moon', 'diff'].map((k) => v.querySelector(`[data-k="${k}"] dd`)?.textContent ?? '')).filter((x) => x[0].includes('percentile')),
      }));
      if (!r.meanings.length || r.meanings.some((t) => t !== want) || /real values are closest/.test(r.lunar)) badMeaning++;
      for (const [e, m, d] of r.pct) {
        rows++;
        const n = (t) => Math.round(parseFloat(t) * 10);
        if (Math.abs(n(e) - n(m)) !== n(d)) badDiff++;
      }
    }
    check(want && badMeaning === 0, `${tag}: every Lunar base pair shows the bundle's Lunar base meaning of similarity and no other rule's wording in its twin section (${badMeaning} of ${ids.length} differ)`);
    check(rows > 0 && badDiff === 0, `${tag}: Lunar base percentile differences agree with the two printed positions (${rows} rows, ${badDiff} differ)`);
    const one = await page.evaluate(() => { const m = window.starsFlow.store.offeredMissions()[0].id; return window.starsFlow.store.twinSharingText(m, 1); });
    check(!one || (/\b1 Earth point\b/.test(one) && !/\b1 Earth points\b/.test(one)), `${tag}: a twin shared by one point says "1 Earth point" (${one})`);
    await ctx.close();
  }

  // ---- phones: the team lead's five acceptance items, measured in every step
  if (size.width < 900) {
    const { page, ctx } = await openPage(browser, base, { size });
    await page.evaluate(() => (document.getElementById('loading').hidden = true));
    const portrait = size.height > size.width;
    const measure = () => page.evaluate(() => {
      const g = (id) => { const r = document.getElementById(id).getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; };
      const centreFree = (id) => { const cv = document.querySelector(`#${id} canvas`); if (!cv) return false; const r = cv.getBoundingClientRect(); const e = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2); return e === cv; };
      const t = document.querySelector('#guide-caption .caption-text');
      return { earth: g('earth-pane'), moon: g('moon-pane'), freeE: centreFree('earth-globe'), freeM: centreFree('moon-globe'), capClip: t.scrollHeight > t.clientHeight + 1 || getComputedStyle(document.getElementById('guide-caption')).overflow === 'hidden' && document.getElementById('guide-caption').scrollHeight > document.getElementById('guide-caption').clientHeight + 1, expanded: document.getElementById('guide-caption').dataset.expanded };
    });
    // start screen: at least the first mission card fully visible
    const first = await page.evaluate(() => { const c = document.querySelector('#intro .choice'); const r = c.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.bottom), window.innerHeight]; });
    check(first[1] <= first[2], `${tag}: the first mission card is visible on the first screen (bottom ${first[1]} of ${first[2]} px)`);
    let mm0 = await measure();
    check(!mm0.capClip || mm0.expanded === 'false', `${tag} start: the caption is not clipped${mm0.expanded === 'false' ? ' (folded by choice, "Full text" control)' : ''}`);
    for (const [key, st] of [['1', 'pick'], ['1', 'compare']]) {
      await press(page, key);
      await waitStep(page, st);
      await page.waitForTimeout(800);
      const m = await measure();
      check(m.earth.h >= 120 && m.moon.h >= 120, `${tag} ${st}: neither globe has zero height (Earth ${Math.round(m.earth.w)}x${Math.round(m.earth.h)}, Moon ${Math.round(m.moon.w)}x${Math.round(m.moon.h)} px)`);
      if (portrait) check(m.moon.y >= m.earth.y + m.earth.h - 2 && Math.abs(m.moon.x - m.earth.x) < 2, `${tag} ${st}: Earth above, Moon below`);
      check(m.freeE && m.freeM, `${tag} ${st}: nothing (credits, captions) covers the centre of either globe`);
      check(!m.capClip, `${tag} ${st}: the caption is not clipped`);
    }
    await page.screenshot({ path: join(SHOTS, `${variant}-${size.width}x${size.height}-phone-pair.png`) });
    await ctx.close();
  }

  // ---- touch: two-finger pinch changes the camera distance, one-finger drag changes the heading
  if (size.width < 900 && twins) {
    const { page, ctx } = await openPage(browser, base, { size, touch: true });
    await press(page, '1');
    await waitStep(page, 'pick');
    // the camera flight to the best places disables input until it ends (Cesium), so wait for it
    await page.waitForFunction(() => window.starsBesideYou.scene('earth').screenSpaceCameraController.enableInputs, null, { timeout: 120000 }).catch(() => undefined);
    await page.evaluate(() => (document.getElementById('loading').hidden = true));
    await page.waitForTimeout(500);
    // a point of the Earth canvas that nothing covers (the panel sits over part of it on a phone)
    const box = await page.evaluate(() => {
      const cv = document.querySelector('#earth-globe canvas');
      const r = cv.getBoundingClientRect();
      for (let fy = 0.5; fy > 0.1; fy -= 0.05) for (let fx = 0.5; fx > 0.15; fx -= 0.05) {
        const x = r.left + r.width * fx, y = r.top + r.height * fy;
        if (document.elementFromPoint(x, y) === cv && document.elementFromPoint(x - 45, y) === cv && document.elementFromPoint(x + 45, y) === cv) return { x, y, w: Math.min(120, r.width / 3), h: r.height };
      }
      return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: 120, h: r.height, covered: true };
    });
    const cam = () => page.evaluate(() => { const c = window.starsBesideYou.viewer('earth').camera; return { h: c.heading, d: window.Cesium ? 0 : 0, height: c.positionCartographic.height, lon: c.positionCartographic.longitude }; });
    const cdp = await ctx.newCDPSession(page);
    const touch = (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map(([x, y], i) => ({ x, y, id: i })) });
    const c0 = await cam();
    const steps = 12;
    await touch('touchStart', [[box.x - 15, box.y], [box.x + 15, box.y]]);
    for (let i = 1; i <= steps; i++) await touch('touchMove', [[box.x - 15 - i * 3, box.y], [box.x + 15 + i * 3, box.y]]);
    await touch('touchEnd', []);
    await page.waitForTimeout(1500);
    const c1 = await cam();
    check(Math.abs(c1.height - c0.height) / c0.height > 0.02, `${tag}: a two-finger pinch on the Earth globe changes the camera distance (${(c0.height / 1000).toFixed(0)} km to ${(c1.height / 1000).toFixed(0)} km)`);
    await touch('touchStart', [[box.x - box.w * 0.25, box.y]]);
    for (let i = 1; i <= steps; i++) await touch('touchMove', [[box.x - box.w * 0.25 + i * (box.w * 0.04), box.y + i * 2]]);
    await touch('touchEnd', []);
    await page.waitForTimeout(1500);
    const c2 = await cam();
    check(Math.abs(c2.lon - c1.lon) > 0.01 || Math.abs(c2.h - c1.h) > 0.01, `${tag}: a one-finger drag on the Earth globe rotates it (longitude ${(c1.lon * 57.3).toFixed(1)}° to ${(c2.lon * 57.3).toFixed(1)}°)`);
    await ctx.close();
  }

  // ---- axe-core on every screen, both palettes
  for (const pal of ['off', 'on']) {
    const { page, ctx } = await openPage(browser, base, { size, storage: { 'starsBesideYou.colourBlind': pal } });
    const label = `${tag}, colour-blind mode ${pal}`;
    await axeScreen(page, `the start screen (${label})`);
    await press(page, '2');
    await waitStep(page, 'pick');
    await page.waitForTimeout(300);
    await axeScreen(page, `the mission screen (${label})`);
    await press(page, '1');
    await waitStep(page, 'compare');
    await page.waitForTimeout(500);
    await axeScreen(page, `the pair screen (${label})`);
    await page.evaluate(() => document.querySelector('#keys-button').click());
    await axeScreen(page, `the shortcuts dialog (${label})`);
    await page.keyboard.press('Escape');
    if (full) {
      await page.evaluate(() => document.querySelector('#credits-button').click());
      await page.waitForTimeout(300);
      await axeScreen(page, `the Data and limits dialog (${label})`);
      await page.keyboard.press('Escape');
    }
    await page.screenshot({ path: join(SHOTS, `${variant}-${size.width}-pair-cvd-${pal}.png`) });
    await ctx.close();
  }
}

const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
const variants = [['shipped', null]];
if (existsSync(join(FX.NO_TWIN_BUNDLE, 'manifest.json'))) variants.push(['no-twin', FX.NO_TWIN_BUNDLE]);
else note(`no-twin fixture not found at ${FX.NO_TWIN_BUNDLE}: build it (tests/lib/fixtures.mjs) to run that variant`);
const sizes = (process.env.A11Y_SIZES ?? '1440x900,375x812,812x375').split(',').map((x) => { const [width, height] = x.split('x').map(Number); return { width, height }; });
const only = process.env.A11Y_ONLY ?? '';
for (const [variant, dir] of variants) {
  if (only && !only.includes(variant)) continue;
  const srv = await serve(DIST, { dataDir: dir });
  for (const size of sizes) {
    try {
      await run(browser, srv.base, variant, size, variant === 'shipped' && size.width === 1440);
    } catch (e) {
      fail(`${variant} ${size.width}: the run stopped: ${e instanceof Error ? e.message.split('\n')[0] : e}`);
    }
  }
  await srv.close();
}
// the other widths of the brief: switches, caption, no horizontal scroll, on every screen
if (!only || only.includes('widths')) {
  const srv = await serve(DIST, {});
  for (const size of [{ width: 768, height: 1024 }, { width: 3840, height: 2160 }]) {
    const tag = `widths ${size.width}x${size.height}`;
    try {
      const { page, ctx } = await openPage(browser, srv.base, { size });
      await switchChecks(page, `${tag} start screen`);
      await page.screenshot({ path: join(SHOTS, `start-${size.width}.png`), timeout: 180000 });
      await press(page, '1');
      await waitStep(page, 'pick');
      await switchChecks(page, `${tag} mission screen`);
      await page.screenshot({ path: join(SHOTS, `mission-${size.width}.png`), timeout: 180000 });
      await press(page, '1');
      await waitStep(page, 'compare');
      await focusIsHeading(page);
      await switchChecks(page, `${tag} pair screen`);
      await page.screenshot({ path: join(SHOTS, `pair-${size.width}.png`), timeout: 180000 });
      await ctx.close();
    } catch (e) {
      fail(`${tag}: the run stopped: ${e instanceof Error ? e.message.split('\n')[0] : e}`);
    }
  }
  await srv.close();
}
await browser.close();
console.log('\ncolour report:', JSON.stringify(colourReport, (k, v) => (typeof v === 'number' ? Math.round(v * 100) / 100 : v)));
console.log(`\n${failures.length ? `${failures.length} FAILED` : 'all passed'}${notes.length ? `; ${notes.length} notes` : ''}`);
process.exit(failures.length ? 1 : 0);
