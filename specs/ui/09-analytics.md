# Feature Spec 9: Analytics

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started
- Form item: #11 (unified coach interface)
- Depends on: [06 Design rules](06-design-rules.md)
- Mockup: `V4e_Athlete`, `V4f_History`, `V4g_Group`, `V4h_Notes` in
  [`mockups/coach-ui-final.html`](mockups/coach-ui-final.html)

## Why

Devin: "This is where I feel the most clunkiness is."

- **History and Reports overlap.** Reports has an "Athlete days" mode that lists the
  same days History does, in less detail, through **its own second athlete picker**.
- **The at-risk marker is buried.** An athlete who has been getting slower is flagged
  only in Analytics → History → switch to Group → pick a group → the Trend column.
  Nothing anywhere else hints that it exists.
- **It is computed in the browser**, one request per athlete, so it cannot be shown
  anywhere else without repeating that cost.
- **The athlete's name is printed three times in a row** on the Athlete tab.

### What each tab does today

Clicked through on 2026-10-06 (screenshots in `ui-captures/` outside the repo):

| | History | Reports |
|---|---|---|
| One athlete | Days → open a day → every set (avg, peak, reps, first-to-last, mini bars) → **Compare reps** | "Athlete days": the same days, own picker → a plainer list of the same sets |
| A group | Each athlete: last trained, sets, average velocity, trend | — |
| The whole room | — | "Daily reports": every finished day → each athlete's sets and reps |
| Only here | Date range; rep comparison; trend | **The frozen record**, including what was prescribed; **Download PDF** |

So "Athlete days" is a weaker copy of History, and Reports adds exactly three things:
the whole-room view, the frozen record, and the PDF.

## Decisions this spec locks in

- **History absorbs Reports.** ANALYTICS has three tabs: **Athlete · History · Notes**.
- **One scope switch on History: Athlete · Group · Everyone.** "Everyone" is the
  whole-room list that Daily reports was.
- **Every day row carries its report.** A finished day is **Frozen** with a **PDF**
  button; a day whose session is still open says so.
- **Opening a day looks the same in every scope**, with what was planned as one line at
  the top.
- **Only "Showing <name>" is removed** from the Athlete tab. The picker and the
  overview card stay.
- **"Behind" is worked out on the server** and shown wherever an athlete's name is.
- **Announcements about at-risk athletes appear only on group views**, as a general
  banner — "Athletes at risk in this group" with a count — that names nobody. The flag
  itself rides on each athlete's own row. **Never an announcement on a single-athlete tab.**
- **Behind keeps its meaning:** slower than the session before on at least 3 of the
  athlete's last 5 training days, judged on their whole history, not the date range.

## What exists today

- `STATE_TABS.analytics = ["athlete", "history", "notes", "reports"]` in `Dashboard.jsx`.
- The athlete picker row, with "Showing <b>name</b>" beside it.
- History: `react/src/coach/GroupHistory.jsx`, `groupHistory.js` (with tests),
  `historyRange.js`. The scope toggle (Athlete / Group) and range (14d / 30d / 90d,
  from/to) appear only on History.
- `groupHistory.js` builds group rows from each athlete's day summaries.
  `BEHIND_DOWN_DAYS = 3`, `BEHIND_OF_LAST = 5`. The screen prints "Built from N requests".
- Reports: `ReportsWorkspace` with **Daily reports** / **Athlete days**, an "Athlete
  filter" select, **Open report**, **Download PDF**. Routes: `reports/`
  (`?athlete=`), `reports/{id}/`, `reports/{id}/pdf/`. Report rows print raw ISO timestamps.
- A report is frozen when a day ends and is never regenerated (`DailyReport`); it holds
  what was prescribed ("effective at day end") and the sets as saved.
- Clicking an athlete's row in the group table does nothing.
- Notes: one text field per athlete, with a character count and **Save note**. Quick
  notes from SESSION are appended to it.

## Non-goals

- New analytics (fatigue detection, insights). Those are stubs today and stay stubs.
- Changing what a report contains or how the PDF looks.
- An athlete's own "my history" page.

---

## Phase 0 — Small removals

- Remove "Showing <name>" beside the picker.
- Remove "Built from N requests…" and the "server-local" wording.
- Report and history rows show dates a coach would write ("Sun, Aug 2"), not ISO strings.

**Done when:**

- [ ] *(Frontend test)* The athlete's name appears once in the control row.
- [ ] *(Frontend test)* No row renders a raw ISO timestamp.
- [ ] *(Browser)* Athlete, History, Notes and Reports all still work.

**Stop. Devin reviews.**

## Phase 1 — "Behind", on the server

- `services/trends.py` (new): the rule from `groupHistory.js`, in Python. Same
  constants, same definition of a training day and of "down".
- Port the cases in `groupHistory.test.js` to Python tests with the same inputs and
  expected outputs, **before** changing the frontend. The JavaScript tests stay until
  Phase 4 as the reference.
- `GET /api/analytics/trends/` — coach only — optional `?group=<id>`. One query's worth
  of work, not one per athlete. For each athlete: `athlete_id`, `last_trained`,
  `trend` (`up` · `down` · `flat` · `none`), `change`, `behind`, `down_count`,
  `judged_over`.
- The athlete list (`GET /api/athletes/`) adds `behind`, `down_count`, `judged_over`
  for coaches, so the roster and the rack list do not need a second call.
- On a hosted installation an athlete never receives these fields about anyone else.

**Done when:**

- [ ] Every ported case gives the same answer in Python as in JavaScript.
- [ ] An athlete with fewer than the needed days is `behind: false` with `trend: "none"`
      — never flagged for lack of data.
- [ ] The endpoint makes a fixed number of queries whatever the group's size (an
      assert-num-queries test with 5 athletes and with 50).
- [ ] Changing the date range does not change `behind`.
- [ ] A coach gets it; an athlete and no login are refused.

**Stop. Devin reviews.**

## Phase 2 — The marker follows the athlete

Spec 06's `RiskTag`, fed by Phase 1:

| Where | Form |
|---|---|
| Roster rows (spec 07) | the tag "Behind 4/5", and the row tinted |
| A group's athlete list (spec 07) | the tag |
| SESSION's rack list (spec 08) | the small red triangle beside the name |
| Analytics → Athlete | the tag under the name, with one line: "Slower than the session before on 4 of the last 5 Training Sessions." |
| Analytics → History, Group scope | Phase 4 |

If specs 07 or 08 have not landed, add the tag to the screens that exist now and carry
it across when they are rebuilt.

**Done when:**

- [ ] *(Frontend test)* Each place renders the tag for a behind athlete and nothing for others.
- [ ] *(Frontend test)* The Athlete and Notes tabs render no banner or count about other athletes.
- [ ] *(Browser)* Mark one athlete behind in test data; they are flagged in all four places.

**Stop. Devin reviews.**

## Phase 3 — History absorbs Reports

Mockup `V4f`.

- The control row — scope, picker, range — is shared by all of ANALYTICS; the range
  shows only where it applies.
- **Scope: Athlete.** The focus card is the open Training Session: its date and name,
  "Planned: …" from the report's prescription (or from the program when the session is
  still open), sets, reps and average velocity, then the set rows with **Compare reps**.
  Earlier sessions are quiet rows: date, sets, reps, average velocity, change, the
  report state, **Open**.
- **Scope: Everyone.** The same list of days for the whole room (what Daily reports
  listed): athletes, sets, reps per day. Opening one shows each athlete as a row that
  opens to their sets.
- **Report state on every row:** *Frozen* and a **PDF** button when the day has a
  report; *Session still open* when it does not.
- Remove the Reports tab, `ReportsWorkspace`'s two-mode toggle and its athlete filter.
  Keep the report detail and PDF calls; they now sit behind History's rows.
- A direct link to an old report still works: it opens History on that day.

**Done when:**

- [ ] *(Frontend test)* ANALYTICS shows three tabs.
- [ ] *(Frontend test)* There is one athlete picker on the screen in every scope.
- [ ] Everything Reports could do is reachable: open a finished day for the whole room;
      open one athlete's day; download either PDF.
- [ ] *(Browser)* With today's five simulated sets: open today → five sets → Compare reps.
- [ ] *(Browser)* A finished day shows Frozen and its PDF downloads.
- [ ] *(Browser)* The numbers in an opened finished day match that day's PDF.

**Stop. Devin reviews.**

## Phase 4 — History by group

Mockup `V4g`.

- A banner at the top when anyone in the group is behind: **"Athletes at risk in this
  group"**, the count, and the definition in one line. **It names nobody.**
- The table lists every athlete in the group, **at-risk first**, each at-risk row
  tinted with its "Behind n/5" tag. Columns: last trained, sets, average velocity, trend.
- **Open** on a row switches to Athlete scope for that athlete. (Rows do nothing today.)
- The data comes from Phase 1's endpoint. Delete the per-athlete fetching in
  `GroupHistory.jsx`, and `groupHistory.js` with its tests once the Python tests cover
  the same cases.

**Done when:**

- [ ] *(Frontend test)* The banner shows only when at least one athlete is behind, and
      contains no athlete's name.
- [ ] *(Frontend test)* At-risk athletes sort first.
- [ ] *(Frontend test)* Loading a group makes one request, not one per athlete.
- [ ] *(Browser)* Open an athlete from the group table.

**Stop. Devin reviews.**

## Phase 5 — Athlete and Notes

Mockups `V4e`, `V4h`.

- **Athlete:** the overview card is the focus card. Two large numbers lead — **best set
  average** and **last session** — because a gap between them is the quickest sign of a
  drop. The other figures (completed sets, total reps, highest peak, heaviest load,
  last five sessions) sit below as a quiet row. "Performance by movement" becomes quiet
  rows, each with its own trend.
- **Notes:** the note is the focus card, with **Save note** as the one lime button, and
  a line saying quick notes from a Session land at the bottom of it.

**Done when:**

- [ ] *(Frontend test)* The overview renders with full history, with one session, and
      with none (no divide-by-zero, no "NaN").
- [ ] *(Browser)* Save a note; add a quick note from SESSION; it appears at the bottom
      of the same note.

---

## Carried in from spec 01 — archived athletes in the picker

Decided 2026-10-06. Spec 01 added archiving: an archived athlete leaves the roster and
every picker, and their sets are kept. That left a gap on this side: ANALYTICS → Athlete
and History choose an athlete from a list, an archived athlete is no longer on it, so
their own page cannot be opened even though all of their data is still there. (Their
sets do still show inside each saved daily report.)

Build it with whichever phase of this spec reworks the athlete picker:

- The picker lists active athletes as it does now, then, under a divider labelled
  **Archived**, the archived ones. `GET /api/athletes/?include_archived=true` already
  returns them, each with `is_active`.
- An archived athlete's page is read-only and says so in one line under their name:
  "Archived. Their history is kept." No notes can be added and no plan edited.
- Archived athletes never appear in the SESSION or PLANNING pickers. This is for
  looking back only.

**Done when:**

- [ ] *(Frontend test)* The Analytics picker shows archived athletes under their own
      heading, after the active ones.
- [ ] *(Browser)* Archive an athlete who has sets; open them from the Archived part of
      the picker; Athlete and History show their data.
- [ ] *(Frontend test)* An archived athlete's page offers no way to add a note or edit
      a plan.
- [ ] No picker in PLANNING or SESSION lists an archived athlete.

## Acceptance criteria

- [ ] ANALYTICS has three tabs and one picker.
- [ ] Nothing Reports did is lost; the frozen record and the PDF are one press from any day.
- [ ] An athlete who is behind is flagged on the roster, in their group, at the rack in
      SESSION, and on their own Analytics page.
- [ ] Group views announce that athletes are at risk without naming one; single-athlete
      views announce nothing.
- [ ] "Behind" is computed once, on the server, with a fixed number of queries.
- [ ] Every screen follows spec 06.

## Risks

| Risk | What reduces it |
|---|---|
| The server's "behind" disagrees with the old browser one | Phase 1 ports the existing test cases first and keeps the JavaScript as the reference until Phase 4 |
| Folding Reports in loses the difference between "as recorded" and "frozen" | Rows say Frozen or Session still open; an opened finished day is checked against its PDF |
| History becomes overwhelming with three scopes | One control row, one table shape, detail only when a day is opened |
| A flag on a minor's name is seen by the wrong person | Coach-only fields; hosted athletes never receive them about others (spec 05) |

## Docs to update when done

`docs/journal/coach-tablet.md` (analytics), `docs/journal/apis.md` (the new route, and
Reports' routes now reached from History), `_COACH_UI_REDESIGN.md` Phase H (group
history) — add a note that the calculation moved to the server.
