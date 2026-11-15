#!/usr/bin/env node
// Data store test (no browser): reads the bundle exactly as the page does (src/data/store.ts,
// imported directly by Node's type stripping) and checks, for every passing Earth cell of every
// offered mission, that the browser recompute reproduces the stored suitability, similarity,
// final and rank (docs/DATA_CONTRACT.md "Recompute formulas"). Runs on the shipped bundle and, when
// present, on the no-twin variant (repo_global_mean).
// Usage: node tests/data.mjs [--bundle=DIR ...]   (default: public/data/v2 and $OTHER_BUNDLE)

import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DataStore, DataError } from '../src/data/store.ts';
import { pyRound2, npRound2, recomputeMission, suitabilityOf } from '../src/data/recompute.ts';

const APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// The no-twin variant (rule repo_global_mean), kept outside public/data.
const OTHER =
  process.env.OTHER_BUNDLE ??
  '/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/bundle_global_mean';
const args = process.argv.filter((a) => a.startsWith('--bundle=')).map((a) => a.slice(9));
const bundles = args.length ? args : [join(APP, 'public/data/v2'), ...(existsSync(OTHER) ? [OTHER] : [])];

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
  check(store.hasTwins() === (rule === 'zone_twin'), 'twins detected from the bundle itself');
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
    const mat = store.matrix(m.id);
    const t1 = performance.now();
    const sc = recomputeMission(mat, w, m.alpha);
    const ms = performance.now() - t1;
    let badS = 0, badSim = 0, badF = 0, badR = 0, badCov = 0;
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
    if (store.hasTwins()) {
      const tw = store.twinsOf(m.id);
      const sum = tw.reduce((s, t) => s + t.earth_cells, 0);
      check(sum === m.ranked_count, `${m.id}: twins.json earth_cells add up to the ranked count (${sum})`);
      const s1 = store.twinSharingText(m.id, tw[0].earth_cells);
      check(!!s1 && !/\bN\b|\bX\b/.test(s1) && (m.id === 'lunar_base') === /lunar base zone/.test(s1), `${m.id}: sharing sentence "${s1}"`);
    }
    if (examples.length) console.log('     ' + examples.join('; '));
    console.log(`     ${m.id}: recompute of ${n} cells took ${ms.toFixed(1)} ms in Node`);

    // the funnel of a top, a middle and an eliminated cell
    const ranked = store.ranked(m.id);
    const top = ranked[0], mid = ranked[Math.floor(ranked.length / 2)];
    for (const [tag, pt] of [['top', top], ['middle', mid]]) {
      await store.prepareCell(pt.id);
      const o = store.outcome(pt.id, m.id);
      check(o.pass && o.rank === pt.rank && o.final === pt.final && o.gates.every((g) => g.pass) && o.common.every((g) => g.pass), `${m.id} ${tag} cell ${pt.id}: passes every gate, rank ${o.rank}, final ${o.final}`);
      const pts = o.breakdown.reduce((s, r) => s + (r.points ?? 0), 0);
      check(Math.abs(pts - (o.suitability ?? NaN)) < 1e-9, `${m.id} ${tag}: points add up to the suitability (${pts.toFixed(4)})`);
      if (store.hasTwins()) check(o.twin != null && o.twin.id === pt.twinId && o.twin.feature != null, `${m.id} ${tag}: twin ${o.twin?.id} near ${o.twin?.feature?.name}`);
      if (m.id === 'lunar_base') check(o.ice != null, `${m.id} ${tag}: ice component present (pass ${o.ice?.pass})`);
    }
    const elimPos = md.failBits.findIndex((b) => b !== 0);
    const elimId = store.landId(elimPos);
    await store.prepareCell(elimId);
    const eo = store.outcome(elimId, m.id);
    check(!eo.pass && eo.rank == null && eo.final == null && eo.line.length > 0, `${m.id} eliminated cell ${elimId}: "${eo.line}"`);
  }

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
