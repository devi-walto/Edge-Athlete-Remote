# Feature Spec 10: The athlete's pages

- Owner: Devin Walton
- Date: 2026-10-06; rewritten 2026-11-11 after the athlete-account design was approved
- Status: Phase 0 built 2026-11-11 (`GET /api/athlete/home/`), awaiting review. No decisions
  open except the room-display button's board (Phase 6)
- Form item: Definition of Done #4 (remote athlete access)
- Depends on: [03 Login links](03-athlete-login-links.md) (the sign-in pages),
  [04 Session link](04-session-link-and-virtual-racks.md) (the join rule and the rack screen),
  [05 Hosted mode](05-hosted-mode.md), [14 Sensors online](14-sensors-online.md) (My sensor and
  Manage sensors, its Phase 10). Reads what [07 Planning](../ui/07-planning.md) schedules.
  Follows [06 Design rules](../ui/06-design-rules.md), rules 10–12
- Mockups: the **REMOTE athlete account** row on the canvas's Final designs page (approved
  2026-11-11), laid out with Home on the left and each path running right:
  `F_Ath_H1` (Home), `F_Ath_H1b` (Home, a session is live), `F_Ath_H1c` (the name menu);
  `F_Ath_L1` (All sessions), `F_Ath_L2` (a past session); `F_Ath_P1`, `F_Ath_P2`,
  `F_Ath_P2b`, `F_Ath_P2c`, `F_Ath_P2d` (My Recent Progress); `F_Ath_A1`, `F_Ath_A2` (Account). Unchanged:
  `F_Ath_R10` (session ended). The sensor boards `F_Ath_M1`, `M1b`, `M2` belong to spec 14.
  Replaced and kept only for the record: `F_Ath_R3`, `R3b`, `R3c`, `S4`, `S5`

## Why

After spec 03 an athlete can sign in, and after spec 04 a session link puts them on
their rack. Between the two there is nothing: spec 03 lands them on a placeholder that
says "open the session link your coach sent". An athlete who signs in on a Tuesday
night has no idea what is planned, and on the day has to go and find a link in a group
chat. And once a session is over, nothing shows them how they did, or whether they are
getting better.

## User stories

- As an athlete training away from the gym, I want to open the app and see what I am
  doing next, and join the session from there when my coach starts it, so that I do not
  depend on finding a link.
- As an athlete, I want to look back at a session and at how I am trending, so that I can
  see my own progress without asking my coach.

## Decisions this spec locks in

- **Six pages, and only six** (Devin, 2026-11-11). Home is the hub; every other page is
  one tap from it and has one way back:

  | Page | Opened from | What opens in place instead of a new page |
  |---|---|---|
  | **Home** | signing in; the picture in the top bar, anywhere | the live banner with Join session; the name menu |
  | **All sessions** | Home → View all sessions | older sessions as you scroll |
  | **A past session** | a Recent sessions row, or All sessions | a set's reps (compare reps) |
  | **My Recent Progress** | Home's greeting card | a movement's trend and its Est. max |
  | **Account** | the name menu | the password help |
  | **Manage sensors** | My sensor's Manage, on Home or Account | the remove confirm (spec 14 Phase 10) |

  Around them, already approved: the session (rack screen) and the Add my sensor page.
- **The top bar is the same everywhere** (spec 06 rule 12): the picture goes Home; the
  athlete's name opens the menu, which holds only **Account** and **Sign out**.
- **A drill-down page only leads back** (spec 06 rule 11): All sessions, a past session,
  My Recent Progress, Account and Manage sensors each have one back link, under the top
  bar, to where they were opened from. A past session opened from All sessions goes back
  to All sessions.
- **Home shows what is coming up for this athlete**: the calendar days of every
  Training Program whose group they are in. Read-only.
- **When a session they belong to is live, the banner turns live and Join sits inside
  it.** The session link still works; a signed-in athlete just no longer needs it.
- **Dates, not times.** A calendar day has a date and no time (`ScheduledSession.date`),
  so Home says "Wed, Nov 11".
- **An athlete sees only their own things.** Their own groups, sessions, sets and
  numbers. No other athlete's name appears anywhere, in a page or in a response behind
  it. The room display is the one shared view (below).
- **Recent sessions: the last 5**, each row only date · workout · sets done of sets
  planned (amber when short). Everything else is one tap down. A small lime
  **View all sessions ›** under the fifth row opens All sessions.
- **My Recent Progress** is the athlete's trends over a **date range they choose, the same
  control as the coach's Analytics**: 14d · 30d · 90d presets and From / To dates
  (default the last 30 days; Devin, 2026-11-11). Every number on the page is for that
  range: sessions attended and sets done, and one row per movement with its speed trend.
  There is no "current block" to work out: an athlete can be in several programs at once,
  and a date range covers all of them honestly. It is not a list of sessions; that is All
  sessions.
- **Est. max is the max the app already keeps**, never a new estimate. It is the
  athlete's newest reference max (`AthleteReferenceMax`): the one written from their best
  set when a session ends (Epley, 1–12 reps), or one the coach entered. It is the same
  number their prescribed weights are worked out from. Labelled **EST. MAX** with the
  number underneath when the app estimated it, **MAX** when the coach entered it, and
  **--** when there is none. A ⓘ opens a two-line explanation in place.
- **Units: pounds or kilograms, one remembered choice on that phone, shared with the rack
  screen's plate loader** (spec 16; Devin, 2026-11-11). Pounds by default. Every load on
  these pages (a past session's sets, the bars' loads, Top load, EST. MAX, the PDF) shows
  in the chosen unit with its unit written ("225 lb" or "102 kg"); speeds always read m/s.
  Loads are stored in pounds (`weight_lbs`) and converted only for display, kilograms to
  the nearest 0.5. **The LB | KG toggle sits inside the opened movement panel** on My
  Recent Progress (`F_Ath_P2`), beside the chart's legend; changing it there changes it
  everywhere on that phone, the plate loader included.
- **Download my report (PDF)**: the athlete's own sets only. Later this may become a more
  general athlete report instead of the coach's daily one.
- **Account is read-only**: name, username and teams are shown, and the coach manages
  them. The athlete's name is the coach's to set (spec 07's first and last name).
- **No password change and no in-app reset request** (narrow attack surface, spec 03).
  Account has a green **Changing your password?** line that opens, in place: ask your
  coach in person for a new login link; it lets you choose a new password.
- **The room display.** An athlete may open `/dashboard` (read-only) by typing it, at any
  time. Its button is shown only on their rack screen while their session is live,
  never on Home or in the menu.
- **Colours follow the approved boards**: teal is a bar's speed, amber a warning or a
  short count, lime the screen's one action, red only for removing.
- **Hosted only.** A gym box has no athlete logins and returns `404` for all of this.
- **No calendar file.** A download goes stale the day a coach moves a program. Not in
  this spec.
- **The look.** These pages use the coach interface's solid look (spec 06 rule 9), sized
  for a phone held upright. The lifting screen keeps the rack screen's own look, because
  it *is* the rack screen.

Replaced decision (2026-10-06): Home showed the last three sessions as a summary and
opening one was optional. It is now five rows, View all, and the past session page.

## What exists (after specs 03, 04, 05 and 14)

- An athlete login is a Django user linked to one `Athlete` (`Athlete.user`).
- `/athlete` (sign in) and `/login-link#<link>` (spec 03 Phase 4), currently ending on
  a placeholder page.
- `POST /api/sessions/{id}/join/` and its membership rule (spec 04 Phase 1).
- `ScheduledSession`: `training_program`, `training_program_workout`, `date`, and
  `session` (empty until the day is set up). A program belongs to one group.
- `GET /api/sessions/active/athlete/{id}/progress/`: the athlete's plan and progress for
  the running session, already used by the rack screen.
- `GET /api/athlete/sensors/` and the My sensor page (spec 14), which Home and Account
  reuse for their My sensor row.
- `AthleteReferenceMax`: append-only, newest wins, `source` manual or estimated;
  `plan_resolution.current_reference_max` reads it; `session_completion` writes the
  estimated row when a session ends.
- The coach's daily report PDF (reportlab), for Phase 4's PDF.
- Online, `/dashboard` (the room display) needs a coach login today.

## Scope

- The routes behind Home, All sessions, a past session, My Recent Progress and Account.
- The six pages and their in-place states, and the top bar.
- What the athlete sees when a session ends.
- Pointing the sign-in pages at Home instead of the placeholder.
- Letting an athlete open the room display, and its button on the rack screen.

## Non-goals

- The lifting screen itself, and the "not started yet" and "not on this session" messages
  (spec 04 Phase 3).
- Manage sensors, Swap and the live/standby rule (spec 14 Phase 10).
- A calendar file or feed. Times on sessions.
- Any athlete editing: their plan, their maxes, their name, their groups, their password.
- A speed-based max estimate.
- Another athlete's numbers anywhere except the room display.
- Notifications that a session has started.

---

## Phase 0 — The Home route

`GET /api/athlete/home/` — athlete only, hosted only. Returns:

```
{
  "athlete":   {"name": "...", "first_name": "...", "groups": ["Varsity Football", "Receivers"]},
  "live":      {"session_id": 41, "title": "Day 2 — Pull", "groups": [...],
                "movements": ["Deadlift", "Barbell Row", "RDL"], "started_at": "..."} | null,
  "coming_up": [{"date": "2026-11-11", "title": "Day 2 — Pull", "groups": [...],
                 "movements": [...], "session_id": 41 | null}, ...],
  "recent":    [{"session_id": 38, "date": "2026-11-10", "title": "Day 1 — Lower + Push",
                 "sets_done": 9, "sets_planned": 9}, ...]
}
```

- **`coming_up`**: calendar days dated today or later, in a program whose group the
  athlete is in, whose session has not ended. Soonest first, at most ten. Two programs on
  one date that share a session (spec 07 Phase 3) come back as one entry naming both
  groups. Until that phase is built, each program's day is its own entry.
- **`live`**: the session that is started, not ended, **and that this athlete may join**,
  decided by the *same function* spec 04's `join` uses, so the two can never disagree.
  Includes a Quick Training Session they were put on. At most one.
- **`recent`**: the athlete's last 5 ended sessions they lifted in, newest first.
  `sets_done` counts their sets (false sets left out); `sets_planned` counts the sets
  their plan prescribed that day.
- **`movements`** are names only. Loads are not sent: they are worked out on the rack
  screen.
- Nothing in the response names another athlete or a group the athlete is not in.

**Done when:**

- [x] An athlete in one group sees that group's future days and nobody else's.
- [x] An athlete in two groups sees both groups' days; a date the two share is one entry.
- [x] A day whose session has ended is not listed; a day set up but not started is listed
      with its `session_id`.
- [x] `live` is set exactly when `join` would succeed for that athlete and that session,
      including a Quick Training Session; `null` otherwise.
- [x] `recent` holds at most 5, newest first, leaves out a session the athlete was on but
      did not lift in, and its counts match the daily report.
- [x] The response contains no athlete name other than the caller's (a test searches the
      whole body for every other athlete's name).
- [x] A coach gets `403`, no login gets `401`, a gym box returns `404`.
- [x] The route makes a fixed number of queries however many days there are.

**Phase 0 result (2026-11-11).** `services/athlete_home.py` (the rules), `athlete_pages.py`
(the door), 13 tests in `test_athlete_home.py`. `sets_done` is the daily report's own count
(real sets, coach adjustments left out); `sets_planned` comes from
`plan_resolution.movements_for_athlete`, the function the rack screen uses, so it reflects the
plan as it stands now (the report snapshot keeps no planned count). A recent session's date
is the local date it started. Backend 764 tests pass as remote and as local.

**Stop. Devin reviews.**

## Phase 1 — Home, and the top bar

Route `/athlete/home`. New files `react/src/athlete/Home.jsx` and
`react/src/athlete/TopBar.jsx`, each opening with a plain-language comment on why it
exists. Boards `F_Ath_H1`, `H1b`, `H1c`.

- **Top bar (every athlete page):** the picture goes Home; the name opens a menu with
  **Account** and **Sign out**. On a drill-down page a back link sits under the bar.
- **Greeting card:** "Hi <first name>", their groups, and a lime **My Recent Progress ›**.
- **The banner is the one focus card**, in three forms:
  - **Live:** "● Live now · started 6:02 PM", the day's title and movements, and the
    screen's one lime button, **Join session**, inside the banner. It goes to
    `/session/<id>` (spec 04).
  - **Next:** "Next · Wed, Nov 11", title and movements, "A Join button appears here when
    your coach starts it", then the following day on one line ("Then: Fri, Nov 13 · Day 3
    — Power").
  - **Nothing planned:** "Nothing is scheduled yet. Your coach will add your sessions here."
- **My sensor:** the athlete's live sensor, "Connected · seen just now", and **Manage**
  (spec 14 Phase 10). No sensor: the Add my sensor row spec 14 already has.
- **Recent sessions:** the 5 rows from `recent`, each opening the past session (Phase 3);
  **View all sessions ›** under them.
- **Staying current:** the page asks the route again every 15 seconds while it is in
  view, so the banner turns live without a reload. It stops asking when the tab is hidden.
- After signing in, and after using a login link, the athlete lands here. The spec 03
  placeholder page is removed. Opening a page signed out goes to `/athlete` and back.

**Done when:**

- [ ] *(Frontend test)* Each banner form renders from the matching response; only the
      live form has a lime button.
- [ ] *(Frontend test)* The picture always routes Home and the name opens the menu, on
      Home and on a drill-down page; the menu holds exactly Account and Sign out.
- [ ] *(Frontend test)* A short day ("6 of 8 sets") shows amber; a full one does not.
- [ ] *(Browser)* With Home open, the coach starts the session: within 15 seconds the
      banner shows "Live now" and **Join session**, with no reload.
- [ ] *(Browser)* **Join session** lands on the athlete's Ready screen.
- [ ] *(Browser)* On a 390-pixel-wide phone nothing scrolls sideways and every button is
      at least 44 pixels tall.
- [ ] *(Browser)* Sign out returns to `/athlete` and the Back button does not show Home.

**Stop. Devin reviews.**

## Phase 2 — When the session ends

Board `F_Ath_R10`, unchanged. When the coach ends the session while an athlete is on the
rack screen, the rack is released (spec 04 Phase 2). Instead of an error, the athlete
sees: "Session ended · Your coach ended the session. Everything is saved."; today's sets,
reps and average speed ("not measured" if every set was typed in); each movement with how
many of its sets were done; **Back to home**. A set still open when the session ended is
closed and kept by the server, and counted.

**Done when:**

- [ ] *(Frontend test)* The rack screen losing its rack because the session ended shows
      this page, not the observer or recovery screens.
- [ ] The totals equal the athlete's rows in the session's daily report.
- [ ] *(Browser)* End the session from the coach's side mid-rest: the athlete's phone
      shows the page within a few seconds, with the right totals.

**Stop. Devin reviews.**

## Phase 3 — All sessions, and a past session

Boards `F_Ath_L1`, `F_Ath_L2`. The data is already saved; the coach's Analytics reads it
but is coach-only and lives inside the large `Dashboard.jsx`, so these are new
athlete-scoped routes and new, simple pages. They do not reuse or touch the coach's
screens.

- `GET /api/athlete/sessions/?before=<cursor>` — the athlete's ended sessions they lifted
  in, newest first, 20 at a time, each `{session_id, date, title, sets_done,
  sets_planned}`, and the cursor for the next page.
- `GET /api/athlete/sessions/{id}/` — the caller's own sets in that session, grouped by
  movement in the order lifted: `{date, title, groups, totals: {sets_done, sets_planned,
  reps, avg_velocity | null}, movements: [{name, sets: [{set_number, weight_lbs, reps,
  avg_velocity | null, reps_detail: [mean_velocity, ...]}]}]}`. False sets left out. A
  session the athlete did not lift in returns `404`, the same as one that does not exist,
  so the route cannot be used to discover sessions.
- **All sessions** (`/athlete/sessions`): rows grouped by month, the same row as Recent
  sessions; the next page loads as the athlete scrolls ("Loading older sessions…"). Back
  link: Home.
- **A past session** (`/athlete/sessions/<id>`): the banner (date, group, title), three
  tiles (sets done of planned, reps, average speed), one card per movement with a row per
  set ("Set 2 · 225 lb × 5 · 0.66 m/s"). **Tapping a set opens its reps in place**: one
  teal bar per rep with its speed, coloured by the same rule as the rack screen's set
  summary (`F_Ath_R8`, where a fading rep turns amber), and the drop first to last. A typed-in set reads "not measured" and does not
  open. Back link: wherever it was opened from (Home or All sessions).

**Done when:**

- [ ] The routes return only the caller's sets; athlete A asking for a session only
      athlete B lifted in gets `404`.
- [ ] Paging returns every session exactly once, newest first, with no gaps.
- [ ] The totals and per-rep speeds match the athlete's rows in that session's daily
      report.
- [ ] *(Frontend test)* A typed-in set shows "not measured", not 0.00, and has no reps to
      open.
- [ ] *(Frontend test)* The past session's back link names All sessions when opened from
      there, and Home when opened from Recent sessions.
- [ ] *(Browser)* Home → View all → scroll → a session → open a set → back → back, on a
      390-pixel-wide phone.
- [ ] The coach's Analytics screens and `Dashboard.jsx` are unchanged (`git diff`).

**Stop. Devin reviews.**

## Phase 4 — My Recent Progress

Boards `F_Ath_P1`, `F_Ath_P2`, `F_Ath_P2b`, `F_Ath_P2c`, `F_Ath_P2d` (the range control replaced
the block banner on 2026-11-11).

- **The range** works exactly as the coach's Analytics range does, and shares its code
  (`react/src/coach/historyRange.js`: the presets, `normaliseRange`, `rangeLabel`): a
  14d · 30d · 90d pill group and From / To date boxes, with a label such as "Last 30
  days". Default: the last 30 days. Choosing a preset fills the dates; editing a date
  clears the preset. A range is whole days in the school's time zone, today included.
- `GET /api/athlete/progress/?from=YYYY-MM-DD&to=YYYY-MM-DD` — athlete only, hosted only.
  Counted from the athlete's own sets in sessions inside the range (false sets left out):
  `{range: {from, to}, sessions: {done, planned}, sets: {done, planned}, movements:
  [{name, top_load_lbs, trend: [{date, top_set_avg_velocity, load_lbs}], change,
  best_rep_velocity, max: {weight_lbs, source: "estimated" | "manual"} | null}]}`.
  - `sessions.planned` counts the athlete's calendar days in the range (any of their
    programs); `sessions.done` the ones they lifted in. `sets` likewise against their
    prescriptions.
  - A movement is listed if they lifted it in the range. `trend` covers the **whole**
    range in **14 bars or fewer**, grouped by the server so the response stays small
    however long the range (Devin, 2026-11-11). The step is the **smallest one on the
    ladder session → week → month → quarter → year that gives 14 bars or fewer**: for each
    step, bars = the number of calendar periods the range touches; take the first that
    fits. So 30 days → one bar per session, 90 days → per week, a year → per month,
    20 months → per quarter, 4 years → per year.
    - A session bar is that session's top set; a week, month, quarter or year bar is the
      best top set in it.
    - Bars are whole calendar periods (weeks start Monday). A period the range only partly
      covers is marked `partial`.
    - Each point carries `bucket` (`session` | `week` | `month` | `quarter` | `year`),
      `label` ("Nov 4", "Oct 6", "Oct", "Q3 '26", "2026"), `partial`, and its speed and
      load. `change` is the last point's speed minus the first's.
  - `max` is `current_reference_max` for the movement **today**, whatever the range: the
    max their weights come from. Never recomputed here.
  - Any length of range is allowed (no cap; the ladder keeps the chart small). From after
    To is refused with `400`.
- **The page** (`/athlete/progress`, back link Home): the range card, two tiles
  (sessions, sets done), then one row per movement: name, top set, a small teal trend
  line, the change (amber when it went down).
- **Tapping a movement opens it in place**: one teal bar per point in `trend`, never
  scrolling sideways. **A legend line on top says what one bar is** ("Each bar = 1 week ·
  its best top set (m/s)"), changing with the step. **Under each bar, its period** (the
  `label`); **above it, its speed with its unit** ("0.70" over "m/s"); **inside it, its
  load with its unit** ("225 lb"), written upward in dark text on the teal (bars start tall
  enough to hold it, so every bar shows all three, units included). A second legend line
  says so: "Speed above · load inside · when, below". A
  partial period's bar is drawn lighter, with the note "Lighter bars: periods the range
  only partly covers". The **Top load** tile has the heaviest. Boards: `F_Ath_P2`
  (30 days, per session), `F_Ath_P2c` (a year, per month), `F_Ath_P2d` (20 months, per
  quarter). The collapsed row's small line is the overview; the bars are the detail.
  Then three tiles: Best rep, Top load, and
  **EST. MAX** (or **MAX** when the coach entered it, **--** when there is none), and the
  ⓘ explanation. Only one movement is open at a time.
- **Download my report (PDF)** at the bottom: the daily report's layout, limited to the
  athlete's own sets in the chosen range. Athlete only.

**Done when:**

- [ ] The tiles and trends count only the athlete's own sets inside the range (false sets
      left out) and match the daily reports for those days.
- [ ] An athlete in two programs gets one row per movement covering both.
- [ ] `trend` never exceeds 14 points: the smallest step on session → week → month →
      quarter → year that fits; a period point is its best top set; partly covered periods
      are marked `partial`.
- [ ] `max` equals today's `current_reference_max` for that movement, whatever the range;
      `source` decides EST. MAX or MAX; no max gives `null` and the page shows "--".
- [ ] From after To returns `400`; a 20-month range returns 8 quarter points.
- [ ] The PDF holds only the caller's sets in the range; another athlete's name appears
      nowhere in it.
- [ ] *(Frontend test)* A preset fills From and To; editing a date clears the preset; the
      label follows ("Last 30 days", or the two dates).
- [ ] *(Frontend test)* Opening a movement closes any other; the ⓘ text opens in place.
- [ ] *(Frontend test)* With kilograms chosen, every load on the page reads kg (converted from
      pounds, nearest 0.5) and every speed still reads m/s.
- [ ] *(Browser)* Home → My Recent Progress → 90d → open Back Squat → change From → back,
      on a 390-pixel-wide phone.

**Stop. Devin reviews.**

## Phase 5 — Account

Boards `F_Ath_A1`, `F_Ath_A2`. Page `/athlete/account`, back link Home. Read-only rows:
name ("your coach manages your name and teams"), username, teams. The My sensor row with
Manage (as on Home). **Changing your password?** in lime, which opens the coach-link
explanation in place. **Sign out of this phone** at the bottom. No route of its own: the
name, username and groups come from the athlete's session details.

**Done when:**

- [ ] *(Frontend test)* Nothing on the page edits anything except through Manage.
- [ ] *(Frontend test)* The password help opens and closes in place.
- [ ] *(Browser)* Name menu → Account → back; Sign out from Account.

**Stop. Devin reviews.**

## Phase 6 — The room display, for athletes

- **Server:** online, `/dashboard` and the routes behind it accept an athlete login,
  read-only (no route that changes anything). A coach login still works as today.
- **Button:** the athlete's rack screen shows **Room display** while their session is
  live, opening the room display. It never appears on Home or in the menu.
- **Before building:** the rack screen's button has no board yet. Draw it on the
  Proposed page and get it approved first (spec 06's Final designs rule).

**Done when:**

- [ ] An athlete login can open the room display and cannot change anything through its
      routes (each write route refuses an athlete with `403`).
- [ ] *(Frontend test)* The Room display button shows on the rack screen only while the
      session is live.
- [ ] *(Browser)* An athlete opens the room display from the rack screen mid-session and
      sees the same live data as the coach.

**Stop. Devin reviews.**

---

## Acceptance criteria

- [ ] A signed-in athlete can see what is planned for them without asking anyone.
- [ ] A signed-in athlete can get into a live session from Home without the session link.
- [ ] An athlete can look back at any session they lifted in and see each rep, and see how
      they are trending, on six pages, each one tap from Home with one way back.
- [ ] No page and no response shows an athlete anything about another athlete, except the
      room display.
- [ ] A gym box has none of this.

## Risks

| Risk | What reduces it |
|---|---|
| Home says "Join" for a session `join` then refuses | Both use one membership function; Phase 0 tests them against each other |
| Another athlete's name leaks through a shared session, a group roster or the PDF | The routes send group and movement names only; tests search each response and the PDF |
| Polling every 15 seconds from many phones loads the server | The route makes a fixed, small number of queries and stops when the tab is hidden |
| Est. max confuses athletes, or disagrees with their weights | It is the very max their weights come from, labelled EST. or not, with a ⓘ; nothing new is estimated |
| "Coming up" is wrong on a shared date before spec 07 Phase 3 exists | It degrades to one row per program, which is still true |
| The room display shows athletes more than they should see | It is the screen already on the gym's wall; Phase 6 refuses every write route to athletes |

## Docs to update when done

`docs/journal/core/remote/access.md` (what an athlete can see, and the room display),
the route table in `docs/handbook/reference/`, and a short `docs/journal/` entry on why the
athlete's pages are six read-only views, each one tap from Home.
