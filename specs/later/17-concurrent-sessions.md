# Feature Spec 17: Locations, and several sessions running at once (remote)

- Owner: Devin Walton
- Date: 2026-10-22; **revised 2026-11-14** (locations, shared racks in several rooms,
  check-in across locations, idle sessions, setting a device's location)
- Status: **Written, not scheduled.** After spec 18 (racks that set themselves up), best
  with or after the coach redesign (specs 07–09), since the coach's live room changes most.
  Needs boards before its screens are built (see "Screens").
- Depends on: [13 Registry and console](13-registry-and-console.md), **built first**
  (it records how many locations a school may have, and applies it),
  [18 Shared racks](../remote/18-shared-racks-online.md) (rack tablets that set
  themselves up), [04 Session link and virtual racks](../remote/04-session-link-and-virtual-racks.md),
  [11 Mine first](../ui/11-mine-first.md) (a coach's own sessions come first)

## Why

A school runs one training session at a time today: starting a second is refused ("a
training day is already open"). In a gym that's right, because the racks are physical
and shared by whoever is in the room. Online, nothing is shared: each athlete has their
own rack and sensor. A school with several teams (football and track, say) can want
both lifting at the same hour, each with its own coach, start and end.

**What works today, and when it is enough:** a session can have several groups taking
part, each training its own plan (spec 07, "Add to the existing sessions?"). That is
the answer when teams lift together under one coach. It falls short when they don't:
one **End training day** ends everyone's, there is one start time, one daily report, and
one live room with both teams mixed.

**And a school with more than one weight room** (Devin, 2026-11-14): a department on a
higher plan can have teams lifting in two rooms at the same hour, each room with its own
rack tablets, TV and coach. **It stays one school, one database:** a team that trains in
the other room one day, or an athlete who moves between them, keeps one account and one
history, with no copying between rooms. (Moving data between a *local install* and the
remote server is a different feature: the data export and sync spec, not this one.)

## User stories

- As a coach of one team at a school with several, I want to start and end my team's
  session without touching another team's, and see only my own team in the live room.
- As a coach at a school with two weight rooms, I want each room's tablets, TV and session
  to be that room's, and an athlete's account to work the same in either room.

## Decisions (Devin, 2026-10-22)

- **Remote only.** A gym box keeps one running session at a time.
- **After the class**, with the redesign. Until then, teams lifting together share one
  session (above).
- **A switch per school, off by default, that the operator turns on or off at any time**
  (Devin: the point of the spec is that this one switch decides it, so that offering it
  to some schools and not others later needs no rewrite). Details in "The switch" below.

## Decisions (Devin, 2026-11-14)

- **A Location table.** Every install has at least one row; most schools (lower plans)
  have exactly one, and higher plans may have more. Each location has a **name**
  (editable in the app: "Main weight room", "Football facility") and an optional
  **address**, kept so a later feature can give athletes a link to where today's session
  is. Sessions, rack tablets and sensors refer to a location by its id.
- **One running session per location.** Two locations, two sessions at once; a second
  session in the same location is still refused. (Proposed below: the per-school switch
  becomes "how many locations this school may have", so concurrency follows locations.)
- **Checking in works across locations the way it works across racks today.** Checking in
  at a rack (a name tap or an NFC band) moves the athlete to that rack; where an athlete is
  comes from their newest check-in, whichever location it's in. Nobody can be in two
  places at once, so an athlete who taps their name in the other room simply moves there,
  and shows up in that rack's "At this rack" list, easy to find.
- **Sessions left running get a warning, and idle ones stop costing compute.** When more
  than one session has been running for an extended time, a small alert inside the coach's
  session banner names them ("Sessions left running: Main room 6 h, Football 9 h"). A
  session where no set has been completed at any of its racks for a while is **idle**,
  and is suspended automatically (not ended: ending freezes the daily report, so that stays
  a coach's choice, or a much later automatic step).
- **A device's location is picked once, with as little friction as possible.** When a
  school has more than one location, setting up a rack tablet (and a school sensor) shows
  **"Multiple locations found"** and asks where the device is, once. Rack tablets gain a
  **settings menu** to change it (and their name) on the fly. A coach's device gets a
  setting under the picture in the top bar for switching where it is.


## What exists today

- `services/active_session.py` is the one answer to "which session is running?"
  (`open_sessions()`, `active_session()`), and **"at most one" is assumed by its
  callers**: `sessions_view` and `session_start` refuse a second; the rack routes
  (`rack_state`, `rack_checkin`, `rack_checkins`, `rack_nfc_tap`), `prescriptions_view`,
  `session_detail`, `sessions_active`, `athlete_progress`, `session_status`, the live room
  (`services/room_state.py`) and the simulator (`simulate_node`) each take "the" running
  session.
- **Already per session online:** a virtual rack belongs to one session
  (`RackRuntime.session`); joining names its session (`/session/<id>`); ending names its
  session (`/api/sessions/<id>/`); a daily report belongs to one session.

## The switch

The whole feature hangs on one per-school switch. It's an entitlement, so it is kept
where nobody at the school can change it: **recorded in the registry, applied to the
school** (spec 13, "What a school may use"; decided 2026-10-22, with spec 13 built
first).

- **The record:** the school's row in `ea_registry` (spec 13), `features`: several
  sessions at once, on or off. Off unless set.
- **Applied to the school:** the console (or `eactl sessions "School" on|off`) updates
  the record, then writes `EA_CONCURRENT_SESSIONS=on|off` into the school's own settings
  (the `school-settings` ConfigMap) and restarts its django. Missing means off, so every
  school is unchanged until someone turns it on. Nothing about the school's data changes
  in either direction.
- **Read in one place:** `concurrent_sessions_allowed()` in `services/active_session.py`
  reads the school's copy. Nothing else reads it, and **the school never reads the
  registry**. A gym box answers no whatever the setting says. If the source ever moves,
  only this function changes.
- **What it decides, and only that:** whether a session may be **started** while
  another is running. Everything else (each rack, coach and display finding its own
  session) works the same with it on or off; with one session running there's only one
  to find.
- **Turning it off while several are running** ends nothing: they carry on until each is
  ended normally. Starting a new one is refused until only one is left running.

## Locations

- **The table** (fields agreed 2026-11-14, so later ideas don't each need a migration):

  | Field | What it's for |
  |---|---|
  | `name` | "Main weight room"; editable in the app |
  | `short_name` | "Main", "FB": a rack tablet's header, the TV, the brackets after a shared rack name |
  | `kind` | weight room, field or track, or online (athletes at home): an online location never shows an address or map link |
  | `address` | for a later "where's my session" link for athletes |
  | `latitude`, `longitude` | the map link without guessing from the address; later, perhaps checking a check-in happened there |
  | `timezone` | which day a late session counts as (daily reports, "still open from an earlier day"), for programs with facilities apart or online teams |
  | `color` | a small tag telling locations apart on the coach's screens, from the colour tokens only |
  | `archived_at` | retire a location without losing its history |
  | `created_at`, `updated_at` | housekeeping |

  Left out on purpose (Devin): directions for athletes, a sort order. Lists sort by name;
  the location the migration made is the default for new devices. Also left out until
  there's a use: opening hours, phone, capacity (count its racks), Wi-Fi name, an outside
  system's id; and no catch-all "extra" field (nothing checks what's in it).
- **Made with one row on every install by the migration,** named after the installation
  ("Demo U") and renamable; a local install has one forever (a gym box is one room; sync,
  in its own spec, treats a local install as one location of its school).
- **What refers to it:** a session (`TrainingSession.location`), a rack tablet
  (`RackScreen.location`, chosen at "Set up this rack"), a school sensor
  (`Node.location`: **follows the rack it's paired with**, so it's only asked for a sensor
  that's on no rack yet, in Room Layout). An online athlete's own rack has no location: it
  belongs to the session it was made for (`RackRuntime.session`), as now.
- **One location, nothing new on screen.** No picker, no "where" field, no location name in
  the banner. Everything below appears only once a second location exists.
- **Managed where?** Room Layout (or the coach's settings): add, rename, set the address,
  archive. Adding past the plan's "Locations included" is refused with a plain sentence ("Your plan includes 2 locations"). Archiving
  a location with tablets or sensors asks where they go first.

## Checking in across locations

- **Unchanged rule, wider reach:** an athlete's current rack is their newest check-in, now
  across every running session, not only one. Checking in at a rack in the other location
  moves them; the old rack's "At this rack" list loses them, the new one gains them.
- **Their sets file into the session of the rack they lift at,** so each location's daily
  report holds what was lifted there. Their history, maxes and progress are one record
  either way.
- **An athlete not on that location's roster** (their team's session is running in the
  other room, and they walk over to lift here): the rack's check-in list shows this
  session's roster, as today; a coach adds them to this session if they should be here
  (Devin, 2026-11-14: an unlikely case, keep it simple).

## Sessions left running, and idle sessions

- **The warning:** inside the coach's session banner (`SessionWidget`), once two or more
  sessions have been running longer than **4 hours** (Devin, 2026-11-14), one line names
  each with how long it has run. The existing "Still open from an earlier day" flag stays,
  per session.
- **Idle:** no set completed at any of the session's racks for **120 minutes** (Devin,
  2026-11-14: long enough for warm-ups or a team talk mid-lift). An idle session is **suspended**: its rack tablets show "No session yet",
  its live room and TV stop updating and its online athletes' racks close, so it stops
  costing compute; its data and roster are untouched and nothing is frozen. A coach
  **resumes** it (it picks up exactly where it was) or **ends** it (the daily report is
  made then).
- **Ended automatically, later:** a session suspended for **24 hours** (Devin, 2026-11-14)
  is ended as if a coach had pressed End, so a report always exists eventually.
- **Make-ups after it ends** are their own spec (to write; see the specs index): today the
  server still accepts a set filed into an ended session (the original design's make-up
  flow) and every set has `is_makeup`, but no screen does it and the daily report, frozen
  at the end, wouldn't show it.
- **Whether suspending saves compute in practice:** the live room, TV and tablets poll and
  listen only while a session runs, and online athletes' racks hold live connections; a
  suspended session has none of these. Spec 15 (usage) measures it.

## Setting a device's location

- **Rack tablet, at setup** (spec 18's "Set up this rack"): with more than one location,
  the step shows "Multiple locations found" and a pick, above the name. One location: no
  question, it's that one.
- **Rack tablet, later:** a small settings menu on the idle rack screen (beside spec 18's
  corner switch): the rack's name, its location. Changing location mid-session is refused
  while a set is open; otherwise the tablet moves and shows that location's session.
- **School sensor:** takes the location of the rack it's paired with; one on no rack is
  given a location in Room Layout ("Multiple locations found" when it's added).
- **Coach's device:** a setting under the picture in the top bar, "This device is at:
  Main weight room", switchable any time. It decides which location's session the coach's
  live room and TV open on, and where a session they start goes (changeable when starting).
- **TV (room display):** its location is its rack's (it's a rack tablet flipped by the
  corner switch), or chosen in its own settings if it's only ever a TV.

## The design

Every "which session?" question becomes **"which session for this ..."**:

| Who asks | Today | With several running |
|---|---|---|
| A rack tablet (gym or online shared rack) | the running session | the running session at its location |
| Checking in, starting and finishing a set | the running session | the session of the rack's location |
| An athlete's current rack | newest check-in in the running session | newest check-in across all running sessions |
| An athlete's rack (online) | the running session | the session its rack belongs to (`RackRuntime.session`) |
| An athlete's page, joining | the session in the link | unchanged |
| The coach's live room | the running session | **their own** (spec 11: sessions of groups they coach), with a switch between running sessions |
| Starting a session | refused if one runs | allowed when the school's switch is on |
| Ending a session | the session named | unchanged; ends only that one |
| The wall display | the running session | the running session at its location |
| Rack numbers free, 30-day clean-up (spec 18) | today's session | every running session |
| An athlete in two groups, both running | — | they join whichever link they open; one rack each, in that session |
| A gym box | one running session | unchanged |

`active_session()` stays for a gym box and for a school with the switch off; the callers
above move to the "for this rack / coach / display" versions.

**The switch becomes a count: "Locations included" (Devin, 2026-11-14: decided, and named
so it says what it limits):** instead of on/off, the registry records **how many locations
the school's plan includes**, meaning how many places it can run a session in at the same
time (1 unless set). Applied the same way (`EA_LOCATIONS_INCLUDED`, read only by
`locations_included()`), and sold that way ("Program: 2 locations included"). One running session per location follows from it, so
"several sessions at once" needs no separate switch. An online-only school with two teams
lifting at the same hour gives each its own location ("Football", "Track"); the address is
optional.

**The safety net from the first draft stays, sharper:** `active_session()` with no location
is removed, so every caller has to say which location (or rack, or session) it means. A
caller that's missed fails in the test suite instead of filing sets into the wrong session.

## Screens

New boards needed on the canvas before building (the Final designs rule): "Multiple
locations found" on Set up this rack; the rack tablet's settings menu; the coach's "This
device is at" setting under the top bar picture; the sessions-left-running line in the
banner; suspended / resume in the coach's live room; locations in Room Layout (or
settings); a location picker for a sensor on no rack.

## Phases (outline; cut properly when scheduled)

0. **Locations:** the table, one row made on every install, names and addresses, managed in
   the app, the "Locations included" count from the registry (spec 13). Nothing else changes; every test
   passes with one location.
1. **"Which session?" by location:** `active_session()` takes a location; the rack routes,
   check-in, sets, the rack screen's reads and the room view find the session through the
   rack's location; starting a session is refused only within its own location. Check-in
   moves an athlete across locations.
2. **Devices:** a rack tablet's location at setup and in its settings menu; a sensor's
   location follows its rack; the coach's "This device is at"; the TV follows its rack.
3. **The coach's view:** their own sessions first, a switch between running ones, the live
   room and TV per location; the sessions-left-running line.
4. **Idle sessions:** suspend after the idle threshold, resume, the later automatic end;
   what stops while suspended.
5. **Reports, the simulator and seeders per location;** rehearsal: two rooms, two coaches,
   two sessions at once on the demo school, an athlete moving between them, one room going
   idle and being suspended while the other keeps running.

## Acceptance criteria

- [ ] With the switch on, two sessions run at once; each coach sees and ends only their
      own; each athlete's sets land in the session they joined.
- [ ] With the switch off, and on every gym box, nothing changes.
- [ ] Turning the switch on or off needs no change to a school's data, and nothing but
      `concurrent_sessions_allowed()` reads it.
- [ ] Nobody at the school can turn it on: not an administrator, not the school's app,
      not a restored safety copy (checked by trying each).
- [ ] Turning it off while two are running ends neither; a third can't start.
- [ ] Each session gets its own daily report.
- [ ] A school with one location sees nothing new anywhere.
- [ ] An athlete checking in at a rack in another location moves there, appears in that
      rack's "At this rack", and their sets file into that location's session; their
      account and history are the same in both.
- [ ] A session idle past the threshold is suspended, stops its live updates, and resumes
      exactly where it was; ending it then makes its report.
- [ ] A rack tablet picks its location once at setup when there's more than one, and can
      change it from its settings menu (not with a set open).

## Risks

| Risk | What reduces it |
|---|---|
| A set lands in the wrong session | The session comes from the rack, which belongs to exactly one; a test per caller |
| A caller still asks for "the" session and gets either one | Phase 0 makes `active_session()` refuse to answer when more than one runs, so a missed caller fails loudly in tests |
| Coaches lose track of a session left running | The live room lists every running session the coach can see, with its start time; the banner warns when several run long; idle ones are suspended |
| Suspending a session mid-lift | Idle means no set completed at any of its racks for the threshold, and a session with a set open is never idle |
| An athlete on two running rosters | Where they are is their newest check-in, as across racks today; their sets go to the session of the rack they lift at |
| Locations add friction for a one-room school | One location shows nothing new: no picker, no field, no name |
