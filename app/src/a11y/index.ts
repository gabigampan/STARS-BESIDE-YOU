// The accessibility layer: the two header switches, the audio guide, the palette and the keys.
// One instance for the page (window.starsA11y for tests and the console).

import { AudioGuide } from './audio';
import { createSwitch, type SwitchHandle } from './switches';
import { PREF_AUDIO, PREF_PALETTE } from './prefs';
import { applyPalette } from './palette';

export class A11y {
  readonly guide: AudioGuide;
  readonly audioSwitch: SwitchHandle;
  readonly paletteSwitch: SwitchHandle;

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
    slot.append(this.audioSwitch.el, this.paletteSwitch.el);
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
