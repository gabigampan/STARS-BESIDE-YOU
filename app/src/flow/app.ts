// The product flow: choose a mission -> pick a point -> compare the pair -> start the mission.
// Owns the state, the layout step (body[data-step]), the markers, beams and paired view; the
// panels are rendered by intro.ts, missionPanel.ts and detailPanel.ts.

import { globesApi, type MarkerItem } from '../api';
import { DataError, DataStore, type RankedPoint } from '../data/store.ts';
import { pyRound2, recomputeMission, type MissionScores } from '../data/recompute.ts';
import type { Mission } from '../data/types.ts';
import { missionName } from './copy';
import { renderDataDialog, openDataDialog } from './dataDialog';
import { meaningText, renderDetail, renderDetailLoading } from './detailPanel';
import { renderIntro } from './intro';
import { anyVideo, hasVideo, loadMediaIndex, videoSpec } from './media';
import { MissionPanel } from './missionPanel';
import { renderSteps, type Step } from './steps';
import { h } from './dom';

export interface RankItem extends RankedPoint {
  place: string;
}

export interface FlowState {
  step: Step;
  missionId: string | null;
  selectedId: number | null;
  /** null = the team's weights / alpha. */
  weights: number[] | null;
  alpha: number | null;
}

export class FlowApp {
  readonly store = new DataStore();
  readonly state: FlowState = { step: 'choose', missionId: null, selectedId: null, weights: null, alpha: null };
  private dataError: string | null = null;
  private dataReady = false;
  private loadingMission: string | null = null;
  private placeCache = new Map<number, string>();
  private rankingCache = new Map<string, RankItem[]>();
  private custom: { scores: MissionScores; items: RankItem[]; rankOf: Map<number, number> } | null = null;
  private recomputeTimes: number[] = [];
  private recomputeSeq = 0;
  private missionPanel!: MissionPanel;
  private readonly status = document.getElementById('flow-status') as HTMLElement;
  private readonly intro = document.getElementById('intro') as HTMLElement;
  private readonly detail = document.getElementById('detail-panel') as HTMLElement;
  private readonly moonNote = document.getElementById('moon-rule') as HTMLElement;
  private readonly stepsNav = document.getElementById('steps') as HTMLElement;
  readonly ready: Promise<void>;
  private detailSeq = 0;

  constructor() {
    document.body.classList.add('flow');
    this.setStep('choose');
    this.missionPanel = new MissionPanel(this, document.getElementById('mission-panel') as HTMLElement);
    this.renderIntro();
    this.ready = this.start();
  }

  // ---------- start ----------

  private async start(): Promise<void> {
    await Promise.all([
      loadMediaIndex(),
      this.store.loadStart().catch((e: unknown) => {
        this.dataError = e instanceof DataError ? e.message : `The mission data could not be read (${e instanceof Error ? e.message : String(e)}). Reload the page to try again.`;
      }),
    ]);
    this.dataReady = !this.dataError;
    if (this.dataReady) document.body.classList.toggle('has-twins', this.store.hasTwins());
    this.renderIntro();
    this.renderSteps();
    if (this.dataReady) {
      renderDataDialog(this.store, this.ruleText(), meaningText(this));
      // Place names for the list come next; they are small and needed as soon as a mission is open.
      this.store.loadPlaceDetail().then(
        () => {
          this.placeCache.clear();
          this.rankingCache.clear();
          if (this.state.step === 'pick') this.refreshRanking();
        },
        () => undefined,
      );
    }
    await globesApi.ready;
    globesApi.markers.onPick((body, id) => this.onPick(body, id));
  }

  // ---------- accessors for the panels and tests ----------

  hasData(): boolean {
    return this.dataReady;
  }
  error(): string | null {
    return this.dataError;
  }
  loading(): string | null {
    return this.loadingMission;
  }
  mission(): Mission | null {
    return this.state.missionId ? this.store.mission(this.state.missionId) : null;
  }
  teamWeights(m: Mission): number[] {
    return m.weighted_variables.map((w) => w.weight);
  }
  weights(): number[] {
    const m = this.mission();
    return this.state.weights ?? (m ? this.teamWeights(m) : []);
  }
  alpha(): number {
    return this.state.alpha ?? this.mission()?.alpha ?? this.store.missionsJson.alpha;
  }
  usingCustom(): boolean {
    return this.state.weights !== null || this.state.alpha !== null;
  }
  lastRecomputeMs(): number | null {
    return this.recomputeTimes.length ? this.recomputeTimes[this.recomputeTimes.length - 1] : null;
  }
  recomputeLog(): number[] {
    return [...this.recomputeTimes];
  }

  placeText(id: number): string {
    let t = this.placeCache.get(id);
    if (t === undefined) {
      const p = this.store.place(this.store.landPosOf(id));
      t = p.text ?? 'Unnamed land cell';
      this.placeCache.set(id, t);
    }
    return t;
  }

  /** The current ranking of the open mission (stored, or recomputed with the user's weights). */
  ranking(): RankItem[] {
    const id = this.state.missionId;
    if (!id) return [];
    if (this.custom) return this.custom.items;
    let r = this.rankingCache.get(id);
    if (!r) {
      r = this.store.ranked(id).map((p) => ({ ...p, place: this.placeText(p.id) }));
      this.rankingCache.set(id, r);
    }
    return r;
  }

  rankOf(id: number): number | null {
    if (this.custom) return this.custom.rankOf.get(id) ?? null;
    return this.ranking().find((r) => r.id === id)?.rank ?? null;
  }

  missionHasVideo(): boolean {
    const m = this.mission();
    return !!m && hasVideo(m);
  }

  // ---------- steps and layout ----------

  private setStep(step: Step): void {
    this.state.step = step;
    document.body.dataset.step = step;
    const panes = [document.getElementById('earth-pane'), document.getElementById('moon-pane')];
    for (const p of panes) p?.toggleAttribute('inert', step === 'choose');
    this.intro.hidden = step !== 'choose';
    (document.getElementById('mission-panel') as HTMLElement).hidden = step !== 'pick';
    this.detail.hidden = step !== 'compare';
    this.renderSteps();
    this.settleLayout();
  }

  private settleLayout(): void {
    try {
      for (const b of ['earth', 'moon'] as const) {
        globesApi.viewer(b).resize();
        globesApi.scene(b).requestRender();
      }
    } catch {
      /* globes not created yet */
    }
  }

  renderSteps(): void {
    const m = this.mission();
    const any = this.dataReady ? this.store.offeredMissions().some((x) => hasVideo(x)) : anyVideo();
    renderSteps(this.stepsNav, {
      step: this.state.step,
      withVideo: m ? hasVideo(m) : any,
      missionName: m ? missionName(m) : null,
      canPick: !!m,
      canCompare: this.state.selectedId != null,
      go: (s) => this.goToStep(s),
    });
  }

  goToStep(s: Step | 'video'): void {
    if (s === 'choose') void this.changeMission();
    else if (s === 'pick' && this.state.missionId) void this.backToRanking();
    else if (s === 'compare' && this.state.selectedId != null) void this.select(this.state.selectedId);
    else if (s === 'video') void this.startMission();
  }

  private renderIntro(): void {
    renderIntro(this.intro, this);
  }

  announce(text: string): void {
    this.status.textContent = '';
    window.setTimeout(() => (this.status.textContent = text), 30);
  }

  // ---------- choose ----------

  async chooseMission(id: string, opts: { keepSelection?: boolean } = {}): Promise<void> {
    if (!this.dataReady) return;
    this.loadingMission = id;
    this.renderIntro();
    this.missionPanel.renderLoading(this.store.mission(id));
    try {
      await this.store.loadMission(id);
    } catch (e) {
      this.loadingMission = null;
      this.dataError = null;
      this.renderIntro();
      this.missionPanel.renderError(e instanceof Error ? e.message : String(e), () => void this.chooseMission(id, opts));
      return;
    } finally {
      this.loadingMission = null;
    }
    const changed = this.state.missionId !== id;
    this.state.missionId = id;
    if (changed) {
      this.state.weights = null;
      this.state.alpha = null;
      this.custom = null;
    }
    await this.store.loadTwins().catch(() => undefined);
    if (!opts.keepSelection) {
      this.state.selectedId = null;
      await this.leaveCompare();
      this.setStep('pick');
      globesApi.resetView();
      void this.viewTwinZone();
    }
    this.missionPanel.render();
    this.updateMarkers();
    this.renderIntro();
    if (!opts.keepSelection) {
      this.viewTopEarth();
      // the chosen card is gone: keyboard focus goes to the main action of the new screen, the first ranked place
      this.missionPanel.focusFirst();
    }
    const m = this.store.mission(id);
    this.announce(`${missionName(m)} mission chosen: ${this.ranking().length} places on Earth pass its filters.`);
    // Start fetching the utilities for the weight sliders in the background.
    window.setTimeout(() => void this.store.loadAllTiles().catch(() => undefined), 1500);
  }

  /** With twins, turn the Moon camera to the lunar zone that holds the mission's twins. */
  private async viewTwinZone(): Promise<void> {
    const m = this.mission();
    if (!m || !this.store.hasTwins()) return;
    const twins = this.store.twinsOf(m.id);
    if (!twins.length) return;
    const rad = Math.PI / 180;
    let x = 0, y = 0, z = 0;
    for (const t of twins) {
      x += Math.cos(t.lat * rad) * Math.cos(t.lon * rad);
      y += Math.cos(t.lat * rad) * Math.sin(t.lon * rad);
      z += Math.sin(t.lat * rad);
    }
    const r = Math.hypot(x, y, z) || 1;
    const lat = Math.asin(z / r) / rad;
    const lon = Math.atan2(y, x) / rad;
    const c = [Math.cos(lat * rad) * Math.cos(lon * rad), Math.cos(lat * rad) * Math.sin(lon * rad), Math.sin(lat * rad)];
    let spread = 0;
    for (const t of twins) {
      const v = [Math.cos(t.lat * rad) * Math.cos(t.lon * rad), Math.cos(t.lat * rad) * Math.sin(t.lon * rad), Math.sin(t.lat * rad)];
      spread = Math.max(spread, Math.acos(Math.min(1, v[0] * c[0] + v[1] * c[1] + v[2] * c[2])));
    }
    const km = spread * this.store.manifest.grid.bodies.MOON.radius_km;
    await globesApi.flyTo('moon', lat, lon, Math.max(500, 2.6 * km), 1.2);
  }

  async changeMission(): Promise<void> {
    await this.leaveCompare();
    this.state.selectedId = null;
    globesApi.markers.clearMarkers('earth');
    globesApi.markers.clearMarkers('moon');
    this.setStep('choose');
    globesApi.resetView();
    this.renderIntro();
    (this.intro.querySelector('.choice[aria-pressed="true"], .choice') as HTMLElement | null)?.focus();
  }

  // ---------- markers ----------

  updateMarkers(): void {
    const items = this.ranking();
    if (!items.length) {
      globesApi.markers.clearMarkers('earth');
      globesApi.markers.clearMarkers('moon');
      return;
    }
    let lo = Infinity;
    let hi = -Infinity;
    for (const it of items) {
      lo = Math.min(lo, it.final);
      hi = Math.max(hi, it.final);
    }
    const span = hi - lo || 1;
    const earth: MarkerItem[] = items.map((it) => ({ id: it.id, lat: it.lat, lon: it.lon, score: (it.final - lo) / span, rank: it.rank, label: it.place }));
    globesApi.markers.setMarkers('earth', earth, { topLabels: 10 });
    if (this.store.hasTwins() && this.state.missionId) {
      // The lunar twins of the ranked points; each carries the best final of the Earth points sharing it.
      const best = new Map<number, RankItem>();
      for (const it of items) if (it.twinId != null && !best.has(it.twinId)) best.set(it.twinId, it);
      const moon: MarkerItem[] = [];
      for (const [tid, it] of best) {
        const t = this.store.twin(this.state.missionId, tid);
        if (!t) continue;
        moon.push({ id: tid, lat: t.lat, lon: t.lon, score: (it.final - lo) / span, label: t.feature ? `near ${t.feature.name}` : undefined });
      }
      globesApi.markers.setMarkers('moon', moon, { topLabels: 0 });
    } else globesApi.markers.clearMarkers('moon');
    if (this.state.selectedId != null) globesApi.markers.setSelected('earth', this.rankOf(this.state.selectedId) ? this.state.selectedId : null);
  }

  private onPick(body: 'earth' | 'moon', id: string | number): void {
    if (this.state.step === 'choose' || !this.state.missionId) return;
    if (body === 'earth') {
      if (typeof id !== 'number' || this.rankOf(id) == null) return;
      void this.select(id);
    } else {
      if (!this.store.hasTwins() || typeof id !== 'number') return;
      const first = this.ranking().find((r) => r.twinId === id);
      if (first) void this.select(first.id);
    }
  }

  // ---------- weights ----------

  async setWeights(weights: number[] | null, alpha: number | null): Promise<number | null> {
    const m = this.mission();
    if (!m) return null;
    const team = this.teamWeights(m);
    const same = (a: number[] | null) => !a || a.every((v, i) => v === team[i]);
    this.state.weights = same(weights) ? null : weights;
    this.state.alpha = alpha === null || alpha === m.alpha ? null : alpha;
    const seq = ++this.recomputeSeq;
    if (!this.usingCustom()) {
      this.custom = null;
      this.afterRecompute(0);
      return 0;
    }
    if (!this.store.allTilesLoaded()) {
      this.missionPanel.setRecomputeStatus('loading');
      try {
        await this.store.loadAllTiles();
      } catch (e) {
        this.missionPanel.setRecomputeStatus('error', e instanceof Error ? e.message : String(e));
        return null;
      }
      if (seq !== this.recomputeSeq) return null;
    }
    const t0 = performance.now();
    const mat = this.store.matrix(m.id);
    const scores = recomputeMission(mat, this.weights(), this.alpha());
    const items: RankItem[] = [];
    const rankOf = new Map<number, number>();
    for (let k = 0; k < scores.order.length; k++) {
      const p = scores.order[k];
      const id = mat.ids[p];
      const lp = this.store.landPosOf(id);
      rankOf.set(id, k + 1);
      items.push({
        id,
        landPos: lp,
        passPos: p,
        lat: this.store.latOf(id),
        lon: this.store.lonOf(id),
        rank: k + 1,
        final: pyRound2(scores.final[p]),
        suitability: scores.suitability[p],
        similarity: mat.similarity[p],
        twinId: this.ranking0(m.id, p),
        simVarsUsed: null,
        missingTemp: this.store.missingTempAt(m.id, p),
        place: this.placeText(id),
      });
    }
    this.custom = { scores, items, rankOf };
    this.afterRecompute(t0);
    return this.lastRecomputeMs();
  }

  private ranking0(missionId: string, passPos: number): number | null {
    const md = this.store.missionDataOf(missionId);
    if (!md.twin) return null;
    const t = md.twin[passPos];
    return t === this.store.manifest.encoding.int32_missing ? null : t;
  }

  /** List, markers and (when open) the comparison, all from the new ranking; t0 = start of the recompute. */
  private afterRecompute(t0: number): void {
    this.missionPanel.renderList();
    this.updateMarkers();
    if (t0) this.recomputeTimes.push(performance.now() - t0);
    this.missionPanel.setRecomputeStatus(this.usingCustom() ? 'custom' : 'team', this.lastRecomputeMs() ?? undefined);
    if (this.state.step === 'compare' && this.state.selectedId != null) this.renderDetailNow(this.state.selectedId);
  }

  async resetWeights(): Promise<void> {
    await this.setWeights(null, null);
    this.missionPanel.render();
    this.announce("Weights reset to the team's values.");
  }

  refreshRanking(): void {
    this.missionPanel.renderList();
    this.updateMarkers();
  }

  // ---------- compare ----------

  async select(id: number, missionId?: string): Promise<void> {
    if (missionId && missionId !== this.state.missionId) {
      // visible response at once while the other mission loads (checklist 07)
      renderDetailLoading(this.detail, this, id);
      await this.chooseMission(missionId, { keepSelection: true });
    }
    const m = this.mission();
    if (!m) return;
    const seq = ++this.detailSeq;
    this.state.selectedId = id;
    this.setStep('compare');
    const ranked = this.rankOf(id) != null;
    globesApi.markers.setSelected('earth', ranked ? id : null);
    if (!this.store.isTileLoaded(this.store.tileIndexOf(id)) || !this.store.offeredMissions().every((x) => this.store.isMissionLoaded(x.id))) {
      renderDetailLoading(this.detail, this, id);
    }
    try {
      await this.store.prepareCell(id);
    } catch (e) {
      if (seq !== this.detailSeq) return;
      renderDetailLoading(this.detail, this, id, e instanceof Error ? e.message : String(e), () => void this.select(id));
      return;
    }
    if (seq !== this.detailSeq) return;
    const o = this.renderDetailNow(id);
    (this.detail.querySelector('h2') as HTMLElement | null)?.focus({ preventScroll: true });
    this.announce(`${this.placeText(id)}: ${o.pass ? `rank ${this.rankOf(id)}` : 'eliminated for this mission'}.`);
    // the pair on the globes
    const lat = this.store.latOf(id);
    const lon = this.store.lonOf(id);
    const twin = o.pass ? o.twin : null;
    if (twin) {
      globesApi.markers.setSelected('moon', twin.id);
      globesApi.beams.setBeams([{ earth: { lat, lon }, moon: { lat: twin.lat, lon: twin.lon }, strength: 1 }]);
      await globesApi.focus.focusPair({
        earth: { lat, lon, cell: this.store.cellFootprint(id) },
        moon: { lat: twin.lat, lon: twin.lon, cell: this.store.cellFootprint(twin.id) },
      });
    } else {
      globesApi.markers.setSelected('moon', null);
      globesApi.beams.clearBeams();
      if (globesApi.focus.isFocused()) await globesApi.focus.exitFocus({ durationMs: 0 });
      // No paired view: the Earth cell alone is outlined at its true 1-degree footprint.
      globesApi.focus.outline('earth', this.store.cellFootprint(id));
      this.settleLayout();
      await globesApi.flyTo('earth', lat, lon, 2600, 1.2);
    }
  }

  renderDetailNow(id: number) {
    const m = this.mission()!;
    const o = this.store.outcome(id, m.id, this.usingCustom() ? this.weights() : undefined, this.usingCustom() ? this.alpha() : undefined);
    renderDetail(this.detail, this, id, o);
    return o;
  }

  private async leaveCompare(): Promise<void> {
    globesApi.beams.clearBeams();
    globesApi.focus.outline('earth', null);
    globesApi.markers.setSelected('earth', null);
    globesApi.markers.setSelected('moon', null);
    if (globesApi.focus.isFocused()) await globesApi.focus.exitFocus({ durationMs: 0 });
  }

  async backToRanking(): Promise<void> {
    const id = this.state.selectedId;
    const wasTwin = globesApi.focus.isFocused();
    await this.leaveCompare();
    this.setStep('pick');
    if (!wasTwin) {
      globesApi.resetView();
      void this.viewTwinZone();
      this.viewTopEarth();
    }
    this.missionPanel.render();
    if (id != null) this.missionPanel.focusRow(id);
  }

  async startMission(): Promise<void> {
    const m = this.mission();
    const spec = m ? videoSpec(m) : null;
    if (!spec) return;
    const opener = document.activeElement as HTMLElement | null;
    document.body.dataset.video = 'open';
    this.renderSteps();
    await globesApi.video.openVideo(spec);
    delete document.body.dataset.video;
    this.renderSteps();
    opener?.focus();
  }

  openLimits(missionId?: string): void {
    openDataDialog(missionId);
  }

  /** Why there is no twin, verbatim from the bundle (the mission's similarity.no_twin_reason, else similarity.json's). */
  noTwinText(m: Mission | null = this.mission()): string {
    return m?.similarity.no_twin_reason ?? this.store.similarity.no_twin_reason ?? this.store.missionsJson.missions.find((x) => x.similarity.no_twin_reason)?.similarity.no_twin_reason ?? '';
  }

  /** The true cell size in plain words (both bodies). */
  cellSizeText(): string {
    const g = this.store.manifest.grid.bodies;
    return `Each point is a 1° cell: about ${Math.round(g.EARTH.cell_ns_km)} km across on Earth and ${Math.round(g.MOON.cell_ns_km)} km on the Moon (narrower east-west towards the poles). Values are averages over the whole cell.`;
  }

  ruleText(): string {
    if (!this.dataReady) return '';
    if (this.store.hasTwins()) {
      const m = this.mission();
      const zone = m?.similarity.zone?.name;
      return `Similarity rule: each Earth point is paired with its most similar lunar cell inside the mission's target zone${zone ? ` (${zone})` : ''}.`;
    }
    return `Similarity rule: ${this.noTwinText()}`;
  }

  updateMoonNote(): void {
    if (!this.dataReady) return;
    this.moonNote.replaceChildren();
    if (this.store.hasTwins()) {
      const m = this.mission();
      if (!m) return;
      const t = this.store.twinsOf(m.id).length;
      this.moonNote.append(h('p', null, `Markers: the ${t} lunar twins of the ranked Earth points, inside ${m.similarity.zone?.name ?? "the mission's target zone"}.`));
    } else {
      this.moonNote.append(h('p', { 'data-verbatim': 'no_twin_reason' }, this.noTwinText()));
    }
    this.updateEarthNote();
  }

  /** The Earth-side legend of the markers (what size, brightness and the numbers mean). */
  updateEarthNote(): void {
    const el = document.getElementById('earth-rule');
    if (!el) return;
    const m = this.mission();
    el.replaceChildren();
    if (!this.dataReady || !m) return;
    const n = this.ranking().length;
    el.append(h('p', null, `Markers: the ${n.toLocaleString('en-GB')} ranked places; larger and brighter means a higher final score; numbers are the top 10 ranks.`));
  }

  /** Turn the Earth camera to the best-ranked places of the open mission. */
  private viewTopEarth(): void {
    const top = this.ranking()[0];
    if (top) void globesApi.flyTo('earth', top.lat, top.lon, 9000, 1.2);
  }
}
