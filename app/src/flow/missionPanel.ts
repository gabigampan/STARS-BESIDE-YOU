// Mission panel (step "pick a point"): the mission and its status label, the counts in plain words,
// the weight sliders (one per weighted variable, plus alpha) and the ranked list (top 50, more on
// demand). A row, a marker click or Enter on a focused row opens the comparison.

import { globesApi } from '../api';
import type { Mission } from '../data/types.ts';
import type { FlowApp } from './app';
import { missionLine, missionName, statusWords } from './copy';
import { button, capitalise, fixed, h, icon, int, num } from './dom';
import { levelLegend } from './legend';

const PAGE = 50;

export class MissionPanel {
  private limit = PAGE;
  private listEl: HTMLOListElement | null = null;
  private moreEl: HTMLElement | null = null;
  private statusEl: HTMLElement | null = null;
  private weightsOpen = false;

  constructor(
    private readonly app: FlowApp,
    private readonly root: HTMLElement,
  ) {
    root.setAttribute('aria-label', 'Mission and ranked places');
  }

  renderLoading(m: Mission): void {
    this.root.replaceChildren(
      h('div', { class: 'panel-body' }, h('h2', { class: 'panel-title' }, missionName(m)), h('p', { class: 'loading-line', role: 'status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading the ranked places')),
    );
  }

  renderError(message: string, retry: () => void): void {
    this.root.hidden = false;
    this.root.replaceChildren(
      h('div', { class: 'panel-body' }, h('div', { class: 'alert', role: 'alert' }, h('p', null, message), button('Try again', retry, { kind: 'primary' }), button('Choose another mission', () => void this.app.changeMission(), { kind: 'quiet', icon: 'back' }))),
    );
  }

  render(): void {
    const m = this.app.mission();
    if (!m) return;
    this.limit = PAGE;
    const store = this.app.store;
    const land = store.manifest.counts.EARTH.land_cells;
    const pass = m.pass_counts.EARTH;
    const reasons = m.top_failure_reasons.EARTH_LAND.map((r) => {
      const code = m.reason_codes.find((c) => c.code === r.reason);
      const gate = code ? m.gates.find((g) => g.variable === code.variable) : undefined;
      const text = code ? `${capitalise(code.label)}${gate && code.kind !== 'missing' ? ` (limit ${gate.limit})` : ''}` : r.reason;
      return h('li', null, h('span', null, text), h('span', { class: 'count' }, `${int(r.cells)} cells`));
    });

    const head = h(
      'header',
      { class: 'panel-head' },
      button('Change mission', () => void this.app.changeMission(), { kind: 'quiet', icon: 'back', cls: 'btn-small' }),
      h('h2', { class: 'panel-title', tabindex: '-1' }, `${missionName(m)} mission`),
      h('p', { class: 'panel-sub' }, missionLine(m)),
      h(
        'p',
        { class: 'status-line' },
        h('span', { class: `tag tag-status` }, icon('info'), statusWords(m)),
        h('button', { type: 'button', class: 'linklike', onclick: () => this.app.openLimits(m.id) }, 'Known limitations'),
      ),
    );

    const counts = h(
      'section',
      { class: 'panel-sec counts', 'aria-label': 'How many places pass' },
      h('p', { class: 'lead' }, `Of ${int(land)} land cells on Earth, `, h('strong', null, `${int(pass)} pass`), ` the ${missionName(m).toLowerCase()} filters and are ranked; ${int(land - pass)} are eliminated.`),
      h('p', { class: 'muted' }, this.app.ruleText()),
    );
    const elim = h(
      'section',
      { class: 'panel-sec elim', 'aria-labelledby': 'elim-title' },
      h('h3', { id: 'elim-title' }, 'Why the other cells are eliminated'),
      h('p', { class: 'muted' }, 'Commonest reasons (a cell can fail several):'),
      h('ul', { class: 'reasons' }, reasons),
    );

    // weights
    const details = h('details', { class: 'panel-sec weights' }) as HTMLDetailsElement;
    details.open = this.weightsOpen;
    details.addEventListener('toggle', () => (this.weightsOpen = details.open));
    details.append(h('summary', null, 'Adjust the weights'));
    const w = this.app.weights();
    const sliders = h('div', { class: 'sliders' });
    const inputs: HTMLInputElement[] = [];
    m.weighted_variables.forEach((wv, i) => {
      const id = `w-${wv.variable}`;
      const out = h('output', { for: id, class: 'slider-val' }, num(w[i], 2));
      const input = h('input', { type: 'range', id, min: '0', max: '1', step: '0.05', value: String(w[i]), 'aria-describedby': `${id}-team` }) as HTMLInputElement;
      inputs.push(input);
      input.addEventListener('input', () => {
        out.textContent = num(Number(input.value), 2);
        void this.app.setWeights(inputs.map((x) => Number(x.value)), this.app.state.alpha);
      });
      sliders.append(
        h(
          'div',
          { class: 'slider' },
          h('label', { for: id }, wv.label),
          out,
          input,
          h('p', { class: 'slider-team', id: `${id}-team` }, `Team value ${num(wv.weight, 2)}`),
        ),
      );
    });
    const a = this.app.alpha();
    const aOut = h('output', { for: 'w-alpha', class: 'slider-val' }, num(a, 2));
    const aIn = h('input', { type: 'range', id: 'w-alpha', min: '0', max: '1', step: '0.05', value: String(a), 'aria-describedby': 'w-alpha-team' }) as HTMLInputElement;
    aIn.addEventListener('input', () => {
      aOut.textContent = num(Number(aIn.value), 2);
      void this.app.setWeights(this.app.state.weights ?? m.weighted_variables.map((x) => x.weight), Number(aIn.value));
    });
    sliders.append(
      h(
        'div',
        { class: 'slider slider-alpha' },
        h('label', { for: 'w-alpha' }, 'Alpha: share of similarity in the final score'),
        aOut,
        aIn,
        h('p', { class: 'slider-team', id: 'w-alpha-team' }, `Team value ${num(m.alpha, 2)}. Final = alpha x similarity + (1 - alpha) x suitability.`),
      ),
    );
    this.statusEl = h('p', { class: 'recompute-status', role: 'status' });
    details.append(
      h('p', { class: 'muted' }, 'Weights change the suitability only; the hard filters and the similarity stay as the team set them.'),
      sliders,
      button("Reset to team values", () => void this.app.resetWeights(), { kind: 'secondary', id: 'reset-weights' }),
      this.statusEl,
    );

    // ranking
    this.listEl = h('ol', { class: 'rank-list', 'aria-label': `Ranked places for the ${missionName(m)} mission` }) as HTMLOListElement;
    this.moreEl = h('div', { class: 'more' });
    const ranking = h(
      'section',
      { class: 'panel-sec ranking', 'aria-labelledby': 'ranking-title' },
      h('h3', { id: 'ranking-title' }, 'Ranked places'),
      h('p', { class: 'muted' }, 'Pick a place in the list or a marker on the Earth globe to compare it with the Moon. Up and Down move through the list; Enter opens the comparison.'),
      h('div', { class: 'rank-head', 'aria-hidden': 'true' }, h('span', null, 'Rank'), h('span', null, 'Place'), h('span', null, 'Final score')),
      this.listEl,
      this.moreEl,
    );

    this.root.replaceChildren(h('div', { class: 'panel-body' }, head, counts, details, ranking, elim, levelLegend()));
    this.setRecomputeStatus(this.app.usingCustom() ? 'custom' : 'team', this.app.lastRecomputeMs() ?? undefined);
    this.renderList();
    this.app.updateMoonNote();
  }

  renderList(): void {
    if (!this.listEl || !this.moreEl) return;
    const items = this.app.ranking();
    const shown = items.slice(0, this.limit);
    const rows = shown.map((it) => {
      const b = h(
        'button',
        { type: 'button', class: 'rank-row', 'data-id': String(it.id) },
        h('span', { class: 'rank-n' }, String(it.rank)),
        h('span', { class: 'rank-place' }, it.place),
        h('span', { class: 'rank-score' }, h('span', { class: 'score-bar', style: `--v:${Math.max(0, Math.min(100, it.final))}%`, 'aria-hidden': 'true' }), fixed(it.final, 2)),
      );
      b.setAttribute('aria-label', `Rank ${it.rank}: ${it.place}, final score ${fixed(it.final, 2)} of 100`);
      b.addEventListener('click', () => globesApi.markers.activate('earth', it.id));
      b.addEventListener('focus', () => globesApi.markers.setHighlighted('earth', it.id));
      b.addEventListener('blur', () => globesApi.markers.setHighlighted('earth', null));
      b.addEventListener('keydown', (e) => this.rowKey(e, b));
      return h('li', null, b);
    });
    this.listEl.replaceChildren(...rows);
    if (!items.length) {
      this.listEl.append(h('li', { class: 'empty' }, 'No place passes this mission with these settings. Use "Reset to team values" or choose another mission.'));
    }
    this.moreEl.replaceChildren();
    if (items.length > this.limit) {
      this.moreEl.append(
        h('p', { class: 'muted' }, `Showing ${int(shown.length)} of ${int(items.length)} ranked places.`),
        button(`Show ${Math.min(PAGE, items.length - this.limit)} more`, () => {
          const first = this.limit;
          this.limit += PAGE;
          this.renderList();
          (this.listEl?.querySelectorAll<HTMLElement>('.rank-row')[first])?.focus();
        }, { kind: 'secondary', id: 'show-more' }),
      );
    } else if (items.length) this.moreEl.append(h('p', { class: 'muted' }, `All ${int(items.length)} ranked places are listed.`));
  }

  private rowKey(e: KeyboardEvent, b: HTMLElement): void {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Home' && e.key !== 'End') return;
    const rows = Array.from(this.listEl?.querySelectorAll<HTMLElement>('.rank-row') ?? []);
    const i = rows.indexOf(b);
    const n = e.key === 'ArrowDown' ? i + 1 : e.key === 'ArrowUp' ? i - 1 : e.key === 'Home' ? 0 : rows.length - 1;
    if (n >= 0 && n < rows.length) rows[n].focus();
    e.preventDefault();
    e.stopPropagation();
  }

  focusRow(id: number): void {
    const items = this.app.ranking();
    const k = items.findIndex((x) => x.id === id);
    if (k >= this.limit) {
      this.limit = Math.ceil((k + 1) / PAGE) * PAGE;
      this.renderList();
    }
    const row = this.listEl?.querySelector<HTMLElement>(`.rank-row[data-id="${id}"]`);
    if (row) row.focus();
    else (this.root.querySelector('.panel-title') as HTMLElement | null)?.focus();
  }

  setRecomputeStatus(state: 'team' | 'custom' | 'loading' | 'error', detail?: number | string): void {
    if (!this.statusEl) return;
    this.statusEl.replaceChildren();
    this.root.dataset.weights = state === 'custom' ? 'custom' : 'team';
    if (state === 'loading') this.statusEl.append(h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading the per-cell utilities to recompute the scores');
    else if (state === 'error') this.statusEl.append(icon('cross'), `The scores could not be recomputed: ${detail}`);
    else if (state === 'custom') this.statusEl.append(icon('info'), `Your weights are in use: scores, ranks, markers and list recomputed in the browser${typeof detail === 'number' ? ` in ${num(detail, 0)} ms` : ''}.`);
    else this.statusEl.append(icon('check'), "The team's weights are in use.");
    const badge = this.root.querySelector('.weights summary');
    if (badge) badge.textContent = state === 'custom' ? 'Adjust the weights (your weights are in use)' : 'Adjust the weights';
  }
}
