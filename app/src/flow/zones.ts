// Mission zones on the Moon (contract revision 6: mission_zones.json and the moon_base.bin region
// column). When a mission is chosen the Moon globe shows its search zone (a light tint with an
// outline, over the imagery) and the Moon caption names it, with a "Why this zone?" control. The
// panel gives the mission's zone_why text, the general note and, under "Other parts of the Moon",
// each region outside the zone with its approved text for this mission. A tap or click on a lunar
// cell outside the zone opens the same panel at that region's entry. Every text is the bundle's,
// verbatim; with texts null only the regions and the zone are shown. Nothing appears when the
// bundle has no zone data.

import { Cartesian2, Ellipsoid, ImageryLayer, Rectangle, SingleTileImageryProvider } from 'cesium';
import { palette } from '../a11y/palette';
import { globesApi } from '../api';
import type { Mission, MissionZonesJson, ZoneRegion } from '../data/types.ts';
import type { FlowApp } from './app';
import { missionName } from './copy';
import { append, button, h, icon, int, latLonText } from './dom';

const PX_PER_CELL = 10;

function dateWords(iso: string): string {
  const d = new Date(`${iso}T12:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(d);
}

export class ZoneView {
  private layer: ImageryLayer | null = null;
  private missionId: string | null = null;
  private dialog: HTMLDialogElement | null = null;
  private lastMarkerPick = -1;
  private bound = false;
  private seq = 0;

  constructor(private readonly app: FlowApp) {}

  /** True when the open mission's zone is on the globe (the bundle has zone data and it loaded). */
  active(): boolean {
    return this.missionId != null && this.app.store.zones != null;
  }

  /** Show the zone of a mission (no-op without zone data in the bundle). */
  async show(missionId: string): Promise<void> {
    const store = this.app.store;
    const seq = ++this.seq;
    if (!store.hasZones()) return this.hide();
    try {
      await store.loadZones();
    } catch {
      // the zone is an explanation layer: without it the flow still works; the Moon caption says so
      this.missionId = null;
      this.app.updateMoonNote();
      return;
    }
    if (seq !== this.seq) return;
    this.missionId = missionId;
    this.bindTap();
    this.draw(missionId);
    this.app.updateMoonNote();
  }

  /** Draw the zone again in the active palette. */
  repaint(): void {
    if (this.missionId) this.draw(this.missionId);
  }

  hide(): void {
    this.seq++;
    this.missionId = null;
    this.removeLayer();
    this.closePanel();
  }

  private removeLayer(): void {
    if (!this.layer) return;
    try {
      globesApi.scene('moon').imageryLayers.remove(this.layer, true);
      globesApi.scene('moon').requestRender();
    } catch {
      /* globes gone */
    }
    this.layer = null;
  }

  /** The zone as one image over the whole Moon: a light tint inside, a line along its edge. */
  private draw(missionId: string): void {
    this.removeLayer();
    const mask = this.app.store.zoneMask(missionId);
    if (!mask) return;
    const g = this.app.store.manifest.grid;
    const W = g.cols * PX_PER_CELL;
    const H = g.rows * PX_PER_CELL;
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const pal = palette();
    ctx.fillStyle = `rgba(${pal.zoneLine.join(', ')}, ${pal.zoneFillAlpha})`;
    for (let r = 0; r < g.rows; r++) for (let c = 0; c < g.cols; c++) if (mask[r * g.cols + c]) ctx.fillRect(c * PX_PER_CELL, r * PX_PER_CELL, PX_PER_CELL, PX_PER_CELL);
    ctx.fillStyle = `rgba(${pal.zoneLine.join(', ')}, 0.85)`;
    const at = (r: number, c: number) => (r < 0 || r >= g.rows ? 0 : mask[r * g.cols + ((c + g.cols) % g.cols)]);
    for (let r = 0; r < g.rows; r++) {
      for (let c = 0; c < g.cols; c++) {
        if (!mask[r * g.cols + c]) continue;
        const x = c * PX_PER_CELL;
        const y = r * PX_PER_CELL;
        if (!at(r - 1, c) && r > 0) ctx.fillRect(x, y, PX_PER_CELL, 1);
        if (!at(r + 1, c) && r < g.rows - 1) ctx.fillRect(x, y + PX_PER_CELL - 1, PX_PER_CELL, 1);
        if (!at(r, c - 1)) ctx.fillRect(x, y, 1, PX_PER_CELL);
        if (!at(r, c + 1)) ctx.fillRect(x + PX_PER_CELL - 1, y, 1, PX_PER_CELL);
      }
    }
    try {
      const provider = new SingleTileImageryProvider({
        url: canvas.toDataURL('image/png'),
        tileWidth: W,
        tileHeight: H,
        rectangle: Rectangle.fromDegrees(-180, -90, 180, 90),
        ellipsoid: Ellipsoid.MOON,
      });
      const layer = new ImageryLayer(provider, {});
      globesApi.scene('moon').imageryLayers.add(layer);
      globesApi.scene('moon').requestRender();
      this.layer = layer;
      document.body.dataset.zone = missionId;
    } catch {
      this.layer = null;
    }
  }

  // ---------- the Moon caption ----------

  /** The zone label and the "Why this zone?" control, for the Moon caption. */
  control(m: Mission, id = 'zone-why'): HTMLElement | null {
    if (!this.active() || this.missionId !== m.id) return null;
    const names = this.zoneRegions(m.id).map((r) => r.label);
    const zone = this.app.zoneName(m) ?? names.join(' and ');
    return h(
      'div',
      { class: 'zone-caption', 'data-zone': m.id },
      h('p', { class: 'zone-label' }, h('span', { class: 'zone-swatch', 'aria-hidden': 'true' }), h('span', null, `Search zone (outlined): ${zone}`)),
      button('Why this zone?', () => this.openPanel(), { kind: 'quiet', icon: 'info', cls: 'btn-small zone-why-btn', id }),
    );
  }

  private zoneRegions(missionId: string): ZoneRegion[] {
    const z = this.app.store.zones;
    if (!z) return [];
    const codes = new Set(this.app.store.zoneCodes(missionId));
    return z.regions.filter((r) => codes.has(r.code));
  }

  private outsideRegions(missionId: string): ZoneRegion[] {
    const z = this.app.store.zones;
    if (!z) return [];
    const codes = new Set(this.app.store.zoneCodes(missionId));
    return z.regions.filter((r) => !codes.has(r.code));
  }

  // ---------- tap on a lunar cell ----------

  private bindTap(): void {
    if (this.bound) return;
    this.bound = true;
    globesApi.markers.onPick((body) => {
      if (body === 'moon') this.lastMarkerPick = performance.now();
    });
    const canvas = globesApi.scene('moon').canvas;
    let down: { x: number; y: number; t: number; id: number } | null = null;
    canvas.addEventListener('pointerdown', (e) => {
      if (!e.isPrimary || e.button > 0) return;
      down = { x: e.clientX, y: e.clientY, t: e.timeStamp, id: e.pointerId };
    });
    canvas.addEventListener('pointerup', (e) => {
      const d = down;
      down = null;
      if (!d || d.id !== e.pointerId || !this.active() || this.app.state.step === 'choose') return;
      if (Math.hypot(e.clientX - d.x, e.clientY - d.y) > 6 || e.timeStamp - d.t > 700) return; // a drag
      const r = canvas.getBoundingClientRect();
      const x = e.clientX - r.left;
      const y = e.clientY - r.top;
      // the marker layer handles its own taps first; a tap on a twin marker is not a tap on the ground
      window.setTimeout(() => {
        if (performance.now() - this.lastMarkerPick < 120) return;
        const id = this.cellAt(x, y);
        if (id != null) this.onCell(id);
      }, 0);
    });
  }

  /** The lunar cell under a canvas point, or null off the globe. */
  cellAt(x: number, y: number): number | null {
    const scene = globesApi.scene('moon');
    const p = scene.camera.pickEllipsoid(new Cartesian2(x, y), Ellipsoid.MOON);
    if (!p) return null;
    const c = Ellipsoid.MOON.cartesianToCartographic(p);
    if (!c) return null;
    return this.app.store.moonCellAt((c.latitude * 180) / Math.PI, (c.longitude * 180) / Math.PI);
  }

  /** A lunar cell was tapped: outside the zone, open the panel at its region. Returns the region code shown, if any. */
  onCell(id: number): string | null {
    const m = this.app.mission();
    if (!m || !this.active()) return null;
    const region = this.app.store.regionOfCell(id);
    if (!region || this.app.store.zoneCodes(m.id).includes(region.code)) return null;
    this.openPanel(region.code, id);
    return region.code;
  }

  // ---------- the panel ----------

  private ensureDialog(): HTMLDialogElement {
    if (this.dialog) return this.dialog;
    const d = h('dialog', { class: 'credits zone-dialog', id: 'zone-dialog', 'aria-labelledby': 'zone-title' }) as HTMLDialogElement;
    d.addEventListener('click', (e) => {
      // only a pointer click on the backdrop closes it (a keyboard click has no position)
      if (e.target !== d || e.detail === 0) return;
      const r = d.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) d.close();
    });
    document.body.append(d);
    this.dialog = d;
    return d;
  }

  closePanel(): void {
    if (this.dialog?.open) this.dialog.close();
  }

  /** Open the panel; with a region code, at that region's entry (named at the top), from a tapped cell. */
  openPanel(regionCode?: string, cellId?: number): void {
    const m = this.app.mission();
    const z = this.app.store.zones;
    if (!m || !z) return;
    const d = this.ensureDialog();
    const returnTo = document.activeElement as HTMLElement | null;
    d.replaceChildren(...this.panelContent(m, z, regionCode, cellId));
    if (!d.open) d.showModal();
    d.dataset.mission = m.id;
    d.dataset.region = regionCode ?? '';
    const target = regionCode ? (d.querySelector(`#zone-region-${regionCode} summary`) as HTMLElement | null) : null;
    if (target) {
      target.scrollIntoView({ block: 'nearest' });
      target.focus({ preventScroll: true });
    } else (d.querySelector('.zone-close') as HTMLElement | null)?.focus();
    d.addEventListener('close', () => window.setTimeout(() => returnTo?.isConnected && returnTo.focus(), 0), { once: true });
    this.app.announce(regionCode ? `Why the ${missionName(m)} test is not searched here: ${z.regions.find((r) => r.code === regionCode)?.label ?? ''}.` : `Why the ${missionName(m)} zone.`);
  }

  private panelContent(m: Mission, z: MissionZonesJson, regionCode?: string, cellId?: number): HTMLElement[] {
    const t = z.texts;
    const inZone = this.zoneRegions(m.id);
    const outside = this.outsideRegions(m.id);
    const zone = this.app.zoneName(m) ?? inZone.map((r) => r.label).join(' and ');
    const tapped = regionCode ? z.regions.find((r) => r.code === regionCode) : undefined;
    const close = h(
      'button',
      { type: 'button', class: 'btn btn-icon zone-close', 'aria-label': 'Close' },
      icon('close'),
    );
    close.addEventListener('click', () => this.closePanel());
    const head = h('div', { class: 'credits-head' }, h('h2', { id: 'zone-title' }, `Why this zone? ${missionName(m)} mission`), close);
    const body = h('div', { class: 'credits-body zone-body' });
    if (tapped) {
      const where = cellId != null ? ` (cell at ${latLonText(this.app.store.moonLatLon(cellId).lat, this.app.store.moonLatLon(cellId).lon)})` : '';
      body.append(h('p', { class: 'zone-tapped', 'data-region': tapped.code }, icon('info'), h('span', null, `You chose a point in ${tapped.label}${where}, outside this mission's search zone. Its entry is open below.`)));
    }
    append(body, [
      h('h3', { class: 'dlg-h' }, 'The search zone'),
      h('p', { class: 'zone-name' }, h('strong', null, zone), inZone.length ? ` (${inZone.map((r) => `${r.label}, ${int(r.cells)} cells`).join('; ')})` : ''),
      t?.zone_why?.[m.id] ? h('p', { 'data-text': 'zone_why' }, t.zone_why[m.id]) : null,
      t?.general_note ? h('p', { 'data-text': 'general_note' }, t.general_note) : null,
      h('h3', { class: 'dlg-h' }, 'Other parts of the Moon'),
    ]);
    const list = h('div', { class: 'zone-regions' });
    for (const r of outside) {
      const text = t?.outside?.[m.id]?.[r.code] ?? null;
      const det = h(
        'details',
        { class: 'zone-region', id: `zone-region-${r.code}`, 'data-region': r.code },
        h('summary', null, h('span', null, r.label), h('span', { class: 'muted' }, ` · ${int(r.cells)} cells`)),
        text ? h('p', { 'data-text': `outside.${r.code}` }, text) : h('p', { class: 'muted' }, 'Outside this mission\'s search zone.'),
      ) as HTMLDetailsElement;
      if (r.code === regionCode) det.open = true;
      list.append(det);
    }
    body.append(list);
    const src = h('button', { type: 'button', class: 'linklike', id: 'zone-sources' }, 'Sources of these texts (Data and limits)');
    src.addEventListener('click', () => {
      this.closePanel();
      this.app.openLimits('zones');
    });
    body.append(h('p', { class: 'zone-foot muted' }, t ? `Mission facts consulted on ${dateWords(z.consulted_on)}. ` : '', src));
    return [head, body];
  }
}
