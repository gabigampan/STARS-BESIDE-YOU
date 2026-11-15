// Comparison panel (step "compare the pair"), in this order: place and true cell size; the result
// in one line; the lunar side; the hard filters; suitability by contribution with coverage;
// similarity (meaning, the variables that are part of it with both sides' values and z-scores, the
// ones that are not); alpha and the final as arithmetic; confidence; levels and sources on demand;
// the other two missions; the ice component for Lunar base; then Back and Start mission.

import type { GateRow, MissionOutcome, RequiredRow } from '../data/store.ts';
import type { Level } from '../data/types.ts';
import type { FlowApp } from './app';
import { missionName, statusWords } from './copy';
import { LEVEL_WORDS, button, capitalise, fixed, h, icon, int, latLonText, levelTag, num, valueText, verdict } from './dom';
import { levelLegend } from './legend';
import { hasVideo } from './media';

function cellSize(app: FlowApp, lat: number, body: 'EARTH' | 'MOON'): string {
  const g = app.store.manifest.grid.bodies[body];
  const ns = g.cell_ns_km;
  const ew = ns * Math.cos((lat * Math.PI) / 180);
  return `${int(ns)} km north-south x ${int(ew)} km east-west`;
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
  h('section', { class: 'panel-sec' }, h('h3', null, title), ...children);

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
          { class: r.pass ? 'is-pass' : 'is-fail' },
          h('th', { scope: 'row' }, app.store.labelOfMissionVariable(m.mission, r.gate.variable)),
          h('td', { class: 'mono' }, r.gate.limit),
          h('td', null, valueText(r.value.value, app.store.variable(r.gate.variable)?.unit ?? m.mission.weighted_variables.find((w) => w.variable === r.gate.variable)?.unit ?? '')),
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

export function renderDetail(root: HTMLElement, app: FlowApp, id: number, o: MissionOutcome): void {
  const store = app.store;
  const m = o.mission;
  const lat = store.latOf(id);
  const lon = store.lonOf(id);
  const place = store.place(o.landPos);
  const twins = store.hasTwins();
  const custom = app.usingCustom();
  const total = app.ranking().length;
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
    place.nearest && place.nearestKm != null ? h('p', { class: 'muted' }, `Nearest populated place: ${place.nearest}, ${num(place.nearestKm, 0)} km from the cell centre.`) : null,
  );

  // 2. result
  const result = o.pass
    ? h(
        'p',
        { class: 'result is-pass', 'data-result': 'pass' },
        verdict(true, ['Passes', '']),
        h('span', null, ` Rank ${rank ?? 'not ranked'} of ${int(total)} · final score `, h('strong', { class: 'final' }, fixed(o.final, 2)), ' / 100'),
        custom ? h('span', { class: 'tag' }, 'your weights') : null,
      )
    : h('p', { class: 'result is-fail', 'data-result': 'fail' }, verdict(false, ['', 'Eliminated for this mission']), h('span', { class: 'reason' }, `: ${o.line}`));

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
      h('p', { class: 'share' }, `${int(share)} Earth ${share === 1 ? 'point has' : 'points share'} this twin for the ${missionName(m).toLowerCase()} mission.`),
      t.feature ? h('p', null, h('a', { href: t.feature.url, target: '_blank', rel: 'noopener' }, `${t.feature.name} in the USGS/IAU Gazetteer of Planetary Nomenclature`, icon('ext'))) : null,
      h('p', { class: 'muted' }, `The twin is the most similar lunar cell inside ${m.similarity.zone?.name ?? "the mission's target zone"}. It is marked on the Moon globe and joined to this point by the beam.`),
    );
  } else if (twins) {
    lunar = h('section', { class: 'panel-sec lunar' }, h('h3', null, 'Lunar twin'), h('p', null, 'No lunar twin: a twin is designated only for points that pass this mission.'));
  } else {
    lunar = h(
      'section',
      { class: 'panel-sec lunar', 'data-twin': 'none' },
      h('h3', null, 'Lunar side'),
      h('p', { class: 'lead no-twin' }, app.noTwinText()),
      h('p', { class: 'muted' }, `The lunar reference is "${(store.similarity.target as { name?: string }).name ?? 'the whole-Moon average'}": the values in the similarity table below. There is no lunar marker, beam or paired view under this rule.`),
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
        null,
        h('th', { scope: 'row' }, r.wv.label, h('span', { class: 'sub' }, valueText(r.value.value, r.wv.unit), ' · ', levelTag(r.wv.levels.EARTH))),
        h('td', null, bar(r.utility), h('span', { class: 'num' }, r.utility == null ? 'no data' : num(r.utility, 3))),
        h('td', { class: 'num' }, num(r.weight, 2)),
        h('td', { class: 'num' }, r.contribution == null ? 'ignored' : num(r.contribution, 3)),
      ),
    );
    sections.push(
      sec(
        'Suitability',
        h('p', { class: 'lead' }, `Suitability `, h('strong', null, fixed(o.suitability, 2)), ' / 100', custom ? ' with your weights' : " with the team's weights", ` · ${statusWords(m).toLowerCase()}`),
        h('p', { class: 'muted' }, 'Each variable becomes a utility from 0 (the team\'s "bad" value) to 1 (its "good" value); suitability is the weighted mean x 100. Rows are sorted by contribution = weight x utility.'),
        h(
          'table',
          { class: 'rows suit' },
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Variable and value'), h('th', { scope: 'col' }, 'Utility 0-1'), h('th', { scope: 'col' }, 'Weight'), h('th', { scope: 'col' }, 'Contribution'))),
          h('tbody', null, rows),
        ),
        h('p', null, `Coverage ${num((o.coverage ?? 0) * 100, 1)} %: share of the total weight with data for this cell${(o.coverage ?? 1) < 1 ? '; the missing variables are ignored and the other weights renormalised' : ''}.`),
      ),
    );
  }

  // 6. similarity (shown for every cell, so an eliminated cell still shows how it compares)
  const moonHead = twins ? 'Lunar twin' : 'Whole-Moon average';
  const simRows = o.similarityRows.map((r) =>
    h(
      'tr',
      { class: r.clipped ? 'is-clipped' : '' },
      h('th', { scope: 'row' }, r.label, h('span', { class: 'sub' }, `weight ${num(r.normWeight, 3)}`)),
      h('td', null, h('span', { class: 'val' }, valueText(r.earth.value, r.unit)), h('span', { class: 'sub' }, zText(r.earth.z), ' · ', levelTag(r.earth.level))),
      h('td', null, h('span', { class: 'val' }, valueText(r.moon.value, r.unit)), h('span', { class: 'sub' }, zText(r.moon.z), ' · ', levelTag(r.moon.level))),
    ),
  );
  const notActive = store.similarity.variables.filter((v) => v.status !== 'active');
  const infoRows = o.infoRows.map((r) =>
    h(
      'tr',
      null,
      h('th', { scope: 'row' }, r.label, h('span', { class: 'sub' }, 'not part of the similarity')),
      h('td', null, h('span', { class: 'val' }, valueText(r.earth.value, r.unit)), h('span', { class: 'sub' }, levelTag(r.earth.level))),
      h('td', null, h('span', { class: 'val' }, valueText(r.moon.value, r.unit)), h('span', { class: 'sub' }, r.moon.how === 'commonest' ? 'commonest class · ' : r.moon.how === 'mean' ? 'whole-Moon mean · ' : '', levelTag(r.moon.level))),
    ),
  );
  sections.push(
    sec(
      'Similarity to the Moon',
      o.pass ? h('p', { class: 'lead' }, 'Similarity ', h('strong', null, fixed(o.similarity, 2)), ' / 100') : h('p', { class: 'lead' }, 'No similarity is scored for an eliminated cell; the values are shown for comparison.'),
      h(
        'p',
        { class: 'meaning' },
        icon('info'),
        h('span', null, 'What "similar" means here: each body is scaled on its own (z-scores), so a high similarity means this place sits in the same relative position on Earth as the lunar side does on the Moon. It does not mean equal values: compare the absolute values in each row.'),
      ),
      h(
        'table',
        { class: 'rows sim' },
        h('caption', null, 'Part of the similarity'),
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Variable'), h('th', { scope: 'col' }, 'This Earth cell'), h('th', { scope: 'col' }, moonHead))),
        h('tbody', null, simRows),
      ),
      notActive.length
        ? h(
            'ul',
            { class: 'notes' },
            notActive.map((v) =>
              h('li', null, h('strong', null, `${store.similarityLabel(v.variable).label}: `), v.status === 'excluded' ? 'excluded on these data. ' : 'not active on these data. ', capitalise(v.status_reason ?? '')),
            ),
          )
        : null,
      h(
        'table',
        { class: 'rows info' },
        h('caption', null, 'Shown for comparison, not part of the similarity'),
        h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Variable'), h('th', { scope: 'col' }, 'This Earth cell'), h('th', { scope: 'col' }, moonHead))),
        h('tbody', null, infoRows),
      ),
    ),
  );

  if (o.pass) {
    // 7. final as arithmetic
    sections.push(
      sec(
        'Final score',
        h(
          'p',
          { class: 'arith' },
          `Final = alpha x similarity + (1 - alpha) x suitability = ${num(alpha, 2)} x ${fixed(o.similarity, 2)} + ${num(1 - alpha, 2)} x ${fixed(o.suitability, 2)} = `,
          h('strong', null, fixed(o.final, 2)),
        ),
        h('p', { class: 'muted' }, `Alpha ${num(alpha, 2)}${custom && alpha !== m.alpha ? ` (yours; the team's is ${num(m.alpha, 2)})` : " (the team's value)"}.`),
      ),
    );
    // 8. confidence
    const levels = m.weighted_variables.map((w) => `${w.label}: Earth ${LEVEL_WORDS[w.levels.EARTH ?? 'NO_DATA']}, Moon ${LEVEL_WORDS[w.levels.MOON ?? 'NO_DATA']}`);
    sections.push(
      sec(
        'Confidence',
        h('p', { class: 'lead' }, h('strong', null, capitalise(o.confidence ?? 'none')), ` (score ${num(o.confidenceScore, 3)} of 1, with the team's weights)`),
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
        e ? h('p', null, h('span', { class: 'side' }, 'Earth: '), levelTag(e.level as Level), ` ${e.product || 'no product'}${e.true_baseline ? `; true baseline ${e.true_baseline}` : ''}. ${e.caveat ?? ''}`) : null,
        mo ? h('p', null, h('span', { class: 'side' }, 'Moon: '), levelTag(mo.level as Level), ` ${mo.product || 'no product'}. ${mo.caveat ?? ''}`) : null,
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
            h('span', { class: 'other-what' }, oo.pass ? `rank ${oo.rank} of ${int(x.ranked_count)}, final ${fixed(oo.final, 2)}` : oo.line),
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
          ice.pass ? ` · ice suitability ${fixed(ice.suitability, 2)} / 100` : h('span', { class: 'reason' }, `: ${ice.line}`),
        ),
        ice.pass
          ? h('ul', { class: 'notes' }, ice.utilities.map((u) => h('li', null, `${u.wv.label}: ${valueText(u.value.value, u.wv.unit)}, utility ${u.utility == null ? 'no data' : num(u.utility, 3)}`)))
          : null,
      ),
    );
  }

  sections.push(levelLegend());

  const foot = h('div', { class: 'panel-foot' }, backButton(app));
  if (hasVideo(m)) {
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
