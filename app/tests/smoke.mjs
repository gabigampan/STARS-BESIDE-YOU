#!/usr/bin/env node
// Smoke test: build the key-free site, serve dist/, open it in headless Chromium and check that
// both globes draw real imagery with no errors.
// Usage: node tests/smoke.mjs [--no-build] [--skip-4k] [--only=desktop,phone,fullmoon,tablet,uhd]
// Screenshots go to $SHOTS_DIR (default: the team scratchpad folder below).

import { spawnSync } from 'node:child_process';
import { createReadStream, existsSync, mkdirSync, readFileSync, readdirSync, statSync } from 'node:fs';
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
  '/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/shots-frontend';
const IMAGERY_HOSTS = ['gibs.earthdata.nasa.gov', 'trek.nasa.gov', 'tiles.maps.eox.at'];
const LOAD_TIMEOUT = 300_000; // SwiftShader (software WebGL) is slow
const failures = [];
const fail = (msg) => {
  failures.push(msg);
  console.log(`FAIL ${msg}`);
};
const ok = (msg) => console.log(`ok   ${msg}`);

// ---------- build ----------
if (!process.argv.includes('--no-build')) {
  // Key-free build: make sure ion mode is off whatever the shell has.
  const env = { ...process.env, VITE_USE_ION: '' };
  const r = spawnSync('npm', ['run', 'build'], { cwd: APP, env, encoding: 'utf8' });
  if (r.status !== 0) {
    console.log(r.stdout, r.stderr);
    process.exit(1);
  }
  ok('production build');
}

// The ion token must never reach the deployable bundle (the value is read, never printed).
{
  const envFile = join(APP, '.env.local');
  const m = existsSync(envFile) ? readFileSync(envFile, 'utf8').match(/^VITE_CESIUM_ION_TOKEN=(.+)$/m) : null;
  const token = m?.[1]?.trim().replace(/^["']|["']$/g, '');
  if (token) {
    const walk = (d) => readdirSync(d).flatMap((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]));
    const leaked = walk(DIST).filter((f) => /\.(js|html|css|json)$/.test(f) && readFileSync(f, 'utf8').includes(token));
    if (leaked.length) fail(`ion token found in ${leaked.length} built file(s)`);
    else ok('ion token absent from dist/');
  }
}

// ---------- static server ----------
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.woff': 'font/woff',
  '.wasm': 'application/wasm', '.xml': 'application/xml', '.glb': 'model/gltf-binary',
};
const server = createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  let p = normalize(join(DIST, decodeURIComponent(url.pathname)));
  if (!p.startsWith(DIST)) return void res.writeHead(403).end();
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) return void res.writeHead(404).end('not found');
  res.writeHead(200, { 'content-type': MIME[extname(p)] ?? 'application/octet-stream' });
  createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}/`;
mkdirSync(SHOTS, { recursive: true });

// ---------- browser ----------
const browser = await chromium.launch();

async function canvasStats(page, body) {
  // Render and read back in the same task (the drawing buffer is not preserved between frames).
  return page.evaluate((b) => {
    const scene = window.starsBesideYou.scene(b);
    // requestRenderMode skips frames nobody asked for: ask, then render now.
    scene.requestRender();
    scene.render(window.starsBesideYou.viewer(b).clock.currentTime);
    const src = scene.canvas;
    const n = 96;
    const c = document.createElement('canvas');
    c.width = n;
    c.height = n;
    const ctx = c.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(src, 0, 0, n, n);
    const d = ctx.getImageData(0, 0, n, n).data;
    let dark = 0, sum = 0, sum2 = 0;
    const colours = new Set();
    for (let i = 0; i < d.length; i += 4) {
      const l = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
      if (l < 10) dark++;
      sum += l;
      sum2 += l * l;
      colours.add(((d[i] >> 3) << 10) | ((d[i + 1] >> 3) << 5) | (d[i + 2] >> 3));
    }
    const count = d.length / 4;
    const mean = sum / count;
    return { darkFraction: dark / count, mean, std: Math.sqrt(sum2 / count - mean * mean), colours: colours.size };
  }, body);
}

function judgeCanvas(tag, s, { minLit = 0.08, minColours = 40 } = {}) {
  const lit = 1 - s.darkFraction;
  const desc = `${tag}: lit ${(lit * 100).toFixed(1)} %, std ${s.std.toFixed(1)}, colours ${s.colours}`;
  if (lit < minLit) fail(`${desc} - canvas mostly black`);
  else if (s.std < 6 || s.colours < minColours) fail(`${desc} - canvas is one flat colour`);
  else ok(desc);
}

async function waitTiles(page, body, timeout = 180_000) {
  await page.waitForFunction(
    (b) => {
      const s = window.starsBesideYou?.scene(b);
      if (!s) return false;
      s.requestRender();
      return s.globe.tilesLoaded;
    },
    body,
    { timeout, polling: 500 },
  );
  await page.waitForTimeout(800);
}

async function run(name, viewport, { zoom = false, query = '', fullMoon = false, settle = true } = {}) {
  console.log(`\n== ${name} ${viewport.width}x${viewport.height}`);
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await context.newPage();
  page.setDefaultTimeout(180_000); // screenshots wait for a frame; software WebGL at 4K is slow
  const errors = [];
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(`console: ${m.text()}`);
  });
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('requestfailed', (r) => {
    const host = new URL(r.url()).hostname;
    const why = r.failure()?.errorText ?? '';
    if (IMAGERY_HOSTS.includes(host) && !why.includes('ERR_ABORTED')) errors.push(`request failed: ${r.url()} (${why})`);
  });
  page.on('response', (r) => {
    const host = new URL(r.url()).hostname;
    if (IMAGERY_HOSTS.includes(host) && r.status() >= 400) errors.push(`HTTP ${r.status()}: ${r.url()}`);
  });

  const t0 = Date.now();
  await page.goto(BASE + query, { waitUntil: 'load' });
  try {
    await page.waitForSelector('#loading', { state: 'hidden', timeout: LOAD_TIMEOUT });
    ok(`loading screen left after ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  } catch {
    const msg = await page.locator('#loading-error').textContent().catch(() => '');
    fail(`loading screen never left (${msg || 'no error message shown'})`);
    await page.screenshot({ path: join(SHOTS, `${name}-stuck.png`) });
    await context.close();
    return;
  }

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 0) fail(`horizontal overflow of ${overflow} px`);
  else ok('no horizontal overflow');

  if (settle) {
    await waitTiles(page, 'earth');
    await waitTiles(page, 'moon');
  } else {
    await page.waitForTimeout(5000); // software WebGL at 4K cannot finish every tile in time
  }
  judgeCanvas('earth canvas', await canvasStats(page, 'earth'));
  // The Moon's night side is dark by design; require a lit crescent at least.
  // The Moon is grey: fewer distinct colours than Earth even when fully lit.
  judgeCanvas('moon canvas', await canvasStats(page, 'moon'), { minLit: 0.03, minColours: 24 });
  await page.screenshot({ path: join(SHOTS, `${name}-page.png`) });

  if (fullMoon) {
    // Full Moon: the whole near side is lit. Tycho's rays must be south of centre, Imbrium north-west.
    await page.locator('#moon-pane').screenshot({ path: join(SHOTS, `${name}-moon-home.png`) });
    await page.evaluate(() => window.starsBesideYou.flyTo('moon', -25, -8, 2300, 0));
    await waitTiles(page, 'moon');
    judgeCanvas('moon near side, south (full Moon)', await canvasStats(page, 'moon'));
    await page.locator('#moon-pane').screenshot({ path: join(SHOTS, `${name}-moon-south.png`) });
  }

  if (zoom) {
    // Iberian peninsula.
    await page.evaluate(() => window.starsBesideYou.flyTo('earth', 40.0, -4.0, 1500, 0));
    await waitTiles(page, 'earth');
    judgeCanvas('earth zoomed (Iberia)', await canvasStats(page, 'earth'));
    await page.locator('#earth-pane').screenshot({ path: join(SHOTS, `${name}-earth-iberia.png`) });
    // Closer: Sierra de Guadarrama / Madrid, where the Sentinel-2 layer is fully shown.
    await page.evaluate(() => window.starsBesideYou.flyTo('earth', 40.6, -3.9, 220, 0));
    await waitTiles(page, 'earth');
    judgeCanvas('earth close (Madrid, Sentinel-2)', await canvasStats(page, 'earth'));
    await page.locator('#earth-pane').screenshot({ path: join(SHOTS, `${name}-earth-madrid.png`) });
    // Tycho crater, 43.3 S 11.2 W.
    await page.evaluate(() => window.starsBesideYou.flyTo('moon', -43.3, -11.2, 450, 0));
    await waitTiles(page, 'moon');
    judgeCanvas('moon zoomed (Tycho)', await canvasStats(page, 'moon'));
    await page.locator('#moon-pane').screenshot({ path: join(SHOTS, `${name}-moon-tycho.png`) });
    const far = await page.evaluate(() => window.starsBesideYou.toCanvas('moon', 43.3, 168.8));
    if (far !== null) fail('toCanvas did not return null for a far-side point');
    else ok('toCanvas returns null on the far side');
    // Credits dialog opens and closes from the keyboard.
    await page.click('#credits-button');
    const open = await page.evaluate(() => document.getElementById('credits-dialog').open);
    await page.screenshot({ path: join(SHOTS, `${name}-credits.png`) });
    await page.keyboard.press('Escape');
    if (!open) fail('credits dialog did not open');
    else ok('credits dialog opens');
  }

  for (const e of errors) fail(e);
  if (!errors.length) ok('no console errors, page errors or failed imagery requests');
  await context.close();
}

const only = process.argv.find((a) => a.startsWith('--only='))?.slice(7).split(',');
const want = (n) => !only || only.includes(n);
try {
  if (want('desktop')) await run('desktop', { width: 1440, height: 900 }, { zoom: true });
  if (want('phone')) await run('phone', { width: 375, height: 812 }, { zoom: true });
  if (want('fullmoon')) await run('fullmoon', { width: 1440, height: 900 }, { query: '?time=2026-11-24T12:00:00Z', fullMoon: true });
  if (want('tablet')) await run('tablet', { width: 768, height: 1024 });
  if (want('uhd') && !process.argv.includes('--skip-4k')) await run('uhd', { width: 3840, height: 2160 }, { settle: false });
} finally {
  await browser.close();
  server.close();
}

console.log(`\nscreenshots: ${SHOTS}`);
if (failures.length) {
  console.log(`${failures.length} failure(s)`);
  process.exit(1);
}
console.log('smoke test passed');
