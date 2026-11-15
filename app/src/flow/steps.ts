// The step indicator: choose a mission, pick a point, compare the pair, start the mission.
// The current step is marked by its number in a filled disc, bold text and "(current step)" for
// screen readers; done steps carry a tick; reachable steps are buttons (go back or continue).

import { h, icon } from './dom';

export type Step = 'choose' | 'pick' | 'compare';

interface StepsModel {
  step: Step;
  withVideo: boolean;
  missionName: string | null;
  canPick: boolean;
  canCompare: boolean;
  go: (s: Step | 'video') => void;
}

export function renderSteps(nav: HTMLElement, m: StepsModel): void {
  const video = document.body.dataset.video === 'open';
  const items: { key: Step | 'video'; label: string; reachable: boolean }[] = [
    { key: 'choose', label: 'Choose a mission', reachable: true },
    { key: 'pick', label: 'Pick a point', reachable: m.canPick },
    { key: 'compare', label: 'Compare the pair', reachable: m.canCompare },
  ];
  if (m.withVideo) items.push({ key: 'video', label: 'Start the mission', reachable: m.canCompare && m.step === 'compare' });
  const current = video ? 'video' : m.step;
  const ci = items.findIndex((i) => i.key === current);
  const ol = h('ol', { class: 'steps-list' });
  items.forEach((it, i) => {
    const state = i === ci ? 'current' : i < ci ? 'done' : 'todo';
    const marker = h('span', { class: 'step-num', 'aria-hidden': 'true' }, state === 'done' ? icon('check') : String(i + 1));
    const text = h('span', { class: 'step-label' }, it.label);
    const sr = h('span', { class: 'sr-only' }, state === 'current' ? ' (current step)' : state === 'done' ? ' (done)' : '');
    let el: HTMLElement;
    if (state !== 'current' && it.reachable) {
      el = h('button', { type: 'button', class: 'step-btn' }, marker, text, sr);
      el.addEventListener('click', () => m.go(it.key));
    } else el = h('span', { class: 'step-btn', 'aria-current': state === 'current' ? 'step' : null }, marker, text, sr);
    ol.append(h('li', { class: `step is-${state}` }, el));
  });
  const where = h('p', { class: 'steps-where' }, `Step ${ci + 1} of ${items.length}`, m.missionName ? h('span', { class: 'steps-mission' }, ` · ${m.missionName} mission`) : null);
  nav.replaceChildren(where, ol);
}
