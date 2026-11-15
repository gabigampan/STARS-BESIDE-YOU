#!/usr/bin/env node
// Deterministic frame-by-frame renderer.
//   node render.js scenarios/solar.json --work <dir> [--frames a:b] [--stills 1.5,20] [--encode-only] [--aa 0]
// Steps the scene time frame by frame (never real time), screenshots each 1920x1080 frame to PNG,
// logs the values shown on the panel (values.jsonl), then encodes MP4 / WebM / posters / captions.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const { chromium } = require('playwright');

const HERE = __dirname;
const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? argv[i + 1] : d; };
const flag = (k) => argv.includes('--' + k);
const scPath = path.resolve(argv[0]);
const SC = JSON.parse(fs.readFileSync(scPath, 'utf8'));
const WORK = path.resolve(opt('work', path.join(HERE, 'build')));
const TW = path.join(WORK, SC.name);
const FR = path.join(TW, 'frames');
const OUT = path.resolve(path.dirname(scPath), SC.output_dir);
const FFMPEG = '/usr/bin/ffmpeg', FFPROBE = '/usr/bin/ffprobe';
const NF = Math.round(SC.duration_s * SC.fps);

const MIME = { '.js': 'text/javascript', '.html': 'text/html', '.json': 'application/json', '.png': 'image/png' };
function serve() {
  return new Promise((res) => {
    const srv = http.createServer((req, rsp) => {
      const u = decodeURIComponent(req.url.split('?')[0]);
      let f = null;
      if (u === '/' || u === '/index.html') f = path.join(HERE, 'page', 'index.html');
      else if (u === '/scenario.json') f = scPath;
      else if (u.startsWith('/page/')) f = path.join(HERE, 'page', u.slice(6));
      else if (u.startsWith('/three/')) f = path.join(HERE, 'node_modules', 'three', u.slice(7));
      else if (u.startsWith('/work/')) f = path.join(TW, u.slice(6));
      if (!f || !fs.existsSync(f)) { rsp.writeHead(404); rsp.end(); return; }
      rsp.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
      fs.createReadStream(f).pipe(rsp);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

async function openPage(srv) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: SC.width, height: SC.height }, deviceScaleFactor: 1 });
  const logs = [];
  page.on('console', (m) => logs.push(m.text()));
  page.on('pageerror', (e) => logs.push('PAGEERROR ' + e.message));
  await page.goto(`http://127.0.0.1:${srv.address().port}/?aa=${opt('aa', '1')}`);
  try { await page.waitForFunction(() => window.__ready === true, null, { timeout: 300000 }); }
  catch (e) { console.error(logs.join('\n')); throw e; }
  const gl = await page.evaluate(() => { const g = document.getElementById('gl').getContext('webgl2'); const d = g.getExtension('WEBGL_debug_renderer_info'); return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER); });
  console.log('WebGL renderer:', gl);
  return { browser, page, logs, gl };
}

async function renderFrames() {
  fs.mkdirSync(FR, { recursive: true });
  const srv = await serve();
  const { browser, page, logs, gl } = await openPage(srv);
  if (flag('topdown')) {
    await page.evaluate(() => window.renderTopdown());
    await page.screenshot({ path: path.join(TW, 'check_topdown_render.png') });
    console.log('wrote', path.join(TW, 'check_topdown_render.png'));
    await browser.close(); srv.close(); return;
  }
  const stills = opt('stills', null);
  if (stills) {
    const sd = path.join(TW, 'stills'); fs.mkdirSync(sd, { recursive: true });
    for (const s of stills.split(',')) {
      const t = parseFloat(s), t0 = Date.now();
      const v = await page.evaluate((tt) => window.renderAt(tt), t);
      await page.screenshot({ path: path.join(sd, `still_${t.toFixed(2)}.png`) });
      console.log(`still t=${t} ${(Date.now() - t0)} ms`, JSON.stringify(v));
    }
    if (logs.length) console.log(logs.join('\n'));
    await browser.close(); srv.close(); return;
  }
  const [a, b] = (opt('frames', `0:${NF - 1}`)).split(':').map(Number);
  const vlog = path.join(TW, 'values.jsonl');
  const times = [];
  for (let i = a; i <= b; i++) {
    const fp = path.join(FR, `f${String(i).padStart(5, '0')}.png`);
    if (fs.existsSync(fp) && !flag('force')) continue;
    const t = i / SC.fps, t0 = Date.now();
    const v = await page.evaluate((tt) => window.renderAt(tt), t);
    await page.screenshot({ path: fp + '.tmp.png' });
    fs.renameSync(fp + '.tmp.png', fp);
    fs.writeFileSync(path.join(FR, `v${String(i).padStart(5, '0')}.json`), JSON.stringify({ i, ...v }));
    times.push(Date.now() - t0);
    if (i % 30 === 0 || i === b) console.log(`frame ${i}/${NF - 1} ${times[times.length - 1]} ms (mean ${Math.round(times.reduce((x, y) => x + y, 0) / times.length)} ms)`);
  }
  if (logs.length) console.log(logs.slice(0, 20).join('\n'));
  fs.writeFileSync(path.join(TW, `timing_${a}_${b}.json`), JSON.stringify({ frames: times.length, mean_ms: times.reduce((x, y) => x + y, 0) / Math.max(1, times.length), gl }));
  await browser.close(); srv.close();
  // gather values
  const vals = [];
  for (let i = 0; i < NF; i++) { const p = path.join(FR, `v${String(i).padStart(5, '0')}.json`); if (fs.existsSync(p)) vals.push(fs.readFileSync(p, 'utf8')); }
  fs.writeFileSync(vlog, vals.join('\n') + '\n');
}

function run(args) { console.log('ffmpeg', args.join(' ')); execFileSync(FFMPEG, ['-hide_banner', '-loglevel', 'error', '-y', ...args], { stdio: 'inherit', cwd: TW }); }

function encode() {
  fs.mkdirSync(OUT, { recursive: true });
  const n = SC.name, inp = ['-framerate', String(SC.fps), '-i', path.join(FR, 'f%05d.png')];
  const crf = String(SC.encode?.x264_crf ?? 20);
  run([...inp, '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-profile:v', 'high', '-level:v', '4.1', '-pix_fmt', 'yuv420p',
    '-r', String(SC.fps), '-movflags', '+faststart', '-an', path.join(OUT, `${n}.mp4`)]);
  const vcrf = String(SC.encode?.vp9_crf ?? 34), plog = path.join(TW, 'vp9pass');
  run([...inp, '-c:v', 'libvpx-vp9', '-crf', vcrf, '-b:v', '0', '-pix_fmt', 'yuv420p', '-row-mt', '1', '-tile-columns', '2', '-deadline', 'good', '-cpu-used', '2', '-pass', '1', '-passlogfile', plog, '-an', '-f', 'null', '/dev/null']);
  run([...inp, '-c:v', 'libvpx-vp9', '-crf', vcrf, '-b:v', '0', '-pix_fmt', 'yuv420p', '-row-mt', '1', '-tile-columns', '2', '-deadline', 'good', '-cpu-used', '2', '-pass', '2', '-passlogfile', plog, '-an', path.join(OUT, `${n}.webm`)]);
  const pf = path.join(FR, `f${String(Math.round(SC.poster_s * SC.fps)).padStart(5, '0')}.png`);
  run(['-i', pf, '-q:v', '2', path.join(OUT, `${n}-poster.jpg`)]);
  run(['-i', pf, '-c:v', 'libwebp', '-quality', '88', path.join(OUT, `${n}-poster.webp`)]);
}

// ------------------------------------------------------------------ captions from the logged values
function ts(s) { const m = Math.floor(s / 60), x = s - m * 60; return `${String(m).padStart(2, '0')}:${x.toFixed(3).padStart(6, '0')}`; }
function captions() {
  const vals = fs.readFileSync(path.join(TW, 'values.jsonl'), 'utf8').trim().split('\n').map((l) => JSON.parse(l));
  const at = (t) => vals[Math.min(vals.length - 1, Math.round(t * SC.fps))];
  const C = SC.captions;
  for (const lang of ['en', 'es']) {
    const L = C[lang], dec = lang === 'es' ? ',' : '.';
    const num = (x, d = 1) => (Math.abs(x) < 0.5 * Math.pow(10, -d) ? 0 : x).toFixed(d).replace('.', dec);
    const big = (x) => Math.round(x).toLocaleString(lang === 'es' ? 'es-ES' : 'en-US', { useGrouping: 'always' });
    let out = `WEBVTT - ${L.header}\n\nNOTE\n${L.note}\n\n`;
    const cues = C.cue_times;
    cues.forEach((t0, k) => {
      const t1 = k + 1 < cues.length ? cues[k + 1] : SC.duration_s;
      const v = at(t0);
      const lines = [];
      if (L.text[k]) lines.push(L.text[k]);
      if (t0 < SC.sun.sim_end_s) {
        const st = L.status[v.status] || v.status;
        if (SC.name === 'solar') {
          lines.push(`${st} · ${L.sun} ${num(v.sunElev)}° / ${L.az} ${num(v.sunAz)}° · ${L.hz} ${num(v.horizon)}°`);
          lines.push(`${L.power} ${big(v.P)} W/m² · ${L.energy} ${num(v.E, 2)} kWh/m² · ${num(v.days)} ${L.days} · ×${big(Number(v.compression.toPrecision(3)))}`);
        } else {
          lines.push(`${st} · ${L.temp} ${num(v.T)} K (${num(v.T - 273.15)} °C, ${L.model}) · ${L.sun} ${num(v.sunElev)}° / ${L.az} ${num(v.sunAz)}°`);
          lines.push(`${num(v.days)} ${L.days} · ×${big(Number(v.compression.toPrecision(3)))}`);
        }
      }
      out += `${k + 1}\n${ts(t0)} --> ${ts(t1)}\n${lines.join('\n')}\n\n`;
    });
    fs.writeFileSync(path.join(OUT, `${SC.name}.${lang}.vtt`), out);
  }
}

function probe() {
  const res = {};
  for (const f of [`${SC.name}.mp4`, `${SC.name}.webm`, `${SC.name}-poster.jpg`, `${SC.name}-poster.webp`, `${SC.name}.en.vtt`, `${SC.name}.es.vtt`]) {
    const p = path.join(OUT, f);
    const size = fs.statSync(p).size;
    let info = null;
    if (!f.endsWith('.vtt')) info = JSON.parse(execFileSync(FFPROBE, ['-v', 'error', '-count_frames', '-show_entries', 'stream=codec_name,profile,level,pix_fmt,width,height,r_frame_rate,nb_read_frames,duration:format=duration,bit_rate,format_name', '-of', 'json', p]).toString());
    else execFileSync(FFPROBE, ['-v', 'error', p]);
    res[f] = { size, info };
  }
  const buf = fs.readFileSync(path.join(OUT, `${SC.name}.mp4`));
  res.faststart = { moov_offset: buf.indexOf('moov'), mdat_offset: buf.indexOf('mdat') };
  fs.writeFileSync(path.join(TW, 'ffprobe.json'), JSON.stringify(res, null, 1));
  console.log(JSON.stringify(res, null, 1));
}

(async () => {
  if (!flag('encode-only') && !flag('captions-only')) await renderFrames();
  if (opt('stills', null) || opt('frames', null) || flag('topdown')) return;
  if (!flag('captions-only')) encode();
  captions(); probe();
})().catch((e) => { console.error(e); process.exit(1); });
