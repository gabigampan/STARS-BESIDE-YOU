// Mission video dialog: a modal <dialog> built on first use (nothing in the page offers a video
// until openVideo is called with real files). Native video controls, captions shown by default,
// the credit line and a note under the player. Focus is kept inside the dialog, Escape or the
// close button (an X) closes it, and focus returns to the element that opened it. If the video
// cannot be loaded the player is replaced by a message saying what happened and what to do.

export interface VideoSource {
  src: string;
  /** MIME type, for example 'video/mp4' or 'video/webm'. */
  type: string;
}

export interface VideoTrack {
  src: string;
  srclang: string;
  label: string;
  default?: boolean;
}

export interface VideoSpec {
  title: string;
  sources: readonly VideoSource[];
  poster?: string;
  tracks?: readonly VideoTrack[];
  /** Credit line shown under the player. */
  credit?: string;
  /** Short note shown under the credit (what the video shows, how it was made). */
  note?: string;
}

export interface VideoApi {
  /** Open the dialog and load the video. Resolves when the dialog closes. */
  openVideo(spec: VideoSpec): Promise<void>;
  /** Close the dialog if it is open. */
  closeVideo(): void;
  isOpen(): boolean;
}

/** Dispatched on document when a mission video's dialog opens and each time its film starts playing
 * (the audio guide listens and falls silent: one sound at a time). */
export const VIDEO_START_EVENT = 'stars:video-start';

const announceStart = () => document.dispatchEvent(new Event(VIDEO_START_EVENT));

const FOCUSABLE = 'button, [href], input, select, textarea, video[controls], [tabindex]:not([tabindex="-1"])';

export class VideoDialog implements VideoApi {
  private dialog: HTMLDialogElement | null = null;
  private returnFocus: HTMLElement | null = null;
  private resolveClose: (() => void) | null = null;
  private spec: VideoSpec | null = null;

  isOpen(): boolean {
    return !!this.dialog?.open;
  }

  openVideo(spec: VideoSpec): Promise<void> {
    if (!spec || !spec.title || !spec.sources?.length) {
      return Promise.reject(new Error('openVideo needs a title and at least one source'));
    }
    const dialog = this.build();
    if (dialog.open) this.closeVideo();
    this.returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    this.spec = spec;
    this.fill(spec);
    dialog.showModal();
    announceStart();
    this.startPlayback(dialog);
    return new Promise((resolve) => (this.resolveClose = resolve));
  }

  /**
   * "Start the mission" starts the film: focus goes to the player (Space then pauses or plays it, it
   * never closes the dialog) and playback begins, muted if the browser refuses sound without a
   * gesture. Under prefers-reduced-motion the film waits, paused, with focus on the player.
   */
  private startPlayback(dialog: HTMLDialogElement): void {
    const video = dialog.querySelector('video');
    if (!video) {
      (dialog.querySelector('.video-retry, .video-close') as HTMLButtonElement | null)?.focus();
      return;
    }
    video.tabIndex = 0;
    video.focus();
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
    video.play().catch(() => {
      video.muted = true;
      return video.play().catch(() => undefined);
    });
  }

  closeVideo(): void {
    if (this.dialog?.open) this.dialog.close();
  }

  private build(): HTMLDialogElement {
    if (this.dialog) return this.dialog;
    const d = document.createElement('dialog');
    d.className = 'video-dialog';
    d.setAttribute('aria-labelledby', 'video-title');
    d.innerHTML = `
      <div class="video-head">
        <h2 id="video-title" class="video-title"></h2>
        <button type="button" class="btn video-close" aria-label="Close video">
          <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
            <path d="M5 5 L19 19 M19 5 L5 19" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
          </svg>
        </button>
      </div>
      <div class="video-frame"></div>
      <div class="video-error" role="alert" hidden>
        <p class="video-error-text"></p>
        <button type="button" class="btn video-retry">Try again</button>
      </div>
      <p class="video-credit"></p>
      <p class="video-note"></p>`;
    document.body.appendChild(d);
    d.querySelector('.video-close')?.addEventListener('click', () => d.close());
    d.querySelector('.video-retry')?.addEventListener('click', () => {
      if (this.spec) this.fill(this.spec);
    });
    d.addEventListener('close', () => {
      const v = d.querySelector('video');
      if (v) {
        v.pause();
        v.removeAttribute('src');
        v.querySelectorAll('source').forEach((s) => s.remove());
        v.load();
      }
      this.returnFocus?.focus();
      this.returnFocus = null;
      this.resolveClose?.();
      this.resolveClose = null;
    });
    // Backdrop click closes.
    d.addEventListener('click', (e) => {
      if (e.target === d) {
        const r = d.getBoundingClientRect();
        if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) d.close();
      }
    });
    // Keep Tab inside the dialog.
    d.addEventListener('keydown', (e) => {
      if (e.key !== 'Tab') return;
      const items = Array.from(d.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => !el.closest('[hidden]') && el.getClientRects().length > 0,
      );
      if (!items.length) return;
      const first = items[0] as HTMLElement;
      const last = items[items.length - 1] as HTMLElement;
      const active = document.activeElement;
      if (e.shiftKey && (active === first || !d.contains(active))) {
        last.focus();
        e.preventDefault();
      } else if (!e.shiftKey && (active === last || !d.contains(active))) {
        first.focus();
        e.preventDefault();
      }
    });
    this.dialog = d;
    return d;
  }

  private fill(spec: VideoSpec): void {
    const d = this.dialog as HTMLDialogElement;
    (d.querySelector('.video-title') as HTMLElement).textContent = spec.title;
    const credit = d.querySelector('.video-credit') as HTMLElement;
    credit.textContent = spec.credit ?? '';
    credit.hidden = !spec.credit;
    const note = d.querySelector('.video-note') as HTMLElement;
    note.textContent = spec.note ?? '';
    note.hidden = !spec.note;
    const errorBox = d.querySelector('.video-error') as HTMLElement;
    errorBox.hidden = true;

    const frame = d.querySelector('.video-frame') as HTMLElement;
    frame.hidden = false;
    frame.replaceChildren();
    const video = document.createElement('video');
    video.controls = true;
    video.preload = 'metadata';
    video.playsInline = true;
    video.crossOrigin = 'anonymous';
    video.addEventListener('play', announceStart);
    if (spec.poster) video.poster = spec.poster;
    const names = spec.sources.map((s) => s.src.split('/').pop() || s.src).join(', ');
    const fail = (why: string) => {
      if (!errorBox.hidden) return;
      video.pause();
      frame.hidden = true;
      frame.replaceChildren();
      (d.querySelector('.video-error-text') as HTMLElement).textContent =
        `The video could not be played: ${why} (${names}). ` +
        'Check your connection and choose Try again; if it still fails, the file is missing from this deployment.';
      errorBox.hidden = false;
      (d.querySelector('.video-retry') as HTMLButtonElement).focus();
    };
    const playable = spec.sources.filter((s) => !s.type || video.canPlayType(s.type) !== '');
    if (!playable.length) {
      fail('this browser cannot play any of the offered formats');
      return;
    }
    playable.forEach((s, i) => {
      const el = document.createElement('source');
      el.src = s.src;
      if (s.type) el.type = s.type;
      // Every <source> failing means nothing could be loaded (video.error stays null in that case).
      if (i === playable.length - 1) el.addEventListener('error', () => fail('the file was not found or could not be read'));
      video.appendChild(el);
    });
    video.addEventListener('error', () => {
      const code = video.error?.code;
      fail(code === 3 ? 'the file is damaged or in an unsupported encoding' : 'the file was not found or could not be read');
    });
    const tracks = spec.tracks ?? [];
    const hasDefault = tracks.some((t) => t.default);
    tracks.forEach((t, i) => {
      const el = document.createElement('track');
      el.kind = 'captions';
      el.src = t.src;
      el.srclang = t.srclang;
      el.label = t.label;
      if (t.default || (!hasDefault && i === 0)) el.default = true;
      video.appendChild(el);
    });
    // Captions on by default: show the default track (or the first one).
    const showCaptions = () => {
      const list = Array.from(video.textTracks);
      const want = tracks.findIndex((t) => t.default);
      list.forEach((tt, i) => (tt.mode = i === (want >= 0 ? want : 0) ? 'showing' : 'disabled'));
    };
    video.addEventListener('loadedmetadata', showCaptions);
    frame.appendChild(video);
    showCaptions();
  }
}
