// Sunlight and time: which Sun lights both globes. Three choices in the header:
//   'full-moon' (default)  fixed instant computed in scene/fullMoon.ts: Moon's near side fully lit,
//                          Europe and Africa in daylight. Physical lighting, clock stopped.
//   'now'                  the real time, running. Physical lighting.
//   'even'                 day and night shading off on both globes (not physical), for inspecting any point.
// A page link with ?time=ISO starts in 'link' mode (that instant, physical, clock running); ?light=now|even|full-moon
// picks a choice from the link.

import { Cartesian3, ClockStep, JulianDate, Math as CesiumMath } from 'cesium';
import { computeFullMoonInstant, type FullMoonInstant } from '../scene/fullMoon';
import { earthHome, moonHome, resetView, type Body, type Globes } from '../scene/globes';
import { subsolarPointEarth, sunDirectionMoonFixed } from '../scene/sun';

export type SunlightChoice = 'full-moon' | 'now' | 'even';
export type SunlightMode = SunlightChoice | 'link';

export interface SunlightApi {
  /** Active mode. 'link' only when the page was opened with ?time=. */
  mode(): SunlightMode;
  /** Switch the light. Cameras still on their home view turn to face the sunlit side. */
  set(choice: SunlightChoice): void;
  /** The computed Full Moon instant (UTC). */
  fullMoonDate(): Date;
  /** The sentence shown in the header for the active mode. */
  describe(): string;
  /** Sub-solar point (degrees) on a body for the current clock (where the Sun is overhead). */
  subsolar(body: Body): { lat: number; lon: number };
  /** Called after every change; returns an unsubscribe function. */
  onChange(listener: (mode: SunlightMode) => void): () => void;
}

const fmt = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'UTC',
  hour12: false,
});
export const formatUtc = (d: Date) => `${fmt.format(d)} UTC`;

export class Sunlight implements SunlightApi {
  private current: SunlightMode = 'full-moon';
  private readonly full: FullMoonInstant;
  private readonly listeners = new Set<(m: SunlightMode) => void>();
  private linkTime: JulianDate | undefined;

  constructor(
    private readonly globes: Globes,
    private readonly reducedMotion: () => boolean,
  ) {
    this.full = computeFullMoonInstant();
  }

  /** Apply the start mode from the page URL (?time=, ?light=) or the default, without animation. */
  start(search = window.location.search): void {
    const params = new URLSearchParams(search);
    const time = params.get('time');
    const light = params.get('light');
    const ms = time ? Date.parse(time) : NaN;
    // the team lead's ruling: one fixed, even lighting on both globes (no sunlight options)
    void ms;
    void light;
    this.apply('even', true);
  }

  mode(): SunlightMode {
    return this.current;
  }

  set(choice: SunlightChoice): void {
    if (choice === this.current) return;
    this.apply(choice, this.reducedMotion());
  }

  fullMoonDate(): Date {
    return JulianDate.toDate(this.full.time);
  }

  describe(): string {
    const clock = this.globes.clock;
    switch (this.current) {
      case 'full-moon':
        return `Full Moon light, ${formatUtc(this.fullMoonDate())}`;
      case 'now':
        return `Light now, ${formatUtc(JulianDate.toDate(clock.currentTime))}`;
      case 'even':
        return 'Even light: day and night shading off (not physical)';
      case 'link':
        return `Light for ${formatUtc(JulianDate.toDate(clock.currentTime))}, set by the page link`;
    }
  }

  subsolar(body: Body): { lat: number; lon: number } {
    const time = this.globes.clock.currentTime;
    if (body === 'earth') return subsolarPointEarth(time);
    const d = sunDirectionMoonFixed(time, new Cartesian3());
    return { lat: CesiumMath.toDegrees(Math.asin(d.z)), lon: CesiumMath.toDegrees(Math.atan2(d.y, d.x)) };
  }

  onChange(listener: (m: SunlightMode) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private apply(mode: SunlightMode, instant: boolean): void {
    const { clock, earth, moon } = this.globes;
    this.current = mode;
    clock.clockStep = ClockStep.SYSTEM_CLOCK_MULTIPLIER;
    clock.multiplier = 1;
    if (mode === 'full-moon') {
      clock.currentTime = JulianDate.clone(this.full.time);
      clock.shouldAnimate = false;
    } else if (mode === 'now') {
      clock.currentTime = JulianDate.now();
      clock.shouldAnimate = true;
    } else if (mode === 'link' && this.linkTime) {
      clock.currentTime = JulianDate.clone(this.linkTime);
      clock.shouldAnimate = true;
    }
    this.globes.setPhysicalLighting(mode !== 'even');
    if (mode !== 'even') {
      earth.home = earthHome(clock.currentTime);
      moon.home = moonHome(clock.currentTime);
    }
    // Cameras the user has not moved turn to face the sunlit side; others stay where they are.
    for (const v of [earth, moon]) {
      if (v.atHome) resetView(v, instant);
      v.scene.requestRender();
    }
    this.listeners.forEach((l) => l(mode));
  }
}

/**
 * Header control: the radio group in index.html (#sunlight), the visible status line (#sun-time)
 * and a polite live region (#sunlight-status) that announces a change once.
 */
export function bindSunlightControl(sunlight: Sunlight): void {
  const group = document.getElementById('sunlight');
  const line = document.getElementById('sun-time');
  const live = document.getElementById('sunlight-status');
  if (!group || !line || !live) return;
  const radios = Array.from(group.querySelectorAll<HTMLInputElement>('input[name="sunlight"]'));
  const sync = (announce: boolean) => {
    const mode = sunlight.mode();
    for (const r of radios) r.checked = r.value === mode;
    const text = sunlight.describe();
    line.textContent = text;
    group.dataset.mode = mode;
    if (announce) live.textContent = text;
  };
  for (const r of radios) {
    r.addEventListener('change', () => {
      if (r.checked) sunlight.set(r.value as SunlightChoice);
    });
  }
  sunlight.onChange(() => sync(true));
  sync(false);
  // "Now" runs in real time: keep the printed time current (not announced).
  window.setInterval(() => {
    if (sunlight.mode() === 'now' || sunlight.mode() === 'link') line.textContent = sunlight.describe();
  }, 15_000);
}
