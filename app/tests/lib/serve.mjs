// Static server for dist/ with byte ranges (video), used by the flow test. `dataDir`, when given,
// is served at /data/v2/ instead of the copy in dist/ (to test another bundle variant without
// touching public/data). `block` lists URL path suffixes answered with 404 (forced failures).

import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize } from 'node:path';

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.svg': 'image/svg+xml', '.woff2': 'font/woff2',
  '.woff': 'font/woff', '.wasm': 'application/wasm', '.xml': 'application/xml', '.glb': 'model/gltf-binary',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.vtt': 'text/vtt; charset=utf-8', '.bin': 'application/octet-stream', '.mp3': 'audio/mpeg',
};

export async function serve(dist, { dataDir = null } = {}) {
  const state = { dataDir, block: [] };
  const server = createServer((req, res) => {
    const url = new URL(req.url, 'http://x');
    let path = decodeURIComponent(url.pathname);
    if (state.block.some((b) => path.endsWith(b))) return void res.writeHead(404).end('not found');
    let root = dist;
    if (state.dataDir && path.startsWith('/data/v2/')) {
      root = state.dataDir;
      path = path.slice('/data/v2'.length);
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
  return { base: `http://127.0.0.1:${server.address().port}/`, state, close: () => new Promise((r) => server.close(r)) };
}
