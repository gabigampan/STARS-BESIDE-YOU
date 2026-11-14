#!/usr/bin/env node
// Interaction modules test: drives sunlight, markers, paired focus, beams and the video dialog
// through window.starsBesideYou in headless Chromium, with synthetic items created here only.
// Usage: node tests/modules.mjs [--no-build] [--only=desktop,phone,reduced]
// Screenshots go to $SHOTS_DIR (default: the team scratchpad folder below). Fails on any console error.

import { spawnSync } from 'node:child_process';
import { createReadStream, existsSync, mkdirSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { dirname, extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(APP, 'dist');
const SHOTS =
  process.env.SHOTS_DIR ??
  '/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/shots-frontend2';
// Optional fallback clip (made with ffmpeg outside the repository) when the rover files are absent.
const FALLBACK_MEDIA = process.env.TEST_MEDIA_DIR ?? '';
const MISSING_VIDEO = 'media/rover/this-file-does-not-exist.webm';

const failures = [];
const fail = (msg) => {
  failures.push(msg);
  console.log(`FAIL ${msg}`);
};
const ok = (msg) => console.log(`ok   ${msg}`);
const check = (cond, msg) => (cond ? ok(msg) : fail(msg));

if (!process.argv.includes('--no-build')) {
  const r = spawnSync('npm', ['run', 'build'], { cwd: APP, env: { ...process.env, VITE_USE_ION: '' }, encoding: 'utf8' });
  if (r.status !== 0) {
    console.log(r.stdout, r.stderr);
    process.exit(1);
  }
  ok('production build');
}

// ---------- static server (with byte ranges, for video) ----------
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.woff2': 'font/woff2',
  '.woff': 'font/woff', '.wasm': 'application/wasm', '.xml': 'application/xml', '.glb': 'model/gltf-binary',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.vtt': 'text/vtt; charset=utf-8',
};
const server = createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  let root = DIST;
  let path = decodeURIComponent(url.pathname);
  if (FALLBACK_MEDIA && path.startsWith('/test-media/')) {
    root = FALLBACK_MEDIA;
    path = path.slice('/test-media'.length);
  }
  let p = normalize(join(root, path));
  if (!p.startsWith(root)) return void res.writeHead(403).end();
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) return void res.writeHead(404).end('not found');
  const size = statSync(p).size;
  const type = MIME[extname(p)] ?? 'application/octet-stream';
  const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range ?? '');
  if (range) {
    const start = range[1] ? Number(range[1]) : 0;
    const end = range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
    res.writeHead(206, { 'content-type': type, 'accept-ranges': 'bytes', 'content-range': `bytes ${start}-${end}/${size}`, 'content-length': end - start + 1 });
    return void createReadStream(p, { start, end }).pipe(res);
  }
  res.writeHead(200, { 'content-type': type, 'accept-ranges': 'bytes', 'content-length': size });
  createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}/`;
mkdirSync(SHOTS, { recursive: true });

const roverInDist = existsSync(join(DIST, 'media/rover/rover.webm')) && existsSync(join(DIST, 'media/rover/rover.en.vtt'));
const MEDIA = roverInDist
  ? {
      title: 'Rover mission: driving across the lunar surface',
      sources: [
        { src: 'media/rover/rover.webm', type: 'video/webm' },
        { src: 'media/rover/rover.mp4', type: 'video/mp4' },
      ],
      poster: 'media/rover/rover-poster.jpg',
      tracks: [
        { src: 'media/rover/rover.en.vtt', srclang: 'en', label: 'English', default: true },
        { src: 'media/rover/rover.es.vtt', srclang: 'es', label: 'Español' },
      ],
      credit: 'Rover mission video: 3D simulation by the Stars Beside You team (not real footage)',
      note: 'A VIPER-like rover crossing a lunar sector; the on-screen panel shows its distance, pitch and roll.',
    }
  : {
      title: 'Test clip',
      sources: [{ src: 'test-media/clip.webm', type: 'video/webm' }],
      tracks: [{ src: 'test-media/clip.en.vtt', srclang: 'en', label: 'English', default: true }],
      credit: 'Test clip generated with ffmpeg',
      note: 'Synthetic test pattern.',
    };
if (!roverInDist && !FALLBACK_MEDIA) {
  console.log('rover media missing and TEST_MEDIA_DIR not set: video tests need one of them');
  process.exit(1);
}

const browser = await chromium.launch();

// ---------- helpers that run in the page ----------

/** Render both globes now and read back luminance statistics (drawing buffer is not preserved). */
async function stats(page, body, region) {
  return page.evaluate(
    ({ b, region }) => {
      const api = window.starsBesideYou;
      const scene = api.scene(b);
      scene.requestRender();
      scene.render(api.viewer(b).clock.currentTime);
      const src = scene.canvas;
      const r = region ?? { x: 0, y: 0, w: src.width, h: src.height };
      const n = region ? 1 : 0.25;
      const w = Math.max(1, Math.round(r.w * n));
      const h = Math.max(1, Math.round(r.h * n));
      const c = document.createElement('canvas');
      c.width = w;
      c.height = h;
      const ctx = c.getContext('2d', { willReadFrequently: true });
      ctx.drawImage(src, r.x, r.y, r.w, r.h, 0, 0, w, h);
      const d = ctx.getImageData(0, 0, w, h).data;
      const lum = new Float32Array(d.length / 4);
      let lit = 0;
      let sum = 0;
      for (let i = 0, j = 0; i < d.length; i += 4, j++) {
        const l = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
        lum[j] = l;
        sum += l;
        if (l > 25) lit++;
      }
      return { mean: sum / lum.length, lit: lit / lum.length, lum: Array.from(lum) };
    },
    { b: body, region },
  );
}
const meanAbsDiff = (a, b) => {
  let s = 0;
  for (let i = 0; i < a.lum.length; i++) s += Math.abs(a.lum[i] - b.lum[i]);
  return s / a.lum.length;
};

async function waitTiles(page, body, timeout = 240_000) {
  await page.waitForFunction(
    (b) => {
      const s = window.starsBesideYou?.scene(b);
      if (!s) return false;
      s.requestRender();
      return s.globe.tilesLoaded;
    },
    body,
    { timeout, polling: 400 },
  );
}

async function shot(page, name) {
  await page.waitForTimeout(300);
  await page.screenshot({ path: join(SHOTS, `${name}.png`) });
}

const canvasRect = (page, body) =>
  page.evaluate((b) => {
    const r = window.starsBesideYou.scene(b).canvas.getBoundingClientRect();
    return { left: r.left, top: r.top, width: r.width, height: r.height };
  }, body);

/** Synthetic markers: `n` items per body from a seeded generator; the ten best near (lat0, lon0). */
function makeItems(n, seed, lat0, lon0, spreadDeg) {
  let s = seed >>> 0;
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const items = [];
  for (let i = 0; i < n; i++) {
    const lat = (Math.asin(2 * rnd() - 1) * 180) / Math.PI;
    const lon = rnd() * 360 - 180;
    items.push({ id: `t${i}`, lat, lon, score: rnd() * 0.85 });
  }
  // The ten best: on a ring around the view centre, spaced so their labels do not collide.
  for (let k = 0; k < 10; k++) {
    const a = (k / 10) * Math.PI * 2;
    items[k].lat = lat0 + spreadDeg * Math.sin(a);
    items[k].lon = lon0 + spreadDeg * Math.cos(a);
    items[k].score = 1 - k * 0.01;
  }
  items.sort((x, y) => y.score - x.score);
  items.forEach((it, i) => {
    it.rank = i + 1;
    it.label = `Test site ${i + 1}`;
  });
  return items;
}

async function run(name, viewport, { touch = false } = {}) {
  console.log(`\n== ${name} ${viewport.width}x${viewport.height}`);
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1, hasTouch: touch });
  const page = await context.newPage();
  page.setDefaultTimeout(240_000);
  const errors = [];
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    const url = m.location()?.url ?? '';
    // The deliberate missing-file check produces exactly one expected 404.
    if (url.endsWith(MISSING_VIDEO) && /404/.test(m.text())) return;
    errors.push(`console: ${m.text()} ${url}`);
  });
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('response', (r) => {
    if (r.status() >= 400 && !r.url().endsWith(MISSING_VIDEO)) errors.push(`HTTP ${r.status()}: ${r.url()}`);
  });

  await page.goto(BASE, { waitUntil: 'load' });
  await page.waitForSelector('#loading', { state: 'hidden', timeout: 300_000 });
  await waitTiles(page, 'earth');
  await waitTiles(page, 'moon');
  const P = (body) => (body === 'earth' ? 'Earth' : 'Moon');

  // ===== 1. sunlight =====
  const first = await page.evaluate(() => {
    const api = window.starsBesideYou;
    const out = { mode: api.sunlight.mode(), date: api.sunlight.fullMoonDate().toISOString(), header: document.getElementById('sun-time').textContent };
    for (const b of ['earth', 'moon']) {
      const sub = api.sunlight.subsolar(b);
      const p = api.toCanvas(b, sub.lat, sub.lon);
      const c = api.scene(b).canvas;
      out[b] = { sub, p, w: c.clientWidth, h: c.clientHeight };
    }
    return out;
  });
  console.log(`     full Moon instant ${first.date}; header "${first.header}"`);
  check(first.mode === 'full-moon', 'default light is Full Moon');
  check(/Full Moon/.test(first.header) && first.header.includes('24 Nov 2026'), 'header names Full Moon and prints its date');
  for (const b of ['earth', 'moon']) {
    const f = first[b];
    // Facing the sunlit side: the sub-solar point is on the visible disc, near the middle.
    const off = f.p ? Math.hypot(f.p.x - f.w / 2, f.p.y - f.h / 2) / Math.min(f.w, f.h) : Infinity;
    check(off < 0.3, `${P(b)} camera faces the sunlit side on load (sub-solar point ${off.toFixed(2)} of the view from centre)`);
  }
  await shot(page, `${name}-01-full-moon`);

  // Fixed cameras so the three choices are compared on the same view.
  await page.evaluate(() => {
    const api = window.starsBesideYou;
    api.flyTo('earth', 10, 15, 14000, 0);
    api.flyTo('moon', 0, 0, 4200, 0);
  });
  await waitTiles(page, 'earth');
  await waitTiles(page, 'moon');
  const lightStats = {};
  for (const choice of ['now', 'even', 'full-moon']) {
    await page.locator(`.seg:has(input[value="${choice}"])`).click();
    await page.waitForTimeout(400);
    const st = await page.evaluate(() => ({
      mode: window.starsBesideYou.sunlight.mode(),
      header: document.getElementById('sun-time').textContent,
      live: document.getElementById('sunlight-status').textContent,
      checked: document.querySelector('input[name="sunlight"]:checked')?.value,
    }));
    const words = { 'full-moon': /Full Moon/, now: /now/i, even: /Even light.*not physical/ }[choice];
    check(st.mode === choice && st.checked === choice, `${choice}: mode and radio state`);
    check(words.test(st.header), `${choice}: header says "${st.header}"`);
    check(st.live === st.header, `${choice}: change announced in the live region`);
    lightStats[choice] = { earth: await stats(page, 'earth'), moon: await stats(page, 'moon') };
    await shot(page, `${name}-02-light-${choice}`);
  }
  for (const b of ['earth', 'moon']) {
    const s = lightStats;
    const d1 = meanAbsDiff(s['full-moon'][b], s.now[b]);
    const d2 = meanAbsDiff(s['full-moon'][b], s.even[b]);
    const d3 = meanAbsDiff(s.now[b], s.even[b]);
    console.log(`     ${P(b)} lit fraction: full ${s['full-moon'][b].lit.toFixed(3)}, now ${s.now[b].lit.toFixed(3)}, even ${s.even[b].lit.toFixed(3)}; diffs ${d1.toFixed(2)} ${d2.toFixed(2)} ${d3.toFixed(2)}`);
  }
  {
    const s = lightStats;
    check(meanAbsDiff(s['full-moon'].moon, s.now.moon) > 2, 'Moon pixels differ between Full Moon and Now');
    check(s['full-moon'].moon.lit > s.now.moon.lit + 0.05, 'Moon near side is more lit at Full Moon than now (crescent)');
    check(meanAbsDiff(s['full-moon'].moon, s.even.moon) > 0.3 || meanAbsDiff(s['full-moon'].earth, s.even.earth) > 0.3, 'Even light renders differently from Full Moon');
    check(meanAbsDiff(s.now.earth, s.even.earth) > 1 || meanAbsDiff(s.now.moon, s.even.moon) > 1, 'Even light renders differently from Now');
    check(s.even.moon.lit >= s.now.moon.lit && s.even.earth.lit >= s.now.earth.lit - 0.01, 'Even light has no night side');
  }
  // Keyboard: arrow keys move between the choices (native radio group).
  await page.locator('input[name="sunlight"][value="even"]').focus();
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(300);
  check((await page.evaluate(() => window.starsBesideYou.sunlight.mode())) === 'now', 'arrow key changes the choice (Even light -> Now)');
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(300);
  check((await page.evaluate(() => window.starsBesideYou.sunlight.mode())) === 'full-moon', 'arrow key changes the choice (Now -> Full Moon)');
  const focusRing = await page.evaluate(() => getComputedStyle(document.querySelector('input[name="sunlight"]:checked + span')).outlineStyle);
  check(focusRing !== 'none', 'keyboard focus is visible on the sunlight control');
  const sizes = await page.evaluate(() =>
    Array.from(document.querySelectorAll('.seg span, .sun-time, .sunlight-label')).map((el) => {
      const r = el.getBoundingClientRect();
      return { fs: parseFloat(getComputedStyle(el).fontSize), w: r.width, h: r.height, cls: el.className };
    }),
  );
  check(sizes.every((s) => s.fs >= 14), `sunlight text at least 14 px (${[...new Set(sizes.map((s) => s.fs))].join(', ')} px)`);
  check(sizes.filter((s) => s.cls === '').every((s) => s.w >= 44 && s.h >= 44), 'sunlight choices at least 44 x 44 px');

  // Back to the home views (Full Moon).
  await page.evaluate(() => window.starsBesideYou.resetView());
  await waitTiles(page, 'earth');
  await waitTiles(page, 'moon');

  // ===== 2. markers =====
  const home = await page.evaluate(() => {
    const api = window.starsBesideYou;
    return { earth: api.sunlight.subsolar('earth'), moon: api.sunlight.subsolar('moon') };
  });
  const earthHome = await page.evaluate(() => {
    // Camera sub-point of each body (home centre).
    const api = window.starsBesideYou;
    const out = {};
    for (const b of ['earth', 'moon']) {
      const c = api.scene(b).camera.positionCartographic;
      out[b] = { lat: (c.latitude * 180) / Math.PI, lon: (c.longitude * 180) / Math.PI };
    }
    return out;
  });
  void home;
  const items = {
    earth: makeItems(3000, 11, earthHome.earth.lat, earthHome.earth.lon, 30),
    moon: makeItems(3000, 23, earthHome.moon.lat, earthHome.moon.lon, 35),
  };
  const before = { earth: await stats(page, 'earth'), moon: await stats(page, 'moon') };
  await page.evaluate((items) => {
    const api = window.starsBesideYou;
    window.__picks = [];
    api.markers.onPick((body, id, source) => window.__picks.push({ body, id, source }));
    api.markers.setMarkers('earth', items.earth, { topLabels: 10 });
    api.markers.setMarkers('moon', items.moon, { topLabels: 10 });
  }, items);
  const after = { earth: await stats(page, 'earth'), moon: await stats(page, 'moon') };
  const counts = await page.evaluate(() => [window.starsBesideYou.markers.count('earth'), window.starsBesideYou.markers.count('moon')]);
  check(counts[0] === 3000 && counts[1] === 3000, `3,000 markers per body (${counts.join(', ')})`);
  check(meanAbsDiff(before.earth, after.earth) > 0.3 && meanAbsDiff(before.moon, after.moon) > 0.3, 'markers are drawn on both globes');
  await shot(page, `${name}-03-markers`);

  // Screen state of every marker, to find isolated ones and far-side ones.
  const states = await page.evaluate((ids) => {
    const api = window.starsBesideYou;
    const out = {};
    for (const b of ['earth', 'moon']) out[b] = ids[b].map((id) => ({ id, ...api.markers.screenState(b, id) }));
    return out;
  }, { earth: items.earth.map((i) => i.id), moon: items.moon.map((i) => i.id) });
  const isolated = (list, minDist) =>
    list.filter((a) => a.visible && a.fade > 0.99 && list.every((b) => b === a || !b.visible || b.fade < 0.02 || Math.hypot(a.x - b.x, a.y - b.y) > minDist));

  if (touch) {
    // Phone panes are small: move closer so neighbouring markers are more than a finger apart.
    await page.evaluate((c) => {
      const api = window.starsBesideYou;
      api.flyTo('earth', c.earth.lat, c.earth.lon, 2500, 0);
      api.flyTo('moon', c.moon.lat, c.moon.lon, 700, 0);
    }, earthHome);
    await page.waitForTimeout(500);
    Object.assign(
      states,
      await page.evaluate((ids) => {
        const api = window.starsBesideYou;
        const out = {};
        for (const b of ['earth', 'moon']) out[b] = ids[b].map((id) => ({ id, ...api.markers.screenState(b, id) }));
        return out;
      }, { earth: items.earth.map((i) => i.id), moon: items.moon.map((i) => i.id) }),
    );
  }
  for (const body of ['earth', 'moon']) {
    const rect = await canvasRect(page, body);
    const nVis = states[body].filter((s) => s.visible).length;
    const nFar = states[body].filter((s) => s.fade === 0).length;
    console.log(`     ${P(body)}: ${nVis} markers visible, ${nFar} hidden on the far side`);
    // A marker that is the unambiguous nearest one to a point `off` px away from it (touch: 15 px,
    // inside the 44 px target; mouse: 2 px).
    const off = touch ? 15 : 2.2;
    const vis = states[body].filter((s) => s.visible && s.fade > 0.99 && s.x > 30 && s.y > 30 && s.x < rect.width - 30 && s.y < rect.height - 30);
    let target = null;
    let tap = null;
    for (const t of vis) {
      for (let a = 0; a < 8 && !target; a++) {
        const px = t.x + off * Math.cos((a * Math.PI) / 4);
        const py = t.y + off * Math.sin((a * Math.PI) / 4);
        const dt = Math.hypot(px - t.x, py - t.y);
        if (vis.every((o) => o === t || Math.hypot(px - o.x, py - o.y) > dt + 8)) {
          target = t;
          tap = { x: px, y: py };
        }
      }
      if (target) break;
    }
    if (!target) {
      fail(`${P(body)}: no marker to click`);
      continue;
    }
    console.log(`     ${P(body)}: target ${target.id} at ${target.x.toFixed(0)}, ${target.y.toFixed(0)}; pointer ${off} px away`);
    await page.evaluate(() => (window.__picks = []));
    if (touch) {
      await page.touchscreen.tap(rect.left + tap.x, rect.top + tap.y);
    } else {
      await page.mouse.move(rect.left + tap.x, rect.top + tap.y);
      await page.waitForTimeout(300);
      const cursor = await page.evaluate((b) => window.starsBesideYou.scene(b).canvas.style.cursor, body);
      check(cursor === 'pointer', `${P(body)}: pointer cursor over a marker`);
      await page.mouse.click(rect.left + tap.x, rect.top + tap.y);
    }
    await page.waitForTimeout(300);
    const picks = await page.evaluate(() => window.__picks);
    check(picks.length === 1 && picks[0].id === target.id && picks[0].body === body, `${P(body)}: ${touch ? 'tap 15 px from' : 'click on'} marker ${target.id} fires onPick with its id (${JSON.stringify(picks)})`);
    if (!touch) {
      // With a mouse the radius is small: a click 15 px away from an isolated marker picks nothing.
      const far = isolated(states[body], 30)[0];
      if (far) {
        await page.evaluate(() => (window.__picks = []));
        await page.mouse.click(rect.left + far.x + 12, rect.top + far.y + 9);
        await page.waitForTimeout(300);
        const none = await page.evaluate(() => window.__picks.length);
        check(none === 0, `${P(body)}: a mouse click 15 px from a marker picks nothing`);
      }
      await page.mouse.move(rect.left + 5, rect.top + rect.height - 5);
    }
  }
  await shot(page, `${name}-04-picked`);
  if (touch) {
    await page.evaluate(() => window.starsBesideYou.resetView());
    await page.waitForTimeout(2500);
    Object.assign(
      states,
      await page.evaluate((ids) => {
        const api = window.starsBesideYou;
        const out = {};
        for (const b of ['earth', 'moon']) out[b] = ids[b].map((id) => ({ id, ...api.markers.screenState(b, id) }));
        return out;
      }, { earth: items.earth.map((i) => i.id), moon: items.moon.map((i) => i.id) }),
    );
  }

  // Top ranks carry their number: compare pixels right of the rank-1 Earth marker with topLabels 0 vs 10.
  {
    await page.evaluate(() => ['earth', 'moon'].forEach((b) => window.starsBesideYou.markers.setSelected(b, null)));
    const s1 = await page.evaluate(() => window.starsBesideYou.markers.screenState('earth', 't0') ?? null);
    const rank1 = states.earth.find((s) => s.id === items.earth[0].id);
    const region = { x: Math.round(rank1.x + 6), y: Math.round(rank1.y - 10), w: 22, h: 20 };
    const withLabels = await stats(page, 'earth', region);
    await page.evaluate((it) => window.starsBesideYou.markers.setMarkers('earth', it, { topLabels: 0 }), items.earth);
    const noLabels = await stats(page, 'earth', region);
    await page.evaluate((it) => window.starsBesideYou.markers.setMarkers('earth', it, { topLabels: 10 }), items.earth);
    void s1;
    check(meanAbsDiff(withLabels, noLabels) > 3, `rank number drawn next to the best marker (pixel difference ${meanAbsDiff(withLabels, noLabels).toFixed(1)})`);
  }

  // Selection draws a ring (pixels on a circle around the marker change) and its label.
  {
    // The second-best Moon marker (same scene with and without selection, so neighbours cancel out).
    const mw = (await canvasRect(page, 'moon')).width;
    const t = items.moon
      .slice(0, 10)
      .map((it) => states.moon.find((s) => s.id === it.id))
      .find((s) => s.visible && s.x > 30 && s.x < mw - 110);
    const region = { x: Math.round(t.x - 16), y: Math.round(t.y - 16), w: 32, h: 32 };
    const off = await stats(page, 'moon', region);
    await page.evaluate((id) => window.starsBesideYou.markers.setSelected('moon', id), t.id);
    const on = await stats(page, 'moon', region);
    // Ring: pixels at radius ~ (size + 14) / 2 brighten.
    const r = (t.size + 14) / 2;
    let ringGain = 0;
    let n = 0;
    for (let a = 0; a < 16; a++) {
      const x = Math.round(16 + r * Math.cos((a / 16) * Math.PI * 2));
      const y = Math.round(16 + r * Math.sin((a / 16) * Math.PI * 2));
      if (x < 0 || y < 0 || x >= 32 || y >= 32) continue;
      ringGain += on.lum[y * 32 + x] - off.lum[y * 32 + x];
      n++;
    }
    ringGain /= Math.max(1, n);
    check(ringGain > 20, `selection ring drawn around the marker (ring brightens by ${ringGain.toFixed(0)})`);
    const labelRegion = { x: Math.round(t.x + r + 6), y: Math.round(t.y - 9), w: 60, h: 18 };
    const lOn = await stats(page, 'moon', labelRegion);
    await page.evaluate(() => window.starsBesideYou.markers.setSelected('moon', null));
    const lOff = await stats(page, 'moon', labelRegion);
    await page.evaluate((id) => window.starsBesideYou.markers.setSelected('moon', id), t.id);
    check(meanAbsDiff(lOn, lOff) > 6, `selected marker shows its label (pixel difference ${meanAbsDiff(lOn, lOff).toFixed(1)})`);
    await shot(page, `${name}-05-selected`);
  }

  // Far-side markers are hidden: a single marker at the antipode of the view centre draws nothing.
  {
    const c = earthHome.moon;
    const anti = { id: 'far', lat: -c.lat, lon: c.lon > 0 ? c.lon - 180 : c.lon + 180, score: 1, rank: 1, label: 'Far side' };
    const near = { id: 'near-limb', lat: c.lat, lon: c.lon + 65, score: 1 };
    await page.evaluate(() => window.starsBesideYou.markers.clearMarkers('moon'));
    const st = await page.evaluate(({ anti, near }) => {
      const api = window.starsBesideYou;
      api.markers.setMarkers('moon', [anti, near]);
      return { far: api.markers.screenState('moon', 'far'), near: api.markers.screenState('moon', 'near-limb') };
    }, { anti, near });
    check(!st.far.visible && st.far.fade === 0, 'far-side marker is hidden');
    check(st.near.fade > 0 && st.near.fade < 1, `marker near the limb fades (fade ${st.near.fade.toFixed(2)})`);
    const region = { x: Math.round(st.far.x - 8), y: Math.round(st.far.y - 8), w: 16, h: 16 };
    const withFar = await stats(page, 'moon', region);
    await page.evaluate(() => window.starsBesideYou.markers.clearMarkers('moon'));
    const without = await stats(page, 'moon', region);
    check(meanAbsDiff(withFar, without) < 0.5, `no pixels drawn for the far-side marker (difference ${meanAbsDiff(withFar, without).toFixed(2)})`);
    await page.evaluate((it) => window.starsBesideYou.markers.setMarkers('moon', it, { topLabels: 10 }), items.moon);
  }

  // Keyboard path: activate() from a list fires onPick with source 'keyboard'.
  await page.evaluate(() => (window.__picks = []));
  await page.evaluate(() => window.starsBesideYou.markers.activate('earth', 't5'));
  const kp = await page.evaluate(() => window.__picks);
  check(kp.length === 1 && kp[0].id === 't5' && kp[0].source === 'keyboard', 'activate() (Enter in a list) fires onPick from the keyboard');

  // ===== 4. beam (home views) =====
  const pair = { earth: items.earth[0], moon: items.moon[0] };
  await page.evaluate((pair) => {
    const api = window.starsBesideYou;
    api.markers.setSelected('earth', pair.earth.id);
    api.markers.setSelected('moon', pair.moon.id);
    api.beams.setBeams([
      { earth: pair.earth, moon: pair.moon, strength: 1 },
      { earth: { lat: pair.earth.lat + 12, lon: pair.earth.lon - 10 }, moon: { lat: pair.moon.lat - 10, lon: pair.moon.lon + 14 }, strength: 0.25 },
    ]);
  }, pair);
  await page.waitForTimeout(500);
  {
    const res = await page.evaluate((pair) => {
      const api = window.starsBesideYou;
      const drawn = api.beams.lastDrawn().find((d) => d.strength === 1);
      const exp = {};
      for (const b of ['earth', 'moon']) {
        const r = api.scene(b).canvas.getBoundingClientRect();
        const p = api.toCanvas(b, pair[b].lat, pair[b].lon);
        exp[b] = { x: r.left + p.x, y: r.top + p.y };
      }
      const ov = document.querySelector('.beam-overlay');
      const ctx = ov.getContext('2d');
      const k = ov.width / window.innerWidth;
      const alphaAt = (x, y) => ctx.getImageData(Math.round(x * k), Math.round(y * k), 1, 1).data;
      const mid = { x: (exp.earth.x + exp.moon.x) / 2, y: (exp.earth.y + exp.moon.y) / 2 };
      // A point well off the line, for contrast.
      const dx = exp.moon.x - exp.earth.x;
      const dy = exp.moon.y - exp.earth.y;
      const len = Math.hypot(dx, dy);
      const offLine = { x: mid.x - (dy / len) * 60, y: mid.y + (dx / len) * 60 };
      const hit = document.elementFromPoint(mid.x, mid.y);
      return {
        drawn,
        exp,
        mid: Array.from(alphaAt(mid.x, mid.y)),
        off: Array.from(alphaAt(offLine.x, offLine.y)),
        hit: hit ? hit.tagName + '.' + hit.className : null,
        pe: getComputedStyle(ov).pointerEvents,
        z: getComputedStyle(ov).zIndex,
      };
    }, pair);
    const dE = Math.hypot(res.drawn.earth.x - res.exp.earth.x, res.drawn.earth.y - res.exp.earth.y);
    const dM = Math.hypot(res.drawn.moon.x - res.exp.moon.x, res.drawn.moon.y - res.exp.moon.y);
    check(dE < 3 && dM < 3 && res.drawn.earth.kind === 'point' && res.drawn.moon.kind === 'point', `beam joins the two projected points (off by ${dE.toFixed(1)} and ${dM.toFixed(1)} px)`);
    check(res.mid[3] > 10 && res.off[3] < 3, `beam is drawn along the line (alpha ${res.mid[3]} on it, ${res.off[3]} beside it)`);
    check(res.pe === 'none' && !/beam-overlay/.test(res.hit ?? ''), `overlay intercepts no pointer events (element under the beam: ${res.hit})`);
    await shot(page, `${name}-06-beam`);
    // A click on the beam reaches the globe: pick the Earth marker under the beam's Earth end.
    await page.evaluate(() => (window.__picks = []));
    const sEarth = await page.evaluate((id) => window.starsBesideYou.markers.screenState('earth', id), pair.earth.id);
    const er = await canvasRect(page, 'earth');
    if (touch) await page.touchscreen.tap(er.left + sEarth.x, er.top + sEarth.y);
    else await page.mouse.click(er.left + sEarth.x, er.top + sEarth.y);
    await page.waitForTimeout(300);
    const bp = await page.evaluate(() => window.__picks);
    check(bp.length === 1 && bp[0].id === pair.earth.id, 'a click through the beam reaches the marker under it');
  }
  // Far-side lunar end: the beam stops at the Moon's limb.
  {
    const c = earthHome.moon;
    const farMoon = { lat: c.lat, lon: c.lon > 0 ? c.lon - 130 : c.lon + 130 };
    await page.evaluate(({ e, m }) => window.starsBesideYou.beams.setBeams([{ earth: e, moon: m, strength: 1 }]), { e: pair.earth, m: farMoon });
    await page.waitForTimeout(400);
    const drawn = (await page.evaluate(() => window.starsBesideYou.beams.lastDrawn()))[0];
    check(drawn.moon.kind === 'limb', `far-side end is drawn at the limb (kind ${drawn.moon.kind})`);
    const mr = await canvasRect(page, 'moon');
    const cx = mr.width / 2;
    const cy = mr.height / 2;
    const lx = drawn.moon.x - mr.left;
    const ly = drawn.moon.y - mr.top;
    const len = Math.hypot(lx - cx, ly - cy);
    const ux = (lx - cx) / len;
    const uy = (ly - cy) / len;
    const sample = async (d) =>
      (await stats(page, 'moon', { x: Math.round(lx + ux * d) - 1, y: Math.round(ly + uy * d) - 1, w: 3, h: 3 })).mean;
    const inside = await sample(-6);
    const outside = await sample(6);
    check(inside > 35 && outside < 25, `limb end sits on the Moon's edge (lit ${inside.toFixed(0)} inside, ${outside.toFixed(0)} outside)`);
    await shot(page, `${name}-07-beam-far-side`);
  }

  // ===== 3. paired focus =====
  {
    await page.evaluate(() => {
      // Stand-in for the next stage's comparison panel (test only).
      const p = document.getElementById('detail-panel');
      p.innerHTML = '<div style="padding:16px"><h2 style="font:600 18px Barlow Semi Condensed">Comparison (test content)</h2><p style="margin-top:8px">Synthetic text inserted by the test to give the panel a size.</p></div>';
      p.hidden = false;
    });
    const e = pair.earth;
    const m = pair.moon;
    const cell = (p) => ({ west: Math.floor(p.lon), east: Math.floor(p.lon) + 1, south: Math.floor(p.lat), north: Math.floor(p.lat) + 1 });
    // Focus on the marked sites themselves; the caller passes the 1-degree cell that holds each one.
    const focusE = { lat: e.lat, lon: e.lon, cell: cell(e) };
    const focusM = { lat: m.lat, lon: m.lon, cell: cell(m) };
    const savedCams = await page.evaluate(() => ['earth', 'moon'].map((b) => window.starsBesideYou.scene(b).camera.positionWC.clone()));
    const res = await page.evaluate(async ({ focusE, focusM }) => {
      const api = window.starsBesideYou;
      const t0 = performance.now();
      // Simulated 60 fps clock: software WebGL takes ~0.5 s per frame here, so the flight is timed
      // on the animation's own clock (16.7 ms per frame) and the wall time is reported alongside.
      let sim = 0;
      const okk = await api.focus.focusPair({ earth: focusE, moon: focusM }, { timeSource: () => (sim += 1000 / 60) });
      const wall = performance.now() - t0;
      const out = { ok: okk, wall, report: api.focus.lastFlight(), focused: api.focus.isFocused() };
      for (const [b, f] of [['earth', focusE], ['moon', focusM]]) {
        const c = api.scene(b).canvas;
        const r = c.getBoundingClientRect();
        const p = api.toCanvas(b, f.lat, f.lon);
        const sw = api.toCanvas(b, f.cell.south, f.cell.west);
        const ne = api.toCanvas(b, f.cell.north, f.cell.east);
        const page = { x: r.left + p.x, y: r.top + p.y };
        const hit = document.elementFromPoint(page.x, page.y);
        const cam = api.scene(b).camera.positionCartographic;
        out[b] = {
          p, page, w: c.clientWidth, h: c.clientHeight,
          cellW: Math.abs(ne.x - sw.x), cellH: Math.abs(ne.y - sw.y),
          heightKm: cam.height / 1000, camLat: (cam.latitude * 180) / Math.PI, camLon: (cam.longitude * 180) / Math.PI,
          hit: hit ? hit.tagName : null,
          underPanel: (() => {
            const pr = document.getElementById('detail-panel').getBoundingClientRect();
            return page.x >= pr.left && page.x <= pr.right && page.y >= pr.top && page.y <= pr.bottom;
          })(),
        };
      }
      out.panel = (() => {
        const r = document.getElementById('detail-panel').getBoundingClientRect();
        return { left: r.left, top: r.top, width: r.width, height: r.height };
      })();
      return out;
    }, { focusE, focusM });
    console.log(`     focus flight: planned ${res.report.plannedMs} ms, ${res.report.animationMs.toFixed(0)} ms of simulated 60 fps time, wall ${res.wall.toFixed(0)} ms on software WebGL`);
    check(res.ok && res.focused, 'focusPair resolves true and the view is focused');
    check(res.report.animationMs <= 1500 && res.report.plannedMs <= 1500, `both cameras arrive in under 1.5 s of simulated time (${res.report.animationMs.toFixed(0)} ms)`);
    for (const b of ['earth', 'moon']) {
      const r = res[b];
      const f = b === 'earth' ? focusE : focusM;
      const dc = Math.hypot(r.p.x - r.w / 2, r.p.y - r.h / 2);
      check(dc < 3 && Math.abs(r.camLat - f.lat) < 0.01, `${P(b)} camera above the point (${dc.toFixed(1)} px from centre, ${r.heightKm.toFixed(0)} km up)`);
      const share = Math.max(r.cellW, r.cellH) / Math.min(r.w, r.h);
      check(share > 0.25 && share < 0.6, `${P(b)} 1-degree cell framed (${r.cellW.toFixed(0)} x ${r.cellH.toFixed(0)} px, ${(share * 100).toFixed(0)} % of the view)`);
      check(r.hit === 'CANVAS' && !r.underPanel, `${P(b)} point stays visible beside the comparison panel`);
    }
    await page.evaluate(({ e, m }) => window.starsBesideYou.beams.setBeams([{ earth: e, moon: m, strength: 1 }]), { e: focusE, m: focusM });
    await waitTiles(page, 'earth');
    await waitTiles(page, 'moon');
    await shot(page, `${name}-08-focus`);
    // Off-screen end: an Earth point outside the zoomed view fades toward the canvas edge.
    await page.evaluate(({ e, m }) => window.starsBesideYou.beams.setBeams([{ earth: { lat: e.lat + 8, lon: e.lon }, moon: m, strength: 1 }]), { e: focusE, m: focusM });
    await page.waitForTimeout(400);
    const offDrawn = (await page.evaluate(() => window.starsBesideYou.beams.lastDrawn()))[0];
    {
      const er = await canvasRect(page, 'earth');
      const onEdge = Math.min(Math.abs(offDrawn.earth.x - er.left), Math.abs(offDrawn.earth.x - er.left - er.width), Math.abs(offDrawn.earth.y - er.top), Math.abs(offDrawn.earth.y - er.top - er.height));
      check(offDrawn.earth.kind === 'edge' && onEdge < 3, `off-screen end fades at the Earth canvas edge (kind ${offDrawn.earth.kind}, ${onEdge.toFixed(1)} px from the edge)`);
      await shot(page, `${name}-08b-focus-offscreen-end`);
    }
    await page.evaluate(({ e, m }) => window.starsBesideYou.beams.setBeams([{ earth: e, moon: m, strength: 1 }]), { e: focusE, m: focusM });

    const exit = await page.evaluate(async () => {
      const api = window.starsBesideYou;
      const okk = await api.focus.exitFocus();
      return { ok: okk, focused: api.focus.isFocused(), report: api.focus.lastFlight(), cams: ['earth', 'moon'].map((b) => api.scene(b).camera.positionWC.clone()) };
    });
    const back = exit.cams.map((c, i) => Math.hypot(c.x - savedCams[i].x, c.y - savedCams[i].y, c.z - savedCams[i].z) / 1000);
    check(exit.ok && !exit.focused && back.every((d) => d < 50), `exitFocus returns both cameras (${back.map((d) => d.toFixed(1)).join(', ')} km from the earlier views)`);
    await page.evaluate(() => {
      const p = document.getElementById('detail-panel');
      p.hidden = true;
      p.replaceChildren();
    });
  }

  // ===== performance: 3,000 markers per body and one beam =====
  {
    const perf = await page.evaluate(async () => {
      const api = window.starsBesideYou;
      const scenes = ['earth', 'moon'].map((b) => api.scene(b));
      const gls = scenes.map((s) => s.canvas.getContext('webgl2') || s.canvas.getContext('webgl'));
      const px = new Uint8Array(4);
      const pct = (a, q) => [...a].sort((x, y) => x - y)[Math.floor(a.length * q)];
      // CPU + GPU time of one frame of both globes while both cameras turn (readPixels waits for the GPU).
      const measure = async (frames) => {
        const times = [];
        for (let i = 0; i < frames; i++) {
          const t = performance.now();
          scenes.forEach((s, k) => {
            s.camera.rotateRight(0.003);
            s.render(api.viewer('earth').clock.currentTime);
            gls[k].readPixels(0, 0, 1, 1, gls[k].RGBA, gls[k].UNSIGNED_BYTE, px);
          });
          times.push(performance.now() - t);
          await new Promise((r) => setTimeout(r, 0));
        }
        return { median: pct(times, 0.5), p90: pct(times, 0.9) };
      };
      // Real frame pacing: rAF intervals while both cameras turn (Cesium's own loop renders, the beam redraws).
      const pacing = () =>
        new Promise((resolve) => {
          const out = [];
          let last = 0;
          let n = 0;
          const step = (t) => {
            if (last) out.push(t - last);
            last = t;
            for (const s of scenes) {
              s.camera.rotateRight(0.003);
              s.requestRender();
            }
            if (++n < 20) requestAnimationFrame(step);
            else resolve(pct(out, 0.5));
          };
          requestAnimationFrame(step);
        });
      const markers = { earth: api.markers.count('earth'), moon: api.markers.count('moon') };
      const beams = api.beams.lastDrawn().length;
      const d0 = api.beams.drawCount();
      const withAll = await measure(20);
      const rafWith = await pacing();
      const beamDraws = api.beams.drawCount() - d0;
      api.markers.clearMarkers('earth');
      api.markers.clearMarkers('moon');
      api.beams.clearBeams();
      await new Promise((r) => setTimeout(r, 200));
      const without = await measure(20);
      const rafWithout = await pacing();
      return { withAll, without, rafWith, rafWithout, markers, beams, beamDraws };
    });
    console.log(
      `     frame time, both globes, ${perf.markers.earth} + ${perf.markers.moon} markers and ${perf.beams} beam: ` +
        `median ${perf.withAll.median.toFixed(0)} ms (p90 ${perf.withAll.p90.toFixed(0)} ms); without markers or beam ${perf.without.median.toFixed(0)} ms. ` +
        `rAF interval while turning: ${perf.rafWith.toFixed(0)} ms with, ${perf.rafWithout.toFixed(0)} ms without (software WebGL, SwiftShader); beam redraws ${perf.beamDraws}`,
    );
    ok(`performance measured (${name})`);
    await page.evaluate(({ items, pair }) => {
      const api = window.starsBesideYou;
      api.markers.setMarkers('earth', items.earth, { topLabels: 10 });
      api.markers.setMarkers('moon', items.moon, { topLabels: 10 });
      api.beams.setBeams([{ earth: pair.earth, moon: pair.moon, strength: 1 }]);
      api.resetView();
    }, { items, pair });
    await page.waitForTimeout(1500);
  }

  // ===== 5. video dialog =====
  {
    check((await page.locator('dialog.video-dialog').count()) === 0, 'no video dialog in the page before openVideo');
    await page.locator('#credits-button').focus();
    await page.evaluate((spec) => {
      window.__videoClosed = false;
      window.starsBesideYou.video.openVideo(spec).then(() => (window.__videoClosed = true));
    }, MEDIA);
    await page.waitForSelector('dialog.video-dialog[open] video');
    await page.waitForFunction(() => document.querySelector('dialog.video-dialog video')?.readyState >= 1, null, { timeout: 60_000 });
    const v = await page.evaluate(async () => {
      const video = document.querySelector('dialog.video-dialog video');
      video.currentTime = 4;
      await new Promise((r) => video.addEventListener('seeked', r, { once: true }));
      await new Promise((r) => setTimeout(r, 400));
      const tt = Array.from(video.textTracks);
      const showing = tt.find((t) => t.mode === 'showing');
      return {
        controls: video.controls,
        tracks: tt.map((t) => `${t.language}:${t.mode}`),
        activeCue: showing?.activeCues?.[0]?.text ?? null,
        credit: document.querySelector('.video-credit').textContent,
        note: document.querySelector('.video-note').textContent,
        active: document.activeElement?.className,
        modal: document.querySelector('dialog.video-dialog').matches(':modal'),
        closeLabel: document.querySelector('.video-close').getAttribute('aria-label'),
        closeSize: (() => {
          const r = document.querySelector('.video-close').getBoundingClientRect();
          return [r.width, r.height];
        })(),
      };
    });
    check(v.modal && v.controls, 'video dialog is modal with native controls');
    check(v.tracks[0]?.endsWith(':showing') && !!v.activeCue, `captions on by default (${v.tracks.join(', ')}; cue "${(v.activeCue ?? '').split('\n')[0]}")`);
    check(v.credit === MEDIA.credit && v.note === MEDIA.note, 'credit line and note under the player');
    check(/video-close/.test(v.active ?? '') && v.closeLabel === 'Close video' && v.closeSize[0] >= 44 && v.closeSize[1] >= 44, 'focus starts on the 44 px close (X) button');
    await shot(page, `${name}-09-video`);
    // Focus trap: Tab and Shift+Tab never leave the dialog.
    let escaped = false;
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press('Tab');
      if (!(await page.evaluate(() => !!document.activeElement?.closest('dialog.video-dialog')))) escaped = true;
    }
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press('Shift+Tab');
      if (!(await page.evaluate(() => !!document.activeElement?.closest('dialog.video-dialog')))) escaped = true;
    }
    check(!escaped, 'Tab and Shift+Tab stay inside the dialog');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    const closed = await page.evaluate(() => ({
      open: document.querySelector('dialog.video-dialog').open,
      resolved: window.__videoClosed,
      focus: document.activeElement?.id,
    }));
    check(!closed.open && closed.resolved, 'Escape closes the video dialog');
    check(closed.focus === 'credits-button', `focus returns to the opener (${closed.focus})`);

    // A missing file shows a message, never a blank player.
    await page.evaluate((spec) => {
      window.starsBesideYou.video.openVideo({ ...spec, sources: [{ src: 'media/rover/this-file-does-not-exist.webm', type: 'video/webm' }] });
    }, MEDIA);
    await page.waitForSelector('.video-error:not([hidden])', { timeout: 30_000 });
    const err = await page.evaluate(() => ({
      text: document.querySelector('.video-error-text').textContent,
      frameHidden: document.querySelector('.video-frame').hidden,
      videos: document.querySelectorAll('dialog.video-dialog video').length,
      role: document.querySelector('.video-error').getAttribute('role'),
    }));
    check(err.frameHidden && err.videos === 0 && err.role === 'alert', 'failed load replaces the player with an alert');
    check(/could not be played/.test(err.text) && /Try again/.test(err.text), `failure message says what happened and what to do ("${err.text.slice(0, 80)}...")`);
    await shot(page, `${name}-10-video-error`);
    await page.locator('.video-close').click();
    check(!(await page.evaluate(() => document.querySelector('dialog.video-dialog').open)), 'close button (X) closes the dialog');
  }

  // Clearing everything leaves no trace.
  await page.evaluate(() => {
    const api = window.starsBesideYou;
    api.markers.clearMarkers('earth');
    api.markers.clearMarkers('moon');
    api.beams.clearBeams();
  });
  await page.waitForTimeout(300);
  const blank = await page.evaluate(() => {
    const ov = document.querySelector('.beam-overlay');
    const d = ov.getContext('2d').getImageData(0, 0, ov.width, ov.height).data;
    let m = 0;
    for (let i = 3; i < d.length; i += 4) m = Math.max(m, d[i]);
    return m;
  });
  check(blank === 0, 'clearBeams leaves the overlay empty');

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  check(overflow <= 0, 'no horizontal overflow');
  for (const e of errors) fail(e);
  if (!errors.length) ok('no console errors or failed requests');
  await context.close();
}

/** Reduced motion: focusPair is instant, beams do not animate. */
async function runReduced() {
  console.log('\n== reduced motion 1440x900');
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page = await context.newPage();
  page.setDefaultTimeout(240_000);
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(BASE, { waitUntil: 'load' });
  await page.waitForSelector('#loading', { state: 'hidden', timeout: 300_000 });
  const r = await page.evaluate(async () => {
    const api = window.starsBesideYou;
    const okk = await api.focus.focusPair({ earth: { lat: 23.5, lon: 12.5 }, moon: { lat: -43.5, lon: -11.5 } });
    const rep = api.focus.lastFlight();
    api.beams.setBeams([{ earth: { lat: 23.5, lon: 12.5 }, moon: { lat: -43.5, lon: -11.5 }, strength: 1 }]);
    await new Promise((res) => setTimeout(res, 300));
    const d0 = api.beams.drawCount();
    await new Promise((res) => setTimeout(res, 1500));
    const d1 = api.beams.drawCount();
    const ov = document.querySelector('.beam-overlay');
    const snap = () => {
      const d = ov.getContext('2d').getImageData(0, 0, ov.width, ov.height).data;
      let s = 0;
      for (let i = 3; i < d.length; i += 64) s += d[i];
      return s;
    };
    const a = snap();
    await new Promise((res) => setTimeout(res, 800));
    const b = snap();
    await api.focus.exitFocus();
    return { ok: okk, rep, redraws: d1 - d0, same: a === b, exitRep: api.focus.lastFlight() };
  });
  check(r.ok && r.rep.plannedMs === 0 && r.exitRep.plannedMs === 0, 'reduced motion: focusPair and exitFocus are instant');
  check(r.redraws === 0 && r.same, 'reduced motion: the beam does not animate while nothing moves');
  for (const e of errors) fail(`console: ${e}`);
  await context.close();
}

const only = process.argv.find((a) => a.startsWith('--only='))?.slice(7).split(',');
const want = (n) => !only || only.includes(n);
try {
  if (want('desktop')) await run('desktop', { width: 1440, height: 900 });
  if (want('phone')) await run('phone', { width: 375, height: 812 }, { touch: true });
  if (want('reduced')) await runReduced();
} finally {
  await browser.close();
  server.close();
}

console.log(`\nscreenshots: ${SHOTS}`);
if (failures.length) {
  console.log(`${failures.length} failure(s)`);
  process.exit(1);
}
console.log('modules test passed');
