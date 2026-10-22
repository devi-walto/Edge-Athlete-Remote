# Feature Spec 17: Several sessions running at once (remote)

- Owner: Devin Walton
- Date: 2026-10-22
- Status: **After the class.** Written so the design isn't lost; not scheduled, not part
  of the Definition of Done. Best built with or after the coach interface redesign
  (specs 06–11), because the coach's live room changes most.
- Depends on: [13 Registry and console](13-registry-and-console.md), **built first**
  (it records which schools have this feature and applies it),
  [04 Session link and virtual racks](../remote/04-session-link-and-virtual-racks.md),
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

## User story

As a coach of one team at a school with several, I want to start and end my team's
session without touching another team's, and see only my own team in the live room.

## Decisions (Devin, 2026-10-22)

- **Remote only.** A gym box keeps one running session at a time.
- **After the class**, with the redesign. Until then, teams lifting together share one
  session (above).
- **A switch per school, off by default, that the operator turns on or off at any time**
  (Devin: the point of the spec is that this one switch decides it, so that offering it
  to some schools and not others later needs no rewrite). Details in "The switch" below.


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

## The design

Every "which session?" question becomes **"which session for this ..."**:

| Who asks | Today | With several running |
|---|---|---|
| An athlete's rack (online) | the running session | the session its rack belongs to (`RackRuntime.session`) |
| An athlete's page, joining | the session in the link | unchanged |
| The coach's live room | the running session | **their own** (spec 11: sessions of groups they coach), with a switch between running sessions |
| Starting a session | refused if one runs | allowed when the school's switch is on |
| Ending a session | the session named | unchanged; ends only that one |
| The wall display | the running session | the session chosen on that display |
| An athlete in two groups, both running | — | they join whichever link they open; one rack each, in that session |
| A gym box | one running session | unchanged |

`active_session()` stays for a gym box and for a school with the switch off; the callers
above move to the "for this rack / coach / display" versions.

## Phases (outline; cut properly when scheduled)

0. The switch: the feature in spec 13's registry and console, applied to the school's
   settings; `concurrent_sessions_allowed()`; `eactl sessions on|off`; starting a second
   session allowed only when it's on. Every existing test passes unchanged with it off.
1. The rack routes and the athlete's room views find the session through the rack.
2. The coach's live room and status: their own session first, a switch between running
   ones; room state per session.
3. The wall display chooses its session; reports, insights and the simulator per
   session.
4. Rehearsal: two coaches, two teams, two sessions at once on the demo school; ending
   one leaves the other running.

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

## Risks

| Risk | What reduces it |
|---|---|
| A set lands in the wrong session | The session comes from the rack, which belongs to exactly one; a test per caller |
| A caller still asks for "the" session and gets either one | Phase 0 makes `active_session()` refuse to answer when more than one runs, so a missed caller fails loudly in tests |
| Coaches lose track of a session left running | The live room lists every running session the coach can see, with its start time |
