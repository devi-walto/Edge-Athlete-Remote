# Feature Spec 10: The athlete's home page

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started. **One decision open** (does an athlete see "Recent"; see below)
- Form item: Definition of Done #4 (remote athlete access)
- Depends on: [03 Login links](03-athlete-login-links.md) (the sign-in pages),
  [04 Session link](04-session-link-and-virtual-racks.md) (the join rule and the rack screen),
  [05 Hosted mode](05-hosted-mode.md). Reads what [07 Planning](../ui/07-planning.md) schedules
- Mockup: the **REMOTE flow** row on the canvas's Final designs page —
  `F_Ath_R3` (home), `F_Ath_R3b` (home, a session is live), `F_Ath_R10` (session ended)

## Why

After spec 03 an athlete can sign in, and after spec 04 a session link puts them on
their rack. Between the two there is nothing: spec 03 lands them on a placeholder that
says "open the session link your coach sent". An athlete who signs in on a Tuesday
night has no idea what is planned, and on the day has to go and find a link in a group
chat.

## User story

As an athlete training away from the gym, I want to open the app and see what I am
doing next, and join the session from there when my coach starts it, so that I do not
depend on finding a link.

## Decisions this spec locks in

- **Home shows what is coming up for this athlete**: the calendar days of every
  Training Program whose group they are in. Read-only.
- **When a session they belong to is live, home offers Join.** The session link still
  works; a signed-in athlete just no longer needs it.
- **Dates, not times.** A calendar day has a date and no time
  (`ScheduledSession.date`), so home says "Wed, Oct 7". If scheduling ever gains a
  time, it shows up here with no other change.
- **An athlete sees only their own things.** Their own groups, their own sessions,
  their own numbers. No other athlete's name appears anywhere, in the page or in the
  response behind it.
- **Hosted only.** A gym box has no athlete logins and returns `404` for all of this.
- **No calendar file.** A download goes stale the day a coach moves a program, and
  without times it would only make all-day events. If it is ever wanted, it should be
  a subscription feed, not a download. Not in this spec.
- **The look.** Home and the sign-in pages use the coach interface's solid look
  ([spec 06](../ui/06-design-rules.md) rule 9), sized for a phone held upright. The
  lifting screen keeps the rack screen's own look, because it *is* the rack screen.

### Open decision — does an athlete see "Recent"?

The mockup shows a short **Recent** list under "Coming up", tagged TO DECIDE: the
athlete's last few finished sessions, each with sets, reps and average speed.

- **Recommendation: yes, at that summary level only.** It costs one more query over
  the athlete's own sets, it gives them a reason to open the app, and it shows nothing
  a coach has not already seen. No drill-down, no charts, no comparing to anyone.
- If the answer is no, Phase 3 is dropped and nothing else changes.

## What exists (after specs 03, 04 and 05)

- An athlete login is a Django user linked to one `Athlete` (`Athlete.user`).
- `/athlete` (sign in) and `/login-link/<link>` (spec 03 Phase 4), currently ending on
  a placeholder page.
- `POST /api/sessions/{id}/join/` and its membership rule (spec 04 Phase 1).
- `ScheduledSession`: `training_program`, `training_program_workout`, `date`, and
  `session` (empty until the day is set up). A program belongs to one group.
- `GET /api/athletes/{id}/progress/`: the athlete's plan and progress for the running
  session, already used by the rack screen.

## Scope

- One read-only route for the home page.
- The home page, with its three states: nothing live, a session live, nothing planned.
- What the athlete sees when a session ends.
- Pointing the sign-in pages at home instead of the placeholder.

## Non-goals

- The lifting screen, and the "not started yet" and "not on this session" messages
  (spec 04 Phase 3).
- A calendar file or feed. Times on sessions.
- Any athlete editing: their plan, their maxes, their groups.
- A history page with charts or set-by-set detail.
- Notifications that a session has started.

---

## Phase 0 — The route

`GET /api/athlete/home/` — athlete only, hosted only. Returns:

```
{
  "athlete":   {"name": "...", "groups": ["Varsity Football", "Receivers"]},
  "live":      {"session_id": 41, "title": "Day 2 — Pull", "groups": [...],
                "movements": ["Deadlift", "Barbell Row", "RDL"], "started_at": "..."} | null,
  "coming_up": [{"date": "2026-10-07", "title": "Day 2 — Pull", "groups": [...],
                 "movements": [...], "session_id": 41 | null}, ...]
}
```

- **`coming_up`**: calendar days dated today or later, belonging to a program whose
  group the athlete is in, whose session has not ended. Soonest first, at most ten.
  **Two programs on one date that share a session** (spec 07 Phase 3) come back as
  **one** entry naming both groups, with the movements the athlete would actually get.
  Until that phase is built, each program's day is its own entry.
- **`live`**: the session that is started and not ended **and that this athlete may
  join** — decided by the *same function* spec 04's `join` uses, so the two can never
  disagree. This includes a Quick Training Session they were put on, which has no
  calendar day. At most one.
- **`movements`** are names only, in the order the athlete would do them. Loads are
  not sent: they are worked out against the athlete's max on the rack screen.
- Nothing in the response names another athlete or a group the athlete is not in.

**Done when:**

- [ ] An athlete in one group sees that group's future days and nobody else's.
- [ ] An athlete in two groups sees both groups' days; a date the two share is one entry.
- [ ] A day whose session has ended is not listed; a day that is set up but not started
      is listed with its `session_id`.
- [ ] `live` is set exactly when `join` would succeed for that athlete and that session,
      including a Quick Training Session with no program; it is `null` otherwise.
- [ ] The response contains no athlete name other than the caller's (a test searches
      the whole body for every other athlete's name).
- [ ] A coach gets `403`, no login gets `401`, a gym box returns `404`.
- [ ] The route makes a fixed number of queries however many days there are.

**Stop. Devin reviews.**

## Phase 1 — The home page

Route `/athlete/home`. New file `react/src/athlete/Home.jsx`, opening with a
plain-language comment on why it exists. Mockups `F_Ath_R3` and `F_Ath_R3b`.

- **Top bar:** the athlete's profile image and name. Pressing it offers **Sign out**.
- **Banner:** "Hi <first name>" and their groups.
- **The top card is the one focus card**, and it has three forms:
  - **A session is live:** "Live now · started 6:02 PM", the day's title, its
    movements, and the screen's one lime button, **Join session**, which goes to
    `/session/<id>` (spec 04).
  - **Nothing live, something planned:** "Next · Wed, Oct 7", the title and movements,
    and the line "A Join button appears here when your coach starts it."
  - **Nothing planned:** a dashed "Nothing is scheduled yet. Your coach will add your
    sessions here."
- **Coming up:** the remaining days as solid rows: date and title, groups underneath.
- **Staying current:** the page asks the route again every 15 seconds while it is in
  view, so the Join button appears without a reload. It stops asking when the tab is
  hidden.
- After signing in, and after using a login link, the athlete lands here. The spec 03
  placeholder page is removed.
- Opening `/athlete/home` signed out goes to `/athlete` and comes back.

**Done when:**

- [ ] *(Frontend test)* Each of the three top-card forms renders from the matching
      response; only the live form has a lime button.
- [ ] *(Frontend test)* A shared date shows both group names on one row.
- [ ] *(Frontend test)* No time of day is shown for a planned day.
- [ ] *(Browser)* With home open, the coach starts the session: within 15 seconds the
      top card becomes "Live now" with **Join session**, with no reload.
- [ ] *(Browser)* **Join session** lands on the athlete's Ready screen.
- [ ] *(Browser)* On a 390-pixel-wide phone nothing scrolls sideways and every button
      is at least 44 pixels tall.
- [ ] *(Browser)* Sign out returns to `/athlete` and the Back button does not show home.

**Stop. Devin reviews.**

## Phase 2 — When the session ends

Mockup `F_Ath_R10`. When the coach ends the session while an athlete is on the rack
screen, the rack is released (spec 04 Phase 2). Instead of an error, the athlete sees:

- a banner, "Session ended · Your coach ended the session. Everything is saved.";
- three numbers for today: sets, reps, average speed (average speed reads "not
  measured" if every set was typed in; spec 04 3e);
- each movement with how many of its sets were done;
- **Back to home**.

The numbers come from the athlete's own sets in that session. A set that was still
open when the session ended is closed and kept by the server (spec 04 Phase 2) and is
counted.

**Done when:**

- [ ] *(Frontend test)* The rack screen losing its rack because the session ended
      shows this page, not the observer or recovery screens.
- [ ] The totals equal the athlete's rows in the session's daily report.
- [ ] *(Browser)* End the session from the coach's side mid-rest: the athlete's phone
      shows the page within a few seconds, with the right totals.

**Stop. Devin reviews.**

## Phase 3 — Recent *(only if the open decision is yes)*

The route gains `"recent"`: the athlete's last three ended sessions, each
`{date, title, sets, reps, avg_velocity | null}`, counted from their own sets (false
sets left out). Home shows them as solid rows under "Coming up".

**Done when:**

- [ ] The three most recent ended sessions the athlete lifted in are listed, newest
      first; a session they were on but did not lift in is left out.
- [ ] The numbers match the athlete's rows in each session's daily report.
- [ ] A session where every set was typed in shows "not measured" for speed.
- [ ] The route still makes a fixed number of queries.

**Stop. Devin reviews.**

---

## Acceptance criteria

- [ ] A signed-in athlete can see what is planned for them without asking anyone.
- [ ] A signed-in athlete can get into a live session without the session link.
- [ ] No page and no response shows an athlete anything about another athlete.
- [ ] A gym box has none of this.

## Risks

| Risk | What reduces it |
|---|---|
| Home says "Join" for a session `join` then refuses | Both use one membership function; Phase 0 tests them against each other |
| Another athlete's name leaks through a shared session or a group roster | The route sends group names and movement names only; a test searches the response |
| Polling every 15 seconds from many phones loads the server | The route makes a fixed, small number of queries and stops when the tab is hidden |
| "Coming up" is wrong on a shared date before spec 07 Phase 3 exists | It degrades to one row per program, which is still true; it tightens when that phase lands |
| Scope grows into an athlete history app before November 11 | Recent is three summary rows or nothing; everything else is a non-goal |

## Docs to update when done

`docs/remote/access.md` (what an athlete can see), the route table in
`docs/reference/`, and a short `docs/journal/` entry on why the athlete's home is a
read-only view of the coach's calendar and not a second planner.
