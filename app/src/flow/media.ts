// Which missions have a video: media-index.json is written at build time from the folders present
// in public/media/ (scripts/mediaIndex.ts). No index, or no entry, means no "Start mission" button.

import type { VideoSpec } from '../modules/video';
import type { Mission } from '../data/types.ts';
import { missionMediaFolder, missionName } from './copy';

interface MediaEntry {
  folder: string;
  name: string;
  sources: { src: string; type: string }[];
  poster: string | null;
  tracks: { src: string; srclang: string; label: string; default?: boolean }[];
  credit: string | null;
}

let index: Record<string, MediaEntry> = {};

export async function loadMediaIndex(): Promise<void> {
  try {
    const res = await fetch('media-index.json');
    if (!res.ok) return;
    const j = (await res.json()) as { videos?: Record<string, MediaEntry> };
    index = j.videos ?? {};
  } catch {
    index = {};
  }
}

export function hasVideo(m: Mission): boolean {
  return (index[missionMediaFolder(m)]?.sources.length ?? 0) > 0;
}

export function videoSpec(m: Mission): VideoSpec | null {
  const e = index[missionMediaFolder(m)];
  if (!e || !e.sources.length) return null;
  const name = missionName(m);
  return {
    title: `${name} mission: 3D simulation`,
    sources: e.sources,
    poster: e.poster ?? undefined,
    tracks: e.tracks,
    credit: e.credit ?? `${name} mission video: 3D simulation by the Stars Beside You team (not real footage)`,
    note: 'A 3D simulation made by the team to show the mission; it is not real footage and was not filmed at the place you picked.',
  };
}
