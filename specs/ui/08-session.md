# Feature Spec 8: Session

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started
- Form item: #11 (unified coach interface)
- Depends on: [06 Design rules](06-design-rules.md)
- Mockup: `V3c_SessionEmpty`, `V3d_QuickSession`, `V4d_Session`, `V2e_RackStates` in
  [`mockups/coach-ui-final.html`](mockups/coach-ui-final.html)

## Why

Three problems on the live room, and one about getting into it:

- **The same facts appear three times.** The athlete's name, movement and load are in
  the rack list, again in a "Rack observation" card, and again in the big set card.
- **Sensor status appears twice**, and takes a whole card at the bottom of the screen.
- **A tab row with one tab** ("ROOM").
- **SESSION is disabled when no day is set up.** Because of that, starting an unplanned
  session had to be put in PLANNING → Calendar, where a comment in `Dashboard.jsx` admits
  it is only there because SESSION cannot be reached. An unplanned session does not
  belong in Planning.

## Decisions this spec locks in

- **SESSION can always be opened.** With nothing running it offers two ways in: the
  next planned Training Session, or a **Quick Training Session**.
- **A Quick Training Session is three guided steps:** choose athletes → choose a
  workout → start.
- **The Rack observation card is removed.** The set card carries everything.
- **The set card has a state for "no set yet".** Today it only appears once a rack has
  a set; the observation card was the only thing showing a rack before that.
- **Sensor controls shrink to a badge on the set card.** Quiet while the sensor is
  healthy. **Amber, with words, when it is not.** Pressing it opens the swap controls.
- **Every rack in the list carries a small sensor dot**, so a dead sensor shows on a
  rack the coach is not looking at.
- **The ability to swap a sensor from the live room stays.** It was kept on purpose in
  August: "one is for setting the room up, the other is for fixing a rack while looking
  at it" (commit `c75cd52`).
- **No ROOM tab.**
- **The athlete's name stays in the rack list and on the quick note.** Devin is fine with those.

## What exists today

- `react/src/coach/StateNavbar.jsx` dims and disables SESSION when `daySet` is false
  (unless the coach is already on it). `Dashboard.jsx` computes `daySet` from a running
  day or a staged one, and redirects away from SESSION otherwise.
- `OpenDayFromScratch` (rendered in PLANNING → Calendar when no day is running) calls
  `POST /api/sessions/`, which **starts the room immediately** — there is no staged step.
- `StartStagedDay` in SESSION starts a day that was set up from the Calendar
  (`POST /api/sessions/{id}/start/`).
- `RackSelectionControls` — the read-only "Rack observation" panel: movement, load,
  progress, rack state, latest result, hardware.
- The set card (`coach-set-hero`) renders only when `rack.latest_set` exists.
- `CoachHardware` — "Rack health · Connected hardware": the sensor's name and pulse
  state, and a picker calling `PUT /api/racks/node-assignment/` (addressed by the
  screen's device id; refuses a sensor on another rack or with an open set).
- Room state carries, per rack: the athlete, the latest set, `screen_device_id`, the
  node and its pulse state.
- `QuickNote` — appends to the athlete's note; never replaces it.

## Non-goals

- Remote racks, the session link and "Not joined yet" (spec 04 adds them to this screen).
- Moving an athlete between racks from the coach's tablet (removed on purpose earlier;
  an athlete's rack is wherever they checked in).
- Changing what ending a day does.

---

## Phase 0 — SESSION can always be opened

- `StateNavbar`: SESSION is never disabled. Remove the dimmed, not-allowed styling.
- `Dashboard.jsx`: remove the redirect away from SESSION when no day is set.
- Add a small lime dot on the SESSION button **while a day is running**, so the bar
  still says whether something is live.
- With no day running and none staged, SESSION renders the empty state from Phase 1
  (for this phase, a plain placeholder).

**Done when:**

- [ ] *(Frontend test)* SESSION is enabled with no day, with a staged day, and with a running day.
- [ ] *(Frontend test)* The dot shows only while a day is running.
- [ ] *(Browser)* Typing `/coach/session` with nothing running stays on SESSION.
- [ ] The existing navbar tests are updated, not deleted, and pass.

**Stop. Devin reviews.**

## Phase 1 — Nothing running: two ways in

Mockup `V3c`.

- Heading: "No Training Session is running — Start the next planned one, or run a quick
  one without planning."
- **Planned** (the focus card): the next session from the calendar that is not
  complete — its date, day name, group, program and movements.
  - If it is already set up (state Ready): **Start**.
  - If it is only planned: **Set up and start** — sets it up
    (`…/scheduled-sessions/{id}/session/`) and then starts it
    (`…/sessions/{id}/start/`). If the second call fails the day stays set up, and the
    card shows **Start**.
  - **Pick a different day** goes to the Calendar.
  - If nothing is scheduled, the card says so and points to Design.
- **Unplanned**: **Quick Training Session** — "Three steps: choose athletes, choose a
  workout, start. Nothing has to be on the calendar."

**Done when:**

- [ ] *(Frontend test)* The planned card shows the earliest incomplete session, and the
      right button for Planned and for Ready.
- [ ] *(Frontend test)* With an empty calendar the planned card explains and links to Design.
- [ ] *(Browser)* **Set up and start** opens the live room in one press.
- [ ] *(Browser)* If the start call is made to fail, the day is left set up, not half-created.

**Stop. Devin reviews.**

## Phase 2 — The Quick Training Session

Mockup `V3d`. New file `react/src/coach/QuickSession.jsx`. Uses spec 06's `Step`.

1. **Choose athletes** — whole Training Groups, or individual athletes from the roster.
   Once done it collapses to one line with **Change**.
2. **Choose a workout** — the days already built, listed by Training Block (and by
   current Training Program), one selectable; or **No workout**: "Athletes pick their
   movement at the rack; sets are still recorded."
3. **Start** — a name (pre-filled, e.g. "Quick session · Tue, Oct 6") and **Start**.

Behind it:

- No workout → `POST /api/sessions/` with the label and athletes. This is what
  `OpenDayFromScratch` does today.
- With a workout → the same, plus a Training Program with **no block behind it**
  holding a copy of the chosen day, attached to the session
  (`POST training-programs/` without `training_block`, then
  `…/sessions/{id}/participation/`). The model already calls this a first-class path.
  **Confirm in this phase** that the existing create route can copy a chosen day's
  movements; if it cannot, add a small server helper rather than doing the copy in the
  browser.
- Remove `OpenDayFromScratch` from PLANNING → Calendar once this works.

**Done when:**

- [ ] *(Frontend test)* Each step can be reopened and changed before starting; Start is
      unavailable until athletes are chosen.
- [ ] A quick session with a workout: each chosen athlete sees that day's movements at
      the rack, and the saved sets are attributed to that day.
- [ ] A quick session with no workout starts, records sets, and ends into a report.
- [ ] The Training Block the day was taken from is unchanged afterwards.
- [ ] *(Browser)* Planning → Calendar no longer offers "open a day from scratch".

**Stop. Devin reviews.**

## Phase 3 — One card per rack

Mockups `V4d` and `V2e`.

- Remove the lone ROOM tab (spec 06, rule 7).
- Remove `RackSelectionControls`.
- The set card always renders for the selected rack, as the focus card:

  | Rack is… | Card shows |
  |---|---|
  | checked in, no set yet | "Rack N · No set yet", the athlete, "Checked in · no movement picked" (or the movement), `--` |
  | lifting / resting | "Rack N · Set k of n", athlete, movement and load, the large velocity number, peak, reps, target |
  | false set | the same, with the state chip reading "False set" |
  | empty | "Rack N · Nobody checked in" |

- A **state chip** on the card: Idle · Lifting · Resting · False set.
- The rep chart and "What changed" lose their boxes and sit on hairlines. Quick note
  becomes one row; its button is an outline.
- The rack list: the selected rack is bright with a lime border; the others are grey rows.

**Done when:**

- [ ] *(Frontend test)* A rack with a check-in and no set renders the card (it rendered
      nothing before).
- [ ] *(Frontend test)* Each of the four states renders the right label and chip.
- [ ] *(Frontend test)* The name, movement and load each appear once in the detail area.
- [ ] Nothing the observation card showed is lost: rack state is the chip, hardware is
      the badge (Phase 4), latest result is the card's numbers.
- [ ] *(Browser)* With the simulator, the card moves through no-set → lifting → resting.

**Stop. Devin reviews.**

## Phase 4 — The sensor badge

- On the set card, beside the state chip, a button-badge:
  - healthy: a mint dot and "Sensor" — small and grey;
  - pulse overdue or no sensor: **amber, with a warning mark and words** — "Sensor not
    responding" or "No sensor";
  - both have a small chevron, so it reads as pressable.
- Pressing it opens a small panel: the sensor's name, how long since its last
  heartbeat, **Swap to another sensor** (the same picker and the same
  `PUT /api/racks/node-assignment/` call `CoachHardware` uses), **Unlink**.
- Each row in the rack list gets a sensor dot: mint when healthy, a hollow amber ring
  when not.
- Remove the `CoachHardware` card. Its logic moves into the panel; nothing about the
  endpoint changes.
- Room Layout keeps its own sensor linking. Two places is intended: one to set a room
  up, one to fix a rack mid-session.

**Done when:**

- [ ] *(Frontend test)* The badge is quiet when the pulse is fresh and amber with text
      when it is overdue or missing.
- [ ] *(Frontend test)* The rack list shows the right dot for each rack.
- [ ] *(Browser)* Swap a sensor from the badge during a session; the rack's reps come
      from the new sensor.
- [ ] The server's refusals still surface as messages: a sensor on another rack; a
      sensor with an open set.
- [ ] No "Connected hardware" card remains.

---

## Acceptance criteria

- [ ] A coach can reach SESSION at any time, and start either a planned or an unplanned
      session from it.
- [ ] Unplanned sessions are no longer started from Planning.
- [ ] The live room shows each fact about the selected rack once.
- [ ] A rack with an athlete but no set is visible.
- [ ] A failing sensor is visible from the rack list and the set card, and can be
      swapped without leaving the room.
- [ ] Every screen follows spec 06.

## Risks

| Risk | What reduces it |
|---|---|
| A quiet badge hides a dead sensor | It is only quiet while healthy; failure is amber with words, and the rack list repeats it |
| "Set up and start" leaves a half-made day | Phase 1 handles the second call failing and tests it |
| Removing the observation card loses the rack's state before a set exists | Phase 3's no-set state, with its own test |
| An enabled SESSION confuses a coach with nothing to run | The empty state says what to do next, and the dot shows when something is live |

## Docs to update when done

`docs/journal/coach-tablet.md` — SESSION is always reachable, and why the earlier
"dim it until a day is set" rule was dropped. `_COACH_UI_REDESIGN.md` describes the old
gating; add a note pointing here rather than rewriting history.
