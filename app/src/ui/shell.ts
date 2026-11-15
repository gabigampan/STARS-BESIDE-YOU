// Header controls, credits dialog and loading screen (the sunlight control is in modules/sunlight.ts).

import { renderCredits, type CreditEntry } from './credits';
import type { Body, ImageryStatus } from '../scene/globes';

function $(id: string): HTMLElement {
  const el = document.getElementById(id);
  if (!el) throw new Error(`#${id} missing from index.html`);
  return el;
}

export function setupCredits(extra: CreditEntry[] = []): void {
  const dialog = $('credits-dialog') as HTMLDialogElement;
  const open = $('credits-button');
  const close = $('credits-close');
  renderCredits($('credits-body'), extra);
  open.addEventListener('click', () => {
    dialog.showModal();
    close.focus();
  });
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (e) => {
    // A click on the backdrop (outside the dialog box) closes it.
    const r = dialog.getBoundingClientRect();
    const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
    if (!inside) dialog.close();
  });
  dialog.addEventListener('close', () => open.focus());
}

export function setupLabelsToggle(onChange: (visible: boolean) => void): void {
  const btn = $('labels-toggle');
  btn.addEventListener('click', () => {
    const next = btn.getAttribute('aria-pressed') !== 'true';
    btn.setAttribute('aria-pressed', String(next));
    // the state in words as well as by the box (never by colour alone)
    const t = btn.querySelector('.toggle-text');
    if (t) t.textContent = `Place names: ${next ? 'on' : 'off'}`;
    onChange(next);
  });
}

/** Narrow screens: the Sunlight and Place names controls sit behind a "View" button. */
export function setupViewMenu(): void {
  const btn = document.getElementById('view-toggle');
  const tools = document.getElementById('view-tools');
  if (!btn || !tools) return;
  const set = (open: boolean) => {
    btn.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('view-open', open);
  };
  btn.addEventListener('click', () => set(btn.getAttribute('aria-expanded') !== 'true'));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && document.body.classList.contains('view-open')) {
      set(false);
      btn.focus();
    }
  });
  document.addEventListener('pointerdown', (e) => {
    const t = e.target as Node;
    if (document.body.classList.contains('view-open') && !tools.contains(t) && !btn.contains(t)) set(false);
  });
}

export function setupResetButtons(reset: (body?: Body) => void): void {
  document.querySelectorAll<HTMLButtonElement>('[data-reset]').forEach((b) => {
    b.addEventListener('click', () => reset(b.dataset.reset as Body));
  });
  window.addEventListener('keydown', (e) => {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
    const target = e.target as HTMLElement | null;
    if (target && (target.closest('dialog[open]') || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
    if (e.key === 'r' || e.key === 'R' || e.key === 'Home') {
      reset();
      e.preventDefault();
    }
  });
}

export class LoadingScreen {
  private readonly root = $('loading');
  private readonly error = $('loading-error');
  private readonly retry = $('loading-retry');
  private readonly lead = $('loading-lead');
  private readonly state: Record<Body, ImageryStatus> = { earth: { ready: false }, moon: { ready: false } };
  private done = false;
  private resolveFn: (error?: string) => void = () => undefined;
  readonly finished: Promise<string | undefined>;

  constructor(timeoutMs: number) {
    this.finished = new Promise((r) => (this.resolveFn = r));
    this.retry.addEventListener('click', () => window.location.reload());
    window.setTimeout(() => {
      if (this.done) return;
      const waiting = (['earth', 'moon'] as Body[]).filter((b) => !this.state[b].ready);
      const names = waiting.map((b) => (b === 'earth' ? 'NASA GIBS (Earth)' : 'NASA Moon Trek (Moon)')).join(' and ');
      this.fail(
        `Imagery from ${names} has not finished loading after ${Math.round(timeoutMs / 1000)} seconds. ` +
          'The service may be slow or unreachable from this network. Reload to try again.',
      );
    }, timeoutMs);
  }

  update(body: Body, status: ImageryStatus): void {
    if (this.done) return;
    this.state[body] = { ...status };
    const row = $(`loading-${body}`);
    const tag = row.querySelector('.state');
    if (tag) tag.textContent = status.error ? 'Failed' : status.ready ? 'Ready' : 'Loading';
    row.dataset.state = status.error ? 'failed' : status.ready ? 'ready' : 'loading';
    if (status.error) {
      this.fail(status.error);
      return;
    }
    if (this.state.earth.ready && this.state.moon.ready) this.finish();
  }

  fail(message: string): void {
    if (this.done) return;
    this.done = true;
    this.lead.textContent = 'Imagery could not be loaded.';
    this.error.textContent = message;
    this.error.hidden = false;
    this.retry.hidden = false;
    this.root.dataset.state = 'failed';
    this.retry.focus();
    this.resolveFn(message);
  }

  private finish(): void {
    this.done = true;
    this.root.dataset.state = 'done';
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const remove = () => {
      this.root.hidden = true;
    };
    if (reduce) remove();
    else window.setTimeout(remove, 450);
    this.resolveFn(undefined);
  }
}
