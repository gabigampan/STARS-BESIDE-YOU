#!/usr/bin/env node
// Regression checks for five production bugs (builds nothing: run `npm run build` first):
// A "Data, limits and credits" keeps data sections, the 19 audio-guide texts and the credits (with and without WebGL);
// B on a phone, Escape with the Options sheet open folds the sheet and stays on the mission step;
// C on a phone, the centre of each globe pane receives the touch (not the loading line);
// D the Cesium credit logo link has a hit area of at least 44x44;
// E the five analog buttons are at least 8 px apart and fit without page scroll at 1366x768 and 1440x900.
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
const ready = (page) => page.waitForFunction(() => window.starsFlow?.hasData(), null, { timeout: 30_000 });
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
{
  const browser = await chromium.launch({ args: ['--disable-gpu', '--disable-3d-apis'] });
  await checkDialog(browser, 'no WebGL');
  await browser.close();
}

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
// ---------- A with WebGL ----------
await checkDialog(browser, 'WebGL');

// ---------- B, C phone ----------
{
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
for (const [w, h] of [[1366, 768], [1440, 900]]) {
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
        return { w: Math.round(b.width), h: Math.round(b.height), imgH: img ? Math.round(img.height) : 0 };
      });
      const lastBtn = btns.length ? btns[btns.length - 1].getBoundingClientRect().bottom : 1e9;
      return { n: btns.length, gaps, last: Math.round(last), lastBtn: Math.round(lastBtn), vh: innerHeight, pageScroll: document.documentElement.scrollHeight > innerHeight + 1, logo };
    });
    check(r.n === 5 && r.gaps.every((g) => g >= 8), `E ${w}x${h} ${m}: ${r.n} analogs, gaps ${r.gaps.join(',')} px (want >= 8)`);
    check(r.lastBtn <= r.vh && !r.pageScroll, `E ${w}x${h} ${m}: fifth analog bottom ${r.lastBtn} <= ${r.vh}, no page scroll (${!r.pageScroll}); panel's last element bottom ${r.last}`);
    check(r.logo.length > 0 && r.logo.every((l) => l.w >= 44 && l.h >= 44), `D ${w}x${h} ${m}: credit logo links ${r.logo.map((l) => `${l.w}x${l.h} (logo ${l.imgH} px)`).join('; ')}`);
  }
  await ctx.close();
}
await browser.close();
await srv.close?.();
console.log(failed ? `${failed} check(s) failed` : 'all regression checks passed');
process.exit(failed ? 1 : 0);
