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

---

# Accessibility layer and phone pass (web-accessibility branch, 2026-11-15, second web session)

First measurement by the web developer; the independent reviewer measures again. Commits on
`web-accessibility` from 8a2fdcf onwards. Numbers below are from `npm run test:a11y`
(`app/tests/a11y.mjs`), `npm run test:data`, `npm run smoke` and `npm run test:flow` on this machine
(software WebGL, 4 shared CPUs).

## What was built

- **Two sliding switches in the header, on every screen and width**: "Audio guide" and
  "Colour-blind mode" (`src/a11y/switches.ts`). Native `<button role="switch">`, `aria-checked`
  kept in step, the label and the words On / Off beside a track whose thumb slides; Tab reaches them,
  Space and Enter toggle; at least 44 x 44 px and 8 px from neighbours; both off by default and
  remembered in `localStorage` (a browser without storage still works for the page).
- **One audio player** (`src/a11y/audio.ts`): the only `<audio>` element; welcome track on the
  start screen, the mission introduction when a mission is chosen, the pair track when one of the
  top five is opened, and only when the pair on screen has the cell ids the track was recorded for
  (`public/audio/tracks.json`, from `docs/AUDIO_TOP5.json`). Starting a track pauses and rewinds the
  previous one. Off: nothing sounds, no file requested. The caption (under the steps) is the
  transcript from `public/audio/transcripts.json`, character for character, with the state in
  words (Playing, Paused, Finished, Text only, Press R to play, Audio not available: text shown) and
  a Repeat control. No audio is generated, synthesised or edited anywhere; no speech synthesis.
- **Captions and screen readers**: the caption is not a live region; the single live region
  (`#flow-status`) announces each step in one sentence, so nothing is read twice and the recording
  and the screen reader do not talk over each other on the same text.
- **Keyboard guide** (`src/a11y/keys.ts`): 1, 2, 3 choose a mission (each card shows "Press 1"
  ... with a key cap); the mission panel starts with **the five best analogs** (five large numbered
  buttons with the Earth place, its lunar twin and the final score; the team's ranks 1 to 5 read
  from the bundle; with the user's own weights the panel says so); 1 to 5 open them; Escape goes
  back one step (a dialog closes first); R repeats the audio (the view reset moved to Home, as the
  reviewer asked); `?` and the "Keys" button open the shortcut list. Shortcuts never fire with a
  modifier, in the search field, on a slider, select or radio group, or while a dialog is open.
  Focus goes to the heading of each new step.
- **Colour-blind mode** (`src/a11y/palette.ts`): every interface colour and every globe overlay
  (marker score ramp, selection ring, beam, zone fill and outline, cell outlines, focus ring,
  buttons, badges, switch) behind named tokens with two palettes; the safe one uses the Okabe-Ito
  colours (Okabe and Ito, Color Universal Design, https://jfly.uni-koeln.de/color/), cited in the
  README and in Data and limits, with the audio credit.
- **Data**: the Solar panels `{loss_pct}` rule `share_lost_of_displayed_tenths` implemented exactly
  (by rule name, not by mission); the Solar sentence is back on all 6,360 pairs. Lunar base per-pair
  sentences are filled with `toFixed` on the stored float32 as the contract says (they now equal the
  engine's `explain.json` on all 25 published pairs; before, 2 differed by 0.1).
- **Reviewer findings fixed**: (1) Lunar base pairs now show the bundle's
  `similarity_meaning_lunar_base` (chosen by the mission's rule, never a default); (2) Lunar base
  percentile rows print the difference computed from the two positions as printed (integer tenths,
  half up), while Within / Outside stays decided on the true values; (3) "1 Earth point" in the
  singular. (4) R no longer resets the views.
- **Phones**: compact header at 375 px (both switches on one row, the page name kept as the h1 for
  screen readers), caption in two lines; tests take every fixture folder from an environment variable
  with defaults in `app/.fixtures/` (git-ignored); the no-twin fixture was built here with the engine
  (`python -m engine build --similarity-rule repo_global_mean`).

## Colour checks (culori 4.0.2 simulation, Machado 2009; CIEDE2000; WCAG contrast)

| Palette | Lowest text contrast | Lowest CIEDE2000 between colours that must be told apart, under protanopia / deuteranopia / tritanopia |
|---|---|---|
| Colour-blind (Okabe-Ito) | 8.31:1 (accent on panel) | accent vs warning 50.0, ramp low vs high 51.4, selection ring vs top marker 43.9, zone outline vs beam 50.0, switch on vs off 19.8: all >= 10 (GO) |
| Standard | 8.52:1 (warning on panel) | accent vs warning 6.4, ring vs top marker 2.6, zone vs beam 3.0 (below 10: the standard palette relies on text, icons and size; that is why the switch exists) |

Every state carries text or an icon in both palettes (switch On/Off words, caption state words,
Within/Outside with tick or cross and the word, key caps with numbers).

## Checklist, first measurement (both palettes)

| Item | Result | Measurement |
|---|---|---|
| 01 Purpose at first sight | GO | start screen sentence + audience line; the three mission cards are the largest controls, each with its key hint |
| 02 Main flow, back and forward, step known | GO | keys 1-3, 1-5 and Escape at every step on both bundles, 1440x900, 375x812, 812x375 (test:a11y); step indicator unchanged |
| 03 One main action, repeated parts alike | GO | top five and switches use one implementation each |
| 04 Legibility 14 px, words, 3 typefaces | GO | type scale unchanged (min 14 px); new text in plain English |
| 05 Contrast and colour, greyscale | GO | lowest contrast 8.31:1; nothing by colour alone (see above); axe-core colour-contrast clean on every screen in both palettes |
| 06 Touch sizes and spacing | GO for the new controls | switches, Repeat, top-five buttons >= 44 px, switches 8 px or more from neighbours at 375, 768, 1440, 3840 |
| 07 Response, errors, empty | GO | 404 on the MP3 files: caption + "Audio not available: text shown", no error on screen or in the console; 404 on transcripts.json: caption built from the screen |
| Red alerts | GO | no filler, no technical text in the new parts; Keys button and both switches work on every screen |

## Test results

See the final runs below (filled at the end of the session).
