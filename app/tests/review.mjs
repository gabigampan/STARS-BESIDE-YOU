#!/usr/bin/env node
// Regression test for the faults found by the UX and correctness reviews of 2026-11-15 (one check,
// or a group of checks, per fault). Runs the built dist/ in headless Chromium against BOTH bundle
// variants (the shipped zone_twin bundle and a temporary copy of the no-twin repo_global_mean
// bundle served at /data/v2/) at 1440x900 and 375x812.
// Usage: node tests/review.mjs [--no-build] [--only=twin|notwin] [--sizes=desktop,phone]
// Screenshots: $SHOTS_DIR (default below).

import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { serve } from './lib/serve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(APP, 'dist');
const SCRATCH = '/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars';
const SHOTS = process.env.SHOTS_DIR ?? join(SCRATCH, 'shots-final');
const OTHER = process.env.OTHER_BUNDLE ?? join(SCRATCH, 'bundle_global_mean');
const arg = (k) => process.argv.find((a) => a.startsWith(`--${k}=`))?.slice(k.length + 3);
const ONLY = arg('only');
const SIZES = (arg('sizes') ?? 'desktop,phone').split(',');
const SIZE = { desktop: { w: 1440, h: 900 }, phone: { w: 375, h: 812 } };

const SNAKE = /\b[a-z]+_[a-z0-9]+(?:_[a-z0-9]+)*\b/;
const SPANISH = /\b(regolito|roca|arena|suelo|hielo|agua|continuo|discontinuo|esporadico|ninguno)\b/i;
const INTERVAL = /\binf\b|\[[-\d.]+, [-\d.inf]+\]/;
const DEV = /mission_scoring|\.py\b|docs\/|require_present|\w >= \d|the repository's rule/;

const failures = [];
const check = (c, m) => {
  if (c) console.log(`ok   ${m}`);
  else {
    failures.push(m);
    console.log(`FAIL ${m}`);
  }
};

if (!process.argv.includes('--no-build')) {
  const r = spawnSync('npm', ['run', 'build'], { cwd: APP, env: { ...process.env, VITE_USE_ION: '' }, encoding: 'utf8' });
  if (r.status !== 0) {
    console.log(r.stdout, r.stderr);
    process.exit(1);
  }
}
mkdirSync(SHOTS, { recursive: true });

/** The rendered text of an element, leaving out the engine's exact reason, closed disclosures and Spanish originals. */
function visibleText(sel) {
  const root = document.querySelector(sel);
  if (!root) return '';
  // the bundle's verbatim no-twin sentence is checked for equality separately
  const hide = [...root.querySelectorAll('.reason-exact, [lang="es"], .tech-notes, [data-verbatim]')];
  const prev = hide.map((e) => e.style.display);
  hide.forEach((e) => (e.style.display = 'none'));
  const t = root.innerText;
  hide.forEach((e, i) => (e.style.display = prev[i]));
  return t;
}

async function run(browser, srv, variant, sizeKey) {
  const tag = `review-${variant}-${sizeKey}`;
  const { w, h: hgt } = SIZE[sizeKey];
  const ctx = await browser.newContext({ viewport: { width: w, height: hgt }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  const ev = (fn, ...a) => page.evaluate(fn, ...a);
  const text = (sel) => ev(visibleText, sel);
  const shot = (name) => page.screenshot({ path: join(SHOTS, `${tag}-${name}.png`) });

  await page.goto(srv.base);
  await page.waitForFunction(() => window.starsFlow?.hasData(), null, { timeout: 120_000 });
  await page.waitForFunction(() => document.getElementById('loading').hidden, null, { timeout: 300_000 });
  const twins = await ev(() => window.starsFlow.store.hasTwins());
  check(twins === (variant === 'twin'), `${tag}: bundle variant read from the bundle (twins ${twins})`);

  // PURPOSE wording (correctness minor): relative similarity stated on the first screen
  const purpose = await ev(() => document.querySelector('#intro .intro-title')?.textContent ?? '');
  check(/own scale/.test(purpose), `${tag}: first sentence qualifies the similarity: "${purpose}"`);

  // Place names toggle: state in words, not by colour alone (UX red alert)
  if (sizeKey === 'phone') {
    check(await ev(() => document.getElementById('view-toggle').checkVisibility()), `${tag}: "View" button offers Sunlight and Place names on a narrow screen`);
    await page.click('#view-toggle');
    check(await ev(() => document.getElementById('sunlight').checkVisibility() && document.getElementById('labels-toggle').checkVisibility()), `${tag}: Sunlight and Place names visible after "View"`);
  }
  const t0 = await ev(() => document.querySelector('#labels-toggle').textContent.trim());
  await page.click('#labels-toggle');
  const t1 = await ev(() => document.querySelector('#labels-toggle').textContent.trim());
  await page.click('#labels-toggle');
  check(t0 === 'Place names: on' && t1 === 'Place names: off', `${tag}: Place names state in words ("${t0}" / "${t1}")`);
  if (sizeKey === 'phone') await page.click('#view-toggle');

  // Data and limits: no developer references in the reading flow; no twin limitation without twins
  await page.click('#credits-button');
  await page.waitForFunction(() => document.getElementById('credits-dialog').open);
  const dlg = await text('#credits-body .data-sections');
  check(!DEV.test(dlg), `${tag}: dialog reading flow free of file, function and code wording${DEV.test(dlg) ? ': ' + dlg.match(DEV)[0] : ''}`);
  check(!SPANISH.test(dlg.replace(/Spanish/g, '')), `${tag}: dialog has no Spanish shown outside the closed original note${SPANISH.test(dlg) ? ': ' + dlg.match(SPANISH)[0] : ''}`);
  check(!INTERVAL.test(dlg), `${tag}: dialog limits in words, no interval notation`);
  const solarLim = await ev(() => window.starsFlow.store.similarity.texts?.solar_limitation?.text ?? '');
  if (!twins) check(!dlg.includes(solarLim.slice(0, 60)), `${tag}: no-twin dialog does not state the twin limitation as fact`);
  await shot('dialog');
  await page.keyboard.press('Escape');

  const missions = await ev(() => window.starsFlow.store.offeredMissions().map((m) => m.id));
  for (const mid of missions) {
    // choose by click; keyboard focus must land on the first ranked place (UX major)
    await page.click(`#intro .choice[data-mission="${mid}"]`);
    await page.waitForFunction(() => document.body.dataset.step === 'pick' && document.querySelector('#mission-panel .rank-row'), null, { timeout: 120_000 });
    await page.waitForTimeout(300);
    check(await ev(() => document.activeElement?.classList.contains('rank-row')), `${tag} ${mid}: focus on the first ranked place after choosing`);
    const rows = await ev(() => [...document.querySelectorAll('#mission-panel .rank-row')].slice(0, 16).map((r) => ({ where: r.querySelector('.rank-where')?.textContent ?? '', label: r.getAttribute('aria-label') })));
    check(rows.every((r) => /° [NS], .*° [EW]/.test(r.where)), `${tag} ${mid}: each row shows the coordinates ("${rows[0].where}")`);
    if (twins) check(rows.every((r) => /Moon: /.test(r.where) && /Moon: /.test(r.label)), `${tag} ${mid}: each row names its lunar twin`);
    else check(rows.every((r) => !/Moon: /.test(r.where)), `${tag} ${mid}: no twin named without twins`);
    const panel = await text('#mission-panel');
    check(!SNAKE.test(panel) && !INTERVAL.test(panel), `${tag} ${mid}: mission panel free of engine keys and interval notation${SNAKE.test(panel) ? ': ' + panel.match(SNAKE)[0] : INTERVAL.test(panel) ? ': ' + panel.match(INTERVAL)[0] : ''}`);
    await ev(() => document.querySelectorAll('#mission-panel details').forEach((d) => (d.open = true)));
    const open = await text('#mission-panel');
    check(!SNAKE.test(open) && !DEV.test(open), `${tag} ${mid}: funnel and weights in plain words${SNAKE.test(open) ? ': ' + open.match(SNAKE)[0] : DEV.test(open) ? ': ' + open.match(DEV)[0] : ''}`);
    await ev(() => document.querySelectorAll('#mission-panel details').forEach((d) => (d.open = false)));
    const earthNote = await ev(() => document.getElementById('earth-rule')?.textContent ?? '');
    check(/^Markers: /.test(earthNote), `${tag} ${mid}: Earth markers explained ("${earthNote.slice(0, 60)}...")`);
    if (sizeKey === 'desktop') {
      const inView = await ev(() => [...document.querySelectorAll('#mission-panel .rank-row')].filter((r) => { const b = r.getBoundingClientRect(); return b.top >= 0 && b.bottom <= innerHeight; }).length);
      check(inView >= 3, `${tag} ${mid}: ${inView} ranked rows in the first view at 1440x900`);
    }
    await ev(() => document.querySelector('#mission-panel').scrollTop = 0);
    await shot(`${mid}-pick`);

    // the top pair: headline strip, plain text, relief baseline, rank format
    const top = await ev(() => window.starsFlow.ranking()[0].id);
    await ev((id) => window.starsFlow.select(id), top);
    await page.waitForFunction((id) => document.getElementById('detail-panel').dataset.cell === String(id) && document.querySelector('#detail-panel .result'), top, { timeout: 90_000 });
    const d = await text('#detail-panel');
    check(await ev(() => !!document.querySelector('#detail-panel .pair-strip [data-fig="final"]')), `${tag} ${mid}: headline strip with the pair and the three scores`);
    check(!SPANISH.test(d), `${tag} ${mid}: comparison panel in English${SPANISH.test(d) ? ': ' + d.match(SPANISH)[0] : ''}`);
    check(!SNAKE.test(d) && !INTERVAL.test(d), `${tag} ${mid}: comparison panel free of engine keys and interval notation${SNAKE.test(d) ? ': ' + d.match(SNAKE)[0] : INTERVAL.test(d) ? ': ' + d.match(INTERVAL)[0] : ''}`);
    check(!/\. shown|the repository's rule/.test(d), `${tag} ${mid}: similarity notes wording`);
    check(!/x 0 km/.test(d), `${tag} ${mid}: no "0 km" cell size`);
    if (mid === 'rover') check(/True baseline: /.test(d), `${tag} ${mid}: relief rows carry their true baseline`);
    await shot(`${mid}-compare`);

    // the video plays and takes the focus (UX major)
    if (await ev(() => !!document.getElementById('start-mission'))) {
      await page.click('#start-mission');
      await page.waitForFunction(() => document.querySelector('.video-dialog')?.open, null, { timeout: 10_000 }).catch(() => undefined);
      await page.waitForTimeout(1500);
      const v = await ev(() => { const x = document.querySelector('.video-dialog video'); return { playing: x && !x.paused && x.currentTime > 0, focus: document.activeElement?.tagName }; });
      check(v.playing && v.focus === 'VIDEO', `${tag} ${mid}: "Start the mission" plays the film with focus on the player (playing ${v.playing}, focus ${v.focus})`);
      await shot(`${mid}-video`);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }

    // a cell eliminated here but ranked in another mission, opened from that mission (loader < 100 ms)
    const pairOther = await ev((m) => {
      const st = window.starsFlow.store;
      for (const x of st.offeredMissions()) {
        if (x.id === m) continue;
        const p = st.ranked(x.id).slice(0, 400).find((r) => !st.outcome(r.id, m).pass);
        if (p) return { id: p.id, from: x.id };
      }
      return null;
    }, mid);
    if (pairOther) {
      await ev(({ id, from }) => window.starsFlow.select(id, from), pairOther);
      await page.waitForFunction(({ id, from }) => { const d = document.getElementById('detail-panel'); return d.dataset.cell === String(id) && d.dataset.mission === from && d.querySelector('.result'); }, pairOther, { timeout: 90_000 });
      await ev(() => {
        window.__t = { t0: null, t1: null };
        new MutationObserver((_, o) => { window.__t.t1 = performance.now(); o.disconnect(); }).observe(document.getElementById('detail-panel'), { childList: true, subtree: true });
      });
      const name = await ev((m) => { const b = [...document.querySelectorAll('#detail-panel .others li')].find((li) => li.dataset.mission === m)?.querySelector('button'); window.__t.t0 = performance.now(); b?.click(); return !!b; }, mid);
      check(name, `${tag} ${mid}: "Open in" offered from the other mission`);
      await page.waitForFunction(() => window.__t.t1 != null, null, { timeout: 5000 }).catch(() => undefined);
      const ms = await ev(() => (window.__t.t1 ?? Infinity) - window.__t.t0);
      check(ms < 100, `${tag} ${mid}: "Open in" shows a response in ${ms.toFixed(1)} ms`);
      await page.waitForFunction(({ id, m }) => { const d = document.getElementById('detail-panel'); return d.dataset.cell === String(id) && d.dataset.mission === m && d.querySelector('.result'); }, { id: pairOther.id, m: mid }, { timeout: 90_000 });
      const e = await text('#detail-panel');
      const reason = await ev(() => document.querySelector('#detail-panel .result .reason')?.textContent ?? '');
      check(/minimum|maximum|excludes|no data/.test(reason) && !SNAKE.test(reason) && !INTERVAL.test(reason), `${tag} ${mid}: elimination reason in words ("${reason}")`);
      check(!SNAKE.test(e) && !INTERVAL.test(e) && !SPANISH.test(e), `${tag} ${mid}: eliminated-cell panel free of engine keys, intervals and Spanish${SNAKE.test(e) ? ': ' + e.match(SNAKE)[0] : INTERVAL.test(e) ? ': ' + e.match(INTERVAL)[0] : SPANISH.test(e) ? ': ' + e.match(SPANISH)[0] : ''}`);
      const lv = await ev(() => [...document.querySelectorAll('#detail-panel tr')].filter((tr) => tr.querySelector('.val')?.textContent === 'no data').every((tr) => /no data/.test(tr.querySelector('.val').parentElement.querySelector('.sub')?.textContent ?? '')));
      check(lv, `${tag} ${mid}: a missing value carries the level "no data"`);
      await shot(`${mid}-eliminated`);
    }

    // a pair without temperature: the mark; the twin sentence only with twins (correctness major)
    const mt = await ev(() => window.starsFlow.ranking().find((r) => r.missingTemp)?.id ?? null);
    if (mt != null) {
      await ev((id) => window.starsFlow.select(id), mt);
      await page.waitForFunction((id) => document.getElementById('detail-panel').dataset.cell === String(id) && document.querySelector('#detail-panel .result'), mt, { timeout: 90_000 });
      const mtx = await text('#detail-panel');
      const mark = await ev(() => window.starsFlow.store.text('missing_temperature_mark'));
      check(mtx.includes(mark), `${tag} ${mid}: missing-temperature mark in the panel`);
      check(twins || !/This twin was chosen/.test(mtx), `${tag} ${mid}: no twin sentence without twins`);
      check(/Rank \d{1,3}(,\d{3})* of /.test(mtx), `${tag} ${mid}: rank and total formatted alike`);
    }

    if (!twins) {
      const nt = await ev(() => ({ shown: document.querySelector('#detail-panel .no-twin')?.textContent ?? document.getElementById('moon-rule')?.textContent ?? '', bundle: window.starsFlow.noTwinText() }));
      const stored = await ev((m) => window.starsFlow.store.mission(m).similarity.no_twin_reason ?? window.starsFlow.store.similarity.no_twin_reason, mid);
      check(stored && nt.bundle === stored, `${tag} ${mid}: the no-twin statement is the bundle's sentence`);
    }

    // all weights zero: say so, do not claim nothing passes (correctness minor)
    await ev(() => window.starsFlow.backToRanking());
    await page.waitForFunction(() => document.body.dataset.step === 'pick');
    const n = await ev(() => window.starsFlow.mission().weighted_variables.length);
    await ev((k) => window.starsFlow.setWeights(new Array(k).fill(0), null), n);
    await page.waitForFunction(() => !!document.querySelector('#mission-panel [data-empty="zero-weights"]') || !!document.querySelector('#mission-panel .empty'), null, { timeout: 60_000 });
    check(await ev(() => !!document.querySelector('#mission-panel [data-empty="zero-weights"]')), `${tag} ${mid}: all-zero weights explained, not "no place passes"`);
    await ev(() => window.starsFlow.resetWeights());
    await ev(() => window.starsFlow.changeMission());
    await page.waitForFunction(() => document.body.dataset.step === 'choose');
  }
  check(errors.length === 0, `${tag}: no page errors${errors.length ? ': ' + errors[0] : ''}`);
  await ctx.close();
}

async function errorsRun(browser, srv, variant) {
  // forced failure: no HTTP status on screen, the step count stays (UX minor)
  const ctx = await browser.newContext({ viewport: { width: SIZE.desktop.w, height: SIZE.desktop.h } });
  const page = await ctx.newPage();
  srv.state.block = ['missions.json'];
  await page.goto(srv.base);
  await page.waitForSelector('#intro .alert', { timeout: 120_000 });
  const t = await page.evaluate(() => ({ alert: document.querySelector('#intro .alert').innerText, steps: document.querySelector('#steps .steps-where')?.textContent ?? '' }));
  check(!/\b\d{3}\b|Not Found|server answered/.test(t.alert), `review-${variant} error: no HTTP status on screen ("${t.alert.slice(0, 80)}...")`);
  check(/of 4/.test(t.steps), `review-${variant} error: the step indicator keeps "of 4" ("${t.steps}")`);
  await page.screenshot({ path: join(SHOTS, `review-${variant}-error-missions.png`) });
  srv.state.block = [];
  await ctx.close();
}

const browser = await chromium.launch();
try {
  if (ONLY !== 'notwin') {
    const srv = await serve(DIST);
    for (const s of SIZES) await run(browser, srv, 'twin', s);
    await errorsRun(browser, srv, 'twin');
    await srv.close();
  }
  if (ONLY !== 'twin' && existsSync(OTHER)) {
    const tmp = mkdtempSync(join(tmpdir(), 'sby-gm-'));
    cpSync(OTHER, tmp, { recursive: true });
    const srv = await serve(DIST, { dataDir: tmp });
    for (const s of SIZES) await run(browser, srv, 'notwin', s);
    await srv.close();
    rmSync(tmp, { recursive: true, force: true });
  } else if (ONLY !== 'twin') check(false, `no-twin bundle not found at ${OTHER}`);
} finally {
  await browser.close();
}
console.log(failures.length ? `\n${failures.length} FAILED` : '\nall review checks passed');
process.exit(failures.length ? 1 : 0);
