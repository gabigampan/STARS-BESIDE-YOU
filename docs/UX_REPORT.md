# UX report: web app against the local jury's checklist (2026-11-15)

Scope: `app/` on branch `final-integration`, measured against `docs/UX_CHECKLIST.md` with the
scripted tests `app/tests/flow.mjs` (key task by mouse and keyboard, every view audited),
`app/tests/data.mjs` (every number against the bundle) and `app/tests/modules.mjs`. Bundles
tested: the shipped bundle (contract revision 6), the revision 5 bundle of this morning (kept in
the scratchpad), the no-twin fixture (`repo_global_mean`) and a zone fixture with `texts: null`.
The app decides everything from the bundle itself: the rule of each mission, whether it has twins,
the pairs file, the per-pair sentences, the zone data.

## What the product shows now

- **Pairs first.** For each mission the ranking lists the Earth places with their lunar twin
  ("Moon: near <feature>") and the final score, then a divider ("No lunar twin: N points" and one
  sentence on why, from the bundle's counts), then the points without a twin by suitability, each
  with the reason in plain words. Counts in words: "6,360 of 18,777 points have a lunar twin".
  A three-way filter (All, Paired, No twin) and a search box (magnifier) reach any point.
- **Comparison of a pair.** Headline: the lunar match and Final, Similarity, Suitability as large
  figures, then the per-pair sentence of the mission (Solar panels: sunlight above the atmosphere
  and the share lost at the Earth site; Lunar base: thermal position, not temperature, with the real
  differences), filled from the bundle. Then one block per similarity variable, key variables first:
  plain name, Earth value, lunar value, difference, tolerance with who set it, Within / Outside (tick
  or cross and the word), weight, score; for a percentile-scaled variable the positions of both
  sides and their difference in points AND both real values with the real difference (K for
  temperatures). The similarity and the final as arithmetic; the values not part of the similarity
  with their differences; the approved meaning sentence of the mission's rule.
- **A point without a twin.** "No lunar twin" and the approved reason sentence in the headline,
  suitability; no similarity, no final, no beam, no paired view; filters, suitability, the other
  missions and "Start the mission" still work.
- **Zones.** With zone data, the Moon shows the mission's search zone (light tint and outline over
  the imagery) and names it; "Why this zone?" opens the zone text, the general note and every other
  region with its text for this mission, with the consultation date and a link to the sources. A
  click or tap on a lunar cell outside the zone opens the panel at that region and names it; the
  list is reachable by keyboard (Tab, Enter).

## Checklist, measured

The table is filled from the last full test runs (see the end of this file).

| Item | How it is met | Measured |
|---|---|---|
| 01 Purpose at first sight | headline sentence and audience line; the three mission cards are the largest controls | flow.mjs "one sentence of purpose", "mission choices are the largest controls" |
| 02 Key task end to end | choose, pick (marker or row), compare, start the mission video, back at every step | flow.mjs, mouse and keyboard, 1440x900 and 375x812 |
| 03 One primary action, shared components | one `button()`, one level tag, one verdict, one `.seg` control for every segmented choice | flow.mjs counts primary buttons per view |
| 04 Text 14 px, words, 3 typefaces | `--step--1` never below 14 px; no column names, no "inf", no bracketed ranges, no Spanish class names in any view (scan) | flow.mjs audit and technical-string scan in every view |
| 05 Contrast, not colour alone | 4.5:1 against composited backgrounds; Place names toggle has a check box and "on/off"; Within/Outside and Pass/Fail carry an icon and the word | flow.mjs audit |
| 06 Touch sizes, 2 m | every control 44 x 44 px with 8 px between; headline figures 32 px and more | flow.mjs audit |
| 07 Response, errors, empty states | visible change under 100 ms or a spinner; data errors say what happened and what to do; empty list states say what to do | flow.mjs timings and forced failures |
| Red alerts | no filler, no "undefined"/"NaN"/"null", no error codes, every state has text or an icon | flow.mjs scan |
