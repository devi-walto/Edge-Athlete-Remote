# Feature Spec 19: The rack screen

- Owner: Devin Walton
- Date: 2026-11-11
- Status: Phase 0 built (2026-11-12), awaiting review. Two decisions are still proposed (see
  "Still to confirm")
- Form item: #11 (unified interface; internal)
- Depends on: [06 Design rules](06-design-rules.md) (done). Nothing else: it can start any
  time, and alongside [10 The athlete's pages](../remote/10-athlete-pages.md), whose files it
  doesn't touch
- Mockups: the gym rack row on the canvas's Final designs page: `F_Rack_NoSession`,
  `F_Rack_L1` to `F_Rack_L6` (with the corner switch on `F_Rack_L1`),
  `F_Rack_SwitchToDisplay`, `F_Display`, `F_Display_SwitchToRack`; the plate loader's
  `F_Rack_Plates1` to `F_Rack_Plates6`. The athlete's room display button has no board yet
  (Phase 6)

## Why

The rack screen is the one screen every athlete uses on every set: the gym's rack tablet
and an online athlete's phone run the same `react/src/rack/RackScreen.jsx` (spec 04 Phase 3).
Several changes to it were decided over October, but each was written into a different
spec: the plate loader (spec 16), only the planned reps counting and each rep's feedback
(spec 09, the coach's Analytics spec, which comes last), the waiting screen and the corner
switch (spec 18, on an unmerged branch), and the athlete's room display button (spec 10).
Built that way, the one screen would be changed four times in four pull requests, and the
rep-counting work would wait behind the whole coach redesign.

This spec gathers every rack screen change into one place, in the order an athlete feels
them, for **both the local install and the remote server** (Devin, 2026-11-11).

## User stories

- As an athlete at a rack before the session starts, I want the screen to say it's ready
  and waiting, so I know nothing is broken.
- As an athlete lifting, I want to see the moment each rep counts, and know when I've done
  the reps the plan asked for, so I lift normally and stop when the work is done.
- As an athlete about to start a set, I want to see which plates go on each side of the bar,
  so I load it without doing the maths.
- As a coach setting up the gym, I want to flip a tablet between a rack and the room display
  from the tablet itself.

## Decisions this spec locks in

Carried over unchanged from the specs they were written in; each phase names where.

- **One screen, both versions.** Every change here lands in `RackScreen.jsx` and its
  pieces, so the gym tablet and the athlete's phone get it together. Where a change is for
  one version only, the phase says so.
- **The rack screen keeps its own look** (spec 06 rule 8): big, readable from the bar.
  Its colours already come from `styles/tokens.css` through `theme.js` (spec 06 Phase 0).
- **No session running: the rack says it's ready and waiting** (spec 18, approved
  2026-10-27, `F_Rack_NoSession`, local and remote).
- **Only the planned reps count** (Devin, 2026-10-27; was spec 09). The sensor sends every
  rep; the server decides which count and keeps them all. The first N count, N being the
  reps planned for that athlete and movement; no planned reps, nothing is capped.
- **The screen answers "did that one count?" as each rep lands** (Devin, 2026-10-30; was
  spec 09 on `feature-rep_counting`): the count pulses lime on a counted rep; a rep that
  won't count shows greyed with its reason. The speed keeps its zone colour.
- **The plate loader** (spec 16, approved 2026-10-21): one side of the bar, before each
  barbell set, pounds by default, one remembered lb / kg choice per device shared with the
  athlete's pages.
- **The corner switch** (spec 18, approved 2026-10-27): a small button in the idle rack
  screen's corner flips the tablet to the room display and back, asking first.
- **An athlete may open the room display** online, read-only; its button is on their rack
  screen only while their session is live (was spec 10 Phase 6).
- **The footer stays word for word** (`phase`, `node`, `buffered`): it's how you see reps
  are being kept on the device (spec 04 Phase 3).

## Still to confirm (proposed, Devin to decide before the phase that needs it)

1. **A rep too slow to be real doesn't count** (Phase 1): mean velocity under 0.15 m/s. On
   the first sensor, picking the board up or putting it down sent "reps" of 0.08 to
   0.13 m/s; even a very heavy barbell rep is faster. Such a rep doesn't use up one of the
   N, so lifting the bar out of the rack can't push the real last rep past the cap.
2. **The feedback means "that rep counted", not "stop / go"** (Phase 2). A stop / go light
   teaches lifters to pause for the sensor; they should lift the way they always do.

## What exists today

- `react/src/rack/RackScreen.jsx` (the phases: idle, ready, countdown, active, summary,
  rest), `Idle.jsx`, `CheckInList.jsx`, `WeightPad.jsx`, `velocity.js`; a rack picks up a
  new session on its own (PR #14).
- Reps arrive through the live rack state; a rep sent twice is counted once (spec 14
  Phase 4). `Rep` has no "counts" field; `POST /api/sets/<id>/complete/` takes the
  tablet's `reps_completed` and velocities.
- `target_reps` per movement is already on the rack's plan (`plan_resolution.py`).
- The local install chooses a tablet's job on "Set up this device" and changes it from the
  room display's cog ("Change device role").
- Online, `/dashboard` needs a coach login.

## Scope

- The waiting screen; rep counting on the server and on the screen; the plate loader; the
  corner switch on a local install; the room display for athletes online.

## Non-goals

- The common login and rack tablets online (spec 18). The corner switch online comes with it.
- The sensor's own light answering each rep (later, below).
- Editing plate sets; other bars; a speed-based max.

---

## Phase 0 — No session running

Built to `F_Rack_NoSession` (spec 18's approved board), local and remote.

- A rack with no session running shows **"No session yet"** in the header, and in place of
  the empty check-in list: **"Rack 3 is ready · Waiting for today's session"**, with "A coach
  starts it from the coach app. This screen updates on its own, then shows who can check
  in." and a small chip saying the sensor is live.
- The NFC prompt is hidden in this state only, since nobody can check in yet.
- When a coach starts a session, the check-in list replaces it on its own (the tablet
  already picks up a new session).

**Done when:**

- [x] *(Frontend test)* With no session, the rack shows the waiting message and no
      check-in list or NFC prompt; with a session, the list is back.
- [x] *(Browser)* Local ~~and remote~~: a coach starts a session and the check-in list replaces
      the message within 5 seconds, with no reload. (Remote has no gym rack tablet until
      spec 18, and an athlete's own rack never shows this screen; the same code serves both.)

**Phase 0 result (2026-11-12).** `rack/NoSession.jsx` to `F_Rack_NoSession`: the header reads
"No session yet" (muted), and in place of the empty list "Rack 3 is ready · Waiting for
today's session" with the board's line. The rack screen keeps asking for a session every
5 seconds as before, so the check-in list replaces it by itself; the wristband reader rests
while waiting. The sensor chip is the shared `ui/Badge`: "Sensor rack_3 is live" (mint
dot) while the sensor pulses, "Sensor rack_3 not responding" (amber) after 15 seconds
without one, "No sensor linked to this rack" when none is. It listens to the sensor's own
pulse (`edgeathlete/node/<id>/pulse`, which browsers may already read), held by the rack
screen the whole time, so coming back to this screen after a session never starts from a
stale guess. The two not-live wordings are mine; the board drew only the live one. The
corner switch on the board is Phase 5. Footer unchanged. An athlete's own rack is untouched.
Tests: frontend 7 in `rack/noSession.test.jsx`. Browser, a throwaway local install at
375 px with the simulated sensor on rack 1: waiting screen as on the board; session started
→ the list in about 1 second; session ended with the sensor on → waiting with "is live"
straight away; sensor switched off → "not responding".

**Stop. Devin reviews.**

## Phase 1 — Only the planned reps count (the server)

Moved from spec 09 ("Added 2026-10-27"). Decision 1 above must be settled first.

- **`Rep` gains `counts`** (yes or no) and, when no, the reason (`past_plan`, or `too_slow`
  if decision 1 is yes), in one migration. Reps already saved all count. Nothing is thrown
  away, so the rule can be changed later and recalculated from what was sent.
- **The first N reps count**, N = the athlete's planned reps for that movement (the plan's
  `reps`, or the coach's per-athlete override: the `target_reps` the rack already shows).
  No planned reps (a Quick Training Session, a movement without reps) counts every rep.
- **The server works out the set's numbers** when the set is saved
  (`POST /api/sets/<id>/complete/`): marks each rep, then sets `reps_completed`,
  `avg_velocity` and `peak_velocity` from the counted reps only, rather than the tablet's.
- **Each rep's `counts` and reason travel with it** in the live rack state, so the screen
  can show it (Phase 2).
- **Everything that reads reps reads only the counted ones:** the athlete's analytics
  (`services/athlete_analytics.py`), the session summary, its frozen report and PDF
  (`services/session_completion.py`), the live room and its leaders, "most reps" among them
  (`services/room_state.py`), velocity records, "Behind", and the athlete's pages (spec 10).
- False Set is unchanged: the whole set is marked false. No change to the sensor, its
  firmware or its messages.

**Done when:**

- [ ] *(Backend test)* A set planned at 5 that receives 7 reps keeps all 7; reps 6 and 7 are
      `past_plan`; `reps_completed` is 5 and the averages are reps 1 to 5 only.
- [ ] *(Backend test, if decision 1 is yes)* A 0.10 m/s rep before the first real one is
      `too_slow` and the 5 real reps after it all count.
- [ ] *(Backend test)* A movement with no planned reps counts every rep.
- [ ] *(Backend test)* The athlete's analytics, the session summary and the live room's
      leaders leave out reps that don't count.
- [ ] Full suite passes in both modes; the migration runs on a copy of a real database.

**Stop. Devin reviews.**

## Phase 2 — The rack screen says so, as each rep lands

Moved from spec 09 (both sections). Decision 2 above must be settled first.

- **The count reads against the plan** ("4 / 5") and stays the largest thing on the screen.
- **On every rep the count pulses once** (about half a second), big enough to read from the
  bar: a counted rep steps the count up and flashes lime; a rep that won't count leaves the
  count alone and shows its speed greyed with its reason, "past the plan" or "too slow".
- **After the Nth rep a line appears:** "Reps past 5 won't count". Extra reps still show
  their speed, greyed, so the athlete can see how the rep felt.
- **The speed keeps its zone colour** (green, yellow, red against the movement's zone); the
  pulse is on the count, so "counted" never reads as "in zone".
- **The set summary** says "5 reps · 2 extra, not counted".
- **An older server** that sends no `counts` shows every rep as counted, exactly as today.
- Missed reps stay visible to the coach as today (the summary's rep list); the screen only
  shows what arrived.

**Done when:**

- [ ] *(Frontend test)* A counted rep pulses the count lime once; a rep past the plan leaves
      the count alone and shows greyed with "past the plan"; neither repeats on a redraw; the
      speed's zone colour is unchanged.
- [ ] *(Frontend test)* After the 5th rep the screen shows "Reps past 5 won't count" and the
      6th rep greyed with its speed; the summary says "5 reps · 1 extra, not counted".
- [ ] *(Frontend test)* A rep with no `counts` shows as counted.
- [ ] *(Browser)* A real sensor, a set planned at 3: lift 5 touch-and-go. Three lime pulses,
      then two greyed reps marked "past the plan", each within a second of the rep; the saved
      set, the coach's live room and the report all show 3.

**Stop. Devin reviews.**

## Phase 3 — The plate loader: which movements use a barbell, and the maths

Spec 16's Phases 0 and 1, built as written there (its decisions, plate sets, colours and
tests are unchanged): `Exercise.barbell`, kept by us, yes for the built-in catalog; and
`react/src/rack/plates.js`, `platesForLoad(loadLb, unit)`.

**Done when:** spec 16's Phase 0 and Phase 1 checklists are all true.

**Stop. Devin reviews.**

## Phase 4 — The plate loader: the widget

Spec 16's Phase 2, built as written there (`PlateLoader.jsx`, to `F_Rack_Plates1` to `6`),
with one change since: **the lb / kg choice is one remembered setting per device, shared with
the athlete's pages** (spec 10, decided 2026-11-11). It lives in one small module both read
and change (one storage key), so tapping the card here and the LB | KG toggle on My Recent
Progress always agree. Loads stay stored in pounds; kilograms are for display, to the
nearest 0.5 on the athlete's pages.

**Done when:** spec 16's Phase 2 checklist is all true, and *(frontend test)* changing the
unit on the rack screen changes it for the athlete's pages on the same device, and back.

**Stop. Devin reviews.**

## Phase 5 — The corner switch, on a local install

Built to `F_Rack_L1` (the corner button), `F_Rack_SwitchToDisplay`, `F_Display` and
`F_Display_SwitchToRack`.

- The idle rack screen gains one small button in its bottom-right corner, above the footer,
  showing the room display's mark (the rising bars). On the room display the same corner
  shows the rack's mark (the barbell) to switch back.
- **Either way it asks first:** "Switch Rack 3 to the room display?" / "Switch back to
  Rack 3?", with Cancel and Switch, so a stray tap can't take a rack away.
- The tablet remembers which it was showing (its existing device role), so a reload keeps it.
- **Local install only** for now: online, gym rack tablets arrive with spec 18, which turns
  the switch on there. An athlete's phone never shows it (its rack is its own; Phase 6 gives
  athletes their own way to the display).
- The room display's cog keeps its other settings; "Change device role" stays for going back
  to "Set up this device".

**Done when:**

- [ ] *(Frontend test)* The corner button asks first; Cancel changes nothing; Switch flips
      the tablet to the room display, and the display's corner flips it back.
- [ ] *(Frontend test)* An athlete's own rack (remote) shows no corner button.
- [ ] *(Browser)* On a local install, a reload keeps whichever the tablet was showing.

**Stop. Devin reviews.**

## Phase 6 — The room display, for athletes (remote)

Moved from spec 10 Phase 6.

- **Server:** online, `/dashboard` and the routes behind it accept an athlete login,
  read-only (no route that changes anything). A coach login still works as today.
- **Button:** the athlete's rack screen shows **Room display** while their session is live,
  opening the room display. It never appears on Home or in the menu.
- **Before building:** the button has no board yet. Draw it on the Proposed page and get it
  approved first (spec 06's Final designs rule).

**Done when:**

- [ ] An athlete login can open the room display and cannot change anything through its
      routes (each write route refuses an athlete with `403`).
- [ ] *(Frontend test)* The Room display button shows on the athlete's rack screen only while
      the session is live.
- [ ] *(Browser)* An athlete opens the room display from the rack screen mid-session and sees
      the same live data as the coach.

**Stop. Devin reviews.**

---

## Later: the sensor's own light (proposed, after Phase 2)

The same "did that count?" answer could blink the sensor's light, so a lifter facing away
from the screen still sees it. It needs the server to send each rep's answer back to that
sensor on its own topic (which the broker's per-sensor rules from spec 14 let only that
sensor read), and the firmware to subscribe and blink: once the moment it sends a rep, then
the answer when it comes back (green / red where the light has two colours; one colour shows
counted as a long blink, won't count as two short ones). With no answer (offline, an older
server) the light just shows the first blink. Not in this spec's phases.

## Acceptance criteria

- [ ] Every change works on the gym tablet and the athlete's phone alike, except where a
      phase says one version.
- [ ] A rack with no session says it's ready and waiting.
- [ ] Only the planned reps count, everywhere a rep is read; every rep is kept.
- [ ] The lifter sees each rep counted, or why not, within a second.
- [ ] Before every barbell set, the plates for one side show, in the device's unit.
- [ ] A local tablet flips between rack and room display from its corner, asking first.
- [ ] The footer is unchanged.

## Risks

| Risk | What reduces it |
|---|---|
| Counting changes the numbers coaches already trust | Every rep is kept with its reason; the rule can be changed and recalculated; old reps all count |
| The pulse distracts mid-set | Half a second, on the count only; the speed's colour is untouched |
| An athlete trusts a kilogram load that's off the prescription | Spec 16's warning names both numbers whenever it isn't exact |
| A stray tap turns a rack into a display mid-session | The switch asks first, and sits only on the idle screen |

## Docs to update when done

`docs/journal/core/rack-screen.md` (the waiting screen, rep counting and feedback, the plate
loader, the switch), `docs/handbook/reference/message-contract.md` (each rep's `counts` in the
rack state), `docs/handbook/reference/api.md` (the set-complete change; athletes on the room
display).
