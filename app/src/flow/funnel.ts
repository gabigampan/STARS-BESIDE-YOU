// The team's filter funnel in plain words. Every threshold, label, unit and alpha comes from the
// bundle (missions.json gates, require_present, alpha; similarity.json active_variables and meaning);
// the engine's own code-level wording of each step stays available in "Technical notes for reviewers".

import type { DataStore } from '../data/store.ts';
import type { Gate, Mission } from '../data/types.ts';
import { limitWords, num } from './dom';

function unit(store: DataStore, m: Mission, variable: string): string {
  return store.variable(variable)?.unit ?? m.weighted_variables.find((w) => w.variable === variable)?.unit ?? '';
}

/** One gate in words: "Solar irradiance at least 2.5 kWh/m²/day" (plus "(Earth only)" where it applies to Earth alone). */
export function gateWords(store: DataStore, m: Mission, g: Gate): string {
  const where = g.applies_to.length === 1 && g.applies_to[0] === 'EARTH' ? ' (Earth only)' : '';
  return `${store.labelOfMissionVariable(m, g.variable)} ${limitWords(g, unit(store, m, g.variable))}${where}`;
}

export interface FunnelStep {
  name: string;
  text: string;
}

/**
 * The six steps of the funnel. With a mission, steps 2 and 3 name that mission's required variables
 * and hard filters; without one, they describe them in general (the dialog lists each mission's).
 */
export function plainFunnel(store: DataStore, m: Mission | null, meaning: string, alpha: number): FunnelStep[] {
  const ref = m ?? store.missionsJson.missions[0];
  const common = ref.gates.filter((g) => g.step === 1).map((g) => gateWords(store, ref, g));
  const sim = store.similarity;
  const active = sim.active_variables.map((v) => store.similarityLabel(v).label);
  const steps: FunnelStep[] = [
    { name: 'Common filters', text: `Every mission first keeps only cells with ${common.join(' and ')}. A cell that fails one is eliminated.` },
    m
      ? { name: 'Required data', text: `${m.require_present.map((v) => store.labelOfMissionVariable(m, v)).join(', ')} must have a value. A cell where one is missing is eliminated with the reason "no data" for that variable.` }
      : { name: 'Required data', text: 'Each mission names the variables a cell must have. A cell where one is missing is eliminated with the reason "no data" for that variable.' },
    m
      ? { name: 'Mission filters', text: `${m.gates.filter((g) => g.step === 3).map((g) => gateWords(store, m, g)).join('; ')}. Failing one eliminates the cell for this mission, with the exact reason: it gets no score, no rank and no marker here, but it may pass another mission.` }
      : { name: 'Mission filters', text: "Each mission has its own hard filters (listed under each mission below). Failing one eliminates the cell for that mission, with the exact reason; it never appears in that mission's ranking or on its globe, but it may pass another mission." },
    {
      name: 'Suitability (0-100)',
      text: 'For the cells that pass, each weighted variable becomes a utility from 0 (the team\'s "bad" value) to 1 (its "good" value; a table for classes). Suitability is the weighted mean x 100. A missing weighted variable is ignored and the other weights renormalised; the coverage says how much of the weight had data.',
    },
    {
      name: 'Similarity to the Moon (0-100)',
      text: `Computed from ${active.length} variables (${active.join(', ')}) with z-scores taken separately on each body. ${meaning}`,
    },
    { name: 'Final score', text: `Final = alpha x similarity + (1 - alpha) x suitability, with alpha = ${num(alpha, 2)}. The cells that pass are ranked by the final score.` },
  ];
  return steps;
}
