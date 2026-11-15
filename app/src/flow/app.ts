// The product flow: choose a mission -> pick a point -> compare the pair -> start the mission.
// Owns the state, the layout step (body[data-step]), the markers, beams and paired view; the
// panels are rendered by intro.ts, missionPanel.ts and detailPanel.ts.

import { globesApi, type MarkerItem } from '../api';
import { DataError, DataStore, type RankedPoint } from '../data/store.ts';
import { pyRound2, recomputeMission, type MissionScores } from '../data/recompute.ts';
import type { Mission } from '../data/types.ts';
import { missionName } from './copy';
import { renderDataDialog, openDataDialog, renderZoneSources } from './dataDialog';
import { meaningText, renderDetail, renderDetailLoading } from './detailPanel';
import { renderIntro } from './intro';
import { anyVideo, hasVideo, loadMediaIndex, videoSpec } from './media';
import { MissionPanel } from './missionPanel';
import { renderSteps, type Step } from './steps';
import { h } from './dom';
import { ZoneView } from './zones';
import { a11y } from '../a11y';
import { onPalette } from '../a11y/palette';
import { missionLine, purposeText } from './copy';

/** Camera height over a chosen point (team lead: smooth and moderate, the region stays visible). */
const PAIR_VIEW_KM = { earth: 550, moon: 350 } as const;

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
  /** Real-value rules: similarity weights (null = the team's). */
  simWeights: number[] | null;
}

export class FlowApp {
  readonly store = new DataStore();
  readonly state: FlowState = { step: 'choose', missionId: null, selectedId: null, weights: null, alpha: null, simWeights: null };
  private dataError: string | null = null;
  private dataReady = false;
  private loadingMission: string | null = null;
  private placeCache = new Map<number, string>();
  private rankingCache = new Map<string, RankItem[]>();
  private custom: { scores: MissionScores; items: RankItem[]; rankOf: Map<number, number> } | null = null;
  private recomputeTimes: number[] = [];
  private recomputeSeq = 0;
  missionPanel!: MissionPanel;
  private readonly status = document.getElementById('flow-status') as HTMLElement;
  private readonly intro = document.getElementById('intro') as HTMLElement;
  private readonly detail = document.getElementById('detail-panel') as HTMLElement;
  private readonly moonNote = document.getElementById('moon-rule') as HTMLElement;
  private readonly stepsNav = document.getElementById('steps') as HTMLElement;
  readonly ready: Promise<void>;
  private detailSeq = 0;
  /** The mission's search zone on the Moon (revision 6 data; inactive without it). */
  readonly zones = new ZoneView(this);

  constructor() {
    document.body.classList.add('flow');
    this.setStep('choose');
    this.missionPanel = new MissionPanel(this, document.getElementById('mission-panel') as HTMLElement);
    this.renderIntro();
    this.updateGuide();
    // colour-blind mode: every overlay of the globes takes the new palette at once
    onPalette(() => {
      if (this.state.missionId && this.state.step !== 'choose') this.updateMarkers();
      this.zones.repaint();
      try {
        (globesApi.focus as unknown as { repaint?: () => void }).repaint?.();
        globesApi.scene('earth').requestRender();
        globesApi.scene('moon').requestRender();
      } catch {
        /* globes not created */
      }
    });
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
    this.updateGuide();
    if (this.dataReady) {
      renderDataDialog(this.store, (m) => this.ruleText(m), (m) => meaningText(this, m));
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
  /** The team's similarity weights of a real-value mission (empty for other rules). */
  teamSimWeights(m: Mission): number[] {
    return this.store.pairVariables(m.id).map((v) => v.weight);
  }
  simWeights(): number[] {
    const m = this.mission();
    return this.state.simWeights ?? (m ? this.teamSimWeights(m) : []);
  }
  usingCustom(): boolean {
    return this.state.weights !== null || this.state.alpha !== null || this.state.simWeights !== null;
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

  /** True when the point is in the open mission's list (ranked or passing without a twin). */
  inList(id: number): boolean {
    return this.ranking().some((r) => r.id === id);
  }

  /** The open mission has twins (its own rule decides, read from the bundle). */
  missionHasTwins(m: Mission | null = this.mission()): boolean {
    return !!m && this.store.hasTwins(m.id);
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
      this.state.simWeights = null;
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
    void this.zones.show(id).then(() => renderZoneSources(this.store));
    if (!opts.keepSelection) {
      this.viewTopEarth();
      // the chosen card is gone: keyboard focus goes to the main action of the new screen, the first ranked place
      this.missionPanel.focusFirst();
    }
    const m = this.store.mission(id);
    const c = this.store.pairCounts(id);
    if (!opts.keepSelection) this.updateGuide();
    this.announce(
      `${missionName(m)} mission chosen: ${c.passing.toLocaleString('en-GB')} places on Earth pass its filters` +
        (c.unpaired > 0 && this.missionHasTwins(m) ? `; ${c.paired.toLocaleString('en-GB')} of them have a lunar twin.` : '.'),
    );
    // Start fetching the utilities for the weight sliders in the background.
    window.setTimeout(() => void this.store.loadAllTiles().catch(() => undefined), 1500);
  }

  /** With twins, turn the Moon camera to the lunar zone that holds the mission's twins. */
  private async viewTwinZone(): Promise<void> {
    const m = this.mission();
    if (!m || !this.store.hasTwins(m.id)) return;
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
    this.zones.hide();
    this.setStep('choose');
    globesApi.resetView();
    this.renderIntro();
    (this.intro.querySelector('h2') as HTMLElement | null)?.focus();
    this.updateGuide();
    this.announce('Start screen: choose a mission with the keys 1, 2 or 3.');
  }

  // ---------- audio guide ----------

  /** The caption (and, with the guide on, the recording) of the current step. */
  updateGuide(): void {
    const g = a11y().guide;
    const m = this.mission();
    const step = this.state.step;
    if (step === 'choose' || !m) {
      const lines = this.dataReady ? this.store.offeredMissions().map((x, i) => `Press ${i + 1} for ${missionName(x)}: ${missionLine(x)}`) : [];
      g.setStep({ track: g.track('start'), title: 'Welcome', fallback: [purposeText(this.dataReady && this.store.hasTwins()), ...lines].join(' ') });
      return;
    }
    if (step === 'pick') {
      g.setStep({
        // the introduction names the five analogs: offered only when the five pair tracks match the bundle's five
        track: this.recordedFiveMatch(m) ? g.track('mission', m.id) : null,
        title: `${missionName(m)} mission`,
        fallback: `${missionName(m)}. ${missionLine(m)} Five of its analogs are listed first: press a number from 1 to 5 to open one, or Escape to go back.`,
      });
      return;
    }
    const id = this.state.selectedId;
    if (id == null) return;
    const item = this.ranking().find((r) => r.id === id);
    const twin = item?.twinId != null ? this.store.twin(m.id, item.twinId) : null;
    // a pair track plays only for the pair it was recorded for (tracks.json ids against the pair on screen)
    // ... and it holds the same place among the five (its narration says "analog n")
    const pos = this.missionPanel.topFiveItems(m).find((x) => x.id === id)?.pos;
    const rec = twin && !this.usingCustom() ? a11y().guide.pairTrack(m.id, `E${id}`, `M${twin.id}`) : null;
    const track = rec && pos != null && rec.rank === pos ? rec : null;
    const parts = [`${this.placeText(id)} on Earth.`];
    if (item?.rank != null) parts.push(`Rank ${item.rank} for the ${missionName(m)} mission${this.usingCustom() ? ' under your own weights' : ''}, final score ${item.final}.`);
    if (twin) parts.push(`Its lunar twin is ${twin.feature ? `near ${twin.feature.name}` : 'a cell of the lunar zone'}, at ${Math.abs(twin.lat).toFixed(1)}° ${twin.lat >= 0 ? 'N' : 'S'}.`);
    else parts.push('It has no lunar twin.');
    parts.push('Press Escape to go back to the list.');
    g.setStep({ track, title: pos != null ? `Analog ${pos}` : item?.rank != null ? `Rank ${item.rank}` : 'Selected place', fallback: parts.join(' ') });
  }

  /** True when the recorded pair tracks of a mission are exactly the bundle's five, place by place. */
  recordedFiveMatch(m: Mission): boolean {
    const g = a11y().guide;
    if (!this.store.hasTwins(m.id)) return false;
    const five = this.missionPanel.topFiveItems(m);
    if (five.length !== 5) return false;
    return five.every((it) => {
      const t = g.track('pair', m.id, it.pos);
      return !!t && it.twinId != null && t.earth_cell_id === `E${it.id}` && t.moon_cell_id === `M${it.twinId}`;
    });
  }

  // ---------- markers ----------

  updateMarkers(): void {
    // markers are the points with a final score (the pairs); points without a twin are in the list only
    const items = this.ranking().filter((it): it is RankItem & { final: number } => it.final != null);
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
    const earth: MarkerItem[] = items.map((it) => ({ id: it.id, lat: it.lat, lon: it.lon, score: (it.final - lo) / span, rank: it.rank ?? undefined, label: it.place }));
    globesApi.markers.setMarkers('earth', earth, { topLabels: 10 });
    if (this.state.missionId && this.store.hasTwins(this.state.missionId)) {
      // The lunar twins of the ranked points; each carries the best final of the Earth points sharing it.
      const best = new Map<number, RankItem & { final: number }>();
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
      if (typeof id !== 'number' || !this.inList(id)) return;
      void this.select(id);
    } else {
      if (!this.store.hasTwins(this.state.missionId) || typeof id !== 'number') return;
      const first = this.ranking().find((r) => r.twinId === id);
      if (first) void this.select(first.id);
    }
  }

  // ---------- weights ----------

  async setWeights(weights: number[] | null, alpha: number | null, simWeights: number[] | null = this.state.simWeights): Promise<number | null> {
    const m = this.mission();
    if (!m) return null;
    const team = this.teamWeights(m);
    const teamSim = this.teamSimWeights(m);
    const same = (a: number[] | null, ref: number[]) => !a || a.every((v, i) => v === ref[i]);
    this.state.weights = same(weights, team) ? null : weights;
    this.state.alpha = alpha === null || alpha === m.alpha ? null : alpha;
    this.state.simWeights = same(simWeights, teamSim) ? null : simWeights;
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
    const scores = recomputeMission(mat, this.weights(), this.alpha(), this.simWeights());
    const items: RankItem[] = [];
    const rankOf = new Map<number, number>();
    for (let k = 0; k < scores.list.length; k++) {
      const p = scores.list[k];
      const id = mat.ids[p];
      const lp = this.store.landPosOf(id);
      const scored = k < scores.order.length;
      if (scored) rankOf.set(id, k + 1);
      const sim = scores.similarity[p];
      items.push({
        id,
        landPos: lp,
        passPos: p,
        lat: this.store.latOf(id),
        lon: this.store.lonOf(id),
        rank: scored ? k + 1 : null,
        final: scored ? pyRound2(scores.final[p]) : null,
        suitability: scores.suitability[p],
        similarity: Number.isNaN(sim) ? null : pyRound2(sim),
        twinId: this.ranking0(m.id, p),
        scored,
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
    await this.setWeights(null, null, null);
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
    // the guide changes at once (the introduction stops, the pair's caption and track start); the panel follows
    this.updateGuide();
    const ranked = this.rankOf(id) != null;
    globesApi.markers.setSelected('earth', ranked ? id : null);
    this.zones?.closePanel();
    // The cameras leave at once for a ranked pair: its place and lunar twin are known from the ranking,
    // so the flights do not wait for the cell's data tile (the first pair of a session used to wait
    // several seconds and end the wait still at the mission's overview heights).
    const early = this.earlyPairFlight(id);
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
    this.updateGuide();
    const r = this.rankOf(id);
    this.announce(`${this.placeText(id)}: ${o.pass ? (r != null ? `rank ${r.toLocaleString('en-GB')}` : 'passes, no lunar twin') : 'eliminated for this mission'}.`);
    // the pair on the globes
    const lat = this.store.latOf(id);
    const lon = this.store.lonOf(id);
    const twin = o.pass ? o.twin : null;
    if (twin) {
      globesApi.markers.setSelected('moon', twin.id);
      globesApi.beams.setBeams([{ earth: { lat, lon }, moon: { lat: twin.lat, lon: twin.lon }, strength: 1 }]);
      // a smooth, moderate zoom on both globes: the region around each cell stays in view (a few hundred km up)
      globesApi.focus.outline('earth', this.store.cellFootprint(id));
      globesApi.focus.outline('moon', this.store.cellFootprint(twin.id));
      if (early && early.twinId === twin.id) await early.done;
      else await Promise.all([globesApi.flyTo('earth', lat, lon, PAIR_VIEW_KM.earth, 1.5), globesApi.flyTo('moon', twin.lat, twin.lon, PAIR_VIEW_KM.moon, 1.5)]);
    } else {
      globesApi.markers.setSelected('moon', null);
      globesApi.beams.clearBeams();
      if (globesApi.focus.isFocused()) await globesApi.focus.exitFocus({ durationMs: 0 });
      // No paired view: the Earth cell alone is outlined at its true 1-degree footprint.
      globesApi.focus.outline('earth', this.store.cellFootprint(id));
      this.settleLayout();
      await globesApi.flyTo('earth', lat, lon, PAIR_VIEW_KM.earth, 1.5);
    }
  }

  /** Start the pair flights for a ranked place with a known lunar twin; null when the twin is not known yet. */
  private earlyPairFlight(id: number): { twinId: number; done: Promise<unknown> } | null {
    const m = this.mission();
    const row = m ? this.ranking().find((r) => r.id === id) : undefined;
    const twin = m && row && row.twinId != null ? this.store.twin(m.id, row.twinId) : null;
    if (!twin) return null;
    const done = Promise.all([
      globesApi.flyTo('earth', row!.lat, row!.lon, PAIR_VIEW_KM.earth, 1.5),
      globesApi.flyTo('moon', twin.lat, twin.lon, PAIR_VIEW_KM.moon, 1.5),
    ]);
    return { twinId: twin.id, done };
  }

  renderDetailNow(id: number) {
    const m = this.mission()!;
    const c = this.usingCustom();
    const o = this.store.outcome(id, m.id, c ? this.weights() : undefined, c ? this.alpha() : undefined, c && this.store.isValueRule(m.id) ? this.simWeights() : undefined);
    renderDetail(this.detail, this, id, o);
    return o;
  }

  private async leaveCompare(): Promise<void> {
    globesApi.beams.clearBeams();
    globesApi.focus.outline('earth', null);
    globesApi.focus.outline('moon', null);
    globesApi.markers.setSelected('earth', null);
    globesApi.markers.setSelected('moon', null);
    if (globesApi.focus.isFocused()) await globesApi.focus.exitFocus({ durationMs: 0 });
  }

  async backToRanking(): Promise<void> {
    const id = this.state.selectedId;
    void globesApi.focus.isFocused();
    await this.leaveCompare();
    globesApi.focus.outline('moon', null);
    this.setStep('pick');
    if (true) {
      globesApi.resetView();
      void this.viewTwinZone();
      this.viewTopEarth();
    }
    this.missionPanel.render();
    // back in the list: focus returns to the row of the pair just left (its place in the list)
    if (id != null) this.missionPanel.focusRow(id);
    else this.missionPanel.focusFirst();
    this.updateGuide();
    const m = this.mission();
    if (m) this.announce(`Back to the ${missionName(m)} mission: its five analogs and the full ranking.`);
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
    const raw = m?.similarity.no_twin_reason ?? this.store.similarity.no_twin_reason ?? this.store.missionsJson.missions.find((x) => x.similarity.no_twin_reason)?.similarity.no_twin_reason ?? '';
    // never a rule's identifier on screen: a sentence that names one (snake_case) is left out
    return raw
      .split(/(?<=\.)\s+/)
      .filter((s) => !/\b[a-z]+_[a-z_]+\b/.test(s))
      .join(' ');
  }

  /** The mission's search zone name on the Moon (missions.json similarity.zone, else similarity.json target.zones). */
  zoneName(m: Mission | null = this.mission()): string | null {
    if (!m) return null;
    const t = this.store.similarity.target as { zones?: Record<string, { name?: string }> } | undefined;
    return m.similarity.zone?.name ?? t?.zones?.[m.id]?.name ?? null;
  }

  /** The true cell size in plain words (both bodies). */
  cellSizeText(): string {
    const g = this.store.manifest.grid.bodies;
    return `Each point is a 1° cell: about ${Math.round(g.EARTH.cell_ns_km)} km across on Earth and ${Math.round(g.MOON.cell_ns_km)} km on the Moon (narrower east-west towards the poles). Values are averages over the whole cell.`;
  }

  ruleText(m: Mission | null = this.mission()): string {
    if (!this.dataReady) return '';
    if (m ? this.store.hasTwins(m.id) : this.store.hasTwins()) {
      const zone = this.zoneName(m);
      return `Similarity rule: each Earth point is paired with its most similar lunar cell inside the mission's target zone${zone ? ` (${zone})` : ''}.`;
    }
    return `Similarity rule: ${this.noTwinText(m)}`;
  }

  updateMoonNote(): void {
    if (!this.dataReady) return;
    this.moonNote.replaceChildren();
    const m = this.mission();
    if (m && this.store.hasTwins(m.id)) {
      const t = this.store.twinsOf(m.id).length;
      this.moonNote.append(h('p', null, `Markers: the ${t.toLocaleString('en-GB')} lunar twins of the paired Earth points, inside ${this.zoneName(m) ?? "the mission's target zone"}.`));
    } else if (m) {
      this.moonNote.append(h('p', { 'data-verbatim': 'no_twin_reason' }, this.noTwinText()));
    }
    const zc = m ? this.zones.control(m) : null;
    if (zc) this.moonNote.append(zc);
    // the same control in the mission panel (the Moon caption is hidden on small screens)
    const slot = document.querySelector('#mission-panel [data-slot="zone"]');
    const zp = m ? this.zones.control(m, 'zone-why-panel') : null;
    slot?.replaceChildren(...(zp ? [zp] : []));
    this.updateEarthNote();
    // the marker legends of both globes, in the panel instead of over the globes
    const ms = document.querySelector('#mission-panel [data-slot="markers"]');
    const earth = document.getElementById('earth-rule');
    ms?.replaceChildren(...[earth, this.moonNote].flatMap((el) => (el ? [...el.querySelectorAll(':scope > p')].map((p) => p.cloneNode(true)) : [])));
  }

  /** The Earth-side legend of the markers (what size, brightness and the numbers mean). */
  updateEarthNote(): void {
    const el = document.getElementById('earth-rule');
    if (!el) return;
    const m = this.mission();
    el.replaceChildren();
    if (!this.dataReady || !m) return;
    const n = this.ranking().filter((r) => r.final != null).length;
    const what = this.missionHasTwins(m) ? 'places with a lunar twin' : 'ranked places';
    el.append(h('p', null, `Markers: the ${n.toLocaleString('en-GB')} ${what}; larger and brighter means a higher final score; numbers are the top 10 ranks.`));
  }

  /** Turn the Earth camera to the top of the open mission's ranking. */
  private viewTopEarth(): void {
    const top = this.ranking()[0];
    if (top) void globesApi.flyTo('earth', top.lat, top.lon, 9000, 1.2);
  }
}
