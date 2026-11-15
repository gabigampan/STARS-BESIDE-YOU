// Types of the engine's static bundle v2 (docs/DATA_CONTRACT.md, contract revisions 4 to 6).
// Only the fields the app reads are typed; everything else stays available as unknown JSON.

export type BodyKey = 'EARTH' | 'MOON';
export type Level = 'MEASURED' | 'DERIVED' | 'MODELLED' | 'UNDOCUMENTED' | 'NO_DATA';

export interface Column {
  name: string;
  type: 'float32' | 'int32';
  rows: string;
  length: number;
  offset: number;
  missing: 'NaN' | number;
  scale: number | null;
  divisor?: number;
  codes?: string;
  unit?: string;
  per_grid_row?: boolean;
  description?: string;
}

export interface FileEntry {
  name: string;
  bytes: number;
  sha256?: string;
  format: 'json' | 'bin';
  load: 'start' | 'on_demand';
  description?: string;
  body?: BodyKey;
  mission?: string;
  row_sets?: Record<string, number>;
  columns?: Column[];
}

export interface DetailTile {
  name: string;
  row_start: number;
  row_end: number;
  land_cells: number;
}

export interface Manifest {
  bundle_version: string;
  contract_revision: number;
  engine_version: string;
  dataset: { id: string; why: string };
  build_time: string;
  similarity_rule: string;
  /** Revision 5: the similarity rule of each mission. */
  similarity_rules?: Record<string, string>;
  grid: {
    rows: number;
    cols: number;
    cell_deg: number;
    bodies: Record<BodyKey, { radius_km: number; cell_ns_km: number; cell_ew_km_at_equator: number; cell_ew_km_rule: string }>;
  };
  encoding: { int32_missing: number };
  counts: {
    EARTH: { cells: number; land_cells: number };
    MOON: { cells: number };
    missions: Record<string, { pass_EARTH: number; pass_MOON: number; ranked_EARTH: number; unpaired_EARTH?: number; distinct_twins: number }>;
  };
  load: { first_view: string[]; default_mission: string };
  detail_tiles: { rows_per_tile: number; lookup: string; files: DetailTile[] };
  files: FileEntry[];
  credits: string[];
  sizes?: { budget: { first_view_max: number; total_max: number } };
}

export interface Gate {
  variable: string;
  step: number;
  columns: Record<BodyKey, string | null>;
  origin: string;
  applies_to: BodyKey[];
  min: number | null;
  max: number | null;
  allow: string[] | null;
  exclude: string[] | null;
  limit: string;
  source: string;
}

export interface WeightedVariable {
  variable: string;
  kind: 'numeric' | 'categorical';
  label: string;
  unit: string;
  columns: Record<BodyKey, string | null>;
  levels: Record<BodyKey, Level | null>;
  weight: number;
  bad: number | null;
  good: number | null;
  map: Record<string, number> | null;
  default: number | null;
  why: string;
  also_in_similarity: boolean;
}

export interface ReasonCode {
  bit: number;
  code: string;
  variable: string;
  kind: 'missing' | 'below_min' | 'above_max' | 'not_allowed' | 'excluded';
  label: string;
  step: number;
  text: string;
  team_text: string;
}

export interface FunnelStep {
  step: number;
  name: string;
  text: string;
}

export interface ZoneInfo {
  name: string;
  kind: string;
  used?: string;
  reason?: string;
  why?: string;
  cells: number;
  regions?: string[] | null;
  source?: string;
  lat_max?: number | null;
  abs_lat_max?: number;
  elevation_max_m?: number;
}

/** Revision 5: one similarity variable of a real-value mission (missions.json similarity.variables). */
export interface PairVariable {
  variable: string;
  label: string;
  unit: string;
  role: 'key' | 'secondary' | string;
  weight: number;
  tolerance: number;
  bound: number;
  tolerance_set_by: string;
  why?: string;
  sides?: Record<BodyKey, { kind: string; column: string | null; level: Level | null; text: string }>;
  /** Columns of earth_<m>_pairs.bin: earth, moon, diff (real values); revision 6 adds earth_pct, moon_pct, diff_pct. */
  pairs_columns: Record<string, string>;
  /** Revision 6: the columns of the compared values (percentiles for a percentile-scaled variable). */
  compared_columns?: Record<string, string>;
  /** Revision 6: 'real' or 'percentile_within_population'. */
  scale?: string;
  /** Revision 6: the unit of the real values when the compared unit differs (K for a percentile variable). */
  real_unit?: string;
  score_column: string;
  /** Any further keys a later revision adds (scale, percentile columns...). */
  [key: string]: unknown;
}

export interface UnpairedReason {
  kind: string;
  variable: string;
  role: string;
  bound: number;
  earth_cells: number;
  gap_min: number;
  gap_median: number;
  gap_max: number;
}

export interface MissionSimilarity {
  rule: string;
  variables?: PairVariable[];
  weights_why?: string;
  score?: string;
  similarity_formula?: string;
  filter?: Record<string, string>;
  passing_count?: number;
  paired_count?: number;
  unpaired_count?: number;
  nopair_kinds?: string[];
  unpaired_reasons?: UnpairedReason[];
  pairs_file?: string;
  list_rule?: string;
  /** Revision 6 (lunar_base): values shown for information, read from the pairs file. */
  info_columns?: { variable: string; unit: string; columns: Record<string, string>; part_of_similarity: boolean }[];
  pair_sentence?: string;
  nopair_groups?: Record<string, string[]>;
  unpaired_by_kind?: Record<string, number>;
  twins?: unknown;
  no_twin_reason?: string;
  zone?: ZoneInfo;
  distinct_twins?: number;
  earth_cells_with_twin?: number;
  largest_share?: { twin_id: number; earth_cells: number; share: number };
}

export interface IceComponent {
  role: string;
  description: string;
  provisional: boolean;
  provisional_note: string | null;
  require_present: string[];
  gates: Gate[];
  weighted_variables: WeightedVariable[];
  reason_codes: ReasonCode[];
  pass_counts: Record<string, number>;
}

export interface Top5Spec {
  rule?: string;
  min_separation_deg?: number | null;
  min_separation_km?: number | null;
  ids: number[];
  overall_ranks?: number[];
}

export interface Mission {
  /** Revision 7: the five shown (ids in order) and the rule, in plain English. */
  top5?: Top5Spec;
  id: string;
  title: string;
  description: string;
  author: string;
  threshold_status: { status: 'provisional' | 'team_design_values' | string; text: string };
  provisional: boolean;
  provisional_note: string | null;
  components: { core: string | null; info: string[] };
  require_present: string[];
  files: Record<BodyKey, string>;
  gates: Gate[];
  weighted_variables: WeightedVariable[];
  reason_codes: ReasonCode[];
  pass_counts: { EARTH: number; EARTH_LAND_CELLS: number; MOON: number; MOON_CELLS: number };
  ranked_count: number;
  passing_without_similarity: number;
  top_failure_reasons: { EARTH_LAND: { reason: string; cells: number }[]; MOON: { reason: string; cells: number }[] };
  alpha: number;
  similarity: MissionSimilarity;
  confidence_counts: Record<string, number>;
  component_results: { ice?: IceComponent };
  known_limitations: string[];
}

export interface MissionsJson {
  bundle_version: string;
  offered_missions: string[];
  default_mission: string;
  alpha: number;
  alpha_why: string;
  similarity_rule: string;
  funnel: FunnelStep[];
  elimination_line_rule: string;
  confidence_codes: string[];
  missions: Mission[];
}

export interface BodyStats {
  valid: boolean;
  n: number;
  median: number | null;
  scale: number;
  mean: number | null;
  min: number | null;
  max: number | null;
  variation: string;
}

export interface SimilarityVariable {
  variable: string;
  status: 'active' | 'excluded' | 'inactive';
  status_reason: string | null;
  weight: number;
  norm_weight: number | null;
  columns: Record<BodyKey, string | null>;
  column_note: string;
  levels: Record<BodyKey, Level | null>;
  stats: Record<BodyKey, BodyStats>;
  target_global_mean?: { z: number | null; value: number | null };
}

export interface GlobalMeanTarget {
  kind: 'global_mean';
  name: string;
  profile: Record<string, { z: number | null; value: number | null }>;
  info_not_in_similarity: Record<string, { mean?: number; commonest?: string; level: Level; part_of_similarity: false }>;
}

export interface ZoneTwinTarget {
  kind: 'zone_twin';
  tie_rule: string;
  lunar_cells_filtered: boolean;
  zones: Record<string, ZoneInfo>;
}

export interface PlaceholderSpec {
  file: string;
  /** A single column; absent on a placeholder computed by a named rule (see `rule`). */
  column?: string;
  /** Contract 2026-11-15: a named display rule computed from several columns. */
  rule?: string;
  columns?: Record<string, string>;
  decimals?: number;
  multiply?: number;
  subtract?: number;
  meaning?: string;
}

export interface BundleText {
  decision: number | string;
  text: string;
  where: string;
  mission?: string;
  /** Revision 5: the missions the text applies to. */
  missions?: string[];
  mission_card?: boolean;
  /** Plain placeholders (a description) or per-pair placeholders (a pairs-file column). */
  placeholders?: Record<string, string | PlaceholderSpec>;
  variant_no_joint_match?: string;
  /** Revision 6: one sentence per no-twin kind. */
  variants?: Record<string, string>;
  /** Revision 6: a text that no longer applies (not shown). */
  status?: string;
  [key: string]: unknown;
}

export interface SimilarityJson {
  rule: string;
  /** Revision 5: the rule of each mission. */
  rules?: Record<string, string>;
  z_rule_missions?: string[];
  real_value?: { info_differences?: Record<string, string[] | string>; [key: string]: unknown };
  /** Revision 6: the percentile rule of lunar_base. */
  percentile_and_real?: { meaning?: string; [key: string]: unknown };
  rule_why?: string;
  rule_options?: Record<string, string>;
  alpha: number;
  // The z-score keys: absent since revision 6 when no shipped mission uses z-scores.
  formula?: { z: string; distance: string; similarity: string; decay: number; final: string };
  meaning?: string;
  earth_population?: { rule: string; cells: number };
  moon_population?: { rule: string; cells: number };
  variables?: SimilarityVariable[];
  active_variables?: string[];
  variation_findings?: { variable: string; body: BodyKey; variation: string; action: string }[];
  not_part_of_similarity?: string[];
  not_part_of_similarity_note?: string;
  target?: GlobalMeanTarget | ZoneTwinTarget;
  /** Contract revision 4: the approved web texts (decisions 1 to 5), verbatim. */
  texts?: Record<string, BundleText>;
  twins?: unknown;
  no_twin_reason?: string;
}

export interface BodyProvenance {
  column: string | null;
  stored: boolean;
  stored_as: string | null;
  level: Level | null;
  level_text: string | null;
  level_note: string | null;
  product: string;
  version: string;
  url: string;
  licence_credit: string;
  native_resolution: string;
  aggregation: string;
  true_baseline: string | null;
  true_baseline_km: number | null;
  cell_ns_km: number | null;
  caveat: string;
}

export interface VariableInfo {
  name: string;
  label: string;
  unit: string;
  kind: string;
  description: string;
  categories: string[] | null;
  /** English display labels of the categories, when the bundle provides them. */
  category_labels?: Record<string, string> | string[] | null;
  bodies: Partial<Record<BodyKey, BodyProvenance>>;
}

export interface LunarInfoColumn {
  column: string;
  stored_as: string;
  label: string;
  unit: string;
  note: string;
  level: Level;
  product: string;
  url: string;
  licence_credit: string;
  caveat: string;
}

export interface VariablesJson {
  levels: Record<string, string>;
  variables: VariableInfo[];
  lunar_info_columns: LunarInfoColumn[];
}

export interface PlacesJson {
  countries: { code: string; name: string }[];
  regions: string[];
  region_rule: string;
}

export interface PlaceDetailJson {
  label_rules: string[];
  label_rule_text: Record<string, string>;
  nearest_places: string[];
}

export interface Twin {
  id: number;
  lat: number;
  lon: number;
  earth_cells: number;
  /** z-score rules only. */
  z?: Record<string, number | null>;
  /** Revision 6: the twin's percentile within the zone for the percentile variables. */
  percentiles?: Record<string, number | null>;
  values: Record<string, number | null>;
  not_part_of_similarity: Record<string, number | string | null>;
  feature: { name: string; type: string; distance_km: number; url: string } | null;
}

export interface TwinsJson {
  gazetteer: string;
  missions: Record<
    string,
    {
      rule: string;
      distinct_twins: number;
      earth_cells_with_twin: number;
      largest_share: { twin_id: number; earth_cells: number; share: number };
      twins: Twin[];
    }
  >;
}

export interface IauFeatures {
  name: string[];
  type: string[];
  lat: number[];
  lon: number[];
  diameter_km: number[];
}

export type NumArray = Float32Array | Int32Array;
export type Columns = Record<string, NumArray>;

/** Revision 6: mission_zones.json (the lunar regions and why each mission is posed where it is). */
export interface ZoneRegion {
  code: string;
  label: string;
  rule: string;
  cells: number;
}

export interface MissionZonesJson {
  consulted_on: string;
  source_document: string;
  regions: ZoneRegion[];
  mission_zone_regions: Record<string, string[]>;
  texts: null | {
    general_note: string;
    zone_why: Record<string, string>;
    outside: Record<string, Record<string, string>>;
  };
  [key: string]: unknown;
}
