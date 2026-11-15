// Interface wording that is not in the bundle: the short mission names and the one line on what
// each mission tests (no threshold or weight is typed here; those come from missions.json).

import type { Mission } from '../data/types.ts';

const SHORT: Record<string, { name: string; line: string; video: string }> = {
  rover: {
    name: 'Rover',
    line: 'Driving a rover over bare, gently sloping ground of moderate roughness.',
    video: 'rover',
  },
  solar: {
    name: 'Solar panels',
    line: 'Placing solar arrays where the Sun is strong, high and the ground is flat.',
    video: 'solar',
  },
  lunar_base: {
    name: 'Lunar base',
    line: 'Exposing base equipment to large daily temperature swings and deep cold.',
    video: 'lunar-base',
  },
};

export function missionName(m: Mission): string {
  return SHORT[m.id]?.name ?? m.title;
}

export function missionLine(m: Mission): string {
  return SHORT[m.id]?.line ?? m.title;
}

/** Folder under public/media/ that holds the mission's video. */
export function missionMediaFolder(m: Mission): string {
  return SHORT[m.id]?.video ?? m.id.replace(/_/g, '-');
}

export function statusWords(m: Mission): string {
  return m.threshold_status.status === 'provisional' ? 'Provisional thresholds' : 'Team design values';
}

export const PURPOSE =
  'Find the places on Earth where a Moon mission can be tested, see how closely each one resembles the Moon, and why.';
export const AUDIENCE = 'For teams that test lunar rovers, solar arrays and base equipment on Earth before they fly.';
