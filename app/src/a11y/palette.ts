// Every colour of the interface and of the globe overlays behind one set of named tokens, with two
// palettes. "standard" is the product's own (warm white and sodium amber on black). "cvd" is the
// colour-blind-safe palette built from the Okabe-Ito colours (Okabe M., Ito K., "Color Universal
// Design (CUD): how to make figures and presentations that are friendly to colorblind people",
// 2002/2008, https://jfly.uni-koeln.de/color/), the values as published there.
// CSS reads the tokens as custom properties on <html>; the globe modules read overlayColours().

export type PaletteName = 'standard' | 'cvd';
type RGB = [number, number, number];

export interface Palette {
  name: PaletteName;
  /** CSS custom properties (the interface). */
  css: Record<string, string>;
  /** Marker score ramp, low to high (r, g, b, alpha 0..1). */
  markerLow: [number, number, number, number];
  markerHigh: [number, number, number, number];
  /** Ring around the selected marker and the selected label. */
  ring: RGB;
  /** Light of the beam between the two globes. */
  beam: RGB;
  /** Zone outline and fill on the Moon. */
  zoneLine: RGB;
  zoneFillAlpha: number;
  /** Outline of a focused cell. */
  cellLine: RGB;
}

/** Okabe-Ito colours (jfly.uni-koeln.de/color, "Color Universal Design"). */
export const OKABE_ITO = {
  black: '#000000',
  orange: '#E69F00',
  skyBlue: '#56B4E9',
  bluishGreen: '#009E73',
  yellow: '#F0E442',
  blue: '#0072B2',
  vermillion: '#D55E00',
  reddishPurple: '#CC79A7',
} as const;

const hex = (h: string): RGB => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const rgba = (c: RGB, a: number) => `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${a})`;

export const PALETTES: Record<PaletteName, Palette> = {
  standard: {
    name: 'standard',
    // "Mission Control": the team patch's navy, gold thread and the cyan of the shuttle's plume
    css: {
      '--text': '#e8ecf4',
      '--text-dim': '#9fb0c8',
      '--sodium': '#e9b949',
      '--accent-hover': '#f2cb6b',
      '--on-accent': '#050b1a',
      '--danger': '#e59a8c',
      '--danger-wash': 'rgba(229, 154, 140, 0.08)',
      '--edge': 'rgba(95, 212, 244, 0.2)',
      '--edge-strong': 'rgba(95, 212, 244, 0.38)',
      '--zone-line': 'rgba(240, 226, 196, 0.95)',
      '--zone-fill': 'rgba(232, 214, 176, 0.16)',
      '--switch-on': '#e9b949',
      '--focus': '#5fd4f4',
      '--hud-cyan': '#5fd4f4',
      '--hud-gold': '#e9b949',
      '--ramp-low': 'rgb(150, 143, 131)',
      '--ramp-high': 'rgb(255, 247, 230)',
    },
    markerLow: [150, 143, 131, 0.38],
    markerHigh: [255, 247, 230, 0.98],
    ring: [255, 250, 240],
    beam: [95, 212, 244],
    zoneLine: [240, 226, 196],
    zoneFillAlpha: 0.1,
    cellLine: [244, 240, 230],
  },
  cvd: {
    name: 'cvd',
    css: {
      '--text': '#f2f2f2',
      '--text-dim': '#bdbdbd',
      '--sodium': OKABE_ITO.skyBlue,
      '--accent-hover': '#7cc5ee',
      '--on-accent': '#000000',
      '--danger': OKABE_ITO.orange,
      '--danger-wash': rgba(hex(OKABE_ITO.orange), 0.1),
      '--edge': 'rgba(220, 220, 220, 0.2)',
      '--edge-strong': 'rgba(220, 220, 220, 0.4)',
      '--zone-line': OKABE_ITO.orange,
      '--zone-fill': rgba(hex(OKABE_ITO.orange), 0.16),
      '--switch-on': OKABE_ITO.skyBlue,
      '--focus': OKABE_ITO.yellow,
      // the HUD's two accents in this palette: gold (selection, final score, main action) becomes the
      // sky blue accent, the cyan line (hairlines, beam, state, focus) becomes the yellow focus colour
      '--hud-cyan': OKABE_ITO.yellow,
      '--hud-gold': OKABE_ITO.skyBlue,
      '--ramp-low': OKABE_ITO.blue,
      '--ramp-high': OKABE_ITO.yellow,
    },
    markerLow: [...hex(OKABE_ITO.blue), 0.55],
    markerHigh: [...hex(OKABE_ITO.yellow), 0.98],
    ring: hex(OKABE_ITO.skyBlue),
    beam: hex(OKABE_ITO.skyBlue),
    zoneLine: hex(OKABE_ITO.orange),
    zoneFillAlpha: 0.12,
    cellLine: hex(OKABE_ITO.skyBlue),
  },
};

let current: Palette = PALETTES.standard;
const listeners = new Set<(p: Palette) => void>();

export function palette(): Palette {
  return current;
}

export function onPalette(fn: (p: Palette) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function applyPalette(name: PaletteName): void {
  current = PALETTES[name];
  const root = document.documentElement;
  root.dataset.palette = name;
  for (const [k, v] of Object.entries(current.css)) root.style.setProperty(k, v);
  for (const fn of listeners) {
    try {
      fn(current);
    } catch {
      /* an overlay not ready yet redraws on its next update */
    }
  }
}
