// Data store for the engine's bundle v2 (docs/DATA_CONTRACT.md). Loads the first view at start
// (manifest, missions, similarity, variables, places, earth_base and the default mission) and the
// rest on demand: the other mission files, one detail tile per selected cell (all tiles only when
// the weight sliders need every utility), place details and twins (only when the rule has them).
// No DOM: the Node tests import this file directly.

import { finalOf, pyRound2, similarityOf, suitabilityOf, type MissionMatrix } from './recompute.ts';
import type {
  Column,
  Columns,
  FileEntry,
  Gate,
  Level,
  Manifest,
  Mission,
  MissionsJson,
  NumArray,
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
    super(
      `The mission data file "${file}" could not be loaded (${detail}). ` +
        'Check the network connection and reload the page; if it keeps failing, the site was published without its data folder.',
    );
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
  rank: number;
  final: number;
  suitability: number;
  similarity: number;
  twinId: number | null;
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
}

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

  /** True when the active similarity rule designates a lunar twin per Earth point (zone_twin). */
  hasTwins(): boolean {
    return this.similarity.target.kind === 'zone_twin' && this.manifest.files.some((f) => f.name === 'twins.json');
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
      const md: MissionData = { mission, failBits, landIndex, passPos, table, twin };
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

  /** The ranked Earth points of a mission with the stored scores, best first. */
  ranked(id: string): RankedPoint[] {
    const md = this.missionDataOf(id);
    const t = md.table;
    const out: RankedPoint[] = [];
    for (let p = 0; p < md.landIndex.length; p++) {
      const rank = this.q(t, 'rank', p);
      if (rank == null) continue;
      const landPos = md.landIndex[p];
      const cellId = this.landIds[landPos];
      const tw = md.twin ? md.twin[p] : this.manifest.encoding.int32_missing;
      out.push({
        id: cellId,
        landPos,
        passPos: p,
        lat: this.latOf(cellId),
        lon: this.lonOf(cellId),
        rank,
        final: this.q(t, 'final', p) as number,
        suitability: this.q(t, 'suitability', p) as number,
        similarity: this.q(t, 'similarity', p) as number,
        twinId: tw === this.manifest.encoding.int32_missing ? null : tw,
        simVarsUsed: this.q(t, 'sim_vars_used', p),
        missingTemp: this.missingTempAt(id, p),
      });
    }
    out.sort((a, b) => a.rank - b.rank);
    return out;
  }

  /** The bit of `temp_k` in sim_missing_bits (its position in similarity.json active_variables), -1 when not active. */
  tempBit(): number {
    return this.similarity.active_variables.indexOf('temp_k');
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
    return this.similarity.texts?.[key]?.text ?? null;
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
    const onlyFor = /about lunar_base/.test(t.where) ? 'lunar_base' : null;
    if (onlyFor && missionId !== onlyFor) template = /^.*?\.(?=\s|$)/.exec(template)?.[0] ?? template;
    return template.replace(/\bN\b/, new Intl.NumberFormat('en-GB').format(earthCells)).replace(/\bX\b/, x < 0.1 ? x.toFixed(2) : x.toFixed(1));
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
    for (let p = 0; p < n; p++) {
      const lp = md.landIndex[p];
      ids[p] = this.landIds[lp];
      const s = this.q(md.table, 'similarity', p);
      similarity[p] = s == null ? NaN : s;
      const tp = this.tilePos(lp);
      if (!tp) throw new Error('matrix() needs every detail tile: call loadAllTiles() first');
      wvs.forEach((wv, v) => {
        const u = this.q(tp.tile, `${id}.u.${wv.variable}`, tp.pos);
        utilities[v][p] = u == null ? NaN : u;
      });
    }
    const m = { ids, similarity, utilities };
    this.matrices.set(id, m);
    return m;
  }

  // ---------- twins ----------

  loadTwins(): Promise<TwinsJson | null> {
    if (!this.hasTwins()) return Promise.resolve(null);
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
    const sv = this.similarity.variables.find((v) => v.variable === variable);
    const info = this.varByName.get(variable) ?? (sv?.columns.EARTH ? this.varByName.get(sv.columns.EARTH) : undefined);
    if (info) return { label: info.label, unit: info.unit };
    return { label: SIMILARITY_FALLBACK_LABELS[variable] ?? variable.replace(/_/g, ' '), unit: '' };
  }

  /**
   * The full funnel of one Earth cell for one mission (docs/DATA_CONTRACT.md "The funnel"), with
   * the suitability rows for `weights` (the mission's own weights when omitted). Call prepareCell first.
   */
  outcome(id: number, missionId: string, weights?: readonly number[], alpha?: number): MissionOutcome {
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
      .sort((a, b) => (b.contribution ?? -1) - (a.contribution ?? -1));

    const p = landPos >= 0 ? md.passPos[landPos] : -1;
    const stored = (name: string) => (p >= 0 ? this.q(md.table, name, p) : null);
    const similarity = stored('similarity');
    let final = stored('final');
    let rank = stored('rank');
    const a = alpha ?? mission.alpha;
    const custom = weights !== undefined || alpha !== undefined;
    if (custom) {
      final = suit?.suitability != null && similarity != null ? pyRound2(finalOf(a, similarity, suit.suitability)) : null;
      rank = null; // the caller knows the recomputed rank
    }
    const ci = stored('confidence');
    const confidence = ci == null ? null : (this.missionsJson.confidence_codes[ci] ?? null);

    // similarity rows
    const twinId = p >= 0 && md.twin ? md.twin[p] : this.manifest.encoding.int32_missing;
    const twin = twinId !== this.manifest.encoding.int32_missing ? this.twin(missionId, twinId) : null;
    const target = this.similarity.target;
    const similarityRows: SimilarityRow[] = this.similarity.active_variables.map((f) => {
      const sv = this.similarity.variables.find((v) => v.variable === f)!;
      const { label, unit } = this.similarityLabel(f);
      const ez = tp ? this.q(tp.tile, `z.${f}`, tp.pos) : null;
      const ev = this.earthValue(sv.columns.EARTH, landPos).raw;
      let mz: number | null = null;
      let mv: number | null = null;
      if (target.kind === 'global_mean') {
        mz = target.profile[f]?.z ?? null;
        mv = target.profile[f]?.value ?? null;
      } else if (twin) {
        mz = twin.z[f] ?? null;
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
    const infoRows: InfoRow[] = this.similarity.not_part_of_similarity.map((variable) => {
      const info = this.varByName.get(variable);
      const earth = this.earthValue(info?.bodies.EARTH?.column ?? variable, landPos);
      let moonValue: number | string | null = null;
      let how: InfoRow['moon']['how'] = 'mean';
      if (target.kind === 'global_mean') {
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
    };
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
  recomputeSimilarity(missionId: string, landPos: number): number | null {
    const md = this.missionDataOf(missionId);
    const tp = this.tilePos(landPos);
    if (!tp) throw new Error('tile not loaded');
    const F = this.similarity.active_variables;
    const nw = F.map((f) => this.similarity.variables.find((v) => v.variable === f)!.norm_weight ?? 0);
    const ze = F.map((f) => this.q(tp.tile, `z.${f}`, tp.pos));
    let zm: (number | null)[];
    const target = this.similarity.target;
    if (target.kind === 'global_mean') zm = F.map((f) => target.profile[f]?.z ?? null);
    else {
      const p = md.passPos[landPos];
      const tw = md.twin ? this.twin(missionId, md.twin[p]) : null;
      zm = F.map((f) => tw?.z[f] ?? null);
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
