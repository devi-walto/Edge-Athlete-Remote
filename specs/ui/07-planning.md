# Feature Spec 7: Planning — Design, Groups, Roster, Calendar

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started. No decisions open
- Form item: #11 (unified coach interface)
- Depends on: [06 Design rules](06-design-rules.md); [01 Coach accounts](../remote/01-coach-accounts.md) for archiving an athlete
- Mockup: `V3a_DesignStep1`, `V3g_CreateProgram`, `V3b_DesignStep2`,
  `V3e_ScheduleOnCalendar`, `V3h_AddToExistingSession`, `V3f_ProgramScheduled`, `V4a_Groups`, `V4b_Roster`,
  `V4c_Calendar` in [`mockups/coach-ui-final.html`](mockups/coach-ui-final.html)

## Why

Planning is where the interface and the data model disagree most:

- **Design and Workout catalog are one component shown twice.** Both list the same
  blocks; one edits days, the other renames and reorders them.
- **The words on the steps do not say what they do** ("The template", "Placed in time",
  "A one-off").
- **A Training Program is meant to be an editable copy, but there is no way to edit
  one.** The API has routes to add, reorder, edit and delete a *block's* days and none
  for a *program's*.
- **Creating a program builds its whole calendar in the same instant**, so there is no
  moment to get the days and the date right first.
- **There is no way to add one athlete in the app.** Athletes arrive only by
  spreadsheet import, and that import sits in the Design tab.

## The model this spec builds toward

```
Training Block  ──create──▶  Training Program  ──schedule──▶  Training Sessions
  (template)                   (your copy)                     (days on the calendar)
       ▲                             │
       └────── save as a new block ──┘
```

1. **Build a Training Block.** A template. Never has a group or dates.
2. **Create a Training Program.** Your own copy of a block, for one group, with a
   **planned start**. Edit its days and its date as much as you like. Nothing is
   on the calendar yet.
3. **Schedule Training Sessions.** Confirm the start date on a calendar — or move it —
   and the program's sessions are created. From then on the day *structure* is locked;
   what is *in* each day can still change.

A program can be **saved as a new Training Block** at any time.

## Decisions this spec locks in

- **PLANNING's tabs become Design · Groups · Roster · Calendar.** Workout catalog is gone.
- **The start date stays required** on a program (no schema change). Before scheduling
  it is a *planned* start and can change freely.
- **Creating a program no longer creates its sessions.** Scheduling does.
- **Scheduled means "has calendar days".** It is derived, not stored.
- **Scheduling confirms the date.** If the coach moves it, the program is updated
  first, then the sessions are created.
- **A scheduled program cannot be scheduled again, and cannot be moved.** Moving a
  scheduled program means deleting days that may already have sessions and saved sets
  on them. It is a separate feature, out of scope.
- **Once scheduled, days cannot be added, removed or reordered.** Each calendar day
  points at a specific day of the program and is frozen when written.
- **A program drops off the Design list once its last session's date has passed.**
- **Athletes are created only in the Roster.** A group's **Add athlete** button picks
  from the roster; it is the only way into a group and it never creates anyone.
- **The one-off session leaves Planning.** It is unplanned work and lives in SESSION
  (spec 08).

### Decided 2026-10-06 — several groups share a session; a program stays one group

**The server already does this, and not through the program.** Checked in the code:

- An **athlete** can be in several Training Groups (`Athlete.training_groups`).
- A **Training Program** belongs to exactly one group. A group can have several programs.
- A **Training Session** can hold several programs at once, one `SessionParticipation`
  row each, each pointing at the day that group is running.
- `services/plan_resolution.py` gives each athlete the **intersection**: the programs
  in this session whose group the athlete is in. For an athlete in two of them, the
  movement lists are **combined** — the bigger group's work first, one entry per
  movement, and where both plans prescribe the same movement the **lighter percentage
  wins**, taking its sets and reps with it.
- Test, using "Varsity Football" and "Receivers":
  `test_two_groups_combine_and_the_lighter_prescription_wins`.

So a receiver gets football's lifts and the receivers' lifts in one session **if both
programs are on that session.** The journal explains the rule and why:
`docs/journal/database.md`, "One session, several groups".

**What was missing is the interface.** Nothing in the front end calls
`POST sessions/{id}/participation/`, and setting up a calendar day
(`scheduled_session_create_session`) creates a session holding only that one program.
Two programs scheduled on the same date became two separate sessions, and only one day
can run at a time.

**Decision:**

- **A Training Program is for one group. No change to the model, and
  `services/plan_resolution.py` is not touched.** Making a program many-to-many was
  rejected: it would rewrite the resolver, and it could not express receivers plus
  football anyway, because those two groups need *different* programs.
- **Groups come together on the session.** When a coach schedules a program onto dates
  where another program already has a Training Session, the interface asks **"Add to
  the existing sessions?"** (mockup `V3h_AddToExistingSession`).
- The multi-group checkboxes are removed from "Create a Training Program". It picks one group.

## What exists today

- `react/src/WorkoutCatalog.jsx` — Design and Catalog, switched by a `section` prop
  (`Dashboard.jsx` renders it for both tabs). "Edit days" in Design only preselects the
  block in the manual builder.
- Block routes (all coach-only): `training-blocks/`, `…/{id}/`, `…/{id}/workouts/`,
  `…/{id}/workout-order/`, `…/{id}/workouts/{wid}/`, `…/workouts/{wid}/exercise-order/`,
  `…/workouts/{wid}/exercises/{eid}/`.
- Program routes: `training-programs/` (list, create) and `training-programs/{id}/promote/`. **Nothing else.**
- `services/planning.py`: `instantiate_block()` copies a block's days into a new program
  and ends with `generate_schedule(program, block)`. `generate_schedule()` is its own
  function, returns nothing quietly when the block has no cadence, no length or no days,
  and uses `ignore_conflicts` so it cannot double a calendar.
- The API refuses to create a program from a block without a start date
  (`"start_date is required to deploy a block"`).
- `ScheduledSession` → `training_program_workout` is `CASCADE`: deleting a program day
  deletes its calendar days.
- `AthleteWorkoutExerciseOverride` → `training_program_exercise` is `CASCADE`: deleting
  a movement from a program deletes athletes' exceptions written on it.
- Calendar: `scheduled-sessions/`, `…/{slot_id}/`, `…/{slot_id}/session/` ("Set up
  day"). States: Planned, Ready, Running, Complete (`ScheduleWorkspace.jsx`).
- Groups: `training-groups/`, `…/{id}/athletes/`, `…/{id}/coaches/`. No route renames
  or deletes a group.
- Athletes: `GET`/`POST athletes/`, `athletes/{id}/`. Imports: `imports/preview/`, `imports/`.
- `react/src/coach/GroupsView.jsx` — group cards, an opened group, and the "Every
  athlete" widget at the bottom.

## Non-goals

- Moving or unscheduling a scheduled program.
- Renaming or deleting a training group.
- Login links and sensors on the roster (specs 03 and 04 add those columns).
- The "my groups" filter.

---

## Phase 0 — Fold Workout catalog into Design

Frontend only. No new behaviour.

- In `WorkoutCatalog.jsx`, a block opens in place to show its days, with what the
  catalog offers today: move up, move down, rename, edit movements, delete.
- Remove the `catalog` tab from `STATE_TABS.planning` and its render branch.
- "Add day" on an open block opens the existing manual builder for that block, in
  place. The always-open builder panel at the bottom goes.
- Spreadsheet import for plans becomes a link at the top of step 1.

**Done when:**

- [ ] Every action the Catalog tab offered is reachable from a block in Design.
- [ ] *(Frontend test)* PLANNING shows three tabs (Roster arrives in Phase 5).
- [ ] The existing block tests pass unchanged; the frontend suite and build pass.
- [ ] *(Browser)* Create a block, add a day, reorder, rename, edit movements, delete a day.

**Stop. Devin reviews.**

## Phase 1 — A program you can edit

Backend. Mirror the block routes for programs, reusing the same serializers and
ordering helper (`apply_order`) where the shapes match:

| Route | Does |
|---|---|
| `GET`/`PATCH training-programs/{id}/` | read; change name, planned start, end date |
| `POST training-programs/{id}/workouts/` | add a day |
| `PATCH`/`DELETE training-programs/{id}/workouts/{wid}/` | rename or delete a day |
| `PUT training-programs/{id}/workout-order/` | reorder days |
| `PUT …/workouts/{wid}/exercise-order/` | reorder movements |
| `POST`/`PATCH`/`DELETE …/workouts/{wid}/exercises/{eid}/` | add, edit, remove a movement |

All coach-only. All refuse nothing yet about scheduling — that is Phase 2.

**Done when:**

- [ ] Each route has tests for the happy path, a missing id (`404`), and a wrong parent
      (a day that belongs to another program is `404`, never edited).
- [ ] **Editing a program never changes the block it came from**, and editing the block
      never changes the program.
- [ ] Deleting a movement that an athlete has an exception on removes that exception
      and says so in the response, so the interface can warn first.
- [ ] `promote` on an edited program produces a block with the edited days.
- [ ] The full Django suite passes; no migration is needed.

**Stop. Devin reviews.**

## Phase 2 — Scheduling becomes its own step

Backend.

- Remove the `generate_schedule()` call from `instantiate_block()`.
- `POST training-programs/{id}/schedule/` with optional `{start_date}`, coach-only, in
  one transaction:
  1. If the program already has calendar days → `409 already_scheduled`.
  2. If a `start_date` is sent, save it on the program.
  3. If the block has no weekly pattern, no length, or the program has no days →
     `422 cannot_schedule` with which one is missing. **Never succeed with zero days.**
  4. Call `generate_schedule()`. Return the program with its sessions.
- The program serializer adds `is_scheduled` and `sessions_count`, and — for the planned
  start's default — `suggested_start`: the next date matching the block's first training
  weekday.
- Once scheduled, the Phase 1 routes that change **structure** return
  `409 program_scheduled`: add day, delete day, reorder days. Renaming a day and
  everything about movements stay allowed. `PATCH` of `start_date` is also refused.
- The program list accepts `?current=1`: everything not scheduled, plus scheduled
  programs whose last calendar day is today or later.
- The seed command already calls `generate_schedule()` itself; confirm it still seeds a
  calendar.

**Done when:**

- [ ] Creating a program from a block creates **no** calendar days.
- [ ] `schedule` creates exactly the days `training_dates()` gives for the saved start.
- [ ] `schedule` with a new `start_date` updates the program and schedules from the new date.
- [ ] A second `schedule` returns `409` and creates nothing.
- [ ] A block with no pattern, no length, or no days returns `422` naming the reason,
      and the program stays unscheduled.
- [ ] After scheduling: add/delete/reorder day and changing `start_date` return `409`;
      renaming a day and editing a movement succeed.
- [ ] `?current=1` hides a program whose last day was yesterday and shows one whose
      last day is today.
- [ ] The tests that expected calendar days straight after creation are updated to call
      `schedule` — and only those tests change.
- [ ] `docker compose --profile seed run --rm seed` still produces a calendar.

**Stop. Devin reviews.**

## Phase 3 — Add to the existing sessions

Backend. Mockup `V3h_AddToExistingSession`.

**When the question is asked.** Calendar days hold a **date, not a time**
(`ScheduledSession.date`), so "already scheduled" means *another program has a calendar
day on the same date*. If times are ever added, the same question gets asked about the
overlap in time instead.

- Migration: `ScheduledSession.shares_session` — a boolean, default `True`. It means
  "when this date is set up, this program goes on the same Training Session as the
  other programs on that date that also share".
- `GET training-programs/{id}/schedule-preview/?start_date=` — coach-only, changes
  nothing. Returns the dates the program would get and, for each date that another
  program already holds, that program's name, group and day. The scheduling screen
  already needs the dates for its preview; this is the same call.
- `POST training-programs/{id}/schedule/` (Phase 2) accepts `share_sessions`
  (default `true`) and writes it to every calendar day it creates. The interface sends
  it only after asking; with no overlaps there is nothing to ask.
- **Setting a day up** (`POST scheduled-sessions/{slot_id}/session/`):
  - if the slot shares: one session for **every sharing slot on that date** — a
    `SessionParticipation` per program, the roster is the union of the groups' athletes,
    and every one of those slots points at the session;
  - if it does not share: exactly today's behaviour, a session for that program alone.
- **If a session for that date is already set up** (and not ended) when a sharing
  program is scheduled onto it, the new program is added to it straight away: a
  participation, the athletes added to the roster, the slot pointed at it.
- `PATCH scheduled-sessions/{slot_id}/` can flip `shares_session` for one date, as long
  as that slot has no session yet.
- Give `POST sessions/{id}/participation/` its first caller: adding a program to a
  session that is already set up, from the Calendar.

**Done when:**

- [ ] `schedule-preview` lists every date and names the other program on each
      overlapping one; it writes nothing.
- [ ] Scheduling with `share_sessions: true` onto dates another program holds: setting
      one of those dates up creates **one** session with two participations and a
      roster holding both groups' athletes once each.
- [ ] An athlete in both groups gets the combined movement list — the existing
      `test_two_groups_combine_and_the_lighter_prescription_wins` passes **unchanged**,
      and a new test reaches the same result through the scheduling and set-up routes.
- [ ] An athlete in only one of the groups sees only that group's plan.
- [ ] `share_sessions: false`: the same dates set up as two separate sessions, as today.
- [ ] Scheduling onto a date whose session is already set up adds the program to it; a
      session that has **ended** is never joined.
- [ ] Flipping `shares_session` on a slot that already has a session is refused.
- [ ] Existing calendar days (created before the migration) default to sharing, and a
      date with a single program behaves exactly as before.
- [ ] `git diff` shows no change to `services/plan_resolution.py`.

**Stop. Devin reviews.**

## Phase 4 — The Design tab

Frontend, on the components from spec 06. Mockups `V3a`, `V3g`, `V3b`, `V3e`, `V3f`.

- **Header sentence:** "A Training Block is a template. Create a Training Program from
  it for one group, then schedule that program as Training Sessions."
- **Step 1 · Build a Training Block** — "A template made of days. It never has a group
  or dates of its own." The open block is the focus card; its button is **Create a
  Training Program →**. Days are labelled "Days in this template · copied into every
  Training Program you create from it". Other blocks are quiet rows.
- **Create a Training Program** (dialog, `V3g`): name; one Training Group; planned start, filled with `suggested_start`. "Nothing goes on the
  calendar until you schedule it."
- **Step 2 · Create a Training Program** — the open program is the focus card: a
  **NOT SCHEDULED** / **SCHEDULED** badge beside its name; its groups and planned start,
  each with **Change**; **Save as a new Training Block** and **Add day** as outline
  buttons; the day list with the same controls as a block, labelled "editing here
  changes only this program, never the block it came from". Primary: **Schedule on the
  Calendar →**. Other programs are quiet rows, each with its badge.
- **A scheduled program** (`V3f`): the day list shows a lock in place of the arrows and
  only **Edit movements**; a line explains why. Primary: **See it on the Calendar →**.
- **Step 3 · Schedule Training Sessions** — a link row to the Calendar.
- **Scheduling screen** (`V3e`, on the Calendar tab): "Confirm the day it starts" with
  the planned start selected, the program's days previewed on its weekly pattern,
  other programs' sessions shown in grey, and **Schedule N Training Sessions**. Clicking
  another day moves the preview. **If any of those dates already has another program's
  session, pressing the button first opens "Add to the existing sessions?"** (`V3h`):
  how many dates overlap and with which program; **Add to the existing sessions**
  (selected by default — "an athlete in both groups gets both workouts together; where
  the two plans share a movement, the lighter one is used") or **Keep them separate**
  ("only one session can run at a time, so the two would be run one after the other").
  The Calendar shows a date's programs together when they share. If scheduling returns `422`, show the reason and do
  not offer the button.
- Delete a movement an athlete has an exception on → warn before, naming how many.
- The word "deploy" appears nowhere.

**Done when:**

- [ ] *(Frontend test)* Exactly one step is active at a time, and exactly one card is a focus card.
- [ ] *(Frontend test)* A scheduled program renders no add, delete or reorder controls.
- [ ] *(Frontend test)* The scheduling screen previews the same dates the server then creates.
- [ ] *(Browser)* Block → program → edit a day → change the planned start → schedule →
      the sessions are on the Calendar on the confirmed date.
- [ ] *(Browser)* Save an edited program as a new Training Block; the new block has the
      edited days and no dates.
- [ ] No text on the tab contains "deploy", "template" as a noun for a thing, or "one-off".

**Stop. Devin reviews.**

## Phase 5 — The Roster tab

New tab, mockup `V4b`. New file `react/src/coach/RosterView.jsx`.

- Header: "Roster — Add one athlete, or import many from a spreadsheet. Training Groups
  decide who trains together."
- Filter chips: Everyone and one per group, plus No group.
- Table: Athlete · Training Groups · Trend · actions (**Change groups**, **Open in
  Analytics**, **Archive**).
- **Add athlete** (primary): a name, then optionally groups. `POST /api/athletes/`.
- **Import a roster** (outline): the existing preview-then-import flow, moved here from Design.
- Archive needs spec 01's `is_active`. Archived athletes are hidden unless a "Show
  archived" toggle is on.
- The Trend column shows **Behind** from spec 09's endpoint; until that exists it shows
  nothing rather than a guess.
- Hosted only, later: the login and sensor columns from specs 03 and 04.

**Done when:**

- [ ] *(Frontend test)* Adding an athlete adds a row without a reload; a blank name is refused.
- [ ] *(Frontend test)* Each filter shows exactly the right athletes; "No group" shows
      athletes in none.
- [ ] *(Browser)* Import a roster from the Roster tab; the Design tab no longer offers
      roster import.
- [ ] *(Browser)* Archive an athlete: gone from the roster and from pickers, history
      still opens in Analytics.

**Stop. Devin reviews.**

## Phase 6 — Groups

Mockup `V4a`. `GroupsView.jsx`.

- The "Every athlete" widget is removed (it is the Roster now).
- An opened group is the focus card: its athletes, each with **Open plan** and
  **Remove**; one primary, **Add athlete to <group>**, which opens a picker of roster
  athletes not already in the group. It creates nobody. The label says so: "added from
  your Roster. New athletes are created in the Roster tab."
- Other groups are quiet rows. **New Training Group** stays.
- The sentence about renaming and deleting groups not being possible leaves the
  screen; it is a note for developers, and it is recorded here instead.

**Done when:**

- [ ] *(Frontend test)* The picker lists only athletes not in the group, and no way to
      type a new name.
- [ ] *(Browser)* Add and remove an athlete; the count and the Roster's group column update.

**Stop. Devin reviews.**

## Phase 7 — Calendar

Mockup `V4c`. `ScheduleWorkspace.jsx`.

- Header: "Training Sessions — Every Training Program is scheduled here as Training
  Sessions. Setting one up creates its roster. It does not start it."
- The **next** session that is not complete is the focus card, with its group, program
  and workout, and **Set up this session**.
- Two views behind one **List | Month** switch (spec 06 rule 9; mockups
  `F_Local_CalendarList`, `F_Local_CalendarMonth`). **List**: "Coming up" and "Earlier"
  as solid rows with the existing four states. **Month**: a grid of solid square day
  blocks; pressing a day with a session opens it, as pressing its row does. The switch
  remembers the coach's last choice. The old Cards view is replaced by Month.
- The "open a day from scratch" panel leaves this tab (spec 08 gives it a home).
- The empty state names the real next step: "Nothing is scheduled. Create a Training
  Program in Design and schedule it."

**Done when:**

- [ ] *(Frontend test)* The focus card is the earliest session that is not complete.
- [ ] *(Frontend test)* With no sessions, the empty state renders and links to Design.
- [ ] *(Browser)* Set up the next session, then start it from SESSION.

---

## Acceptance criteria

- [ ] PLANNING has four tabs: Design, Groups, Roster, Calendar.
- [ ] A coach can build a block, create a program from it, edit that program, schedule
      it by confirming a date, and see its sessions — without leaving Planning.
- [ ] A program's edits never reach its block; a block's edits never reach its programs.
- [ ] Nothing is on the calendar until a program is scheduled; a scheduled program
      cannot be scheduled twice.
- [ ] A coach can add one athlete from the Roster, and only from the Roster.
- [ ] The interface uses Training Block / Training Program / Training Session throughout.
- [ ] Every screen follows spec 06.

## Risks

| Risk | What reduces it |
|---|---|
| Scheduling stops happening and nobody notices a program has no calendar | The NOT SCHEDULED badge on every unscheduled program; step 2's idle row says how many are unscheduled |
| A coach expects to move a scheduled program | The scheduled card says the days are locked and why; moving is named as out of scope |
| Deleting a program movement silently wipes athletes' exceptions | Phase 1 reports it; Phase 4 warns before doing it |
| Two programs on one date are set up as two separate sessions, and only one can run | Phase 3 puts every program on that date onto one session by default |
| Phase 0 loses a catalog action | Its checklist requires every catalog action to be reachable before the tab is removed |

## Docs to update when done

`docs/journal/coach-tablet.md` (planning), `docs/journal/database.md` (a program is
scheduled as a second step, and why), `docs/journal/apis.md` route table, and
`docs/orientation.md`'s vocabulary if it still says "deploy".
