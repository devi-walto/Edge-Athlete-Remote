# Feature Spec 22: Make-ups

- Previously spec 21 (renumbered into build order, 2026-11-14)
- Owner: Devin Walton
- Date: 2026-11-14 (rewritten the same day around a make-up session, Devin's design)
- Status: **Written, not scheduled.** Needs boards before its screens are built.
- Depends on: [21 Locations and several sessions](21-locations-and-concurrent-sessions.md) (idle sessions
  end on their own, so more sessions end with someone missing),
  [11 The rack screen](../ui/11-rack-screen.md) (only the planned reps count),
  [09 The athlete's pages](../remote/09-athlete-pages.md) (where an athlete sees it online)

## Why

An athlete misses a session (sick, a test, a game) and does the workout later. The work
should count toward the day they missed, so the coach sees the team finished Thursday's
plan and the athlete's progress shows Thursday done.

The original design had a make-up flow (canon Phase 7): a set could be filed into a session
that had ended, and every set carries `is_makeup`. Some of it survives: the server still
accepts a set for an ended session, and `Set.is_makeup` exists. But **no screen does it**,
the daily report is frozen at the end so a make-up wouldn't show, and **today's `is_makeup`
is set wrongly**: the rack screen sends `is_makeup: has_data`, and it refreshes the selected
athlete from the name list every 5 seconds (`RackScreen.jsx`, the snapshot effect), whose
`has_data` turns true after the athlete's first finished set, so their later sets that day
are flagged make-ups. (Traced in the code 2026-11-14; the test stack's sets come from the
seeder, which never goes through the rack, so they can't show it.) One known effect: the
session's team completion time leaves make-ups out, so it's likely wrong for sessions
lifted on a real rack.

## User stories

- As an athlete who missed Thursday, I want to do Thursday's workout later and have it
  count for Thursday.
- As a coach, I want to run one make-up session for everyone who owes a workout, each doing
  their own missed day, and see each missed day's report fill in.

## Decisions (Devin, 2026-11-14)

- **Make-ups happen only in a make-up session.** Never offered in the middle of another
  session. A coach opens a one-off session, marks it **Make-up**, and picks who's attending
  from a **"Has make-ups"** list. That's the only setting.
- **Each athlete's missed workout appears on their screen dynamically.** One make-up session
  can hold athletes from different missed sessions, each with a different program.
- **The missed session leaves each absent athlete a pointer** to it, which is what fills the
  "Has make-ups" list.
- **Partly done sessions get no make-up** in this version; the report shows what's missing.
- **A make-up stays open 14 days,** then closes itself (a coach can reopen it). A coach can
  mark it **excused** at any time.
- **Maxes:** the make-up session ends like any session, so **the athletes who lifted in it
  get new maxes from that day's sets**, stamped when it ends: that's their newest real work,
  so newest-wins stays right. **Rebuilding the missed session's report never touches
  maxes**, so nobody else on that day's roster is affected.
- **Everything counts a make-up toward the missed session's date,** with the real date shown
  beside it ("made up Sat, Nov 20"). The coach's athlete history switches to the session's
  date to match the athlete's progress page.
- **Both reports tell the story:** the missed session's report is rebuilt in place to include
  its make-ups (marked, with a link to the make-up session); the make-up session's own report
  lists who made up which day, with links back.

## What "is a make-up" means

**A set is a make-up when it's lifted in a make-up session, for the missed session its
athlete is making up.** The server marks it (`is_makeup`, and a link to the missed session,
below); the screen never sends it. An athlete coming back to a rack for a second movement in
an ordinary session is not making anything up.

## The pointer

- **Made when a session ends** (by a coach, or automatically, spec 21): one `MakeUp` row for
  each athlete who was on the roster and completed **no counted set**. Fields: athlete, the
  missed session, status (`open`, `done`, `excused`, `expired`), made, closed, and the
  make-up session that closed it.
- **Open 14 days,** then `expired` (reopenable). `excused` by a coach any time.
- **Seen by:** the coach (that session's report, the athlete's analytics, the "Has
  make-ups" list); the athlete online, on Home: "Missed: Thu, Nov 18 · Day 2 — Pull", so they
  know they owe it (they make it up in a make-up session their coach opens; *proposed:* no
  button, just the line).

## The make-up session

- **Starting one:** the coach's usual "start a session" with one more choice, **Make-up**.
  Turned on, the group and plan pickers are replaced by the **"Has make-ups"** list: every
  athlete with an open make-up, with the day they missed ("Riley Brooks · Thu, Nov 18 · Day 2
  — Pull"). The coach ticks who's here. **One missed session per athlete per make-up
  session**: an athlete who owes two picks one (the oldest is ticked by default) and does the
  other another day.
- **What's stored:** an ordinary `TrainingSession` with `is_makeup_session`, one
  `SessionParticipation` per athlete as now, each gaining `makeup_for` (the missed session).
  It takes a location like any session (spec 21), so with one location it runs on its own,
  never alongside a regular session; a school with more locations included could run one
  next to another.
- **The rack and the athlete's phone:** nothing new on screen. When an athlete taps in, the
  rack asks for their day as it always does (`athlete_progress`, plan resolution by athlete
  and session); for an athlete on a make-up session, the server answers with **their missed
  session's plan**, prescribed from their **current** max (the newest, as for any session).
  The rack's header shows the make-up session's name; *proposed:* the athlete's day view
  adds a small "Make-up for Thu, Nov 18" line so nobody wonders why the plan differs.
  Online athletes join through the session link like any session.
- **The sets:** filed into the **make-up session** (so its live room, "At this rack", next-set
  numbers and statuses all work unchanged), each marked by the server with `is_makeup` and
  `makeup_for` (the missed session). Nothing is ever written into an ended session.
- **Ending it** (the coach, or idle, spec 21), as any session: its own report; new maxes
  for the athletes who lifted in it, from its sets; then, for each athlete who lifted, their
  pointer becomes `done` and their missed session's report is rebuilt. An athlete who was
  ticked but didn't lift keeps their pointer open.

## Rebuilding the missed session's report

- **In place:** the session's one `DailyReport` row gets a fresh snapshot from the same
  builder, which now also takes sets made up for it (`makeup_for` = this session), keeping
  the session's original end time, plus a note of each rebuild (when, which make-up session).
- **Make-up sets in it** are marked "Made up Sat, Nov 20" with a link to the make-up
  session's report; the PDF prints the same.
- **Never runs the max step.** Tested: after a make-up, only the athletes who lifted in the
  make-up session have new maxes; everyone on the missed session is unchanged.

## Counting by the missed session's date

The athlete's progress and session list already date sets by their session; with
`makeup_for` they use the missed session's date for make-ups. The coach's athlete history
switches from the lift date to the session date the same way, showing the lift date as a
note. The team completion time keeps leaving make-ups out, and the make-up session's own
completion time is not compared with regular sessions.

## Screens

Boards needed before building: the **Make-up** choice and the "Has make-ups" list when
starting a session; the "Make-up for …" line on the rack's day view; the athlete's "Missed"
row on Home; the coach's report and analytics showing owed, made up (with links) and
excused, with Excuse and Reopen; the make-up session's report listing what was made up.

## Phases (outline; cut properly when scheduled)

0. **The flag means one thing:** the server marks make-ups; the rack stops sending
   `is_makeup`; a migration clears the flags saved wrongly (sets in ordinary sessions), and
   keeps a list of what it changed.
1. **Pointers:** made at session end for athletes with no counted sets; open, done, excused,
   expired after 14 days; the coach sees, excuses and reopens them.
2. **The make-up session:** Make-up when starting a session, the "Has make-ups" list,
   `makeup_for` on each participant, plan resolution from the missed session, sets marked by
   the server.
3. **Ending it:** its own report and maxes as any session; pointers done; each missed
   session's report rebuilt in place, never touching maxes; both reports linked; the PDF.
4. **Counting by the missed session's date** in progress, the session list and the coach's
   history; the athlete's "Missed" line on Home.
5. **Rehearsal:** two athletes miss two different sessions; one make-up session for both,
   one at a gym rack and one on their phone; check both missed reports, the make-up report,
   whose maxes changed (only theirs) and progress.

## Acceptance criteria

- [ ] A coach starts a make-up session, ticks athletes from "Has make-ups", and each sees their
      own missed workout on the rack or their phone.
- [ ] Their sets land in the make-up session, linked to the missed one, and the missed
      session's report shows them, rebuilt in place, with a link to the make-up.
- [ ] Only the athletes who lifted in the make-up session get new maxes; nobody else's change.
- [ ] A second set in an ordinary session is never marked a make-up.
- [ ] No make-up is ever offered during an ordinary session.
- [ ] Progress and history count a make-up toward the missed day, showing when it was lifted.

## Risks

| Risk | What reduces it |
|---|---|
| Maxes go out of order | Only the make-up session's own lifters get maxes, stamped at its end (their newest work); the rebuild never runs the max step; tested |
| A set counts toward the wrong day | `makeup_for` comes from the participant row the coach ticked, set by the server; the day view names the missed day |
| Old sets wrongly flagged skew history | Phase 0 corrects them and keeps a list |
| Two reports for one day | The rebuild rewrites the one `DailyReport`; it never makes another |
| A make-up session blocks the room | It's a session like any other; with one location it simply runs when the room is free |
