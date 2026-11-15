// Build-time index of the mission videos present in public/media/<folder>/ (written as
// media-index.json next to index.html). The app reads it at start and offers "Start mission" only
// for missions whose files exist. Each folder holds <name>.mp4 and/or <name>.webm, optionally
// <name>-poster.jpg|webp, <name>.en.vtt, <name>.es.vtt and a README.md whose
// "Credit line to show in the app" is used verbatim.

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import type { Plugin } from 'vite';

export interface MediaEntry {
  folder: string;
  name: string;
  sources: { src: string; type: string }[];
  poster: string | null;
  tracks: { src: string; srclang: string; label: string; default?: boolean }[];
  credit: string | null;
}

export interface MediaIndex {
  videos: Record<string, MediaEntry>;
}

const LANGS: Record<string, string> = { en: 'English', es: 'Español' };

export function buildMediaIndex(publicDir: string): MediaIndex {
  const root = join(publicDir, 'media');
  const videos: Record<string, MediaEntry> = {};
  if (!existsSync(root)) return { videos };
  for (const folder of readdirSync(root).sort()) {
    const dir = join(root, folder);
    if (!statSync(dir).isDirectory()) continue;
    const files = readdirSync(dir).filter((f) => statSync(join(dir, f)).size > 0);
    const video = files.find((f) => /\.(webm|mp4)$/.test(f));
    if (!video) continue;
    const name = video.replace(/\.(webm|mp4)$/, '');
    const url = (f: string) => `media/${folder}/${f}`;
    const sources = (['webm', 'mp4'] as const)
      .filter((ext) => files.includes(`${name}.${ext}`))
      .map((ext) => ({ src: url(`${name}.${ext}`), type: `video/${ext}` }));
    const poster = [`${name}-poster.jpg`, `${name}-poster.webp`].find((f) => files.includes(f)) ?? null;
    const tracks = Object.keys(LANGS)
      .filter((l) => files.includes(`${name}.${l}.vtt`))
      .map((l, i) => ({ src: url(`${name}.${l}.vtt`), srclang: l, label: LANGS[l], ...(i === 0 ? { default: true } : {}) }));
    let credit: string | null = null;
    if (files.includes('README.md')) {
      const readme = readFileSync(join(dir, 'README.md'), 'utf8');
      credit = /Credit line to show in the app:?\**\s*\n+\s*"([^"\n]+)"/i.exec(readme)?.[1] ?? null;
    }
    videos[folder] = { folder, name, sources, poster: poster ? url(poster) : null, tracks, credit };
  }
  return { videos };
}

/** Vite plugin: serves /media-index.json in dev and writes it into the build. */
export function mediaIndexPlugin(publicDir: string): Plugin {
  return {
    name: 'stars-media-index',
    configureServer(server) {
      server.middlewares.use('/media-index.json', (_req, res) => {
        res.setHeader('content-type', 'application/json');
        res.end(JSON.stringify(buildMediaIndex(publicDir)));
      });
    },
    generateBundle() {
      this.emitFile({ type: 'asset', fileName: 'media-index.json', source: JSON.stringify(buildMediaIndex(publicDir), null, 1) });
    },
  };
}
