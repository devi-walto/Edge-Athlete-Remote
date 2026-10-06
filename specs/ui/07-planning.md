# Feature Spec 7: Planning — Design, Groups, Roster, Calendar

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started. **One decision open** (how a program covers several groups)
- Form item: #11 (unified coach interface)
- Depends on: [06 Design rules](06-design-rules.md); [01 Coach accounts](../remote/01-coach-accounts.md) for archiving an athlete
- Mockup: `V3a_DesignStep1`, `V3g_CreateProgram`, `V3b_DesignStep2`,
  `V3e_ScheduleOnCalendar`, `V3f_ProgramScheduled`, `V4a_Groups`, `V4b_Roster`,
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
2. **Create a Training Program.** Your own copy of a block, for one or more groups,
   with a **planned start**. Edit its days and its date as much as you like. Nothing is
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

### Open decision — one program for several groups

Devin: "you can have multiple groups attending a training session so a training
program should let you select multiple groups."

Today a program belongs to exactly one group (`TrainingProgram.training_group`), and
several groups share a session by each having **their own program** attached to it
(`SessionParticipation`). About 20 places in the views and services read "the
program's group", including the code that decides which plan an athlete sees.

| | A. One program, many groups | B. One program per group, created together |
|---|---|---|
| The data | `training_group` becomes many-to-many | No schema change. Choosing two groups creates two programs with the same days |
| The card | One card: "Training Groups: Varsity, Test" | One card grouping the copies, by a shared batch id (one small new field) |
| Editing | One edit, everyone gets it | Edits are applied to every copy by default; a group can be edited alone |
| Risk | Medium–high. Touches plan resolution and ~20 query sites | Low. Plan resolution is untouched; it is how sessions already combine groups |
| Per-group differences (lighter loads for JV) | Not possible without splitting the program | Natural |

**Recommendation: B.** It gives the behaviour asked for with the least risk before
November 11, and it matches how a session already holds several groups. **Confirm
before Phase 3.** Until then, build everything with a single group.

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

## Phase 3 — More than one group

Blocked on the open decision above. For option B:

- Migration: `TrainingProgram.batch` — a nullable UUID shared by programs created together.
- `POST training-programs/` accepts `training_groups: [ids]`; creates one program per
  group with the same `batch`, all-or-nothing.
- The list groups programs by `batch` for display.
- The Phase 1 routes accept `?batch=1` to apply an edit to every program in the batch;
  the interface uses it by default. `schedule` schedules the whole batch on one date.

**Done when:**

- [ ] Creating for two groups makes two programs with identical days and one `batch`.
- [ ] A batch edit changes every copy; a single edit changes one and leaves the others.
- [ ] Scheduling a batch gives every group sessions on the same dates; setting one of
      those days up puts both groups on the same Training Session.
- [ ] Each athlete still sees the plan for their own group (the plan-resolution tests
      pass unchanged).

**Stop. Devin reviews.**

## Phase 4 — The Design tab

Frontend, on the components from spec 06. Mockups `V3a`, `V3g`, `V3b`, `V3e`, `V3f`.

- **Header sentence:** "A Training Block is a template. Create a Training Program from
  it for one group, then schedule that program as Training Sessions."
- **Step 1 · Build a Training Block** — "A template made of days. It never has a group
  or dates of its own." The open block is the focus card; its button is **Create a
  Training Program →**. Days are labelled "Days in this template · copied into every
  Training Program you create from it". Other blocks are quiet rows.
- **Create a Training Program** (dialog, `V3g`): name; Training Groups (one, or several
  after Phase 3); planned start, filled with `suggested_start`. "Nothing goes on the
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
  another day moves the preview. If scheduling returns `422`, show the reason and do
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
- "Coming up" and "Earlier" as quiet rows with the existing four states. List and Cards
  stay as a quiet toggle.
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
| Option B's copies drift apart without anyone meaning them to | Batch edit is the default; a single-group edit is a deliberate second choice |
| Phase 0 loses a catalog action | Its checklist requires every catalog action to be reachable before the tab is removed |

## Docs to update when done

`docs/journal/coach-tablet.md` (planning), `docs/journal/database.md` (a program is
scheduled as a second step, and why), `docs/journal/apis.md` route table, and
`docs/orientation.md`'s vocabulary if it still says "deploy".
