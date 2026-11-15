#!/usr/bin/env node
// Live-site check (read only): loads a deployed URL in headless Chromium and checks the audio guide,
// the three missions, the fifteen pairs, the videos, the switches and the phone layout.
// "Plays" means the media element decodes and its currentTime advances: a headless browser has no
// sound card, so no person hears anything.
// Usage: node tests/live.mjs https://stars-beside-you.vercel.app [shots_dir] [--autoplay]
// Expected durations come from ffprobe on the local public/audio files when ffprobe is installed.
import { createRequire } from 'node:module';
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const BASE = (args[0] || 'https://stars-beside-you.vercel.app').replace(/\/$/, '');
const SHOTS = args[1] || join(APP, 'tests', 'live-shots');
const AUTOPLAY = process.argv.includes('--autoplay');
mkdirSync(SHOTS, { recursive: true });

const AUD = join(APP, 'public', 'audio');
const transcripts = JSON.parse(readFileSync(join(AUD, 'transcripts.json'), 'utf8'));
const missionsJson = JSON.parse(readFileSync(join(APP, 'public', 'data', 'v2', 'missions.json'), 'utf8'));
const ML = Array.isArray(missionsJson.missions) ? missionsJson.missions : Object.values(missionsJson.missions);
const top5 = Object.fromEntries(ML.map((m) => [m.id, m.top5]));
const dur = {};
for (const f of readdirSync(AUD).filter((f) => f.endsWith('.mp3'))) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', join(AUD, f)], { encoding: 'utf8' });
  dur[f] = r.status === 0 ? Number(r.stdout.trim()) : null;
}

const faults = [];
const fault = (s) => { faults.push(s); console.log('FAULT', s); };
const rows = {};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const MISSIONS = [['rover', '1', 'm1_rover.mp3', 'rover'], ['solar', '2', 'm2_solar.mp3', 'solar'], ['lunar_base', '3', 'm3_base.mp3', 'base']];
const HEAD = { rover: 'Five of the 254 sites tied at the top of our model', solar: 'Five of the highest-scoring analogs in our model', lunar_base: 'Five of the highest-scoring analogs in our model' };
const BANNED = /five best|the best (analogs|sites|places|pairs|five)/i;

async function newPage(browser, phone, dsf = 1) {
  const ctx = await browser.newContext(phone ? { viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, deviceScaleFactor: dsf } : { viewport: { width: 1440, height: 900 }, deviceScaleFactor: dsf });
  const p = await ctx.newPage();
  p.errors = []; p.failed = [];
  await p.addInitScript(() => {
    window.__media = new Set();
    const play = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () { window.__media.add(this); return play.apply(this, arguments); };
  });
  p.on('console', (m) => { if (m.type() === 'error') p.errors.push(m.text()); });
  p.on('pageerror', (e) => p.errors.push('pageerror: ' + e.message));
  p.on('requestfailed', (r) => { const u = r.url(); const why = r.failure()?.errorText || ''; if (!/ERR_ABORTED/.test(why) || !/\.(mp3|webm|mp4)/.test(u)) p.failed.push(`${u} ${why}`); });
  p.on('response', (r) => { if (r.status() >= 400) p.failed.push(`${r.url()} HTTP ${r.status()}`); });
  await p.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await sleep(1500);
  return p;
}

const media = (p) => p.evaluate(() => {
  const all = new Set([...document.querySelectorAll('audio,video'), ...(window.__media || [])]);
  return [...all].map((e) => ({ tag: e.tagName, src: e.currentSrc || e.getAttribute('src') || '', paused: e.paused, err: e.error ? e.error.code : null, rs: e.readyState, t: e.currentTime, d: e.duration, muted: e.muted }));
});
const caption = (p) => p.evaluate(() => document.getElementById('caption-text')?.textContent ?? '');

async function checkTrack(p, file, where) {
  await sleep(1200);
  // give a slow first byte up to 10 s more before measuring
  for (let k = 0; k < 20; k++) { const z = (await media(p)).find((m) => m.tag === 'AUDIO' && !m.paused); if (!z || z.rs >= 2) break; await sleep(500); }
  const a = (await media(p)).filter((m) => m.tag === 'AUDIO' && !m.paused);
  await sleep(1500);
  const b = (await media(p)).filter((m) => m.tag === 'AUDIO' && !m.paused);
  const cap = await caption(p);
  const row = { file, where, played: false, heard: null, durOk: false, capEq: cap === transcripts[file], one: a.length === 1 && b.length === 1 };
  if (!row.one) fault(`${file} (${where}): ${a.length}/${b.length} audio elements playing (expected exactly 1): ${JSON.stringify(b.map((x) => x.src))}`);
  const x = b[0], x0 = a[0];
  if (x) {
    const adv = x0 && x.src === x0.src ? x.t - x0.t : 0;
    row.played = x.err == null && x.src.endsWith('/audio/' + file) && (x.rs === 4 || adv >= 1);
    row.adv = +adv.toFixed(2);
    row.heard = Number.isFinite(x.d) ? +x.d.toFixed(2) : null;
    row.durOk = dur[file] != null && row.heard != null && Math.abs(row.heard - dur[file]) <= 0.2;
    if (!x.src.endsWith('/audio/' + file)) fault(`${file} (${where}): playing src is ${x.src}`);
  }
  if (!row.played) fault(`${file} (${where}): not playing ${JSON.stringify(b)}`);
  if (!row.durOk) fault(`${file}: duration ${row.heard} vs file ${dur[file]}`);
  if (!row.capEq) fault(`${file}: caption differs from transcripts.json: "${cap.slice(0, 120)}..."`);
  if (rows[file]) (rows[file].also ||= []).push(row); else rows[file] = row;
  return row;
}

async function screenText(p) {
  return p.evaluate(() => document.body.innerText + '\n' + [...document.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label')).join('\n'));
}

async function setSwitch(p, id, on, viaKey = false) {
  const el = p.locator('#' + id);
  if ((await el.getAttribute('aria-checked')) === String(on)) return;
  if (viaKey) { await el.focus(); await p.keyboard.press('Space'); } else await el.click();
  await sleep(300);
}

const out = { base: BASE, headings: {}, lists: {}, videos: {}, notes: [] };
const browser = await chromium.launch(AUTOPLAY ? { args: ['--autoplay-policy=no-user-gesture-required'] } : {});
try {
  // ---------- desktop, guide on ----------
  const p = await newPage(browser, false, 2);
  out.startCards = await p.locator('button.choice[data-mission]').count();
  if (out.startCards !== 3) fault(`start screen shows ${out.startCards} mission cards`);
  await p.screenshot({ path: join(SHOTS, 'desktop_start.png') });
  const t0 = await screenText(p);
  if (BANNED.test(t0)) fault('start screen contains a banned phrase: ' + t0.match(BANNED)[0]);
  await setSwitch(p, 'switch-audio', true);
  await checkTrack(p, '00_welcome.mp3', 'start');
  for (const [mid, key, intro, pre] of MISSIONS) {
    await p.keyboard.press(key);
    await p.waitForSelector('#top5-title', { timeout: 20000 });
    await checkTrack(p, intro, mid + ' mission');
    const head = (await p.locator('#top5-title').textContent()).trim();
    out.headings[mid] = head;
    if (head !== HEAD[mid]) fault(`${mid} heading "${head}" (expected "${HEAD[mid]}")`);
    const txt = await screenText(p);
    if (BANNED.test(txt)) fault(`${mid} screen contains "${txt.match(BANNED)[0]}"`);
    const list = await p.$$eval('.top5-btn', (bs) => bs.map((b) => ({ id: Number(b.dataset.id), overall: b.dataset.overall, text: b.innerText.replace(/\s+/g, ' ').trim() })));
    out.lists[mid] = list;
    const want = top5[mid].ids, wr = top5[mid].overall_ranks;
    const okIds = JSON.stringify(list.map((l) => l.id)) === JSON.stringify(want);
    // the row prints "Ranked N overall" only when N differs from its place among the five
    const okRanks = !wr || list.every((l, i) => String(wr[i]) === l.overall && (wr[i] === i + 1 || l.text.includes(`Ranked ${wr[i]} overall`)));
    if (!okIds) fault(`${mid} list ids ${list.map((l) => l.id)} vs bundle ${want}`);
    if (!okRanks) fault(`${mid} overall ranks ${list.map((l) => l.overall)} vs bundle ${wr}`);
    if (mid === 'solar') await p.screenshot({ path: join(SHOTS, 'desktop_mission_solar.png') });
    // R repeats the introduction
    await p.keyboard.press('r');
    const rep = await checkTrack(p, intro, mid + ' repeat (R)');
    for (let i = 1; i <= 5; i++) {
      await p.keyboard.press(String(i));
      await sleep(800);
      const file = `${pre}_${i}.mp3`;
      await checkTrack(p, file, `${mid} pair ${i}`);
      const panel = await p.evaluate(() => (document.querySelector('.detail, [data-panel="detail"], .panel') || document.body).innerText);
      const all = await screenText(p);
      if (!/On the Moon/i.test(all) || !/Earth/i.test(all)) fault(`${mid} pair ${i}: both sides not shown`);
      if (/confidence/i.test(all)) fault(`${mid} pair ${i}: a confidence label is shown`);
      if (BANNED.test(all)) fault(`${mid} pair ${i}: banned phrase "${all.match(BANNED)[0]}"`);
      if (mid === 'lunar_base' && !/at the edge of NASA's .{0,80}candidate region/.test(all)) fault(`lunar_base pair ${i}: no "at the edge of NASA's ... candidate region"`);
      if (mid === 'lunar_base' && i === 1) await p.screenshot({ path: join(SHOTS, 'desktop_pair_base1.png') });
      if (i === 1) {
        // the video of the mission
        const start = p.locator('#start-mission');
        if (await start.count()) {
          await start.click();
          await sleep(4000);
          const v = (await media(p)).filter((m) => m.tag === 'VIDEO');
          out.videos[mid] = v.map((x) => ({ src: x.src.split('/').pop(), rs: x.rs, d: x.d, err: x.err }));
          const vv = v[0];
          if (!vv || vv.err != null || vv.rs < 1) fault(`${mid} video not loaded: ${JSON.stringify(v)}`);
          const exp = { solar: 44, lunar_base: 46 }[mid];
          if (vv && exp && Math.round(vv.d) !== exp) fault(`${mid} video duration ${vv.d} (expected ${exp} s)`);
          const aud = (await media(p)).filter((m) => m.tag === 'AUDIO' && !m.paused);
          if (aud.length) out.notes.push(`${mid}: guide audio still playing under the video (${aud[0].src.split('/').pop()})`);
          await p.keyboard.press('Escape');
          await sleep(800);
        } else fault(`${mid}: no "Start the mission" button`);
      }
      await p.keyboard.press('Escape');
      await sleep(800);
      if (!(await p.locator('#top5-title').count())) { fault(`${mid}: Escape from pair ${i} did not return to the mission`); }
    }
    // a pair outside the five offers no track
    if (mid === 'solar') {
      const other = await p.$$eval('.rank-row[data-paired="true"]', (bs, ids) => bs.map((b) => Number(b.dataset.id)).filter((x) => !ids.includes(x)).slice(0, 1), top5[mid].ids);
      if (other.length) {
        await p.locator(`.rank-row[data-id="${other[0]}"]`).first().click();
        await sleep(2500);
        const playing = (await media(p)).filter((m) => m.tag === 'AUDIO' && !m.paused);
        const st = await p.evaluate(() => document.querySelector('.caption-state')?.textContent ?? '');
        out.outsidePair = { id: other[0], playing: playing.map((x) => x.src), state: st };
        if (playing.length) fault(`pair ${other[0]} outside the five plays ${playing[0].src}`);
        await p.keyboard.press('Escape'); await sleep(800);
      } else out.notes.push('no paired ranking row outside the five found');
    }
    await p.keyboard.press('Escape');
    await sleep(1200);
  }
  out.desktopErrors = p.errors; out.desktopFailed = p.failed;
  await p.context().close();

  // ---------- desktop, guide off ----------
  const q = await newPage(browser, false);
  await q.keyboard.press('1');
  await q.waitForSelector('#top5-title', { timeout: 20000 });
  await sleep(2000);
  const play0 = (await media(q)).filter((m) => !m.paused);
  const cap0 = await caption(q);
  out.guideOff = { playing: play0.length, captionEqual: cap0 === transcripts['m1_rover.mp3'] };
  if (play0.length) fault('guide off: something plays');
  if (!out.guideOff.captionEqual) fault('guide off: caption is not the transcript text');
  // colour-blind switch persists; Tab reaches both switches
  await setSwitch(q, 'switch-palette', true, true);
  await q.reload({ waitUntil: 'networkidle' }); await sleep(1500);
  out.paletteAfterReload = await q.locator('#switch-palette').getAttribute('aria-checked');
  if (out.paletteAfterReload !== 'true') fault('colour-blind mode not kept after reload');
  await setSwitch(q, 'switch-palette', false, true);
  const reached = new Set();
  await q.evaluate(() => document.activeElement?.blur());
  for (let i = 0; i < 40; i++) { await q.keyboard.press('Tab'); const id = await q.evaluate(() => document.activeElement?.id); if (id) reached.add(id); }
  out.tabReaches = ['switch-audio', 'switch-palette'].filter((x) => reached.has(x));
  if (out.tabReaches.length !== 2) fault('Tab does not reach both switches: ' + out.tabReaches);
  out.offErrors = q.errors; out.offFailed = q.failed;
  await q.context().close();

  // ---------- phone ----------
  const m = await newPage(browser, true, 2);
  await m.screenshot({ path: join(SHOTS, 'phone_start.png') });
  const lay = await m.evaluate(() => {
    const cv = [...document.querySelectorAll('canvas')].map((c) => c.getBoundingClientRect()).filter((r) => r.width > 50).map((r) => ({ x: r.x, y: r.y, w: r.width, h: r.height }));
    const card = document.querySelector('button.choice[data-mission]')?.getBoundingClientRect();
    const cap = document.getElementById('caption-text');
    const cs = cap ? getComputedStyle(cap) : null;
    return { canvases: cv, card: card && { top: card.top, bottom: card.bottom }, capClipped: cap ? cap.scrollHeight > cap.clientHeight + 1 && cs.overflow !== 'visible' : null, capLineClamp: cs?.webkitLineClamp, scrollW: document.documentElement.scrollWidth };
  });
  out.phone = lay;
  const cvs = lay.canvases;
  if (cvs.length < 2 || !(cvs[1].y >= cvs[0].y + cvs[0].h - 2) || cvs.some((c) => c.h < 50)) fault('phone: globes not stacked with height ' + JSON.stringify(cvs));
  if (lay.capClipped) fault('phone: caption clipped');
  if (!lay.card || lay.card.bottom > 812) fault('phone: first mission card not on the first screen ' + JSON.stringify(lay.card));
  if (lay.scrollW > 375) fault('phone: horizontal scroll ' + lay.scrollW);
  await m.locator('#switch-audio').tap(); await sleep(300);
  await checkTrack(m, '00_welcome.mp3', 'phone start (tap)');
  await m.locator('button.choice[data-mission="solar"]').tap();
  await m.waitForSelector('#top5-title', { timeout: 20000 });
  await checkTrack(m, 'm2_solar.mp3', 'phone solar mission (tap)');
  await m.locator('.top5-btn').first().tap();
  await checkTrack(m, 'solar_1.mp3', 'phone solar pair 1 (tap)');
  await m.screenshot({ path: join(SHOTS, 'phone_pair_solar1.png') });
  out.phoneErrors = m.errors; out.phoneFailed = m.failed;
  await m.context().close();
} finally {
  await browser.close();
}
out.autoplayFlag = AUTOPLAY;
out.durations = dur;
out.rows = rows;
out.faults = faults;
writeFileSync(join(SHOTS, 'live-result.json'), JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
console.log(faults.length ? `NOT YET: ${faults.length} fault(s)` : 'GO: no fault');
process.exit(faults.length ? 1 : 0);
