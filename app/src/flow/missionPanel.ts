// Mission panel (step "pick a point"): the mission and its status label, the counts in plain words,
// the weight sliders (one per weighted variable, plus alpha) and the ranked list (top 50, more on
// demand). A row, a marker click or Enter on a focused row opens the comparison.

import { globesApi } from '../api';
import type { Mission } from '../data/types.ts';
import type { FlowApp } from './app';
import { missionLine, missionName, noPairKindWords, roleWord, statusWords, noteText } from './copy';
import { ceil2, sentenceUnit, type NoPair } from '../data/store.ts';
import { button, capitalise, fixed, h, icon, int, latLonText, num } from './dom';
import type { RankItem } from './app';
import { levelLegend } from './legend';
import { meaningText, tempMark } from './detailPanel';
import { gateWords, plainFunnel } from './funnel';

const PAGE = 50;

export class MissionPanel {
  private limit = PAGE;
  private listEl: HTMLOListElement | null = null;
  private moreEl: HTMLElement | null = null;
  private statusEl: HTMLElement | null = null;
  private weightsOpen = false;
  private query = '';
  /** Which points the list shows: all, only those with a lunar twin, only those without. */
  private show: 'all' | 'paired' | 'unpaired' = 'all';
  private showFor: string | null = null;

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
      const text = code ? (gate && code.kind !== 'missing' ? `${gateWords(store, m, gate)} not met` : capitalise(code.label)) : r.reason;
      return h('li', null, h('span', null, text), h('span', { class: 'count' }, `${int(r.cells)} cells`));
    });

    const head = h(
      'header',
      { class: 'panel-head' },
      button('Change mission', () => void this.app.changeMission(), { kind: 'quiet', icon: 'back', cls: 'btn-small' }),
      h('h2', { class: 'panel-title', tabindex: '-1' }, `${missionName(m)} mission`),
      h(
        'p',
        { class: 'status-line' },
        h('span', { class: `tag tag-status` }, icon('info'), statusWords(m)),
        h('button', { type: 'button', class: 'linklike', onclick: () => this.app.openLimits(m.id) }, 'Known limitations'),
      ),
      this.limitationNote(m),
      this.cardNotes(m),
    );

    // the counts sit under the list heading, one line, so the list starts in the first view (checklist 06/03)
    const pc = store.pairCounts(m.id);
    const twinsHere = this.app.missionHasTwins(m);
    const counts = h(
      'p',
      { class: 'counts', 'aria-label': 'How many places pass', 'data-paired': String(pc.paired), 'data-unpaired': String(pc.unpaired) },
      twinsHere && pc.unpaired > 0
        ? [h('strong', null, `${int(pc.paired)} of ${int(pass)} points have a lunar twin.`), ` ${int(pass)} pass the ${missionName(m).toLowerCase()} filters, of ${int(land)} land cells on Earth; ${int(land - pass)} are eliminated.`]
        : [h('strong', null, `${int(pass)} pass`), ` the ${missionName(m).toLowerCase()} filters and are ranked${twinsHere ? ', each with a lunar twin' : ''}, of ${int(land)} land cells on Earth; ${int(land - pass)} are eliminated.`],
    );
    // the rule and the true cell size, right under the list (so the list starts in the first view)
    const about = h(
      'section',
      { class: 'panel-sec about', 'aria-label': 'How to read the ranking' },
      h('p', { class: 'muted', 'data-note': 'mission-line' }, `${missionName(m)} mission: ${missionLine(m).replace(/^./, (c) => c.toLowerCase())}`),
      h('p', { class: 'muted', 'data-note': 'rule', 'data-verbatim': twinsHere ? null : 'no_twin_reason' }, this.app.ruleText()),
      h('div', { class: 'zone-slot', 'data-slot': 'zone' }),
      // what the markers on the two globes show (off the globes, team lead's ruling)
      h('div', { class: 'markers-slot muted', 'data-slot': 'markers' }),
      h('p', { class: 'muted', 'data-note': 'cell-size' }, this.app.cellSizeText()),
    );
    const funnel = h(
      'details',
      { class: 'panel-sec funnel-sec' },
      h('summary', null, 'How the places are chosen'),
      h(
        'ol',
        { class: 'funnel' },
        plainFunnel(store, m, meaningText(this.app), m.alpha).map((f) => h('li', null, h('strong', null, `${f.name}. `), f.text)),
      ),
      h('p', { class: 'muted' }, `Alpha for this mission: ${num(m.alpha, 2)} (the team's value); it can be changed under "Adjust the weights".`),
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
    // real-value rules: the similarity weights may change too (the twin stays the one chosen at build time)
    const simDefs = store.pairVariables(m.id);
    const sw = this.app.simWeights();
    const simInputs: HTMLInputElement[] = [];
    if (simDefs.length) {
      sliders.append(h('p', { class: 'slider-group' }, 'Similarity weights (the twin of each point stays the same)'));
      simDefs.forEach((d, i) => {
        const id = `sw-${d.variable}`;
        const out = h('output', { for: id, class: 'slider-val' }, num(sw[i], 2));
        const input = h('input', { type: 'range', id, min: '0', max: '1', step: '0.05', value: String(sw[i]), 'aria-describedby': `${id}-team` }) as HTMLInputElement;
        simInputs.push(input);
        input.addEventListener('input', () => {
          out.textContent = num(Number(input.value), 2);
          void this.app.setWeights(this.app.state.weights ?? this.app.teamWeights(m), this.app.state.alpha, simInputs.map((x) => Number(x.value)));
        });
        sliders.append(
          h(
            'div',
            { class: 'slider' },
            h('label', { for: id }, `${d.label} (${roleWord(d.role)})`),
            out,
            input,
            h('p', { class: 'slider-team', id: `${id}-team` }, `Team value ${num(d.weight, 2)}`),
          ),
        );
      });
    }
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
        h('label', { for: 'w-alpha' }, 'Share of similarity in the final score (alpha)'),
        aOut,
        aIn,
        h('p', { class: 'slider-team', id: 'w-alpha-team' }, `Team value ${num(m.alpha, 2)}. Final = alpha x similarity + (1 - alpha) x suitability.`),
      ),
    );
    this.statusEl = h('p', { class: 'recompute-status', role: 'status' });
    details.append(
      h(
        'p',
        { class: 'muted' },
        simDefs.length
          ? 'Weights change the suitability and the similarity score; the hard filters and the lunar twin of each point stay as the team set them.'
          : 'Weights change the suitability only; the hard filters and the similarity stay as the team set them.',
      ),
      sliders,
      button("Reset to team values", () => void this.app.resetWeights(), { kind: 'secondary', id: 'reset-weights' }),
      this.statusEl,
    );

    // ranking
    this.listEl = h('ol', { class: 'rank-list', 'aria-label': `Ranked places for the ${missionName(m)} mission` }) as HTMLOListElement;
    this.moreEl = h('div', { class: 'more' });
    this.query = '';
    const search = h('input', {
      type: 'search',
      id: 'rank-search',
      class: 'search-input',
      placeholder: twinsHere ? 'Find a country, region or lunar feature' : 'Find a country or region',
      autocomplete: 'off',
      spellcheck: 'false',
    }) as HTMLInputElement;
    search.addEventListener('input', () => {
      this.query = search.value.trim().toLowerCase();
      this.limit = PAGE;
      this.renderList();
    });
    search.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') {
        (this.listEl?.querySelector('.rank-row') as HTMLElement | null)?.focus();
        e.preventDefault();
      }
    });
    const searchBox = h(
      'div',
      { class: 'search', role: 'search' },
      h('label', { for: 'rank-search', class: 'search-label sr-only' }, 'Find a ranked place'),
      h('div', { class: 'search-field' }, icon('search'), search),
    );
    if (this.showFor !== m.id) {
      this.show = 'all';
      this.showFor = m.id;
    }
    if (!(twinsHere && pc.unpaired > 0)) this.show = 'all';
    const showBox =
      twinsHere && pc.unpaired > 0
        ? h(
            'fieldset',
            { class: 'show-filter' },
            h('legend', { class: 'sr-only' }, 'Show'),
            (
              [
                ['all', 'All'],
                ['paired', `Paired (${int(pc.paired)})`],
                ['unpaired', `No twin (${int(pc.unpaired)})`],
              ] as const
            ).map(([k, text]) => {
              const input = h('input', { type: 'radio', name: 'show', value: k, id: `show-${k}`, checked: k === this.show }) as HTMLInputElement;
              input.addEventListener('change', () => {
                if (!input.checked) return;
                this.show = k;
                this.limit = PAGE;
                this.renderList();
              });
              return h('label', { class: 'seg' }, input, h('span', null, text));
            }),
          )
        : null;
    const ranking = h(
      'section',
      { class: 'panel-sec ranking', 'aria-labelledby': 'ranking-title' },
      h('h3', { id: 'ranking-title' }, 'Ranked places'),
      counts,
      h(
        'p',
        { class: 'muted pick-hint' },
        `Pick a ${twinsHere ? 'pair' : 'place'} or a marker on the globe to compare it.`,
        h('span', { class: 'sr-only' }, ` Each row: rank, ${twinsHere ? 'Earth place and its lunar twin' : 'place'}, final score. Up and Down move through the list; Enter opens the comparison.`),
      ),
      searchBox,
      showBox,
      this.listEl,
      this.moreEl,
    );

    this.root.replaceChildren(h('div', { class: 'panel-body' }, head, this.topFive(m), details, ranking, about, elim, funnel, levelLegend()));
    this.setRecomputeStatus(this.app.usingCustom() ? 'custom' : 'team', this.app.lastRecomputeMs() ?? undefined);
    this.renderList();
    this.app.updateMoonNote();
  }

  /**
   * Decision 5: the approved limitation of a mission, in full on its card (only where the bundle names
   * the mission). Since revision 5 the solar text is a per-pair template (mission_card false): it is
   * shown filled on every solar pair, never on the card.
   */
  private limitationNote(m: Mission): HTMLElement | null {
    const t = this.app.store.similarity.texts?.['solar_limitation'];
    if (!t || t.mission_card === false || /\{[a-z_]+\}/.test(t.text) || t.mission !== m.id || !this.app.store.hasTwins(m.id)) return null;
    return h('div', { class: 'note-box limitation', 'data-note': 'limitation' }, icon('info'), h('p', null, t.text));
  }

  /** The lunar side of a ranked row in words: "Moon: near <feature>" with twins, else nothing. */
  private twinWords(it: RankItem): string | null {
    const mid = this.app.state.missionId;
    if (!mid || !this.app.store.hasTwins(mid) || it.twinId == null) return null;
    const t = this.app.store.twin(mid, it.twinId);
    if (!t) return null;
    return (t.feature ? `Moon: near ${t.feature.name}` : `Moon: cell at ${latLonText(t.lat, t.lon)}`) + (t.nasa_region?.text ? `, ${t.nasa_region.text}` : '');
  }

  /** The ranking, filtered by the search words (place text and lunar twin name). */
  private visibleItems(): RankItem[] {
    let items = this.app.ranking();
    if (this.show !== 'all') items = items.filter((it) => (this.show === 'paired' ? it.final != null : it.final == null));
    const q = this.query;
    if (!q) return items;
    return items.filter((it) => it.place.toLowerCase().includes(q) || (this.twinWords(it)?.toLowerCase().includes(q) ?? false));
  }

  /** One sentence on why the points after the divider have no twin, from the bundle's counts (missions.json similarity.unpaired_reasons). */
  private unpairedWhy(m: Mission, n: number): string {
    const sim = m.similarity;
    const zone = this.app.zoneName(m) ?? "the mission's lunar zone";
    const parts: string[] = [];
    if (sim.unpaired_by_kind) {
      for (const [kind, cells] of Object.entries(sim.unpaired_by_kind)) if (cells > 0) parts.push(`${int(cells)}: ${noPairKindWords(kind)}`);
    } else {
      const joint = (sim.unpaired_reasons ?? []).filter((r) => r.kind === 'no_joint_match').reduce((s, r) => s + r.earth_cells, 0);
      for (const r of sim.unpaired_reasons ?? []) {
        const d = sim.variables?.find((v) => v.variable === r.variable);
        const label = d?.label.toLowerCase() ?? 'a key value';
        if (r.kind === 'no_zone_cell_within_bound') parts.push(`for ${int(r.earth_cells)}, no cell of ${zone} has ${label} within ${num(r.bound, 2)} ${sentenceUnit(d?.unit ?? '')}`);
        else if (r.kind === 'key_value_missing_on_earth') parts.push(`${int(r.earth_cells)} have no ${label} value on Earth`);
      }
      if (joint) parts.push(`for ${int(joint)}, ${noPairKindWords('no_joint_match')}`);
    }
    return `${int(n)} points pass the filters but have no lunar twin${parts.length ? `: ${parts.join('; ')}` : ''}. They keep their suitability, have no similarity or final score, and are listed by suitability.`;
  }

  /** Keyboard focus on the main action of this screen: the first ranked place. */
  /** A new step: keyboard focus goes to its heading (the five analogs follow it). */
  focusFirst(): void {
    (this.root.querySelector('.panel-title') as HTMLElement | null)?.focus({ preventScroll: true });
  }

  /**
   * The five analogs of the mission under the TEAM's weights (read from the bundle at run time):
   * five large numbered buttons, keys 1 to 5; each opens the comparison of that pair.
   */
  topFiveItems(m: Mission): (RankItem & { pos: number })[] {
    const all = this.app.store.ranked(m.id);
    // revision 7: the bundle names the five (missions.json top5.ids, in order); else ranks 1 to 5
    const ids = m.top5?.ids;
    const picked = ids?.length
      ? ids.map((id) => all.find((p) => p.id === id)).filter((p): p is (typeof all)[number] => !!p)
      : all.filter((p) => p.rank != null && p.rank <= 5).sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
    return picked.slice(0, 5).map((p, i) => ({ ...p, pos: i + 1, place: this.app.placeText(p.id) }));
  }

  /** The bundle's notes for the mission card (texts with "show": mission_card), behind one labelled disclosure. */
  private cardNotes(m: Mission): HTMLElement | null {
    // a note whose text (or first sentence) is already in the five's rule or an earlier note is not repeated
    const seen: string[] = m.top5?.rule ? [m.top5.rule] : [];
    const notes = this.app.store.notesFor('mission_card', m.id).filter((n) => {
      const t = noteText(this.app.store, n.text, m);
      const first = /^.*?\.(?=\s|$)/.exec(t)?.[0] ?? t;
      if (seen.some((x) => x.includes(t) || x.includes(first))) return false;
      seen.push(t);
      return true;
    });
    if (!notes.length) return null;
    return h(
      'details',
      { class: 'card-notes', 'data-notes': 'mission_card' },
      h('summary', null, `Limits of this list (${notes.length})`),
      ...notes.map((n) => h('p', { class: 'bundle-note', 'data-text': n.key }, noteText(this.app.store, n.text, m))),
    );
  }

  /** The heading of the five, as the team worded it (never "best"); the tie count comes from the bundle. */
  private topFiveHeading(m: Mission, n: number, twins: boolean): string {
    const count = n === 5 ? 'Five' : String(n);
    const tie = (m.top5 as { top_tie_n?: number } | undefined)?.top_tie_n;
    if (tie != null && tie > n) return `${count} of the ${int(tie)} sites tied at the top of our model`;
    return `${count} of the highest-scoring ${twins ? 'analogs' : 'places'} in our model`;
  }

  private topFive(m: Mission): HTMLElement {
    const items = this.topFiveItems(m);
    const twins = this.app.missionHasTwins(m);
    const sec = h('section', { class: 'panel-sec top5', 'aria-labelledby': 'top5-title' });
    sec.append(
      h('h3', { id: 'top5-title' }, this.topFiveHeading(m, items.length, twins)),
      h(
        'p',
        { class: 'muted top5-note' },
        this.app.usingCustom()
          ? "These are the team's top five, ranked with the team's weights. Your own weights are in use in the full ranking below, so its order differs."
          : `Chosen with the team's weights. Press a number from 1 to ${items.length} to open one.`,
      ),
    );
    const ol = h('ol', { class: 'top5-list' });
    for (const it of items) {
      const tw = this.twinWords(it);
      const b = h(
        'button',
        { type: 'button', class: 'top5-btn', 'data-id': String(it.id), 'data-rank': String(it.pos), 'data-overall': String(it.rank ?? ''), 'aria-keyshortcuts': String(it.pos) },
        h('kbd', { class: 'key top5-key', 'aria-hidden': 'true' }, String(it.pos)),
        h(
          'span',
          { class: 'top5-text' },
          h('span', { class: 'top5-place' }, h('span', { class: 'sr-only' }, `Analog ${it.pos}: `), it.place),
          tw ? h('span', { class: 'top5-twin' }, tw.replace(/^Moon: /, 'Lunar twin: ')) : null,
          it.rank != null && it.rank !== it.pos ? h('span', { class: 'top5-overall' }, `Ranked ${int(it.rank)} overall`) : null,
        ),
        h('span', { class: 'top5-score' }, h('span', { class: 'top5-score-label' }, 'Final score'), h('span', { class: 'top5-score-val' }, it.final != null ? fixed(it.final, 2) : '–')),
      );
      b.addEventListener('click', () => void this.app.select(it.id));
      ol.append(h('li', null, b));
    }
    sec.append(ol);
    // the rule of the five and the bundle's notes for this list (texts with "show": top5), verbatim
    if (m.top5?.rule) sec.append(h('p', { class: 'muted top5-rule', 'data-text': 'top5.rule' }, m.top5.rule));
    const tie = (m.top5 as { top_tie_n?: number } | undefined)?.top_tie_n;
    if (tie != null && tie > 5 && !(m.top5?.rule ?? '').includes(int(tie))) sec.append(h('p', { class: 'muted', 'data-text': 'top5.top_tie_n' }, `${int(tie)} points are tied at the top score.`));
    for (const n of this.app.store.notesFor('top5', m.id)) sec.append(h('p', { class: 'muted bundle-note', 'data-text': n.key }, noteText(this.app.store, n.text, m)));
    return sec;
  }

  renderList(): void {
    if (!this.listEl || !this.moreEl) return;
    const all = this.app.ranking();
    const items = this.visibleItems();
    const shown = items.slice(0, this.limit);
    const m = this.app.mission();
    const mid = this.app.state.missionId;
    const unpairedTotal = all.filter((it) => it.final == null).length;
    const rows: HTMLElement[] = [];
    let dividerDone = false;
    for (const it of shown) {
      if (it.final == null && !dividerDone && m) {
        dividerDone = true;
        rows.push(
          h(
            'li',
            { class: 'list-divider', 'data-divider': 'no-twin' },
            h('p', { class: 'divider-title' }, icon('info'), h('span', null, `No lunar twin: ${int(unpairedTotal)} ${unpairedTotal === 1 ? 'point' : 'points'}`)),
            h('p', { class: 'divider-why' }, this.unpairedWhy(m, unpairedTotal)),
          ),
        );
      }
      rows.push(h('li', null, this.row(it, mid)));
    }
    this.listEl.replaceChildren(...rows);
    const zeroWeights = this.app.usingCustom() && (this.app.weights().every((w) => w === 0) || (this.app.simWeights().length > 0 && this.app.simWeights().every((w) => w === 0)));
    if (zeroWeights) {
      this.listEl.append(
        h(
          'li',
          { class: 'empty', 'data-empty': 'zero-weights' },
          this.app.weights().every((w) => w === 0)
            ? 'All suitability weights are zero, so no suitability can be computed and no place can be ranked; the filters have not changed. Set at least one weight above 0, or use "Reset to team values".'
            : 'All similarity weights are zero, so no similarity or final score can be computed and no place can be ranked; the filters and the twins have not changed. Set at least one similarity weight above 0, or use "Reset to team values".',
        ),
      );
    } else if (!all.length) {
      this.listEl.append(h('li', { class: 'empty' }, 'No place passes this mission with these settings. Use "Reset to team values" or choose another mission.'));
    } else if (!items.length) {
      this.listEl.append(h('li', { class: 'empty', 'data-empty': 'search' }, this.query ? `No place in this list matches "${this.query}". Clear the search box to see all ${int(all.length)} places.` : 'No place to show with this choice. Choose "All" above to see every place.'));
    }
    this.moreEl.replaceChildren();
    if (items.length > this.limit) {
      this.moreEl.append(
        h('p', { class: 'muted' }, `Showing ${int(shown.length)} of ${int(items.length)} ${this.query ? 'matching ' : ''}places.`),
        button(`Show ${Math.min(PAGE, items.length - this.limit)} more`, () => {
          const first = this.limit;
          this.limit += PAGE;
          this.renderList();
          (this.listEl?.querySelectorAll<HTMLElement>('.rank-row')[first])?.focus();
        }, { kind: 'secondary', id: 'show-more' }),
      );
    } else if (items.length) this.moreEl.append(h('p', { class: 'muted' }, this.query ? `${int(items.length)} places match "${this.query}".` : `All ${int(items.length)} places are listed.`));
  }

  /** The no-twin reason of a row in a few plain words (the full approved sentence is in the panel). */
  private shortReason(np: NoPair): string {
    const d = np.variable;
    const closest = d && np.gap != null ? ` (closest: ${d.label.toLowerCase()} ${num(ceil2(np.gap), 2)} ${sentenceUnit(d.unit)} away, limit ${num(d.bound, 2)} ${sentenceUnit(d.unit)})` : '';
    return `${noPairKindWords(np.kind)}${closest}`;
  }

  /** One row of the list: rank, the Earth place and its lunar twin, the final score; or "No lunar twin" with the reason. */
  private row(it: RankItem, mid: string | null): HTMLButtonElement {
    const twin = this.twinWords(it);
    const coords = latLonText(it.lat, it.lon);
    const paired = it.final != null;
    const noPair = !paired && mid ? this.app.store.noPairAt(mid, it.passPos) : null;
    const reason = noPair ? this.shortReason(noPair) : '';
    const where = paired ? `${coords}${twin ? ` · ${twin}` : ''}` : coords;
    const b = h(
      'button',
      { type: 'button', class: `rank-row${paired ? '' : ' is-unpaired'}`, 'data-id': String(it.id), 'data-paired': String(paired) },
      h('span', { class: 'rank-n', 'aria-hidden': paired ? null : 'true' }, paired && it.rank != null ? int(it.rank) : ''),
      h(
        'span',
        { class: 'rank-place' },
        h('span', { class: 'rank-name' }, it.place),
        h('span', { class: 'rank-where' }, where),
        paired ? null : h('span', { class: 'rank-notwin', 'data-note': 'no-twin' }, h('strong', null, 'No lunar twin'), reason ? `: ${reason}` : ''),
        it.missingTemp ? tempMark(this.app) : null,
      ),
      paired
        ? h('span', { class: 'rank-score' }, h('span', { class: 'rank-final' }, fixed(it.final, 2)), h('span', { class: 'rank-final-k' }, 'final'))
        : h('span', { class: 'rank-score is-suit' }, h('span', { class: 'rank-final' }, fixed(it.suitability, 2)), h('span', { class: 'rank-final-k' }, 'suitability')),
    );
    b.setAttribute(
      'aria-label',
      paired
        ? `Rank ${int(it.rank ?? 0)}: ${it.place}, ${where}, final score ${fixed(it.final, 2)} of 100${it.missingTemp ? `; ${this.app.store.text('missing_temperature_mark') ?? ''}` : ''}`
        : `${it.place}, ${coords}, no lunar twin${reason ? `: ${reason}` : ''}; suitability ${fixed(it.suitability, 2)} of 100`,
    );
    if (it.missingTemp) b.dataset.missingTemp = 'true';
    b.addEventListener('click', () => (paired ? globesApi.markers.activate('earth', it.id) : void this.app.select(it.id)));
    b.addEventListener('focus', () => globesApi.markers.setHighlighted('earth', paired ? it.id : null));
    b.addEventListener('blur', () => globesApi.markers.setHighlighted('earth', null));
    b.addEventListener('keydown', (e) => this.rowKey(e, b));
    return b;
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
    const items = this.visibleItems();
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
