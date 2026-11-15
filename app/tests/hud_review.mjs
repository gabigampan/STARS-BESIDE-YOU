#!/usr/bin/env node
// Independent review of the Mission Control redesign against the brief (R1-R10, T1-T4).
// Build first; writes JSON to $OUT/review.json and screenshots to $OUT. Usage: node tests/hud_review.mjs
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { serve } from './lib/serve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = process.env.OUT ?? '/tmp/hud-review';
const LIVE = 'https://stars-beside-you.vercel.app/';
mkdirSync(OUT, { recursive: true });
const R = {};
const ONLY = (process.env.ONLY ?? 'audit,r3,motion,r10,r9').split(',');
const on = (k) => ONLY.includes(k);
const log = (k, v) => { R[k] = v; console.log(k, JSON.stringify(v).slice(0, 600)); };

const srv = await serve(join(APP, 'dist'));
const browser = await chromium.launch();
const open = async (url, w, h, opts = {}, b = browser) => {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, hasTouch: w < 900, isMobile: false, ...opts });
  const page = await ctx.newPage();
  page.__errors = [];
  page.on('pageerror', (e) => page.__errors.push(String(e).slice(0, 200)));
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  return { ctx, page };
};
const ready = (p) => p.waitForFunction(() => window.starsFlow?.hasData?.(), null, { timeout: 45_000 }).catch(() => undefined);
const step = (p, s) => p.waitForFunction((x) => window.starsFlow?.state.step === x, s, { timeout: 20_000 }).then(() => true, () => false);
const mission = async (p, k) => { await p.keyboard.press(String(k)); const ok = await step(p, 'pick'); await p.waitForFunction(() => document.querySelectorAll('#mission-panel li button').length > 0, null, { timeout: 15_000 }).catch(() => 0); return ok; };
const pair = async (p) => { await p.locator('#mission-panel li button').first().click(); const ok = await step(p, 'compare'); await p.waitForTimeout(900); return ok; };
const back = async (p, s) => { await p.keyboard.press('Escape'); return step(p, s); };
const shot = (p, n) => p.screenshot({ path: join(OUT, n + '.png') }).catch(() => 0);

// ---- page-side audit of every visible text element and control
const audit = (p) => p.evaluate(() => {
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const v = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [v[0], v[1], v[2], v[3] ?? 1]; };
  const lum = ([r, g, b]) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const mix = (a, b) => [0, 1, 2].map((i) => a[i] * a[3] + b[i] * (1 - a[3])).concat(1);
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const vis = (e) => { const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return false; if (r.bottom < 0 || r.right < 0 || r.top > innerHeight || r.left > innerWidth) return false; for (let x = e; x; x = x.parentElement) { const s = getComputedStyle(x); if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0) return false; if (x.closest('.sr-only')) return false; } return true; };
  const label = (e) => (e.innerText || e.getAttribute('aria-label') || e.value || '').trim().replace(/\s+/g, ' ').slice(0, 60);
  const texts = [];
  for (const e of document.querySelectorAll('body *')) {
    if (['SCRIPT', 'STYLE', 'SVG', 'CANVAS', 'VIDEO'].includes(e.tagName) || e.closest('svg')) continue;
    const own = [...e.childNodes].filter((n) => n.nodeType === 3 && n.textContent.trim()).map((n) => n.textContent.trim()).join(' ');
    if (!own || !vis(e)) continue;
    const s = getComputedStyle(e);
    let fg = parse(s.color);
    let bg = null, over = false, layers = [];
    for (let x = e; x; x = x.parentElement) {
      if (x.classList?.contains('pane') || x.classList?.contains('globe')) { over = true; break; }
      const c = parse(getComputedStyle(x).backgroundColor);
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 0.99) { bg = c; break; } }
    }
    let base = bg ?? (over ? [0, 0, 0, 1] : [255, 255, 255, 1]);
    // compose the translucent layers (darkest plausible backing under them: black, when over a globe)
    for (const l of layers.slice(0, bg ? -1 : undefined).reverse()) base = mix(l, base);
    if (layers.length && !bg && over) over = 'translucent-backing';
    const fgc = mix(fg, base);
    texts.push({ t: own.slice(0, 50), tag: e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.split(' ')[0] : ''), color: s.color, bg: `rgb(${base.slice(0, 3).map(Math.round).join(',')})`, ratio: +ratio(fgc, base).toFixed(2), fs: parseFloat(s.fontSize), over: over === true && !layers.length ? 'over imagery' : over || '' });
  }
  const ctrls = [];
  for (const e of document.querySelectorAll('button, a[href], input, select, summary, [role=switch], [role=button], [tabindex]:not([tabindex="-1"])')) {
    if (!vis(e)) continue;
    const r = e.getBoundingClientRect();
    if (r.width < 44 || r.height < 44) ctrls.push({ t: label(e), tag: e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className ? '.' + e.className.split(' ')[0] : ''), w: Math.round(r.width), h: Math.round(r.height), cesium: !!e.closest('.cesium-widget-credits, .cesium-credit-logoContainer') });
  }
  const scroll = [document.documentElement.scrollWidth, document.documentElement.clientWidth, document.documentElement.scrollHeight, innerHeight];
  const out = [];
  for (const e of document.querySelectorAll('body *')) { if (!vis(e)) continue; const r = e.getBoundingClientRect(); if (r.right > innerWidth + 1 || r.left < -1) { if (getComputedStyle(e).position === 'fixed' && e.classList.contains('sr-only')) continue; out.push({ tag: e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className ? '.' + e.className.split(' ')[0] : ''), l: Math.round(r.left), r: Math.round(r.right) }); } }
  return { texts, ctrls, scroll, out: out.slice(0, 20) };
});

const anims = (p) => p.evaluate(() => document.getAnimations().filter((a) => a.playState === 'running' && !(a.effect?.target instanceof Element && a.effect.target.closest('.spinner'))).map((a) => `${a.animationName ?? a.transitionProperty ?? 'waapi'}@${a.effect?.target?.id || a.effect?.target?.className || a.effect?.target?.tagName}`));
const draws = (p) => p.evaluate(() => window.starsBesideYou?.beams?.drawCount?.() ?? null);
const startKF = (p) => p.evaluate(() => { window.__kf = window.__kf || {}; const tick = () => { for (const a of document.getAnimations()) { const n = a.animationName ?? a.transitionProperty ?? 'waapi'; try { const props = new Set(); for (const k of a.effect.getKeyframes()) for (const x of Object.keys(k)) if (!['offset', 'easing', 'composite', 'computedOffset'].includes(x)) props.add(x); if (a.transitionProperty) props.add(a.transitionProperty); window.__kf[n] = [...props]; } catch {} } if (!window.__kfStop) requestAnimationFrame(tick); }; requestAnimationFrame(tick); });
const bdf = (p) => p.evaluate(() => { const panes = [...document.querySelectorAll('.pane')].map((e) => e.getBoundingClientRect()); const hit = []; for (const e of document.querySelectorAll('body *')) { const s = getComputedStyle(e); const v = s.backdropFilter || s.webkitBackdropFilter; if (!v || v === 'none') continue; const r = e.getBoundingClientRect(); if (r.width < 1) continue; if (panes.some((q) => r.left < q.right && r.right > q.left && r.top < q.bottom && r.bottom > q.top)) hit.push(`${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}.${e.className}: ${v}`); } return hit; });

try {
  // ================= R1, R4 (default palette), R5, R6 at 1440x900; R1 at 1366x768
  const audits = {};
  if (on('audit')) for (const [w, h] of [[1440, 900], [1366, 768], [375, 812], [812, 375]]) {
    const { ctx, page } = await open(srv.base, w, h);
    await ready(page);
    await page.waitForTimeout(1800);
    const rec = {};
    rec.start = await audit(page);
    if (w === 1440 || w === 375) await shot(page, `start_${w}`);
    for (const k of [1, 2, 3]) {
      await mission(page, k); await page.waitForTimeout(800);
      rec['mission' + k] = await audit(page);
      if ((w === 1440 || w === 375) && k === 1) await shot(page, `mission_${w}`);
      await pair(page);
      rec['pair' + k] = await audit(page);
      if ((w === 1440 || w === 375) && k === 1) await shot(page, `pair_${w}`);
      await back(page, 'pick'); await back(page, 'choose'); await page.waitForTimeout(300);
    }
    audits[`${w}x${h}`] = rec;
    if (w === 1440) {
      // colour-blind palette pass
      await page.getByRole('switch', { name: /Colour-blind/ }).first().click().catch(async () => page.locator('text=Colour-blind mode').first().click());
      await page.waitForTimeout(500);
      const cb = { start: await audit(page) };
      await shot(page, 'cvd_start_1440');
      for (const k of [1, 2, 3]) { await mission(page, k); await page.waitForTimeout(600); cb['mission' + k] = await audit(page); await pair(page); cb['pair' + k] = await audit(page); if (k === 1) await shot(page, 'cvd_pair_1440'); await back(page, 'pick'); await back(page, 'choose'); }
      audits.cvd1440 = cb;
      await page.locator('#credits-button').click(); await page.waitForTimeout(500); await shot(page, 'credits_1440'); await page.keyboard.press('Escape');
    }
    if (w === 375 || w === 812) {
      const hts = () => page.evaluate(() => ['#earth-pane', '#moon-pane', '#detail-panel', '#mission-panel'].map((s) => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().height) : null; }));
      const fold = {};
      await mission(page, 1); await pair(page);
      fold.pairPanesBefore = await hts();
      const opt = page.locator('#mf-options');
      fold.optExists = await opt.count();
      fold.optAria0 = await opt.getAttribute('aria-expanded').catch(() => null);
      await opt.tap().catch(() => opt.click()); await page.waitForTimeout(500);
      fold.optAria1 = await opt.getAttribute('aria-expanded').catch(() => null);
      fold.afterOptions = await hts();
      if (w === 375) await shot(page, 'phone_options_open');
      await opt.tap().catch(() => opt.click()); await page.waitForTimeout(400);
      fold.afterOptionsClose = await hts();
      const hd = page.locator('#mf-handle');
      fold.handleAria0 = await hd.getAttribute('aria-expanded').catch(() => null);
      await hd.tap().catch(() => hd.click()); await page.waitForTimeout(500);
      fold.handleAria1 = await hd.getAttribute('aria-expanded').catch(() => null);
      fold.afterHandle = await hts();
      if (w === 375) await shot(page, 'phone_sheet_toggled');
      await hd.tap().catch(() => hd.click()); await page.waitForTimeout(400);
      fold.afterHandle2 = await hts();
      log(`R2.fold.${w}`, fold);
    }
    await ctx.close();
  }
  // summarise
  const summ = {};
  for (const [vp, rec] of Object.entries(audits)) {
    summ[vp] = { scroll: {}, lowContrast: [], small: [], ctrls: [], out: {} };
    const seen = new Set(), seenF = new Set(), seenC = new Set();
    for (const [st, a] of Object.entries(rec)) {
      summ[vp].scroll[st] = a.scroll.join('/');
      if (a.out.length) summ[vp].out[st] = a.out;
      for (const t of a.texts) {
        if (t.ratio < 4.5 || t.over === 'over imagery') { const k = t.tag + t.t; if (!seen.has(k)) { seen.add(k); summ[vp].lowContrast.push({ st, ...t }); } }
        if (t.fs < 14) { const k = t.tag + t.t; if (!seenF.has(k)) { seenF.add(k); summ[vp].small.push({ st, t: t.t, tag: t.tag, fs: t.fs }); } }
      }
      for (const c of a.ctrls) { const k = c.tag + c.t; if (!seenC.has(k)) { seenC.add(k); summ[vp].ctrls.push({ st, ...c }); } }
    }
  }
  if (on('audit')) log('audit', summ);

  // ================= R3 text diff vs live
  const collect = async (url) => {
    const { ctx, page } = await open(url, 1440, 900);
    await ready(page); await page.waitForTimeout(1500);
    const t = { start: await page.evaluate(() => document.body.innerText) };
    for (const k of [1, 2, 3]) { await mission(page, k); await page.waitForTimeout(800); t['mission' + k] = await page.evaluate(() => document.body.innerText); await pair(page); t['pair' + k] = await page.evaluate(() => document.body.innerText); t['figs' + k] = await page.evaluate(() => [...document.querySelectorAll('#detail-panel .figs dd')].map((d) => d.textContent)); await back(page, 'pick'); await back(page, 'choose'); }
    await ctx.close();
    return t;
  };
  const red = on('r3') ? await collect(srv.base) : { figs1: null };
  let live = null;
  if (on('r3')) try { live = await collect(LIVE); } catch (e) { log('R3.liveError', String(e)); }
  if (live) {
    const lines = (s) => s.split('\n').map((x) => x.replace(/\s+/g, ' ').trim()).filter(Boolean);
    const diff = {};
    for (const k of Object.keys(red)) {
      if (k.startsWith('figs')) { diff[k] = { red: red[k], live: live[k], equal: JSON.stringify(red[k]) === JSON.stringify(live[k]) }; continue; }
      const a = lines(live[k]), b = lines(red[k]);
      const ca = new Map(); for (const x of a) ca.set(x, (ca.get(x) || 0) + 1);
      const cb = new Map(); for (const x of b) cb.set(x, (cb.get(x) || 0) + 1);
      const onlyLive = [...ca].filter(([x, n]) => (cb.get(x) || 0) < n).map(([x]) => x);
      const onlyRed = [...cb].filter(([x, n]) => (ca.get(x) || 0) < n).map(([x]) => x);
      const sameJoined = a.join(' ') === b.join(' ');
      diff[k] = { onlyLive, onlyRed, sameOrderAndText: sameJoined };
    }
    log('R3', diff);
  }

  // ================= R7 focus + keyboard; R8; T1-T4 (normal motion, 1440)
  if (on('motion')) {
    const { ctx, page } = await open(srv.base, 1440, 900);
    await startKF(page);
    // T1: click a card at 200 ms
    await page.waitForTimeout(200);
    const t1 = {};
    t1.bootOnAt200 = await page.evaluate(() => document.body.classList.contains('hud-boot'));
    const c = page.locator('.choice').first();
    t1.cardCount = await c.count();
    await c.click({ timeout: 3000 }).catch((e) => { t1.clickErr = String(e).slice(0, 120); });
    t1.missionOpened = await step(page, 'pick');
    const tpanel = Date.now();
    await page.waitForFunction(() => performance.getEntriesByName('hud-boot-end').length > 0, null, { timeout: 15_000 }).catch(() => 0);
    t1.marks = await page.evaluate(() => { const s = performance.getEntriesByName('hud-boot-start')[0]?.startTime; const e = performance.getEntriesByName('hud-boot-end')[0]?.startTime; return { start: s, end: e, ms: s != null && e != null ? Math.round(e - s) : null, nav: Math.round(performance.now()) }; });
    await page.waitForFunction(() => [...document.querySelectorAll('.topbar, .steps, .stage > .panel:not([hidden]), .intro-card, .pane')].filter((e) => e.getClientRects().length).every((e) => getComputedStyle(e).opacity === '1'), null, { timeout: 10_000 }).catch(() => 0);
    t1.allOpaqueAt = await page.evaluate(() => Math.round(performance.now()));
    t1.declaredBootMax = null;
    await ctx.close();
    // second page for the rest
    const s = await open(srv.base, 1440, 900);
    const pg = s.page;
    await startKF(pg);
    await pg.waitForTimeout(250);
    t1.declaredBootMax = await pg.evaluate(() => Math.max(0, ...document.getAnimations().filter((a) => /^hud-/.test(a.animationName ?? '')).map((a) => { const t = a.effect.getTiming(); return Number(t.delay) + Number(t.duration); })));
    await ready(pg); await pg.waitForTimeout(2500);
    const r8 = {};
    r8.startAnims = await anims(pg); await pg.waitForTimeout(3000); r8.startAnims3s = await anims(pg);
    r8.bdfStart = await bdf(pg);
    // R7 tab in start
    const tabWalk = async (n) => { const res = []; for (let i = 0; i < n; i++) { await pg.keyboard.press('Tab'); await pg.waitForTimeout(40); res.push(await pg.evaluate(() => { const e = document.activeElement; if (!e || e === document.body) return null; const s = getComputedStyle(e); const ring = (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 2) || (s.boxShadow && s.boxShadow !== 'none'); return { t: (e.innerText || e.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40), tag: e.tagName.toLowerCase() + (e.id ? '#' + e.id : ''), outline: `${s.outlineStyle} ${s.outlineWidth} ${s.outlineColor}`, shadow: s.boxShadow.slice(0, 60), ring }; })); } return res; };
    const tabStart = await tabWalk(25);
    // T2: scan
    await pg.evaluate(() => { window.__scan = []; const t0 = performance.now(); new MutationObserver(() => window.__scan.push([Math.round(performance.now() - t0), document.body.classList.contains('hud-scan')])).observe(document.body, { attributes: true, attributeFilter: ['class'] }); });
    await pg.locator('body').click({ position: { x: 5, y: 5 } }).catch(() => 0);
    await pg.keyboard.press('Escape').catch(() => 0);
    const key1 = await mission(pg, 1);
    const ana = await pg.locator('#mission-panel li button').count();
    await pg.waitForTimeout(1200);
    const scan = await pg.evaluate(() => window.__scan);
    await shot(pg, 'T2_mission_1440');
    r8.missionAnims3s = (await pg.waitForTimeout(2000), await anims(pg));
    r8.bdfMission = await bdf(pg);
    // T4 + T3
    await pg.evaluate(() => { window.__figs = []; const t0 = performance.now(); const id = setInterval(() => { const dds = [...document.querySelectorAll('#detail-panel .figs dd')]; if (dds.length) window.__figs.push([Math.round(performance.now() - t0), dds.map((d) => d.textContent).join('|'), dds.filter((d) => d.classList.contains('hud-counting')).length]); }, 50); setTimeout(() => clearInterval(id), 1500); });
    await pg.keyboard.press('1');
    const k1pair = await step(pg, 'compare');
    await pg.waitForTimeout(1600);
    const figs = await pg.evaluate(() => window.__figs);
    await shot(pg, 'T3_pair_1440');
    const beam0 = await pg.evaluate(() => window.starsBesideYou?.beams?.lastDrawn?.());
    const d0 = await draws(pg); await pg.waitForTimeout(3000); const d1 = await draws(pg); await pg.waitForTimeout(2000); const d2 = await draws(pg);
    r8.pairAnims3s = await anims(pg);
    r8.bdfPair = await bdf(pg);
    r8.draws = [d0, d1, d2];
    const tabPair = await tabWalk(30);
    // drag the earth globe
    await pg.keyboard.press('Escape').catch(() => 0); // may close something; check step
    const stepAfterEsc = await pg.evaluate(() => window.starsFlow.state.step);
    if (stepAfterEsc !== 'compare') { await pg.keyboard.press('1'); await step(pg, 'compare'); await pg.waitForTimeout(1000); }
    const eb = await pg.locator('#earth-globe').boundingBox();
    const dA = await draws(pg);
    await pg.mouse.move(eb.x + eb.width / 2, eb.y + eb.height / 2); await pg.mouse.down(); await pg.mouse.move(eb.x + eb.width / 2 + 80, eb.y + eb.height / 2 + 30, { steps: 8 }); await pg.mouse.up();
    await pg.waitForTimeout(1500);
    const dB = await draws(pg);
    const beam1 = await pg.evaluate(() => window.starsBesideYou?.beams?.lastDrawn?.());
    await shot(pg, 'T3_pair_dragged_1440');
    const escBack = await back(pg, 'pick');
    const escBack2 = await back(pg, 'choose');
    await pg.evaluate(() => { window.__kfStop = true; });
    const kf = await pg.evaluate(() => window.__kf);
    log('T1', t1);
    log('T2', { scanTimeline: scan, key1, analogs: ana });
    log('T4', { samples: figs.length, distinct: [...new Set(figs.map((f) => f[1]))], countingSpanMs: figs.filter((f) => f[2] > 0).map((f) => f[0]).reduce((a, b, i, arr) => [arr[0], arr[arr.length - 1]], null), k1pair, figsRed: red.figs1 });
    log('T3', { beamBefore: beam0, beamAfter: beam1, drawsAroundDrag: [dA, dB] });
    log('R7', { tabStartNoRing: tabStart.filter((x) => x && !x.ring), tabStart: tabStart.map((x) => x && x.tag + ':' + x.t), tabPairNoRing: tabPair.filter((x) => x && !x.ring), tabPair: tabPair.map((x) => x && x.tag + ':' + x.t), keys: { key1Mission: key1, analogs: ana, key1Pair: k1pair, escToPick: escBack, escToChoose: escBack2 } });
    log('R8', { ...r8, keyframeProps: kf });
    await s.ctx.close();
  }

  // ================= R10 reduced motion
  if (on('r10')) {
    const { ctx, page } = await open(srv.base, 1440, 900, { reducedMotion: 'reduce' });
    await page.evaluate(() => { window.__cls = new Set(); const chk = () => { for (const c of document.body.classList) window.__cls.add(c); if (document.querySelector('.hud-counting')) window.__cls.add('hud-counting'); requestAnimationFrame(chk); }; chk(); });
    await ready(page); await page.waitForTimeout(800);
    const a0 = await anims(page);
    await mission(page, 1); await page.waitForTimeout(100); const a1 = await anims(page);
    const d0 = await draws(page);
    await pair(page); const a2 = await anims(page); const d1 = await draws(page); await page.waitForTimeout(2000); const d2 = await draws(page);
    const cls = await page.evaluate(() => [...window.__cls]);
    log('R10', { load: a0, mission: a1, pair: a2, classesSeen: cls, draws: [d0, d1, d2] });
    await ctx.close();
  }

  // ================= R9 no WebGL
  if (on('r9')) {
    const b2 = await chromium.launch({ args: ['--disable-gpu', '--disable-3d-apis'] });
    const { ctx, page } = await open(srv.base, 1440, 900, {}, b2);
    const gl = await page.evaluate(() => { const c = document.createElement('canvas'); return [c.getContext('webgl'), c.getContext('webgl2')].map((x) => x === null); });
    await ready(page); await page.waitForTimeout(2500);
    const msg = await page.evaluate(() => ({ status: [...document.querySelectorAll('.pane-status, [role=alert], .nowebgl, .notice')].filter((e) => e.getClientRects().length && e.innerText.trim()).map((e) => e.innerText.trim().slice(0, 160)), cesiumError: !!document.querySelector('.cesium-widget-errorPanel') }));
    await shot(page, 'R9_nowebgl_start');
    const m = await mission(page, 1); const n = await page.locator('#mission-panel li button').count();
    const p = await pair(page); await shot(page, 'R9_nowebgl_pair');
    const e = await back(page, 'pick');
    const cesiumError2 = await page.evaluate(() => !!document.querySelector('.cesium-widget-errorPanel'));
    log('R9', { glNull: gl, msg, mission: m, analogs: n, pair: p, escBack: e, cesiumError2, errors: page.__errors });
    await ctx.close(); await b2.close();
  }
} finally {
  writeFileSync(join(OUT, `review_${ONLY.join('_')}.json`), JSON.stringify(R, null, 1));
  await browser.close();
  srv.close?.();
}
