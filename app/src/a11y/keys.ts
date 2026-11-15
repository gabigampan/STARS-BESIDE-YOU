// Keyboard guide (one handler for the page):
//   1, 2, 3  start screen: choose a mission
//   1 to 5   mission screen: open one of the five best analogs
//   Escape   back one step (a pair to its mission, a mission to the start); an open dialog closes first
//   R        repeat the audio guide's current track
//   ?        the list of shortcuts (also the "Keys" button in the header)
//   Home     reset both globe views (src/ui/shell.ts)
// Shortcuts never fire with a modifier key, inside a text field, a slider, a select or a radio
// group (controls that use those keys themselves), or while a dialog is open (except Escape, which
// the dialog itself handles).

import type { FlowApp } from '../flow/app';
import type { A11y } from './index';

export const KEY_MAP: { keys: string[]; where: string; what: string }[] = [
  { keys: ['1', '2', '3'], where: 'Start screen', what: 'Choose the Rover, Solar panels or Lunar base mission' },
  { keys: ['1', '2', '3', '4', '5'], where: 'Mission screen', what: 'Open one of the five best analogs' },
  { keys: ['Esc'], where: 'Anywhere', what: 'Go back one step (a dialog closes first)' },
  { keys: ['R'], where: 'Anywhere', what: 'Repeat the audio guide (or start it after a reload)' },
  { keys: ['?'], where: 'Anywhere', what: 'Show this list of shortcuts' },
  { keys: ['Home'], where: 'Anywhere', what: 'Reset both globe views' },
  { keys: ['Tab'], where: 'Anywhere', what: 'Move between controls; Space or Enter uses the focused control' },
  { keys: ['↑', '↓'], where: 'Ranked list', what: 'Move through the list; Enter opens the comparison' },
];

function busyTarget(t: EventTarget | null): boolean {
  const el = t instanceof HTMLElement ? t : null;
  if (!el) return false;
  if (el.isContentEditable) return true;
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) return true;
  return !!el.closest('[role="slider"], [role="radiogroup"], [role="textbox"], [role="combobox"], [role="spinbutton"]');
}

export function setupKeys(app: FlowApp, a11y: A11y): void {
  const dialog = document.getElementById('keys-dialog') as HTMLDialogElement;
  const body = document.getElementById('keys-body') as HTMLElement;
  const openBtn = document.getElementById('keys-button') as HTMLButtonElement;
  const close = document.getElementById('keys-close') as HTMLButtonElement;
  const table = document.createElement('table');
  table.className = 'keys-table';
  table.innerHTML = '<caption class="sr-only">Keyboard shortcuts</caption><thead><tr><th scope="col">Key</th><th scope="col">Where</th><th scope="col">What it does</th></tr></thead>';
  const tb = document.createElement('tbody');
  for (const k of KEY_MAP) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    k.keys.forEach((key, i) => {
      if (i) td.append(' ');
      const kbd = document.createElement('kbd');
      kbd.className = 'key';
      kbd.textContent = key;
      td.append(kbd);
    });
    const w = document.createElement('td');
    w.textContent = k.where;
    const d = document.createElement('td');
    d.textContent = k.what;
    tr.append(td, w, d);
    tb.append(tr);
  }
  table.append(tb);
  const note = document.createElement('p');
  note.className = 'muted';
  note.textContent =
    'Shortcuts do not work while you type in a field or use a slider, and never with Ctrl, Alt or Cmd held down. The audio guide is off until you turn it on with the switch in the header; while it is off nothing sounds, and the text of each step is always shown under the steps.';
  body.replaceChildren(table, note);
  const open = () => {
    if (!dialog.open) dialog.showModal();
    close.focus();
  };
  openBtn.addEventListener('click', open);
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => openBtn.focus());

  window.addEventListener('keydown', (e) => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    if (busyTarget(e.target)) return;
    if (document.querySelector('dialog[open]')) return; // the dialog has the keyboard (Escape closes it)
    if (document.body.classList.contains('view-open') && e.key === 'Escape') return; // the View menu closes first
    const step = app.state.step;
    const key = e.key;
    if (key === '?') {
      open();
      e.preventDefault();
      return;
    }
    if (key === 'r' || key === 'R') {
      a11y.guide.repeat();
      e.preventDefault();
      return;
    }
    if (key === 'Escape') {
      if (step === 'compare') void app.backToRanking();
      else if (step === 'pick') void app.changeMission();
      else return;
      e.preventDefault();
      return;
    }
    if (!/^[1-9]$/.test(key)) return;
    const n = Number(key);
    if (step === 'choose') {
      if (!app.hasData() || app.loading()) return;
      const m = app.store.offeredMissions()[n - 1];
      if (!m) return;
      void app.chooseMission(m.id);
      e.preventDefault();
    } else if (step === 'pick') {
      const m = app.mission();
      if (!m) return;
      const it = app.missionPanel.topFiveItems(m).find((x) => x.rank === n);
      if (!it) return;
      void app.select(it.id);
      e.preventDefault();
    }
  });
}
