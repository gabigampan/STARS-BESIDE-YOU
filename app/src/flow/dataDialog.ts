// "Data and limits": the existing credits dialog, with sections built from the bundle placed before
// the imagery credits: how to read the results, the funnel, each mission's status and known
// limitations, the data levels, and every data source with its licence and credit line.

import type { DataStore } from '../data/store.ts';
import { classWordsIn, missionName, statusWords } from './copy';
import { gateWords, plainFunnel } from './funnel';
import { append, capitalise, h, int, levelTag } from './dom';

const add = (el: Element, ...c: (Node | string | null)[]) => append(el, c);

export function renderDataDialog(store: DataStore, ruleText: string, meaning: string): void {
  const body = document.getElementById('credits-body');
  if (!body) return;
  body.querySelector('.data-sections')?.remove();
  const g = store.manifest.grid.bodies;
  const sim = store.similarity;
  const wrap = h('div', { class: 'data-sections' });

  add(wrap, 
    h('h3', { class: 'dlg-h' }, 'How to read the results'),
    h('p', null, `Every point is a 1° grid cell: about ${int(g.EARTH.cell_ns_km)} km north-south on Earth and ${int(g.MOON.cell_ns_km)} km on the Moon (narrower east-west towards the poles). Every value is an average over the whole cell; nothing here describes a rover-scale site.`),
    h('p', { 'data-note': 'meaning' }, meaning),
    h('p', { 'data-note': 'rule' }, h('strong', null, 'Similarity rule in use. '), h('span', { 'data-verbatim': store.hasTwins() ? null : 'no_twin_reason' }, store.hasTwins() ? capitalise(ruleText.replace(/^Similarity rule: /, '')) : ruleText.replace(/^Similarity rule: /, ''))),
    sim.no_twin_reason && !ruleText.includes(sim.no_twin_reason) ? h('p', null, sim.no_twin_reason) : null,
    h('p', null, 'Final score = alpha x similarity + (1 - alpha) x suitability; ', `alpha = ${store.missionsJson.alpha} for every mission (the team's value; it can be changed under "Adjust the weights").`),
  );

  add(wrap, h('h3', { class: 'dlg-h' }, 'The filter funnel (the same for every mission)'), h('ol', { class: 'funnel' }, plainFunnel(store, null, meaning, store.missionsJson.alpha).map((f) => h('li', null, h('strong', null, `${f.name}. `), f.text))));

  const solarLim = store.similarity.texts?.['solar_limitation']?.text;
  for (const m of store.offeredMissions()) {
    // the approved limitation describes the twin: shown in full under a twin rule, left out without twins (as on the card)
    const approved = store.hasTwins() ? m.known_limitations.filter((l) => l === solarLim) : [];
    const record = m.known_limitations.filter((l) => l !== solarLim || store.hasTwins()).filter((l) => !approved.includes(l));
    add(wrap,
      h('h3', { class: 'dlg-h', id: `limits-${m.id}`, tabindex: '-1' }, `${missionName(m)} mission: known limitations`),
      h('p', null, h('strong', null, `${statusWords(m)}. `), m.threshold_status.status === 'provisional' ? 'The thresholds are provisional: they may change when the team fixes them.' : 'The thresholds are values set by the team, without an external source.'),
      h('p', null, h('strong', null, 'Hard filters: '), `${m.gates.map((g) => gateWords(store, m, g)).join('; ')}.`),
      approved.length ? h('ul', null, approved.map((l) => h('li', null, l))) : null,
      // the engine's own record, with file and variable names: for reviewers, on demand
      h(
        'details',
        { class: 'team-note', 'data-record': m.id },
        h('summary', null, 'Technical record of these limitations'),
        h('p', null, classWordsIn(m.threshold_status.text)),
        h('ul', null, record.map((l) => h('li', null, classWordsIn(l)))),
        m.provisional_note ? h('p', null, "The team's original note (in Spanish, verbatim): ", h('span', { lang: 'es' }, m.provisional_note)) : null,
      ),
    );
  }

  // the code-level wording, for reviewers who want to trace a number to the engine
  add(
    wrap,
    h(
      'details',
      { class: 'tech-notes' },
      h('summary', null, 'Technical notes for reviewers'),
      h('p', null, `Similarity rule "${sim.rule}": ${sim.rule_options[sim.rule] ?? ''}`),
      h('p', null, `Alpha: ${store.missionsJson.alpha_why}`),
      h('p', null, 'The funnel as the engine states it:'),
      h('ol', { class: 'funnel' }, store.missionsJson.funnel.map((f) => h('li', null, h('strong', null, `${capitalise(f.name)}. `), f.text))),
    ),
  );

  add(wrap, 
    h('h3', { class: 'dlg-h' }, 'Data levels'),
    h('ul', { class: 'legend-list wide' }, Object.entries(store.variables.levels).map(([k, t]) => h('li', null, levelTag(k as never), h('span', null, t)))),
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
      h('dt', null, firstUrl ? h('a', { href: firstUrl, target: '_blank', rel: 'noopener' }, product) : product),
      h('dd', null, `Used for: ${e.vars.join(', ')}.`),
      e.licence ? h('dd', { class: 'credit-line' }, e.licence) : null,
    );
  }
  add(wrap, h('h3', { class: 'dlg-h' }, 'Data sources'), dl);
  add(wrap, h('h3', { class: 'dlg-h' }, 'Place names and other credits'), h('ul', null, store.manifest.credits.map((c) => h('li', null, c))));
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
