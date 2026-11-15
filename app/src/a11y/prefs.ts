// Preferences remembered between visits (localStorage), wrapped so that a browser without storage
// (private mode, blocked site data) still works: the value then lives for this page only.

const memory = new Map<string, string>();

export const PREF_AUDIO = 'starsBesideYou.audioGuide';
export const PREF_PALETTE = 'starsBesideYou.colourBlind';

export function readPref(key: string): string | null {
  try {
    const v = window.localStorage.getItem(key);
    if (v !== null) return v;
  } catch {
    /* storage unavailable */
  }
  return memory.get(key) ?? null;
}

export function writePref(key: string, value: string): void {
  memory.set(key, value);
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* storage unavailable: kept for this page only */
  }
}

export function readFlag(key: string): boolean {
  return readPref(key) === 'on';
}

export function writeFlag(key: string, on: boolean): void {
  writePref(key, on ? 'on' : 'off');
}
