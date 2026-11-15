// Small DOM and formatting helpers shared by every flow component (one implementation for every
// repeated element: buttons, tags, rows, icons, level words).

import type { Gate, Level } from '../data/types.ts';
import { classWord } from './copy';

type Child = Node | string | number | null | undefined | false | Child[];
type Attrs = Record<string, string | number | boolean | null | undefined | EventListener>;

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Attrs | null = null, ...children: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v as EventListener);
      else if (k === 'class') el.className = String(v);
      else if (v === true) el.setAttribute(k, '');
      else el.setAttribute(k, String(v));
    }
  }
  append(el, children);
  return el;
}

export function append(el: Element, children: Child[]): void {
  for (const c of children) {
    if (c == null || c === false) continue;
    if (Array.isArray(c)) append(el, c);
    else el.append(c instanceof Node ? c : String(c));
  }
}

const ICONS: Record<string, string> = {
  check: 'M4 12.5l5 5L20 6.5',
  cross: 'M6 6l12 12M18 6L6 18',
  close: 'M6 6l12 12M18 6L6 18',
  back: 'M15 5l-7 7 7 7',
  next: 'M9 5l7 7-7 7',
  play: 'M8 5.5v13l11-6.5z',
  info: 'M12 10.5v6M12 7.2v.1',
  ext: 'M14 5h5v5M19 5l-8 8M10 6H6v12h12v-4',
  search: 'M10.5 4a6.5 6.5 0 1 1 0 13a6.5 6.5 0 1 1 0-13zM15.5 15.5L20 20',
};

/** A stroked 24 px icon (decorative unless `label` is given). */
export function icon(name: keyof typeof ICONS | string, label?: string): SVGSVGElement {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('class', `icon icon-${name}`);
  if (label) {
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', label);
  } else svg.setAttribute('aria-hidden', 'true');
  if (name === 'info') {
    const c = document.createElementNS(ns, 'circle');
    c.setAttribute('cx', '12');
    c.setAttribute('cy', '12');
    c.setAttribute('r', '9');
    svg.append(c);
  }
  const p = document.createElementNS(ns, 'path');
  p.setAttribute('d', ICONS[name] ?? '');
  if (name === 'play') p.setAttribute('class', 'fill');
  svg.append(p);
  return svg;
}

/** The one button implementation. kind: 'primary' (one per view), 'secondary', 'quiet'. */
export function button(
  text: string | Node[],
  onClick: (e: MouseEvent) => void,
  opts: { kind?: 'primary' | 'secondary' | 'quiet'; icon?: string; iconAfter?: string; label?: string; id?: string; cls?: string } = {},
): HTMLButtonElement {
  const b = h('button', {
    type: 'button',
    class: `btn btn-${opts.kind ?? 'secondary'}${opts.cls ? ' ' + opts.cls : ''}`,
    'aria-label': opts.label,
    id: opts.id,
  });
  if (opts.icon) b.append(icon(opts.icon));
  if (typeof text === 'string') b.append(h('span', null, text));
  else append(b, text);
  if (opts.iconAfter) b.append(icon(opts.iconAfter));
  b.addEventListener('click', onClick);
  return b;
}

/** Pass / fail with an icon and the word (never colour alone). */
export function verdict(pass: boolean, words: [string, string] = ['Pass', 'Fail']): HTMLElement {
  return h('span', { class: `verdict ${pass ? 'is-pass' : 'is-fail'}` }, icon(pass ? 'check' : 'cross'), h('span', null, pass ? words[0] : words[1]));
}

export const LEVEL_WORDS: Record<string, string> = {
  MEASURED: 'measured',
  DERIVED: 'derived',
  MODELLED: 'modelled',
  UNDOCUMENTED: 'undocumented',
  NO_DATA: 'no data',
};

/** The data level as a word in a small outlined tag. */
export function levelTag(level: Level | null | undefined): HTMLElement {
  const word = level ? (LEVEL_WORDS[level] ?? level.toLowerCase()) : 'no data';
  return h('span', { class: `level level-${(level ?? 'NO_DATA').toLowerCase()}` }, word);
}

export function tag(text: string, cls = ''): HTMLElement {
  return h('span', { class: `tag ${cls}` }, text);
}

// ---------- numbers ----------

const nf = new Intl.NumberFormat('en-GB');
export const int = (n: number): string => nf.format(Math.round(n));

/** A number with up to `d` decimals, trailing zeros dropped; "no data" for null. */
export function num(v: number | null | undefined, d = 2): string {
  if (v == null || !Number.isFinite(v)) return 'no data';
  const r = Number(v.toFixed(d));
  return new Intl.NumberFormat('en-GB', { maximumFractionDigits: d, minimumFractionDigits: 0 }).format(Object.is(r, -0) ? 0 : r);
}

/** Fixed decimals (scores). */
export function fixed(v: number | null | undefined, d = 2): string {
  if (v == null || !Number.isFinite(v)) return 'no data';
  return new Intl.NumberFormat('en-GB', { maximumFractionDigits: d, minimumFractionDigits: d }).format(v);
}

const UNIT_TEXT: Record<string, string> = {
  m: 'm',
  deg: '°',
  K: 'K',
  degC: '°C',
  'kWh/m2/day': 'kWh/m²/day',
  'fraction 0-1': '',
  category: '',
  'mm/day': 'mm/day',
  'm/s': 'm/s',
  km: 'km',
};

/** Value with its unit for display (categories are shown by class name). Float32 values are rounded sensibly. */
export function valueText(v: number | string | null | undefined, unit: string): string {
  if (v == null || (typeof v === 'number' && !Number.isFinite(v))) return 'no data';
  if (typeof v === 'string') return classWord(v);
  if (unit === 'percentile points') return `${num(v, 1)} percentile points`;
  const u = UNIT_TEXT[unit] ?? unit;
  const abs = Math.abs(v);
  const d = unit === 'fraction 0-1' ? 3 : abs >= 100 ? 1 : abs >= 10 ? 2 : 3;
  const s = num(v, d);
  if (!u) return s;
  return u === '°' || u === '°C' ? `${s}${u}` : `${s} ${u}`;
}

/**
 * A gate's limit in words, from gates[].min / max / allow / exclude (e.g. "at least 2.5 kWh/m²/day",
 * "0.5 to 15°", "not water"); the engine's interval text (gates[].limit) stays available as the exact form.
 */
export function limitWords(g: Gate, unit: string): string {
  const v = (x: number) => valueText(x, unit);
  if (g.min != null && g.max != null) {
    const u = UNIT_TEXT[unit] ?? unit;
    return u === '' ? `${num(g.min, 3)} to ${num(g.max, 3)}` : `${v(g.min).replace(/\s?[^\d.,-]+$/, '')} to ${v(g.max)}`;
  }
  if (g.min != null) return `at least ${v(g.min)}`;
  if (g.max != null) return `at most ${v(g.max)}`;
  if (g.exclude?.length) return `not ${g.exclude.map(classWord).join(' or ')}`;
  if (g.allow?.length) return `one of ${g.allow.map(classWord).join(', ')}`;
  return g.limit;
}

export function latLonText(lat: number, lon: number): string {
  const la = `${num(Math.abs(lat), 1)}° ${lat >= 0 ? 'N' : 'S'}`;
  const lo = `${num(Math.abs(lon), 1)}° ${lon >= 0 ? 'E' : 'W'}`;
  return `${la}, ${lo}`;
}

export function capitalise(s: string): string {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

/** Visually hidden text for screen readers. */
export function srOnly(text: string): HTMLElement {
  return h('span', { class: 'sr-only' }, text);
}
