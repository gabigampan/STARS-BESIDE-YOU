// "Data and limits": the existing credits dialog, with sections built from the bundle placed before
// the imagery credits: how to read the results, the funnel, each mission's status and known
// limitations, the data levels, and every data source with its licence and credit line.

import type { DataStore } from '../data/store.ts';
import type { Mission } from '../data/types.ts';
import { missionName, plainName, plainText, noteText, roleWord, setByWords, staleForRule, statusWords } from './copy';
import { gateWords, plainFunnel } from './funnel';
import { append, h, int, levelTag, valueText } from './dom';

const add = (el: Element, ...c: (Node | string | null)[]) => append(el, c);

export function renderDataDialog(store: DataStore, ruleText: (m: Mission) => string, meaning: (m: Mission) => string): void {
  seenTexts.clear();
  const body = document.getElementById('credits-body');
  if (!body) return;
  body.querySelector('.data-sections')?.remove();
  const g = store.manifest.grid.bodies;
  const wrap = h('div', { class: 'data-sections' });
  const missions = store.offeredMissions();

  add(
    wrap,
    h('h3', { class: 'dlg-h' }, 'How to read the results'),
    h('p', null, `Every point is a 1° grid cell: about ${int(g.EARTH.cell_ns_km)} km north-south on Earth and ${int(g.MOON.cell_ns_km)} km on the Moon (narrower east-west towards the poles). Every value is an average over the whole cell; nothing here describes a rover-scale site.`),
    h(
      'ul',
      { 'data-note': 'rules' },
      missions.map((m) =>
        h('li', { 'data-mission': m.id }, h('strong', null, `${missionName(m)}. `), h('span', { 'data-verbatim': store.hasTwins(m.id) ? null : 'no_twin_reason' }, ruleText(m).replace(/^Similarity rule: /, '')), ' ', h('span', { 'data-note': 'meaning' }, meaning(m))),
      ),
    ),
    h('p', null, 'Final score = alpha x similarity + (1 - alpha) x suitability; ', `alpha = ${store.missionsJson.alpha} for every mission (the team's value; it can be changed under "Adjust the weights").`),
  );

  add(wrap, h('h3', { class: 'dlg-h' }, 'The filter funnel (the same for every mission)'), h('ol', { class: 'funnel' }, plainFunnel(store, null, '', store.missionsJson.alpha).map((f) => h('li', null, h('strong', null, `${f.name}. `), f.text))));

  for (const m of missions) {
    const vars = store.pairVariables(m.id);
    add(
      wrap,
      h('h3', { class: 'dlg-h', id: `limits-${m.id}`, tabindex: '-1' }, `${missionName(m)} mission: known limitations`),
      h('p', null, h('strong', null, `${statusWords(m)}. `), m.threshold_status.status === 'provisional' ? 'The thresholds are provisional: they may change when the team fixes them.' : 'The thresholds are values set by the team, without an external source.'),
      h('p', null, h('strong', null, 'Hard filters: '), `${m.gates.map((g) => gateWords(store, m, g)).join('; ')}.`),
      vars.length
        ? h(
            'p',
            { 'data-note': 'tolerances' },
            h('strong', null, 'Tolerances of the pairs: '),
            vars.map((v) => `${v.label} ${valueText(v.tolerance, v.unit)} (${roleWord(v.role)}; set by ${setByWords(v.tolerance_set_by)})`).join('; ') + '.',
          )
        : null,
      // the engine's record, in plain words (file, code and column references left out)
      // an entry that describes the z-score similarity is left out for a mission that no longer uses it
      h('ul', { 'data-record': m.id }, dedupe(m.known_limitations.filter((l) => !staleForRule(store, m, l)).map((l) => plainText(store, l, m)), seenFor(m)).map((t) => h('li', null, t))),
      criteriaTable(store, m),
      // the bundle's notes for this place ("show" includes data_and_limits), verbatim
      ...store.notesFor('data_and_limits', m.id).filter((n) => n.missions).filter((n) => keep(noteText(store, n.text, m), seenFor(m))).map((n) => h('p', { class: 'bundle-note', 'data-text': n.key }, noteText(store, n.text, m))),
    );
  }
  const general = store.notesFor('data_and_limits', null).filter((n) => !n.missions);
  if (general.length) add(wrap, h('h3', { class: 'dlg-h' }, 'Notes on every mission'), ...general.map((n) => h('p', { class: 'bundle-note', 'data-text': n.key }, noteText(store, n.text))));

  add(wrap, 
    h('h3', { class: 'dlg-h' }, 'Data levels'),
    h('ul', { class: 'legend-list wide' }, Object.entries(store.variables.levels).filter(([k]) => usedLevels(store).has(k)).map(([k, t]) => h('li', null, levelTag(k as never), h('span', null, t)))),
  );

  // sources: one entry per product, with its licence and credit
  const products = new Map<string, { vars: string[]; licence: string; url: string; level: string }>();
  for (const v of store.variables.variables) {
    for (const [body, p] of Object.entries(v.bodies)) {
      if (!p || !p.product || (!p.licence_credit && !p.url)) continue;
      const key = p.product;
      const e = products.get(key) ?? { vars: [], licence: p.licence_credit, url: p.url, level: p.level ?? '' };
      e.vars.push(`${v.label} (${body === 'EARTH' ? 'Earth' : 'Moon'})`);
      products.set(key, e);
    }
  }
  for (const c of store.variables.lunar_info_columns) {
    products.set(c.product, { vars: [`${c.label} (Moon, information only)`], licence: c.licence_credit, url: c.url, level: c.level });
  }
  const dl = h('dl', { class: 'credits-list' });
  for (const [product, e] of products) {
    const firstUrl = e.url.split(/\s;\s|\s/).find((u) => /^https?:/.test(u));
    add(dl, 
      h('dt', null, firstUrl ? h('a', { href: firstUrl, target: '_blank', rel: 'noopener' }, plainName(product)) : plainName(product)),
      h('dd', null, `Used for: ${e.vars.join(', ')}.`),
      e.licence ? h('dd', { class: 'credit-line' }, plainText(store, e.licence)) : null,
    );
  }
  add(wrap, h('h3', { class: 'dlg-h' }, 'Data sources'), dl);
  add(wrap, h('h3', { class: 'dlg-h' }, 'Place names and other credits'), h('ul', null, store.manifest.credits.map((c) => h('li', null, plainText(store, c)))));
  add(wrap, h('h3', { class: 'dlg-h' }, 'Imagery and software'));
  body.prepend(wrap);
}

export function openDataDialog(missionId?: string): void {
  const dialog = document.getElementById('credits-dialog') as HTMLDialogElement | null;
  const opener = document.getElementById('credits-button');
  if (!dialog) return;
  const returnTo = document.activeElement as HTMLElement | null;
  if (!dialog.open) dialog.showModal();
  const target = missionId ? (document.getElementById(`limits-${missionId}`) as HTMLElement | null) : null;
  if (target) {
    target.scrollIntoView({ block: 'start' });
    target.focus({ preventScroll: true });
  } else (document.getElementById('credits-close') as HTMLElement | null)?.focus();
  // shell.ts returns focus to the header button; return it to the caller instead when opened from a panel
  if (returnTo && returnTo !== opener) dialog.addEventListener('close', () => window.setTimeout(() => returnTo.isConnected && returnTo.focus(), 0), { once: true });
}

/**
 * The sources of the zone explanations (revision 6 mission_zones.json): the consultation date, the
 * source document and any source list the bundle gives. Placed before the data sources, reachable
 * from the zone panel ("Sources of these texts").
 */
export function renderZoneSources(store: DataStore): void {
  const z = store.zones;
  const wrap = document.querySelector('#credits-body .data-sections');
  if (!z || !wrap || wrap.querySelector('#limits-zones')) return;
  const sources = (z as { sources?: unknown }).sources;
  const items = Array.isArray(sources)
    ? sources.map((s) => {
        if (typeof s === 'string') return h('li', null, /^https?:/.test(s) ? h('a', { href: s, target: '_blank', rel: 'noopener' }, s) : s);
        const o = s as { title?: string; label?: string; url?: string; id?: string };
        const text = o.title ?? o.label ?? o.url ?? o.id ?? '';
        return h('li', null, o.url ? h('a', { href: o.url, target: '_blank', rel: 'noopener' }, text) : text);
      })
    : [];
  const doc = z.source_document;
  const sec = h(
    'section',
    { class: 'zone-sources' },
    h('h3', { class: 'dlg-h', id: 'limits-zones', tabindex: '-1' }, 'Why each mission is searched in its zone: sources'),
    h(
      'p',
      null,
      `The texts about lunar missions and regions were checked against official mission pages on ${z.consulted_on}. `,
      /^https?:/.test(doc) ? h('a', { href: doc, target: '_blank', rel: 'noopener' }, 'Full source list') : `The full source list is kept with the project's documentation (${doc.replace(/^.*\//, '').replace(/\.md$/i, '').replace(/_/g, ' ').toLowerCase()}).`,
    ),
    items.length ? h('ul', null, items) : null,
  );
  const before = Array.from(wrap.querySelectorAll('h3.dlg-h')).find((x) => x.textContent === 'Data sources');
  if (before) wrap.insertBefore(sec, before);
  else wrap.append(sec);
}

/** The data levels some variable of the bundle actually has (a level no variable has is not offered). */
function usedLevels(store: DataStore): Set<string> {
  const used = new Set<string>();
  const vars = (store.variables as unknown as { variables: Record<string, { bodies?: Record<string, { level?: string } | null> }> | { bodies?: Record<string, { level?: string } | null> }[] }).variables;
  for (const v of Array.isArray(vars) ? vars : Object.values(vars ?? {})) for (const b of Object.values(v?.bodies ?? {})) if (b?.level) used.add(b.level);
  if (!used.size) for (const k of Object.keys(store.variables.levels)) used.add(k);
  return used;
}

/** Revision 8: the criteria set the mission was built with, and how it departs from the team's set. */
function criteriaTable(store: DataStore, m: Mission): HTMLElement | null {
  const cs = (m as unknown as { criteria_set?: { set?: string; title?: string; deviations?: { criterion: string; team?: { weight?: number } | null; ours?: { weight?: number } | null; reason?: string }[] } }).criteria_set;
  if (!cs) return null;
  const label = (v: string) => store.variables.variables?.[v as never]?.['label' as never] ?? plainText(store, v, m);
  const w = (x?: { weight?: number } | null) => (x == null ? 'not used' : x.weight != null ? `weight ${x.weight}` : 'used');
  const rows = (cs.deviations ?? []).map((d) =>
    h('tr', null, h('td', null, String(label(d.criterion))), h('td', null, w(d.team)), h('td', null, w(d.ours)), h('td', null, d.reason ? noteText(store, d.reason, m) : '')),
  );
  return h(
    'div',
    { class: 'criteria-set', 'data-criteria': cs.set ?? '' },
    h('p', null, h('strong', null, 'Criteria used: '), cs.title ?? cs.set ?? ''),
    rows.length
      ? // phones: the four columns scroll inside their own focusable region, never the dialog (regress check G)
        h(
          'div',
          { role: 'region', tabindex: '0', 'aria-label': `Departures from the team's criteria, ${missionName(m)} mission` },
          h(
          'table',
          { class: 'keys-table' },
          h('caption', { class: 'sr-only' }, `Departures from the team's criteria, ${missionName(m)} mission`),
          h('thead', null, h('tr', null, h('th', { scope: 'col' }, 'Criterion'), h('th', { scope: 'col' }, "Team's set"), h('th', { scope: 'col' }, 'Used here'), h('th', { scope: 'col' }, 'Why'))),
          h('tbody', null, rows),
          ),
        )
      : h('p', { class: 'muted' }, "No departure from the team's criteria."),
  );
}

/** Texts already printed for a mission in the dialog (starting with its five's rule). */
const seenTexts = new Map<string, string[]>();
function seenFor(m: Mission): string[] {
  let s = seenTexts.get(m.id);
  if (!s) seenTexts.set(m.id, (s = m.top5?.rule ? [m.top5.rule] : []));
  return s;
}
/** A text is printed unless its whole text, or its first sentence, is already contained in one printed above it. */
function keep(t: string, seen: string[]): boolean {
  const first = /^.*?\.(?=\s|$)/.exec(t)?.[0] ?? t;
  if (seen.some((x) => x.includes(t) || x.includes(first))) return false;
  seen.push(t);
  return true;
}
function dedupe(list: string[], seen: string[]): string[] {
  return list.filter((t) => keep(t, seen));
}
