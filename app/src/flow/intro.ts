// First screen (checklist stage 01): one sentence of purpose, who it is for, and the mission
// selector as the main action: exactly the missions the bundle offers, in its order.

import type { FlowApp } from './app';
import { AUDIENCE, missionLine, purposeText, missionName } from './copy';
import { button, h, icon } from './dom';

export function renderIntro(root: HTMLElement, app: FlowApp): void {
  const hadFocus = root.contains(document.activeElement) ? (document.activeElement as HTMLElement).dataset.mission : undefined;
  const card = h('div', { class: 'intro-card' });
  const logo = h('img', {
    class: 'intro-logo',
    src: './static/brand/stars-beside-you-logo-192.png',
    srcset: './static/brand/stars-beside-you-logo-192.png 192w, ./static/brand/stars-beside-you-logo-512.png 512w',
    sizes: '(max-width: 820px) 72px, 112px',
    width: '112',
    height: '112',
    alt: '',
  });
  card.append(
    h(
      'div',
      { class: 'intro-head' },
      logo,
      h(
        'div',
        { class: 'intro-head-text' },
        h('h2', { class: 'intro-title', id: 'intro-title', tabindex: '-1' }, purposeText(app.hasData() && app.store.hasTwins())),
        h('p', { class: 'intro-audience' }, AUDIENCE),
      ),
    ),
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
  const group = h('div', { class: 'choices', role: 'group', 'aria-label': 'Choose a mission' });
  void legendId;
  if (!ready) {
    card.append(h('p', { class: 'loading-line', role: 'status' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading the mission data'));
  } else {
    const cur = app.state.missionId;
    app.store.offeredMissions().forEach((m, i) => {
      const loading = app.loading() === m.id;
      const b = h(
        'button',
        { type: 'button', class: 'choice', 'data-mission': m.id, 'aria-pressed': cur === m.id ? 'true' : 'false', 'aria-busy': loading ? 'true' : null, 'aria-keyshortcuts': String(i + 1) },
        h('span', { class: 'choice-key' }, h('kbd', { class: 'key', title: `Key ${i + 1}` }, String(i + 1))),
        h('span', { class: 'choice-name' }, missionName(m), icon('next')),
        h('span', { class: 'choice-line' }, missionLine(m)),
        // only a loading sign here; the counts and threshold status are in the mission panel and "Data, limits and credits"
        loading ? h('span', { class: 'choice-meta' }, h('span', { class: 'spinner', 'aria-hidden': 'true' }), 'Loading') : null,
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
    });
    card.append(group);

    // the method's small print, folded (the full account is in "Data, limits and credits")
    card.append(
      h(
        'details',
        { class: 'intro-more' },
        h('summary', null, 'About the data'),
        h(
          'p',
          { class: 'intro-foot' },
          `${app.cellSizeText()} `,
          h('span', { 'data-verbatim': app.hasData() && !app.store.hasTwins() ? 'no_twin_reason' : null }, app.ruleText()),
        ),
      ),
    );
  }
  root.replaceChildren(card);
  if (hadFocus) (root.querySelector(`[data-mission="${hadFocus}"]`) as HTMLElement | null)?.focus();
}
