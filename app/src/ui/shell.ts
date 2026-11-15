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
    // A pointer click on the backdrop (outside the dialog box) closes it; a keyboard click (Enter on a
    // summary or a link inside) has no position and must not.
    if (e.target !== dialog || e.detail === 0) return;
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
    // R repeats the audio guide (src/a11y/keys.ts); Home resets both views
    if (e.key === 'Home') {
      reset();
      e.preventDefault();
    }
  });
}

const BODY_NAME: Record<Body, string> = { earth: 'the Earth', moon: 'the Moon' };
const SOURCE: Record<Body, string> = { earth: 'NASA GIBS (Earth)', moon: 'NASA Moon Trek (Moon)' };

/**
 * Non-blocking loading: each globe's own box shows one short line ("Loading the Earth…") until its
 * first imagery is drawn, or one short failure line with a small Retry. The rest of the page is
 * usable at once. #loading is a screen-reader-only live region: it carries the failure sentence and
 * is hidden once both globes are ready (the automated tests wait on that).
 */
export class LoadingScreen {
  private readonly root = $('loading');
  private readonly error = $('loading-error');
  private readonly retry = $('loading-retry');
  private readonly state: Record<Body, ImageryStatus> = { earth: { ready: false }, moon: { ready: false } };
  private done = false;
  private resolveFn: (error?: string) => void = () => undefined;
  readonly finished: Promise<string | undefined>;

  constructor(timeoutMs: number) {
    this.finished = new Promise((r) => (this.resolveFn = r));
    this.retry.addEventListener('click', () => window.location.reload());
    window.setTimeout(() => {
      for (const b of ['earth', 'moon'] as Body[]) {
        if (this.state[b].ready || this.state[b].error) continue;
        this.failBody(
          b,
          `Imagery from ${SOURCE[b]} has not finished loading after ${Math.round(timeoutMs / 1000)} seconds. ` +
            'The service may be slow or unreachable from this network. Reload to try again.',
        );
      }
    }, timeoutMs);
  }

  private line(body: Body): HTMLElement {
    return $(`${body}-status`);
  }

  update(body: Body, status: ImageryStatus): void {
    if (this.state[body].error) return;
    this.state[body] = { ...status };
    if (status.error) return this.failBody(body, status.error);
    if (status.ready) this.line(body).hidden = true;
    if (this.state.earth.ready && this.state.moon.ready && !this.done) {
      this.done = true;
      this.root.dataset.state = 'done';
      this.root.hidden = true;
      this.resolveFn(undefined);
    }
  }

  private failBody(body: Body, message: string): void {
    this.state[body] = { ready: false, error: message };
    const line = this.line(body);
    line.hidden = false;
    line.dataset.state = 'failed';
    (line.querySelector('.pane-status-text') as HTMLElement).textContent = `The imagery of ${BODY_NAME[body]} did not load.`;
    line.querySelector('.spinner')?.remove();
    line.append(this.retry);
    this.retry.hidden = false;
    this.root.dataset.state = 'failed';
    this.error.textContent = this.error.textContent ? `${this.error.textContent} ${message}` : message;
    this.error.hidden = false;
    if (!this.done) {
      this.done = true;
      this.resolveFn(message);
    }
  }

  /** No WebGL: one short message in place of the globes, nothing else waits for them. */
  noGlobes(message: string): void {
    this.done = true;
    this.root.dataset.state = 'failed';
    this.root.hidden = true;
    const earth = this.line('earth');
    earth.dataset.state = 'off';
    earth.querySelector('.spinner')?.remove();
    (earth.querySelector('.pane-status-text') as HTMLElement).textContent = message;
    this.line('moon').hidden = true;
    document.body.classList.add('no-globes');
    this.resolveFn(message);
  }
}
