// Data store for the engine's bundle v2 (docs/DATA_CONTRACT.md). Loads the first view at start
// (manifest, missions, similarity, variables, places, earth_base and the default mission) and the
// rest on demand: the other mission files, one detail tile per selected cell (all tiles only when
// the weight sliders need every utility), place details and twins (only when the rule has them).
// No DOM: the Node tests import this file directly.

import { finalOf, pairSimilarityOf, pyRound2, similarityOf, suitabilityOf, unrankedOrder, type MissionMatrix } from './recompute.ts';
import type {
  Column,
  Columns,
  FileEntry,
  Gate,
  Level,
  Manifest,
  Mission,
  MissionsJson,
  MissionZonesJson,
  NumArray,
  BundleText,
  PairVariable,
  PlaceholderSpec,
  PlaceDetailJson,
  PlacesJson,
  ReasonCode,
  SimilarityJson,
  SimilarityVariable,
  Twin,
  TwinsJson,
  VariableInfo,
  VariablesJson,
  WeightedVariable,
} from './types.ts';

export const DEFAULT_BASE = 'data/v2/';

export interface FetchResponse {
  ok: boolean;
  status: number;
  statusText?: string;
  json(): Promise<unknown>;
  arrayBuffer(): Promise<ArrayBuffer>;
}
export type Fetcher = (url: string) => Promise<FetchResponse>;

/** A data file could not be read. `message` says what happened and what to do, in plain words. */
export class DataError extends Error {
  readonly file: string;
  readonly detail: string;
  constructor(file: string, detail: string) {
    // The technical detail (HTTP status, network error) goes to the console, not on screen.
    super(
      `The mission data file "${file}" could not be loaded. ` +
        'Check the network connection and reload the page; if it keeps failing, the site was published without its data folder.',
    );
    if (typeof console !== 'undefined') console.warn(`[data] ${file}: ${detail}`);
    this.name = 'DataError';
    this.file = file;
    this.detail = detail;
  }
}

// ---------- binary columns ----------

const LITTLE_ENDIAN_HOST = new Uint8Array(new Uint32Array([1]).buffer)[0] === 1;

export function decodeColumns(buf: ArrayBuffer, entry: FileEntry): Columns {
  const out: Columns = {};
  for (const c of entry.columns ?? []) {
    if (c.offset + 4 * c.length > buf.byteLength) throw new Error(`column ${c.name} runs past the end of ${entry.name}`);
    if (LITTLE_ENDIAN_HOST) {
      out[c.name] = c.type === 'float32' ? new Float32Array(buf, c.offset, c.length) : new Int32Array(buf, c.offset, c.length);
    } else {
      const dv = new DataView(buf, c.offset, 4 * c.length);
      const a = c.type === 'float32' ? new Float32Array(c.length) : new Int32Array(c.length);
      for (let i = 0; i < c.length; i++) a[i] = c.type === 'float32' ? dv.getFloat32(4 * i, true) : dv.getInt32(4 * i, true);
      out[c.name] = a;
    }
  }
  return out;
}

function binarySearch(ids: ArrayLike<number>, id: number): number {
  let lo = 0;
  let hi = ids.length - 1;
  while (lo <= hi) {
    const m = (lo + hi) >> 1;
    if (ids[m] === id) return m;
    if (ids[m] < id) lo = m + 1;
    else hi = m - 1;
  }
  return -1;
}

// ---------- loaded tables ----------

interface Table {
  entry: FileEntry;
  cols: Columns;
  meta: Map<string, Column>;
}

export interface MissionData {
  mission: Mission;
  failBits: Int32Array; // land
  landIndex: Int32Array; // passing -> land position
  passPos: Int32Array; // land -> passing position, -1 = eliminated
  table: Table;
  twin: Int32Array | null; // passing -> lunar id
  /** Revision 5: earth_<m>_pairs.bin of a real-value mission (null for z-score rules). */
  pairs: Table | null;
}

/** Why a passing point has no lunar twin (earth_<m>_pairs.bin nopair_*), with the approved sentence filled in. */
export interface NoPair {
  kind: string;
  variable: PairVariable | null;
  /** The smallest gap found, as the bundle stores it (float32 shown at its shortest decimal); null without an Earth value. */
  gap: number | null;
  /** texts.no_twin_note (or its no_joint_match variant), placeholders filled. */
  sentence: string;
}

/** One similarity variable of a real-value pair, both sides and the difference. */
export interface PairRow {
  def: PairVariable;
  earth: number | null;
  moon: number | null;
  diff: number | null;
  /** s.<v> (0-1); null when the variable has no value on a side. */
  score: number | null;
  /** The weight in use (a similarity slider or the team's). */
  weight: number;
  /** |difference| <= bound (key: 1 x tolerance, secondary: 2 x); null without both values. */
  within: boolean | null;
  /** Further columns a later revision adds for this variable (e.g. percentiles), by their key in pairs_columns. */
  extra: Record<string, number | null>;
  /**
   * Revision 6: when the variable is compared on another scale than its real values (a percentile
   * within each population), `earth`, `moon` and `diff` are the compared values (in def.unit) and
   * `real` holds the real values and their difference (in def.real_unit). Null when compared as is.
   */
  real: { earth: number | null; moon: number | null; diff: number | null; unit: string } | null;
}

/** An approved per-pair sentence of the bundle (a text with pairs-file placeholders), filled for one pair. */
export interface PairSentence {
  key: string;
  text: string;
}

/** A value shown for information next to a pair: both sides and the difference. */
export interface PairInfoRow {
  variable: string;
  label: string;
  unit: string;
  earth: number | string | null;
  moon: number | string | null;
  diff: number | null;
  /** Unit of the difference (a difference of degrees Celsius is in kelvin). */
  diffUnit: string;
  levels: { EARTH: Level | null; MOON: Level | null };
}

/** One value of a cell with its meaning: number, class name, or missing. */
export interface CellValue {
  /** Raw number (float or class index), null when missing. */
  raw: number | null;
  /** Number for numeric variables, the class name for categories, null when missing. */
  value: number | string | null;
}

export interface PlaceLabel {
  country: string | null;
  countryCode: string | null;
  region: string | null;
  nearest: string | null;
  nearestKm: number | null;
  /** "Region, Country", or the country, or null. */
  text: string | null;
}

export interface RankedPoint {
  id: number;
  landPos: number;
  passPos: number;
  lat: number;
  lon: number;
  /** null for a passing point without a final (no lunar twin). */
  rank: number | null;
  final: number | null;
  suitability: number;
  similarity: number | null;
  twinId: number | null;
  /** True when the point has a final score (a twin, or a rule that scores every point). */
  scored: boolean;
  /** How many similarity variables the pair used (earth_<m>.bin sim_vars_used); null in older bundles. */
  simVarsUsed: number | null;
  /** True when the temp_k bit of sim_missing_bits is set (decision 3: mark the pair). */
  missingTemp: boolean;
}

export interface GateRow {
  gate: Gate;
  value: CellValue;
  pass: boolean;
  failed: ReasonCode[];
}

export interface RequiredRow {
  variable: string;
  label: string;
  value: CellValue;
  present: boolean;
  failed: ReasonCode[];
}

export interface BreakdownRow {
  wv: WeightedVariable;
  value: CellValue;
  utility: number | null;
  weight: number;
  contribution: number | null;
  points: number | null;
}

export interface SimilarityRow {
  sv: SimilarityVariable;
  label: string;
  unit: string;
  normWeight: number;
  earth: { value: number | null; z: number | null; level: Level | null };
  moon: { value: number | null; z: number | null; level: Level | null };
  clipped: boolean;
}

export interface InfoRow {
  variable: string;
  label: string;
  unit: string;
  earth: { value: number | string | null; level: Level | null };
  moon: { value: number | string | null; level: Level | null; how: 'mean' | 'commonest' | 'twin' };
}

export interface IceOutcome {
  pass: boolean;
  reasons: ReasonCode[];
  line: string;
  suitability: number | null;
  utilities: { wv: WeightedVariable; value: CellValue; utility: number | null }[];
}

export interface MissionOutcome {
  mission: Mission;
  landPos: number;
  pass: boolean;
  reasons: ReasonCode[];
  /** The one-line elimination reason (elimination_line_rule), empty when the cell passes. */
  line: string;
  common: GateRow[];
  required: RequiredRow[];
  gates: GateRow[];
  breakdown: BreakdownRow[];
  suitability: number | null;
  coverage: number | null;
  similarity: number | null;
  final: number | null;
  rank: number | null;
  confidence: string | null;
  confidenceScore: number | null;
  similarityRows: SimilarityRow[];
  infoRows: InfoRow[];
  twin: Twin | null;
  ice: IceOutcome | null;
  /** Similarity variables used by the pair (sim_vars_used); null when eliminated or absent. */
  simVarsUsed: number | null;
  /** The pair's similarity left temperature out (sim_missing_bits temp_k bit). */
  missingTemp: boolean;
  /** The mission's similarity rule (manifest similarity_rules). */
  rule: string;
  /** True when the rule pairs on real values (missions.json similarity.variables). */
  valueRule: boolean;
  /** Real-value rules: one row per similarity variable (empty for an eliminated point). */
  pairRows: PairRow[];
  /** Real-value rules: the passing point has no twin, and why. */
  noPair: NoPair | null;
  /** Approved per-pair sentences filled for this pair (e.g. the solar sentence). */
  pairSentences: PairSentence[];
  /** Real-value rules: values not part of the similarity, both sides and the difference. */
  pairInfo: PairInfoRow[];
}

/** The shortest decimal that reads back as the same float32 (30.02 stays 30.02, not 30.0200004). */
/** Tenths of a stored float32 as the browser displays it with 1 decimal, half up (DATA_CONTRACT, 2026-11-15). */
export function displayedTenths(raw: number): number {
  const s = f32Decimal(raw).toFixed(12);
  const i = s.indexOf('.');
  return Number(s.slice(0, i)) * 10 + Number(s[i + 1]) + (Number(s[i + 2]) >= 5 ? 1 : 0);
}

/**
 * A placeholder computed by a named display rule of the contract; null when the rule is unknown or a
 * value is missing (the sentence is then not shown half-filled).
 */
export function applyDisplayRule(spec: PlaceholderSpec, read: (column: string | undefined) => number | null): number | null {
  if (spec.rule === 'share_lost_of_displayed_tenths') {
    const above = read(spec.columns?.above);
    const ground = read(spec.columns?.ground);
    if (above == null || ground == null || above < 0 || ground < 0) return null;
    const A = displayedTenths(above);
    const G = displayedTenths(ground);
    if (A <= 0) return null;
    return Math.floor((200 * (A - G) + A) / (2 * A));
  }
  return null;
}

export function f32Decimal(x: number): number {
  if (!Number.isFinite(x)) return x;
  for (let d = 1; d <= 9; d++) {
    const y = Number(x.toPrecision(d));
    if (Math.fround(y) === Math.fround(x)) return y;
  }
  return x;
}

/** A gap with 2 decimals rounded UP (texts.no_twin_note): 0.6563 -> 0.66, 30.02 -> 30.02. */
export function ceil2(x: number): number {
  const d = f32Decimal(x);
  return Math.ceil(Math.round(d * 1e6) / 1e4) / 100;
}

/** Unit words inside a sentence ("within 2 degrees", "kWh/m²/day"). */
const SENTENCE_UNIT: Record<string, string> = { deg: 'degrees', 'kWh/m2/day': 'kWh/m²/day', degC: '°C', K: 'K', m: 'm', km: 'km' };
export const sentenceUnit = (u: string): string => SENTENCE_UNIT[u] ?? u;

const nfSentence = (v: number, d: number) => new Intl.NumberFormat('en-GB', { maximumFractionDigits: d, minimumFractionDigits: 0 }).format(v);

/** A label inside a sentence: lower-case first letter ("Sunlight without atmosphere" -> "sunlight without atmosphere"). */
const midSentence = (label: string) => (/^[A-Z][a-z]/.test(label) ? label[0].toLowerCase() + label.slice(1) : label);

export class DataStore {
  manifest!: Manifest;
  missionsJson!: MissionsJson;
  similarity!: SimilarityJson;
  variables!: VariablesJson;
  places!: PlacesJson;
  placeDetail: PlaceDetailJson | null = null;
  private placeTable: Table | null = null;
  private earth!: Table;
  private landIds!: Int32Array;
  private missionData = new Map<string, MissionData>();
  private missionLoads = new Map<string, Promise<MissionData>>();
  private tiles = new Map<number, Table>();
  private tileLoads = new Map<number, Promise<Table>>();
  private tileOffsets: number[] = [];
  private twins: TwinsJson | null = null;
  private twinsLoad: Promise<TwinsJson | null> | null = null;
  private twinIndex = new Map<string, Map<number, Twin>>();
  private varByName = new Map<string, VariableInfo>();
  private matrices = new Map<string, MissionMatrix>();
  private moonTable: Table | null = null;
  private moonLoad: Promise<Table> | null = null;
  zones: MissionZonesJson | null = null;
  private zonesLoad: Promise<MissionZonesJson | null> | null = null;
  /** Bytes fetched so far, by file name (for tests and the budget check). */
  readonly fetched = new Map<string, number>();

  readonly base: string;
  private readonly fetcher: Fetcher;

  constructor(base: string = DEFAULT_BASE, fetcher: Fetcher = (u) => fetch(u)) {
    this.base = base;
    this.fetcher = fetcher;
  }

  // ---------- fetching ----------

  private async get(name: string): Promise<FetchResponse> {
    let res: FetchResponse;
    try {
      res = await this.fetcher(this.base + name);
    } catch (e) {
      throw new DataError(name, `the request failed: ${e instanceof Error ? e.message : String(e)}`);
    }
    if (!res.ok) throw new DataError(name, `the server answered ${res.status}${res.statusText ? ' ' + res.statusText : ''}`);
    return res;
  }

  private async json<T>(name: string): Promise<T> {
    const res = await this.get(name);
    try {
      const v = (await res.json()) as T;
      this.fetched.set(name, -1);
      return v;
    } catch {
      throw new DataError(name, 'its content is not valid JSON');
    }
  }

  private entry(name: string): FileEntry {
    const e = this.manifest.files.find((f) => f.name === name);
    if (!e) throw new DataError(name, 'the bundle index (manifest.json) does not list it');
    return e;
  }

  private async table(name: string): Promise<Table> {
    const entry = this.entry(name);
    const res = await this.get(name);
    let buf: ArrayBuffer;
    try {
      buf = await res.arrayBuffer();
    } catch (e) {
      throw new DataError(name, `the download was interrupted: ${e instanceof Error ? e.message : String(e)}`);
    }
    if (buf.byteLength !== entry.bytes) throw new DataError(name, `it has ${buf.byteLength} bytes, the index says ${entry.bytes}`);
    this.fetched.set(name, buf.byteLength);
    const meta = new Map((entry.columns ?? []).map((c) => [c.name, c]));
    return { entry, cols: decodeColumns(buf, entry), meta };
  }

  // ---------- start ----------

  /** The first view: manifest, then missions, similarity, variables, places, earth_base and the default mission. */
  async loadStart(): Promise<void> {
    this.manifest = await this.json<Manifest>('manifest.json');
    const [missions, similarity, variables, places, earth] = await Promise.all([
      this.json<MissionsJson>('missions.json'),
      this.json<SimilarityJson>('similarity.json'),
      this.json<VariablesJson>('variables.json'),
      this.json<PlacesJson>('places.json'),
      this.table('earth_base.bin'),
    ]);
    this.missionsJson = missions;
    this.similarity = similarity;
    this.variables = variables;
    this.places = places;
    this.earth = earth;
    this.landIds = earth.cols['id'] as Int32Array;
    for (const v of variables.variables) this.varByName.set(v.name, v);
    let acc = 0;
    this.tileOffsets = this.manifest.detail_tiles.files.map((t) => {
      const o = acc;
      acc += t.land_cells;
      return o;
    });
    await this.loadMission(this.manifest.load.default_mission ?? missions.default_mission);
  }

  // ---------- missions ----------

  /** The offered missions, in the bundle's order (missions.json offered_missions). */
  offeredMissions(): Mission[] {
    return this.missionsJson.offered_missions.map((id) => this.mission(id));
  }

  mission(id: string): Mission {
    const m = this.missionsJson.missions.find((x) => x.id === id);
    if (!m) throw new Error(`mission ${id} is not in missions.json`);
    return m;
  }

  private listed(name: string): boolean {
    return this.manifest.files.some((f) => f.name === name);
  }

  /** The similarity rule of a mission (manifest similarity_rules, else the mission's, else the bundle's one rule). */
  ruleOf(missionId: string): string {
    return this.manifest.similarity_rules?.[missionId] ?? this.mission(missionId).similarity.rule ?? this.similarity.rule;
  }

  /**
   * True when the mission pairs on per-variable values (revision 5 real_value_tolerance, and any later
   * rule written the same way): missions.json similarity.variables with score columns and a pairs file.
   */
  isValueRule(missionId: string): boolean {
    const s = this.mission(missionId).similarity;
    return Array.isArray(s.variables) && s.variables.length > 0 && !!s.pairs_file && this.listed(s.pairs_file);
  }

  /**
   * True when the bundle designates a lunar twin per Earth point: for one mission, when its Earth file
   * has a twin column and twins.json is published; without a mission, when any mission has twins.
   */
  hasTwins(missionId?: string): boolean {
    if (!this.listed('twins.json')) return false;
    const ids = missionId ? [missionId] : this.missionsJson.offered_missions;
    return ids.some((id) => {
      const e = this.manifest.files.find((f) => f.name === this.mission(id).files.EARTH);
      return !!e?.columns?.some((c) => c.name === 'twin');
    });
  }

  /** Every passing point of the mission has a final score (no point is left without a twin). */
  everyPointScored(missionId: string): boolean {
    const m = this.mission(missionId);
    return m.ranked_count === m.pass_counts.EARTH;
  }

  isMissionLoaded(id: string): boolean {
    return this.missionData.has(id);
  }

  loadMission(id: string): Promise<MissionData> {
    const have = this.missionLoads.get(id);
    if (have) return have;
    const p = (async () => {
      const mission = this.mission(id);
      const table = await this.table(mission.files.EARTH);
      const failBits = table.cols['fail_bits'] as Int32Array;
      const landIndex = table.cols['land_index'] as Int32Array;
      const passPos = new Int32Array(failBits.length).fill(-1);
      for (let p = 0; p < landIndex.length; p++) passPos[landIndex[p]] = p;
      const twin = (table.cols['twin'] as Int32Array | undefined) ?? null;
      const pairs = this.isValueRule(id) ? await this.table(mission.similarity.pairs_file as string) : null;
      const md: MissionData = { mission, failBits, landIndex, passPos, table, twin, pairs };
      this.missionData.set(id, md);
      return md;
    })();
    this.missionLoads.set(id, p);
    p.catch(() => this.missionLoads.delete(id));
    return p;
  }

  missionDataOf(id: string): MissionData {
    const md = this.missionData.get(id);
    if (!md) throw new Error(`mission ${id} not loaded yet`);
    return md;
  }

  private q(t: Table, name: string, i: number): number | null {
    const arr = t.cols[name];
    const c = t.meta.get(name);
    if (!arr || !c) return null;
    const v = arr[i];
    if (c.type === 'float32') return Number.isNaN(v) ? null : v;
    if (v === this.manifest.encoding.int32_missing) return null;
    return c.divisor ? v / c.divisor : v;
  }

  /**
   * Every passing Earth point of a mission with the stored scores, in the bundle's list order: the
   * points with a final by rank, then the points without a twin by suitability (earth_<m>_pairs.bin
   * list_order when the bundle has it; the same rule otherwise).
   */
  ranked(id: string): RankedPoint[] {
    const md = this.missionDataOf(id);
    const t = md.table;
    const missing = this.manifest.encoding.int32_missing;
    const n = md.landIndex.length;
    const out: RankedPoint[] = [];
    for (let p = 0; p < n; p++) {
      const rank = this.q(t, 'rank', p);
      const landPos = md.landIndex[p];
      const cellId = this.landIds[landPos];
      const tw = md.twin ? md.twin[p] : missing;
      out.push({
        id: cellId,
        landPos,
        passPos: p,
        lat: this.latOf(cellId),
        lon: this.lonOf(cellId),
        rank,
        final: this.q(t, 'final', p),
        suitability: this.q(t, 'suitability', p) as number,
        similarity: this.q(t, 'similarity', p),
        twinId: tw === missing ? null : tw,
        scored: rank != null,
        simVarsUsed: this.q(t, 'sim_vars_used', p),
        missingTemp: this.missingTempAt(id, p),
      });
    }
    const order = md.pairs?.cols['list_order'];
    if (order) {
      out.sort((a, b) => order[a.passPos] - order[b.passPos]);
      return out;
    }
    const scored = out.filter((r) => r.scored).sort((a, b) => (a.rank as number) - (b.rank as number));
    const rest = out.filter((r) => !r.scored);
    const ids = rest.map((r) => r.id);
    const fin = rest.map(() => NaN);
    const suit = rest.map((r) => r.suitability ?? NaN);
    return [...scored, ...unrankedOrder(ids, fin, suit).map((i) => rest[i])];
  }

  /** Points with a final score and points without a twin, as the bundle counts them. */
  pairCounts(id: string): { passing: number; paired: number; unpaired: number } {
    const m = this.mission(id);
    return { passing: m.pass_counts.EARTH, paired: m.ranked_count, unpaired: m.passing_without_similarity ?? m.pass_counts.EARTH - m.ranked_count };
  }

  // ---------- real-value pairs (revision 5) ----------

  private pairValue(md: MissionData, column: string | undefined, p: number): number | null {
    if (!md.pairs || !column || p < 0) return null;
    const v = this.q(md.pairs, column, p);
    return v == null ? null : f32Decimal(v);
  }

  /** The similarity variables of a real-value mission (missions.json similarity.variables, in order). */
  pairVariables(missionId: string): PairVariable[] {
    return this.isValueRule(missionId) ? (this.mission(missionId).similarity.variables ?? []) : [];
  }

  /** One row per similarity variable of the pair at passing position p (both values, difference, score). */
  pairRowsAt(missionId: string, p: number, simWeights?: readonly number[]): PairRow[] {
    const md = this.missionDataOf(missionId);
    const defs = this.pairVariables(missionId);
    return defs.map((def, i) => {
      const cmp = def.compared_columns ?? def.pairs_columns;
      const earth = this.pairValue(md, cmp.earth, p);
      const moon = this.pairValue(md, cmp.moon, p);
      const diff = this.pairValue(md, cmp.diff, p);
      const score = p >= 0 ? this.q(md.table, def.score_column, p) : null;
      const extra: Record<string, number | null> = {};
      for (const [k, col] of Object.entries(def.pairs_columns)) if (k !== 'earth' && k !== 'moon' && k !== 'diff') extra[k] = this.pairValue(md, col, p);
      const separate = cmp.earth !== def.pairs_columns.earth;
      const real = separate
        ? {
            earth: this.pairValue(md, def.pairs_columns.earth, p),
            moon: this.pairValue(md, def.pairs_columns.moon, p),
            diff: this.pairValue(md, def.pairs_columns.diff, p),
            unit: def.real_unit ?? def.unit,
          }
        : null;
      const within = diff == null ? null : diff <= def.bound * (1 + 1e-6) + 1e-9;
      return { def, earth, moon, diff, score, weight: simWeights?.[i] ?? def.weight, within, extra, real };
    });
  }

  /** Why the passing point at position p has no twin, with texts.no_twin_note filled; null when it is paired. */
  noPairAt(missionId: string, p: number): NoPair | null {
    const md = this.missionDataOf(missionId);
    if (!md.pairs || p < 0) return null;
    const missing = this.manifest.encoding.int32_missing;
    const k = md.pairs.cols['nopair_kind']?.[p];
    if (k == null || k === missing) return null;
    const sim = md.mission.similarity;
    const kind = sim.nopair_kinds?.[k] ?? String(k);
    const vi = md.pairs.cols['nopair_var']?.[p];
    const def = vi == null || vi === missing ? null : (sim.variables?.[vi] ?? null);
    const g = md.pairs.cols['nopair_gap']?.[p];
    const gap = g == null || Number.isNaN(g) ? null : f32Decimal(g);
    const vi2 = md.pairs.cols['nopair_var2']?.[p];
    const def2 = vi2 == null || vi2 === missing ? null : (sim.variables?.[vi2] ?? null);
    const g2 = md.pairs.cols['nopair_gap2']?.[p];
    const gap2 = g2 == null || Number.isNaN(g2) ? null : f32Decimal(g2);
    return { kind, variable: def, gap, sentence: this.noTwinSentence(kind, def, gap, missionId, def2, gap2) };
  }

  /**
   * The approved text of a kind for a mission (similarity.json texts): the entry `key` itself, or a
   * mission-specific entry `key_<anything>` that names the mission; texts with a status ("no longer
   * applies") or an empty mission list are never returned.
   */
  textFor(key: string, missionId: string | null): BundleText | null {
    const texts = this.similarity.texts ?? {};
    const usable = (t: BundleText | undefined) => !!t && !t.status && (!t.missions || (missionId != null && t.missions.includes(missionId)));
    const own = Object.entries(texts).find(([k, t]) => k.startsWith(`${key}_`) && missionId != null && t.missions?.includes(missionId) && !t.status);
    if (own) return own[1];
    return usable(texts[key]) ? texts[key] : null;
  }

  /** texts.no_twin_note (its no_joint_match variant when that is the reason) with the placeholders filled. */
  noTwinSentence(kind: string, def: PairVariable | null, gap: number | null, missionId: string | null = null, def2: PairVariable | null = null, gap2: number | null = null): string {
    const t = this.textFor('no_twin_note', missionId) ?? this.similarity.texts?.['no_twin_note'] ?? null;
    if (!t) return '';
    const template = t.variants?.[kind] ?? (kind === 'no_joint_match' && typeof t.variant_no_joint_match === 'string' ? t.variant_no_joint_match : t.text);
    const label = (d: PairVariable | null) => (d ? midSentence(d.label) : 'a key variable');
    const gapText = (x: number | null) => (x == null ? 'no value' : nfSentence(ceil2(x), 2));
    const filled = template
      .replace(/\{variable2\}/g, label(def2))
      .replace(/\{gap2\}/g, gapText(gap2))
      .replace(/\{unit2\}/g, def2 ? sentenceUnit(def2.unit) : '')
      .replace(/\{variable\}/g, label(def))
      .replace(/\{bound\}/g, def ? nfSentence(def.bound, 2) : '')
      .replace(/\{gap\}/g, gapText(gap))
      .replace(/\{unit\}/g, def ? sentenceUnit(def.unit) : '')
      .replace(/ {2,}/g, ' ')
      .replace(/ ([,.;)])/g, '$1');
    return filled;
  }

  /**
   * The approved per-pair sentences for the pair at position p: every text of similarity.json that
   * names this mission and has placeholders read from a pairs-file column (decimals and multiplier
   * from the bundle). A sentence whose placeholders cannot all be filled is left out, never shown half-filled.
   */
  pairSentencesAt(missionId: string, p: number): PairSentence[] {
    const md = this.missionDataOf(missionId);
    const out: PairSentence[] = [];
    if (!md.pairs || p < 0 || !md.twin || md.twin[p] === this.manifest.encoding.int32_missing) return out;
    for (const [key, t] of Object.entries(this.similarity.texts ?? {})) {
      const forThis = (t.missions ?? (t.mission ? [t.mission] : [])).includes(missionId);
      const specs = Object.entries(t.placeholders ?? {}).filter(
        (e): e is [string, PlaceholderSpec] => typeof e[1] === 'object' && e[1] !== null && ('column' in e[1] || 'rule' in e[1]),
      );
      if (!forThis || !specs.length) continue;
      let text = t.text;
      let completed = true;
      for (const [name, spec] of specs) {
        const fileTable = spec.file === md.pairs.entry.name ? md.pairs : spec.file === md.table.entry.name ? md.table : null;
        const read = (col: string | undefined) => (fileTable && col ? this.q(fileTable, col, p) : null);
        let shown: string | null = null;
        if (spec.rule) {
          const v = applyDisplayRule(spec, read);
          if (v != null) shown = String(v);
        } else {
          const raw = read(spec.column);
          if (raw != null) {
            const v = (f32Decimal(raw) - (spec.subtract ?? 0)) * (spec.multiply ?? 1);
            const d = spec.decimals ?? 1;
            shown = new Intl.NumberFormat('en-GB', { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
          }
        }
        if (shown == null) {
          completed = false;
          break;
        }
        text = text.split(`{${name}}`).join(shown);
      }
      if (completed && !/\{[a-z_]+\}/.test(text)) out.push({ key, text });
    }
    return out;
  }

  /** The bit of `temp_k` in sim_missing_bits (its position in similarity.json active_variables), -1 when not active. */
  tempBit(): number {
    return this.similarity.active_variables?.indexOf('temp_k') ?? -1;
  }

  /** True when the pair of passing position `p` left temperature out of its similarity. */
  missingTempAt(missionId: string, p: number): boolean {
    const md = this.missionDataOf(missionId);
    const bits = md.table.cols['sim_missing_bits'];
    const k = this.tempBit();
    if (!bits || k < 0 || p < 0) return false;
    const b = bits[p];
    return b !== this.manifest.encoding.int32_missing && ((b >>> k) & 1) === 1;
  }

  /** An approved web text of the bundle (similarity.json texts.<key>.text), verbatim; null when absent. */
  text(key: string): string | null {
    const t = this.similarity.texts?.[key];
    // a text marked as no longer applying (revision 6: status), or applying to no mission, is not shown
    if (!t || t.status || (Array.isArray(t.missions) && t.missions.length === 0)) return null;
    return t.text ?? null;
  }

  /**
   * The twin-sharing sentence (decision 4) with N and X filled in. The bundle says the second
   * sentence is about lunar_base only: other missions get the first sentence.
   */
  twinSharingText(missionId: string, earthCells: number): string | null {
    const t = this.similarity.texts?.['twin_sharing_note'];
    if (!t) return null;
    const ranked = this.mission(missionId).ranked_count;
    const x = ranked > 0 ? (100 * earthCells) / ranked : 0;
    // Pick the sentences on the template (no decimals in it yet), then fill N and X.
    let template = t.text;
    const first = /^.*?\.(?=\s|$)/.exec(template)?.[0] ?? template;
    if (/first sentence only, for every mission/i.test(t.where)) template = first;
    else {
      const onlyFor = /about lunar_base/.test(t.where) ? 'lunar_base' : null;
      if (onlyFor && missionId !== onlyFor) template = first;
    }
    const filled = template.replace(/\bN\b/, new Intl.NumberFormat('en-GB').format(earthCells)).replace(/\bX\b/, x < 0.1 ? x.toFixed(2) : x.toFixed(1));
    // one Earth point, not "1 Earth points"
    return earthCells === 1 ? filled.replace(/\b1 Earth points\b/, '1 Earth point') : filled;
  }

  // ---------- grid ----------

  latOf(id: number): number {
    return (this.earth.cols['lat'] as Float32Array)[Math.floor(id / this.manifest.grid.cols)];
  }
  lonOf(id: number): number {
    return (this.earth.cols['lon'] as Float32Array)[id % this.manifest.grid.cols];
  }
  /** Lunar cell centre from the grid rule (manifest.grid). */
  moonLatLon(id: number): { lat: number; lon: number } {
    const g = this.manifest.grid;
    const row = Math.floor(id / g.cols);
    const col = id % g.cols;
    return { lat: 90 - (row + 0.5) * g.cell_deg, lon: -180 + (col + 0.5) * g.cell_deg };
  }
  /** The 1-degree footprint of a cell (both bodies share the grid). */
  cellFootprint(id: number): { west: number; south: number; east: number; north: number } {
    const g = this.manifest.grid;
    const row = Math.floor(id / g.cols);
    const col = id % g.cols;
    const north = 90 - row * g.cell_deg;
    const west = -180 + col * g.cell_deg;
    return { west, east: west + g.cell_deg, north, south: north - g.cell_deg };
  }
  landPosOf(id: number): number {
    return binarySearch(this.landIds, id);
  }
  landCount(): number {
    return this.landIds.length;
  }
  landId(pos: number): number {
    return this.landIds[pos];
  }

  variable(name: string): VariableInfo | undefined {
    return this.varByName.get(name);
  }

  /** A stored Earth value `v.<column>` of a land cell; categories become their class name. */
  earthValue(column: string | null, landPos: number): CellValue {
    if (!column || landPos < 0) return { raw: null, value: null };
    const name = `v.${column}`;
    const c = this.earth.meta.get(name);
    const arr = this.earth.cols[name];
    if (!c || !arr) return { raw: null, value: null };
    const id = this.landIds[landPos];
    const i = c.rows === 'grid_rows' ? Math.floor(id / this.manifest.grid.cols) : landPos;
    const v = arr[i];
    if (c.type === 'float32') return Number.isNaN(v) ? { raw: null, value: null } : { raw: v, value: v };
    if (v === this.manifest.encoding.int32_missing) return { raw: null, value: null };
    if (c.codes) {
      const varName = /variables\.json (\S+) categories/.exec(c.codes)?.[1] ?? column;
      const cats = this.varByName.get(varName)?.categories ?? null;
      return { raw: v, value: cats?.[v] ?? null };
    }
    return { raw: v, value: v };
  }

  // ---------- places ----------

  async loadPlaceDetail(): Promise<void> {
    if (this.placeTable) return;
    const [json, table] = await Promise.all([this.json<PlaceDetailJson>('place_detail.json'), this.table('earth_place_detail.bin')]);
    this.placeDetail = json;
    this.placeTable = table;
  }

  place(landPos: number): PlaceLabel {
    const out: PlaceLabel = { country: null, countryCode: null, region: null, nearest: null, nearestKm: null, text: null };
    if (landPos < 0) return out;
    const missing = this.manifest.encoding.int32_missing;
    const ci = (this.earth.cols['country'] as Int32Array)[landPos];
    const ri = (this.earth.cols['region'] as Int32Array)[landPos];
    if (ci !== missing) {
      out.country = this.places.countries[ci]?.name ?? null;
      out.countryCode = this.places.countries[ci]?.code ?? null;
    }
    if (ri !== missing) out.region = this.places.regions[ri] ?? null;
    if (this.placeTable && this.placeDetail) {
      const ni = (this.placeTable.cols['nearest_place'] as Int32Array)[landPos];
      const nk = (this.placeTable.cols['nearest_place_km'] as Float32Array)[landPos];
      if (ni !== missing) out.nearest = this.placeDetail.nearest_places[ni] ?? null;
      if (!Number.isNaN(nk)) out.nearestKm = nk;
    }
    // The region comes only from a nearby place in the same country (places.json region_rule);
    // without it the label is the country alone (the nearest place may be far away).
    if (out.region && out.country) out.text = `${out.region}, ${out.country}`;
    else out.text = out.country;
    return out;
  }

  // ---------- detail tiles ----------

  tileIndexOf(id: number): number {
    const row = Math.floor(id / this.manifest.grid.cols);
    return this.manifest.detail_tiles.files.findIndex((t) => t.row_start <= row && row <= t.row_end);
  }

  isTileLoaded(k: number): boolean {
    return this.tiles.has(k);
  }

  loadTile(k: number): Promise<Table> {
    const have = this.tileLoads.get(k);
    if (have) return have;
    const p = this.table(this.manifest.detail_tiles.files[k].name).then((t) => {
      this.tiles.set(k, t);
      return t;
    });
    this.tileLoads.set(k, p);
    p.catch(() => this.tileLoads.delete(k));
    return p;
  }

  allTilesLoaded(): boolean {
    return this.tiles.size === this.manifest.detail_tiles.files.length;
  }

  /** Every detail tile (only for the weight sliders, which need every passing cell's utilities). */
  async loadAllTiles(): Promise<void> {
    await Promise.all(this.manifest.detail_tiles.files.map((_, k) => this.loadTile(k)));
  }

  /** Tile and position of a land cell (tiles concatenated in row order give the land order). */
  private tilePos(landPos: number): { tile: Table; pos: number } | null {
    const id = this.landIds[landPos];
    const k = this.tileIndexOf(id);
    const tile = this.tiles.get(k);
    if (!tile) return null;
    const pos = landPos - this.tileOffsets[k];
    const ids = tile.cols['id'] as Int32Array;
    if (ids[pos] === id) return { tile, pos };
    const b = binarySearch(ids, id);
    return b < 0 ? null : { tile, pos: b };
  }

  /** Utilities and similarities of every passing cell of a mission, for the sliders (needs every tile). */
  matrix(id: string): MissionMatrix {
    const have = this.matrices.get(id);
    if (have) return have;
    const md = this.missionDataOf(id);
    const n = md.landIndex.length;
    const wvs = md.mission.weighted_variables;
    const utilities = wvs.map(() => new Float64Array(n));
    const similarity = new Float64Array(n);
    const ids = new Int32Array(n);
    const defs = this.pairVariables(id);
    const simScores = defs.length ? defs.map(() => new Float64Array(n)) : null;
    const paired = defs.length ? new Uint8Array(n) : null;
    const missing = this.manifest.encoding.int32_missing;
    for (let p = 0; p < n; p++) {
      const lp = md.landIndex[p];
      ids[p] = this.landIds[lp];
      if (simScores && paired) {
        paired[p] = md.twin && md.twin[p] !== missing ? 1 : 0;
        defs.forEach((d, v) => {
          const sc = this.q(md.table, d.score_column, p);
          simScores[v][p] = sc == null ? NaN : sc;
        });
      }
      const s = this.q(md.table, 'similarity', p);
      similarity[p] = s == null ? NaN : s;
      const tp = this.tilePos(lp);
      if (!tp) throw new Error('matrix() needs every detail tile: call loadAllTiles() first');
      wvs.forEach((wv, v) => {
        const u = this.q(tp.tile, `${id}.u.${wv.variable}`, tp.pos);
        utilities[v][p] = u == null ? NaN : u;
      });
    }
    const m: MissionMatrix = { ids, similarity, utilities, simScores, paired };
    this.matrices.set(id, m);
    return m;
  }

  // ---------- twins ----------

  loadTwins(): Promise<TwinsJson | null> {
    if (!this.hasTwins()) return Promise.resolve(null);
    if (this.twins) return Promise.resolve(this.twins);
    if (this.twinsLoad) return this.twinsLoad;
    this.twinsLoad = this.json<TwinsJson>('twins.json').then((t) => {
      this.twins = t;
      for (const [mid, m] of Object.entries(t.missions)) this.twinIndex.set(mid, new Map(m.twins.map((x) => [x.id, x])));
      return t;
    });
    this.twinsLoad.catch(() => (this.twinsLoad = null));
    return this.twinsLoad;
  }

  twinsOf(missionId: string): Twin[] {
    return this.twins?.missions[missionId]?.twins ?? [];
  }

  twin(missionId: string, twinId: number): Twin | null {
    return this.twinIndex.get(missionId)?.get(twinId) ?? null;
  }

  // ---------- lunar regions and mission zones (revision 6) ----------

  /** True when the bundle publishes the zone explanations (mission_zones.json and the region column of moon_base.bin). */
  hasZones(): boolean {
    if (!this.listed('mission_zones.json')) return false;
    const e = this.manifest.files.find((f) => f.name === 'moon_base.bin');
    return !!e?.columns?.some((c) => c.name === 'region');
  }

  /** mission_zones.json and the lunar region of every cell (moon_base.bin region); null when the bundle has none. */
  loadZones(): Promise<MissionZonesJson | null> {
    if (!this.hasZones()) return Promise.resolve(null);
    if (this.zonesLoad) return this.zonesLoad;
    this.zonesLoad = Promise.all([this.json<MissionZonesJson>('mission_zones.json'), this.loadMoonBase()]).then(([z]) => {
      this.zones = z;
      return z;
    });
    this.zonesLoad.catch(() => (this.zonesLoad = null));
    return this.zonesLoad;
  }

  loadMoonBase(): Promise<Table> {
    if (this.moonLoad) return this.moonLoad;
    this.moonLoad = this.table('moon_base.bin').then((t) => (this.moonTable = t));
    this.moonLoad.catch(() => (this.moonLoad = null));
    return this.moonLoad;
  }

  /** The region of a lunar cell (index into mission_zones.json regions, or its code), null before loadZones(). */
  regionOfCell(id: number): MissionZonesJson['regions'][number] | null {
    const z = this.zones;
    const col = this.moonTable?.cols['region'];
    if (!z || !col || id < 0 || id >= col.length) return null;
    const v = col[id];
    if (v === this.manifest.encoding.int32_missing) return null;
    return z.regions[v] ?? null;
  }

  /** The region codes of a mission's search zone (mission_zones.json mission_zone_regions). */
  zoneCodes(missionId: string): string[] {
    return this.zones?.mission_zone_regions[missionId] ?? [];
  }

  /** One byte per lunar cell: 1 when the cell is inside the mission's search zone. */
  zoneMask(missionId: string): Uint8Array | null {
    const z = this.zones;
    const col = this.moonTable?.cols['region'];
    if (!z || !col) return null;
    const inZone = new Set(this.zoneCodes(missionId));
    const idx = z.regions.map((r) => inZone.has(r.code));
    const out = new Uint8Array(col.length);
    for (let i = 0; i < col.length; i++) out[i] = idx[col[i]] ? 1 : 0;
    return out;
  }

  /** The lunar cell that holds (lat, lon) on the shared 1-degree grid. */
  moonCellAt(lat: number, lon: number): number {
    const g = this.manifest.grid;
    const row = Math.min(g.rows - 1, Math.max(0, Math.floor((90 - lat) / g.cell_deg)));
    let l = lon;
    while (l < -180) l += 360;
    while (l >= 180) l -= 360;
    const col = Math.min(g.cols - 1, Math.max(0, Math.floor((l + 180) / g.cell_deg)));
    return row * g.cols + col;
  }

  // ---------- the funnel of one cell ----------

  /** Load what outcome() needs for a cell: its tile, every offered mission file, twins. */
  async prepareCell(id: number): Promise<void> {
    const k = this.tileIndexOf(id);
    await Promise.all([
      k >= 0 ? this.loadTile(k) : Promise.resolve(null),
      ...this.missionsJson.offered_missions.map((m) => this.loadMission(m)),
      this.loadTwins(),
    ]);
  }

  similarityLabel(variable: string): { label: string; unit: string } {
    const sv = this.similarity.variables?.find((v) => v.variable === variable);
    const pv = this.missionsJson.missions.flatMap((m) => m.similarity.variables ?? []).find((v) => v.variable === variable);
    const info = this.varByName.get(variable) ?? (sv?.columns.EARTH ? this.varByName.get(sv.columns.EARTH) : undefined);
    if (info) return { label: info.label, unit: info.unit };
    if (pv) return { label: pv.label, unit: pv.real_unit ?? pv.unit };
    return { label: SIMILARITY_FALLBACK_LABELS[variable] ?? variable.replace(/_/g, ' '), unit: '' };
  }

  /**
   * The full funnel of one Earth cell for one mission (docs/DATA_CONTRACT.md "The funnel"), with
   * the suitability rows for `weights` (the mission's own weights when omitted). Call prepareCell first.
   */
  outcome(id: number, missionId: string, weights?: readonly number[], alpha?: number, simWeights?: readonly number[]): MissionOutcome {
    const md = this.missionDataOf(missionId);
    const mission = md.mission;
    const landPos = this.landPosOf(id);
    const bits = landPos >= 0 ? md.failBits[landPos] : -1;
    const codes = mission.reason_codes;
    const reasons = landPos >= 0 ? codes.filter((r) => (bits >>> r.bit) & 1) : [];
    const pass = landPos >= 0 && bits === 0;
    const failedFor = (variable: string) => reasons.filter((r) => r.variable === variable);
    const gateRow = (g: Gate): GateRow => {
      const failed = failedFor(g.variable);
      return { gate: g, value: this.earthValue(g.columns.EARTH, landPos), pass: landPos >= 0 && failed.length === 0, failed };
    };
    const earthGates = mission.gates.filter((g) => g.applies_to.includes('EARTH'));
    const common = earthGates.filter((g) => g.step === 1).map(gateRow);
    const gates = earthGates.filter((g) => g.step === 3).map(gateRow);
    const required: RequiredRow[] = mission.require_present.map((variable) => {
      const col = this.columnOfMissionVariable(mission, variable);
      const failed = reasons.filter((r) => r.variable === variable && r.kind === 'missing');
      const value = this.earthValue(col, landPos);
      return { variable, label: this.labelOfMissionVariable(mission, variable), value, present: value.raw != null, failed };
    });

    const tp = landPos >= 0 ? this.tilePos(landPos) : null;
    const wvs = mission.weighted_variables;
    const w = weights ?? wvs.map((x) => x.weight);
    const utilities = wvs.map((wv) => (pass && tp ? this.q(tp.tile, `${missionId}.u.${wv.variable}`, tp.pos) : null));
    const suit = pass ? suitabilityOf(utilities, w) : null;
    const den = utilities.reduce<number>((s, u, i) => (u == null ? s : s + w[i]), 0);
    const breakdown: BreakdownRow[] = wvs
      .map((wv, i) => {
        const u = utilities[i];
        return {
          wv,
          value: this.earthValue(wv.columns.EARTH, landPos),
          utility: u,
          weight: w[i],
          contribution: u == null ? null : w[i] * u,
          points: u == null || den === 0 ? null : (100 * w[i] * u) / den,
        };
      })
      // by contribution, ties by variable name (the engine's explain.json order)
      .sort((a, b) => (b.contribution ?? -1) - (a.contribution ?? -1) || (a.wv.variable < b.wv.variable ? -1 : a.wv.variable > b.wv.variable ? 1 : 0));

    const p = landPos >= 0 ? md.passPos[landPos] : -1;
    const stored = (name: string) => (p >= 0 ? this.q(md.table, name, p) : null);
    const valueRule = this.isValueRule(missionId);
    const pairRows = pass && valueRule ? this.pairRowsAt(missionId, p, simWeights) : [];
    let similarity = stored('similarity');
    let final = stored('final');
    let rank = stored('rank');
    const a = alpha ?? mission.alpha;
    const custom = weights !== undefined || alpha !== undefined || simWeights !== undefined;
    let simExact: number | null = similarity;
    if (valueRule && pass && similarity != null && simWeights !== undefined) {
      simExact = pairSimilarityOf(
        pairRows.map((r) => r.score),
        pairRows.map((r) => r.weight),
      );
      similarity = simExact == null ? null : pyRound2(simExact);
    }
    if (custom) {
      final = suit?.suitability != null && simExact != null ? pyRound2(finalOf(a, simExact, suit.suitability)) : null;
      rank = null; // the caller knows the recomputed rank
    }
    const ci = stored('confidence');
    const confidence = ci == null ? null : (this.missionsJson.confidence_codes[ci] ?? null);

    // similarity rows
    const twinId = p >= 0 && md.twin ? md.twin[p] : this.manifest.encoding.int32_missing;
    const twin = twinId !== this.manifest.encoding.int32_missing ? this.twin(missionId, twinId) : null;
    const target = this.similarity.target;
    const zRows = !valueRule && !!target && Array.isArray(this.similarity.active_variables);
    const similarityRows: SimilarityRow[] = (zRows ? (this.similarity.active_variables ?? []) : []).map((f) => {
      const sv = this.similarity.variables!.find((v) => v.variable === f)!;
      const { label, unit } = this.similarityLabel(f);
      const ez = tp ? this.q(tp.tile, `z.${f}`, tp.pos) : null;
      const ev = this.earthValue(sv.columns.EARTH, landPos).raw;
      let mz: number | null = null;
      let mv: number | null = null;
      if (target?.kind === 'global_mean') {
        mz = target.profile[f]?.z ?? null;
        mv = target.profile[f]?.value ?? null;
      } else if (twin) {
        mz = twin.z?.[f] ?? null;
        mv = twin.values[f] ?? null;
      }
      return {
        sv,
        label,
        unit,
        normWeight: sv.norm_weight ?? 0,
        earth: { value: ev, z: ez, level: sv.levels.EARTH },
        moon: { value: mv, z: mz, level: sv.levels.MOON },
        clipped: Math.abs(ez ?? 0) >= 4 || Math.abs(mz ?? 0) >= 4,
      };
    });
    const infoRows: InfoRow[] = (zRows ? (this.similarity.not_part_of_similarity ?? []) : []).map((variable) => {
      const info = this.varByName.get(variable);
      const earth = this.earthValue(info?.bodies.EARTH?.column ?? variable, landPos);
      let moonValue: number | string | null = null;
      let how: InfoRow['moon']['how'] = 'mean';
      if (target?.kind === 'global_mean') {
        const t = target.info_not_in_similarity[variable];
        moonValue = t?.mean ?? t?.commonest ?? null;
        how = t?.commonest != null ? 'commonest' : 'mean';
      } else if (twin) {
        moonValue = twin.not_part_of_similarity[variable] ?? null;
        how = 'twin';
      }
      return {
        variable,
        label: info?.label ?? variable,
        unit: info?.unit ?? '',
        earth: { value: earth.value, level: info?.bodies.EARTH?.level ?? null },
        moon: { value: moonValue, level: info?.bodies.MOON?.level ?? null, how },
      };
    });

    // the ice component (lunar_base only, information)
    let ice: IceOutcome | null = null;
    const iceDef = mission.component_results.ice;
    if (iceDef && tp) {
      const ib = tp.tile.cols[`${missionId}.ice.fail_bits`]?.[tp.pos] ?? 0;
      const ir = iceDef.reason_codes.filter((r) => (ib >>> r.bit) & 1);
      ice = {
        pass: ib === 0,
        reasons: ir,
        line: ir.map((r) => r.text).join('; '),
        suitability: this.q(tp.tile, `${missionId}.ice.suitability`, tp.pos),
        utilities: iceDef.weighted_variables.map((wv) => ({
          wv,
          value: this.earthValue(wv.columns.EARTH, landPos),
          utility: this.q(tp.tile, `${missionId}.ice.u.${wv.variable}`, tp.pos),
        })),
      };
    }

    return {
      mission,
      landPos,
      pass,
      reasons,
      line: reasons.map((r) => r.text).join('; '),
      common,
      required,
      gates,
      breakdown,
      suitability: pass && suit ? suit.suitability : null,
      coverage: pass && suit ? suit.coverage : null,
      similarity: pass ? similarity : null,
      final: pass ? final : null,
      rank: pass ? rank : null,
      confidence: pass ? confidence : null,
      confidenceScore: pass ? stored('confidence_score') : null,
      similarityRows,
      infoRows,
      twin: pass ? twin : null,
      ice,
      simVarsUsed: pass ? stored('sim_vars_used') : null,
      missingTemp: pass && p >= 0 ? this.missingTempAt(missionId, p) : false,
      rule: this.ruleOf(missionId),
      valueRule,
      pairRows,
      noPair: pass && valueRule ? this.noPairAt(missionId, p) : null,
      pairSentences: pass && valueRule ? this.pairSentencesAt(missionId, p) : [],
      pairInfo: pass && valueRule ? this.pairInfoOf(landPos, twin, missionId, p) : [],
    };
  }

  /**
   * Values that are not part of a real-value similarity, for information: every value the twin row
   * carries (twins.json not_part_of_similarity) against the Earth cell's own, with the difference.
   * Without a twin, the Earth values of the bundle's information list for the rule.
   */
  pairInfoOf(landPos: number, twin: Twin | null, missionId?: string, p = -1): PairInfoRow[] {
    const names = twin ? Object.keys(twin.not_part_of_similarity) : [];
    // revision 6: values exported per pair in the pairs file come first, from there (both sides and the difference)
    const md = missionId ? this.missionDataOf(missionId) : null;
    const cols = twin && md ? (md.mission.similarity.info_columns ?? []) : [];
    const fromPairs: PairInfoRow[] = cols.map((c) => {
      const info = this.varByName.get(c.variable);
      const lab = this.similarityLabel(c.variable);
      return {
        variable: c.variable,
        label: info?.label ?? lab.label,
        unit: c.unit,
        earth: this.pairValue(md!, c.columns.earth, p),
        moon: this.pairValue(md!, c.columns.moon, p),
        diff: (() => {
          const d = this.pairValue(md!, c.columns.diff, p);
          return d == null ? null : Math.abs(d);
        })(),
        diffUnit: c.unit === 'degC' ? 'K' : c.unit,
        levels: { EARTH: info?.bodies.EARTH?.level ?? null, MOON: info?.bodies.MOON?.level ?? null },
      };
    });
    const done = new Set(cols.map((c) => c.variable));
    // a value already compared in the similarity is not repeated here
    for (const d of missionId ? this.pairVariables(missionId) : []) {
      done.add(d.variable);
      if (d.sides?.EARTH?.column) done.add(d.sides.EARTH.column);
    }
    return fromPairs.concat(names.filter((n) => !done.has(n)).map((variable) => {
      const info = this.varByName.get(variable);
      const ev = this.earthValue(info?.bodies.EARTH?.column ?? variable, landPos).value;
      const e = typeof ev === 'number' ? f32Decimal(ev) : ev;
      const mo = twin?.not_part_of_similarity[variable] ?? null;
      const unit = info?.unit ?? '';
      const diff = typeof e === 'number' && typeof mo === 'number' ? Math.abs(e - mo) : null;
      return {
        variable,
        label: info?.label ?? variable,
        unit,
        earth: e,
        moon: mo,
        diff,
        diffUnit: unit === 'degC' ? 'K' : unit,
        levels: { EARTH: info?.bodies.EARTH?.level ?? null, MOON: info?.bodies.MOON?.level ?? null },
      };
    }));
  }

  /**
   * How one side of a similarity variable is made, in a few words from the bundle (missions.json
   * similarity.variables[].sides): its level and, for a temperature, whether it is an air or a surface
   * temperature and from which product ("modelled air temperature (WorldClim)").
   */
  sideWords(def: PairVariable, body: 'EARTH' | 'MOON'): { level: Level | null; words: string | null } {
    const side = def.sides?.[body];
    if (!side) return { level: null, words: null };
    const lv = /\b(MEASURED|DERIVED|MODELLED)\b/.exec(String(side.level ?? ''))?.[1] as Level | undefined;
    const what = /\b(AIR|SURFACE)\s+temperature/i.exec(side.text ?? '')?.[1]?.toLowerCase();
    const product = /\b(WorldClim|Diviner|MODIS|LOLA|ETOPO)\b/.exec(side.text ?? '')?.[1];
    const levelWord = lv ? ({ MEASURED: 'measured', DERIVED: 'derived', MODELLED: 'modelled' } as Record<string, string>)[lv] : null;
    const words = what ? `${levelWord ? levelWord + ' ' : ''}${what} temperature${product ? ` (${product})` : ''}` : null;
    return { level: lv ?? null, words };
  }

  /** The real column a mission variable is read from (gates or weighted variables say it). */
  columnOfMissionVariable(mission: Mission, variable: string): string | null {
    const g = mission.gates.find((x) => x.variable === variable);
    if (g) return g.columns.EARTH;
    const w = mission.weighted_variables.find((x) => x.variable === variable);
    if (w) return w.columns.EARTH;
    return this.varByName.get(variable)?.bodies.EARTH?.column ?? variable;
  }

  labelOfMissionVariable(mission: Mission, variable: string): string {
    return (
      mission.weighted_variables.find((x) => x.variable === variable)?.label ??
      this.varByName.get(variable)?.label ??
      mission.reason_codes.find((r) => r.variable === variable)?.label.replace(/^[^:]*:\s*/, '') ??
      variable
    );
  }

  /** Recompute the stored similarity of a passing cell from its z-scores (for the exact check). */
  recomputeSimilarity(missionId: string, landPos: number, simWeights?: readonly number[]): number | null {
    const md = this.missionDataOf(missionId);
    if (this.isValueRule(missionId)) {
      const p = md.passPos[landPos];
      if (p < 0 || !md.twin || md.twin[p] === this.manifest.encoding.int32_missing) return null;
      const rows = this.pairRowsAt(missionId, p, simWeights);
      const v = pairSimilarityOf(
        rows.map((r) => r.score),
        rows.map((r) => r.weight),
      );
      return v == null ? null : pyRound2(v);
    }
    const tp = this.tilePos(landPos);
    if (!tp) throw new Error('tile not loaded');
    const F = this.similarity.active_variables ?? [];
    const target = this.similarity.target;
    if (!F.length || !target || !this.similarity.formula) return this.q(md.table, 'similarity', md.passPos[landPos]);
    const nw = F.map((f) => this.similarity.variables?.find((v) => v.variable === f)?.norm_weight ?? 0);
    const ze = F.map((f) => this.q(tp.tile, `z.${f}`, tp.pos));
    let zm: (number | null)[];
    if (target.kind === 'global_mean') zm = F.map((f) => target.profile[f]?.z ?? null);
    else {
      const p = md.passPos[landPos];
      const tw = md.twin ? this.twin(missionId, md.twin[p]) : null;
      zm = F.map((f) => tw?.z?.[f] ?? null);
    }
    return similarityOf(ze, zm, nw, this.similarity.formula.decay);
  }

  /** Stored scores of a passing cell (decoded exactly), for tests. */
  storedScores(missionId: string, passPos: number): { suitability: number | null; similarity: number | null; final: number | null; rank: number | null } {
    const t = this.missionDataOf(missionId).table;
    return {
      suitability: this.q(t, 'suitability', passPos),
      similarity: this.q(t, 'similarity', passPos),
      final: this.q(t, 'final', passPos),
      rank: this.q(t, 'rank', passPos),
    };
  }

  /** The level words of a variable on one body (variables.json). */
  levelOf(variable: string, body: 'EARTH' | 'MOON'): Level | null {
    return this.varByName.get(variable)?.bodies[body]?.level ?? null;
  }

  /** Source and level detail of a variable on a body. */
  provenance(variable: string, body: 'EARTH' | 'MOON') {
    return this.varByName.get(variable)?.bodies[body] ?? null;
  }

  /** Total bytes of the files fetched so far (binary files only; JSON counted from the manifest). */
  fetchedBytes(): number {
    let s = 0;
    for (const [name, b] of this.fetched) s += b >= 0 ? b : (this.manifest.files.find((f) => f.name === name)?.bytes ?? 0);
    return s;
  }
}

/** Labels for similarity variables that variables.json does not describe (repository names). */
const SIMILARITY_FALLBACK_LABELS: Record<string, string> = {
  elevation_rel_m: 'Elevation relative to the body mean',
  sar_sigma0_db: 'Radar backscatter',
};

export type { NumArray };
