// The accessibility layer: the two header switches, the audio guide, the palette and the keys.
// One instance for the page (window.starsA11y for tests and the console).

import { AudioGuide } from './audio';
import { createSwitch, type SwitchHandle } from './switches';
import { PREF_AUDIO, PREF_PALETTE } from './prefs';
import { applyPalette, PALETTES } from './palette';

export class A11y {
  readonly guide: AudioGuide;
  readonly audioSwitch: SwitchHandle;
  readonly paletteSwitch: SwitchHandle;
  readonly namesSwitch: SwitchHandle;
  private namesHandler: ((on: boolean) => void) | null = null;
  /** Both palettes (for the colour checks of the tests). */
  readonly palettes = PALETTES;

  constructor() {
    this.guide = new AudioGuide(document.getElementById('guide-caption') as HTMLElement);
    const slot = document.getElementById('switches') as HTMLElement;
    this.audioSwitch = createSwitch({
      id: 'switch-audio',
      label: 'Audio guide',
      pref: PREF_AUDIO,
      onChange: (on) => {
        this.guide.setEnabled(on);
        announce(on ? 'Audio guide on.' : 'Audio guide off: nothing will sound.');
      },
    });
    this.paletteSwitch = createSwitch({
      id: 'switch-palette',
      label: 'Colour-blind mode',
      pref: PREF_PALETTE,
      onChange: (on) => {
        applyPalette(on ? 'cvd' : 'standard');
        announce(on ? 'Colour-blind mode on.' : 'Colour-blind mode off.');
      },
    });
    applyPalette(this.paletteSwitch.get() ? 'cvd' : 'standard');
    // the texts of the audio guide stay reachable for people who cannot hear it: in "Data, limits and credits"
    void this.guide.ready.then(() => {
      const body = document.getElementById('credits-body');
      const list = this.guide.allTranscripts();
      if (!body || !list.length) return;
      const d = document.createElement('details');
      d.className = 'guide-texts';
      const sum = document.createElement('summary');
      sum.textContent = `Texts of the audio guide (${list.length})`;
      d.append(sum);
      for (const t of list) {
        const p = document.createElement('p');
        p.dataset.file = t.file;
        p.textContent = t.text;
        d.append(p);
      }
      body.append(d);
    });
    this.namesSwitch = createSwitch({
      id: 'switch-names',
      label: 'Place names',
      pref: 'starsBesideYou.placeNames',
      defaultOn: true,
      onChange: (on) => this.namesHandler?.(on),
    });
    slot.append(this.namesSwitch.el, this.audioSwitch.el, this.paletteSwitch.el);
  }

  /** The globes' place names follow the "Place names" switch. */
  setPlaceNamesHandler(fn: (on: boolean) => void): void {
    this.namesHandler = fn;
    fn(this.namesSwitch.get());
  }
}

/** The single live region of the page (#flow-status): one short sentence per step. */
export function announce(text: string): void {
  const el = document.getElementById('flow-status');
  if (!el) return;
  el.textContent = '';
  window.setTimeout(() => (el.textContent = text), 30);
}

let instance: A11y | null = null;
export function a11y(): A11y {
  if (!instance) instance = new A11y();
  return instance;
}
