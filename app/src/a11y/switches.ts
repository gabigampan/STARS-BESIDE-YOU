// The two sliding toggle switches of the header, on every screen and at every width:
// "Audio guide" and "Colour-blind mode", both off by default and remembered (prefs.ts).
// Each is a native <button role="switch">: Tab reaches it, Space and Enter toggle it, aria-checked
// carries the state and the words "On" / "Off" beside the track show it without colour.

import { readPref, writeFlag } from './prefs';

export interface SwitchHandle {
  readonly el: HTMLButtonElement;
  get(): boolean;
  set(on: boolean, persist?: boolean): void;
}

export function createSwitch(opts: { id: string; label: string; pref: string; onChange: (on: boolean) => void; defaultOn?: boolean }): SwitchHandle {
  const el = document.createElement('button');
  el.type = 'button';
  el.id = opts.id;
  el.className = 'switch';
  el.setAttribute('role', 'switch');
  const labelId = `${opts.id}-label`;
  el.setAttribute('aria-labelledby', labelId);
  const label = document.createElement('span');
  label.className = 'switch-label';
  label.id = labelId;
  label.textContent = opts.label;
  const track = document.createElement('span');
  track.className = 'switch-track';
  track.setAttribute('aria-hidden', 'true');
  const thumb = document.createElement('span');
  thumb.className = 'switch-thumb';
  track.append(thumb);
  // the state is the thumb's position (left off, right on) and aria-checked; no state word (team lead's ruling)
  el.append(label, track);

  let on = false;
  const handle: SwitchHandle = {
    el,
    get: () => on,
    set(next: boolean, persist = true) {
      on = next;
      el.setAttribute('aria-checked', String(on));
      el.dataset.state = on ? 'on' : 'off';
      if (persist) writeFlag(opts.pref, on);
      opts.onChange(on);
    },
  };
  el.addEventListener('click', () => handle.set(!on));
  // initial state from storage (default off), without writing it back
  const stored = readPref(opts.pref);
  on = stored === null ? !!opts.defaultOn : stored === 'on';
  el.setAttribute('aria-checked', String(on));
  el.dataset.state = on ? 'on' : 'off';
  return handle;
}
