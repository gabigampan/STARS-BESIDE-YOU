// First screen (checklist stage 01): one sentence of purpose, who it is for, and the mission
// selector as the main action: exactly the missions the bundle offers, in its order.

import type { FlowApp } from './app';
import { AUDIENCE, PURPOSE, missionLine, missionName, statusWords } from './copy';
import { button, h, icon, int } from './dom';

export function renderIntro(root: HTMLElement, app: FlowApp): void {
  const hadFocus = root.contains(document.activeElement) ? (document.activeElement as HTMLElement).dataset.mission : undefined;
  const card = h('div', { class: 'intro-card' });
  card.append(
    h('h2', { class: 'intro-title', id: 'intro-title', tabindex: '-1' }, PURPOSE),
    h('p', { class: 'intro-audience' }, AUDIENCE),
  );
  const err = app.error();
  if (err) {
    card.append(
      h('div', { class: 'alert', role: 'alert' }, h('p', null, err), button('Reload the page', () => window.location.reload(), { kind: 'primary' })),
    );
    root.replaceChildren(card);
    return;
  }
  const ready = app.hasData();
  const legendId = 'choose-legend';
  const group = h('div', { class: 'choices', role: 'group', 'aria-labelledby': legendId });
  card.append(h('p', { class: 'intro-cta', id: legendId }, 'Choose a mission to start'));
  if (!ready) {
    card.append(h('p', { class: 'loading-line', role: 'status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading the mission data'));
  } else {
    const cur = app.state.missionId;
    for (const m of app.store.offeredMissions()) {
      const loading = app.loading() === m.id;
      const b = h(
        'button',
        { type: 'button', class: 'choice', 'data-mission': m.id, 'aria-pressed': cur === m.id ? 'true' : 'false', 'aria-busy': loading ? 'true' : null },
        h('span', { class: 'choice-name' }, missionName(m), icon('next')),
        h('span', { class: 'choice-line' }, missionLine(m)),
        h('span', { class: 'choice-meta' }, loading ? h('span', { class: 'spinner', 'aria-hidden': 'true' }) : null, loading ? 'Loading' : `${int(m.pass_counts.EARTH)} places pass · ${statusWords(m).toLowerCase()}`),
      );
      b.addEventListener('click', () => void app.chooseMission(m.id));
      b.addEventListener('keydown', (e) => {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowDown' && e.key !== 'ArrowLeft' && e.key !== 'ArrowUp') return;
        const all = Array.from(group.querySelectorAll<HTMLButtonElement>('.choice'));
        const i = all.indexOf(b);
        const n = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? (i + 1) % all.length : (i - 1 + all.length) % all.length;
        all[n].focus();
        e.preventDefault();
      });
      group.append(b);
    }
    card.append(group);
    card.append(
      h(
        'p',
        { class: 'intro-foot' },
        `Each point is a 1° cell: about ${int(app.store.manifest.grid.bodies.EARTH.cell_ns_km)} km across on Earth and ${int(app.store.manifest.grid.bodies.MOON.cell_ns_km)} km on the Moon. `,
        app.ruleText(),
      ),
    );
  }
  root.replaceChildren(card);
  if (hadFocus) (root.querySelector(`[data-mission="${hadFocus}"]`) as HTMLElement | null)?.focus();
}
