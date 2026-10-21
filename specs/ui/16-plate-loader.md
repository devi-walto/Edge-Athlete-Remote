# Feature Spec 16: The plate loader on the rack screen

- Owner: Devin Walton
- Date: 2026-10-21
- Status: Written — not started. Built with the UI redesign.
- Form item: #11 (unified interface; internal)
- Depends on: [06 Design rules](06-design-rules.md); [09 Analytics](09-analytics.md) adds
  the other per-movement setting kept in our catalog (mean or peak velocity)
- Mockup: `F_Rack_Plates1` to `F_Rack_Plates5` (the athlete's phone) and
  `F_Rack_Plates6` (the gym rack tablet) on the canvas's Final designs page (approved
  2026-10-21). The two flows' Ready boards, `F_Rack_L2` and `F_Ath_R5`, show it too. The proposals they came from are on the "Remote athlete view
  (proposed)" page.

## Why

Before a set, the rack screen shows the movement and its load ("Back Squat · 225 lb").
The athlete then works out at the rack which plates go on each side: take away the bar,
halve it, and pick the plates. It's slow, it's where mistakes happen, and it's worse
with an odd load or a kilogram gym. The screen already knows the load, so it can show
the plates.

## User story

As an athlete at the rack, I want to see which plates go on each side of the bar for
the set I'm about to start, so I can load it without doing the maths.

## Decisions (Devin, 2026-10-21)

- **Where:** on the screen before a set (Ready), inside the "Up now" card, under the
  load. **Both versions**: the gym rack tablet and the athlete's phone use the same
  rack screen, so they get the same widget.
- **What it shows: one side of the bar, seen from the side.** The right-hand end of the
  bar comes in from the card's left edge and stops just past the last plate; the plates
  stand on it, centred in the card, heaviest nearest the middle of the bar (the order
  they go on). Each plate's weight is written just above it.
- **Sizes look like real plates:** the big bumpers share one height (they share one
  diameter in real life) and differ in thickness; change plates are shorter, but drawn
  bold enough to sit next to the bumpers.
- **Compact:** the label ("Each side · 45 lb bar") and the unit pill share one short
  row; there is no separate "45 + 25 a side" line, because the numbers above the plates
  already say it. Both items of "Rest of today" stay in view.
- **Pounds by default. Tapping anywhere on the card switches between pounds and
  kilograms**; the small LB | KG pill only shows which one is on. **The choice is
  remembered on that tablet or phone** until it's tapped again. A school-wide setting
  can come later.
- **One standard plate set per school**, not editable for now (a coach setting would
  add clutter for little gain):

  | | Bar | Plates |
  |---|---|---|
  | Pounds | 45 lb | 45, 35, 25, 10, 5, 2.5 |
  | Kilograms | 20 kg | 25, 20, 15, 10, 5, 2.5, 1.25 |

- **Colours follow the standard convention, the same for everyone.** Kilogram plates
  use the international weightlifting code, where each colour means a number and change
  plates repeat it at a tenth: red 25 / 2.5, blue 20, yellow 15, green 10, white 5. The
  1.25 kg plate isn't in that code; it's drawn silver, as most gyms have it. Pounds have
  no official code; pound bumpers borrow the colour of the nearest kilogram plate:

  | Pounds | Colour | Kilograms | Colour |
  |---|---|---|---|
  | 45 | blue | 25 | red |
  | 35 | yellow | 20 | blue |
  | 25 | green | 15 | yellow |
  | 10 | white | 10 | green |
  | 5, 2.5 | dark grey | 5 | white |
  | | | 2.5 | red |
  | | | 1.25 | silver |

- **A load that can't be made exactly shows the closest one, with a warning** in amber:
  "137.5 lb can't be loaded exactly. Showing 140 lb, the closest". In kilograms the load
  is converted from the prescription in pounds and loaded from kilogram plates on a
  20 kg bar: "185 lb is 83.9 kg. 85 kg is the closest". A load exactly halfway between
  two goes to the heavier one (137.5 lb shows 140, as on `F_Rack_Plates4`).
- **It hides** when the movement isn't loaded on a barbell, and when the set has no
  load. A load equal to the bar shows the bare bar ("Empty bar"); a load below the bar
  hides the plates and says so.
- **It follows the load live:** when the athlete changes the weight at the rack (the ✎
  beside Load), the plates change at once.

## What exists today

- `react/src/rack/RackScreen.jsx` shows the load on the Ready screen from the athlete's
  own change at the rack, else their last weight, else the prescription
  (`weightOverrides`, `last_weight_lbs`, `target_weight_lbs`). The same value is saved
  as the set's `weight_lbs`. `WeightPad.jsx` is the editor behind the ✎.
- Loads are stored in pounds everywhere.
- The movement catalog (`Exercise`) has no record of what a movement is lifted with.
  Our built-in list is migration `0009`'s starter catalog: all barbell movements.

## Scope

- One field on `Exercise`, kept by us: **lifted on a barbell**, yes or no.
- The plate maths, in the browser, for pounds and kilograms.
- The widget on the Ready screen, in both versions.

## Non-goals

- Editing the plate set or bar per school, per rack, or per athlete (later, if asked).
- Other bars (a 35 lb or 15 kg bar, a trap bar), dumbbells, machines.
- Converting what is saved: loads stay in pounds; the kilogram view is for loading the
  bar only.

---

## Phase 0 — Which movements use a barbell

- `Exercise` gains **`barbell`** (yes or no), kept by us like spec 09's velocity metric:
  yes for every movement in the built-in catalog (all of them are barbell lifts today),
  set by hand for any we add later. Coaches don't see it.
- A movement a coach or an import creates starts as **no**, so the widget never shows
  plates for a dumbbell row. A coach setting can come later if coaches miss it.
- The rack screen's movement data carries it.

**Done when:**

- [ ] The migration marks the built-in catalog as barbell, and nothing else.
- [ ] The rack screen's data for a movement includes `barbell`.
- [ ] Full suite passes in both modes.

## Phase 1 — The plate maths

`react/src/rack/plates.js`, plain functions, no screen:

- `platesForLoad(loadLb, unit)` returns the bar, the plates for one side (heaviest
  first), the total actually loaded, and whether it differs from what was asked.
- In kilograms, the pound load is converted (1 lb = 0.45359237 kg) before loading.
- The closest load: half of (load − bar) rounded to the nearest step of the smallest
  plate (2.5 lb, 1.25 kg; a tie goes heavier), then the plates chosen heaviest first.
  With these standard sets that is always the fewest plates, and always loadable.

**Done when:**

- [ ] *(Unit test)* 225 lb → 45, 45 a side; 185 → 45, 25; 75 → 10, 5; 45 → empty bar.
- [ ] *(Unit test)* 137.5 lb (exactly halfway) → 140 (45, 2.5 a side), flagged as not
      exact; 136 lb → 135; 139 lb → 140.
- [ ] *(Unit test)* 185 lb in kg → 85 kg (25, 5, 2.5 a side), flagged as not exact.
- [ ] *(Unit test)* No load, or a load below the bar, gives nothing to show.

## Phase 2 — The widget

`react/src/rack/PlateLoader.jsx`, built to `F_Rack_Plates1` to `6`, placed in the
Ready screen's "Up now" card under the load.

- The whole card is one button: tapping anywhere on it switches the unit. It reads
  aloud as "Plates for each side: 45, 25 pounds. Tap to switch pounds and kilograms".
- The unit is kept in the browser's own storage (one key, `plate_unit`), so it survives
  reloads on that device; if storage isn't available it just starts in pounds.
- It reads the same load the screen shows, so a change at the rack moves the plates.

**Done when:**

- [ ] *(Frontend test)* The plates drawn match `platesForLoad` for the shown load, in
      order, with each weight above its plate.
- [ ] *(Frontend test)* Tapping anywhere on the card switches the unit; a reload keeps
      it.
- [ ] *(Frontend test)* Changing the load at the rack changes the plates at once.
- [ ] *(Frontend test)* No plates for a movement that isn't a barbell lift, or with no
      load; the warning appears only when the load can't be made exactly.
- [ ] *(Frontend test)* The gym rack screen and the athlete's phone both show it.
- [ ] *(Browser)* On a phone and on a rack tablet, both "Rest of today" rows stay in
      view with the widget showing.

**Stop. Devin reviews.**

---

## Acceptance criteria

- [ ] Before every barbell set, both versions show the plates for one side of the bar.
- [ ] Pounds by default; one tap anywhere on the card switches to kilograms, and the
      device remembers.
- [ ] A load that can't be made exactly shows the closest, with a warning.
- [ ] The plates follow a change of load at the rack.
- [ ] Nothing about what is saved changes.

## Risks

| Risk | What reduces it |
|---|---|
| A gym's plates aren't the standard set (no 35s, or extra change plates) | The closest-load warning is honest about what it assumed; a per-school set is a small later change to one list |
| An athlete trusts a kilogram load that's 1.25 kg off the prescription | The warning names both numbers every time it isn't exact |
| A coach-created barbell movement shows no plates | Starts as "no" on purpose; we mark it in the catalog, or a coach setting comes later |
