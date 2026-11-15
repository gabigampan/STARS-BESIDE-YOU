#!/usr/bin/env node
// Regression checks for five production bugs (builds nothing: run `npm run build` first):
// A "Data, limits and credits" keeps data sections, the 19 audio-guide texts and the credits (with and without WebGL);
// B on a phone, Escape with the Options sheet open folds the sheet and stays on the mission step;
// C on a phone, the centre of each globe pane receives the touch (not the loading line);
// D the Cesium credit logo link has a hit area of at least 44x44;
// E for every mission at 1366x768, 1440x900 and 1920x1080: the heading, the five analog buttons and the three folded rows
//   fit (last row bottom <= viewport - 8) with no page or inner scroll; buttons >= 44 px high, >= 8 px apart; text >= 14 px;
//   no element showing a digit is cut (scrollWidth > clientWidth), except the twin's words, which may end in an ellipsis.
// Exit code 1 when anything fails.

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
const check = (ok, msg) => {
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${msg}`);
  if (!ok) failed++;
};
const srv = await serve(DIST);
// REGRESS_ONLY=F (or e.g. AE) runs only the named check letters; unset runs all
const ONLY = (process.env.REGRESS_ONLY || 'ABCDEF').toUpperCase();
const runs = (letters) => [...letters].some((l) => ONLY.includes(l));
const ready = (page) => page.waitForFunction(() => window.starsFlow?.hasData(), null, { timeout: 120_000 });
const waitStep = (page, s) => page.waitForFunction((x) => window.starsFlow?.state.step === x, s, { timeout: 15_000 }).then(() => true, () => false);
const missionIds = (page) => page.evaluate(() => [...document.querySelectorAll('#intro .choice')].map((c) => c.dataset.mission));

const dialogShape = (page) =>
  page.evaluate(() => {
    const b = document.getElementById('credits-body');
    const kids = [...b.children].map((c) => c.className);
    const pos = (cls) => kids.findIndex((k) => k.split(' ').includes(cls));
    return {
      kids,
      dataSections: b.querySelector('.data-sections')?.children.length ?? 0,
      guideTexts: b.querySelectorAll('.guide-texts p').length,
      creditLines: b.querySelectorAll('.credit-line').length,
      order: [pos('data-sections'), pos('credits-own'), pos('guide-texts')],
    };
  });

async function checkDialog(browser, tag) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(srv.base);
  await ready(page);
  await page.waitForFunction(() => document.querySelectorAll('#credits-body .guide-texts p').length > 0, null, { timeout: 15_000 }).catch(() => {});
  await page.waitForTimeout(1500); // late setup calls (credits after imagery) have run
  const d = await dialogShape(page);
  console.log(`     ${tag}: children ${JSON.stringify(d.kids)}`);
  check(d.dataSections > 0, `A ${tag}: .data-sections has ${d.dataSections} children`);
  check(d.guideTexts === 19, `A ${tag}: ${d.guideTexts} audio-guide texts (want 19)`);
  check(d.creditLines >= 9, `A ${tag}: ${d.creditLines} credit lines`);
  const [ds, cr, gt] = d.order;
  check(ds >= 0 && cr > ds && gt > cr, `A ${tag}: order data sections, credits, guide texts (${d.order.join(',')})`);
  await ctx.close();
}

// ---------- A without WebGL ----------
if (runs('A')) {
  const browser = await chromium.launch({ args: ['--disable-gpu', '--disable-3d-apis'] });
  await checkDialog(browser, 'no WebGL');
  await browser.close();
}

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
// ---------- A with WebGL ----------
if (runs('A')) await checkDialog(browser, 'WebGL');

// ---------- B, C phone ----------
if (runs('BC')) {
  const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.goto(srv.base);
  await ready(page);
  const [m] = await missionIds(page);
  await page.click(`#intro .choice[data-mission="${m}"]`);
  await waitStep(page, 'pick');
  await page.waitForTimeout(500);
  const centres = () =>
    page.evaluate(() =>
      ['earth-globe', 'moon-globe'].map((id) => {
        const g = document.getElementById(id);
        const r = g.getBoundingClientRect();
        const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        const status = !!top?.closest('.pane-status');
        return { id, status, el: top ? `${top.tagName.toLowerCase()}.${top.className}` : 'none', canvasOrCesium: !!top && (top.tagName === 'CANVAS' || !!top.closest('.cesium-widget, .cesium-viewer')) };
      }),
    );
  // force the loading line on (as while imagery loads) to test its touch behaviour
  const forceStatus = () => page.evaluate(() => document.querySelectorAll('.pane-status').forEach((s) => { s.hidden = false; s.dataset.regress = '1'; }));
  for (const [step, go] of [['pick', null], ['pair', async () => { await page.locator('.top5-btn').first().click(); await waitStep(page, 'pair'); await page.waitForTimeout(500); }]]) {
    if (go) await go();
    await forceStatus();
    const c = await centres();
    for (const x of c) check(!x.status, `C 375x812 ${step}: centre of #${x.id} is ${x.el}${x.canvasOrCesium ? ' (globe)' : ''}, not the loading line`);
  }
  await page.keyboard.press('Escape');
  await waitStep(page, 'pick');
  check((await page.evaluate(() => window.starsFlow.state.step)) === 'pick', 'B setup: back on the mission step');
  const opt = page.locator('#mf-options');
  await opt.click();
  await page.waitForFunction(() => document.body.classList.contains('mf-open'), null, { timeout: 5000 }).catch(() => {});
  const opened = await page.evaluate(() => document.body.classList.contains('mf-open'));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);
  const after = await page.evaluate(() => ({ open: document.body.classList.contains('mf-open'), step: window.starsFlow.state.step }));
  check(opened && !after.open && after.step === 'pick', `B 375x812: Options opened ${opened}, after Escape folded ${!after.open}, step ${after.step}`);
  await ctx.close();
}

// ---------- D, E desktop ----------
for (const [w, h] of runs('DE') ? [[1366, 768], [1440, 900], [1920, 1080]] : []) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h } });
  const page = await ctx.newPage();
  await page.goto(srv.base);
  await ready(page);
  for (const m of await missionIds(page)) {
    await page.evaluate(() => window.scrollTo(0, 0));
    if ((await page.evaluate(() => window.starsFlow.state.step)) !== 'choose') {
      await page.keyboard.press('Escape');
      await waitStep(page, 'choose');
    }
    await page.click(`#intro .choice[data-mission="${m}"]`);
    await waitStep(page, 'pick');
    await page.waitForTimeout(600);
    const r = await page.evaluate(() => {
      const btns = [...document.querySelectorAll('.top5-btn')].filter((b) => b.getBoundingClientRect().height > 0);
      const gaps = btns.slice(1).map((b, i) => Math.round((b.getBoundingClientRect().top - btns[i].getBoundingClientRect().bottom) * 10) / 10);
      const list = document.querySelector('.top5-list');
      const panel = list?.closest('.panel, section, aside') ?? list;
      const last = [...panel.querySelectorAll('*')].filter((e) => e.getBoundingClientRect().height > 0).reduce((a, e) => Math.max(a, e.getBoundingClientRect().bottom), 0);
      const logo = [...document.querySelectorAll('.cesium-credit-logoContainer a')].map((a) => {
        const b = a.getBoundingClientRect();
        const img = a.querySelector('img')?.getBoundingClientRect();
        // real hit area: from the box centre, probe 1 px steps with elementFromPoint (a pseudo-element hits as its link)
        const cx = Math.round(b.left + b.width / 2), cy = Math.round(b.top + b.height / 2);
        const hits = (x, y) => { const e = document.elementFromPoint(x, y); return !!e && (e === a || a.contains(e)); };
        const reach = (dx, dy) => { let k = 0; while (k < 400 && hits(cx + (k + 1) * dx, cy + (k + 1) * dy)) k++; return k; };
        const c = hits(cx, cy);
        const hw = c ? reach(-1, 0) + reach(1, 0) + 1 : 0, hh = c ? reach(0, -1) + reach(0, 1) + 1 : 0;
        return { w: Math.round(b.width), h: Math.round(b.height), hw, hh, imgH: img ? Math.round(img.height) : 0 };
      });
      const lastBtn = btns.length ? btns[btns.length - 1].getBoundingClientRect().bottom : 1e9;
      const mp = document.getElementById('mission-panel');
      const R = (e) => e.getBoundingClientRect();
      const rows = [...mp.querySelectorAll('.ranking-box > summary, .weights > summary, .method-box > summary')];
      const lastRow = rows.length === 3 ? Math.round(Math.max(...rows.map((s) => R(s).bottom))) : 1e9;
      const title = mp.querySelector('.panel-title');
      const scrollers = [document.scrollingElement, mp, ...mp.querySelectorAll('*')].filter((e) => e.scrollHeight > e.clientHeight + 1 && (e === document.scrollingElement || getComputedStyle(e).overflowY !== 'visible') && !e.classList.contains('sr-only') && !e.classList.contains('top5-region'));
      const texts = [...mp.querySelectorAll('.top5 *, .panel-title, summary')].filter((e) => R(e).height > 2 && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) && !e.closest('.sr-only'));
      const minFont = Math.min(...texts.map((e) => parseFloat(getComputedStyle(e).fontSize)));
      const cut = [...mp.querySelectorAll('*')].filter((e) => R(e).height > 2 && e.scrollWidth > e.clientWidth + 1 && /\d/.test(e.textContent) && !e.classList.contains('sr-only') && !e.classList.contains('top5-region') && !(e.classList.contains('top5-twin-name') && !/\d/.test([...e.childNodes].filter((n) => !(n.classList && n.classList.contains('top5-region'))).map((n) => n.textContent).join('')))).map((e) => e.className);
      const heights = btns.map((b) => Math.round(R(b).height));
      const twinCut = btns.map((b, i) => [i + 1, b.querySelector('.top5-twin-name')]).filter(([, e]) => e && e.scrollWidth > e.clientWidth).map(([i, e]) => `${i}:${e.firstChild?.textContent}`);
      const placeCut = btns.map((b, i) => [i + 1, b.querySelector('.top5-place')]).filter(([, e]) => e && e.scrollWidth > e.clientWidth).map(([i]) => i);
      return { twinCut, placeCut, lastRow, titleTop: title ? Math.round(R(title).top) : -1, scrollers: scrollers.map((e) => e.id || e.className || e.tagName), minFont, cut, heights, n: btns.length, gaps, last: Math.round(last), lastBtn: Math.round(lastBtn), vh: innerHeight, pageScroll: document.documentElement.scrollHeight > innerHeight + 1, logo };
    });
    check(r.n === 5 && r.gaps.every((g) => g >= 8), `E ${w}x${h} ${m}: ${r.n} analogs, gaps ${r.gaps.join(',')} px (want >= 8)`);
    check(r.lastBtn <= r.vh && !r.pageScroll, `E ${w}x${h} ${m}: fifth analog bottom ${r.lastBtn} <= ${r.vh}, no page scroll (${!r.pageScroll}); panel's last element bottom ${r.last}`);
    check(r.titleTop >= 0 && r.lastRow <= r.vh - 8 && r.scrollers.length === 0, `E ${w}x${h} ${m}: heading top ${r.titleTop}, last folded row bottom ${r.lastRow} <= ${r.vh - 8}, scrolling boxes [${r.scrollers.join(',')}]`);
    check(r.heights.every((x) => x >= 44) && r.minFont >= 14 && r.cut.length === 0, `E ${w}x${h} ${m}: button heights ${r.heights.join(',')} (>= 44), smallest text ${r.minFont} px (>= 14), cut numbers [${r.cut.join(',')}]`);
    check(r.twinCut.length === 0, `E ${w}x${h} ${m}: visible twin line of the five not truncated (cut: [${r.twinCut.join('; ')}]); places cut [${r.placeCut.join(',')}]`);
    check(r.logo.length > 0 && r.logo.every((l) => l.hw >= 44 && l.hh >= 44), `D ${w}x${h} ${m}: ${r.logo.map((l) => `credit logo painted ${l.w}x${l.h}, hit area ${l.hw}x${l.hh} (logo ${l.imgH} px)`).join('; ')}`);
  }
  await ctx.close();
}
// ---------- F: no two visible touch targets closer than 8 px (same rule as tests/flow.mjs) ----------
// start, mission and pair steps; phones with the sheet unfolded and folded; desktop with "Full ranking" open
const tightPairs = (page) =>
  page.evaluate(() => {
    const vis = (el) => el && el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
    const targets = [...document.querySelectorAll('button, a[href], input:not([type=radio]), select, summary, label.seg')].filter((el) => {
      if (!vis(el) || el.disabled || el.closest('.sr-only')) return false;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) return false;
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) return false;
      const top = document.elementFromPoint(cx, cy);
      return !!top && (el.contains(top) || top.contains(el) || top.closest('label') === el);
    });
    // visible box: the target's box intersected with every clipping or scrolling ancestor
    // (overflow other than visible, measured at its padding box) and with the viewport
    const visibleBox = (el) => {
      const r = el.getBoundingClientRect();
      let L = Math.max(r.left, 0), T = Math.max(r.top, 0), Rr = Math.min(r.right, innerWidth), B = Math.min(r.bottom, innerHeight);
      for (let p = el.parentElement; p && p !== document.documentElement; p = p.parentElement) {
        const cs = getComputedStyle(p);
        const cx = cs.overflowX !== 'visible', cy = cs.overflowY !== 'visible';
        if (!cx && !cy) continue;
        const pr = p.getBoundingClientRect();
        const pl = pr.left + p.clientLeft, pt = pr.top + p.clientTop;
        if (cx) { L = Math.max(L, pl); Rr = Math.min(Rr, pl + p.clientWidth); }
        if (cy) { T = Math.max(T, pt); B = Math.min(B, pt + p.clientHeight); }
      }
      return Rr - L >= 1 && B - T >= 1 ? { left: L, top: T, right: Rr, bottom: B } : null;
    };
    const nameOf = (el) => (el.id ? '#' + el.id + ' ' : '') + (el.textContent || el.getAttribute('aria-label') || el.tagName || '').trim().slice(0, 25);
    const out = [];
    const rs = targets.map((el) => [el, visibleBox(el)]).filter(([, r]) => r);
    for (let i = 0; i < rs.length; i++)
      for (let j = i + 1; j < rs.length; j++) {
        const [a, ra] = rs[i], [b, rb] = rs[j];
        if (a.contains(b) || b.contains(a)) continue;
        const d = Math.max(Math.max(0, rb.left - ra.right, ra.left - rb.right), Math.max(0, rb.top - ra.bottom, ra.top - rb.bottom));
        if (d < 8 - 0.5) out.push(`${nameOf(a)} | ${nameOf(b)} (${d.toFixed(1)} px)`);
      }
    return out;
  });
// smallest gap between any visible element matching selA and any matching selB (null when none is visible)
const gapOf = (page, selA, selB) =>
  page.evaluate(([x, y]) => {
    const shown = (s) => [...document.querySelectorAll(s)].filter((e) => e.getClientRects().length && e.checkVisibility({ checkVisibilityCSS: true }));
    let best = null;
    for (const a of shown(x))
      for (const b of shown(y)) {
        const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
        const d = Math.round(Math.max(Math.max(0, rb.left - ra.right, ra.left - rb.right), Math.max(0, rb.top - ra.bottom, ra.top - rb.bottom)) * 10) / 10;
        best = best == null ? d : Math.min(best, d);
      }
    return best;
  }, [selA, selB]);
for (const [w, h] of runs('F') ? [[1440, 900], [1366, 768], [375, 812], [812, 375], [667, 375]] : []) {
  const phone = w < 900;
  const ctx = await browser.newContext(phone ? { viewport: { width: w, height: h }, hasTouch: true, isMobile: true, deviceScaleFactor: 2 } : { viewport: { width: w, height: h } });
  const page = await ctx.newPage();
  await page.goto(srv.base);
  await ready(page);
  await page.waitForTimeout(800);
  const sweep = async (view) => {
    const t = await tightPairs(page);
    check(t.length === 0, `F ${w}x${h} ${view}: no targets closer than 8 px${t.length ? ': ' + t.slice(0, 6).join('; ') : ''}`);
  };
  const folds = async (view) => {
    await sweep(view + (phone ? ' (sheet unfolded)' : ''));
    if (!phone || !(await page.locator('#mf-handle').isVisible())) return;
    const logoGap = await gapOf(page, '.cesium-credit-logoContainer a', '#mf-handle');
    if (logoGap != null) check(logoGap >= 8, `F ${w}x${h} ${view}: credit logo to sheet handle ${logoGap} px (want >= 8)`);
    await page.click('#mf-handle');
    await page.waitForTimeout(400);
    await sweep(view + ' (sheet folded)');
    const g2 = await gapOf(page, '.cesium-credit-logoContainer a', '#mf-handle');
    if (g2 != null) check(g2 >= 8, `F ${w}x${h} ${view} folded: credit logo to sheet handle ${g2} px (want >= 8)`);
    await page.click('#mf-handle');
    await page.waitForTimeout(400);
  };
  await sweep('start');
  const [m] = await missionIds(page);
  await page.click(`#intro .choice[data-mission="${m}"]`);
  await waitStep(page, 'pick');
  await page.waitForTimeout(600);
  await folds('mission');
  // FAULT 2: "Full ranking" unfolded, "Show 50 more" against the next folded row ("Set what matters most")
  const opened = await page.evaluate(() => {
    const d = document.querySelector('#mission-panel .ranking-box');
    if (!d) return false;
    d.open = true;
    return true;
  });
  if (opened) {
    await page.waitForTimeout(300);
    await page.evaluate(() => document.getElementById('show-more')?.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(200);
    const g = await gapOf(page, '#show-more', '#mission-panel .weights > summary');
    check(g != null && g >= 8, `F ${w}x${h} mission, full ranking open: "Show more" to "Set what matters most" ${g} px (want >= 8)`);
    await sweep('mission, full ranking open');
    await page.evaluate(() => { document.querySelector('#mission-panel .ranking-box').open = false; });
    await page.waitForTimeout(300);
  }
  await page.locator('.top5-btn').first().click();
  await waitStep(page, 'pair');
  await page.waitForTimeout(800);
  await folds('pair');
  await ctx.close();
}

await browser.close();
await srv.close?.();
console.log(failed ? `${failed} check(s) failed` : 'all regression checks passed');
process.exit(failed ? 1 : 0);
