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

/** The purpose sentence; with twins the result is a pair (an Earth place and its lunar match). */
export function purposeText(twins: boolean): string {
  return twins
    ? 'Find the places on Earth where a Moon mission can be tested, each paired with the place on the Moon it matches (each world measured on its own scale), and see why.'
    : 'Find the places on Earth where a Moon mission can be tested, see how each one compares with the Moon (each world measured on its own scale), and why.';
}

/**
 * English display words for the team's class names (variables.json categories are kept verbatim in
 * Spanish in the bundle). Display only: the bundle's values, thresholds and utilities are unchanged.
 */
export const CLASS_WORDS: Record<string, string> = {
  roca: 'rock',
  regolito: 'regolith',
  arena: 'sand',
  suelo: 'soil',
  hielo: 'ice',
  agua: 'water',
  continuo: 'continuous',
  discontinuo: 'discontinuous',
  esporadico: 'sporadic',
  ninguno: 'none',
};

export function classWord(c: string): string {
  return CLASS_WORDS[c] ?? c;
}

/** The region label rule in plain words (ASSUMPTIONS 0.9 item 6). */
export const REGION_CAVEAT = 'The region name is taken from the nearest populated place (GeoNames) and can be wrong.';
export const AUDIENCE = 'For teams that test lunar rovers, solar arrays and base equipment on Earth before they fly.';
