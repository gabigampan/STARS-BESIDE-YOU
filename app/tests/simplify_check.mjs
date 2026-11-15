#!/usr/bin/env node
// Independent check of the 18 "simplify for a judge" points (+ phone bars, logo, overlap) against a LIVE URL.
// Usage: node tests/simplify_check.mjs https://stars-beside-you.vercel.app [shotsDir]
import { mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const URL0 = process.argv[2] || 'https://stars-beside-you.vercel.app';
const SHOTS = process.argv[3] || '/tmp/check18';
mkdirSync(SHOTS, { recursive: true });
const out = {};
const log = (k, v) => { out[k] = v; console.log(k, JSON.stringify(v)); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const BAD = ['Guide: Welcome', 'Show less', 'Repeat R', 'NASA Blue Marble', 'LRO Wide Angle Camera mosaic', 'Step 1 of 4', 'Step 2 of 4', 'Step 3 of 4', 'of 4', '(current step)', 'Choose a mission to start', 'Press 1', 'Each point is a 1 degree cell', 'Similarity rule', 'provisional thresholds', 'team design values', 'five best', 'Sunlight', 'Full Moon', 'Even light', 'Markers:', 'Search zone', 'Why this zone?'];
function pageState() {
  const vis = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !e.closest('[hidden]') && !e.closest('dialog:not([open])') && !e.closest('details:not([open]) > :not(summary)'); };
  const txt = document.body.innerText;
  const aria = [...document.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label')).join(' | ');
  const d = document.documentElement;
  const off = [...document.querySelectorAll('body *')].filter((e) => vis(e) && !e.closest('.globe')).filter((e) => { const r = e.getBoundingClientRect(); return r.right > innerWidth + 1 || r.left < -1; }).slice(0, 5).map((e) => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().left) + '..' + Math.round(e.getBoundingClientRect().right));
  return { txt, aria, sw: d.scrollWidth, cw: d.clientWidth, sh: d.scrollHeight, ih: innerHeight, off, step: window.starsFlow?.state.step, sel: window.starsFlow?.state.selectedId };
}
function overlapScan() {
  const vis = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.opacity !== '0' && !e.closest('[hidden]'); };
  const roots = ['.topbar', '#mf-handle', '#mf-sheet', '.panel:not([hidden])', '.intro:not([hidden])', '.pane-caption', '.pane-reset', '#guide-caption'].flatMap((s) => [...document.querySelectorAll(s)]);
  const boxes = [];
  for (const root of roots) {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      if (!n.textContent.trim() || !vis(n.parentElement)) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) if (r.width > 1 && r.height > 1) boxes.push({ el: n.parentElement, r, t: n.textContent.trim().slice(0, 30) });
    }
  }
  // clip by scroll container visibility
  const inView = (b) => { let p = b.el.parentElement; while (p && p !== document.body) { const s = getComputedStyle(p); if (/(auto|scroll|hidden)/.test(s.overflowY)) { const pr = p.getBoundingClientRect(); if (b.r.bottom < pr.top || b.r.top > pr.bottom) return false; } p = p.parentElement; } return b.r.bottom > 0 && b.r.top < innerHeight; };
  const B = boxes.filter(inView);
  const hits = [];
  for (let i = 0; i < B.length; i++) for (let j = i + 1; j < B.length; j++) {
    const a = B[i], b = B[j]; if (a.el === b.el || a.el.contains(b.el) || b.el.contains(a.el)) continue;
    const ox = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
    const oy = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
    if (ox > 1 && oy > 1) hits.push(a.t + ' x ' + b.t);
  }
  const cut = [...document.querySelectorAll('.panel *, .intro *, .topbar *')].filter((e) => vis(e) && /\d/.test(e.textContent) && e.children.length === 0 && e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX !== 'visible').map((e) => e.textContent.trim().slice(0, 30));
  return { n: B.length, hits: hits.slice(0, 8), nh: hits.length, cut: cut.slice(0, 5) };
}
function heights() {
  const api = window.starsBesideYou; if (!api?.hasGlobes?.()) return null;
  const h = (b) => Math.round(api.scene(b).camera.positionCartographic.height / 1000);
  return { earth: h('earth'), moon: h('moon') };
}
function cardText() { const p = document.getElementById('detail-panel'); return p ? p.innerText : ''; }

async function open(browser, w, h, touch, extra = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, hasTouch: touch, isMobile: touch, ...extra });
  const page = await ctx.newPage();
  const errs = [];
  page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)); });
  page.on('pageerror', (e) => errs.push('pageerror ' + String(e).slice(0, 160)));
  page.on('requestfailed', (r) => errs.push('reqfail ' + r.url().slice(0, 120) + ' ' + (r.failure()?.errorText || '')));
  page.on('response', (r) => { if (r.status() >= 400) errs.push('HTTP ' + r.status() + ' ' + r.url().slice(0, 120)); });
  const t0 = Date.now();
  await page.goto(URL0, { waitUntil: 'domcontentloaded' });
  let cardsAt = null;
  try { await page.locator('[data-mission]').first().waitFor({ state: 'visible', timeout: 6000 }); cardsAt = Date.now() - t0; } catch {}
  await sleep(1500);
  return { ctx, page, errs, cardsAt };
}
const bad = (s) => BAD.filter((b) => s.includes(b));

const browser = await chromium.launch();
const SIZES = [[1366, 768, false], [1440, 900, false], [1920, 1080, false], [375, 812, true], [812, 375, true], [320, 568, true]];
for (const [w, h, touch] of SIZES) {
  const tag = `${w}x${h}`;
  const r = { };
  const { ctx, page, errs, cardsAt } = await open(browser, w, h, touch);
  r.cardsAt = cardsAt;
  const st0 = await page.evaluate(pageState);
  r.start = { sw: st0.sw, cw: st0.cw, sh: st0.sh, ih: st0.ih, off: st0.off, bad: bad(st0.txt + ' ' + st0.aria), nameCount: (st0.txt.match(/Stars Beside You/g) || []).length };
  r.startCardsInView = await page.evaluate(() => [...document.querySelectorAll('[data-mission]')].filter((e) => { const b = e.getBoundingClientRect(); return b.width > 0 && b.top >= 0 && b.bottom <= innerHeight + 1; }).length);
  if (w === 1440 || w === 375) {
    r.startText = st0.txt.slice(0, 1500);
    r.switches = await page.evaluate(() => [...document.querySelectorAll('[role=switch]')].map((e) => ({ label: e.innerText.trim() || e.getAttribute('aria-label'), checked: e.getAttribute('aria-checked') })));
    r.resets = await page.evaluate(() => [...document.querySelectorAll('.pane-reset')].map((e) => ({ name: e.getAttribute('aria-label'), text: e.innerText.trim(), w: Math.round(e.getBoundingClientRect().width) })));
    r.overGlobes = await page.evaluate(() => [...document.querySelectorAll('.pane')].map((p) => [...p.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() && e.getBoundingClientRect().width > 0 && !e.closest('[hidden]') && !e.closest('.globe .cesium-credit-textContainer')).map((e) => e.textContent.trim().slice(0, 40))));
    r.logo = await page.evaluate(() => ({ imgs: [...document.querySelectorAll('img')].filter((i) => /logo|brand/.test(i.src)).map((i) => ({ src: i.currentSrc.split('/').pop(), w: Math.round(i.getBoundingClientRect().width), h: Math.round(i.getBoundingClientRect().height), nw: i.naturalWidth, cls: i.className })), icon: [...document.querySelectorAll('link[rel~=icon]')].map((l) => l.href.split('/').pop()) }));
    r.credits = await page.evaluate(() => { const t = document.getElementById('credits-body')?.textContent || ''; return { blueMarble: /Blue Marble/i.test(t), lro: /LRO|Lunar Reconnaissance/i.test(t), cell: /1 degree|1°/.test(t), len: t.length }; });
  }
  await page.screenshot({ path: `${SHOTS}/${tag}_start.png` });
  if (touch) r.ovStart = await page.evaluate(overlapScan);
  // mobile options
  if (touch && w !== 320) {
    r.bar = await page.evaluate(() => { const t = document.querySelector('.topbar').getBoundingClientRect(); const o = document.getElementById('mf-options'); return { h: Math.round(t.height), opt: !!o, exp: o?.getAttribute('aria-expanded'), label: o?.getAttribute('aria-label') || o?.innerText }; });
    try {
      await page.click('#mf-options'); await sleep(600);
      r.barOpen = await page.evaluate(() => { const s = document.getElementById('mf-sheet'); const v = (e) => e && e.getBoundingClientRect().height > 0 && !e.closest('[hidden]'); return { exp: document.getElementById('mf-options').getAttribute('aria-expanded'), sw: [...document.querySelectorAll('[role=switch]')].filter(v).length, keys: v(document.getElementById('keys-button')), credits: v(document.getElementById('credits-button')) }; });
      await page.screenshot({ path: `${SHOTS}/${tag}_options.png` });
      await page.keyboard.press('Escape'); await sleep(500);
      r.barEsc = await page.evaluate(() => document.getElementById('mf-options').getAttribute('aria-expanded'));
    } catch (e) { r.barErr = String(e).slice(0, 120); }
  }
  const missions = ['1', '2', '3'];
  r.missions = [];
  for (const k of missions) {
    await page.keyboard.press('Escape'); await sleep(300); await page.keyboard.press('Escape'); await sleep(500);
    await page.keyboard.press(k); await sleep(1800);
    const sm = await page.evaluate(pageState);
    const m = { k, step: sm.step, sw: sm.sw, cw: sm.cw, sh: sm.sh, ih: sm.ih, off: sm.off, bad: bad(sm.txt + ' ' + sm.aria), analogs: await page.evaluate(() => [...document.querySelectorAll('.top5-btn')].filter((e) => e.getBoundingClientRect().width > 0).map((e) => { const b = e.getBoundingClientRect(); return { t: e.innerText.replace(/\s+/g, ' ').slice(0, 70), inView: b.top >= 0 && b.bottom <= innerHeight + 1 }; })) };
    if (w === 1440 || w === 375) m.text = sm.txt.slice(0, 1800);
    await page.screenshot({ path: `${SHOTS}/${tag}_m${k}.png` });
    if (touch) m.ov = await page.evaluate(overlapScan);
    if (touch && w === 375 || w === 812) m.globesOpen = await page.evaluate(() => ['earth-pane', 'moon-pane'].map((id) => Math.round(document.getElementById(id).getBoundingClientRect().height)));
    // open first analog
    try { if (touch) await page.locator('.top5-btn').first().click({ timeout: 3000 }); else await page.keyboard.press('1'); } catch (e) { m.clickErr = String(e).slice(0, 100); await page.keyboard.press('1'); }
    await sleep(4000);
    const sp = await page.evaluate(pageState);
    m.pair = { step: sp.step, sel: sp.sel, sw: sp.sw, cw: sp.cw, sh: sp.sh, ih: sp.ih, off: sp.off, bad: bad(sp.txt + ' ' + sp.aria) };
    m.cam = await page.evaluate(heights);
    m.card = await page.evaluate(cardText);
    m.more = await page.evaluate(() => { const p = document.getElementById('detail-panel'); return { details: [...p.querySelectorAll('details')].map((d) => ({ s: d.querySelector('summary')?.innerText, open: d.open })), btns: [...p.querySelectorAll('[aria-expanded]')].map((b) => b.innerText + ':' + b.getAttribute('aria-expanded')) }; });
    if (touch) m.pairOv = await page.evaluate(overlapScan);
    if (touch && (w === 375 || w === 812)) {
      m.handle = await page.evaluate(() => { const hd = document.getElementById('mf-handle'); return hd ? { exp: hd.getAttribute('aria-expanded'), text: hd.innerText, globes: ['earth-pane', 'moon-pane'].map((id) => Math.round(document.getElementById(id).getBoundingClientRect().height)) } : null; });
      try {
        await page.click('#mf-handle', { timeout: 2000 }); await sleep(800);
        m.handleFolded = await page.evaluate(() => ({ exp: document.getElementById('mf-handle').getAttribute('aria-expanded'), globes: ['earth-pane', 'moon-pane'].map((id) => Math.round(document.getElementById(id).getBoundingClientRect().height)) }));
        await page.screenshot({ path: `${SHOTS}/${tag}_m${k}_folded.png` });
        await page.click('#mf-handle', { timeout: 2000 }); await sleep(800);
        m.handleUnfolded = await page.evaluate(() => ({ exp: document.getElementById('mf-handle').getAttribute('aria-expanded'), globes: ['earth-pane', 'moon-pane'].map((id) => Math.round(document.getElementById(id).getBoundingClientRect().height)) }));
      } catch (e) { m.handleErr = String(e).slice(0, 100); }
    }
    await page.screenshot({ path: `${SHOTS}/${tag}_m${k}_pair.png` });
    r.missions.push(m);
  }
  // audio guide at 1440
  if (w === 1440 || w === 375) {
    try {
      await page.keyboard.press('Escape'); await sleep(300); await page.keyboard.press('Escape'); await sleep(500);
      if (touch) { await page.click('#mf-options'); await sleep(500); }
      const before = await page.evaluate(() => document.getElementById('guide-caption').innerText);
      await page.locator('[role=switch]', { hasText: 'Audio' }).click(); await sleep(2500);
      r.audio = await page.evaluate(() => { const c = document.getElementById('guide-caption'); const a = [...document.querySelectorAll('audio')]; const vis = c.getBoundingClientRect().height > 0; return { caption: c.innerText, captionH: Math.round(c.getBoundingClientRect().height), vis, audios: a.map((x) => ({ src: x.currentSrc.split('/').pop(), t: x.currentTime, paused: x.paused })) }; });
      r.audio.before = before;
      await sleep(1500);
      r.audio.t2 = await page.evaluate(() => [...document.querySelectorAll('audio')].map((x) => x.currentTime));
      await page.screenshot({ path: `${SHOTS}/${tag}_audio.png` });
    } catch (e) { r.audioErr = String(e).slice(0, 150); }
  }
  r.errs = errs.slice(0, 15);
  log(tag, r);
  await ctx.close();
}
// videos captions
try {
  const { ctx, page } = await open(browser, 1440, 900, false);
  await page.keyboard.press('1'); await sleep(1500); await page.keyboard.press('1'); await sleep(3000);
  const vb = page.locator('button', { hasText: /video|watch/i }).first();
  await vb.click({ timeout: 3000 }); await sleep(2000);
  const v = await page.evaluate(() => [...document.querySelectorAll('video')].map((x) => ({ tracks: [...x.textTracks].map((t) => t.kind + ':' + t.mode), ctrls: x.controls })));
  const capBtns = await page.evaluate(() => [...document.querySelectorAll('dialog[open] button, dialog[open] [role=switch]')].map((b) => b.innerText.trim() + '|' + (b.getAttribute('aria-pressed') || b.getAttribute('aria-checked') || '')));
  log('video', { v, capBtns });
  await page.screenshot({ path: `${SHOTS}/video.png` });
  await ctx.close();
} catch (e) { log('videoErr', String(e).slice(0, 150)); }
// no webgl
try {
  const b2 = await chromium.launch({ args: ['--disable-gpu', '--disable-3d-apis'] });
  const ctx = await b2.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const t0 = Date.now();
  await page.goto(URL0, { waitUntil: 'domcontentloaded' });
  let at = null; try { await page.locator('[data-mission]').first().waitFor({ state: 'visible', timeout: 4000 }); at = Date.now() - t0; } catch {}
  await sleep(1500);
  const r = await page.evaluate(() => ({ gl: !!document.createElement('canvas').getContext('webgl'), errPanel: document.querySelectorAll('.cesium-widget-errorPanel').length, msgs: [...document.querySelectorAll('.pane-status, .no-globes, [role=alert], .notice')].filter((e) => e.getBoundingClientRect().height > 0).map((e) => e.innerText.trim()).filter(Boolean) }));
  r.cardsAt = at;
  await page.keyboard.press('1'); await sleep(1500);
  r.list = await page.evaluate(() => [...document.querySelectorAll('.top5-btn')].map((e) => e.innerText.replace(/\s+/g, ' ').slice(0, 50)));
  r.loading = await page.evaluate(() => /Loading/.test(document.body.innerText));
  await page.keyboard.press('1'); await sleep(1500);
  r.pairStep = await page.evaluate(() => window.starsFlow?.state.step + ' ' + window.starsFlow?.state.selectedId);
  await page.keyboard.press('Escape'); await sleep(800);
  r.afterEsc = await page.evaluate(() => window.starsFlow?.state.step);
  await page.screenshot({ path: `${SHOTS}/nowebgl.png` });
  log('nowebgl', r);
  await b2.close();
} catch (e) { log('nowebglErr', String(e).slice(0, 150)); }
await browser.close();
