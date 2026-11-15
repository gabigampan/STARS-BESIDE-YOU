// The audio guide: the one audio element of the page and the caption of what is (or would be) heard.
//
// - Tracks are the team's recordings in public/audio (served as audio/ beside index.html), listed in
//   audio/tracks.json; the caption of a track is its text in audio/transcripts.json, shown exactly.
// - Switch off (the default): nothing sounds and no audio file is requested (the element has no src
//   and preload="none"); the caption still shows the text of the current step, marked "Text only".
// - Starting a track pauses and rewinds the previous one first: two tracks never sound at once.
// - A missing or failing file shows its caption with "Audio not available: text shown" and no error.
// - A browser that refuses to start sound before the first key press or click: the caption says
//   "Press R to play".
//
// Screen readers: the caption area is NOT a live region. The single live region of the page
// (#flow-status) announces each step in one short sentence and, when a recording plays, says so;
// the full caption is reachable as ordinary text right below the steps. So the spoken recording and
// the screen reader never read the same long text at the same time, and nothing is read twice.

import { readFlag, PREF_AUDIO } from './prefs';
import { VIDEO_START_EVENT } from '../modules/video';

export interface TrackEntry {
  id: string;
  step: 'start' | 'mission' | 'pair';
  file: string;
  mission?: string;
  rank?: number;
  earth_cell_id?: string;
  moon_cell_id?: string;
}

export interface TracksManifest {
  format: string;
  tracks: TrackEntry[];
}

export type CaptionState = 'playing' | 'paused' | 'finished' | 'text-only' | 'unavailable' | 'press-r' | 'loading' | 'pending';

const STATE_WORDS: Record<CaptionState, string> = {
  playing: 'Playing',
  paused: 'Paused',
  finished: 'Finished',
  'text-only': 'Text only',
  unavailable: 'Audio not available: text shown',
  'press-r': 'Press R to play',
  loading: 'Starting',
  pending: 'Text only: new recording pending',
};

export interface GuideStep {
  /** The track recorded for this step, or null (then only the caption built from the screen is shown). */
  track: TrackEntry | null;
  /** Short title of the caption ("Welcome", "Rover mission", ...). */
  title: string;
  /** A caption built from the data on screen, used when there is no recorded track or no transcript. */
  fallback: string;
}

function audioBase(): string {
  return new URL('audio/', document.baseURI).href;
}

export class AudioGuide {
  readonly el: HTMLAudioElement;
  private enabled = readFlag(PREF_AUDIO);
  private manifest: TracksManifest | null = null;
  private transcripts: Record<string, string> | null = null;
  /** audio/pending.json: tracks whose new text is in transcripts.json while the MP3 is still the old one. */
  private pending = new Set<string>();
  private expanded = false;
  private readonly moreBtn: HTMLButtonElement;
  private step: GuideStep | null = null;
  private state: CaptionState = 'text-only';
  private requestSeq = 0;
  private readonly root: HTMLElement;
  private readonly titleEl: HTMLElement;
  private readonly stateEl: HTMLElement;
  private readonly textEl: HTMLElement;
  private readonly repeatBtn: HTMLButtonElement;
  readonly ready: Promise<void>;
  /** Every track start, for tests and the console: file names in order. */
  readonly log: string[] = [];

  constructor(root: HTMLElement) {
    this.root = root;
    this.el = document.createElement('audio');
    this.el.preload = 'none';
    this.el.id = 'guide-audio';
    this.el.hidden = true;
    document.body.append(this.el);

    root.classList.add('caption');
    const head = document.createElement('div');
    head.className = 'caption-head';
    this.titleEl = document.createElement('h2');
    this.titleEl.className = 'caption-title';
    this.titleEl.id = 'caption-title';
    this.stateEl = document.createElement('span');
    this.stateEl.className = 'caption-state';
    this.repeatBtn = document.createElement('button');
    this.repeatBtn.type = 'button';
    this.repeatBtn.className = 'btn btn-small caption-repeat';
    this.repeatBtn.setAttribute('aria-keyshortcuts', 'R');
    this.repeatBtn.innerHTML = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.4-5.7M4 4v5h5"/></svg><span>Repeat</span><kbd class="key" aria-hidden="true">R</kbd>';
    this.repeatBtn.addEventListener('click', () => this.repeat());
    this.moreBtn = document.createElement('button');
    this.moreBtn.type = 'button';
    this.moreBtn.className = 'btn btn-small caption-more';
    this.moreBtn.setAttribute('aria-controls', 'caption-text');
    this.moreBtn.addEventListener('click', () => this.setExpanded(!this.expanded));
    // one short line: the track's name, its state, and "Text" that opens the transcript on demand (R repeats; no button)
    head.append(this.titleEl, this.stateEl, this.moreBtn);
    this.textEl = document.createElement('p');
    this.textEl.className = 'caption-text';
    this.textEl.id = 'caption-text';
    this.textEl.tabIndex = -1;
    root.setAttribute('aria-labelledby', 'caption-title');
    root.append(head, this.textEl);
    // the whole text is shown while the guide speaks; with the guide off it starts folded (one control unfolds it)
    // the whole caption is always shown (never clipped); "Show less" folds it on request
    // exception: a phone on its side folds the welcome caption so that the mission cards fit the first
    // screen ("Full text" unfolds it); every later step, and the guide when it speaks, show it whole
    // the transcript stays folded until asked for; the whole line is shown only while the guide is on
    this.setExpanded(false);
    root.hidden = !this.enabled;

    this.el.addEventListener('playing', () => this.setState('playing'));
    this.el.addEventListener('pause', () => {
      if (!this.el.ended && this.state === 'playing') this.setState('paused');
    });
    this.el.addEventListener('ended', () => this.setState('finished'));
    this.el.addEventListener('error', () => {
      // only an error of the source we asked for counts (a reset clears the source)
      if (this.el.getAttribute('src')) this.setState('unavailable');
    });
    // a mission video opening or starting to play silences the guide (see interrupt)
    document.addEventListener(VIDEO_START_EVENT, () => this.interrupt());
    this.ready = this.load();
  }

  private async load(): Promise<void> {
    const get = async <T>(name: string): Promise<T | null> => {
      try {
        const r = await fetch(new URL(name, audioBase()).href, { cache: 'no-cache' });
        if (!r.ok) return null;
        return (await r.json()) as T;
      } catch {
        return null;
      }
    };
    const [m, t, p] = await Promise.all([get<TracksManifest>('tracks.json'), get<Record<string, string>>('transcripts.json'), get<{ pending_rerecord?: string[] }>('pending.json')]);
    this.pending = new Set(Array.isArray(p?.pending_rerecord) ? p.pending_rerecord.filter((x) => typeof x === 'string') : []);
    this.manifest = m && Array.isArray(m.tracks) ? m : null;
    this.transcripts = t && typeof t === 'object' ? t : null;
    if (this.step) this.render();
  }

  /** Every track's caption (transcripts.json), in the order of tracks.json, for "Data, limits and credits". */
  allTranscripts(): { file: string; text: string }[] {
    const t = this.transcripts;
    if (!t) return [];
    const files = this.manifest?.tracks.map((x) => x.file) ?? Object.keys(t);
    return files.filter((f) => typeof t[f] === 'string').map((f) => ({ file: f, text: t[f] }));
  }

  isEnabled(): boolean {
    return this.enabled;
  }

  captionState(): CaptionState {
    return this.state;
  }

  current(): GuideStep | null {
    return this.step;
  }

  /** The recorded track of a step, from tracks.json (null when the manifest has none). */
  track(step: TrackEntry['step'], mission?: string, rank?: number): TrackEntry | null {
    return this.manifest?.tracks.find((t) => t.step === step && (mission == null || t.mission === mission) && (rank == null || t.rank === rank)) ?? null;
  }

  /** The pair track recorded for exactly this pair (Earth and lunar cell ids as in docs/AUDIO_TOP5.json), or null. */
  pairTrack(mission: string, earthRef: string, moonRef: string): TrackEntry | null {
    return this.manifest?.tracks.find((t) => t.step === 'pair' && t.mission === mission && t.earth_cell_id === earthRef && t.moon_cell_id === moonRef) ?? null;
  }

  /** The caption text of the current step: the transcript of its track, else the caption from the screen. */
  captionText(): string {
    const s = this.step;
    if (!s) return '';
    const t = s.track && this.transcripts ? this.transcripts[s.track.file] : undefined;
    return typeof t === 'string' ? t : s.fallback;
  }

  /** Enter a new step: stop whatever sounds, show its caption, and play its track when the guide is on. */
  setStep(step: GuideStep): void {

    const same = !!step.track && this.step?.track?.file === step.track.file && (this.state === 'playing' || this.state === 'loading');
    this.step = step;
    if (same) {
      this.render();
      return;
    }
    this.stop();
    this.render();
    if (step.track && this.pending.has(step.track.file)) this.setState('pending');
    else if (this.enabled && step.track) void this.play();
    else this.setState('text-only');
  }

  /** Show the whole caption (unfolded) or one or two lines of it (folded). */
  setExpanded(on: boolean): void {
    this.expanded = on;
    this.root.dataset.expanded = String(on);
    this.moreBtn.setAttribute('aria-expanded', String(on));
    this.moreBtn.textContent = on ? 'Hide text' : 'Text';
    this.moreBtn.setAttribute('aria-label', on ? 'Hide text of the audio guide' : 'Text of the audio guide');
    this.textEl.hidden = !on;
  }

  setEnabled(on: boolean): void {
    this.enabled = on;
    this.root.hidden = !on;
    if (!on) this.setExpanded(false);
    if (!on) {
      this.stop();
      this.setState('text-only');
    } else if (this.step?.track) void this.play();
    else this.setState('text-only');
  }

  /** R / the Repeat control: the current track from the start (or, with the guide off, the caption again). */
  repeat(): void {
    if (!this.step) return;
    if (this.enabled && this.step.track) void this.play();
    else this.textEl.focus?.();
  }

  /**
   * Something else needs the sound (a mission video): the track that plays or is starting stops, the
   * caption stays as it is, and nothing restarts by itself. As after the end of a track, the guide stays
   * silent until R (the track from the start) or a new step.
   */
  interrupt(): void {
    if (this.state !== 'playing' && this.state !== 'loading' && this.el.paused) return;
    this.stop();
    this.setState('paused');
  }

  /** Pause and rewind, and drop the source so that nothing more is requested. */
  stop(): void {
    this.requestSeq++;
    const el = this.el;
    if (!el.paused) el.pause();
    if (el.getAttribute('src')) {
      try {
        el.currentTime = 0;
      } catch {
        /* no media loaded */
      }
      el.removeAttribute('src');
      el.load();
    }
  }

  private async play(): Promise<void> {
    const track = this.step?.track;
    if (!track) return;
    if (this.pending.has(track.file)) {
      this.setState('pending');
      return;
    }
    // a second request for the track that is starting right now is the same request
    if (this.state === 'loading' && this.el.getAttribute('src')?.endsWith(`/${track.file}`)) return;
    this.stop();
    const seq = this.requestSeq;
    const el = this.el;
    el.src = new URL(track.file, audioBase()).href;
    this.log.push(track.file);
    this.setState('loading');
    try {
      el.currentTime = 0;
    } catch {
      /* not loaded yet */
    }
    try {
      await el.play();
      if (seq === this.requestSeq && !el.paused) this.setState('playing');
    } catch (e) {
      if (seq !== this.requestSeq) return;
      const name = e instanceof DOMException ? e.name : '';
      if (name === 'NotAllowedError') this.setState('press-r');
      else if (name === 'AbortError') return;
      else this.setState('unavailable');
    }
  }

  private setState(s: CaptionState): void {
    this.state = s;
    this.root.dataset.state = s;
    this.stateEl.textContent = this.enabled || s !== 'text-only' ? STATE_WORDS[s] : 'Text only (audio guide off)';
  }

  private render(): void {
    const s = this.step;
    this.titleEl.textContent = s ? `Audio guide: ${s.title}` : "Audio guide";
    this.textEl.textContent = this.captionText();
    this.root.dataset.source = s?.track && this.transcripts && typeof this.transcripts[s.track.file] === 'string' ? 'transcript' : 'screen';
    this.setState(this.state);
  }
}
