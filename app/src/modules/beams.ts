// Light beam between an Earth point and its lunar twin, drawn on a full-page overlay canvas that
// sits above the globes and below the panels and never takes pointer events. The beam is additive
// light: a few soft strokes of decreasing width (falloff across), a gradient along it that is
// brighter at both ends, and a small glow where it touches each surface. An end on the far side
// stops at that body's limb and fades; an end outside its globe's canvas fades toward the edge.
// Redrawn only after a globe renders with a moved camera, on resize, or when the list changes.
// Mission Control look: a thin cyan line with a soft halo, and a targeting reticle on the Earth site
// and on its twin. When a new pair is set, the reticles lock on (scale 1.2 to 1 in 250 ms) and the
// beam draws from the Earth site to the twin (400 ms); then nothing moves until the camera does.
// Under reduced motion the pair appears at once.

import { Cartesian2, Cartesian3, Matrix4, SceneTransforms } from 'cesium';
import { palette } from '../a11y/palette';
import type { Body, BodyView, Globes } from '../scene/globes';

export interface LatLon {
  lat: number;
  lon: number;
}

export interface Beam {
  earth: LatLon;
  moon: LatLon;
  /** 0..1: 1 for the selected pair, about 0.2-0.35 for faint companions. */
  strength: number;
}

export type BeamEndKind = 'point' | 'limb' | 'edge' | 'hidden';

export interface BeamEnd {
  /** Page (viewport) CSS px. */
  x: number;
  y: number;
  kind: BeamEndKind;
}

export interface BeamsApi {
  setBeams(list: readonly Beam[]): void;
  clearBeams(): void;
  /** End points of each beam as last drawn (for tests). */
  lastDrawn(): { earth: BeamEnd; moon: BeamEnd; strength: number }[];
  /** How many times the overlay was redrawn (for tests and performance checks). */
  drawCount(): number;
}

// the beam's light comes from the active palette (src/a11y/palette.ts)
const lightRgb = () => palette().beam.join(', ');
// Falloff across the beam: wide faint halo to a narrow core; added together they approximate a
// soft (roughly Gaussian) profile rather than a drawn line.
const LAYERS = [
  { width: 10, alpha: 0.06 },
  { width: 4, alpha: 0.16 },
  { width: 1.5, alpha: 0.95 },
];
// the reticle's colour: the HUD's gold (the colour-blind palette's accent when that mode is on)
const reticleColour = () => getComputedStyle(document.documentElement).getPropertyValue('--hud-gold').trim() || '#e9b949';
const BEAM_MS = 400;
const LOCK_MS = 250;
const easeOut = (p: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, p)), 3);

interface Rect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export class Beams implements BeamsApi {
  private list: Beam[] = [];
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private drawn: { earth: BeamEnd; moon: BeamEnd; strength: number }[] = [];
  private draws = 0;
  private readonly lastView: Record<Body, Matrix4> = { earth: new Matrix4(), moon: new Matrix4() };
  private needsDraw = false;
  /** Start of the lock-on of the current pair (performance.now()), 0 when settled. */
  private introStart = 0;
  private introKey = '';
  private introFrame = 0;
  private reticle = '#e9b949';
  private readonly scratch = new Cartesian2();

  constructor(
    private readonly globes: Globes,
    private readonly reducedMotion: () => boolean,
  ) {
    for (const v of [globes.earth, globes.moon]) {
      v.scene.postRender.addEventListener(() => {
        if (!this.list.length) return;
        if (!Matrix4.equalsEpsilon(v.scene.camera.viewMatrix, this.lastView[v.body], 1e-9)) {
          Matrix4.clone(v.scene.camera.viewMatrix, this.lastView[v.body]);
          this.schedule();
        }
      });
    }
    window.addEventListener('resize', () => this.schedule());
  }

  setBeams(list: readonly Beam[]): void {
    this.list = list
      .filter((b) => b && Number.isFinite(b.earth?.lat) && Number.isFinite(b.moon?.lat))
      .map((b) => ({ ...b, strength: Math.min(1, Math.max(0, Number(b.strength) || 0)) }))
      .sort((a, b) => a.strength - b.strength);
    if (this.list.length) this.ensureCanvas();
    this.reticle = reticleColour();
    this.startIntro();
    this.schedule();
  }

  clearBeams(): void {
    this.setBeams([]);
  }

  lastDrawn() {
    return this.drawn.map((d) => ({ earth: { ...d.earth }, moon: { ...d.moon }, strength: d.strength }));
  }

  drawCount(): number {
    return this.draws;
  }

  private ensureCanvas(): void {
    if (this.canvas) return;
    const c = document.createElement('canvas');
    c.className = 'beam-overlay';
    c.setAttribute('aria-hidden', 'true');
    document.body.appendChild(c);
    this.canvas = c;
    this.ctx = c.getContext('2d');
  }

  private schedule(): void {
    if (this.needsDraw) return;
    this.needsDraw = true;
    requestAnimationFrame(() => {
      this.needsDraw = false;
      this.draw();
    });
  }

  /** A new selected pair: lock on and draw the beam once (a few hundred ms of frames, then still). */
  private startIntro(): void {
    const top = this.list.find((b) => b.strength >= 1);
    const key = top ? `${top.earth.lat},${top.earth.lon},${top.moon.lat},${top.moon.lon}` : '';
    if (key === this.introKey) return;
    this.introKey = key;
    cancelAnimationFrame(this.introFrame);
    this.introFrame = 0;
    this.introStart = 0;
    if (!key || this.reducedMotion()) return;
    this.introStart = performance.now();
    const tick = () => {
      if (!this.introStart) return;
      if (performance.now() - this.introStart >= BEAM_MS) this.introStart = 0;
      this.draw(true);
      this.introFrame = this.introStart ? requestAnimationFrame(tick) : 0;
    };
    this.introFrame = requestAnimationFrame(tick);
  }

  /** 0..1 progress of the beam's draw and of the reticles' lock-on (1 when settled). */
  private progress(): { beam: number; lock: number } {
    if (!this.introStart) return { beam: 1, lock: 1 };
    const t = performance.now() - this.introStart;
    return { beam: easeOut(t / BEAM_MS), lock: easeOut(t / LOCK_MS) };
  }

  /** Project a surface point; on the far side, the nearest point of the limb instead. */
  private end(view: BodyView, p: LatLon): BeamEnd {
    const scene = view.scene;
    const ellipsoid = view.ellipsoid;
    const rect = view.scene.canvas.getBoundingClientRect();
    const world = Cartesian3.fromDegrees(p.lon, p.lat, 0, ellipsoid);
    const cam = ellipsoid.transformPositionToScaledSpace(scene.camera.positionWC, new Cartesian3());
    const pt = ellipsoid.transformPositionToScaledSpace(world, new Cartesian3());
    const toCam = Cartesian3.subtract(cam, pt, new Cartesian3());
    let kind: BeamEndKind = 'point';
    let target = world;
    if (Cartesian3.dot(toCam, pt) <= 0) {
      // Limb point in the plane of the body centre, the camera and the point.
      const camLen = Cartesian3.magnitude(cam);
      const chat = Cartesian3.normalize(cam, new Cartesian3());
      const q = Cartesian3.subtract(pt, Cartesian3.multiplyByScalar(chat, Cartesian3.dot(pt, chat), new Cartesian3()), new Cartesian3());
      if (Cartesian3.magnitude(q) < 1e-9) return { x: NaN, y: NaN, kind: 'hidden' };
      Cartesian3.normalize(q, q);
      const cosT = 1 / camLen;
      const sinT = Math.sqrt(Math.max(0, 1 - cosT * cosT));
      const limb = Cartesian3.add(
        Cartesian3.multiplyByScalar(chat, cosT, new Cartesian3()),
        Cartesian3.multiplyByScalar(q, sinT, new Cartesian3()),
        new Cartesian3(),
      );
      Cartesian3.multiplyByScalar(limb, 0.9995, limb); // just inside the visible disc
      target = ellipsoid.transformPositionFromScaledSpace(limb, new Cartesian3());
      kind = 'limb';
    }
    const w = SceneTransforms.worldToWindowCoordinates(scene, target, this.scratch);
    if (!w) return { x: NaN, y: NaN, kind: 'hidden' };
    return { x: rect.left + w.x, y: rect.top + w.y, kind };
  }

  private draw(fromIntro = false): void {
    const canvas = this.canvas;
    const ctx = this.ctx;
    if (!canvas || !ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = window.innerWidth;
    const H = window.innerHeight;
    if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) {
      canvas.width = Math.round(W * dpr);
      canvas.height = Math.round(H * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    if (!fromIntro) this.draws++;
    this.drawn = [];
    if (!this.list.length) return;
    const { earth, moon } = this.globes;
    const eRect = rectOf(earth.scene.canvas);
    const mRect = rectOf(moon.scene.canvas);
    ctx.globalCompositeOperation = 'lighter';
    for (const b of this.list) {
      let a = this.end(earth, b.earth);
      let m = this.end(moon, b.moon);
      if (a.kind === 'hidden' || m.kind === 'hidden') {
        this.drawn.push({ earth: a, moon: m, strength: b.strength });
        continue;
      }
      // Ends outside their own globe's canvas: move them to that canvas edge, in the direction of
      // the point as seen from the canvas centre, and fade the beam there.
      if (!inside(a, eRect)) a = toEdge(a, eRect);
      if (!inside(m, mRect)) m = toEdge(m, mRect);
      this.drawn.push({ earth: a, moon: m, strength: b.strength });
      if (a.kind === 'hidden' || m.kind === 'hidden') continue;
      const pr = b.strength >= 1 ? this.progress() : { beam: 1, lock: 1 };
      this.drawBeam(ctx, a, m, b.strength, pr.beam);
      if (b.strength >= 1) {
        ctx.globalCompositeOperation = 'source-over';
        for (const e of [a, m]) if (e.kind === 'point') this.drawReticle(ctx, e, pr.lock);
        ctx.globalCompositeOperation = 'lighter';
      }
    }
    ctx.globalCompositeOperation = 'source-over';
  }

  /** A targeting reticle: a ring, four ticks and four corner brackets; scale 1.2 to 1 while locking on. */
  private drawReticle(ctx: CanvasRenderingContext2D, e: BeamEnd, lock: number): void {
    const s = 1.2 - 0.2 * lock;
    const R = 13 * s;
    const B = 24 * s; // half size of the bracket square
    const L = 7 * s; // bracket arm
    ctx.save();
    ctx.globalAlpha = 0.35 + 0.65 * lock;
    ctx.strokeStyle = this.reticle;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(e.x, e.y, R, 0, Math.PI * 2);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      ctx.moveTo(e.x + dx * (R - 4 * s), e.y + dy * (R - 4 * s));
      ctx.lineTo(e.x + dx * (R + 6 * s), e.y + dy * (R + 6 * s));
    }
    for (const [sx, sy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
      const cx = e.x + sx * B;
      const cy = e.y + sy * B;
      ctx.moveTo(cx - sx * L, cy);
      ctx.lineTo(cx, cy);
      ctx.lineTo(cx, cy - sy * L);
    }
    ctx.stroke();
    ctx.restore();
  }

  private drawBeam(ctx: CanvasRenderingContext2D, a: BeamEnd, full: BeamEnd, s: number, grow = 1): void {
    // while drawing in, the beam runs from the Earth site to a point on its way to the twin
    const b: BeamEnd = grow >= 1 ? full : { x: a.x + (full.x - a.x) * grow, y: a.y + (full.y - a.y) * grow, kind: grow > 0.97 ? full.kind : 'point' };
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    if (len < 1) return;
    const endAlpha = (e: BeamEnd) => (e.kind === 'point' ? 1 : 0);
    const near = Math.min(0.12, 40 / len);
    for (const layer of LAYERS) {
      const g = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
      const k = layer.alpha * s;
      const LIGHT = lightRgb();
      const c = (v: number) => `rgba(${LIGHT}, ${Math.max(0, Math.min(1, v * k)).toFixed(4)})`;
      g.addColorStop(0, c(endAlpha(a)));
      g.addColorStop(near, c(a.kind === 'point' ? 0.85 : 0.35));
      g.addColorStop(0.5, c(0.7));
      g.addColorStop(1 - near, c(b.kind === 'point' ? 0.85 : 0.35));
      g.addColorStop(1, c(endAlpha(b)));
      ctx.strokeStyle = g;
      ctx.lineWidth = layer.width * (0.6 + 0.4 * s);
      ctx.lineCap = 'butt';
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }
    // a small square where the beam touches each surface (the twin's only once the beam reaches it)
    const LIGHT = lightRgb();
    ctx.fillStyle = `rgba(${LIGHT}, ${(0.95 * s).toFixed(4)})`;
    for (const e of grow >= 1 ? [a, b] : [a]) {
      if (e.kind !== 'point') continue;
      ctx.fillRect(e.x - 2.5, e.y - 2.5, 5, 5);
    }
  }
}

function rectOf(el: HTMLElement): Rect {
  const r = el.getBoundingClientRect();
  return { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
}

function inside(p: BeamEnd, r: Rect): boolean {
  return p.x >= r.left && p.x <= r.right && p.y >= r.top && p.y <= r.bottom;
}

/** The point where the line from the centre of r toward p leaves r, as an 'edge' end. */
function toEdge(p: BeamEnd, r: Rect): BeamEnd {
  const cx = (r.left + r.right) / 2;
  const cy = (r.top + r.bottom) / 2;
  const dx = p.x - cx;
  const dy = p.y - cy;
  if (!Number.isFinite(dx) || !Number.isFinite(dy) || (dx === 0 && dy === 0)) return { x: NaN, y: NaN, kind: 'hidden' };
  const hw = (r.right - r.left) / 2 - 1;
  const hh = (r.bottom - r.top) / 2 - 1;
  const t = Math.min(dx !== 0 ? hw / Math.abs(dx) : Infinity, dy !== 0 ? hh / Math.abs(dy) : Infinity);
  return { x: cx + dx * t, y: cy + dy * t, kind: 'edge' };
}
