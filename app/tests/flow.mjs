#!/usr/bin/env node
// Product flow test (checklist docs/UX_CHECKLIST.md, measured): build, serve dist/, and run the key
// task in headless Chromium against BOTH bundle variants (the shipped zone_twin bundle in
// public/data/v2 and a temporary copy of the no-twin repo_global_mean bundle served at /data/v2/)
// at 1440x900 and 375x812: choose each mission, check the counts against the bundle, pick the top
// point by mouse (marker on the globe) and by keyboard (list), check every number of the comparison
// panel against the bundle for a top, a middle and an eliminated cell per mission, move a weight
// slider and compare the new order with a recompute written here from the contract formulas, reset,
// open the video where one exists, go back at every step. Every view is audited for text size,
// typefaces, contrast, target sizes and spacing, horizontal scroll, one primary action and the red
// alerts. Console errors fail the run. Then forced failures (missing data file, missing detail tile,
// blocked imagery host) and the layouts at 768 and 3840 px.
// Contract revision 5 and later: each mission follows its own rule, read from the bundle. For a
// real-value mission the list shows the pairs, then a divider and the points without a twin; the
// panel of a pair shows every similarity variable (both values, difference, tolerance with who set
// it, within or not, weight, score) and the per-pair sentences; the panel of a point without a twin
// shows the no-twin sentence, no similarity, no final, no beam. With zone data (revision 6, or the
// zone fixture: --only=zones) the Moon shows the mission's zone and the "Why this zone?" panel opens
// by mouse, by keyboard and from a tap on a lunar cell outside the zone. Every view's text is scanned
// for technical strings (underscores inside words, "inf", bracketed ranges, Spanish class names).
// Usage: node tests/flow.mjs [--no-build] [--only=twin|notwin|zones] [--sizes=desktop,phone] [--skip-extra] [--extras-only]
// Screenshots: $SHOTS_DIR (default below).

import * as FX from './lib/fixtures.mjs';
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DataStore } from '../src/data/store.ts';
import { classWord, noPairKindWords, plainText, setByWords, staleForRule } from '../src/flow/copy.ts';
import { serve } from './lib/serve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(APP, 'dist');
const SHOTS = join(FX.SHOTS_DIR, 'flow');
const OTHER = FX.NO_TWIN_BUNDLE;
const arg = (k) => process.argv.find((a) => a.startsWith(`--${k}=`))?.slice(k.length + 3);
const ONLY = arg('only');
const SIZES = (arg('sizes') ?? 'desktop,phone').split(',');
const RED = /\bundefined\b|\bNaN\b|\bnull\b|lorem ipsum|title here|\basdf\b|error \d{3}|\[object object\]/i;
const ZONES = FX.ZONE_FIXTURE;

const failures = [];
const ok = (m) => console.log(`ok   ${m}`);
const fail = (m) => {
  failures.push(m);
  console.log(`FAIL ${m}`);
};
const check = (c, m) => (c ? ok(m) : fail(m));
const report = {};

// ---------- build ----------
if (!process.argv.includes('--no-build')) {
  const r = spawnSync('npm', ['run', 'build'], { cwd: APP, env: { ...process.env, VITE_USE_ION: '' }, encoding: 'utf8' });
  if (r.status !== 0) {
    console.log(r.stdout, r.stderr);
    process.exit(1);
  }
  ok('production build');
}
mkdirSync(SHOTS, { recursive: true });

// ---------- expectations, read from the bundles in Node ----------
const fileFetcher = (dir) => async (url) => {
  try {
    const buf = await readFile(join(dir, url.replace(/^.*\//, '')));
    return { ok: true, status: 200, json: async () => JSON.parse(buf.toString('utf8')), arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) };
  } catch {
    return { ok: false, status: 404, json: async () => null, arrayBuffer: async () => new ArrayBuffer(0) };
  }
};
async function expectations(dir) {
  const store = new DataStore('data/v2/', fileFetcher(dir));
  await store.loadStart();
  await Promise.all([store.loadAllTiles(), store.loadTwins(), store.loadPlaceDetail(), ...store.missionsJson.offered_missions.map((m) => store.loadMission(m))]);
  const explain = JSON.parse(readFileSync(join(dir, 'explain.json'), 'utf8'));
  return { store, explain };
}
const media = JSON.parse(readFileSync(join(DIST, 'media-index.json'), 'utf8')).videos;
const MEDIA_FOLDER = { rover: 'rover', solar: 'solar', lunar_base: 'lunar-base' };

// Python's round(x, 2) on the exact binary value: half-even only on an exact tie (e.g. 96.625).
function round2HalfEven(x) {
  const s = Math.abs(x).toFixed(40);
  const dot = s.indexOf('.');
  const rest = s.slice(dot + 3);
  if (/^50*$/.test(rest)) {
    const cents = Math.round(Math.abs(x) * 100 - 0.5);
    return (Math.sign(x) * (cents % 2 === 0 ? cents : cents + 1)) / 100;
  }
  return Number(x.toFixed(2));
}

// The recompute of the contract ("Recompute formulas (browser)"), written again here on purpose.
function independentOrder(store, missionId, weights, alpha, simWeights) {
  const mat = store.matrix(missionId);
  const md = store.missionDataOf(missionId);
  const defs = store.pairVariables(missionId);
  const rows = [];
  for (let p = 0; p < mat.ids.length; p++) {
    let num = 0, den = 0;
    for (let v = 0; v < weights.length; v++) {
      const u = mat.utilities[v][p];
      if (Number.isNaN(u)) continue;
      num += weights[v] * u;
      den += weights[v];
    }
    let sim = mat.similarity[p];
    if (defs.length) {
      // real values: 100 * sum ws s / sum ws over the scores of the pair (the twin is fixed)
      sim = NaN;
      if (md.twin[p] !== -2147483648) {
        let sn = 0, sd = 0;
        defs.forEach((d, v) => {
          const q = md.table.cols[d.score_column][p];
          if (q === -2147483648) return;
          sn += (simWeights?.[v] ?? d.weight) * (q / 1e6);
          sd += simWeights?.[v] ?? d.weight;
        });
        if (sd > 0) sim = (100 * sn) / sd;
      }
    }
    if (!den || Number.isNaN(sim)) continue;
    const f = alpha * sim + (1 - alpha) * ((100 * num) / den);
    rows.push([round2HalfEven(f), mat.ids[p]]);
  }
  rows.sort((a, b) => b[0] - a[0] || a[1] - b[1]);
  return rows;
}

// ---------- number helpers for panel text ----------
const nums = (t) => (t.match(/-?\d[\d,]*(?:\.\d+)?/g) ?? []).map((x) => Number(x.replace(/,/g, '')));
const near = (a, b, d) => a != null && b != null && Math.abs(a - b) <= 0.5 * 10 ** -d + 1e-9;
const int = (n) => new Intl.NumberFormat('en-GB').format(Math.round(n));
const f2 = (v) => new Intl.NumberFormat('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(v);

// ---------- page audit (checklist 04, 05, 06, 07 and the red alerts) ----------
function auditInPage() {
  const vis = (el) => el && el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
  const out = { small: [], fonts: [], lowContrast: [], smallTargets: [], tight: [], hscroll: false, primaries: 0, red: null };
  const families = new Set();
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return [0, 0, 0, 0];
    const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  };
  const lum = ([r, g, b]) => {
    const f = (v) => ((v /= 255) <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const bgOf = (el) => {
    // composite the background stack down to the first opaque layer; null over a globe (imagery)
    const layers = [];
    for (let e = el; e; e = e.parentElement) {
      if (e.classList?.contains('globe')) return null;
      const c = parse(getComputedStyle(e).backgroundColor);
      if (c[3] > 0) layers.push(c);
      if (c[3] >= 0.999) break;
    }
    let acc = [0, 0, 0];
    for (let i = layers.length - 1; i >= 0; i--) {
      const [r, g, b, a] = layers[i];
      acc = [r * a + acc[0] * (1 - a), g * a + acc[1] * (1 - a), b * a + acc[2] * (1 - a)];
    }
    return acc;
  };
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  for (let n = tw.nextNode(); n; n = tw.nextNode()) {
    if (!n.nodeValue.trim()) continue;
    const el = n.parentElement;
    if (!el || seen.has(el) || !vis(el) || el.closest('.sr-only, .cesium-credit-lightbox, .cesium-widget-credits, [hidden], dialog:not([open]), details:not([open]) > :not(summary)')) continue;
    if (el.closest('#loading') && document.getElementById('loading').hidden) continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) continue;
    seen.add(el);
    const cs = getComputedStyle(el);
    families.add(cs.fontFamily.split(',')[0].trim().replace(/["']/g, ''));
    if (parseFloat(cs.fontSize) < 14 - 1e-6) out.small.push(`${n.nodeValue.trim().slice(0, 40)} (${cs.fontSize})`);
    const bg = bgOf(el);
    if (bg) {
      const fg = parse(cs.color);
      const c = [fg[0] * fg[3] + bg[0] * (1 - fg[3]), fg[1] * fg[3] + bg[1] * (1 - fg[3]), fg[2] * fg[3] + bg[2] * (1 - fg[3])];
      const L1 = lum(c), L2 = lum(bg);
      const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      if (ratio < 4.5) out.lowContrast.push(`${n.nodeValue.trim().slice(0, 40)} (${ratio.toFixed(2)})`);
    }
  }
  out.fonts = [...families];
  // targets that are really on screen (topmost at their centre)
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
  for (const [el, r] of rects) if (r.width < 44 - 0.5 || r.height < 44 - 0.5) out.smallTargets.push(`${nameOf(el).slice(0, 40)} ${Math.round(r.width)}x${Math.round(r.height)}`);
  for (let i = 0; i < rects.length; i++)
    for (let j = i + 1; j < rects.length; j++) {
      const [a, ra] = rects[i], [b, rb] = rects[j];
      if (a.contains(b) || b.contains(a)) continue;
      const dx = Math.max(0, rb.left - ra.right, ra.left - rb.right);
      const dy = Math.max(0, rb.top - ra.bottom, ra.top - rb.bottom);
      if (Math.max(dx, dy) < 8 - 0.5) out.tight.push(`${nameOf(a).slice(0, 25)} | ${nameOf(b).slice(0, 25)} (${Math.max(dx, dy).toFixed(1)} px)`);
    }
  out.hscroll = document.documentElement.scrollWidth > innerWidth + 0.5 || document.body.scrollWidth > innerWidth + 0.5;
  out.primaries = [...document.querySelectorAll('.btn-primary')].filter((b) => vis(b)).length;
  const text = document.body.innerText;
  const m = text.match(/.{0,40}(\bundefined\b|\bNaN\b|\bnull\b|lorem ipsum|title here|\basdf\b|error \d{3}|\[object object\])/i);
  out.red = m ? m[0] : null;
  // technical strings (the team's requirement: plain English, no column names, no "inf", no
  // bracketed ranges, no Spanish class names); link targets and the Cesium credit box are not text
  const tech = /.{0,30}(\b[A-Za-z0-9]+_[A-Za-z0-9_]+\b|\binf\b|\[[-\d.,\s]+,\s*[-\d.inf]+\]|\b(?:roca|regolito|arena|suelo|hielo|agua|continuo|discontinuo|esporadico|ninguno)\b|\.json\b|\.py\b|\{[a-z_]+\}).{0,20}/;
  const tx = text.replace(/\S+@\S+/g, '');
  const tm = tx.match(tech);
  out.tech = tm ? tm[0] : null;
  return out;
}

// ---------- one run ----------
async function run(browser, srv, variant, exp, size) {
  const tag = `${variant}-${size.key}`;
  const { store, explain } = exp;
  const ctx = await browser.newContext({ viewport: { width: size.w, height: size.h }, reducedMotion: size.reduce ? 'reduce' : 'no-preference', deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [];
  // Imagery tiles come from third-party hosts (NASA GIBS, Moon Trek, EOX); a tile they refuse (often
  // an error answer without a CORS header) is a network event outside the app, counted separately.
  const imageryNoise = [];
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    const t = m.text();
    if (/gibs\.earthdata\.nasa\.gov|trek\.nasa\.gov|tiles\.maps\.eox\.at/.test(t) || /^Failed to load resource: net::ERR_FAILED$/.test(t)) imageryNoise.push(t.slice(0, 200));
    else errors.push(t.slice(0, 300));
  });
  page.on('pageerror', (e) => errors.push(`pageerror ${e.message}`));
  let shotN = 0;
  const shot = async (name) => {
    const p = join(SHOTS, `${tag}-${String(++shotN).padStart(2, '0')}-${name}.png`);
    await page.screenshot({ path: p });
    return p;
  };
  const audit = async (view) => {
    const a = await page.evaluate(auditInPage);
    check(a.small.length === 0, `${tag} ${view}: every visible text is 14 px or more${a.small.length ? ': ' + a.small.slice(0, 4).join('; ') : ''}`);
    check(a.fonts.length <= 3, `${tag} ${view}: ${a.fonts.length} typefaces (${a.fonts.join(', ')})`);
    check(a.lowContrast.length === 0, `${tag} ${view}: text contrast 4.5:1 or more${a.lowContrast.length ? ': ' + a.lowContrast.slice(0, 4).join('; ') : ''}`);
    check(a.smallTargets.length === 0, `${tag} ${view}: controls at least 44 x 44 px${a.smallTargets.length ? ': ' + a.smallTargets.slice(0, 5).join('; ') : ''}`);
    check(a.tight.length === 0, `${tag} ${view}: 8 px between neighbouring controls${a.tight.length ? ': ' + a.tight.slice(0, 4).join('; ') : ''}`);
    check(!a.hscroll, `${tag} ${view}: no horizontal scroll`);
    check(a.primaries <= 1, `${tag} ${view}: ${a.primaries} primary action(s) in view`);
    check(!a.red, `${tag} ${view}: no red-alert strings${a.red ? ': "' + a.red + '"' : ''}`);
    check(!a.tech, `${tag} ${view}: no technical strings in view${a.tech ? ': "' + a.tech + '"' : ''}`);
  };
  const flow = (fn, ...a) => page.evaluate(fn, ...a);
  const stepIs = async (s) => (await flow(() => document.body.dataset.step)) === s;
  const waitStep = (s) => page.waitForFunction((x) => document.body.dataset.step === x, s, { timeout: 60_000 });
  const waitDetail = (id, mission) =>
    page.waitForFunction(([i, m]) => {
      const d = document.getElementById('detail-panel');
      return d.dataset.cell === String(i) && d.dataset.mission === m && !!d.querySelector('.result');
    }, [id, mission], { timeout: 90_000 });
  // time from a real input event to the first visible change (checklist 07)
  const armResponse = () =>
    flow(() => {
      window.__resp = { t0: null, t1: null };
      const mark = () => { if (window.__resp.t0 == null) window.__resp.t0 = performance.now(); };
      for (const ev of ['pointerdown', 'keydown']) document.addEventListener(ev, mark, { capture: true, once: true });
      const mo = new MutationObserver(() => {
        if (window.__resp.t0 != null && window.__resp.t1 == null) { window.__resp.t1 = performance.now(); mo.disconnect(); }
      });
      mo.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });
    });
  const responseMs = async () => {
    await page.waitForFunction(() => window.__resp && window.__resp.t1 != null, null, { timeout: 5000 }).catch(() => undefined);
    return flow(() => (window.__resp.t1 != null ? window.__resp.t1 - window.__resp.t0 : Infinity));
  };
  const responses = [];
  const measured = async (what, act) => {
    await armResponse();
    await act();
    const ms = await responseMs();
    responses.push([what, ms]);
    check(ms < 100, `${tag} ${what}: visible response in ${ms.toFixed(1)} ms`);
  };

  // ---- load ----
  const t0 = Date.now();
  await page.goto(srv.base);
  await page.waitForFunction(() => window.starsFlow && window.starsFlow.hasData(), null, { timeout: 120_000 });
  await page.waitForFunction(() => document.getElementById('loading').hidden, null, { timeout: 300_000 });
  ok(`${tag}: data and imagery ready in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  if (size.reduce) check(await flow(() => window.starsBesideYou.prefersReducedMotion()), `${tag}: reduced motion is honoured (flights become instant)`);

  // ---- step 1: choose ----
  check(await stepIs('choose'), `${tag}: first screen is the mission choice`);
  const intro = await flow(() => {
    const choices = [...document.querySelectorAll('#intro .choice')];
    const area = (el) => { const r = el.getBoundingClientRect(); return r.width * r.height; };
    const others = [...document.querySelectorAll('button, a[href], input, summary, label.seg')].filter((e) => !e.closest('#intro') && e.checkVisibility());
    return {
      purpose: document.querySelector('#intro .intro-title')?.textContent ?? '',
      names: choices.map((c) => c.querySelector('.choice-name').textContent.trim()),
      lines: choices.map((c) => c.querySelector('.choice-line').textContent.trim()),
      ids: choices.map((c) => c.dataset.mission),
      minChoice: Math.min(...choices.map(area)),
      maxOther: Math.max(0, ...others.map(area)),
      steps: document.querySelector('#steps .steps-where')?.textContent ?? '',
    };
  });
  check(intro.purpose.length > 20, `${tag}: one sentence of purpose: "${intro.purpose}"`);
  check(intro.names.join('|') === 'Rover|Solar panels|Lunar base', `${tag}: exactly three choices, in the bundle's order: ${intro.names.join(', ')}`);
  check(intro.ids.join(',') === store.missionsJson.offered_missions.join(','), `${tag}: choices follow missions.json offered_missions`);
  check(intro.lines.every((l) => l.length > 10), `${tag}: one line on what each mission tests`);
  check(intro.minChoice > intro.maxOther, `${tag}: the mission choices are the largest controls on the first screen (${Math.round(intro.minChoice)} vs ${Math.round(intro.maxOther)} px²)`);
  check(/Step 1 of [34]/.test(intro.steps), `${tag}: step indicator says "${intro.steps.trim()}"`);
  await shot('choose');
  await audit('choose');

  // ---- "Data and limits" (built from the bundle, merged with the credits); the X closes it ----
  await measured('open "Data and limits"', () => page.click('#credits-button'));
  await page.waitForFunction(() => document.getElementById('credits-dialog').open);
  const dlg = await flow(() => ({
    text: document.getElementById('credits-body').innerText,
    all: document.getElementById('credits-body').textContent,
    meaning: [...document.querySelectorAll('#credits-body [data-note="meaning"]')].map((e) => e.textContent).join(' '),
    sources: document.querySelectorAll('#credits-body .data-sections .credits-list dt').length,
    imagery: /Blue Marble/.test(document.getElementById('credits-body').innerText),
  }));
  // the solar limitation describes the twin: without twins it is left out, as on the card
  const solarLim = store.similarity.texts?.solar_limitation?.text;
  // the technical record sits in a closed disclosure: read its text content; the approved solar limitation is shown open
  // known limitations: the engine's record in plain words (plainText), never the per-pair template
  const lims = store.offeredMissions().every((x) => x.known_limitations.every((l) => (staleForRule(store, x, l) ? !dlg.all.includes(plainText(store, l, x)) : dlg.all.includes(plainText(store, l, x))))) && (!solarLim || !/\{/.test(solarLim) || !dlg.all.includes(solarLim));
  check(/111 km/.test(dlg.text) && /30 km/.test(dlg.text), `${tag}: "Data and limits" states the cell size`);
  check(dlg.meaning.length > 40 && store.offeredMissions().every((x) => dlg.meaning.includes(x.id === 'lunar_base' || !store.isValueRule(x.id) ? '' : store.text('similarity_meaning_real_values') ?? '')), `${tag}: "Data and limits" says what similarity means for each mission's rule`);
  check(lims, `${tag}: "Data and limits" lists every known limitation of the three missions, in plain words`);
  check(dlg.sources >= 5 && dlg.imagery && store.manifest.credits.every((c) => dlg.text.includes(plainText(store, c))), `${tag}: sources with licences (${dlg.sources}), the bundle's credits and the imagery credits are together`);
  await shot('data-and-limits');
  await audit('data and limits');
  await page.click('#credits-close');
  check(!(await flow(() => document.getElementById('credits-dialog').open)), `${tag}: the X closes "Data and limits"`);

  const missions = store.offeredMissions();
  for (let mi = 0; mi < missions.length; mi++) {
    const m = missions[mi];
    const name = intro.names[mi];
    const ranked = store.ranked(m.id).filter((r) => r.final != null);
    const unpairedList = store.ranked(m.id).filter((r) => r.final == null);
    const twinsM = store.hasTwins(m.id);
    const top = ranked[0];
    // ---- choose: keyboard for the first mission, mouse for the others ----
    if (mi === 0) {
      await flow(() => document.activeElement?.blur());
      let found = false;
      for (let k = 0; k < 40 && !found; k++) {
        await page.keyboard.press('Tab');
        found = await flow(() => document.activeElement?.classList.contains('choice'));
      }
      check(found, `${tag}: the mission choices are reachable with Tab`);
      await measured(`choose ${m.id} with Enter`, () => page.keyboard.press('Enter'));
    } else {
      await measured(`choose ${m.id} by mouse`, () => page.click(`#intro .choice[data-mission="${m.id}"]`));
    }
    await waitStep('pick');
    await page.waitForSelector('#mission-panel .rank-row');
    await page.waitForTimeout(600);
    await shot(`${m.id}-pick`);
    await audit(`${m.id} pick`);

    // counts in plain words
    const panel = await flow(() => document.getElementById('mission-panel').innerText);
    const land = store.manifest.counts.EARTH.land_cells, pass = m.pass_counts.EARTH;
    check(panel.includes(`of ${int(land)} land cells`) && panel.includes(`${int(pass)} pass`) && panel.includes(`${int(land - pass)} are eliminated`), `${tag} ${m.id}: counts ${int(land)} land, ${int(pass)} pass, ${int(land - pass)} eliminated`);
    if (unpairedList.length) check(panel.includes(`${int(ranked.length)} of ${int(pass)} points have a lunar twin`), `${tag} ${m.id}: "${int(ranked.length)} of ${int(pass)} points have a lunar twin" in plain words`);
    const reasons = await flow(() => [...document.querySelectorAll('#mission-panel .reasons li .count')].map((e) => e.textContent));
    check(reasons.join('|') === m.top_failure_reasons.EARTH_LAND.map((r) => `${int(r.cells)} cells`).join('|'), `${tag} ${m.id}: commonest elimination reasons as the bundle counts them`);
    check(panel.includes(m.threshold_status.status === 'provisional' ? 'Provisional thresholds' : 'Team design values') && panel.includes('Known limitations'), `${tag} ${m.id}: status label and link to known limitations`);
    check(/1° cell: about 111 km across on Earth and 30 km on the Moon/.test(panel), `${tag} ${m.id}: the true cell size is stated`);
    if (mi === 1) {
      await page.click('#mission-panel .status-line .linklike');
      await page.waitForFunction(() => document.getElementById('credits-dialog').open);
      const focusOn = await flow(() => document.activeElement?.id ?? '');
      check(focusOn === `limits-${m.id}`, `${tag} ${m.id}: "Known limitations" opens the dialog at this mission's limitations`);
      await page.click('#credits-close');
    }
    const lim = store.similarity.texts?.solar_limitation;
    if (lim && lim.mission === m.id) {
      const shown = await flow(() => {
        const n = document.querySelector('#mission-panel [data-note="limitation"]');
        return n && n.checkVisibility() && !n.closest('details') ? n.textContent : null;
      });
      if (lim.mission_card === false || /\{/.test(lim.text)) check(shown === null, `${tag} ${m.id}: the per-pair solar sentence is not on the mission card (it is filled on every pair)`);
      else if (twinsM) check(shown === lim.text, `${tag} ${m.id}: the approved limitation is shown in full on the mission card`);
      else check(shown === null, `${tag} ${m.id}: the twin limitation is not shown under a rule without twins (it describes the twin)`);
    }
    // list
    const rows = await flow(() => [...document.querySelectorAll('#mission-panel .rank-row')].map((r) => ({ id: Number(r.dataset.id), text: r.innerText, temp: r.dataset.missingTemp === 'true' })));
    const exp50 = ranked.slice(0, 50);
    check(rows.length === Math.min(50, ranked.length), `${tag} ${m.id}: top ${rows.length} places listed`);
    check(rows.every((r, i) => r.id === exp50[i].id), `${tag} ${m.id}: list order equals the stored rank`);
    const placeOk = rows.every((r, i) => {
      const p = store.place(exp50[i].landPos).text ?? 'Unnamed land cell';
      const tw = twinsM && exp50[i].twinId != null ? store.twin(m.id, exp50[i].twinId) : null;
      return r.text.includes(p) && r.text.includes(f2(exp50[i].final)) && r.text.startsWith(int(exp50[i].rank)) && (!tw || r.text.includes(tw.feature ? `Moon: near ${tw.feature.name}` : 'Moon: cell at'));
    });
    check(placeOk, `${tag} ${m.id}: every row shows rank, place (region, country), ${twinsM ? 'its lunar twin, ' : ''}and final score from the bundle`);
    check(rows.every((r, i) => r.temp === exp50[i].missingTemp), `${tag} ${m.id}: missing-temperature marks in the top 50 match sim_missing_bits`);
    const markerCounts = await flow(() => [window.starsBesideYou.markers.count('earth'), window.starsBesideYou.markers.count('moon')]);
    check(markerCounts[0] === m.ranked_count, `${tag} ${m.id}: ${markerCounts[0]} Earth markers = the passing points only`);
    if (twinsM) check(markerCounts[1] === store.twinsOf(m.id).length, `${tag} ${m.id}: ${markerCounts[1]} lunar markers = the distinct twins`);
    else {
      check(markerCounts[1] === 0, `${tag} ${m.id}: no lunar markers without twins`);
      const note = await flow(() => document.getElementById('moon-rule').innerText);
      check(note.includes(m.similarity.no_twin_reason ?? store.similarity.no_twin_reason), `${tag} ${m.id}: the Moon side gives the bundle's own reason why there is no lunar twin`);
    }
    if (store.hasZones()) await checkZones(page, tag, store, m, size);
    if (unpairedList.length) await checkUnpairedList(page, tag, store, m, ranked, unpairedList);
    const more = await page.$('#show-more');
    if (more && size.key === 'desktop' && mi === 0) {
      await measured(`${m.id} show more`, () => page.click('#show-more'));
      const n = await flow(() => document.querySelectorAll('#mission-panel .rank-row').length);
      check(n === Math.min(100, ranked.length), `${tag} ${m.id}: "Show more" lists ${n} places`);
    }

    // ---- weights ----
    if (size.key === 'desktop' || m.id === 'solar') {
      await page.click('#mission-panel .weights > summary');
      const slider = `#mission-panel input#w-${m.weighted_variables[0].variable}`;
      await page.focus(slider);
      await page.keyboard.press('ArrowRight');
      await page.waitForFunction(() => /Your weights are in use/.test(document.querySelector('#mission-panel .recompute-status')?.textContent ?? ''), null, { timeout: 60_000 });
      await page.keyboard.press('ArrowRight'); // second move: the utilities are now in memory
      await page.waitForFunction(() => window.starsFlow.recomputeLog().length >= 2, null, { timeout: 30_000 }).catch(() => undefined);
      await page.waitForTimeout(200);
      const st = await flow(() => ({
        w: [...document.querySelectorAll('#mission-panel .sliders input[type=range][id^="w-"]:not(#w-alpha)')].map((i) => Number(i.value)),
        sw: [...document.querySelectorAll('#mission-panel .sliders input[type=range][id^="sw-"]')].map((i) => Number(i.value)),
        alpha: Number(document.getElementById('w-alpha').value),
        ids: [...document.querySelectorAll('#mission-panel .rank-row')].slice(0, 50).map((r) => Number(r.dataset.id)),
        finals: [...document.querySelectorAll('#mission-panel .rank-row .rank-final')].slice(0, 50).map((r) => r.textContent.trim()),
        status: document.querySelector('#mission-panel .recompute-status').textContent,
        log: window.starsFlow.recomputeLog(),
        markers: window.starsBesideYou.markers.count('earth'),
      }));
      const expOrder = independentOrder(store, m.id, st.w, st.alpha, st.sw.length ? st.sw : undefined).slice(0, 50);
      check(st.w[0] !== m.weighted_variables[0].weight, `${tag} ${m.id}: slider moved by keyboard (${m.weighted_variables[0].weight} -> ${st.w[0]})`);
      check(st.ids.every((id, i) => id === expOrder[i][1]) && st.finals.every((f, i) => f.endsWith(f2(expOrder[i][0]))), `${tag} ${m.id}: recomputed order and finals equal the test's own recompute (top 50)`);
      check(/Your weights are in use/.test(st.status), `${tag} ${m.id}: says in words that the user's weights are in use`);
      check(st.markers === m.ranked_count, `${tag} ${m.id}: markers recomputed (${st.markers})`);
      const ms = st.log[st.log.length - 1];
      (report.recompute ??= []).push({ run: tag, mission: m.id, cells: m.ranked_count, ms: Number(ms.toFixed(1)), all: st.log.map((x) => Number(x.toFixed(1))) });
      if (size.key === 'desktop') check(ms < 100, `${tag} ${m.id}: recompute of ${m.ranked_count} cells, ranks, markers and list in ${ms.toFixed(1)} ms`);
      await shot(`${m.id}-weights`);
      await audit(`${m.id} weights`);
      await measured(`${m.id} reset weights`, () => page.click('#reset-weights'));
      await page.waitForFunction(() => /team's weights are in use/.test(document.querySelector('#mission-panel .recompute-status')?.textContent ?? ''));
      const back = await flow(() => [...document.querySelectorAll('#mission-panel .rank-row')].slice(0, 50).map((r) => Number(r.dataset.id)));
      const sliders = await flow(() => [...document.querySelectorAll('#mission-panel .sliders input[type=range][id^="w-"]:not(#w-alpha)')].map((i) => Number(i.value)));
      check(back.every((id, i) => id === exp50[i].id) && sliders.every((v, i) => v === m.weighted_variables[i].weight), `${tag} ${m.id}: "Reset to team values" restores the weights and the stored order`);
      if (store.isValueRule(m.id) && size.key === 'desktop') {
        // a similarity weight: the twin stays, the similarity, final and order are recomputed
        const sv = store.pairVariables(m.id).at(-1);
        await page.focus(`#mission-panel input#sw-${sv.variable}`);
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(300);
        const st2 = await flow(() => ({
          w: [...document.querySelectorAll('#mission-panel .sliders input[type=range][id^="w-"]:not(#w-alpha)')].map((i) => Number(i.value)),
          sw: [...document.querySelectorAll('#mission-panel .sliders input[type=range][id^="sw-"]')].map((i) => Number(i.value)),
          alpha: Number(document.getElementById('w-alpha').value),
          ids: [...document.querySelectorAll('#mission-panel .rank-row')].slice(0, 50).map((r) => Number(r.dataset.id)),
          finals: [...document.querySelectorAll('#mission-panel .rank-row .rank-final')].slice(0, 50).map((r) => r.textContent.trim()),
        }));
        const exp2 = independentOrder(store, m.id, st2.w, st2.alpha, st2.sw).slice(0, 50);
        check(st2.sw.at(-1) !== sv.weight && st2.ids.every((id, i) => id === exp2[i][1]) && st2.finals.every((f, i) => f.endsWith(f2(exp2[i][0]))), `${tag} ${m.id}: a similarity weight (${sv.label} ${sv.weight} -> ${st2.sw.at(-1)}) recomputes order and finals as the test does (top 50)`);
        await page.click('#reset-weights');
        await page.waitForFunction(() => /team's weights are in use/.test(document.querySelector('#mission-panel .recompute-status')?.textContent ?? ''));
      }
      await page.click('#mission-panel .weights > summary');
    }

    // ---- pick the top point: by mouse ----
    if (size.key === 'desktop') {
      await flow(([lat, lon]) => window.starsBesideYou.flyTo('earth', lat, lon, 2500, 0), [top.lat, top.lon]);
      await page.waitForTimeout(500);
      const pt = await flow((id) => {
        const s = window.starsBesideYou.markers.screenState('earth', id);
        const r = window.starsBesideYou.scene('earth').canvas.getBoundingClientRect();
        return s && s.visible ? { x: r.left + s.x, y: r.top + s.y } : null;
      }, top.id);
      check(!!pt, `${tag} ${m.id}: the top marker is on screen`);
      if (pt) {
        await measured(`${m.id} pick the top marker by mouse`, () => page.mouse.click(pt.x, pt.y));
      }
    } else {
      await measured(`${m.id} pick the top row by touch/mouse`, () => page.click(`#mission-panel .rank-row[data-id="${top.id}"]`));
    }
    await waitStep('compare').catch(() => undefined);
    await waitDetail(top.id, m.id).catch(() => undefined);
    check((await flow(() => document.getElementById('detail-panel').dataset.cell)) === String(top.id), `${tag} ${m.id}: the top point (cell ${top.id}) opens the comparison by mouse`);
    await page.waitForTimeout(1600); // paired flight
    await checkTop(page, tag, store, explain, m, top);
    await checkPair(page, tag, store, m, top, twinsM, size);
    // per-pair sentences (e.g. the solar sentence): filled from the bundle, in the first view of the panel
    const ps = store.pairSentencesAt(m.id, top.passPos);
    if (ps.length) {
      const seen = await flow((keys) => keys.map((k) => {
        const el = document.querySelector(`#detail-panel [data-note="${k}"]`);
        if (!el || !el.checkVisibility()) return null;
        const r = el.getBoundingClientRect();
        return { text: el.textContent.trim(), top: r.top, inView: r.top >= 0 && r.top < innerHeight };
      }), ps.map((x) => x.key));
      check(seen.every((x, i) => x && x.text === ps[i].text && x.inView), `${tag} ${m.id}: per-pair sentence shown where it cannot be missed: "${ps[0].text.slice(0, 80)}..."`);
      check(!(await flow(() => /charge(s|d)? (the )?same|same (energy|charge)/i.test(document.getElementById('detail-panel').innerText))), `${tag} ${m.id}: nothing says panels charge the same in both places`);
    }
    await shot(`${m.id}-compare-top`);
    await audit(`${m.id} compare`);
    for (const [k, frac] of [['middle-of-panel', 0.45], ['end-of-panel', 1]]) {
      await flow((f) => { const s = document.querySelector('#detail-panel .panel-scroll'); s.scrollTop = f * (s.scrollHeight - s.clientHeight); }, frac);
      await shot(`${m.id}-compare-top-${k}`);
      await audit(`${m.id} compare (${k})`);
    }

    // ---- video ----
    const hasVid = !!media[MEDIA_FOLDER[m.id]]?.sources?.length;
    const startBtn = await page.$('#start-mission');
    check(!!startBtn === hasVid, `${tag} ${m.id}: "Start mission" ${hasVid ? 'offered (video files present)' : 'absent (no video files)'}`);
    if (startBtn) {
      await measured(`${m.id} start mission`, () => startBtn.click());
      await page.waitForFunction(() => window.starsBesideYou.video.isOpen(), null, { timeout: 20_000 });
      await page.waitForTimeout(1200);
      const v = await flow(() => ({
        title: document.querySelector('.video-dialog .video-title')?.textContent ?? '',
        credit: document.querySelector('.video-dialog .video-credit')?.textContent ?? '',
        note: document.querySelector('.video-dialog .video-note')?.textContent ?? '',
        step: document.querySelector('#steps .steps-where')?.textContent ?? '',
        src: document.querySelector('.video-dialog video')?.currentSrc ?? '',
        paused: document.querySelector('.video-dialog video')?.paused ?? true,
        t: document.querySelector('.video-dialog video')?.currentTime ?? 0,
        focus: document.activeElement?.tagName ?? '',
      }));
      if (size.reduce) check(v.paused && v.focus === 'VIDEO', `${tag} ${m.id}: under reduced motion the film waits, paused, with focus on the player`);
      else check(!v.paused && v.t > 0 && v.focus === 'VIDEO', `${tag} ${m.id}: "Start the mission" plays the film (t = ${v.t.toFixed(2)} s) with focus on the player, not on Close`);
      check(/3D simulation/.test(v.title) && /not real footage/i.test(v.credit + v.note), `${tag} ${m.id}: video labelled as a 3D simulation, not real footage ("${v.credit}")`);
      check(v.credit === media[MEDIA_FOLDER[m.id]].credit, `${tag} ${m.id}: credit line from the media README`);
      check(/Step 4 of 4/.test(v.step), `${tag} ${m.id}: step indicator on "Start the mission"`);
      await shot(`${m.id}-video`);
      await audit(`${m.id} video`);
      await page.click('.video-dialog .video-close');
      await page.waitForFunction(() => !window.starsBesideYou.video.isOpen(), null, { timeout: 5000 });
      check(await stepIs('compare'), `${tag} ${m.id}: the X closes the video and returns to the comparison`);
    }

    // ---- back to the ranking, then the keyboard path to the same point ----
    await measured(`${m.id} back to the ranking`, () => page.click('#detail-panel .panel-foot .back-btn'));
    await waitStep('pick');
    check((await flow(() => document.activeElement?.dataset?.id)) === String(top.id), `${tag} ${m.id}: back to the ranking returns focus to the row of the point`);
    if (size.key === 'desktop' || mi === 0) {
      await flow(() => { document.querySelector('#mission-panel .panel-title').focus(); });
      let onRow = false;
      for (let k = 0; k < 40 && !onRow; k++) {
        await page.keyboard.press('Tab');
        onRow = await flow(() => document.activeElement?.classList.contains('rank-row'));
      }
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('ArrowUp');
      const fid = await flow(() => document.activeElement?.dataset?.id);
      check(onRow && fid === String(top.id), `${tag} ${m.id}: Tab reaches the list; arrows move through it`);
      await measured(`${m.id} open the top row with Enter`, () => page.keyboard.press('Enter'));
      await waitDetail(top.id, m.id);
      check(await stepIs('compare'), `${tag} ${m.id}: the keyboard opens the same comparison`);
      await page.waitForTimeout(800);
      await page.click('#detail-panel .panel-foot .back-btn');
      await waitStep('pick');
    }

    // ---- a middle cell ----
    const mid = ranked[Math.floor(ranked.length / 2)];
    await flow((id) => window.starsFlow.select(id), mid.id);
    await waitDetail(mid.id, m.id);
    await page.waitForTimeout(1200);
    await checkPanel(page, `${tag} ${m.id} middle`, store, m, mid.id, twinsM);
    await shot(`${m.id}-compare-middle`);
    // the steps: "Pick a point" goes back, "Compare the pair" returns
    await page.click('#steps .step-btn:has-text("Pick a point")');
    await waitStep('pick');
    check(true, `${tag} ${m.id}: the step indicator goes back to "Pick a point"`);
    await page.click('#steps .step-btn:has-text("Compare the pair")');
    await waitDetail(mid.id, m.id);
    check(await stepIs('compare'), `${tag} ${m.id}: the step indicator continues to "Compare the pair"`);

    // ---- missing temperature (an Antarctic pair) ----
    const antarctic = ranked.find((r) => r.missingTemp);
    if (antarctic && (m.id === 'rover' || (m.id === 'solar' && size.key === 'desktop'))) {
      await flow((id) => window.starsFlow.select(id), antarctic.id);
      await waitDetail(antarctic.id, m.id);
      const t = await flow(() => ({
        mark: document.querySelector('#detail-panel .result [data-mark="missing-temperature"]')?.textContent ?? null,
        note: document.querySelector('#detail-panel [data-note="missing-temperature"] p')?.textContent ?? null,
      }));
      // the approved note describes a twin chosen on relief: only under a twin rule
      check(t.mark === store.text('missing_temperature_mark') && t.note === (twinsM ? store.text('missing_temperature_note') : null), `${tag} ${m.id}: cell ${antarctic.id} (${antarctic.lat} lat) marked "${t.mark}" in the panel, with the note`);
      await checkPanel(page, `${tag} ${m.id} antarctic`, store, m, antarctic.id, twinsM);
      await shot(`${m.id}-compare-missing-temperature`);
      await page.click('#detail-panel .panel-foot .back-btn');
      await waitStep('pick');
      const row = await flow((id) => {
        const r = document.querySelector(`#mission-panel .rank-row[data-id="${id}"]`);
        return r ? { mark: r.querySelector('[data-mark="missing-temperature"]')?.textContent ?? null, label: r.getAttribute('aria-label') } : null;
      }, antarctic.id);
      check(!!row && row.mark === store.text('missing_temperature_mark') && row.label.includes(row.mark), `${tag} ${m.id}: the same pair (rank ${antarctic.rank}) carries the mark in the ranking list`);
      await shot(`${m.id}-list-missing-temperature`);
    }

    // ---- an eliminated cell reached from another mission ----
    const next = missions[(mi + 1) % missions.length];
    const nmd = store.missionDataOf(next.id);
    const elim = ranked.find((r) => nmd.failBits[r.landPos] !== 0);
    if (elim) {
      await flow((id) => window.starsFlow.select(id), elim.id);
      await waitDetail(elim.id, m.id);
      await page.click(`#detail-panel .others li[data-mission="${next.id}"] .btn`);
      await waitDetail(elim.id, next.id);
      await page.waitForTimeout(800);
      const o = store.outcome(elim.id, next.id);
      const res = await flow(() => ({ text: document.querySelector('#detail-panel .result')?.innerText ?? '', engine: document.querySelector('#detail-panel .result .reason')?.dataset.engineReason ?? '' }));
      check(/Eliminated for this mission/.test(res.text) && res.engine === o.line && !res.text.includes(o.line), `${tag} ${next.id}: cell ${elim.id}, eliminated, reason in plain words "${res.text.split('\n').pop().slice(0, 100)}" (engine: "${o.line}")`);
      await checkPanel(page, `${tag} ${next.id} eliminated`, store, next, elim.id, store.hasTwins(next.id));
      const sections = await flow(() => [...document.querySelectorAll('#detail-panel [data-sec]')].map((s) => s.dataset.sec));
      check(!sections.includes('suitability') && !sections.includes('final-score'), `${tag} ${next.id}: no suitability or final for an eliminated cell`);
      if (store.hasTwins(next.id)) check(!(await flow(() => window.starsBesideYou.beams.lastDrawn().length)), `${tag} ${next.id}: no beam for an eliminated cell`);
      await shot(`${next.id}-compare-eliminated`);
      await audit(`${next.id} eliminated`);
      // back at every step: comparison -> ranking (of the other mission) -> mission choice
      await page.click('#detail-panel .panel-foot .back-btn');
      await waitStep('pick');
      check((await flow(() => window.starsFlow.state.missionId)) === next.id, `${tag}: back from the eliminated cell lands on the ${next.id} ranking`);
    }
    if (await stepIs('compare')) {
      await page.click('#detail-panel .panel-foot .back-btn');
      await waitStep('pick');
    }
    await measured('change mission', () => page.click('#mission-panel .panel-head .btn'));
    await waitStep('choose');
    check(await stepIs('choose'), `${tag}: "Change mission" goes back to the mission choice`);
  }

  if (imageryNoise.length) console.log(`     ${tag}: ${imageryNoise.length} imagery tile request(s) refused by a third-party host (not app errors)`);
  check(errors.length === 0, `${tag}: no console errors${errors.length ? ': ' + errors.slice(0, 3).join(' | ') : ''}`);
  (report.responses ??= []).push({ run: tag, max_ms: Number(Math.max(...responses.map((r) => r[1])).toFixed(1)), n: responses.length });
  await ctx.close();
}

// ---- the comparison panel against the bundle ----
async function panelData(page) {
  return page.evaluate(() => {
    const d = document.getElementById('detail-panel');
    const rows = (sel) => [...d.querySelectorAll(sel)].map((r) => ({ v: r.dataset.variable, pass: r.dataset.pass, limit: r.querySelector('[data-limit]')?.dataset.limit ?? null, cells: [...r.children].map((c) => c.innerText) }));
    return {
      title: d.querySelector('.panel-title')?.textContent ?? '',
      coords: d.querySelector('.panel-head .coords')?.textContent ?? '',
      head: d.querySelector('.panel-head')?.innerText ?? '',
      result: d.querySelector('.result')?.innerText ?? '',
      engine: d.querySelector('.result .reason')?.dataset.engineReason ?? null,
      rank: d.querySelector('.result')?.dataset.rank ?? '',
      gates: rows('table.gates tbody tr'),
      required: [...d.querySelectorAll('table.required tbody tr')].map((r) => r.innerText),
      suit: rows('table.suit tbody tr'),
      suitability: d.querySelector('[data-value="suitability"]')?.textContent ?? null,
      coverage: d.querySelector('[data-value="coverage"]')?.textContent ?? null,
      similarity: d.querySelector('[data-value="similarity"]')?.textContent ?? null,
      sim: rows('table.sim tbody tr'),
      info: rows('table.info tbody tr'),
      arith: d.querySelector('[data-value="arith"]')?.textContent ?? null,
      confidence: d.querySelector('[data-value="confidence"]')?.textContent ?? null,
      lunar: d.querySelector('.lunar')?.innerText ?? '',
      twin: d.querySelector('.lunar')?.dataset.twin ?? null,
      share: d.querySelector('.lunar .share')?.textContent ?? null,
      link: d.querySelector('.lunar a')?.href ?? null,
      meaning: d.querySelector('[data-note="meaning"]')?.textContent ?? null,
      others: [...d.querySelectorAll('.others li')].map((li) => ({ m: li.dataset.mission, t: li.innerText })),
      ice: d.querySelector('[data-sec="ice-prospecting-information-only"]')?.innerText ?? null,
      sources: !!d.querySelector('details.sources'),
      back: !!d.querySelector('.back-btn'),
      pairVars: [...d.querySelectorAll('.pair-var')].map((b) => ({
        v: b.dataset.variable,
        within: b.dataset.within,
        role: b.querySelector('.tag-role')?.textContent ?? '',
        vals: Object.fromEntries([...b.querySelectorAll('.pair-vals > div')].map((x) => [x.dataset.k, x.querySelector('dd').innerText])),
      })),
      simArith: d.querySelector('[data-value="sim-arith"]')?.textContent ?? null,
      noTwin: d.querySelector('.pair-strip [data-note="no-twin"]')?.textContent ?? null,
      finalSec: !!d.querySelector('[data-sec="final-score"]'),
    };
  });
}

async function checkPanel(page, label, store, m, id, twins) {
  const p = await panelData(page);
  const o = store.outcome(id, m.id);
  const lat = store.latOf(id), lon = store.lonOf(id);
  const place = store.place(o.landPos).text ?? 'Unnamed land cell';
  const bad = [];
  if (p.title !== place) bad.push(`place "${p.title}" vs "${place}"`);
  const [la, lo] = nums(p.coords);
  if (!near(la, Math.abs(lat), 1) || !near(lo, Math.abs(lon), 1)) bad.push(`coords ${p.coords}`);
  if (!/111 km north-south x \d+(\.\d)? km east-west/.test(p.head)) bad.push('cell size');
  // result line
  const unpaired = o.pass && o.final == null;
  if (unpaired) {
    if (!/no lunar twin/.test(p.result) || !p.result.includes(f2(o.suitability)) || p.finalSec) bad.push(`result of a point without a twin "${p.result}"`);
  } else if (o.pass) {
    if (Number(p.rank) !== o.rank || !p.result.includes(`Rank ${int(o.rank)} of ${int(m.ranked_count)}`) || !p.result.includes(f2(o.final))) bad.push(`result "${p.result}"`);
  } else if (p.engine !== o.line || p.result.includes(o.line) || !/Eliminated for this mission/.test(p.result)) bad.push('elimination line (plain words shown, the engine line kept in data-engine-reason)');
  // hard filters: limit, value, pass/fail with the word
  const gates = [...o.common, ...o.gates];
  if (p.gates.length !== gates.length) bad.push(`gate rows ${p.gates.length} vs ${gates.length}`);
  gates.forEach((g, i) => {
    const r = p.gates[i];
    // the limit is shown in words (no engine interval notation); the engine's interval stays in data-limit
    if (!r || r.v !== g.gate.variable || r.limit !== g.gate.limit || /\binf\b|\[/.test(r.cells[1]) || r.pass !== String(g.pass) || !r.cells[3].includes(g.pass ? 'Pass' : 'Fail')) bad.push(`gate ${g.gate.variable}`);
    else if (typeof g.value.value === 'number' && !near(nums(r.cells[2])[0], g.value.value, 0) && Math.abs(nums(r.cells[2])[0] - g.value.value) > 0.06 * Math.abs(g.value.value) + 0.002) bad.push(`gate value ${g.gate.variable} ${r.cells[2]} vs ${g.value.value}`);
    else if (typeof g.value.value === 'string' && !r.cells[2].startsWith(classWord(g.value.value))) bad.push(`gate class ${g.gate.variable}`);
    else if (g.value.value == null && !r.cells[2].startsWith('no data')) bad.push(`gate missing ${g.gate.variable}`);
  });
  if (p.required.length !== o.required.length || o.required.some((r, i) => !p.required[i].includes(r.present ? 'Has data' : 'No data'))) bad.push('required rows');
  if (o.pass) {
    // suitability rows sorted by contribution
    if (p.suit.map((r) => r.v).join(',') !== o.breakdown.map((r) => r.wv.variable).join(',')) bad.push('suitability order');
    o.breakdown.forEach((b, i) => {
      const r = p.suit[i];
      if (!r) return;
      const u = nums(r.cells[1])[0], w = nums(r.cells[2])[0], c = nums(r.cells[3])[0];
      if (b.utility == null ? !/no data/.test(r.cells[1]) : !near(u, b.utility, 3)) bad.push(`utility ${b.wv.variable}`);
      if (!near(w, b.weight, 2)) bad.push(`weight ${b.wv.variable}`);
      if (b.contribution == null ? !/ignored/.test(r.cells[3]) : !near(c, b.contribution, 3)) bad.push(`contribution ${b.wv.variable}`);
      if (!/measured|derived|modelled|no data/.test(r.cells[0])) bad.push(`level word ${b.wv.variable}`);
    });
    if (!near(Number(p.suitability), o.suitability, 2)) bad.push(`suitability ${p.suitability} vs ${o.suitability}`);
    if (!near(nums(p.coverage ?? '')[0], 100 * o.coverage, 1)) bad.push('coverage');
    if (o.confidence == null ? p.confidence != null : !p.confidence?.toLowerCase().startsWith(o.confidence) || !near(nums(p.confidence)[0], o.confidenceScore, 3)) bad.push(`confidence "${p.confidence}"`);
  }
  if (o.pass && !unpaired) {
    if (!near(Number(p.similarity), o.similarity, 2)) bad.push('similarity');
    const a = nums(p.arith ?? '');
    const alpha = m.alpha;
    if (!near(a[a.length - 1], o.final, 2) || !p.arith.includes(`${alpha} x ${f2(o.similarity)}`) || !p.arith.includes(f2(o.suitability))) bad.push(`arithmetic "${p.arith}"`);
  }
  if (o.valueRule && o.pass && !unpaired) {
    // every similarity variable, key variables first, with both values, difference, tolerance, who set it, within, weight, score
    const rows = [...o.pairRows].sort((x, y) => (x.def.role === 'key' ? 0 : 1) - (y.def.role === 'key' ? 0 : 1));
    if (p.pairVars.map((r) => r.v).join(',') !== rows.map((r) => r.def.variable).join(',')) bad.push(`pair variables ${p.pairVars.map((r) => r.v)}`);
    rows.forEach((r, i) => {
      const b = p.pairVars[i];
      if (!b) return;
      const pct = r.def.unit === 'percentile points';
      const close = (txt, v, p1 = pct) => v == null ? /no data/.test(txt) : Math.abs(nums(txt)[0] - v) <= (p1 ? 0.051 : 0.006 * Math.abs(v) + 0.006);
      if (!close(b.vals.earth, r.earth) || !close(b.vals.moon, r.moon) || !close(b.vals.diff, r.def.unit === 'percentile points' && r.earth != null && r.moon != null ? Math.abs(Math.round(b.vals.earth * 10) - Math.round(b.vals.moon * 10)) / 10 : r.diff)) bad.push(`pair values ${r.def.variable}: ${b.vals.earth} / ${b.vals.moon} / ${b.vals.diff}`);
      if (r.real && (!close(b.vals['earth-real'], r.real.earth, false) || !close(b.vals['moon-real'], r.real.moon, false) || !close(b.vals['diff-real'], r.real.diff, false) || !/\bK\b/.test(b.vals['diff-real'] ?? '') === (r.real.unit === 'K'))) bad.push(`real values ${r.def.variable}: ${b.vals['earth-real']} / ${b.vals['moon-real']} / ${b.vals['diff-real']}`);
      if (!close(b.vals.tolerance, r.def.tolerance) || !b.vals.tolerance.includes(`Set by: ${setByWords(r.def.tolerance_set_by)}`)) bad.push(`tolerance ${r.def.variable}`);
      if (!b.vals.within.includes(r.within ? 'Within' : 'Outside') || b.within !== String(r.within)) bad.push(`within ${r.def.variable}`);
      if (!near(nums(b.vals.weight)[0], r.weight, 2) || (r.score != null && !near(nums(b.vals.score)[0], r.score, 3))) bad.push(`weight/score ${r.def.variable}`);
      if (!b.role.includes(r.def.role === 'key' ? 'key' : 'secondary')) bad.push(`role ${r.def.variable}`);
    });
    if (!p.simArith || !near(nums(p.simArith).at(-1), o.similarity, 2)) bad.push(`similarity arithmetic "${p.simArith}"`);
    if (p.info.length !== o.pairInfo.length || o.pairInfo.some((r, i) => r.diff != null && !(Math.abs(nums(p.info[i].cells[3])[0] - r.diff) <= 0.006 * r.diff + 0.01))) bad.push('information rows with differences');
  }
  if (unpaired) {
    if (p.twin !== 'none' || p.noTwin !== o.noPair?.sentence || p.pairVars.length || p.similarity != null) bad.push(`no-twin panel: "${p.noTwin}" vs "${o.noPair?.sentence}"`);
  }
  // similarity: absolute values and z of both sides (Moon column only when it exists)
  const showMoon = o.pass || !twins;
  if (!o.valueRule) o.similarityRows.forEach((s, i) => {
    const r = p.sim[i];
    if (!r || r.v !== s.sv.variable) return void bad.push(`sim row ${s.sv.variable}`);
    const e = nums(r.cells[1]);
    if (s.earth.value != null && Math.abs(e[0] - s.earth.value) > 0.006 * Math.abs(s.earth.value) + 0.01) bad.push(`earth value ${s.sv.variable} ${r.cells[1]}`);
    if (s.earth.z != null && !r.cells[1].includes(`z ${Number(s.earth.z.toFixed(2))}`.replace(/(\.\d*?)0+$/, '$1'))) {
      const z = nums(r.cells[1].split('z ')[1] ?? '')[0];
      if (!near(z, s.earth.z, 2)) bad.push(`earth z ${s.sv.variable}`);
    }
    if (showMoon) {
      if (r.cells.length !== 3) return void bad.push('moon column missing');
      const mv = nums(r.cells[2]);
      if (s.moon.value != null && Math.abs(mv[0] - s.moon.value) > 0.006 * Math.abs(s.moon.value) + 0.01) bad.push(`moon value ${s.sv.variable}`);
      const z = nums(r.cells[2].split('z ')[1] ?? '')[0];
      if (s.moon.z != null && !near(z, s.moon.z, 2)) bad.push(`moon z ${s.sv.variable}`);
    } else if (r.cells.length !== 2) bad.push('moon column shown for an eliminated twin cell');
  });
  if (!o.valueRule) {
    if (p.info.length !== store.similarity.not_part_of_similarity.length || !p.info.every((r) => /not part of the similarity/.test(r.cells[0]))) bad.push('information rows');
    const rock = p.info.find((r) => r.v === 'rock_or_bare_frac');
    if (store.text('rock_note') && (!rock || !rock.cells[0].includes(store.text('rock_note')))) bad.push('bare-ground note');
  }
  // the meaning of the mission's own rule (similarity_meaning_<x> naming the mission), from the bundle
  const wantMeaning = o.valueRule ? (store.textFor('similarity_meaning', m.id)?.text ?? store.text('similarity_meaning_real_values')) : twins ? store.text('similarity_meaning') : store.similarity.meaning.split(/(?<=\.)\s/)[0];
  if (p.meaning !== wantMeaning) bad.push('meaning sentence');
  // other missions
  const others = store.offeredMissions().filter((x) => x.id !== m.id);
  others.forEach((x, i) => {
    const oo = store.outcome(id, x.id);
    const li = p.others[i];
    if (!li || li.m !== x.id) return void bad.push(`other ${x.id}`);
    if (oo.pass && oo.final == null ? !(li.t.includes('Passes') && li.t.includes('no lunar twin')) : oo.pass ? !(li.t.includes('Passes') && li.t.includes(`rank ${int(oo.rank)} of`) && li.t.includes(f2(oo.final))) : !(li.t.includes('Eliminated') && li.t.includes(oo.reasons.map((r) => r.label[0].toUpperCase() + r.label.slice(1)).join('; ')))) bad.push(`other ${x.id} "${li.t}"`);
  });
  // lunar side
  if (twins && o.pass && !unpaired) {
    const t = o.twin;
    if (p.twin !== String(t.id) || !p.lunar.includes(`Near ${t.feature.name}`) || !p.lunar.includes(`${Number(t.feature.distance_km.toFixed(1))} km`) || p.link !== t.feature.url) bad.push('twin');
    if (p.share !== store.twinSharingText(m.id, t.earth_cells)) bad.push(`share "${p.share}"`);
  }
  const noTwin = m.similarity.no_twin_reason ?? store.similarity.no_twin_reason;
  if (!twins && (p.twin !== 'none' || !noTwin || !p.lunar.includes(noTwin))) bad.push('no-twin statement (the bundle\'s sentence)');
  if (m.id === 'lunar_base' && o.ice) {
    if (!p.ice || !p.ice.includes(o.ice.pass ? 'Passes the ice filters' : 'Does not pass the ice filters') || (o.ice.pass && !p.ice.includes(f2(o.ice.suitability)))) bad.push('ice component');
  }
  if (!p.sources || !p.back) bad.push('sources on demand / back control');
  check(bad.length === 0, `${label}: cell ${id} panel numbers equal the bundle${bad.length ? ': ' + bad.slice(0, 6).join('; ') : ''}`);
}

async function checkTop(page, tag, store, explain, m, top) {
  // the top cell against explain.json, an independent export of the same numbers
  const e = explain.missions[m.id][0];
  const p = await panelData(page);
  const bad = [];
  if (e.id !== top.id || Number(p.rank) !== 1) bad.push('rank 1');
  if (!near(Number(p.suitability), e.suitability, 2) || !near(nums(p.coverage)[0], 100 * e.coverage, 1)) bad.push('suitability/coverage');
  if (p.suit.map((r) => r.v).join(',') !== e.breakdown.map((b) => b.variable).join(',')) bad.push('breakdown order');
  e.breakdown.forEach((b, i) => {
    const r = p.suit[i];
    if (r && (!near(nums(r.cells[1])[0], b.utility, 3) || !near(nums(r.cells[3])[0], b.contribution, 3))) bad.push(`breakdown ${b.variable}`);
  });
  if (!near(Number(p.similarity), e.similarity.value, 2)) bad.push('similarity');
  for (const r of p.sim) {
    const ez = e.similarity.earth[r.v]?.z, mz = e.similarity.moon[r.v]?.z;
    if (ez != null && !near(nums(r.cells[1].split('z ')[1])[0], ez, 2)) bad.push(`earth z ${r.v}`);
    if (mz != null && !near(nums(r.cells[2].split('z ')[1])[0], mz, 2)) bad.push(`moon z ${r.v}`);
  }
  if (!near(nums(p.arith).at(-1), e.final, 2)) bad.push('final');
  if (!p.confidence.toLowerCase().startsWith(e.confidence) || !near(nums(p.confidence)[0], e.confidence_score, 3)) bad.push('confidence');
  if (e.similarity.twin && (p.twin !== String(e.similarity.twin.id) || !p.lunar.includes(e.similarity.twin.feature))) bad.push('twin');
  if (m.id === 'lunar_base' && e.components?.ice && !p.ice.includes(e.components.ice.pass ? 'Passes the ice filters' : 'Does not pass')) bad.push('ice');
  check(bad.length === 0, `${tag} ${m.id}: top cell ${top.id} panel equals explain.json${bad.length ? ': ' + bad.join('; ') : ''}`);
  if (e.similarity.variables) {
    for (const v of e.similarity.variables) {
      const b = p.pairVars.find((x) => x.v === v.variable);
      const tol = (x) => (v.unit === 'percentile points' ? 0.051 : 0.006 * Math.abs(x) + 0.006);
      if (!b || !near(nums(b.vals.score)[0], v.score, 3) || Math.abs(nums(b.vals.earth)[0] - v.earth) > tol(v.earth) || Math.abs(nums(b.vals.moon)[0] - v.moon) > tol(v.moon)) bad.push(`pair variable ${v.variable} vs explain.json`);
      if (b && v.earth_real != null && v.unit !== v.real_unit && Math.abs(nums(b.vals['earth-real'])[0] - v.earth_real) > 0.006 * Math.abs(v.earth_real) + 0.006) bad.push(`real value ${v.variable} vs explain.json`);
    }
  }
  check(bad.length === 0, `${tag} ${m.id}: top cell ${top.id} similarity variables equal explain.json${bad.length ? ': ' + bad.join('; ') : ''}`);
  await checkPanel(page, `${tag} ${m.id} top`, store, m, top.id, store.hasTwins(m.id));
}

// ---- points without a lunar twin: the list (divider, filter, reason) and the panel ----
async function checkUnpairedList(page, tag, store, m, ranked, unpairedList) {
  const flow = (fn, ...a) => page.evaluate(fn, ...a);
  await page.click('#mission-panel .show-filter label:has(input[value="unpaired"])');
  await page.waitForFunction((id) => document.querySelector('#mission-panel .rank-row')?.dataset.id === String(id), unpairedList[0].id, { timeout: 10_000 }).catch(() => undefined);
  const l = await flow(() => ({
    divider: document.querySelector('#mission-panel [data-divider="no-twin"]')?.innerText ?? null,
    rows: [...document.querySelectorAll('#mission-panel .rank-row')].slice(0, 20).map((r) => ({ id: Number(r.dataset.id), paired: r.dataset.paired, text: r.innerText, label: r.getAttribute('aria-label') })),
  }));
  const first = unpairedList[0];
  const np = store.noPairAt(m.id, first.passPos);
  const reason = noPairKindWords(np.kind);
  check(!!l.divider && l.divider.includes(`No lunar twin: ${int(unpairedList.length)} points`) && /no lunar twin/.test(l.divider), `${tag} ${m.id}: divider "${(l.divider ?? '').split('\n')[0]}" with one sentence on why`);
  check(l.rows.length > 0 && l.rows.every((r, i) => r.id === unpairedList[i].id && r.paired === 'false' && r.text.includes('No lunar twin')), `${tag} ${m.id}: "No twin" lists the ${int(unpairedList.length)} points without a twin in the bundle's order (by suitability)`);
  check(l.rows[0].text.includes(reason) && l.rows[0].text.includes(f2(first.suitability)) && !/final/.test(l.rows[0].text), `${tag} ${m.id}: a row without a twin gives the reason in plain words and the suitability, no final ("${reason.slice(0, 90)}")`);
  await page.screenshot({ path: join(SHOTS, `${tag}-${m.id}-list-no-twin.png`) });
  // the panel of that point: no similarity, no final, no beam, no paired view; the mission can still start
  await page.click(`#mission-panel .rank-row[data-id="${first.id}"]`);
  await page.waitForFunction(([i, mm]) => { const d = document.getElementById('detail-panel'); return d.dataset.cell === String(i) && d.dataset.mission === mm && !!d.querySelector('.result'); }, [first.id, m.id], { timeout: 90_000 });
  await page.waitForTimeout(1200);
  await checkPanel(page, `${tag} ${m.id} no twin`, store, m, first.id, store.hasTwins(m.id));
  const g = await flow(() => ({ beams: window.starsBesideYou.beams.lastDrawn().length, focused: window.starsBesideYou.focus.isFocused(), moon: window.starsBesideYou.markers.selected('moon'), start: !!document.getElementById('start-mission'), strip: document.querySelector('#detail-panel .pair-strip')?.getBoundingClientRect().top ?? -1 }));
  const hasVid = !!media[MEDIA_FOLDER[m.id]]?.sources?.length;
  check(g.beams === 0 && !g.focused && g.moon == null && g.start === hasVid && g.strip >= 0 && g.strip < 900, `${tag} ${m.id}: point without a twin: no beam, no paired view, no lunar marker; "Start the mission" ${hasVid ? 'still offered' : 'absent (no video)'}; the reason is in the first view`);
  await page.screenshot({ path: join(SHOTS, `${tag}-${m.id}-compare-no-twin.png`) });
  await page.click('#detail-panel .panel-foot .back-btn');
  await page.waitForFunction(() => document.body.dataset.step === 'pick');
  check((await flow(() => document.activeElement?.dataset?.id)) === String(first.id), `${tag} ${m.id}: back from a point without a twin returns focus to its row`);
  await page.click('#mission-panel .show-filter label:has(input[value="all"])');
  await page.waitForFunction((id) => document.querySelector('#mission-panel .rank-row')?.dataset.id === String(id), ranked[0].id, { timeout: 10_000 });
}

// ---- the mission's zone on the Moon and "Why this zone?" (revision 6 data, or the zone fixture) ----
async function checkZones(page, tag, store, m, size) {
  const flow = (fn, ...a) => page.evaluate(fn, ...a);
  const z = await store.loadZones();
  const codes = store.zoneCodes(m.id);
  const outside = z.regions.filter((r) => !codes.includes(r.code));
  await page.waitForFunction(() => !!document.querySelector('#mission-panel [data-slot="zone"] .zone-caption'), null, { timeout: 60_000 }).catch(() => undefined);
  const cap = await flow(() => ({
    moon: document.querySelector('#moon-rule .zone-caption')?.innerText ?? null,
    panel: document.querySelector('#mission-panel [data-slot="zone"] .zone-caption')?.innerText ?? null,
    layer: document.body.dataset.zone ?? null,
  }));
  const zname = m.similarity.zone?.name ?? store.similarity.target.zones?.[m.id]?.name;
  check(!!cap.panel && cap.panel.includes('Search zone') && (!zname || cap.panel.includes(zname)) && /Why this zone\?/.test(cap.panel) && cap.layer === m.id, `${tag} ${m.id}: the search zone is drawn on the Moon and named ("${(cap.panel ?? '').split('\n')[0]}")`);
  const btn = size.key === 'desktop' && cap.moon ? '#zone-why' : '#zone-why-panel';
  const readDlg = () => flow(() => {
    const d = document.getElementById('zone-dialog');
    return d && d.open ? {
      region: d.dataset.region,
      why: d.querySelector('[data-text="zone_why"]')?.textContent ?? null,
      note: d.querySelector('[data-text="general_note"]')?.textContent ?? null,
      regions: [...d.querySelectorAll('.zone-region')].map((x) => ({ code: x.dataset.region, open: x.open, label: x.querySelector('summary')?.innerText ?? '', text: x.querySelector('[data-text]')?.textContent ?? null })),
      tapped: d.querySelector('.zone-tapped')?.innerText ?? null,
      foot: d.querySelector('.zone-foot')?.innerText ?? '',
      focus: document.activeElement?.closest('.zone-region')?.dataset.region ?? document.activeElement?.className ?? '',
    } : null;
  });
  // mouse
  await page.click(btn);
  await page.waitForFunction(() => document.getElementById('zone-dialog')?.open, null, { timeout: 5000 });
  let d = await readDlg();
  const t = z.texts;
  const textsOk = !t || (d.why === t.zone_why[m.id] && d.note === t.general_note && d.regions.every((r) => r.text === t.outside[m.id][r.code]));
  check(!!d && d.regions.map((r) => r.code).join() === outside.map((r) => r.code).join() && d.regions.every((r, i) => r.label.includes(outside[i].label)) && textsOk, `${tag} ${m.id}: "Why this zone?" (mouse) shows the zone text, the general note and the ${outside.length} other regions, ${t ? 'texts verbatim' : 'regions only (texts null)'}`);
  check(/Sources of these texts/.test(d.foot) && (!t || d.foot.includes(new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${z.consulted_on}T12:00:00Z`)))), `${tag} ${m.id}: consultation date and a link to the sources list ("${d.foot.trim()}")`);
  await page.screenshot({ path: join(SHOTS, `${tag}-${m.id}-zone-panel.png`) });
  const a = await page.evaluate(auditInPage);
  check(!a.small.length && !a.lowContrast.length && !a.smallTargets.length && !a.tech && !a.red && !a.hscroll, `${tag} ${m.id} zone panel: text size, contrast, targets, no technical strings${[...a.small, ...a.lowContrast, ...a.smallTargets, a.tech ?? ''].filter(Boolean).slice(0, 3).map((x) => ': ' + x).join('')}`);
  await page.click('#zone-dialog .zone-close');
  check(!(await flow(() => document.getElementById('zone-dialog').open)), `${tag} ${m.id}: the X closes the zone panel`);
  // keyboard: the control, then a region of the list
  await page.focus('#zone-why-panel');
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => document.getElementById('zone-dialog')?.open, null, { timeout: 5000 });
  let reached = false;
  for (let k = 0; k < 20 && !reached; k++) {
    await page.keyboard.press('Tab');
    reached = await flow((c) => document.activeElement?.closest('.zone-region')?.dataset.region === c, outside[0].code);
  }
  await page.keyboard.press('Enter');
  d = await readDlg();
  check(reached && d.regions[0].open, `${tag} ${m.id}: by keyboard, Tab reaches "${outside[0].label}" in the list and Enter opens its entry`);
  await page.keyboard.press('Escape');
  check(!(await flow(() => document.getElementById('zone-dialog').open)) && (await flow(() => document.activeElement?.id)) === 'zone-why-panel', `${tag} ${m.id}: Escape closes the zone panel and focus returns to the control`);
  // a tap on a lunar cell outside the zone (desktop: the Moon globe is on screen)
  if (size.key === 'desktop') {
    const target = outside.find((r) => ['D', 'F', 'E'].includes(r.code)) ?? outside[0];
    let best = null;
    for (let id = 0; id < 64800; id++) {
      if (store.regionOfCell(id)?.code !== target.code) continue;
      const { lat, lon } = store.moonLatLon(id);
      const dd = Math.abs(lat - 10) + Math.abs(lon - 10);
      if (!best || dd < best.dd) best = { id, lat, lon, dd };
    }
    await flow(([lat, lon]) => window.starsBesideYou.flyTo('moon', lat, lon, 600, 0), [best.lat, best.lon]);
    await page.waitForTimeout(800);
    const c = await flow(() => { const r = window.starsBesideYou.scene('moon').canvas.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; });
    await page.mouse.click(c.x, c.y);
    await page.waitForFunction(() => document.getElementById('zone-dialog')?.open, null, { timeout: 5000 }).catch(() => undefined);
    d = await readDlg();
    const want = store.regionOfCell(best.id);
    check(!!d && d.region === want.code && d.regions.find((r) => r.code === want.code)?.open && (d.tapped ?? '').includes(want.label) && d.focus === want.code, `${tag} ${m.id}: a click on a lunar cell outside the zone (${best.lat}, ${best.lon}) opens the panel at "${want.label}" and names it`);
    await page.screenshot({ path: join(SHOTS, `${tag}-${m.id}-zone-tap.png`) });
    if (d) await page.click('#zone-dialog .zone-close');
  }
}

// ---- the zone fixture: only the zone checks, every mission ----
async function zoneRun(browser, srv, exp, size) {
  const tag = `zones-${size.key}`;
  const ctx = await browser.newContext({ viewport: { width: size.w, height: size.h }, reducedMotion: size.reduce ? 'reduce' : 'no-preference' });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(srv.base);
  await page.waitForFunction(() => window.starsFlow?.hasData() && document.getElementById('loading').hidden, null, { timeout: 300_000 });
  for (const m of exp.store.offeredMissions()) {
    await page.click(`#intro .choice[data-mission="${m.id}"]`);
    await page.waitForSelector('#mission-panel .rank-row');
    await checkZones(page, tag, exp.store, m, size);
    await page.click('#mission-panel .panel-head .btn');
    await page.waitForFunction(() => document.body.dataset.step === 'choose');
    check(!(await page.evaluate(() => document.body.dataset.zone && document.querySelector('#moon-rule .zone-caption'))), `${tag} ${m.id}: the zone is removed when the mission is left`);
  }
  check(errors.length === 0, `${tag}: no page errors${errors.length ? ': ' + errors[0] : ''}`);
  await ctx.close();
}

async function checkPair(page, tag, store, m, top, twins, size) {
  const s = await page.evaluate(([id]) => {
    const api = window.starsBesideYou;
    const tw = window.starsFlow.store.missionDataOf(window.starsFlow.state.missionId);
    const twinId = api.markers.selected('moon');
    const rectOf = (el) => (el && !el.hidden ? el.getBoundingClientRect() : null);
    const pos = (body, mid) => {
      const st = mid == null ? null : api.markers.screenState(body, mid);
      if (!st || !st.visible) return null;
      const r = api.scene(body).canvas.getBoundingClientRect();
      return { x: r.left + st.x, y: r.top + st.y };
    };
    return {
      earthSel: api.markers.selected('earth'),
      moonSel: twinId,
      beams: api.beams.lastDrawn().length,
      focused: api.focus.isFocused(),
      earthPt: pos('earth', id),
      moonPt: pos('moon', twinId),
      panel: rectOf(document.getElementById('detail-panel')),
      note: document.getElementById('moon-rule').innerText,
      _ : tw ? 1 : 0,
    };
  }, [top.id]);
  const inside = (pt, r) => pt && r && pt.x >= r.left && pt.x <= r.right && pt.y >= r.top && pt.y <= r.bottom;
  check(s.earthSel === top.id, `${tag} ${m.id}: the Earth marker is selected`);
  check(!!s.earthPt && !inside(s.earthPt, s.panel), `${tag} ${m.id}: the panel does not cover the selected Earth point`);
  if (twins) {
    const t = store.outcome(top.id, m.id).twin;
    check(s.moonSel === t.id, `${tag} ${m.id}: the lunar twin marker ${t.id} is selected`);
    check(s.beams === 1, `${tag} ${m.id}: one beam joins the pair`);
    check(s.focused, `${tag} ${m.id}: paired view (focusPair) with both cells outlined`);
    check(!!s.moonPt && !inside(s.moonPt, s.panel), `${tag} ${m.id}: the panel does not cover the lunar twin`);
  } else {
    check(s.moonSel == null && s.beams === 0 && !s.focused, `${tag} ${m.id}: no lunar marker, no beam, no paired view without twins`);
    check(s.note.includes(m.similarity.no_twin_reason ?? store.similarity.no_twin_reason), `${tag} ${m.id}: the Moon side states the bundle's no-twin reason`);
  }
}

// ---------- extra: forced failures and other widths ----------
async function extras(browser, srv, exp) {
  const page0 = async (w, h) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    page.setDefaultTimeout(180_000); // software WebGL at 3840 px is slow to settle
    return { ctx, page };
  };
  // a missing data file
  {
    srv.state.block = ['similarity.json'];
    const { ctx, page } = await page0(1440, 900);
    await page.goto(srv.base);
    await page.waitForSelector('#intro .alert', { timeout: 60_000 });
    const t = await page.evaluate(() => document.querySelector('#intro .alert').innerText);
    check(/similarity\.json/.test(t) && /could not be loaded/.test(t) && /reload/i.test(t), `missing data file: "${t.split('\n')[0]}"`);
    await page.waitForFunction(() => document.getElementById('loading').hidden, null, { timeout: 300_000 }).catch(() => undefined);
    await page.screenshot({ path: join(SHOTS, 'error-missing-data-file.png') });
    await ctx.close();
    srv.state.block = [];
  }
  // a missing detail tile when a point is opened
  {
    const { ctx, page } = await page0(1440, 900);
    await page.goto(srv.base);
    await page.waitForFunction(() => window.starsFlow?.hasData() && document.getElementById('loading').hidden, null, { timeout: 300_000 });
    await page.evaluate(() => window.starsFlow.chooseMission('rover'));
    const top = exp.store.ranked('rover')[0];
    const tile = exp.store.manifest.detail_tiles.files[exp.store.tileIndexOf(top.id)].name;
    srv.state.block = [tile];
    await page.evaluate(() => window.starsFlow.store.loadAllTiles = async () => undefined);
    await page.click(`#mission-panel .rank-row[data-id="${top.id}"]`);
    await page.waitForSelector('#detail-panel .alert', { timeout: 30_000 });
    const t = await page.evaluate(() => document.querySelector('#detail-panel .alert').innerText);
    check(t.includes(tile) && /Try again/.test(t), `missing detail tile: "${t.split('\n')[0]}"`);
    await page.screenshot({ path: join(SHOTS, 'error-missing-detail-tile.png') });
    srv.state.block = [];
    await page.click('#detail-panel .alert .btn');
    await page.waitForSelector('#detail-panel .result', { timeout: 30_000 });
    check(true, 'missing detail tile: "Try again" recovers once the file is back');
    await ctx.close();
  }
  // a blocked imagery host
  {
    const { ctx, page } = await page0(1440, 900);
    await page.route(/gibs\.earthdata\.nasa\.gov/, (r) => r.abort());
    await page.goto(srv.base);
    await page.waitForFunction(() => document.getElementById('loading').dataset.state === 'failed', null, { timeout: 200_000 }).catch(() => undefined);
    const t = await page.evaluate(() => ({ e: document.getElementById('loading-error').innerText, retry: !document.getElementById('loading-retry').hidden }));
    check(/GIBS|Earth/.test(t.e) && /reload|try again/i.test(t.e) && t.retry, `blocked imagery host: "${t.e}"`);
    await page.screenshot({ path: join(SHOTS, 'error-blocked-imagery.png') });
    await ctx.close();
  }
  // other widths: 768 and 3840
  for (const [w, h] of [[768, 1024], [3840, 2160]]) {
    const { ctx, page } = await page0(w, h);
    try {
    await page.goto(srv.base);
    await page.waitForFunction(() => window.starsFlow?.hasData() && document.getElementById('loading').hidden, null, { timeout: 300_000 });
    const views = [];
    await page.screenshot({ path: join(SHOTS, `twin-${w}-01-choose.png`) });
    views.push(await page.evaluate(auditInPage));
    await page.click('#intro .choice[data-mission="solar"]');
    await page.waitForSelector('#mission-panel .rank-row');
    await page.waitForTimeout(800);
    await page.screenshot({ path: join(SHOTS, `twin-${w}-02-pick.png`) });
    views.push(await page.evaluate(auditInPage));
    const top = exp.store.ranked('solar')[0];
    await page.click(`#mission-panel .rank-row[data-id="${top.id}"]`);
    await page.waitForSelector('#detail-panel .result', { timeout: 60_000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: join(SHOTS, `twin-${w}-03-compare.png`) });
    views.push(await page.evaluate(auditInPage));
    const cover = await page.evaluate((id) => {
      const api = window.starsBesideYou;
      const r = document.getElementById('detail-panel').getBoundingClientRect();
      return ['earth', 'moon'].map((b) => {
        const sel = api.markers.selected(b);
        const st = sel == null ? null : api.markers.screenState(b, sel);
        const c = api.scene(b).canvas.getBoundingClientRect();
        if (!st || !st.visible) return 'not visible';
        const x = c.left + st.x, y = c.top + st.y;
        return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom ? 'covered' : 'clear';
      });
    }, top.id);
    check(views.every((v) => !v.hscroll), `${w} px: no horizontal scroll in any view`);
    check(views.every((v) => !v.small.length && !v.smallTargets.length && !v.lowContrast.length && !v.tight.length), `${w} px: text size, contrast, target size and spacing${views.flatMap((v) => [...v.small, ...v.smallTargets, ...v.lowContrast, ...v.tight]).slice(0, 4).map((s) => ': ' + s).join('')}`);
    check(cover.every((c) => c === 'clear'), `${w} px: the panel covers neither selected point (${cover.join(', ')})`);
    } catch (e) {
      fail(`${w} px: stopped: ${e.message.split('\n')[0]}`);
    } finally {
      // a page left open keeps software WebGL busy and slows every later run
      await ctx.close();
    }
  }
}

// ---------- main ----------
const tmp = mkdtempSync(join(tmpdir(), 'stars-bundle-'));
const variants = [];
if (!ONLY || ONLY === 'twin') variants.push({ key: 'twin', dir: join(APP, 'public/data/v2'), dataDir: null });
if ((!ONLY || ONLY === 'notwin') && existsSync(OTHER)) {
  cpSync(OTHER, join(tmp, 'v2'), { recursive: true });
  variants.push({ key: 'notwin', dir: join(tmp, 'v2'), dataDir: join(tmp, 'v2') });
} else if (!ONLY || ONLY === 'notwin') fail(`no-twin bundle not found at ${OTHER}`);
if ((!ONLY || ONLY === 'zones') && existsSync(ZONES)) {
  cpSync(ZONES, join(tmp, 'zones'), { recursive: true });
  variants.push({ key: 'zones', dir: join(tmp, 'zones'), dataDir: join(tmp, 'zones'), light: true });
}
const sizes = [
  { key: 'desktop', w: 1440, h: 900 },
  { key: 'phone', w: 375, h: 812, reduce: true },
].filter((s) => SIZES.includes(s.key));

const browser = await chromium.launch();
try {
  for (const v of variants) {
    const exp = await expectations(v.dir);
    const srv = await serve(DIST, { dataDir: v.dataDir });
    console.log(`\n== ${v.key}: rules ${JSON.stringify(exp.store.manifest.similarity_rules ?? exp.store.similarity.rule)}, contract revision ${exp.store.manifest.contract_revision}`);
    check(exp.store.offeredMissions().every((m) => exp.store.hasTwins(m.id) === !!exp.store.manifest.files.find((f) => f.name === m.files.EARTH).columns.some((c) => c.name === 'twin')), `${v.key}: twins decided from the bundle itself, per mission`);
    for (const s of process.argv.includes('--extras-only') ? [] : sizes) {
      try {
        if (v.light) await zoneRun(browser, srv, exp, s);
        else await run(browser, srv, v.key, exp, s);
      } catch (e) {
        fail(`${v.key}-${s.key}: run stopped: ${e.message.split('\n')[0]}`);
        // close what the stopped run left open: an open page keeps software WebGL busy
        for (const c of browser.contexts()) await c.close().catch(() => undefined);
      }
    }
    if (v.key === 'twin' && !process.argv.includes('--skip-extra')) {
      try {
        await extras(browser, srv, exp);
      } catch (e) {
        fail(`extras stopped: ${e.message.split('\n')[0]}`);
        for (const c of browser.contexts()) await c.close().catch(() => undefined);
      }
    }
    await srv.close();
  }
} finally {
  await browser.close();
  rmSync(tmp, { recursive: true, force: true });
}
writeFileSync(join(SHOTS, 'flow-report.json'), JSON.stringify(report, null, 1));
console.log('\nrecompute times (ms):', JSON.stringify(report.recompute ?? []));
console.log('slowest visible response per run (ms):', JSON.stringify(report.responses ?? []));
console.log(failures.length ? `\n${failures.length} failure(s)` : '\nall flow checks passed');
process.exit(failures.length ? 1 : 0);
