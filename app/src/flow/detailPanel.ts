// Comparison panel (step "compare the pair"), in this order: place and true cell size; the result
// in one line; the lunar side; the hard filters; suitability by contribution with coverage;
// similarity (meaning, the variables that are part of it with both sides' values and z-scores, the
// ones that are not); alpha and the final as arithmetic; confidence; levels and sources on demand;
// the other two missions; the ice component for Lunar base; then Back and Start mission.

import type { GateRow, MissionOutcome, PairRow, RequiredRow } from '../data/store.ts';
import type { Level, Mission, ReasonCode } from '../data/types.ts';
import type { FlowApp } from './app';
import { REGION_CAVEAT, firstSentence, missionName, plainName, plainText, roleWord, setByWords, statusWords } from './copy';
import { LEVEL_WORDS, button, capitalise, fixed, h, icon, int, latLonText, levelTag, limitWords, num, valueText, verdict } from './dom';
import { levelLegend } from './legend';
import { hasVideo } from './media';

/** Beyond this distance the nearest populated place says little about the cell, so it is not shown. */
const NEAREST_PLACE_MAX_KM = 300;

function cellSize(app: FlowApp, lat: number, body: 'EARTH' | 'MOON'): string {
  const g = app.store.manifest.grid.bodies[body];
  const ns = g.cell_ns_km;
  const ew = ns * Math.cos((lat * Math.PI) / 180);
  // one decimal below 10 km, so a polar cell never reads "0 km"
  return `${int(ns)} km north-south x ${ew < 10 ? num(ew, 1) : int(ew)} km east-west`;
}

/** The level word of a shown value: "no data" when the value is missing (one of the four levels). */
function levelOfValue(value: unknown, level: Level | string | null | undefined): HTMLElement | null {
  if (value != null && !level) return null; // a value whose level the bundle does not state: no word rather than a wrong one
  return levelTag(value == null ? 'NO_DATA' : (level as Level | null | undefined));
}

function unitOf(app: FlowApp, m: Mission, variable: string): string {
  return app.store.variable(variable)?.unit ?? m.weighted_variables.find((w) => w.variable === variable)?.unit ?? '';
}

/**
 * The true baseline and caveat of a relief variable (variables.json bodies.EARTH), resolving
 * "see <variable> baseline" to that variable's own text. Null for variables without a baseline.
 */
export function reliefNote(app: FlowApp, variable: string): { baseline: string; caveat: string } | null {
  const e = app.store.variable(variable)?.bodies.EARTH;
  if (!e?.true_baseline) return null;
  let caveat = e.caveat ?? '';
  let baseline = e.true_baseline;
  const ref = /^see (\S+) baseline$/.exec(caveat.trim());
  if (ref) {
    const r = app.store.variable(ref[1])?.bodies.EARTH;
    caveat = r?.caveat ?? '';
    if (/^see /.test(baseline)) baseline = r?.true_baseline ?? baseline;
  }
  return { baseline, caveat };
}

function reliefSub(app: FlowApp, variable: string): HTMLElement | null {
  const n = reliefNote(app, variable);
  return n ? h('span', { class: 'sub note', 'data-note': 'baseline' }, `True baseline: ${plainText(app.store, n.baseline)} (see "Slope and roughness" below)`) : null;
}

/** The caveat of every relief variable shown in the panel, once each (ASSUMPTIONS 0.9 item 3). */
function reliefSection(app: FlowApp, variables: string[]): HTMLElement | null {
  const seen = new Set<string>();
  const items: HTMLElement[] = [];
  for (const v of variables) {
    const n = reliefNote(app, v);
    const label = app.store.variable(v)?.label ?? v;
    if (!n || seen.has(label)) continue;
    seen.add(label);
    items.push(h('li', { 'data-variable': v }, h('strong', null, `${label}: `), `true baseline ${plainText(app.store, n.baseline)}. ${capitalise(firstSentence(plainText(app.store, n.caveat)))}`));
  }
  if (!items.length) return null;
  return h(
    'section',
    { class: 'panel-sec relief', 'data-sec': 'relief' },
    h('h3', null, 'Slope and roughness'),
    h('p', { class: 'muted' }, `These are averages over a cell of about ${int(app.store.manifest.grid.bodies.EARTH.cell_ns_km)} km, computed over kilometre baselines, not rover-scale values.`),
    h('ul', { class: 'notes' }, items),
  );
}

/** One elimination reason in plain words: the variable's label, this cell's value and the limit. */
export function reasonWords(app: FlowApp, o: MissionOutcome, r: ReasonCode): string {
  const m = o.mission;
  const label = app.store.labelOfMissionVariable(m, r.variable);
  if (r.kind === 'missing') return `${label}: no data for this cell`;
  const row = [...o.common, ...o.gates].find((g) => g.gate.variable === r.variable);
  if (!row) return capitalise(r.label);
  const unit = unitOf(app, m, r.variable);
  const val = valueText(row.value.value, unit);
  if (r.kind === 'below_min') return `${label} below the minimum: ${val}, needs ${limitWords(row.gate, unit)}`;
  if (r.kind === 'above_max') return `${label} above the maximum: ${val}, needs ${limitWords(row.gate, unit)}`;
  return `${label}: ${val}, which this mission excludes (${limitWords(row.gate, unit)})`;
}

/** Short reason labels (bundle reason_codes[].label), for lists. */
function reasonLabels(o: MissionOutcome): string {
  return o.reasons.map((r) => capitalise(r.label)).join('; ');
}

function backButton(app: FlowApp): HTMLButtonElement {
  return button('Back to the ranking', () => void app.backToRanking(), { kind: 'quiet', icon: 'back', cls: 'btn-small back-btn' });
}

export function renderDetailLoading(root: HTMLElement, app: FlowApp, id: number, error?: string, retry?: () => void): void {
  root.replaceChildren(
    h(
      'div',
      { class: 'panel-body' },
      backButton(app),
      h('h2', { class: 'panel-title', tabindex: '-1' }, app.placeText(id)),
      h('p', { class: 'muted' }, latLonText(app.store.latOf(id), app.store.lonOf(id))),
      error
        ? h('div', { class: 'alert', role: 'alert' }, h('p', null, error), retry ? button('Try again', retry, { kind: 'primary' }) : null)
        : h('p', { class: 'loading-line', role: 'status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading the details of this cell'),
    ),
  );
}

const sec = (title: string, ...children: (Node | string | null | false)[]) =>
  h('section', { class: 'panel-sec', 'data-sec': title.toLowerCase().replace(/[^a-z]+/g, '-').replace(/^-|-$/g, '') }, h('h3', null, title), ...children);

function gateTable(caption: string, rows: GateRow[], app: FlowApp, m: MissionOutcome): HTMLElement | null {
  if (!rows.length) return null;
  return h(
    'table',
    { class: 'rows gates' },
    h('caption', null, caption),
    h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Filter'), h('th', { scope: 'col' }, 'Limit'), h('th', { scope: 'col' }, 'This cell'), h('th', { scope: 'col' }, 'Result'))),
    h(
      'tbody',
      null,
      rows.map((r) =>
        h(
          'tr',
          { class: r.pass ? 'is-pass' : 'is-fail', 'data-variable': r.gate.variable, 'data-pass': String(r.pass) },
          h(
            'th',
            { scope: 'row' },
            app.store.labelOfMissionVariable(m.mission, r.gate.variable),
            reliefSub(app, r.gate.variable),
            r.gate.variable === 'mask_fraction' && typeof r.value.value === 'number' && r.value.value < 0.5
              ? h('span', { class: 'sub note', 'data-note': 'half-land' }, 'Less than half of this cell is land, so its averages mix land and sea: a coarse cell.')
              : null,
          ),
          h('td', { 'data-limit': r.gate.limit }, limitWords(r.gate, unitOf(app, m.mission, r.gate.variable))),
          h('td', null, h('span', { class: 'val' }, valueText(r.value.value, unitOf(app, m.mission, r.gate.variable))), h('span', { class: 'sub' }, levelOfValue(r.value.value, app.store.levelOf(r.gate.variable, 'EARTH')))),
          h('td', null, verdict(r.pass)),
        ),
      ),
    ),
  );
}

function requiredTable(rows: RequiredRow[]): HTMLElement | null {
  if (!rows.length) return null;
  return h(
    'table',
    { class: 'rows required' },
    h('caption', null, 'Step 2. Required data'),
    h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Variable'), h('th', { scope: 'col' }, 'Result'))),
    h('tbody', null, rows.map((r) => h('tr', null, h('th', { scope: 'row' }, r.label), h('td', null, verdict(r.present, ['Has data', 'No data']))))),
  );
}

function bar(v: number | null): HTMLElement {
  const pct = v == null ? 0 : Math.max(0, Math.min(1, v)) * 100;
  return h('span', { class: 'ubar', 'aria-hidden': 'true' }, h('span', { style: `width:${pct}%` }));
}

function zText(z: number | null): string {
  if (z == null) return 'z: no value';
  const s = num(z, 2);
  return Math.abs(z) >= 4 ? `z ${s} (at the clip: at least 4 spreads from the median)` : `z ${s}`;
}

/** The plain-words meaning of the similarity, from the bundle (decision 1; the generic meaning without twins). */
export function meaningText(app: FlowApp, m = app.mission()): string {
  const st = app.store;
  const general = st.similarity.meaning ?? '';
  if (m ? st.hasTwins(m.id) : st.hasTwins()) {
    // the approved meaning of this mission's rule (similarity_meaning_<rule> naming the mission, or the general one)
    const own = m ? st.textFor('similarity_meaning', m.id) : null;
    if (own) return own.text;
    if (m && st.isValueRule(m.id)) return st.text('similarity_meaning_real_values') ?? general;
    return st.text('similarity_meaning') ?? general;
  }
  // The approved sentence describes twins; without them the bundle's general meaning applies (its first sentence).
  return /^.*?\.(?=\s|$)/.exec(general)?.[0] ?? general;
}

function meaningNote(app: FlowApp): HTMLElement {
  return h('p', { class: 'meaning', 'data-note': 'meaning' }, icon('info'), h('span', null, meaningText(app)));
}

/** The short mark of decision 3, shared by the list and the panel. */
export function tempMark(app: FlowApp): HTMLElement | null {
  const t = app.store.text('missing_temperature_mark');
  return t ? h('span', { class: 'mark-temp', 'data-mark': 'missing-temperature' }, icon('info'), h('span', null, t)) : null;
}

function missingTempNote(app: FlowApp): HTMLElement | null {
  // The approved note describes a twin chosen on relief only: it applies only when the mission has twins.
  const t = app.missionHasTwins() ? app.store.text('missing_temperature_note') : null;
  return h('div', { class: 'note-box', 'data-note': 'missing-temperature' }, tempMark(app), t ? h('p', null, t) : null);
}

/** The lunar side in a few words: "near <feature>" or the twin cell's coordinates. */
function twinPlace(o: MissionOutcome): string {
  return o.twin?.feature ? `near ${o.twin.feature.name}` : o.twin ? `lunar cell at ${latLonText(o.twin.lat, o.twin.lon)}` : 'no lunar twin';
}

/** The approved per-pair sentences (e.g. the solar sentence), filled from the bundle and placed in the headline. */
function pairSentenceBoxes(o: MissionOutcome): HTMLElement[] {
  return o.pairSentences.map((ps) => h('div', { class: 'note-box pair-sentence', 'data-note': ps.key, role: 'note' }, icon('info'), h('p', null, ps.text)));
}

/** Headline of the pair (checklist 06 extra, legible from 2 m): the lunar match and the three scores. */
function pairStrip(app: FlowApp, o: MissionOutcome): HTMLElement | null {
  if (!o.pass) return null;
  const st = app.store;
  const twins = st.hasTwins(o.mission.id);
  const fig = (k: string, v: string, key: string) => h('div', { class: 'fig', 'data-fig': key }, h('dt', null, k), h('dd', null, v));
  if (o.noPair || (o.valueRule && o.final == null)) {
    return h(
      'div',
      { class: 'pair-strip is-unpaired', 'data-pair': 'none' },
      h('p', { class: 'pair-line' }, h('span', { class: 'pair-k' }, 'On the Moon'), h('strong', null, 'No lunar twin')),
      o.noPair ? h('p', { class: 'pair-reason', 'data-note': 'no-twin' }, o.noPair.sentence) : null,
      h('dl', { class: 'figs' }, fig('Suitability', fixed(o.suitability, 2), 'suitability')),
    );
  }
  const moon = twins ? twinPlace(o) : ((st.similarity.target as { name?: string } | undefined)?.name ?? 'the whole-Moon average');
  return h(
    'div',
    { class: 'pair-strip', 'data-pair': o.twin ? String(o.twin.id) : 'mean' },
    h('p', { class: 'pair-line' }, h('span', { class: 'pair-k' }, twins ? 'Paired on the Moon with' : 'Compared on the Moon with'), h('strong', null, moon)),
    h('dl', { class: 'figs' }, fig('Final', fixed(o.final, 2), 'final'), fig('Similarity', fixed(o.similarity, 2), 'similarity'), fig('Suitability', fixed(o.suitability, 2), 'suitability')),
    ...pairSentenceBoxes(o),
  );
}

/** A value with its unit; a difference of degrees Celsius is a difference in kelvin. */
function diffText(v: number | null, unit: string): string {
  return valueText(v, unit === 'degC' ? 'K' : unit);
}

/** How a side's real value is made, in words from the bundle ("modelled air temperature (WorldClim)"), with its level. */
function sideSub(app: FlowApp, r: PairRow, body: 'EARTH' | 'MOON'): HTMLElement | null {
  const sw = app.store.sideWords(r.def, body);
  if (!sw.words && !sw.level) return null;
  return h('span', { class: 'sub', 'data-k': `side-${body.toLowerCase()}` }, sw.words ?? '', sw.words ? ' · ' : '', levelTag(sw.level));
}

/** The similarity of a real-value pair: one block per variable (key variables first), the arithmetic, the information values. */
function pairSimilarity(app: FlowApp, o: MissionOutcome): (HTMLElement | null)[] {
  const st = app.store;
  const rows = [...o.pairRows].sort((a, b) => (a.def.role === 'key' ? 0 : 1) - (b.def.role === 'key' ? 0 : 1));
  const meaning = st.text('similarity_meaning_real_values');
  const block = (r: PairRow) =>
    h(
      'div',
      { class: `pair-var role-${r.def.role}`, 'data-variable': r.def.variable, 'data-within': String(r.within) },
      h('h4', { class: 'pair-var-head' }, h('span', null, r.def.label), h('span', { class: `tag tag-role` }, roleWord(r.def.role))),
      r.real ? h('p', { class: 'pair-scale' }, 'Compared as a position: the percentile of each side within its own population (Earth: the points passing this mission; Moon: the cells of the zone).') : null,
      h(
        'dl',
        { class: 'pair-vals' },
        h('div', { 'data-k': 'earth' }, h('dt', null, r.real ? 'Earth position' : 'Earth'), h('dd', null, valueText(r.earth, r.def.unit))),
        h('div', { 'data-k': 'moon' }, h('dt', null, r.real ? 'Moon position' : 'Moon'), h('dd', null, valueText(r.moon, r.def.unit))),
        h('div', { 'data-k': 'diff' }, h('dt', null, r.real ? 'Difference in position' : 'Difference'), h('dd', null, diffText(r.diff, r.def.unit))),
        h(
          'div',
          { 'data-k': 'tolerance' },
          h('dt', null, 'Tolerance'),
          h(
            'dd',
            null,
            valueText(r.def.tolerance, r.def.unit),
            r.def.bound !== r.def.tolerance ? h('span', { class: 'sub' }, `a pair may differ by up to ${valueText(r.def.bound, r.def.unit)} (twice the tolerance, secondary variable)`) : h('span', { class: 'sub' }, 'a pair may differ by up to the tolerance (key variable)'),
            h('span', { class: 'sub', 'data-k': 'set-by' }, `Set by: ${setByWords(r.def.tolerance_set_by)}`),
          ),
        ),
        h('div', { 'data-k': 'within' }, h('dt', null, 'Within'), h('dd', null, r.within == null ? 'no value on a side' : verdict(r.within, ['Within', 'Outside']))),
        h('div', { 'data-k': 'weight' }, h('dt', null, 'Weight'), h('dd', null, num(r.weight, 2))),
        h('div', { 'data-k': 'score' }, h('dt', null, 'Score 0-1'), h('dd', null, r.score == null ? 'left out (no value)' : fixed(r.score, 3))),
      ),
      r.real
        ? h(
            'dl',
            { class: 'pair-vals pair-real', 'data-k': 'real' },
            h('div', { 'data-k': 'earth-real' }, h('dt', null, 'Earth, real value'), h('dd', null, valueText(r.real.earth, r.real.unit), sideSub(app, r, 'EARTH'))),
            h('div', { 'data-k': 'moon-real' }, h('dt', null, 'Moon, real value'), h('dd', null, valueText(r.real.moon, r.real.unit), sideSub(app, r, 'MOON'))),
            h('div', { 'data-k': 'diff-real' }, h('dt', null, 'Real difference'), h('dd', null, diffText(r.real.diff, r.real.unit))),
          )
        : null,
    );
  const used = rows.filter((r) => r.score != null);
  const arith =
    o.similarity != null && used.length
      ? h(
          'p',
          { class: 'arith', 'data-value': 'sim-arith' },
          `Similarity = 100 x (${used.map((r) => `${num(r.weight, 2)} x ${fixed(r.score, 3)}`).join(' + ')}) / (${used.map((r) => num(r.weight, 2)).join(' + ')}) = `,
          h('strong', null, fixed(o.similarity, 2)),
        )
      : null;
  const info = o.pairInfo.length
    ? h(
        'table',
        { class: 'rows info pair-info' },
        h('caption', null, 'Shown for information, not part of the similarity'),
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Variable'), h('th', { scope: 'col' }, 'This Earth cell'), h('th', { scope: 'col' }, twinPlace(o)), h('th', { scope: 'col' }, 'Difference'))),
        h(
          'tbody',
          null,
          o.pairInfo.map((r) =>
            h(
              'tr',
              { 'data-variable': r.variable },
              h('th', { scope: 'row' }, r.label, r.variable === 'rock_or_bare_frac' && st.text('rock_note') ? h('span', { class: 'sub note', 'data-note': 'rock' }, st.text('rock_note')) : null),
              h('td', null, h('span', { class: 'val' }, valueText(r.earth, r.unit)), h('span', { class: 'sub' }, levelOfValue(r.earth, r.levels.EARTH))),
              h('td', null, h('span', { class: 'val' }, valueText(r.moon, r.unit)), h('span', { class: 'sub' }, levelOfValue(r.moon, r.levels.MOON))),
              h('td', null, r.diff == null ? (typeof r.earth === 'string' && typeof r.moon === 'string' ? (r.earth === r.moon ? 'same class' : 'different class') : 'no data') : valueText(r.diff, r.diffUnit)),
            ),
          ),
        ),
      )
    : null;
  return [
    h('p', { class: 'lead' }, 'Similarity ', h('strong', { 'data-value': 'similarity' }, fixed(o.similarity, 2)), ' / 100', app.usingCustom() ? ' with your weights' : " with the team's weights"),
    meaning ? h('p', { class: 'meaning', 'data-note': 'meaning' }, icon('info'), h('span', null, meaning)) : null,
    h('div', { class: 'pair-vars' }, rows.map(block)),
    arith,
    info,
  ];
}

export function renderDetail(root: HTMLElement, app: FlowApp, id: number, o: MissionOutcome): void {
  const store = app.store;
  const m = o.mission;
  const lat = store.latOf(id);
  const lon = store.lonOf(id);
  const place = store.place(o.landPos);
  const twins = store.hasTwins(m.id);
  const custom = app.usingCustom();
  const total = app.ranking().filter((r) => r.final != null).length;
  const unpaired = o.pass && o.final == null && (o.valueRule || o.noPair != null);
  const rank = o.pass ? (custom ? app.rankOf(id) : o.rank) : null;
  const alpha = app.alpha();

  // 1. place
  const head = h(
    'header',
    { class: 'panel-head' },
    h('p', { class: 'eyebrow' }, `${missionName(m)} mission · Earth point`),
    h('h2', { class: 'panel-title', tabindex: '-1' }, place.text ?? 'Unnamed land cell'),
    h('p', { class: 'coords' }, `${latLonText(lat, lon)} · cell ${id}`),
    h('p', { class: 'muted' }, `A 1° cell of about ${cellSize(app, lat, 'EARTH')}: every value below is an average over the whole cell, not a site.`),
    place.nearest && place.nearestKm != null && place.nearestKm <= NEAREST_PLACE_MAX_KM ? h('p', { class: 'muted' }, `Nearest populated place: ${place.nearest}, ${num(place.nearestKm, 0)} km from the cell centre.`) : null,
    place.region ? h('p', { class: 'muted', 'data-note': 'region' }, REGION_CAVEAT) : null,
    pairStrip(app, o),
  );

  // 2. result
  const result = unpaired
    ? h(
        'p',
        { class: 'result is-pass is-unpaired', 'data-result': 'no-twin' },
        verdict(true, ['Passes the filters', '']),
        h('span', null, ` · no lunar twin, so no rank and no final score · suitability `, h('strong', { class: 'final' }, fixed(o.suitability, 2)), ' / 100'),
        h('span', { class: 'tag' }, statusWords(m)),
        custom ? h('span', { class: 'tag' }, 'your weights') : null,
      )
    : o.pass
    ? h(
        'p',
        { class: 'result is-pass', 'data-result': 'pass', 'data-rank': String(rank ?? '') },
        verdict(true, ['Passes', '']),
        h('span', null, ` Rank ${rank == null ? 'not ranked' : int(rank)} of ${int(total)} · final score `, h('strong', { class: 'final' }, fixed(o.final, 2)), ' / 100'),
        h('span', { class: 'tag' }, statusWords(m)),
        custom ? h('span', { class: 'tag' }, 'your weights') : null,
        o.missingTemp ? tempMark(app) : null,
      )
    : h(
        'p',
        { class: 'result is-fail', 'data-result': 'fail' },
        verdict(false, ['', 'Eliminated for this mission:']),
        // plain words only (the engine's coded reason, reason_codes[].text, stays out of view: data-engine-reason)
        h('span', { class: 'reason', 'data-engine-reason': o.line }, o.reasons.map((r) => reasonWords(app, o, r)).join('; ') + '.'),
      );

  // 3. the lunar side, up front: which place on the Moon this point is compared with
  let lunar: HTMLElement;
  if (twins && o.twin) {
    const t = o.twin;
    const share = store.twinsOf(m.id).find((x) => x.id === t.id)?.earth_cells ?? t.earth_cells;
    lunar = h(
      'section',
      { class: 'panel-sec lunar', 'data-twin': String(t.id) },
      h('h3', null, 'Lunar twin'),
      h(
        'p',
        { class: 'lead' },
        t.feature ? h('strong', null, `Near ${t.feature.name}`) : h('strong', null, 'Lunar cell'),
        t.feature ? ` (${t.feature.type.replace(/,.*$/, '').toLowerCase()}), ${num(t.feature.distance_km, 1)} km from its centre` : '',
      ),
      h('p', { class: 'coords' }, `Twin cell centre ${latLonText(t.lat, t.lon)} · cell of about ${cellSize(app, t.lat, 'MOON')}`),
      h('p', { class: 'share', 'data-share': String(share) }, store.twinSharingText(m.id, share) ?? `${int(share)} Earth points share this twin.`),
      t.feature ? h('p', null, h('a', { href: t.feature.url, target: '_blank', rel: 'noopener' }, `${t.feature.name} in the USGS/IAU Gazetteer of Planetary Nomenclature`, icon('ext'))) : null,
      h(
        'p',
        { class: 'muted' },
        o.valueRule
          ? `The twin is the lunar cell inside ${app.zoneName(m) ?? "the mission's target zone"} whose real values are closest within the tolerances. It is marked on the Moon globe and joined to this point by the beam.`
          : `The twin is the most similar lunar cell inside ${app.zoneName(m) ?? "the mission's target zone"}. It is marked on the Moon globe and joined to this point by the beam.`,
      ),
    );
  } else if (unpaired) {
    lunar = h(
      'section',
      { class: 'panel-sec lunar', 'data-twin': 'none' },
      h('h3', null, 'Lunar twin'),
      h('p', { class: 'lead' }, h('strong', null, 'No lunar twin'), o.noPair ? ' (the reason is given above).' : '.'),
      h('p', { class: 'muted' }, 'There is no lunar marker, beam or paired view for this point. Its filters and suitability below are complete, and the mission can still be started.'),
    );
  } else if (twins) {
    lunar = h('section', { class: 'panel-sec lunar' }, h('h3', null, 'Lunar twin'), h('p', null, 'No lunar twin: a twin is designated only for points that pass this mission.'));
  } else {
    lunar = h(
      'section',
      { class: 'panel-sec lunar', 'data-twin': 'none' },
      h('h3', null, 'Lunar side'),
      h('p', { class: 'lead no-twin', 'data-verbatim': 'no_twin_reason' }, app.noTwinText(m)),
      h('p', { class: 'muted' }, `The lunar reference is "${(store.similarity.target as { name?: string } | undefined)?.name ?? 'the whole-Moon average'}": the values in the similarity table below. There is no lunar marker, beam or paired view under this rule.`),
    );
  }

  // 4. hard filters
  const filters = sec(
    'Hard filters',
    h('p', { class: 'muted' }, `Failing any filter eliminates the cell for this mission. Thresholds: ${statusWords(m).toLowerCase()}.`),
    gateTable('Step 1. Common filters (every mission)', o.common, app, o),
    requiredTable(o.required),
    gateTable('Step 3. Mission filters', o.gates, app, o),
  );

  const sections: (HTMLElement | null)[] = [head, result, lunar, filters];

  if (o.pass) {
    // 5. suitability
    const rows = o.breakdown.map((r) =>
      h(
        'tr',
        { 'data-variable': r.wv.variable },
        h('th', { scope: 'row' }, r.wv.label, h('span', { class: 'sub' }, valueText(r.value.value, r.wv.unit), ' · ', levelOfValue(r.value.value, r.wv.levels.EARTH)), reliefSub(app, r.wv.variable)),
        h('td', null, bar(r.utility), h('span', { class: 'num' }, r.utility == null ? 'no data' : num(r.utility, 3))),
        h('td', { class: 'num' }, num(r.weight, 2)),
        h('td', { class: 'num' }, r.contribution == null ? 'ignored' : num(r.contribution, 3)),
      ),
    );
    sections.push(
      sec(
        'Suitability',
        h('p', { class: 'lead' }, `Suitability `, h('strong', { 'data-value': 'suitability' }, fixed(o.suitability, 2)), ' / 100', custom ? ' with your weights' : " with the team's weights", ` · ${statusWords(m).toLowerCase()}`),
        h('p', { class: 'muted' }, 'Each variable becomes a utility from 0 (the team\'s "bad" value) to 1 (its "good" value); suitability is the weighted mean x 100. Rows are sorted by contribution = weight x utility.'),
        h(
          'table',
          { class: 'rows suit' },
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Variable and value'), h('th', { scope: 'col' }, 'Utility 0-1'), h('th', { scope: 'col' }, 'Weight'), h('th', { scope: 'col' }, 'Contribution'))),
          h('tbody', null, rows),
        ),
        h('p', { 'data-value': 'coverage' }, `Coverage ${num((o.coverage ?? 0) * 100, 1)} %: share of the total weight with data for this cell${(o.coverage ?? 1) < 1 ? '; the missing variables are ignored and the other weights renormalised' : ''}.`),
      ),
    );
  }

  // 6. similarity (shown for every cell, so an eliminated cell still shows how it compares)
  const moonHead = twins ? (o.twin?.feature ? `Lunar twin, near ${o.twin.feature.name}` : 'Lunar twin') : 'Whole-Moon average';
  // An eliminated cell has no twin under a twin rule: show its Earth values only.
  const showMoon = o.pass || !twins;
  const moonCell = (c: HTMLElement) => (showMoon ? c : null);
  const simRows = o.similarityRows.map((r) =>
    h(
      'tr',
      { class: r.clipped ? 'is-clipped' : '', 'data-variable': r.sv.variable },
      h('th', { scope: 'row' }, r.label, h('span', { class: 'sub' }, `weight ${num(r.normWeight, 3)}`), reliefSub(app, r.sv.columns.EARTH && store.variable(r.sv.columns.EARTH) ? r.sv.columns.EARTH : r.sv.variable)),
      h('td', null, h('span', { class: 'val' }, valueText(r.earth.value, r.unit)), h('span', { class: 'sub' }, zText(r.earth.z), ' · ', levelOfValue(r.earth.value, r.earth.level))),
      moonCell(h('td', null, h('span', { class: 'val' }, valueText(r.moon.value, r.unit)), h('span', { class: 'sub' }, zText(r.moon.z), ' · ', levelOfValue(r.moon.value, r.moon.level)))),
    ),
  );
  const notActive = (store.similarity.variables ?? []).filter((v) => v.status !== 'active');
  const infoRows = o.infoRows.map((r) =>
    h(
      'tr',
      { 'data-variable': r.variable },
      h(
        'th',
        { scope: 'row' },
        r.label,
        h('span', { class: 'sub' }, 'not part of the similarity'),
        r.variable === 'rock_or_bare_frac' && store.text('rock_note') ? h('span', { class: 'sub note', 'data-note': 'rock' }, store.text('rock_note')) : null,
      ),
      h('td', null, h('span', { class: 'val' }, valueText(r.earth.value, r.unit)), h('span', { class: 'sub' }, levelOfValue(r.earth.value, r.earth.level))),
      moonCell(h('td', null, h('span', { class: 'val' }, valueText(r.moon.value, r.unit)), h('span', { class: 'sub' }, r.moon.how === 'commonest' ? 'commonest class · ' : r.moon.how === 'mean' ? 'whole-Moon mean · ' : '', levelOfValue(r.moon.value, r.moon.level)))),
    ),
  );
  if (o.valueRule) {
    sections.push(
      sec(
        'Similarity to the Moon',
        ...(o.pass && o.final != null && o.pairRows.length
          ? pairSimilarity(app, o)
          : [
              h(
                'p',
                { class: 'lead' },
                o.pass ? 'No similarity is computed for a point without a lunar twin: it has no rank and no final score.' : 'No similarity and no lunar twin are computed for a cell eliminated for this mission.',
              ),
              store.text('similarity_meaning_real_values') ? h('p', { class: 'meaning', 'data-note': 'meaning' }, icon('info'), h('span', null, store.text('similarity_meaning_real_values'))) : null,
            ]),
      ),
    );
  } else sections.push(
    sec(
      'Similarity to the Moon',
      o.pass
        ? h('p', { class: 'lead' }, 'Similarity ', h('strong', { 'data-value': 'similarity' }, fixed(o.similarity, 2)), ' / 100', o.simVarsUsed != null ? h('span', { class: 'muted' }, ` · computed with ${o.simVarsUsed} of ${store.similarity.active_variables?.length ?? 0} variables`) : null)
        : h('p', { class: 'lead' }, twins ? 'No similarity and no lunar twin are computed for a cell eliminated for this mission; its Earth values are shown for reference.' : 'No similarity is scored for an eliminated cell; the values are shown for comparison.'),
      meaningNote(app),
      o.missingTemp ? missingTempNote(app) : null,
      h(
        'table',
        { class: 'rows sim' },
        h('caption', null, 'Part of the similarity'),
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Variable'), h('th', { scope: 'col' }, 'This Earth cell'), moonCell(h('th', { scope: 'col' }, moonHead)))),
        h('tbody', null, simRows),
      ),
      notActive.length
        ? h(
            'ul',
            { class: 'notes' },
            notActive.map((v) =>
              h(
                'li',
                null,
                h('strong', null, `${store.similarityLabel(v.variable).label}: `),
                v.status === 'excluded' ? 'excluded on these data. ' : 'not active on these data. ',
                v.variable === 'rock_or_bare_frac' && store.text('rock_note') ? 'Shown below for information.' : `${capitalise((v.status_reason ?? '').replace(/\s*\([^)]*\)\s*$/, ''))}.`,
              ),
            ),
          )
        : null,
      h(
        'table',
        { class: 'rows info' },
        h('caption', null, 'Shown for comparison, not part of the similarity'),
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Variable'), h('th', { scope: 'col' }, 'This Earth cell'), moonCell(h('th', { scope: 'col' }, moonHead)))),
        h('tbody', null, infoRows),
      ),
    ),
  );

  sections.push(
    reliefSection(app, [
      ...[...o.common, ...o.gates].map((g) => g.gate.variable),
      ...o.breakdown.map((b) => b.wv.variable),
      ...o.similarityRows.map((r) => (r.sv.columns.EARTH && store.variable(r.sv.columns.EARTH) ? r.sv.columns.EARTH : r.sv.variable)),
      ...o.pairRows.map((r) => r.def.sides?.EARTH?.column ?? r.def.variable),
    ]),
  );

  if (o.pass && o.final != null) {
    // 7. final as arithmetic
    sections.push(
      sec(
        'Final score',
        h(
          'p',
          { class: 'arith', 'data-value': 'arith' },
          `Final = alpha x similarity + (1 - alpha) x suitability = ${num(alpha, 2)} x ${fixed(o.similarity, 2)} + ${num(1 - alpha, 2)} x ${fixed(o.suitability, 2)} = `,
          h('strong', null, fixed(o.final, 2)),
        ),
        h('p', { class: 'muted' }, `Alpha ${num(alpha, 2)}${custom && alpha !== m.alpha ? ` (yours; the team's is ${num(m.alpha, 2)})` : " (the team's value)"}.`),
      ),
    );
  }
  if (o.pass && o.confidence != null) {
    // 8. confidence
    const levels = m.weighted_variables.map((w) => `${w.label}: Earth ${LEVEL_WORDS[w.levels.EARTH ?? 'NO_DATA']}, Moon ${LEVEL_WORDS[w.levels.MOON ?? 'NO_DATA']}`);
    sections.push(
      sec(
        'Confidence',
        h('p', { class: 'lead', 'data-value': 'confidence' }, h('strong', null, capitalise(o.confidence ?? 'none')), ` (score ${num(o.confidenceScore, 3)} of 1, with the team's weights)`),
        h(
          'p',
          { class: 'muted' },
          `Why: confidence comes only from the data levels of this mission's weighted variables on both bodies and from the coverage (${num((o.coverage ?? 0) * 100, 0)} %). It does not measure the similarity or the quality of this cell's own data. Levels: ${levels.join('; ')}.`,
        ),
      ),
    );
  }

  // 9. levels and sources on demand
  const used = new Map<string, string>();
  for (const g of [...o.common, ...o.gates]) used.set(g.gate.variable, g.gate.columns.EARTH ?? g.gate.variable);
  for (const r of o.breakdown) used.set(r.wv.variable, r.wv.columns.EARTH ?? r.wv.variable);
  for (const r of o.similarityRows) used.set(r.sv.variable, r.sv.columns.EARTH ?? r.sv.variable);
  for (const r of o.infoRows) used.set(r.variable, r.variable);
  const src = h('details', { class: 'panel-sec sources' }, h('summary', null, 'Data level and source of each value'));
  const seen = new Set<string>();
  for (const [variable, column] of used) {
    const info = store.variable(variable) ?? store.variable(column);
    if (!info || seen.has(info.name)) continue;
    seen.add(info.name);
    const e = info.bodies.EARTH;
    const mo = info.bodies.MOON;
    src.append(
      h(
        'div',
        { class: 'src' },
        h('h4', null, info.label),
        e ? h('p', null, h('span', { class: 'side' }, 'Earth: '), levelTag(e.level as Level), ` ${plainName(e.product || 'no product')}${e.true_baseline ? `; true baseline ${e.true_baseline}` : ''}. ${plainText(store, e.caveat ?? '')}`) : null,
        mo ? h('p', null, h('span', { class: 'side' }, 'Moon: '), levelTag(mo.level as Level), ` ${plainName(mo.product || 'no product')}. ${plainText(store, mo.caveat ?? '')}`) : null,
      ),
    );
  }
  sections.push(src);

  // 10. the other missions
  const others = store.offeredMissions().filter((x) => x.id !== m.id);
  sections.push(
    sec(
      'The same cell in the other missions',
      h(
        'ul',
        { class: 'others' },
        others.map((x) => {
          const oo = store.outcome(id, x.id);
          return h(
            'li',
            { 'data-mission': x.id },
            h('span', { class: 'other-name' }, missionName(x)),
            verdict(oo.pass, ['Passes', 'Eliminated']),
            h(
              'span',
              { class: 'other-what' },
              oo.pass
                ? oo.final == null
                  ? `no lunar twin, suitability ${fixed(oo.suitability, 2)}`
                  : `rank ${oo.rank == null ? 'not ranked' : int(oo.rank)} of ${int(x.ranked_count)}, final ${fixed(oo.final, 2)}`
                : reasonLabels(oo),
            ),
            button(`Open in ${missionName(x)}`, () => void app.select(id, x.id), { kind: 'quiet', cls: 'btn-small', iconAfter: 'next' }),
          );
        }),
      ),
      h('p', { class: 'muted' }, "Scores in other missions use the team's weights."),
    ),
  );

  // 11. ice component (lunar base)
  if (o.ice) {
    const ice = o.ice;
    sections.push(
      sec(
        'Ice prospecting (information only)',
        h('p', { class: 'muted' }, m.component_results.ice?.role ? capitalise(m.component_results.ice.role) + '.' : 'Information only; never changes the ranking.'),
        h(
          'p',
          null,
          verdict(ice.pass, ['Passes the ice filters', 'Does not pass the ice filters']),
          ice.pass ? ` · ice suitability ${fixed(ice.suitability, 2)} / 100` : h('span', { class: 'reason' }, `: ${ice.reasons.map((r) => capitalise(r.label)).join('; ')}`),
        ),
        ice.pass
          ? h('ul', { class: 'notes' }, ice.utilities.map((u) => h('li', null, `${u.wv.label}: ${valueText(u.value.value, u.wv.unit)}, utility ${u.utility == null ? 'no data' : num(u.utility, 3)}`)))
          : null,
      ),
    );
  }

  sections.push(levelLegend());

  const foot = h('div', { class: 'panel-foot' }, backButton(app));
  if (hasVideo(m) && o.pass) {
    foot.append(button(`Start the ${missionName(m).toLowerCase()} mission`, () => void app.startMission(), { kind: 'primary', icon: 'play', id: 'start-mission' }));
  }
  const body = h('div', { class: 'panel-body' }, ...sections.filter(Boolean));
  const scrollTop = root.querySelector('.panel-scroll')?.scrollTop ?? 0;
  const sameCell = root.dataset.cell === String(id) && root.dataset.mission === m.id;
  root.dataset.cell = String(id);
  root.dataset.mission = m.id;
  root.dataset.pass = o.pass ? 'true' : 'false';
  const scroll = h('div', { class: 'panel-scroll' }, body);
  root.replaceChildren(scroll, foot);
  if (sameCell) scroll.scrollTop = scrollTop;
}
