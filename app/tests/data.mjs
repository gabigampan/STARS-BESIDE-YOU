#!/usr/bin/env node
// Data store test (no browser): reads the bundle exactly as the page does (src/data/store.ts,
// imported directly by Node's type stripping) and checks, for every passing Earth cell of every
// offered mission, that the browser recompute reproduces the stored suitability, similarity,
// final and rank (docs/DATA_CONTRACT.md "Recompute formulas"), for the rule of each mission as the
// bundle states it: z-scores (zone_twin, repo_global_mean) or real values within tolerances
// (revision 5: per-variable scores, pairs file, points without a twin listed after the pairs). Also the
// per-pair sentences, the no-twin sentences, the slider recompute with other weights, and the zone
// data of revision 6 when present. Runs on the shipped bundle, the no-twin variant (repo_global_mean)
// and the zone fixture (when present).
// Usage: node tests/data.mjs [--bundle=DIR ...]   (default: public/data/v2 and $OTHER_BUNDLE)

import * as FX from './lib/fixtures.mjs';
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DataStore, DataError, ceil2 } from '../src/data/store.ts';
import { pyRound2, npRound2, recomputeMission, suitabilityOf } from '../src/data/recompute.ts';
import { plainText } from '../src/flow/copy.ts';

const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// The no-twin variant (rule repo_global_mean), kept outside public/data.
const OTHER =
  FX.NO_TWIN_BUNDLE;
const args = process.argv.filter((a) => a.startsWith('--bundle=')).map((a) => a.slice(9));
const ZONES = FX.ZONE_FIXTURE;
// the revision 5 bundle as shipped this morning (kept to prove the app still reads it)
const REV5 = FX.REV5_BUNDLE;
const bundles = args.length ? args : [join(APP, 'public/data/v2'), ...[OTHER, REV5, ZONES].filter((d) => existsSync(d))];
// Technical strings that must never reach the interface (column names, interval notation, code)
const TECHNICAL = /[a-z0-9]_[a-z0-9]|\binf\b|\bNaN\b|\bundefined\b|\bnull\b|\[[^\]]*,[^\]]*\]|\.json\b|\.py\b|\{[a-z_]+\}/;

const failures = [];
const ok = (m) => console.log(`ok   ${m}`);
const fail = (m) => {
  failures.push(m);
  console.log(`FAIL ${m}`);
};
const check = (c, m) => (c ? ok(m) : fail(m));

const fileFetcher = (dir) => async (url) => {
  const p = join(dir, url.replace(/^.*\//, ''));
  try {
    const buf = await readFile(p);
    return {
      ok: true,
      status: 200,
      json: async () => JSON.parse(buf.toString('utf8')),
      arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
    };
  } catch {
    return { ok: false, status: 404, statusText: 'Not Found', json: async () => null, arrayBuffer: async () => new ArrayBuffer(0) };
  }
};

// rounding helpers against known Python / numpy results
check(pyRound2(0.125) === 0.12 && pyRound2(0.375) === 0.38 && pyRound2(2.675) === 2.67 && pyRound2(1.005) === 1, 'pyRound2 matches Python round(x, 2) on exact and inexact halves');
check(npRound2(0.125) === 0.12 && npRound2(0.025) === 0.02 && npRound2(0.375) === 0.38 && npRound2(0.135) === 0.14, 'npRound2 matches numpy.round(x, 2) on halves');

for (const dir of bundles) {
  console.log(`\n== bundle ${dir}`);
  const store = new DataStore('data/v2/', fileFetcher(dir));
  await store.loadStart();
  const rule = store.similarity.rule;
  console.log(`     rule ${rule}, twins ${store.hasTwins()}`);
  check(store.missionsJson.offered_missions.join(',') === 'rover,solar,lunar_base', 'exactly the three offered missions, in order (rover, solar, lunar_base)');
  for (const id of store.missionsJson.offered_missions) {
    const e = store.manifest.files.find((f) => f.name === store.mission(id).files.EARTH);
    const col = !!e.columns.some((c) => c.name === 'twin');
    check(store.hasTwins(id) === col, `${id}: rule ${store.ruleOf(id)}, twins ${store.hasTwins(id)} (decided from the bundle's own columns)`);
  }
  check(store.manifest.contract_revision >= 4, `contract revision ${store.manifest.contract_revision}`);
  const firstView = store.manifest.load.first_view.reduce((s, n) => s + (store.manifest.files.find((f) => f.name === n)?.bytes ?? 0), 0);
  check(firstView <= store.manifest.sizes.budget.first_view_max, `first view ${firstView} bytes within the bundle's budget`);
  const t0 = performance.now();
  await store.loadAllTiles();
  await store.loadTwins();
  console.log(`     all detail tiles loaded in ${(performance.now() - t0).toFixed(0)} ms`);

  for (const m of store.offeredMissions()) {
    const md = await store.loadMission(m.id);
    const n = md.landIndex.length;
    check(n === m.pass_counts.EARTH && n === store.manifest.counts.missions[m.id].pass_EARTH, `${m.id}: ${n} passing cells as missions.json and the manifest say`);
    const passFromBits = md.failBits.reduce((s, b) => s + (b === 0 ? 1 : 0), 0);
    check(passFromBits === n, `${m.id}: fail_bits = 0 exactly for the passing cells (${passFromBits})`);
    const w = m.weighted_variables.map((x) => x.weight);
    const valueRule = store.isValueRule(m.id);
    const sw = store.pairVariables(m.id).map((v) => v.weight);
    const mat = store.matrix(m.id);
    const t1 = performance.now();
    const sc = recomputeMission(mat, w, m.alpha, sw);
    const ms = performance.now() - t1;
    let badS = 0, badSim = 0, badF = 0, badR = 0, badCov = 0, badL = 0;
    const examples = [];
    for (let p = 0; p < n; p++) {
      const st = store.storedScores(m.id, p);
      const s = Number.isNaN(sc.suitability[p]) ? null : pyRound2(sc.suitability[p]);
      if (s !== st.suitability) { badS++; if (examples.length < 3) examples.push(`suit p${p} ${s} vs ${st.suitability}`); }
      const sim = store.recomputeSimilarity(m.id, md.landIndex[p]);
      if (sim !== st.similarity) { badSim++; if (examples.length < 6) examples.push(`sim p${p} ${sim} vs ${st.similarity}`); }
      const f = Number.isNaN(sc.final[p]) ? null : pyRound2(sc.final[p]);
      if (f !== st.final) { badF++; if (examples.length < 9) examples.push(`final p${p} ${f} vs ${st.final}`); }
      if ((sc.ranks[p] || null) !== st.rank) badR++;
      // coverage through the generic function too
      const u = mat.utilities.map((col) => (Number.isNaN(col[p]) ? null : col[p]));
      if (Math.abs(suitabilityOf(u, w).coverage - sc.coverage[p]) > 1e-12) badCov++;
    }
    check(badS === 0, `${m.id}: suitability recomputed exactly on all ${n} cells (${badS} differ)`);
    check(badSim === 0, `${m.id}: similarity recomputed from z-scores exactly on all ${n} cells (${badSim} differ)`);
    check(badF === 0, `${m.id}: final recomputed exactly on all ${n} cells (${badF} differ)`);
    check(badR === 0, `${m.id}: rank recomputed exactly on all ${n} cells (${badR} differ)`);
    check(badCov === 0, `${m.id}: coverage identical through both code paths`);
    // the whole list: ranked points by rank, then the points without a twin by suitability
    const lo = md.pairs?.cols['list_order'];
    const ranked0 = store.ranked(m.id);
    if (lo) sc.list.forEach((p, k) => { if (lo[p] !== k + 1) badL++; });
    ranked0.forEach((r, k) => { if (sc.list[k] !== r.passPos) badL++; });
    check(badL === 0 && ranked0.length === n, `${m.id}: list order recomputed exactly (${lo ? 'equals list_order of the pairs file' : 'ranked, then unranked by suitability'}) on all ${n} points`);
    const paired = ranked0.filter((r) => r.final != null).length;
    check(paired === m.ranked_count && n - paired === (m.passing_without_similarity ?? 0), `${m.id}: ${paired} points with a final, ${n - paired} without a twin (missions.json ${m.ranked_count} / ${m.passing_without_similarity})`);
    check(ranked0.findIndex((r) => r.final == null) === -1 || ranked0.slice(ranked0.findIndex((r) => r.final == null)).every((r) => r.final == null), `${m.id}: every point without a twin comes after every paired point`);
    // slider recompute with other weights: the browser path against a direct computation per cell
    {
      const w2 = w.map((x, i) => (i === 0 ? Math.min(1, x + 0.15) : x));
      const sw2 = sw.map((x, i) => (i === sw.length - 1 ? Math.min(1, x + 0.3) : x));
      const a2 = 0.65;
      const sc2 = recomputeMission(mat, w2, a2, sw2);
      let bad2 = 0;
      for (let p = 0; p < n; p++) {
        const lp = md.landIndex[p];
        const o = store.outcome(store.landId(lp), m.id, w2, a2, valueRule ? sw2 : undefined);
        const f = Number.isNaN(sc2.final[p]) ? null : pyRound2(sc2.final[p]);
        if (f !== o.final) bad2++;
        if (valueRule) {
          const sim = store.recomputeSimilarity(m.id, lp, sw2);
          if ((Number.isNaN(sc2.similarity[p]) ? null : pyRound2(sc2.similarity[p])) !== sim) bad2++;
        }
      }
      check(bad2 === 0, `${m.id}: sliders (suitability ${valueRule ? ', similarity' : ''} and alpha moved) recompute every passing point the same way in the list and in the panel (${bad2} differ)`);
    }
    if (valueRule) {
      // revision 5: per-pair sentences and no-twin sentences
      let badPair = 0, badNo = 0, sentences = 0;
      const tpl = store.textFor('no_twin_note', m.id);
      const tplOf = (kind) => tpl.variants?.[kind] ?? (kind === 'no_joint_match' ? tpl.variant_no_joint_match : tpl.text);
      for (let p = 0; p < n; p++) {
        const r = ranked0.find((x) => x.passPos === p);
        const ps = store.pairSentencesAt(m.id, p);
        const np = store.noPairAt(m.id, p);
        if (r.final != null) {
          if (np) badNo++;
          sentences += ps.length;
          for (const x of ps) if (/\{|\}|NaN|undefined/.test(x.text)) badPair++;
          const rows = store.pairRowsAt(m.id, p);
          if (rows.some((row) => row.def.role === 'key' && row.within !== true)) badPair++;
        } else {
          if (!np || !np.sentence || /\{|\}/.test(np.sentence) || !np.sentence.startsWith(tplOf(np.kind).slice(0, 20))) badNo++;
          if (ps.length) badPair++;
        }
      }
      check(badNo === 0, `${m.id}: every point without a twin has the filled no-twin sentence, no paired point has one`);
      const perPair = Object.entries(store.similarity.texts ?? {}).filter(([, t]) => (t.missions ?? []).includes(m.id) && Object.values(t.placeholders ?? {}).some((x) => typeof x === 'object')).length;
      check(badPair === 0 && sentences === perPair * paired, `${m.id}: ${sentences} per-pair sentences filled (${perPair} per pair), every key variable within its tolerance`);
      const un = ranked0.find((r) => r.final == null);
      if (un) console.log(`     ${m.id}: first point without a twin, cell ${un.id}: "${store.noPairAt(m.id, un.passPos).sentence}"`);
      const top = ranked0[0];
      const ps = store.pairSentencesAt(m.id, top.passPos);
      if (ps.length) console.log(`     ${m.id}: per-pair sentence of the top pair: "${ps[0].text}"`);
      // the per-pair sentences equal the ones the engine wrote in explain.json (where it has them)
      const explain = existsSync(join(dir, 'explain.json')) ? JSON.parse(await readFile(join(dir, 'explain.json'), 'utf8')) : null;
      const items = explain?.missions?.[m.id] ?? [];
      let cmp = 0, diff = 0;
      for (const it of items) {
        const want = it.similarity?.pair_sentence;
        if (typeof want !== 'string') continue;
        const r = ranked0.find((x) => x.id === it.id);
        const got = r ? store.pairSentencesAt(m.id, r.passPos).map((x) => x.text) : [];
        cmp++;
        if (!got.includes(want)) {
          diff++;
          if (diff <= 2) console.log(`     ${m.id} cell ${it.id}: web "${got[0]}" / engine "${want}"`);
        }
      }
      if (cmp) check(diff === 0, `${m.id}: the per-pair sentence equals the engine's in explain.json on all ${cmp} published pairs (${diff} differ)`);
      // the share lost agrees with the two numbers printed beside it (contract 2026-11-15), on a sample of 500 pairs
      const tplLoss = store.similarity.texts?.solar_limitation?.placeholders?.loss_pct;
      if (tplLoss && typeof tplLoss === 'object' && tplLoss.rule && (store.similarity.texts.solar_limitation.missions ?? []).includes(m.id)) {
        const pairedPos = ranked0.filter((r) => r.final != null).map((r) => r.passPos);
        const stepK = Math.max(1, Math.floor(pairedPos.length / 500));
        let n500 = 0, bad500 = 0;
        for (let k = 0; k < pairedPos.length && n500 < 500; k += stepK) {
          n500++;
          const t = store.pairSentencesAt(m.id, pairedPos[k]).find((x) => x.key === 'solar_limitation')?.text ?? '';
          const mm = /only ([0-9.]+) of those ([0-9.]+) kWh.*?\((\d+) % is lost/.exec(t);
          if (!mm) { bad500++; continue; }
          const G = Math.round(Number(mm[1]) * 10), A = Math.round(Number(mm[2]) * 10);
          if (Math.floor((200 * (A - G) + A) / (2 * A)) !== Number(mm[3])) bad500++;
        }
        check(n500 >= Math.min(500, pairedPos.length) && bad500 === 0, `${m.id}: on a sample of ${n500} pairs the share lost agrees with the two printed numbers (${bad500} differ)`);
        // and the top 5 carry the same percentage as the team's recorded audio (transcripts.json)
        const tr = existsSync(join(APP, 'public/audio/transcripts.json')) ? JSON.parse(await readFile(join(APP, 'public/audio/transcripts.json'), 'utf8')) : null;
        if (tr && dir === join(APP, 'public/data/v2')) {
          // the bundle's five (missions.json top5.ids, revision 7), else ranks 1 to 5
          const ids5 = m.top5?.ids;
          const top5 = ids5?.length ? ids5.map((id) => ranked0.find((r) => r.id === id)).filter(Boolean) : ranked0.filter((r) => r.rank != null && r.rank <= 5).sort((a, b) => a.rank - b.rank);
          const got = top5.map((r) => /\((\d+) % is lost/.exec(store.pairSentencesAt(m.id, r.passPos).find((x) => x.key === 'solar_limitation')?.text ?? '')?.[1] ?? '?');
          const heard = top5.map((r, i) => /(\d+) percent (?:less|is lost)/.exec(tr[`solar_${i + 1}.mp3`] ?? '')?.[1] ?? '?');
          check(got.length === 5 && got.join() === heard.join(), `${m.id}: the top 5 sentences carry the same share lost as the recorded audio (${got.join(', ')} / audio ${heard.join(', ')})`);
        }
      }
    }
    if (!valueRule) {
    // revision 4: the per-pair variable count and missing bits agree with the z-scores used
    const F = store.similarity.active_variables;
    const tb = store.tempBit();
    let badUsed = 0, marked = 0, markedOutside = 0;
    const svu = md.table.cols['sim_vars_used'];
    for (let p = 0; p < n; p++) {
      const lp = md.landIndex[p];
      const o = store.outcome(store.landId(lp), m.id);
      const used = o.similarityRows.filter((r) => r.earth.z != null && r.moon.z != null).length;
      if (svu && svu[p] !== used) badUsed++;
      const mt = store.missingTempAt(m.id, p);
      if (mt) { marked++; if (store.latOf(store.landId(lp)) > -60) markedOutside++; }
      if (mt !== o.similarityRows.some((r) => r.sv.variable === 'temp_k' && (r.earth.z == null || r.moon.z == null))) badUsed++;
    }
    check(!!svu && badUsed === 0, `${m.id}: sim_vars_used and the temp_k bit (${tb} of ${F.join(',')}) agree with the z-scores on all ${n} cells`);
    console.log(`     ${m.id}: ${marked} pairs marked "${store.text('missing_temperature_mark')}" (${markedOutside} north of 60 S)`);
    }
    if (store.hasTwins(m.id)) {
      const tw = store.twinsOf(m.id);
      const sum = tw.reduce((s, t) => s + t.earth_cells, 0);
      check(sum === m.ranked_count, `${m.id}: twins.json earth_cells add up to the ranked count (${sum})`);
      const s1 = store.twinSharingText(m.id, tw[0].earth_cells);
      const firstOnly = /first sentence only, for every mission/i.test(store.similarity.texts.twin_sharing_note.where);
      check(!!s1 && !/\bN\b|\bX\b/.test(s1) && (!firstOnly && m.id === 'lunar_base') === /lunar base zone/.test(s1), `${m.id}: sharing sentence "${s1}"`);
    }
    // the known limitations reach the interface in plain words
    const techLims = m.known_limitations.map((l) => plainText(store, l, m)).filter((t) => TECHNICAL.test(t));
    check(techLims.length === 0, `${m.id}: known limitations in plain words${techLims.length ? ': ' + techLims[0].slice(0, 160) : ''}`);
    if (examples.length) console.log('     ' + examples.join('; '));
    console.log(`     ${m.id}: recompute of ${n} cells took ${ms.toFixed(1)} ms in Node`);

    // the funnel of a top, a middle and an eliminated cell
    const ranked = store.ranked(m.id).filter((r) => r.final != null);
    const top = ranked[0], mid = ranked[Math.floor(ranked.length / 2)];
    for (const [tag, pt] of [['top', top], ['middle', mid]]) {
      await store.prepareCell(pt.id);
      const o = store.outcome(pt.id, m.id);
      check(o.pass && o.rank === pt.rank && o.final === pt.final && o.gates.every((g) => g.pass) && o.common.every((g) => g.pass), `${m.id} ${tag} cell ${pt.id}: passes every gate, rank ${o.rank}, final ${o.final}`);
      const pts = o.breakdown.reduce((s, r) => s + (r.points ?? 0), 0);
      check(Math.abs(pts - (o.suitability ?? NaN)) < 1e-9, `${m.id} ${tag}: points add up to the suitability (${pts.toFixed(4)})`);
      if (store.hasTwins(m.id)) check(o.twin != null && o.twin.id === pt.twinId && o.twin.feature != null, `${m.id} ${tag}: twin ${o.twin?.id} near ${o.twin?.feature?.name}`);
      if (m.id === 'lunar_base') check(o.ice != null, `${m.id} ${tag}: ice component present (pass ${o.ice?.pass})`);
    }
    const elimPos = md.failBits.findIndex((b) => b !== 0);
    const elimId = store.landId(elimPos);
    await store.prepareCell(elimId);
    const eo = store.outcome(elimId, m.id);
    check(!eo.pass && eo.rank == null && eo.final == null && eo.line.length > 0, `${m.id} eliminated cell ${elimId}: "${eo.line}"`);
  }

  // revision 6 zone data (or its fixture): regions, the zone of each mission, the texts
  if (store.hasZones()) {
    const z = await store.loadZones();
    const total = z.regions.reduce((s, r) => s + r.cells, 0);
    check(total === 64800, `zones: ${z.regions.length} regions cover the ${total} lunar cells`);
    const byCode = new Map(z.regions.map((r) => [r.code, 0]));
    for (let id = 0; id < 64800; id++) { const r = store.regionOfCell(id); if (r) byCode.set(r.code, byCode.get(r.code) + 1); }
    check(z.regions.every((r) => byCode.get(r.code) === r.cells), 'zones: the region column of moon_base.bin agrees with the region counts');
    for (const m of store.offeredMissions()) {
      const mask = store.zoneMask(m.id);
      const inZone = mask.reduce((s, v) => s + v, 0);
      const want = m.similarity.zone?.cells ?? store.similarity.target.zones?.[m.id]?.cells;
      check(want == null || inZone === want, `zones: ${m.id} zone = regions ${store.zoneCodes(m.id).join('+')} = ${inZone} cells (${want ?? 'no zone count in missions.json'})`);
      if (z.texts) {
        const outside = z.regions.filter((r) => !store.zoneCodes(m.id).includes(r.code));
        check(!!z.texts.zone_why[m.id] && outside.every((r) => typeof z.texts.outside[m.id]?.[r.code] === 'string'), `zones: ${m.id} has its zone text and a text for each of the ${outside.length} regions outside`);
      }
    }
  } else console.log('     no zone data in this bundle (revision 6 adds mission_zones.json)');

  // the no-twin gap is shown with 2 decimals rounded up, never as the bound itself
  check(ceil2(Math.fround(30.02)) === 30.02 && ceil2(Math.fround(0.6563)) === 0.66 && ceil2(Math.fround(1002.5862)) === 1002.59, 'gap rounding: 30.02 -> 30.02, 0.6563 -> 0.66, 1002.5862 -> 1002.59');

  // a missing data file gives a plain-words error
  const broken = new DataStore('data/v2/', async (url) => (url.endsWith('similarity.json') ? { ok: false, status: 404, statusText: 'Not Found', json: async () => null, arrayBuffer: async () => new ArrayBuffer(0) } : fileFetcher(dir)(url)));
  try {
    await broken.loadStart();
    fail('a missing similarity.json is reported');
  } catch (e) {
    check(e instanceof DataError && /similarity\.json/.test(e.message) && /reload/i.test(e.message), `missing file reported: "${e.message}"`);
  }
}

console.log(failures.length ? `\n${failures.length} failure(s)` : '\nall data checks passed');
process.exit(failures.length ? 1 : 0);
