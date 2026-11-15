// Compact legend of the data levels, shared by both panels (one implementation).

import { h, levelTag } from './dom';

const SHORT: [string, string][] = [
  ['MEASURED', 'from a named measured product'],
  ['DERIVED', 'a stated formula on measured values'],
  ['MODELLED', 'a model or a value set by definition'],
  ['NO_DATA', 'no value for this cell'],
];

export function levelLegend(): HTMLElement {
  return h(
    'section',
    { class: 'panel-sec legend', 'aria-label': 'Data levels' },
    h('h3', null, 'Data levels'),
    h('ul', { class: 'legend-list' }, SHORT.map(([k, t]) => h('li', null, levelTag(k as never), h('span', null, t)))),
  );
}
