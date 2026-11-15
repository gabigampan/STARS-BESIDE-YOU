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

Last runs on this machine (4 shared CPUs, software WebGL; four suites ran in parallel at the end,
so the timeouts below are suspected starvation and must be re-run alone):

| Script | Bundle / size | Result |
|---|---|---|
| typecheck, build | - | pass |
| test:data | shipped, no-twin fixture | all passed (incl. Solar sentence = explain.json on 25 pairs, share lost agrees with the printed numbers on 500 pairs, top 5 = audio 35, 36, 38, 37, 36; Lunar base sentence = explain.json on 25 pairs) |
| test:a11y | shipped 375x812 and 812x375 (+ 768, 3840 widths) | 212 ok, 0 failed (incl. touch: pinch 9,000 km to 3,704 km, drag rotates 106.5° to 97.3°; axe clean on every screen, both palettes) |
| test:a11y | no-twin fixture 1440x900 and 375x812 | 154 ok, 0 failed |
| test:a11y | shipped 1440x900 | 91 ok and 0 failed when this report was written (still running); the earlier full run had 1 real track playing in Chromium (m1_rover.mp3, 33.0 s) |
| test:flow | shipped + fixture, desktop and phone | 522 ok; 4 Lunar base panel checks failed because the test still expected the old meaning sentence and the unrounded difference (the reviewer's findings 1 and 2): the test is updated in the last commit, not re-run; 1 "page.click timeout" in the desktop run (suspected starvation) |
| smoke | shipped | 32 ok; 1 failed: imagery did not finish within 90 s while three other browser suites ran (starvation); re-run alone |
| review.mjs | - | not run in this session |

Frame rate: this machine renders WebGL in software (SwiftShader), so no frame-rate figure measured
here says anything about 60 fps on a computer or 30 fps on a phone; not measured.

## Not done / to check

- Phone landscape (812x375): the switches, caption, top five and shortcut list fit and work (tested),
  but on the mission and pair screens the panel leaves the globes almost no height; the globes are
  shown on the start screen and when the panel is scrolled. A layout change for landscape phones is
  not done.
- After Escape from a pair, focus returns to that pair's row in the list (kept from the existing
  flow test and its checklist item) rather than to the step heading; every forward step focuses its
  heading.
- The standard palette is not colour-blind-safe by distance (numbers above); it relies on text and
  icons, and the switch provides the safe palette.
- review.mjs and a solo re-run of smoke and test:flow are pending.

---

# Round 2: reviewer findings, engine corrections, team decisions (web-accessibility, after 47474f8)

Merged `origin/final-integration` (contract revision 7: Rover on slope and roughness, the bundle's
five with 2-degree separation, notes with `show`). The web needed no per-mission change for it.

## Fixed

| Finding | Fix | Test |
|---|---|---|
| UX major 1: caption cut at three lines | caption unfolded (whole transcript) while the guide is on; folded to one or two lines with a "Full text" control (aria-expanded) when off; a very long one scrolls in a focusable box, never cut | test:a11y "whole caption is shown", "Full text unfolds" |
| UX major 2: phone first screen | compact header (switches on one row), caption folded, compact mission cards: at 375x812 the purpose and all three choices are on screen (lowest choice 711 of 812 px); at 812x375 the start screen scrolls and every choice can be brought into view | test:a11y "first screen without scrolling" |
| UX minor: header wraps at 1440 | brand line hidden below 1800 px: header 87 px, one row | test:a11y "header stays on one row" |
| UX minor + figures 2: pair track late | the guide changes as soon as a pair is chosen (introduction stopped and reset, pair track started) before the panel data arrive; a second request for a starting track is ignored | test:a11y "within 300 ms of key 1" |
| UX minor: technical leftovers | "Share of similarity in the final score (alpha)"; data error says "The mission data could not be loaded" (file name only in a short note for the team); imagery error without tile coordinates (they go to the console). The zone label "PSR" comes from the bundle (engine owner) | test:flow scans |
| UX minor: label over bright imagery | wider dark halo on the selected label, offset above the beam | visual |
| UX minor: focus on BODY at load | focus moves to the first screen's heading when the loading screen closes | - |
| Figures 1 (round 3): "Lunar twin" sentence typed per rule | the twin section only says where the twin lies; how it is chosen is the bundle's meaning text of the mission's rule | test:a11y Lunar base block |
| Figures 3: introductions for any bundle | an introduction (which names the five) plays only when all five pair tracks match the bundle's five place by place; otherwise a caption from the screen. With the current bundle: Lunar base yes, Rover and Solar panels no (their five changed) | test:a11y "no introduction plays" |
| Figures 4: rule ids in Data and limits | a sentence that names a rule identifier is left out (reported to the director) | test:a11y "no rule identifier" |
| Engine B1: Solar saturation note | shown through `show` (mission card, every Solar pair, Data and limits) | test:a11y notes |
| Engine B2: Lunar base sentence | toFixed on the stored float32 for templates without display_rule; equals explain.json on all 25 Lunar base items (and Solar 25) | test:data |
| Engine B3: level UNDOCUMENTED | only levels some variable has are listed | - |
| Engine B5: distances | the nearest-place distance is the stored float32's shortest decimal, rounded once | - |
| Decision 1: the bundle's five | `missions.json` `top5.ids` in order (fallback ranks 1 to 5); "Ranked N overall"; the rule under the five; keys 1 to 5 and pair tracks by position and cell ids | test:a11y |
| Decision 2: pending.json | listed tracks: caption with "Text only: new recording pending", never requested (even with R) | test:a11y pending block |
| Decision 3: notes with `show` | rendered in every place named, for the missions named, with no per-key code; mission-card notes behind "Limits of this list (N)" | test:a11y notes |

Three bundle notes carry file and column names; the web passes them through its plain-words
filter until the engine owner rephrases them (reported).

## Results of the final round

Filled below when the runs finish.
