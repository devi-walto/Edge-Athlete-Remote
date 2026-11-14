# Feature Spec 21: Make-ups

- Owner: Devin Walton
- Date: 2026-11-14
- Status: **Draft for Devin's review.** Not scheduled. *Proposed* points need his call.
- Depends on: [17 Locations and several sessions](17-concurrent-sessions.md) (idle
  sessions end on their own, so more sessions end with someone missing),
  [19 The rack screen](../ui/19-rack-screen.md) (only the planned reps count),
  [10 The athlete's pages](../remote/10-athlete-pages.md) (where an athlete sees it online)

## Why

An athlete misses a session (sick, a test, a game) and does the workout a day or two later.
The work should count toward the day they missed, so the coach sees the whole team finished
Thursday's plan, and the athlete's progress shows Thursday done.

The original design had this (canon Phase 7, "makeup flow"): a set could be filed into a
session that had already ended, and every set carries `is_makeup`. Some of it survives:

- **The server still accepts a set filed into an ended session** (`set_create` doesn't
  check the session is running).
- **`Set.is_makeup` exists**, and the session's completion time leaves make-ups out.

But **no screen does it**, the daily report is frozen when the session ends so a make-up
wouldn't show in it, and **today's `is_makeup` is set wrongly**: the rack screen sends
`is_makeup: has_data`, and `has_data` turns true once an athlete has finished one set in the
running session, so their later sets that same day are marked as make-ups (seen in the code,
2026-11-14; to confirm against real data). This spec gives the flag one meaning and fixes it.

## User stories

- As an athlete who missed Thursday, I want to do Thursday's workout today and have it count
  for Thursday.
- As a coach, I want to see who still owes a session, and have their make-up land in that
  day's report, without anyone's maxes being disturbed.

## Decisions (Devin, 2026-11-14)

- **The missed session leaves each absent athlete a pointer** to it. Any one-off session
  they lift later can be pointed at it: it brings in that day's plan, and their sets are
  filed into the original session as make-ups.
- **A make-up rebuilds that day's report in place:** the same report, rewritten to include
  the make-up. Never a second report.
- **A make-up never recalculates anyone's max**, the make-up athlete's included. Maxes are
  worked out once when a session ends and the newest wins; working them out again later
  would put old numbers ahead of newer ones and pull everyone's prescribed weights out of
  order. A coach who wants a max changed enters it by hand.
- **A make-up counts toward the missed session's date,** with the real lift date shown
  beside it ("made up Thu, Nov 20").

## What "is a make-up" means

**`is_makeup` is true only for a set filed into a session after that session ended.** It is
set by the server from the session, never sent by the screen. An athlete coming back to a
rack for a second movement in a running session is not making anything up. (The rack's
`has_data` keeps its other job, if any, and stops deciding this.)

## The pointer

- **Made when a session ends** (by a coach, or automatically after being idle, spec 17): one
  `MakeUp` row for each athlete who was on the session's roster and completed **no counted
  set** in it. Fields: athlete, the missed session, status (`open`, `done`, `excused`),
  made, finished.
- **Partly done** (some sets, not all): *proposed:* no pointer in the first version; the
  coach's report shows what's missing. A later phase can offer "finish the rest".
- **How long it stays open:** *proposed:* 14 days, then it closes itself as `expired` (the
  coach can still reopen it). A coach can mark it **excused** at any time.
- **Who sees it:**
  - **The athlete online:** on Home, under the focus card: "Missed: Thu, Nov 18 · Day 2 —
    Pull · Make it up". Open ones only.
  - **The coach:** on that session's report and in the athlete's analytics: who still owes
    it, who made it up and when, who was excused.

## Doing a make-up

The make-up is not a session of its own. **It's the athlete lifting the missed day's plan,
with the sets filed into the missed session.** Where they lift:

- **Online, on their own phone:** "Make it up" opens their own rack (spec 04) bound to the
  missed session in make-up mode: the rack screen shows that day's movements and the
  prescribed weights, and the sets go into the missed session. Their rack is released when
  they finish (or after the usual idle time).
- **At a gym rack, during another session:** on the rack's day view, an athlete with an open
  make-up sees "Make up Thu, Nov 18" beside today's plan. Choosing it switches the rack to
  that day's movements; the check-in still belongs to today's session (that's where they
  are), and the sets belong to the missed one. The coach's live room shows them with a small
  "Make-up: Thu" tag.
- **At a gym rack, no session running:** *proposed:* a coach starts a short session for it,
  or picks the athlete's make-up from Room Layout; to settle with the boards.
- **The prescribed weights** come from the missed day's plan and the athlete's **current**
  max (the newest one, as for any session today). The plan doesn't change, only when it's
  lifted.
- **Finishing:** the athlete (or the coach) presses **Finish make-up**, or the rack goes
  idle. Then: the pointer becomes `done`, and the missed session's report is rebuilt in
  place.

## Rebuilding the report

- **In place:** the session's one `DailyReport` row gets a fresh snapshot (the same builder
  that made it, `_snapshot`), keeping the session's original end time, plus a note of each
  rebuild (when, which make-up).
- **Never calls the max step** (`_recalculate_reference_maxes`), for anyone. A test pins
  that a rebuild leaves every max exactly as it was.
- **The PDF** shows make-up sets with their real date.

## Counting it everywhere by the session's date

The coach's athlete history dates a set by when it was lifted; the athlete's progress and
session list date it by its session. With make-ups those disagree, so: **everything counts a
make-up toward its session's date**, and shows the lift date as a note. The coach's history
changes to match (*proposed*); the team completion time keeps leaving make-ups out, as it
does now.

## Screens

Boards needed before building: the athlete's "Missed" row on Home and the make-up rack in
make-up mode; the gym rack's "Make up Thu" choice on the day view; the coach's report and
analytics showing owed, made up and excused, with Excuse.

## Phases (outline; cut properly when scheduled)

0. **The flag means one thing:** the server sets `is_makeup` from the session (ended = make-
   up); the rack stops sending it; the wrong flags already saved are corrected by a
   migration (sets in a session that hadn't ended when they were lifted are not make-ups).
1. **Pointers:** made at session end for athletes with no counted sets; open, done, excused,
   expired; the coach sees and excuses them.
2. **Rebuilding a report in place,** never touching maxes; the PDF and the report screen show
   make-ups with their real date.
3. **Online make-ups:** "Missed" on Home, the athlete's own rack in make-up mode.
4. **Gym make-ups:** the rack's "Make up Thu" choice during another session; the live room
   tag.
5. **Counting by session date** across history and progress; rehearsal: miss Thursday, make
   it up Saturday at home and Monday at a gym rack, check the report, maxes and progress.

## Acceptance criteria

- [ ] A set lifted for a missed session lands in that session as a make-up, and its report
      shows it, rebuilt in place.
- [ ] No max changes because of a make-up, for anyone.
- [ ] A second set in a running session is never marked a make-up.
- [ ] An athlete who missed a session sees it online until it's made up, excused or expired.
- [ ] Progress and history count a make-up toward the missed day, showing when it was lifted.

## Risks

| Risk | What reduces it |
|---|---|
| Maxes go out of order | A rebuild never runs the max step; tested |
| A make-up set lands in the wrong session | The pointer names the session; the rack's make-up mode shows that day's name; the server marks `is_makeup` itself |
| Old sets wrongly marked make-ups skew history | Phase 0 corrects them with a migration that keeps a list of what it changed |
| Two reports for one day | The rebuild rewrites the one `DailyReport`; it never creates another |

## Still to confirm (Devin)

1. **Partly done sessions:** no make-up in the first version (the report shows what's
   missing)? Or "finish the rest" from the start?
2. **How long a make-up stays open:** 14 days, then it closes itself?
3. **A gym make-up with no session running:** a coach starts a short session for it, or it's
   started from Room Layout?
4. **The coach's history switching to count by session date** (with the lift date shown):
   yes?
