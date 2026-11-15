// Interface wording that is not in the bundle: the short mission names and the one line on what
// each mission tests (no threshold or weight is typed here; those come from missions.json).

import type { DataStore } from '../data/store.ts';
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
    ? 'Find the places on Earth where a Moon mission can be tested, each paired with the place on the Moon it resembles, with the values of both side by side, and see why.'
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

/** A bundle sentence with the team's quoted class names ('regolito') shown in English ('regolith'). */
export function classWordsIn(text: string): string {
  return text.replace(/'([a-z]+)'/g, (all, w: string) => (CLASS_WORDS[w] ? `'${CLASS_WORDS[w]}'` : all));
}

/** The first sentence of a bundle text (the plain part of a caveat; the full text stays in the sources). */
export function firstSentence(text: string): string {
  return /^.*?\.(?=\s|$)/.exec(text)?.[0] ?? text;
}

/** The region label rule in plain words (ASSUMPTIONS 0.9 item 6). */
export const REGION_CAVEAT = 'The region name is taken from the nearest populated place (GeoNames) and can be wrong.';
export const AUDIENCE = 'For teams that test lunar rovers, solar arrays and base equipment on Earth before they fly.';

/** The role of a similarity variable in words. */
export function roleWord(role: string): string {
  return role === 'key' ? 'key variable' : role === 'secondary' ? 'secondary variable' : role.replace(/_/g, ' ');
}

/**
 * Who set a tolerance, in plain words: the bundle's tolerance_set_by up to its first colon (the rest
 * names files and line numbers, kept for reviewers in "Technical notes").
 */
export function setByWords(text: string): string {
  // up to the first ": " (a clock time such as 08:55 stays), without brackets that point at documents
  return text
    .split(': ')[0]
    .replace(/\s*\([^()]*(?:\/|\.md|\.py|\.json)[^()]*\)/g, '')
    .trim();
}

const LEVEL_PLAIN: Record<string, string> = { MEASURED: 'measured', DERIVED: 'derived', MODELLED: 'modelled', NO_DATA: 'no data', UNDOCUMENTED: 'undocumented' };

/**
 * A bundle sentence written for the engine's record (known limitations, notes), in plain words for the
 * interface: references to files, code and columns in brackets are left out, variable names become
 * their labels, mission ids their names, class names English, interval notation words. The bundle's
 * approved web texts (similarity.json texts) are never passed through this: they are shown verbatim.
 */
export function plainText(store: DataStore, text: string, mission?: Mission): string {
  const all = store.missionsJson.missions;
  const missions = mission ? [mission, ...all.filter((x) => x !== mission)] : all;
  let t = text;
  const technical = /\.json|\.py|\.csv|\.bin|\.md\b|docs\/|\bline \d|[a-z0-9]_[a-z0-9]|\w\.\w+\(|\bfacts\./i;
  // brackets that only point at files, code or columns
  for (let k = 0; k < 2; k++) t = t.replace(/\s*\(([^()]*)\)/g, (all, inner: string) => (technical.test(inner) ? '' : all));
  // facts.<key>: the value itself
  t = t.replace(/\bfacts\.([a-z0-9_]+)/g, (_all, key: string) => {
    for (const m of missions) {
      const v = (m as unknown as { facts?: Record<string, unknown> }).facts?.[key];
      if (typeof v === 'number') return /lat/.test(key) ? `${v}°` : String(v);
    }
    return 'a stated limit';
  });
  // mission ids, variable names, other snake_case words
  t = t.replace(/\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g, (w) => {
    const m = missions.find((x) => x.id === w);
    if (m) return missionName(m);
    const v = store.variable(w);
    if (v) return v.label.toLowerCase();
    const pv = missions.flatMap((x) => x.similarity.variables ?? []).find((x) => x.variable === w);
    if (pv) return pv.label.toLowerCase();
    if (w === 'analog_finder') return "the repository's analogue finder";
    return w.replace(/_/g, ' ');
  });
  t = t.replace(/\b(MEASURED|DERIVED|MODELLED|NO_DATA|UNDOCUMENTED)\b/g, (w) => LEVEL_PLAIN[w] ?? w.toLowerCase());
  t = t.replace(/\[(-?[\d.,]+), inf\]/g, 'at least $1').replace(/\[-inf, (-?[\d.,]+)\]/g, 'at most $1').replace(/\[(-?[\d.,]+), (-?[\d.,]+)\]/g, '$1 to $2');
  t = t.replace(/\|lat\|\s*<=\s*([\d.]+)(?:°| deg)?/g, 'latitude within $1° of the equator').replace(/\s<=\s/g, ' at most ').replace(/\s>=\s/g, ' at least ');
  t = t.replace(/(\d) deg\b/g, '$1°').replace(/\bkWh\/m2\/day\b/g, 'kWh/m²/day');
  t = classWordsIn(t);
  // any other code-like name (product ids such as LDEM_16): underscores read as spaces
  t = t.replace(/([A-Za-z0-9])_(?=[A-Za-z0-9])/g, '$1 ');
  t = t.replace(/\s{2,}/g, ' ').replace(/\s+([.,;:])/g, '$1').trim();
  return t.replace(/(^|[.!?]\s+)([a-z])/g, (_all, p: string, c: string) => p + c.toUpperCase());
}

/** Why a point has no twin, by kind (missions.json similarity.nopair_kinds), in a few plain words for the list. */
const NOPAIR_WORDS: Record<string, string> = {
  key_value_missing_on_earth: 'a key value is missing on Earth',
  no_zone_cell_within_bound: 'no cell of the zone is close enough in a key value',
  no_joint_match: 'each value alone has a close lunar cell, but no single cell is within every tolerance at once',
  no_cell_meets_thermal_position: 'no cell of the zone matches the thermal position',
  no_cell_meets_terrain: 'no cell of the zone matches the terrain',
  no_cell_meets_either: 'no cell matches either the thermal position or the terrain',
  no_single_cell_meets_both: 'some cells match the thermal position and others the terrain, but no single cell matches both',
};
export function noPairKindWords(kind: string): string {
  return NOPAIR_WORDS[kind] ?? kind.replace(/_/g, ' ');
}

/** A known limitation that describes the z-score similarity, for a mission whose rule no longer uses z-scores. */
export function staleForRule(store: DataStore, m: Mission, text: string): boolean {
  if (!store.isValueRule(m.id)) return false;
  if (/\bz-scores?\b/i.test(text)) return true;
  // "<variable> ... is a suitability criterion only" for a variable the similarity now compares
  const used = store.pairVariables(m.id).flatMap((d) => [d.variable, d.sides?.EARTH?.column ?? '']).filter(Boolean);
  return /suitability criterion only/i.test(text) && used.some((c) => new RegExp(`\\b${c}\\b`).test(text));
}

/** A product or file name for display: underscores read as spaces ("LOLA LDEM_16" -> "LOLA LDEM 16"). */
export function plainName(name: string): string {
  return name.replace(/_/g, ' ');
}
