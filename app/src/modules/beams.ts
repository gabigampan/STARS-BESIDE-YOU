// Light beam between an Earth point and its lunar twin, drawn on a full-page overlay canvas that
// sits above the globes and below the panels and never takes pointer events. The beam is additive
// light: a few soft strokes of decreasing width (falloff across), a gradient along it that is
// brighter at both ends, and a small glow where it touches each surface. An end on the far side
// stops at that body's limb and fades; an end outside its globe's canvas fades toward the edge.
// Redrawn only after a globe renders with a moved camera, on resize, or when the list changes;
// a slow, faint shimmer runs otherwise (none under reduced motion).

import { Cartesian2, Cartesian3, Matrix4, SceneTransforms } from 'cesium';
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

const LIGHT = '255, 239, 214';
// Falloff across the beam: wide faint halo to a narrow core; added together they approximate a
// soft (roughly Gaussian) profile rather than a drawn line.
const LAYERS = [
  { width: 30, alpha: 0.03 },
  { width: 16, alpha: 0.05 },
  { width: 8, alpha: 0.08 },
  { width: 3.5, alpha: 0.13 },
  { width: 1.2, alpha: 0.26 },
];

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
  private shimmerTimer = 0;
  private shimmer = 1;
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
    this.schedule();
    this.updateShimmer();
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

  private updateShimmer(): void {
    window.clearInterval(this.shimmerTimer);
    this.shimmerTimer = 0;
    this.shimmer = 1;
    if (!this.list.length || this.reducedMotion()) return;
    // ~8 redraws a second; a 7-second breath of +-5 %.
    this.shimmerTimer = window.setInterval(() => {
      if (document.hidden) return;
      this.shimmer = 1 + 0.05 * Math.sin((performance.now() / 7000) * Math.PI * 2);
      this.draw(true);
    }, 125);
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

  private draw(fromShimmer = false): void {
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
    if (!fromShimmer) this.draws++;
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
      this.drawBeam(ctx, a, m, b.strength * this.shimmer);
    }
    ctx.globalCompositeOperation = 'source-over';
  }

  private drawBeam(ctx: CanvasRenderingContext2D, a: BeamEnd, b: BeamEnd, s: number): void {
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    if (len < 1) return;
    const endAlpha = (e: BeamEnd) => (e.kind === 'point' ? 1 : 0);
    const near = Math.min(0.12, 40 / len);
    for (const layer of LAYERS) {
      const g = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
      const k = layer.alpha * s;
      const c = (v: number) => `rgba(${LIGHT}, ${Math.max(0, Math.min(1, v * k)).toFixed(4)})`;
      g.addColorStop(0, c(endAlpha(a)));
      g.addColorStop(near, c(a.kind === 'point' ? 0.85 : 0.35));
      g.addColorStop(0.5, c(0.42));
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
    for (const e of [a, b]) {
      if (e.kind !== 'point') continue;
      const r = 10 + 16 * s;
      const g = ctx.createRadialGradient(e.x, e.y, 0, e.x, e.y, r);
      g.addColorStop(0, `rgba(${LIGHT}, ${(0.45 * s).toFixed(4)})`);
      g.addColorStop(0.25, `rgba(${LIGHT}, ${(0.16 * s).toFixed(4)})`);
      g.addColorStop(1, `rgba(${LIGHT}, 0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(e.x, e.y, r, 0, Math.PI * 2);
      ctx.fill();
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
