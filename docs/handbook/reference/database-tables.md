# Database tables

The part of the system where a wrong assumption does lasting damage, because it changes
numbers a coach then trains people against.

**This page is the tables.** Every one is collapsed below, carrying its own schema and
the decisions attached to it — open the ones you need. The only thing kept out here is
the tuning file, because it is not a table.


::::::{dropdown} New here? The database in plain English

**What this is.** A friendly tour of every table in the Edge Athlete database and how
they fit together — written so you don't need to be an engineer to follow it. If you've
ever wondered "where does the app keep the athletes?" or "what actually happens when a
set finishes?", this is the map.

**The one sentence version.** Edge Athlete watches athletes lift a barbell, measures how
fast the bar moves, and saves every rep so coaches can see who's training well and who's
fatiguing. The database is where all of that is remembered.

> **How to read this doc.** A "table" is just a list — think of a spreadsheet with one
> tab per kind of thing (one tab for athletes, one for sets, and so on). Each row is one
> item; each column is one detail about it. When one table "points to" another, it just
> means a row remembers which row it belongs to — like a set remembering which athlete
> did it. That's all you need to know to follow everything below.

The source of truth is [`django/event_handler/models.py`](https://github.com/devi-walto/Edge-Athlete-Remote/blob/main/django/event_handler/models.py),
which carries the full reasoning in comments. This is the readable version.

## The 30-second big picture

There are four worlds in this system, and the tables split along them:

1. **The equipment on the gym floor** — the sensors on the bars and the tablets at each rack.
2. **The people** — the athletes, the groups they train in, and the coaches who run them.
3. **The plan** — the reusable templates, the deployed instances, and the calendar.
4. **The training that actually happened** — sessions, sets, reps, and the frozen report.

Everything connects back to two anchors: an **athlete** (who) and an **exercise** (what
movement).

## The idea that explains the whole schema

**A plan never stores pounds. It stores a percent.**

A coach writes "Back Squat — 5×3 at 80%" *once*, for a whole group. Each athlete's actual
bar weight is worked out at the moment it's read: 80% × *that athlete's own current
benchmark*. Thirty athletes, one plan, thirty correct bars — and when someone gets
stronger their weights follow automatically, because the benchmark moved, not because
anyone edited the plan.

This is why you will not find a "target weight" column anywhere. If you go looking for one
and can't find it, that's the design working.

## World 1 — The equipment on the gym floor

### `Node` — the sensor on the barbell
The device (an ESP32 with a motion sensor) clamped to a bar. It's what actually measures
bar speed. Each node has a permanent name (`node_id`), and a coach assigns it to a
physical rack by setting its `rack_number`. It reports its own health every few seconds —
battery, signal, when it was last heard from. It can also carry a list of movements its
rack is *physically capable* of; that filters what the tablet offers, and never blocks a
set.

*Think of it as:* the fitness tracker on the bar.

### `RackScreen` — the tablet standing at a rack
The touchscreen at each rack showing the live workout. Like the node, it has its own
permanent id (`device_id`, created by the browser on first setup) and a `rack_number` a
coach assigns.

> **The single most important "gotcha" in the whole system:** the sensor (`Node`) and the
> tablet (`RackScreen`) are **two completely separate things**. They are *not* linked in
> the database. The only thing that connects them is that a coach put them at the **same
> rack number**. So "Rack 3" is really "whatever sensor a coach called Rack 3" plus
> "whatever tablet a coach called Rack 3" — assigned independently.

### `MonitoringEvent` — "something changed, tell the wall display"
A durable note that the room state moved. It's written the instant something happens, and
a separate loop delivers it to the dashboard afterward and ticks it off. Built this way on
purpose: if the connection drops, the row simply stays undelivered until the next attempt,
instead of the update vanishing.

## World 2 — The people

### `Athlete` — a lifter
One person who trains: their name, optional notes, an optional NFC tag id (tap-to-identify
at a rack), and the groups they currently train with.

An athlete can be in **several groups at once** — a football player might also sit in a
speed group, and each group runs its own plan. Which plan applies on a given day is
answered by the session itself. Membership is current-state only: adding or removing a
group never rewrites history, because past sessions and sets stay attached to whatever
they were created under.

### `TrainingGroup` — a named subset of athletes who train together
"Varsity Football", "Freshman Speed".

> ⚠️ **This is not the list of everyone in the system.** Every person lives in `Athlete`;
> a group is a *slice* of them that a coach hangs a plan on. A gym runs many groups at
> once, and several groups can share one session.

It carries no dates and no workouts — it is "who trains together", not a schedule.

### `TrainingGroupCoach` — which staff run a group
Real weight rooms put several people on one group: a head coach plus assistants. This is
the table that says so, with a `role` on each row.

> ⚠️ **Being listed here is a statement, not a permission.** Nothing in the API asks this
> table whether a write is allowed — any logged-in coach can still do anything. That is a
> deliberate choice ("filter, not fence"), so **don't read a row here as authorization**
> until something actually enforces it. See SPEC §9.

### `Tag` — labels for grouping movements
Simple labels hung on exercises — "lower body", "push" — so movements can be filtered.

### `BlockCategory` — labels for finding templates
"Off-season", "Football", "Freshman". Deliberately a *different* table from `Tag`, even
though both are "a name you hang on something": `Tag` is a vocabulary of movement labels,
and mixing the two would make a word like "Upper" mean a body region or a grade level
depending on what it's attached to. A block can have several categories at once, because
a block honestly is both "Off-season" *and* "Football".

### `Exercise` — the official list of movements
The master catalog — "Back Squat", "Bench Press". This exists so a movement means *exactly
one thing* everywhere. Without it, one coach typing "Back Squat" and another typing "back
squat" would quietly split an athlete's history in half. Every plan, benchmark, and set
points at a catalog entry instead of spelling out the name.

*Think of it as:* the gym's official menu — everyone orders from the same menu.

## World 3 — The plan

This is the part with the most tables, and it's really one idea repeated twice: **a
timeless template, and a dated copy of it.**

### `TrainingBlock` — the reusable template
A plan a coach designs once and redeploys — tweak last year's block, run it again this
year. It has **no group and no dates**; those only appear when it's deployed. It also
carries how long it runs (`duration_weeks`) and which days of the week it trains
(`cadence_days_of_week`), which is what the calendar generator reads.

- `TrainingBlockWorkout` — one ordered day inside the template ("Day 1: Squat").
- `TrainingBlockExercise` — one prescription row inside a day: which movement, how many
  sets and reps, **what percent**, and the target bar-speed range.

### `TrainingProgram` — the deployed instance
The template, given to a group, placed in time. Deploying **copies** every day and every
prescription row down into the program's own tables.

> **Why copy instead of point?** So the two are independent. Editing a deployed program
> changes only that group's plan; editing the template changes only *future* deployments.
> Neither can reach back and rewrite the other.

A program can also be built from scratch with no template behind it — the link to a block
is optional, and a standalone one-off is a first-class path, not a shortcut. Going the
other way (turning a good one-off *into* a reusable template) copies every day and row
**up** into a new block; just pointing the link would leave a block claiming to be the
source of a program while containing nothing.

- `TrainingProgramWorkout` — the editable copy of a day.
- `TrainingProgramExercise` — the editable copy of a prescription row.

### `AthleteWorkoutExerciseOverride` — the exception for one athlete
The rare case where a percent doesn't fit one specific person. It overrides the **percent**
(or the sets/reps), never a fixed weight — so the athlete's bar still moves with their
benchmark instead of being frozen at a number. Most athletes have none of these; it's a
thin escape hatch, not the common path.

### `ScheduledSession` — one planned slot on the calendar
"This program's Day 3, on Wednesday the 12th." Generated from the block's cadence and
duration.

> ⚠️ **The slot is a plan; the session is the real thing.** A slot starts with no session
> attached and stays that way until a coach actually creates that day. Deleting a session
> leaves its slot behind as an unrun plan, rather than erasing the fact that training was
> scheduled.

Slots are also **frozen once generated** — changing the block's cadence afterwards moves
nothing that already exists. A coach who wants a new cadence deploys again.

## World 4 — The training that actually happened

### `TrainingSession` — one training day
A window of time in the gym holding all the sets performed during it.

> ⚠️ **A session can exist before it runs.** Its start time is empty for a session that has
> been created but not started — Thursday's session, set up on Tuesday. It's filled in when
> a coach actually starts the day.
>
> So "the active session" means **started and not ended**, never merely existing. A future
> session that could quietly capture check-ins is exactly the bug this shape prevents.

A session is **shared**: several groups can be on the same one, each through its own
participation row.

### `SessionParticipation` — which group is running which day
The join that lets many groups share one session, each pointing at its own program and the
day it's running. It stores no copy of the plan — what was performed already lives in
`Set`, and what was prescribed gets frozen by the daily report at end of day.

### `Set` — one set an athlete performed
The heart of the system. One athlete, one movement, a number of reps. The row is created
the moment the set *starts*, and its summary — reps completed, average and peak bar speed —
is filled in when it *finishes*. It can be flagged a "false set" if it was aborted.

> **A set is the only permanent record that an athlete actually did something.** Deleting a
> session that contains any lifting is refused outright, rather than silently taking every
> set and rep with it. Ending a day is a timestamp, not a delete.

One flag deserves a warning: `is_coach_adjustment` marks a row a **coach** wrote to change
an athlete's carried-forward working weight, not a real lift. It looks exactly like a
completed set, so every count, status, report, and chart has to consciously exclude it.

### `Rep` — one individual repetition
The finest detail: a single rep with its exact speed, how long it took, and its
green/yellow/red color. This is what the whole sensor system exists to capture.

> ⚠️ **The second big gotcha:** rep rows are **only** created all at once, when a set
> finishes — never one at a time as they happen. While the athlete is lifting, reps are
> held on the tablet, and the whole batch is saved in one go at the end. This keeps the
> workout safe if the gym's WiFi blips mid-set.

### `RackCheckIn` — who's at which rack, right now
A sign-in sheet: every time an athlete checks in at a rack, one row is added. Nobody ever
edits or deletes a row — the **newest** row says which rack they're at, so moving racks
just adds a newer row and they leave the old rack's list. A rack's "hot list" and the
room's live "who's lifting / resting / ready" view are both just *questions asked of this
sheet plus the set times* — nothing extra is stored.

### `AthleteReferenceMax` — an athlete's *current* benchmark strength
The anchor number every percent multiplies against. Two things make it unusual:

- **It is not a lifetime personal best.** It's what the athlete can do *now*, so it can go
  **down** as well as up. If someone comes back weaker, this drops, and their prescribed
  weights drop with it. Lifetime bests are a separate idea, worked out from set history.
- **It only ever adds, never edits.** Each new benchmark writes a brand-new row. The
  athlete's current benchmark is simply their **newest** row for that movement. You get the
  full history of how their strength changed, for free, and nothing is ever lost.

A benchmark can be typed in by a coach or estimated by the system from velocity data — a
`source` field tells them apart. `rep_basis` keeps the honest original fact (a 3-rep effort
is not a 1-rep effort).

*Think of it as:* a dated logbook — you always trust the most recent page, but every old
page is kept.

### `DailyReport` — the frozen record of a finished day
Written once when a session ends, never edited. It holds the **entire day as a snapshot**:
roster, every athlete's sets and reps, racks used, room totals.

> **This is the one deliberate exception to "work it out, don't store it".** A report has to
> keep saying what was true on the day it was made. If it were recalculated on demand, a
> coach editing next week's plan — or an athlete's benchmark drifting — would silently
> rewrite last month's history. Immutability *is* the feature.

**A daily report and a reference max are not the same thing**, and they're easy to confuse:
the report freezes *a day*, the reference max tracks *a person's strength over time*.
Ending a day writes a report **and** may add new reference-max rows — two separate outputs.

## How the connections read in plain English

- An **athlete** belongs to many **training groups**; a group has many athletes.
- A **training group** is run by one or more **coaches**, and trains one or more
  **programs** over time.
- A **block** is a template; deploying it **copies** its days and rows into a **program**.
  Neither can edit the other afterwards.
- A **program** has many days (**program workouts**), each with many prescription rows
  (**program exercises**) — and each row stores a **percent**, never pounds.
- A **program** can be laid onto a calendar as many **scheduled sessions**, each of which
  may or may not have become a real session yet.
- A **session** hosts many groups (via **participations**) and contains many **sets**; a
  **set** is made of many **reps**.
- An **exercise** ties the plan, the benchmarks, and the results together, so an athlete's
  plan, strength, and performance for a movement all line up on one identity.
- A **node** measured many **sets** — if a node is removed, its sets survive and simply
  forget which sensor took them.
- A **rack screen** connects to nothing directly; it finds its sensor only by sharing a
  rack number.

## Mini-glossary

| Term you'll see | What it means here |
|---|---|
| **Table** | A list of one kind of thing (athletes, sets, …). Like a spreadsheet tab. |
| **Row / record** | One item in that list — one athlete, one set. |
| **Field / column** | One detail about it — a name, a weight, a timestamp. |
| **Points to / belongs to** | A row remembering which other row it's tied to (a set → its athlete). |
| **Many-to-many** | A two-way "many" link (athletes ↔ groups; exercises ↔ tags). |
| **Velocity** | How fast the bar moved, in meters per second — the core measurement. |
| **Velocity zone** | The bar-speed range that counts as "on target" for a prescribed set. |
| **False set** | A botched or aborted set, recorded as such and counted as zero reps. |
| **Reference max** | An athlete's *current* working benchmark for a movement. Not a lifetime best. |
| **Target percent** | The percent of that benchmark a plan prescribes. Pounds are worked out from it. |
| **Block vs. program** | Block = reusable template, no dates. Program = a dated copy given to a group. |
| **Node** | The sensor on the bar. |
| **Rack screen** | The tablet at the rack. (Separate from the node!) |

## What used to be here

Two tables you may see referenced in older notes are **gone**, and knowing why saves
confusion:

| Old table | What happened |
|---|---|
| `Program` | The per-athlete plan, one typed weight per person per movement. Replaced by the block/program hierarchy: a plan now belongs to a **group** and stores a **percent**. Dropped in migration `0011`. |
| `Session` | Renamed `TrainingSession` in migration `0012`, so the name says which of the four "session-ish" ideas it is. Full rename list in the P9 rename list. |

*The 24 tables above are the current model. If it changes, the source of truth is
[`django/event_handler/models.py`](https://github.com/devi-walto/Edge-Athlete-Remote/blob/main/django/event_handler/models.py) — keep this overview
in step with it.*

::::::

## How it all connects

Every table below sits somewhere on this. For a plain-English tour of each one, see
{doc}`database-tables`.

```{include} ../../_erd.md
:parser: myst
```

## Where the training numbers live

Every value a coach or sports scientist might argue with sits in **one file** —
`services/tuning.py` — beside the functions that use them: how generous the one-rep-max
estimate is, which rep counts are trusted, how the bar is rounded, how long "resting"
lasts.

Two deliberate exclusions, both documented in that file:

- **Operational limits stay next to the code they protect** (upload size caps, page
  limits). They guard one piece of code rather than expressing a view about training,
  and keeping the tuning file short is what keeps it findable.
- **The rep colour threshold cannot move.** The tablet computes each rep's colour and
  sends it; the server only stores what it was told. There is no second copy to change.
  Moving it means editing the frozen rack contract *and* accepting that every colour
  already stored was computed under the old rule.

## Who computes what

Some fields in the {doc}`message-contract` are worked out, not sent raw by the hardware.

Getting this wrong is the most likely way two parts disagree.

| Field | Who computes it | How |
|---|---|---|
| `velocity_color` | **the rack tablet**, per rep | Compare the rep's velocity to the *exercise's* velocity zone (`velocity_zone_min/max`), sourced from `session_exercises[]` in the `GET /api/sessions/active/` response the tablet already fetched once at rack-assignment time (Phase 10/11) — **not** `GET /api/prescriptions/`, which the v2 rack-screen flow no longer calls. `green` = on target, `yellow` = dropping, `red` = fatigued. Included when the tablet sends the set-complete body. |
| `rep_number` (saved) | **the rack tablet** | Numbered `1..N` within the set. The tablet owns set boundaries, so it assigns the authoritative number; the node's `rep_number` is only advisory ordering. |
| `is_velocity_pr` | **Django**, at set-complete | `true` if this set's `peak_velocity` beats the athlete's previous best for that exercise. |
| `is_weight_pr` | **Django**, at set-complete | `true` if this set's `weight_lbs` beats the athlete's previous heaviest for that exercise. |

## One session, several groups — and an athlete in two of them

**What forced it.** A weight room is rarely one group. Varsity football lifts as a
team, and the receivers also have position work, in the same room on the same day. A
receiver is in both. Somebody has to decide what that one athlete does today — and it
should not be the athlete at the rack, or a coach picking a plan for each person.

**What we chose.** Three small rules that add up:

- **An athlete can be in several training groups.**
- **A training program belongs to exactly one group.** A group can have several programs.
- **A training session can hold several programs at once**, one `SessionParticipation`
  row each, each saying which day that group is running.

Then, when an athlete checks in, the server works out their plan fresh
(`services/plan_resolution.py`):

1. Take the programs **in this session**, and keep the ones whose group **this athlete
   is in**. For a lineman that is one program; for a receiver it is two.
2. **Combine the lists**, the bigger group's work first, so the team lift comes before
   position work.
3. **One entry per movement.** If both plans prescribe the same movement, **the lighter
   percentage wins**, and it brings its own sets and reps with it.
4. Apply any exception a coach wrote for that athlete, then turn each percentage into
   pounds against the athlete's own current max.

A worked example, with a 200 lb max on everything:

| | Varsity Football | Receivers | What a receiver does |
|---|---|---|---|
| Back Squat | 5 × 3 at 80% | 3 × 5 at 70% | **3 × 5 at 70% — 140 lb** (the lighter plan, whole) |
| Bench Press | 3 × 5 at 75% | — | 3 × 5 at 75% |
| Power Clean | 4 × 2 at 70% | — | 4 × 2 at 70% |
| Deadlift | — | 3 × 1 at 60% | 3 × 1 at 60% |

Four movements, squat once. A lineman in the same session sees football's three and
nothing else. Nobody configured anything per athlete.

**What we rejected, and why.**

- **A program that belongs to several groups.** It reads like the obvious answer and
  it cannot express the case that matters: football and receivers need *different*
  programs. It would also have put the group on the wrong side of the join that
  everything above depends on.
- **A session that belongs to one group.** Then two groups in the room at once would be
  two sessions, and only one training day can be open at a time.
- **Listing a shared movement twice.** Progress is counted per movement. A duplicate
  makes the same completed sets show up twice and corrupts the set counter the rack
  screen relies on.
- **The heavier plan winning, or averaging the two.** A coach lowers a group's number
  on purpose, to take load off. The lower number is the deliberate one.
- **Mixing one plan's load with the other's sets and reps.** That is a prescription
  nobody wrote. The winning row is taken whole.

**What it cost.**

- **An athlete's plan for the day is stored nowhere.** It is worked out each time it
  is asked for. "Why is his squat at 70%?" can only be answered by looking at both
  programs. What was actually prescribed is frozen into the daily report when the day ends.
- **It only happens if both programs are on the session.** The server has supported
  that from the start; the coach's screens have not. Setting a day up from the calendar
  puts one program on the session, and nothing in the interface adds a second. Until
  that is built, the demo seed command is the only thing that produces a shared session.
- **"Bigger group first" is a rule of thumb.** It is right for a team lift followed by
  position work, and it is the first thing to revisit if a coach wants to set the order.

The rule has a test that uses exactly this example:
`test_two_groups_combine_and_the_lighter_prescription_wins`.

---

<!-- SCHEMA SECTION START — generated by docs/refresh-schema.py -->

<!-- Clusters below are ## so this document keeps a single H1. -->

Grouped by what they are for. Every table's schema comes straight from `models.py`, so
it cannot drift; the writing around it is ours.

:::{note}
`id` is not listed. Every table has one — an automatic whole number, assigned by the
database, unique forever. You never set it yourself.

The column tables are generated. Anything you write around them is preserved — see
`docs/refresh-schema.py`.
:::

## The room

The physical things in the gym, and the screens standing at them.

### `Node`

An ESP32 + sensor unit on a rack. Identified by node_id; a coach links it to a physical rack via rack_number. Its live fields are updated by frequent mqtt pulses.

:::::{dropdown} Schema and decisions

<!-- schema:Node:start -->
| Column | Type | Notes |
|---|---|---|
| `node_id` | text | **unique**, max 255 |
| `owner` | link → | → `Athlete`, on delete: `SET_NULL`, optional, reverse: `owned_nodes` |
| `rack_number` | whole number | optional |
| `mount_type` | text | max 10, choices: `MOUNT_CHOICES`, default `MOUNT_BAR` |
| `firmware_version` | text | optional, max 50 |
| `acquisition_kind` | text | max 16, choices: `ACQUISITION_CHOICES`, default `ACQUISITION_MQTT` |
| `battery_level` | whole number | optional |
| `signal_strength` | whole number | optional |
| `last_seen` | date + time | optional |
| `is_active` | true/false | default `True` |
| `is_simulated` | true/false | default `False` |
| `allowed_exercises` | many-to-many → | → `Exercise`, reverse: `allowed_on_nodes` |

**Table rules**

- `constraints = [models.CheckConstraint(condition=models.Q(rack_number__isnull=True) | models.Q(node_id__regex='^[A-Za-z0-9_-]{1,64}$'), name='assigned_node_id_is_mqtt_safe'), models.UniqueConstraint(fields=['rack_number'], condition=models.Q(rack_number__isnull=False), name='node_one_per_assigned_rack')]`
<!-- schema:Node:end -->


**Decisions.** `allowed_exercises` is a **hardware fact, not a schedule** — what this
sensor's rack is physically able to run. It **filters** what the tablet offers and is
never enforced by rejecting a set, so a mislabelled rack cannot block an athlete
mid-session (merge canon D9). Empty means unrestricted, so it costs a normal rack
nothing.

Two constraints carry weight. `node_one_per_assigned_rack` is what makes
one-rack-one-sensor structural rather than a rule the API remembers to apply, and it is
scoped to non-null rack numbers so any number of nodes can sit unassigned on the shelf.
`assigned_node_id_is_mqtt_safe` only bites **once a node is assigned** — an id becomes
part of an MQTT topic at that point, so it has to be topic-safe, but an unassigned node
imported from anywhere is left alone.

`acquisition_kind` lives **per node**, not as a global setting. That is what lets MQTT
sensors and WT901 Bluetooth sensors run in the same room at the same time; a system-wide
switch would have forced a gym to choose one transport for every rack.

:::::

### `RackScreen`

A tablet PWA standing at a rack. Its device_id is generated in the browser on first setup; rack_number is null until a coach assigns it. Separate from Node — a screen and its sensor are assigned independently.

:::::{dropdown} Schema and decisions

<!-- schema:RackScreen:start -->
| Column | Type | Notes |
|---|---|---|
| `device_id` | text | **unique**, max 255 |
| `rack_number` | whole number | optional |
| `last_seen` | date + time | set on save |

**Table rules**

- `constraints = [models.UniqueConstraint(fields=['rack_number'], condition=models.Q(rack_number__isnull=False), name='screen_one_per_assigned_rack')]`
<!-- schema:RackScreen:end -->


**Decisions.** The screen and its sensor are **not linked in the database**, and an FK
between them was rejected. The only thing tying them together is that a coach gave both
the same `rack_number`, assigned independently.

This is the single most common source of confusion in the schema, so it is worth saying
plainly: "Rack 3" is *whatever sensor a coach called Rack 3* plus *whatever tablet a
coach called Rack 3*. The reason to keep them apart is that they fail apart — a tablet
can be swapped without touching the sensor, and a dead sensor can be replaced without
re-provisioning the tablet.

`device_id` is generated **in the browser** on first setup rather than issued by the
server, so a screen has an identity before anyone has assigned it anything.

:::::

### `RackCheckIn`

A record that an athlete signed in ("checked in") at a rack during a session. ADD-ONLY, newest-wins — the same shape as AthleteReferenceMax. An athlete's CURRENT rack for a session is simply their newest row for that session. Because a newer check-in supersedes the older one, an athlete is only ever "owned" by one rack at a time: we assume they can't lift at two racks at once, so checking in somewhere new just moves them there. This is what a rack's HOT LIST (the fast re-pick shortcut on the check-in screen) reads from — the athletes whose newest check-in is that rack. Nothing here is meant to outlive the session.

:::::{dropdown} Schema and decisions

<!-- schema:RackCheckIn:start -->
| Column | Type | Notes |
|---|---|---|
| `session` | link → | → `TrainingSession`, on delete: `CASCADE`, reverse: `checkins` |
| `athlete` | link → | → `Athlete`, on delete: `CASCADE`, reverse: `checkins` |
| `rack_number` | whole number | — |
| `checked_in_at` | date + time | set on create |

**Table rules**

- `ordering = ['-checked_in_at']`
- `indexes = [models.Index(fields=['session', 'athlete', '-checked_in_at'], name='checkin_session_athlete_idx')]`
<!-- schema:RackCheckIn:end -->


**Decisions.** Add-only, newest-wins — the same shape as `AthleteReferenceMax`. A
"current rack" column that got updated in place was rejected: it would answer today's
question and destroy the history behind it.

Because a newer row supersedes the older one, an athlete is **only ever owned by one
rack**, and that falls out of the shape instead of being enforced. Moving racks is just
a newer row, and they leave the old rack's list automatically. The assumption underneath
is that nobody lifts at two racks at once.

A rack's **hot list** and the room's live "lifting / resting / ready" view are both just
questions asked of this sheet plus the set times — **nothing extra is stored** for
either. The index matches the only lookup that is ever done: this athlete's newest row
for this session.

:::::

### `RackRuntime`

The server-owned controller lease and transient presentation state for one rack. Completed training history remains in Set and Rep; no raw sensor data lives here.

:::::{dropdown} Schema and decisions

<!-- schema:RackRuntime:start -->
| Column | Type | Notes |
|---|---|---|
| `rack_number` | whole number | **unique** |
| `controller_screen` | link → | → `RackScreen`, on delete: `SET_NULL`, optional, reverse: `controlled_runtimes` |
| `client_instance_id` | text | max 255 |
| `controller_token_digest` | text | max 64 |
| `controller_epoch` | PositiveBigIntegerField | default `0` |
| `lease_expires_at` | date + time | optional |
| `state_version` | PositiveBigIntegerField | default `0` |
| `phase` | text | max 24, choices: `PHASE_CHOICES`, default `PHASE_IDLE` |
| `selected_athlete` | link → | → `Athlete`, on delete: `SET_NULL`, optional, reverse: `selected_at_runtimes` |
| `selected_exercise` | link → | → `Exercise`, on delete: `SET_NULL`, optional, reverse: `selected_at_runtimes` |
| `current_set` | link → | → `Set`, on delete: `SET_NULL`, optional, reverse: `runtime_states` |
| `rep_count` | whole number ≥ 0 | default `0` |
| `latest_mean_velocity` | decimal | optional |
| `latest_peak_velocity` | decimal | optional |
| `latest_color` | text | max 16 |
| `phase_started_at` | date + time | optional |
| `updated_at` | date + time | set on save |
| `owner_athlete` | link → | → `Athlete`, on delete: `SET_NULL`, optional, reverse: `owned_racks` |
| `session` | link → | → `TrainingSession`, on delete: `SET_NULL`, optional, reverse: `virtual_racks` |
<!-- schema:RackRuntime:end -->


**Decisions.** The **server** owns the controller lease, not the tablet. One screen
holds `controller_screen` plus a token digest and an expiry, so a second tablet opening
the same rack cannot start issuing commands — and a tablet that dies simply lets its
lease lapse rather than locking the rack forever.

`state_version` and `controller_epoch` are monotonic counters so a client can tell a
stale message from a current one. Broadcasts carry the revision rather than the state
itself, which is what keeps this table off the live path.

Deliberately holds **transient presentation state only** — the current phase, what is
selected, the latest velocity read. Completed training stays in `Set` and `Rep`, and no
raw sensor data is written here at all. Losing this table would cost the room its
current screen, not its history.

:::::

### `RackCommandReceipt`

A durable accepted controller-command result, preventing retry duplication.

:::::{dropdown} Schema and decisions

<!-- schema:RackCommandReceipt:start -->
| Column | Type | Notes |
|---|---|---|
| `runtime` | link → | → `RackRuntime`, on delete: `CASCADE`, reverse: `command_receipts` |
| `command_id` | uuid | — |
| `controller_epoch` | PositiveBigIntegerField | — |
| `controller_device_id` | text | max 255 |
| `client_instance_id` | text | max 255 |
| `controller_token_digest` | text | max 64 |
| `response_status` | PositiveSmallIntegerField | — |
| `response_body` | JSON | — |
| `created_at` | date + time | set on create |

**Table rules**

- `indexes = [models.Index(fields=['runtime', 'created_at'], name='rack_receipt_runtime_time_idx')]`
- `constraints = [models.UniqueConstraint(fields=['runtime', 'command_id'], name='rack_command_once_per_runtime')]`
<!-- schema:RackCommandReceipt:end -->


**Decisions.** Exists solely so a **retried command cannot happen twice**. The unique
constraint on `(runtime, command_id)` is the whole mechanism: a repeat arrives, collides,
and the stored `response_status` and `response_body` are replayed instead of the command
running again.

Storing the full response rather than just a "seen it" marker is the point — a retry
after a dropped connection gets the *same answer as the original*, not a bare
acknowledgement it has to interpret.

This is the durable half of a pattern the rest of the system does in memory, and it is
durable here because a command that fires twice on a rack is visible to an athlete
mid-lift.

:::::

## People

Who lifts, who coaches, and who trains together.

### `Athlete`

A lifter. Optionally carries an NFC tag id for tap-to-identify at a rack.

:::::{dropdown} Schema and decisions

<!-- schema:Athlete:start -->
| Column | Type | Notes |
|---|---|---|
| `name` | text | max 255 |
| `nfc_tag_id` | text | **unique**, optional, max 255 |
| `created_at` | date + time | set on create |
| `notes` | long text | — |
| `is_simulated` | true/false | default `False` |
| `is_active` | true/false | default `True` |
| `user` | one-to-one → | → `settings.AUTH_USER_MODEL`, on delete: `SET_NULL`, optional, reverse: `athlete` |
| `training_groups` | many-to-many → | → `TrainingGroup`, reverse: `athletes` |
<!-- schema:Athlete:end -->


**Decisions.** Group membership is **many-to-many and current-state only**. A football
player can also sit in a speed group, each running its own program, and which one applies
on a given day is answered by the session — whichever of their groups is participating
in it.

Adding or removing a group **never rewrites history**, because past sessions and sets
stay attached to whatever they were created under. That is why membership can be edited
freely without a coach worrying about damaging last month's records.

`nfc_tag_id` is optional and unique. Tap-to-identify is a convenience at the rack, not
the identity itself — an athlete without a tag is a complete athlete.

:::::

### `TrainingGroup`

A NAMED SUBSET of athletes who train together on one program — e.g. "Varsity Football" or "Freshman Speed". ⚠️ This is NOT the list of everyone in the system. Every registered person lives in the Athlete table; a TrainingGroup is a slice of them that a coach hangs a TrainingProgram on. A gym runs many groups at once, each on its own program, and several groups can share one session (see SessionParticipation). Membership lives on Athlete.training_groups (M2M), not here — an athlete can be in several groups at once. Long-lived: a group outlives many blocks/programs. It carries no dates and no workouts itself — it's "who trains together," not a schedule. ⚠️ The staff who run a group live in TrainingGroupCoach, not in a field here. This used to be a single `coach` FK, which could not say what a real weight room does every day: "Sarah and Mike both run Varsity".

:::::{dropdown} Schema and decisions

<!-- schema:TrainingGroup:start -->
| Column | Type | Notes |
|---|---|---|
| `name` | text | max 255 |
| `created_at` | date + time | set on create |
<!-- schema:TrainingGroup:end -->

**Why it exists.** The unit a coach hangs a program on. A gym runs several at once, each on its own program.

#### Athletes belong to groups many-to-many, not one-to-one

An athlete can be in football *and* the speed squad at once, each with its own program;
the session decides which one applies.

Membership is **current state only** — adding or removing someone from a group never
rewrites past sessions or completed sets. History stays attached to what actually
happened at the time.

#### The name is inverted from gym usage

This is a **named subset** of athletes, **not the list of everyone**. Every registered
person lives in `Athlete`; a group is a slice of them. Reading it as "the roster" is the
most common first misunderstanding of this schema.


**Decisions.** Carries **no dates and no workouts**. It is "who trains together", not a
schedule — a group outlives many blocks and programs, and giving it a date range would
have forced a new group every season.

The staff who run it live in `TrainingGroupCoach`, not in a field here. This replaced a
single `coach` FK, which could not express what a real weight room does every day:
*Sarah and Mike both run Varsity.*

`head_coach` remains as a convenience property for display and for anything needing one
name. It is **not a permission check and not the only coach** — read `coaches` when the
question is "who may run this".

:::::

### `TrainingGroupCoach`

Which staff run a TrainingGroup, and in what capacity. A join table rather than a field on TrainingGroup because a real weight room puts several people on one group — a head coach plus assistants — and a single FK can only ever name one of them. That FK is what this replaced; its value was carried over as the head coach of each group it named. ⚠️ Being listed here is currently a STATEMENT, not a permission. Nothing in the API asks this table whether a write is allowed — `IsCoach` still means "is authenticated", same as before. The canon calls this filter-not-fence, and it is deliberate: recording who runs what is useful on its own, and a real boundary can be added on top later without undoing any of this. Do not read a row here as authorization until something actually enforces it.

:::::{dropdown} Schema and decisions

<!-- schema:TrainingGroupCoach:start -->
| Column | Type | Notes |
|---|---|---|
| `training_group` | link → | → `TrainingGroup`, on delete: `CASCADE`, reverse: `coach_links` |
| `coach` | link → | → `settings.AUTH_USER_MODEL`, on delete: `PROTECT`, reverse: `training_group_links` |
| `role` | text | max 20, choices: `ROLE_CHOICES`, default `ASSISTANT` |
| `created_at` | date + time | set on create |

**Table rules**

- `constraints = [models.UniqueConstraint(fields=['training_group', 'coach'], name='one_row_per_coach_per_group')]`
<!-- schema:TrainingGroupCoach:end -->


**Decisions.** A join table rather than a field, because a single FK can only ever name
one person and real groups have a head coach plus assistants. The old FK's value was
carried over as the head coach of each group it named, so nothing was lost in the
change.

⚠️ **Being listed here is a statement, not a permission.** Nothing in the API asks this
table whether a write is allowed — `IsCoach` still means "is authenticated". The canon
calls this **filter-not-fence**, and it is deliberate: recording who runs what is useful
on its own, and a real boundary can be added on top later without undoing any of this.
Do not read a row here as authorization until something actually enforces it.

`PROTECT` on the coach FK matches what it replaced: deleting a user who still runs a
group fails loudly rather than quietly orphaning the group's staff. The unique
constraint stops the same coach being added twice and silently doubling every staff
list.

:::::

## The movement catalog

The shared vocabulary every plan and every set points at.

### `Exercise`

The catalog entry for one movement — the single official identity that every training plan, set, and reference max points at, instead of each one hand-typing the name. This is what stops "Back Squat" and "back squat" from drifting into two different movements. `is_stub` marks a row auto-created from an unrecognized import that a coach hasn't confirmed yet (used later, Phase 6).

:::::{dropdown} Schema and decisions

<!-- schema:Exercise:start -->
| Column | Type | Notes |
|---|---|---|
| `name` | text | **unique**, max 255 |
| `tags` | many-to-many → | → `Tag`, reverse: `exercises` |
| `is_stub` | true/false | default `False` |
| `created_at` | date + time | set on create |
<!-- schema:Exercise:end -->


**Decisions.** One official identity per movement, pointed at by every plan, benchmark
and set, instead of each one storing the name as text. Without it, one coach typing
"Back Squat" and another typing "back squat" would quietly split an athlete's history in
half — and the split would be invisible until someone noticed a chart was missing
months.

`name` is globally unique, which is what makes that guarantee hold.

`is_stub` marks a row auto-created from an unrecognized import that a coach has not
confirmed yet. An import that hit an unknown movement could have been rejected outright;
creating a stub instead means the import completes and the cleanup is a separate, calmer
job.

:::::

### `Tag`

A label for grouping movements (e.g. 'lower', 'push'). Just a name for now; a coach hangs these on Exercises so they can be filtered later.

:::::{dropdown} Schema and decisions

<!-- schema:Tag:start -->
| Column | Type | Notes |
|---|---|---|
| `name` | text | **unique**, max 100 |
<!-- schema:Tag:end -->


**Decisions.** Just a name, deliberately. There is no colour, no ordering and no
hierarchy, because none of that is needed to filter a movement list and each one would
have to be maintained forever.

Kept **separate from `BlockCategory`** even though both are "a name you hang on
something" — see that table for the reasoning. The short version: `Tag`'s vocabulary is
movement labels and its `name` is globally unique, so merging the two namespaces would
make a word like "Upper" ambiguous.

:::::

### `BlockCategory`

A label for finding things in the shared block catalog — "Off-season", "Football", "Freshman". ⚠️ This is deliberately NOT the existing `Tag` model, even though both are "a name you hang on something". `Tag`'s vocabulary is movement labels for Exercises ("lower", "push") and its `name` is globally unique, so reusing it would put two unrelated vocabularies in one namespace and make a word like "Upper" mean a body region or a grade level depending on what it hangs off. Two small tables are cheaper than one ambiguous one. A block has MANY of these, not one, because real categories sit on different axes: a block is honestly both "Off-season" AND "Football", and those are not competing answers to the same question. Forcing one would mean inventing combination rows ("Off-season Football"), which multiplies badly.

:::::{dropdown} Schema and decisions

<!-- schema:BlockCategory:start -->
| Column | Type | Notes |
|---|---|---|
| `name` | text | **unique**, max 60 |
| `created_at` | date + time | set on create |

**Table rules**

- `verbose_name_plural = 'block categories'`
<!-- schema:BlockCategory:end -->


**Decisions.** Deliberately **not** the existing `Tag` model. `Tag`'s vocabulary is
movement labels for exercises ("lower", "push") and its `name` is globally unique, so
reusing it would put two unrelated vocabularies in one namespace and make a word like
"Upper" mean a body region or a grade level depending on what it hangs off. **Two small
tables are cheaper than one ambiguous one.**

A block has **many** of these, not one, because real categories sit on different axes: a
block is honestly both "Off-season" *and* "Football", and those are not competing answers
to the same question. Forcing a single category would mean inventing combination rows
("Off-season Football"), which multiplies badly.

Filtering is any-of, so a block tagged both turns up under either.

:::::

## Templates — what a coach designs

Reusable training, written once and redeployed.

### `TrainingBlock`

A reusable, timeless TEMPLATE a coach designs once and redeploys (tweak last year's block, run it again next year). Deliberately has no group and no dates — those only exist once a TrainingProgram instantiates it. ⚠️ This name is intentionally the OPPOSITE of the old, retired meaning ("Block" used to be a dated phase owned by a group) — here it's purely the template. Carries a duration/cadence so a future calendar-generator feature can auto-place sessions from it later. That generator isn't built yet — this just keeps the door open without inventing more structure than needed today.

:::::{dropdown} Schema and decisions

<!-- schema:TrainingBlock:start -->
| Column | Type | Notes |
|---|---|---|
| `coach` | link → | → `settings.AUTH_USER_MODEL`, on delete: `PROTECT`, reverse: `training_blocks` |
| `name` | text | max 255 |
| `categories` | many-to-many → | → `BlockCategory`, reverse: `blocks` |
| `duration_weeks` | whole number | optional |
| `cadence_days_of_week` | text | max 100 |
| `created_at` | date + time | set on create |
| `updated_at` | date + time | set on save |
<!-- schema:TrainingBlock:end -->

**Why it exists.** The reusable template a coach designs once and redeploys, season after season.

#### The block is the template, not a dated phase

⚠️ **Inverted from common strength-and-conditioning usage on purpose.** In normal gym
speech a "block" is a dated phase of training. **Here the block is the reusable
template**, and `TrainingProgram` is the dated instance created from it.

Anyone arriving with coaching background reads this backwards at first. It is the
single most likely source of a misreading in the whole schema.

#### Reading the hierarchy

Four table names carry most of the confusion, because **they are inverted from common
gym usage on purpose**. Each one's dropdown explains itself; the shape is:

```
TrainingBlock   →   TrainingProgram   →   TrainingGroup   →   TrainingSession
  template            instance             squad              one shared timeslot
```

:::{warning}
**That arrow is "bigger idea → smaller idea." It is NOT the foreign-key direction.**
The actual keys point differently, and deliberately so. Reading one as the other
produces a confidently wrong mental model of the whole schema — the most likely way to
misread this database.
:::


**Decisions.** No group and no dates — those exist only once a `TrainingProgram`
instantiates it. That absence is the whole point of the table: it is what makes a block
redeployable next season instead of a record of one season.

⚠️ The name is intentionally the **opposite** of its old, retired meaning. "Block" used
to be a dated phase owned by a group; here it is purely the template. Older documents
using the old sense are wrong, not subtly different.

`duration_weeks` and `cadence_days_of_week` were written long before anything read them
— they existed to keep the door open for a calendar generator without inventing more
structure than the day needed. `ScheduledSession` is the feature that finally reads
them.

⚠️ `updated_at` is a trap worth knowing. `auto_now` only fires when **this** row is
saved, and most edits are to a day or a prescription row inside the block. Those are
still edits to the template, so every write touching a descendant has to call
`touch_block()` in `services/planning.py` — or the "recently edited" sort quietly
lies.

:::::

### `TrainingBlockWorkout`

One ordered workout inside a block's template (e.g. "Day 1: Squat").

:::::{dropdown} Schema and decisions

<!-- schema:TrainingBlockWorkout:start -->
| Column | Type | Notes |
|---|---|---|
| `training_block` | link → | → `TrainingBlock`, on delete: `CASCADE`, reverse: `workouts` |
| `name` | text | max 255 |
| `position` | whole number ≥ 0 | — |

**Table rules**

- `ordering = ['position']`
- `constraints = [models.UniqueConstraint(fields=['training_block', 'position'], name='block_workout_unique_position')]`
<!-- schema:TrainingBlockWorkout:end -->


**Decisions.** Ordering is an explicit `position` column with a unique constraint per
block, not an implicit sort by id or name. Days get reordered and inserted between
others, and an id order cannot express that without rewriting rows.

The unique constraint means two days cannot claim the same slot — which also makes
**swapping two days a two-step operation**, the same trade `ScheduledSession` makes for
dates.

:::::

### `TrainingBlockExercise`

One prescription row inside a block workout — the MASTER copy a program snapshot-copies from at instantiation. Always a percent of the athlete's reference max plus a velocity zone, never an absolute weight.

:::::{dropdown} Schema and decisions

<!-- schema:TrainingBlockExercise:start -->
| Column | Type | Notes |
|---|---|---|
| `training_block_workout` | link → | → `TrainingBlockWorkout`, on delete: `CASCADE`, reverse: `exercises` |
| `exercise` | link → | → `Exercise`, on delete: `PROTECT`, reverse: `training_block_exercises` |
| `position` | whole number ≥ 0 | — |
| `sets` | whole number ≥ 0 | — |
| `reps` | whole number ≥ 0 | — |
| `target_percent` | decimal | — |
| `velocity_zone_min` | decimal | optional |
| `velocity_zone_max` | decimal | optional |

**Table rules**

- `ordering = ['position']`
- `constraints = [models.UniqueConstraint(fields=['training_block_workout', 'position'], name='block_exercise_unique_position')]`
<!-- schema:TrainingBlockExercise:end -->


**Decisions.** Always a **percent** of the athlete's reference max plus a velocity zone,
**never an absolute weight**. This is the rule the whole schema is built around: one
prescription serves thirty athletes, and each one's bar is resolved when the row is
read.

If you go looking for a target-weight column here and cannot find one, that is the design
working, not a gap.

This is the **master copy**. A program snapshot-copies from it at instantiation rather
than pointing at it — see `TrainingProgram` for why.

:::::

## Programs — a template placed in time

A block scheduled for a real group, on real dates.

### `TrainingProgram`

A scheduled INSTANCE for a group, placed in time. Usually instantiated from a TrainingBlock (its prescription gets snapshot-copied down at creation time), but training_block is NULLABLE — a coach can also build a standalone one-off program with its own prescription and no template behind it. Both are permanent, first-class paths, not a migration shim. ⚠️ This docstring used to claim that promoting a one-off into a reusable template was "just adding a TrainingBlock row and pointing this FK at it". **That was false**, and it was repeated in several places before anyone checked. Setting `training_block` records where a program CAME FROM; it copies nothing. Pointing it at a fresh block would produce a block claiming to be the source of this program while containing zero days — and deploying that block would hand a group an empty plan. Promotion is `instantiate_block()` run backwards: create the block, copy every day and prescription row UP into it, and only then point the FK. That is `promote_program_to_block()` in services/planning.py (P15).

:::::{dropdown} Schema and decisions

<!-- schema:TrainingProgram:start -->
| Column | Type | Notes |
|---|---|---|
| `training_group` | link → | → `TrainingGroup`, on delete: `CASCADE`, reverse: `programs` |
| `training_block` | link → | → `TrainingBlock`, on delete: `PROTECT`, optional, reverse: `programs` |
| `name` | text | max 255 |
| `start_date` | date | — |
| `end_date` | date | optional |
| `created_at` | date + time | set on create |
<!-- schema:TrainingProgram:end -->

**Why it exists.** A block placed in time for a specific group. The dated thing.


**Decisions.** Deploying **copies** every day and prescription row down into the
program's own tables rather than pointing at the block's. That keeps the two independent:
editing a deployed program changes only that group's plan, and editing the template
changes only *future* deployments. Neither can reach back and rewrite the other — which
is what stops a coach tidying a template from silently altering a season already in
progress.

`training_block` is **nullable** on purpose. A standalone one-off program with its own
prescription and no template behind it is a first-class path, not a migration shim.

⚠️ **A correction worth reading, because the wrong version was repeated in several
places before anyone checked.** This docstring used to claim that promoting a one-off into
a reusable template was "just adding a `TrainingBlock` row and pointing this FK at it".
**That was false.** Setting `training_block` records where a program *came from*; it
copies nothing. Pointing it at a fresh block would produce a block claiming to be the
source of this program while containing zero days — and deploying that block would hand a
group an empty plan. Real promotion is `instantiate_block()` run backwards: create the
block, copy every day and row **up** into it, and only then point the FK. That is
`promote_program_to_block()` in `services/planning.py`.

:::::

### `TrainingProgramWorkout`

The editable copy of a TrainingBlockWorkout, living on this program instance. Editing this affects only this program; editing the block affects future instances instantiated from it later.

:::::{dropdown} Schema and decisions

<!-- schema:TrainingProgramWorkout:start -->
| Column | Type | Notes |
|---|---|---|
| `training_program` | link → | → `TrainingProgram`, on delete: `CASCADE`, reverse: `workouts` |
| `name` | text | max 255 |
| `position` | whole number ≥ 0 | — |

**Table rules**

- `ordering = ['position']`
- `constraints = [models.UniqueConstraint(fields=['training_program', 'position'], name='program_workout_unique_position')]`
<!-- schema:TrainingProgramWorkout:end -->


**Decisions.** The editable copy of a block day. Editing it affects **only this
program**; editing the block affects only instances deployed later.

Same explicit `position` and unique constraint as its template counterpart, for the same
reason — a copied plan has to survive being reordered.

:::::

### `TrainingProgramExercise`

The editable copy of a TrainingBlockExercise — the runtime prescription row. The absolute target is always DERIVED at read time (target_percent × the athlete's CURRENT AthleteReferenceMax, which itself keeps updating as new session data comes in) — never stored here as a fixed number.

:::::{dropdown} Schema and decisions

<!-- schema:TrainingProgramExercise:start -->
| Column | Type | Notes |
|---|---|---|
| `training_program_workout` | link → | → `TrainingProgramWorkout`, on delete: `CASCADE`, reverse: `exercises` |
| `exercise` | link → | → `Exercise`, on delete: `PROTECT`, reverse: `training_program_exercises` |
| `position` | whole number ≥ 0 | — |
| `sets` | whole number ≥ 0 | — |
| `reps` | whole number ≥ 0 | — |
| `target_percent` | decimal | — |
| `velocity_zone_min` | decimal | optional |
| `velocity_zone_max` | decimal | optional |

**Table rules**

- `ordering = ['position']`
- `constraints = [models.UniqueConstraint(fields=['training_program_workout', 'position'], name='program_exercise_unique_position')]`
<!-- schema:TrainingProgramExercise:end -->

**Why it exists.** Where a prescription actually lives — the movement, the sets and reps, and **the percentage**. Note what is *not* here: any column holding a weight in pounds. Weight (b) in the three-weights table is derived from this row plus the athlete's reference max, and never stored.

#### A plan stores a percentage, never a weight

A coach prescribes "Back Squat 5×3 at 80%" once, for a whole group. There is no
target-weight column anywhere in the database. The actual number on the bar is worked
out *when the screen asks for it*, against that athlete's own current max.


**Decisions.** The absolute target is **derived at read time** — `target_percent` ×
the athlete's *current* reference max — and never stored here as a fixed number.

That matters more than it looks. The reference max keeps moving as new session data
arrives, so a stored target would be correct at the moment it was written and slowly
wrong afterwards, with nothing to indicate it had drifted. Deriving costs a lookup and
is always right.

It also means prescribed weights follow an athlete **down** as well as up, which is the
intended behaviour and the thing most people try to "fix" first.

:::::

### `AthleteWorkoutExerciseOverride`

A coach-set per-athlete EXCEPTION for one prescription row — for the rare outlier where a percent doesn't fit that specific athlete. Overrides the PERCENT, never a static weight — the derivation still multiplies whatever's overridden here against the athlete's current reference max, so it stays dynamic instead of freezing a number in time. Most athletes need no override at all; this is a thin escape hatch, not the common path.

:::::{dropdown} Schema and decisions

<!-- schema:AthleteWorkoutExerciseOverride:start -->
| Column | Type | Notes |
|---|---|---|
| `athlete` | link → | → `Athlete`, on delete: `CASCADE`, reverse: `workout_exercise_overrides` |
| `training_program_exercise` | link → | → `TrainingProgramExercise`, on delete: `CASCADE`, reverse: `athlete_overrides` |
| `target_percent` | decimal | optional |
| `sets` | whole number ≥ 0 | optional |
| `reps` | whole number ≥ 0 | optional |
| `updated_at` | date + time | set on save |

**Table rules**

- `constraints = [models.UniqueConstraint(fields=['athlete', 'training_program_exercise'], name='athlete_override_unique_per_exercise'), models.CheckConstraint(check=models.Q(target_percent__isnull=False) | models.Q(sets__isnull=False) | models.Q(reps__isnull=False), name='athlete_override_at_least_one_field')]`
<!-- schema:AthleteWorkoutExerciseOverride:end -->


**Decisions.** Overrides the **percent**, never a static weight. The derivation still
multiplies whatever is overridden here against the athlete's current reference max, so an
overridden athlete's bar stays dynamic instead of being frozen at a number — the one
property the whole percent-based design exists to protect.

A check constraint requires **at least one** of percent, sets or reps to be set, so an
override row cannot exist while overriding nothing. Unique per athlete per prescription
row, so there is never a question of which override wins.

Most athletes have none of these. It is a thin escape hatch, and it was kept thin on
purpose — a general per-athlete plan editor would have made the group prescription
meaningless.

:::::

### `ScheduledSession`

One planned training slot: this program's day N, on this date. WHAT THIS IS FOR, plainly: a coach deploys an 8-week block that trains Mon/Wed/Fri and wants to see it on a calendar. Before this, nothing turned `start_date` + cadence into actual dates — `cadence_days_of_week` and `duration_weeks` were written and never read by anything. ⚠️ THE SLOT IS A PLAN; THE SESSION IS THE REAL THING. `session` is nullable and stays null until a coach actually creates that day. This separation is why the change is small: no model is asked to mean two things, and a `TrainingSession` still only exists when someone means to run it. ⚠️ SLOTS ARE FROZEN ONCE GENERATED. Editing the block's cadence afterwards moves no existing slot — the same independence rule as a deployed program. Once a program is an instance it is its own thing; a coach who wants the new cadence deploys the block again. Moving a single slot is one `date` write and regenerates nothing.

:::::{dropdown} Schema and decisions

<!-- schema:ScheduledSession:start -->
| Column | Type | Notes |
|---|---|---|
| `training_program` | link → | → `TrainingProgram`, on delete: `CASCADE`, reverse: `scheduled_sessions` |
| `training_program_workout` | link → | → `TrainingProgramWorkout`, on delete: `CASCADE`, reverse: `scheduled_sessions` |
| `date` | date | — |
| `session` | link → | → `TrainingSession`, on delete: `SET_NULL`, optional, reverse: `scheduled_slots` |
| `created_at` | date + time | set on create |

**Table rules**

- `ordering = ['date', 'id']`
- `constraints = [models.UniqueConstraint(fields=['training_program', 'date'], name='one_slot_per_program_per_day')]`
<!-- schema:ScheduledSession:end -->


**Decisions.** ⚠️ **The slot is a plan; the session is the real thing.** `session` is
nullable and stays null until a coach actually creates that day. This separation is why
the feature was small: no model is asked to mean two things, and a `TrainingSession`
still only exists when someone means to run it.

`SET_NULL` rather than `CASCADE` on that FK — deleting a session leaves its slot on the
calendar as an **unrun plan**, rather than erasing the fact that training was scheduled
at all.

**`CASCADE`, not `PROTECT`, on the program day, and the first instinct was wrong.**
`PROTECT` looked right — "don't let a day the calendar points at disappear" — but it
protected nothing and broke something: no route deletes a program day directly, while
`PROTECT` here made the whole **program** undeletable, because deleting it cascades to
its days and the slots then blocked their own parent's cleanup. A slot for a day that no
longer exists is meaningless, so it goes with it.

⚠️ **Slots are frozen once generated.** Editing the block's cadence afterwards moves
nothing that already exists — the same independence rule a deployed program follows. A
coach wanting a new cadence deploys again.

One slot per program per day stops a double-run of the generator quietly doubling a
calendar. ⚠️ It also means moving a slot **onto** an occupied date is refused rather than
stacking two days on one date — the intended answer, but it makes **swapping** two slots
a two-step operation.

:::::

## Running a training day

The live session, and which groups are on it.

### `TrainingSession`

One training session in the gym — a window of time containing many sets across the athletes who took part. A session is SHARED: several TrainingGroups can be on the same one, each via its own SessionParticipation row pointing at that group's program and the day they are running. The session itself belongs to nobody. ⚠️ `started_at` IS NULLABLE, and that is the whole of P14's schema change: **a session can exist before it runs.** Null means "created, not started yet" — Thursday's session, set up on Tuesday. It is set when a coach actually starts the day. Because of that, "the active session" means STARTED and not ended, never merely existing — see services/active_session.py. A future session that could capture check-ins is exactly the D18 failure, and nullable `started_at` is what makes it structurally impossible rather than merely guarded against. ⚠️ Never order sessions by `-started_at` without excluding nulls: Postgres sorts NULLs FIRST descending, so an unstarted future session would come back as the newest thing in the room.

:::::{dropdown} Schema and decisions

<!-- schema:TrainingSession:start -->
| Column | Type | Notes |
|---|---|---|
| `label` | text | max 255 |
| `started_at` | date + time | optional |
| `ended_at` | date + time | optional |
| `athletes` | many-to-many → | → `Athlete`, reverse: `sessions` |
| `notes` | long text | — |
| `is_simulated` | true/false | default `False` |
<!-- schema:TrainingSession:end -->

**Why it exists.** One shared timeslot when lifting happens.

#### Owned by nobody

This is a **root record**. It carries no group column, and that is deliberate: the link
to a group lives on `SessionParticipation`, which is what allows **several groups to
share one timeslot**.

Adding a group foreign key here would look like a tidy-up and would quietly break the
shared-session case.


**Decisions.** ⚠️ `started_at` is **nullable**, and that single change is what lets a
session exist before it runs — Thursday's session, set up on Tuesday. It is filled in
when a coach actually starts the day, which is why it is not `auto_now_add`.

Because of that, **"the active session" means started and not ended**, never merely
existing. A future session that could quietly capture check-ins is exactly the failure
this shape prevents — structurally, rather than by remembering to guard against it.

⚠️ **Never order sessions by `-started_at` without excluding nulls.** Postgres sorts
NULLs *first* descending, so an unstarted future session comes back as the newest thing
in the room.

The session belongs to **nobody**: several groups share one, each through its own
participation row.

:::::

### `SessionParticipation`

The join between a shared session and one group's program — this is what lets many groups be on the same session at once instead of a session belonging to just one group. Deliberately carries NO snapshot blob: what was actually performed already lives in Set/Rep, and what was prescribed gets frozen for the whole session by DailyReport at end-of-day. Storing a third copy here would be two write paths for one guarantee (see merge canon D14).

:::::{dropdown} Schema and decisions

<!-- schema:SessionParticipation:start -->
| Column | Type | Notes |
|---|---|---|
| `session` | link → | → `TrainingSession`, on delete: `CASCADE`, reverse: `participations` |
| `training_program` | link → | → `TrainingProgram`, on delete: `PROTECT`, reverse: `session_participations` |
| `training_program_workout` | link → | → `TrainingProgramWorkout`, on delete: `PROTECT`, optional, reverse: `session_participations` |
| `created_at` | date + time | set on create |

**Table rules**

- `constraints = [models.UniqueConstraint(fields=['session', 'training_program'], name='session_participation_unique')]`
<!-- schema:SessionParticipation:end -->

**Why it exists.** The join that lets several groups share one session — and the reason `TrainingSession` itself needs no group column.


**Decisions.** Deliberately carries **no snapshot blob**. What was actually performed
already lives in `Set` and `Rep`, and what was prescribed gets frozen for the whole
session by `DailyReport` at end of day. Storing a third copy here would be two write
paths for one guarantee (merge canon D14) — and two write paths eventually disagree.

`PROTECT` on the program, so a program that a session has actually run cannot be deleted
out from under it.

Unique per session per program, so a group cannot join the same session twice.

:::::

## What actually happened

Performed work, and the numbers derived from it.

### `Set`

One set an athlete performed. Created when the set starts; its summary fields (reps_completed, velocities, is_false_set) are filled in by the batch set-complete write when the set ends.

:::::{dropdown} Schema and decisions

<!-- schema:Set:start -->
| Column | Type | Notes |
|---|---|---|
| `session` | link → | → `TrainingSession`, on delete: `PROTECT`, reverse: `sets` |
| `athlete` | link → | → `Athlete`, on delete: `CASCADE`, reverse: `sets` |
| `node` | link → | → `Node`, on delete: `SET_NULL`, optional, reverse: `sets` |
| `exercise` | link → | → `Exercise`, on delete: `PROTECT`, reverse: `sets` |
| `set_number` | whole number | — |
| `weight_lbs` | decimal | optional |
| `started_at` | date + time | set on create |
| `ended_at` | date + time | optional |
| `reps_completed` | whole number | default `0` |
| `avg_velocity` | decimal | optional |
| `peak_velocity` | decimal | optional |
| `is_false_set` | true/false | default `False` |
| `is_coach_adjustment` | true/false | default `False` |
| `is_makeup` | true/false | default `False` |
| `is_simulated` | true/false | default `False` |

**Table rules**

- `ordering = ['set_number']`
<!-- schema:Set:end -->

**Why it exists.** One performed set — this is weight **(c)**, the load that was actually on the bar. It is written once, when the rack tablet submits the finished set in a single batch.


**Decisions.** **`PROTECT` on the session, not `CASCADE`.** A set is the only permanent
record that an athlete actually did something, and deleting the session it happened in
used to take every set and rep inside it with no warning and no way back. The delete is
now refused while any lifting exists, which turns a silent, unrecoverable loss into an
error message. Ending a day is `ended_at`, not a delete.

`SET_NULL` on the node, going the other way: retiring a dead sensor should not take the
training it measured with it. Those sets survive and simply forget which sensor read
them.

⚠️ **`is_coach_adjustment` is the flag most likely to produce a wrong number.** It marks
a row a *coach* wrote to change an athlete's carried-forward working weight, not a real
lift. It has to be a completed set — `ended_at` and `weight_lbs` — to move that weight,
but that same shape would otherwise count as genuine work. So every read over `Set` rows
must consciously include or exclude it: these feed `last_weight_lbs` **only**, and are
excluded from set counts, "resting" status, analytics, `has_data`/`is_makeup`, and
reports. Merge canon D15 has the exhaustive list. **Do not add a `Set` read without
deciding this.**

`weight_lbs` is stored here — unlike the plan, which stores only a percent — because this
is the load that was actually on the bar. It is a fact, not a prescription, and it is what
makes weight PRs and load-velocity analysis possible.

:::::

### `Rep`

One completed rep inside a set. Written only in bulk by the set-complete endpoint. velocity_color is the green/yellow/red zone read for the rep.

:::::{dropdown} Schema and decisions

<!-- schema:Rep:start -->
| Column | Type | Notes |
|---|---|---|
| `set` | link → | → `Set`, on delete: `CASCADE`, reverse: `reps` |
| `rep_number` | whole number | — |
| `timestamp` | date + time | — |
| `mean_velocity` | decimal | — |
| `peak_velocity` | decimal | — |
| `duration_ms` | whole number | — |
| `velocity_color` | text | max 16 |

**Table rules**

- `ordering = ['rep_number']`
<!-- schema:Rep:end -->


**Decisions.** Written **only in bulk**, by the set-complete endpoint, never one at a
time as reps happen.

This is the second big surprise in the system and it is deliberate. While an athlete is
lifting, reps are held on the tablet in browser storage; the whole batch is saved in one
request when the set ends. The database gets **one write per set**, not one per rep, and
a Wi-Fi drop mid-set loses nothing — the tablet still holds everything.

The cost accepted in exchange: a set that is never finished is never persisted at all.
See {doc}`../../journal/core/rack-screen` for the reasoning and the failure this design accepts on
purpose.

:::::

### `AthleteReferenceMax`

An athlete's CURRENT WORKING reference for one movement — the anchor number programs multiply against to build target weights. This is deliberately NOT a lifetime personal best: it tracks what the athlete can do about NOW, so it can go DOWN as well as up (a rough patch should pull prescribed weights back). Lifetime bests are a separate concept, already derivable from Set history and surfaced via the is_weight_pr / is_velocity_pr flags — do not conflate the two. ADD-ONLY history table: every recorded reference writes a NEW row, and an athlete's "current reference" for a movement is simply their newest row for it (a newer, lower number legitimately supersedes an older, higher one). We never edit or delete an old row. Progression over time is graphable for free, and a live session reads a stable snapshot (everyone's newest row) while a value entered mid-session just becomes that athlete's newest row and applies forward. A reference can be a coach-entered number OR one the system estimates from velocity data later — both live here, told apart by `source`, so you can graph how close the estimate lands to the manual value. `rep_basis` keeps the honest original fact (a 3-rep effort is not a 1-rep effort); targets convert to a common 1-rep basis when they're computed. `source_session` links an estimated row back to the session that produced it, so a later coach "publish"/re-publish (a future phase) can trace and supersede its own estimates without mutating history. Null for manual entries and for estimates not tied to a single session; SET_NULL so the reference survives if that session is ever deleted. `exercise` links to the Exercise catalog (same as Program and Set) so every reference points at one official movement identity, not a loose name string.

:::::{dropdown} Schema and decisions

<!-- schema:AthleteReferenceMax:start -->
| Column | Type | Notes |
|---|---|---|
| `athlete` | link → | → `Athlete`, on delete: `CASCADE`, reverse: `reference_maxes` |
| `exercise` | link → | → `Exercise`, on delete: `PROTECT`, reverse: `reference_maxes` |
| `reference_weight_lbs` | decimal | — |
| `rep_basis` | whole number | default `1` |
| `source` | text | max 16, choices: `SOURCE_CHOICES`, default `SOURCE_MANUAL` |
| `source_session` | link → | → `TrainingSession`, on delete: `SET_NULL`, optional, reverse: `produced_reference_maxes` |
| `recorded_at` | date + time | set on create |

**Table rules**

- `ordering = ['-recorded_at']`
- `indexes = [models.Index(fields=['athlete', 'exercise', '-recorded_at'], name='aref_athlete_exercise_idx')]`
<!-- schema:AthleteReferenceMax:end -->

**Why it exists.** The anchor. **Every prescribed weight in the entire system is a percentage of a row in this table.** Nothing else in the schema plays that role, which is why so much care is spent on it.

#### The three weights, and which lever moves which

Confusing any two of these is the most expensive mistake available on this project. It
derailed an earlier attempt at the system, which is why it is written down this plainly.

| | Weight | Where it lives | What moves it |
|---|---|---|---|
| **a** | **Reference max** — what the athlete can lift *now* | Stored in `AthleteReferenceMax`. Add-only, newest wins. | A coach entering a new one, or the recalculation when a session ends |
| **b** | **Prescribed target** — what the plan says to lift today | **Nowhere. Always derived** as a percentage of (a) | Move (a), or set a per-athlete override |
| **c** | **Actual load** — what is on the bar right now | Stored on `Set` | The athlete's number pad, or a coach adjusting today's load |

**The rule:** to change the *prescription*, move **(a)**. To change only what someone is
lifting *right now*, move **(c)**. **(b) is derived and never written.**

When a coach says "change their weight" they mean one of two different things, and the
system offers a separate lever for each. They do not compete: (a) rewrites future
targets, (c) nudges today without touching the plan.
#### It is allowed to go down

**What forced it.** This could have been a personal record — the best an athlete has
ever lifted.

**What we chose.** It is **what they can do now**, not a lifetime best. Add-only,
newest wins, and the newest value may be *lower* than the last. Prescribed weights
follow it down.

**What we rejected, and why.** Making it a high-water mark. That produces exactly the
wrong behaviour for the thing this product exists to detect: an athlete returning from
illness, or deep in a hard block, would be prescribed weights based on their best day
ever. The system is meant to notice fatigue and respond to it.

**What it cost.** It looks like a bug the first time you see it, and the tempting
"fix" — clamping it so it can only rise — breaks the core purpose.

#### How a target weight is worked out

Two of these steps are the ones people get wrong:

1. Find the athlete's **newest** reference max for that movement.
2. **Normalise it to a one-rep basis.** A max recorded as "225 for 3" is not a one-rep
   max; it is converted with a standard formula first.
3. Apply the prescribed percentage.
4. Apply a per-athlete override if one exists.
5. **Round to the nearest 5 lb**, because that is how plates load.
6. **If the athlete has no reference max, return nothing.**

**Step 6 is a decision, not an oversight.** No max means no target — do not guess, do
not substitute zero, do not error the request. An empty target is a legal value the
rack screen already handles, and the athlete can enter a load by hand. Failing soft
keeps one missing number from breaking a whole rack's session.

**Step 2 is the one people skip**, and skipping it silently inflates every prescribed
weight for any athlete whose max was recorded at more than one rep.


**Decisions.** **Add-only.** Every recorded reference writes a new row, and an athlete's
current reference for a movement is simply their **newest** row for it. Old rows are
never edited or deleted. Progression over time is graphable for free, a live session reads
a stable snapshot, and a value entered mid-session just becomes the newest row and applies
forward.

⚠️ **This is not a lifetime personal best, and a newer lower number legitimately
supersedes an older higher one.** It tracks what the athlete can do *now*, so a rough
patch should pull prescribed weights back — that is the feature. Lifetime bests are a
separate idea, already derivable from `Set` history via the `is_weight_pr` /
`is_velocity_pr` flags. **Do not conflate the two.**

`source` tells a coach-entered number from a system estimate, both living in the same
table so you can graph how close the estimate lands to the manual value. `rep_basis`
keeps the honest original fact — a 3-rep effort is not a 1-rep effort — and targets
convert to a common basis when computed.

`source_session` links an estimate back to the session that produced it, so a later
re-publish can trace and supersede its own estimates **without mutating history**.
`SET_NULL`, so the reference survives if that session is ever deleted.

:::::

### `DailyReport`

The permanent record of one finished training day — written once, never edited. WHY THIS IS STORED RATHER THAN DERIVED (the one deliberate exception to this codebase's derive-don't-store rule): a report has to keep saying what was true on the day it was generated. If we recomputed it on demand, a coach editing next week's program — or an athlete's max drifting — would silently rewrite last month's history. Immutability IS the feature here, so the whole day gets frozen into `snapshot` at the moment the session ends. `snapshot` holds the entire report as JSON (roster, each athlete's sets and reps, which racks they used, room totals) so reading a report never depends on the live tables it came from. `schema_version` lets an older stored snapshot still be read correctly after the shape evolves.

:::::{dropdown} Schema and decisions

<!-- schema:DailyReport:start -->
| Column | Type | Notes |
|---|---|---|
| `session` | one-to-one → | → `TrainingSession`, on delete: `PROTECT`, reverse: `daily_report` |
| `schema_version` | whole number ≥ 0 | default `1` |
| `generated_at` | date + time | set on create |
| `snapshot` | JSON | — |

**Table rules**

- `ordering = ['-generated_at', '-id']`
- `indexes = [models.Index(fields=['-generated_at', '-id'], name='daily_report_newest_idx'), GinIndex(models.Func(models.F('snapshot'), models.Value('$.athletes[*].athlete.id'), function='jsonb_path_query_array'), name='daily_report_athlete_ids_gin')]`
- `constraints = [models.CheckConstraint(check=models.Q(schema_version__gte=1), name='daily_report_positive_schema_version')]`
<!-- schema:DailyReport:end -->


**Decisions.** **Stored, not derived — the one deliberate exception to this codebase's
derive-don't-store rule.** A report has to keep saying what was true on the day it was
generated. Recomputed on demand, a coach editing next week's program — or an athlete's
max drifting — would silently rewrite last month's history. **Immutability is the
feature**, so the whole day is frozen into `snapshot` the moment the session ends.

`snapshot` holds the entire report as JSON — roster, each athlete's sets and reps, racks
used, room totals — so reading a report never depends on the live tables it came from.
`schema_version` lets an older stored snapshot still be read correctly after the shape
evolves.

⚠️ **A daily report and a reference max are not the same thing**, and they are easy to
confuse: the report freezes *a day*, the reference max tracks *a person's strength over
time*. Ending a day writes a report **and** may add new reference-max rows — two separate
outputs of one action.

The GIN index exists because "which reports mention this athlete?" is the main way
reports get browsed, and the answer lives inside the JSON rather than in a column. It is
**Postgres-only**, which is fine here — the base station always runs Postgres. The query
works without it, just slower.

:::::

## System

Plumbing, not training data.

### `MonitoringEvent`

A durable record that "something changed" — written the instant it happens; a separate publisher loop delivers it to the dashboard afterward and marks it published. Adopted from Braydon's realtime/ layer: sturdier than a fire-and-forget MQTT publish, because a dropped connection just leaves the row unpublished for the next attempt instead of losing the update outright.

:::::{dropdown} Schema and decisions

<!-- schema:MonitoringEvent:start -->
| Column | Type | Notes |
|---|---|---|
| `event_id` | uuid | **unique**, default `uuid.uuid4` |
| `reason` | text | max 32 |
| `occurred_at` | date + time | set on create |
| `published_at` | date + time | optional |
| `publish_attempts` | whole number ≥ 0 | default `0` |
| `last_error` | text | max 255 |
| `is_simulated` | true/false | default `False` |
<!-- schema:MonitoringEvent:end -->


**Decisions.** A durable row written the instant something changes, with a separate
publisher loop delivering it afterward and marking it published — rather than publishing
to MQTT directly at the moment of the change.

A fire-and-forget publish was rejected because a dropped broker connection loses the
update outright and nothing notices. Here the row simply stays unpublished until the next
attempt, and `publish_attempts` and `last_error` say what went wrong.

Adopted from Braydon's `realtime/` layer. The broadcast carries a **revision number, not
the state itself** — clients refetch when they hear the number moved, which keeps
privacy-sensitive detail off the broker entirely. See {doc}`../../journal/core/real-time`.

⚠️ Its absence is a real failure mode, not a theoretical one: the wall display once sat
on stale numbers for an entire session because `session_start` never wrote one of
these.

:::::


## Unsorted

New tables that have not been filed into a group yet. Add them to `CLUSTERS` in `docs/refresh-schema.py`.

### `InstallationSetup`

Persistent, locked first-run marker; never inferred from a deleted account. Enrollment also needs a secret that only someone with access to the base station itself can obtain, otherwise whoever loads the website first claims the installation. `setup_code_hash` holds a one-way hash of a short, locally-issued code — never the code itself — so a database leak does not hand out the claim token. The code expires and is cleared on first success.

:::::{dropdown} Schema

<!-- schema:InstallationSetup:start -->
| Column | Type | Notes |
|---|---|---|
| `completed_at` | date + time | optional |
| `setup_code_hash` | text | max 255, default `''` |
| `setup_code_created_at` | date + time | optional |
| `setup_code_expires_at` | date + time | optional |
<!-- schema:InstallationSetup:end -->

<!-- TO FILL IN: move these two lines out of this comment, then retitle
     the dropdown above from 'Schema' to 'Schema and decisions'.

**Why it exists.** (what this table is for, in one or two sentences)

**Decisions.** (what was chosen here, and what was rejected)
-->

:::::

### `CoachProfile`

Per-coach account state that is not part of Django's User table. Only `must_change_password` today: an administrator creates a coach with a temporary password, and that flag makes the first sign-in change it before the rest of the app is reachable.

:::::{dropdown} Schema

<!-- schema:CoachProfile:start -->
| Column | Type | Notes |
|---|---|---|
| `user` | one-to-one → | → `auth.User`, on delete: `CASCADE`, reverse: `coach_profile` |
| `must_change_password` | true/false | default `False` |
<!-- schema:CoachProfile:end -->

<!-- TO FILL IN: move these two lines out of this comment, then retitle
     the dropdown above from 'Schema' to 'Schema and decisions'.

**Why it exists.** (what this table is for, in one or two sentences)

**Decisions.** (what was chosen here, and what was rejected)
-->

:::::

### `AthleteLoginLink`

A one-time link a coach sends an athlete, to make (or remake) their login. Treated like a password: the link itself is never stored, only a one-way hash of its secret part, the same way Django stores passwords. It works once, expires after 3 days, and a newer link cancels it. All of that is checked in services/login_links.py; this table only records what happened.

:::::{dropdown} Schema and decisions

<!-- schema:AthleteLoginLink:start -->
| Column | Type | Notes |
|---|---|---|
| `token_hash` | text | max 128 |
| `lookup` | text | **unique**, max 16 |
| `created_at` | date + time | — |
| `expires_at` | date + time | — |
| `used_at` | date + time | optional |
| `cancelled_at` | date + time | optional |
| `athlete` | link → | → `Athlete`, on delete: `CASCADE`, reverse: `login_links` |
| `created_by` | link → | → `settings.AUTH_USER_MODEL`, on delete: `SET_NULL`, optional, reverse: `+` |
<!-- schema:AthleteLoginLink:end -->

**Why it exists.** Athletes never create their own logins. A coach sends a personal
link, and using it makes the athlete's login. This table records each link (spec 03).

**Decisions.**
- The link is `<lookup>.<secret>`. `lookup` finds the row directly; the secret is
  stored only as a hash, so a copy of the database can't be used to claim a login.
- Every failure (wrong, expired, used, cancelled, unknown) gives the same answer, so
  nobody can learn which.
- Using a link switches the old login off and renames it (`<name>~replaced-<id>`), so
  the athlete can keep their username. The old login row is kept, not deleted.
- An archived athlete's link stops working, so a link can't switch an archived
  athlete's login back on.
- Rejected: storing the link itself; a separate "forgot password" path (a new link
  does both).
- **Built on the shared one-time rows** (2026-10-19, spec 14). The first six columns
  come from `OneTimeSecret`, an abstract model with no table of its own; making,
  finding and using up the link follow `services/one_time_secrets.py`, which the
  first-run setup code and sensor claim codes use too. Nothing in this table changed.

:::::

### `SensorClaimCode`

A one-time code an athlete gives their sensor, so the sensor can claim itself. The athlete gets it on their athlete page ("Add my sensor"); the sensor sends it to the school with its ID, and gets its own sensor token back (spec 14). Treated like a password (see OneTimeSecret). It works once, for 15 minutes, and a newer code cancels the older. Checked in services/sensor_claims.py; this table only records what happened.

:::::{dropdown} Schema and decisions

<!-- schema:SensorClaimCode:start -->
| Column | Type | Notes |
|---|---|---|
| `token_hash` | text | max 128 |
| `lookup` | text | **unique**, max 16 |
| `created_at` | date + time | — |
| `expires_at` | date + time | — |
| `used_at` | date + time | optional |
| `cancelled_at` | date + time | optional |
| `athlete` | link → | → `Athlete`, on delete: `CASCADE`, reverse: `sensor_claim_codes` |
| `sensor` | link → | → `Node`, on delete: `SET_NULL`, optional, reverse: `+` |
<!-- schema:SensorClaimCode:end -->

**Why it exists.** Online, an athlete adds their own sensor without anyone's help. The
code is how the school knows the sensor that sends it belongs to that athlete (spec 14).

**Decisions.**
- A code, not the athlete's account password: the account password never passes
  through the sensor, and a code can only add a sensor, once.
- Built on the shared one-time rows (`OneTimeSecret`): only a hash is stored, every
  failure gives the same answer, and wrong codes are slowed down.
- 15 minutes: long enough to set a sensor up over USB, short enough that a code left
  on a screen is worthless.
- A sensor that already belongs to someone else is refused, and the code stays usable;
  a coach removes the sensor from its owner first.
- The sensor's token is not stored here or anywhere in the database. The broker keeps
  only a salted hash of it (its dynamic security file), and the claim reply is the only
  time the token itself exists outside the sensor.
- Rejected: the athlete's account password or its hash on the sensor; the coach
  typing sensor IDs on the roster (claiming does it).

:::::
<!-- SCHEMA SECTION END -->

