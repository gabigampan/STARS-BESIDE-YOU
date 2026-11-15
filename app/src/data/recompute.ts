// The browser recompute of docs/DATA_CONTRACT.md "Recompute formulas (browser)", exactly as written
// there: suitability from the exported utilities, similarity from the exported z-scores, final and
// rank. Pure functions with no DOM, so the same code runs in the page and in the Node tests.

/** Python's round(x, 2): the exact binary value of x rounded to 2 decimals, exact ties to even. */
export function pyRound2(x: number): number {
  if (!Number.isFinite(x)) return x;
  const y = x * 100;
  const fl = Math.floor(y);
  const frac = y - fl;
  // Far from a half: the product's rounding error (about 1e-14) cannot change the result.
  if (Math.abs(frac - 0.5) > 1e-7) return Math.round(y) / 100;
  // Near a half: decide from the exact decimal expansion of x (toFixed is exact up to 100 digits).
  const neg = x < 0;
  const s = Math.abs(x).toFixed(100);
  const dot = s.indexOf('.');
  const keep = s.slice(0, dot + 3);
  const rest = s.slice(dot + 3);
  let up: boolean;
  if (rest[0] > '5') up = true;
  else if (rest[0] < '5') up = false;
  else if (/[1-9]/.test(rest.slice(1))) up = true;
  else {
    const last = Number(keep[keep.length - 1]);
    up = last % 2 === 1; // exact tie: to even
  }
  let v = Number(keep);
  if (up) v = (Math.round(v * 100) + 1) / 100;
  return neg ? -v : v;
}

/** numpy.round(x, 2): rint(x * 100) / 100 (round half to even on the product). */
export function npRound2(x: number): number {
  if (!Number.isFinite(x)) return x;
  const y = x * 100;
  const r = Math.round(y);
  if (Math.abs(y - Math.trunc(y)) === 0.5) {
    const f = Math.floor(y);
    return (f % 2 === 0 ? f : f + 1) / 100;
  }
  return r / 100;
}

export interface SuitabilityResult {
  /** 0-100, unrounded; null when no weighted variable has a utility. */
  suitability: number | null;
  /** Share of the total weight that could be used, 0-1. */
  coverage: number;
}

/**
 * suitability = 100 * sum_{v in U} w_v * u_v / sum_{v in U} w_v (sum in V order);
 * coverage = sum_{v in U} w_v / sum_{v in V} w_v. `u[i]` null or NaN = missing.
 */
export function suitabilityOf(u: readonly (number | null)[], w: readonly number[]): SuitabilityResult {
  let num = 0;
  let den = 0;
  let total = 0;
  for (let i = 0; i < w.length; i++) {
    total += w[i];
    const ui = u[i];
    if (ui == null || Number.isNaN(ui)) continue;
    num += w[i] * ui;
    den += w[i];
  }
  return { suitability: den > 0 ? (100 * num) / den : null, coverage: total > 0 ? den / total : 0 };
}

/**
 * d2 = sum nw_f (ze_f - zm_f)^2 over F when every pair is present, else the same sum over the
 * present pairs divided by their summed weights; similarity = numpy.round(100 exp(-decay sqrt(d2)), 2).
 */
export function similarityOf(
  ze: readonly (number | null)[],
  zm: readonly (number | null)[],
  nw: readonly number[],
  decay: number,
): number | null {
  let sum = 0;
  let wPresent = 0;
  let present = 0;
  for (let i = 0; i < nw.length; i++) {
    const a = ze[i];
    const b = zm[i];
    if (a == null || b == null || Number.isNaN(a) || Number.isNaN(b)) continue;
    const d = a - b;
    sum += nw[i] * d * d;
    wPresent += nw[i];
    present++;
  }
  if (present === 0) return null;
  const d2 = present === nw.length ? sum : sum / wPresent;
  return npRound2(100 * Math.exp(-decay * Math.sqrt(d2)));
}

/** final = alpha * similarity + (1 - alpha) * suitability (unrounded suitability). */
export function finalOf(alpha: number, similarity: number, suitability: number): number {
  return alpha * similarity + (1 - alpha) * suitability;
}

/**
 * Ranks (1 = best) by round(final, 2) descending, ties by cell id ascending. `finals[i]` NaN = no
 * final (rank 0 = not ranked). Returns the ranks and the order (indices, best first).
 */
export function rankByFinal(ids: ArrayLike<number>, finals: ArrayLike<number>): { ranks: Int32Array; order: Int32Array } {
  const n = ids.length;
  const keys = new Float64Array(n);
  const idx: number[] = [];
  for (let i = 0; i < n; i++) {
    const f = finals[i];
    if (Number.isNaN(f)) continue;
    keys[i] = pyRound2(f);
    idx.push(i);
  }
  idx.sort((a, b) => keys[b] - keys[a] || ids[a] - ids[b]);
  const ranks = new Int32Array(n);
  idx.forEach((i, k) => (ranks[i] = k + 1));
  return { ranks, order: Int32Array.from(idx) };
}

/**
 * Fast path for the weight sliders: every passing cell of one mission, utilities as one
 * Float64Array per weighted variable (NaN = missing), similarities as stored.
 */
export interface MissionMatrix {
  ids: Int32Array;
  similarity: Float64Array; // NaN = no similarity
  utilities: Float64Array[]; // [variable][cell]
}

export interface MissionScores {
  suitability: Float64Array; // unrounded, NaN = none
  coverage: Float64Array;
  final: Float64Array; // unrounded, NaN = none
  ranks: Int32Array; // 0 = not ranked
  order: Int32Array; // cell positions, best first
}

export function recomputeMission(m: MissionMatrix, weights: readonly number[], alpha: number): MissionScores {
  const n = m.ids.length;
  const nv = weights.length;
  const suitability = new Float64Array(n);
  const coverage = new Float64Array(n);
  const final = new Float64Array(n);
  let total = 0;
  for (let v = 0; v < nv; v++) total += weights[v];
  for (let i = 0; i < n; i++) {
    let num = 0;
    let den = 0;
    for (let v = 0; v < nv; v++) {
      const u = m.utilities[v][i];
      if (u !== u) continue; // NaN
      num += weights[v] * u;
      den += weights[v];
    }
    const s = den > 0 ? (100 * num) / den : NaN;
    suitability[i] = s;
    coverage[i] = total > 0 ? den / total : 0;
    const sim = m.similarity[i];
    final[i] = s === s && sim === sim ? alpha * sim + (1 - alpha) * s : NaN;
  }
  const { ranks, order } = rankByFinal(m.ids, final);
  return { suitability, coverage, final, ranks, order };
}
