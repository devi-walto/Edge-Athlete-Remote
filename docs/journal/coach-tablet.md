# The coach's tools

Everything a coach touches: logging in, wiring the room together, planning training,
and reading what happened.

:::{admonition} Who built this
:class: note
**The room-layout controls** — assigning screens and sensors to rack slots,
releasing a screen, unlinking a sensor, and releasing every screen at once —
**Carl and Devin**. They sit on the rack-assignment REST API Carl built in Phase 4,
extended this sprint with the release and unlink endpoints.

**Force-clearing a wedged rack** — the escape hatch for an open set nobody can
finish — **Braydon**.

**Everything else on this page** — login, planning, the spreadsheet import, reports
and the scheduling workspace — **Devin**, delivered through the merge (P0–P15)
rather than as the Phase 14 that was originally written.
:::

:::{admonition} The redesign has shipped — in THIS repo
:class: note
The three-state console below is what this repo runs. It was merged on 2026-09-17
(`a50e3f7`), taking the coach UI from eight flat tabs to PLANNING / SESSION /
ANALYTICS.

Two shapes still exist in the world, so it is worth knowing which you are looking at:
the **team's** repo still runs the grouped-eight-tab console, recorded further down
because it is still live there and still the thing a second codebase will be compared
against.
:::

## Where the coach's code actually lives

This trips people up immediately: the folder called `coach/` is **not** the coach
admin console.

- **`react/src/coach/`** — a small, narrow folder: logging in, and assigning tablets
  and sensors to rack numbers.
- **`react/src/` proper** — the actual console: the room dashboard, the workout
  catalog, the schedule workspace, the reports workspace.

---

## Decision: rack assignment is a screen, not configuration

**What forced it.** A sensor and a tablet are separate identities with nothing
connecting them. The only thing that makes them both "Rack 3" is a coach saying so,
independently, for each one.

**What we chose.** A dedicated setup screen where that pairing happens, rather than a
config file or an automatic guess.

**Why it matters operationally.** It is the reason **a rack showing no data is
usually an assignment problem, not a hardware one.** That single sentence saves more
debugging time than anything else on this page.

**What is still missing.** There is no way to link a sensor to a rack from a screen in
the gym — the server endpoint for it exists and works, but nothing calls it from the
coach's tools. That gap is a known outstanding task.

---

## Decision: one auth boundary, and everything goes through it

**What forced it.** Coach actions are the privileged ones — creating athletes,
changing plans, assigning racks. Scattering token handling across screens is how one
screen ends up quietly unauthenticated.

**What we chose.** Every authenticated coach request goes through a single helper in
`coach/api.js`. If you are adding a coach screen, import from there rather than
writing another fetch wrapper.

The token is kept in browser storage deliberately, so a page refresh does not drop a
coach mid-session — which, during a live demo in front of a room, matters more than
it sounds.

---

## The redesign: three states instead of eight tabs

**What forced it.** The console had grown to eight tabs sitting side by side. They
were not peers — a coach uses completely different parts of it depending on *when*
they are: planning next week, running today's session, or reviewing afterwards. A flat
tab bar gave equal weight to all of it and made the common path slow.

**What we chose.** Three states, grouped by **when** rather than by feature:

| State | The coach is… |
|---|---|
| **PLANNING** | Designing training ahead of time — blocks, programs, groups, the calendar |
| **SESSION** | Running the room right now |
| **ANALYTICS** | Looking at one athlete afterwards — history, reports, notes |

**The state lives in the URL.** `/coach/planning`, `/coach/session`,
`/coach/analytics`. That makes a reload keep its place, the browser Back button work
correctly, and a specific view linkable.

**The rule that held the whole redesign together:** *no backend routes change.* The
work was a re-shelving of things that already worked, not a rewrite. Only the final
group-history feature was allowed to reconsider that, deliberately.

**What we rejected, and why.** Rebuilding each state as its own page. The three states
are meant to read as **one surface changing mode**, not three separate screens — the
navigation bar stays put and animates between them. Rebuilding on each transition
would have thrown away the live room state and refetched everything, turning a mode
change into a page load wearing a costume.

:::{admonition} A real bug this caused
:class: note
The first implementation reset the whole coach app on every state change, because
React was told to treat each state as a brand-new component. The symptom looked
cosmetic — the sliding indicator jumped instead of animating — but underneath, the
room state, athlete list and movement catalog were being refetched every time. The
fix was to compare rather than replace. The reasoning is preserved as a comment in
`App.jsx`, because the "obvious" version is the broken one.
:::

**What it cost.** Two shapes existed at once for six weeks — the eight-tab console
on the team's `main`, and this on a branch — and anyone reading the coach code had to
know which they were looking at. Merging it here ended that for this repo and not for
the other one, which is the honest cost of a fork rather than a fix.

**What the merge itself had to settle.** The branch forked on 5 August and the trunk
kept moving, so two files genuinely conflicted: `App.jsx` and `Dashboard.jsx`. The
rule used was *the redesign wins on shape, the trunk wins on behaviour the redesign
never touched* — decided per hunk by asking which side actually CHANGED a thing
relative to the fork point, not which side was newer. So the states, the navbar, the
session widget, groups, quick notes and the removal of the empty-room panels came
from the redesign; live velocity on the session hero and coach-side sensor linking
stayed from the trunk, because the redesign had simply never seen them.

---

## Superseded: the eight tabs, grouped

**This is history in this repo, and current in the team's.** Kept because a fork with
no memory of what it replaced cannot explain itself later.

Before the three states, the eight tabs were visually split into **Room** and
**Athlete** groups with a divider between them. The three states replace that whole
row, so `react/src/coachTabs.js` is now dead code here — it is still imported by
nothing, and its tests still pass, which is exactly how dead code survives.

**What forced it.** Eight flat tabs mix room-level views (room, workouts,
schedule, reports) with per-athlete ones (athlete, history, programs, notes).
Those two kinds are not peers: a per-athlete view is meaningless until a coach
picks an athlete, and a flat row gave them equal weight with no hint of that.

**What we chose.** Two groups separated by a divider. Per-athlete
tabs are **dimmed until an athlete is selected** — clicking one before that shows
"Select an athlete to open their view." The room group is always live. The logic
is pure and tested in `react/src/coachTabs.js` (`tabDisabled`, `tabGroup`).

**Why it was done this way at the time.** The grouping was the low-risk mainline
increment that answered "per-athlete views are mixed in with room-level ones with no
visual cue" without touching routes or data, while the three-state redesign was still
unproven on a branch. That reasoning was right then and is worth keeping: it is the
shape of decision that gets made under a deadline, and it did not block the larger
change.

---

## Spreadsheet upload

**What forced it.** Coaches already keep everything in spreadsheets. Making them
retype a season's training into a new app is how a new app gets abandoned.
**What we chose.** Take the file they already have. Three kinds of sheet are
supported — a **roster** (a list of people), a **max sheet** (what each person can
lift), and a **plan** (the workouts as percentages).

**The rule that governs the whole importer: when a number's meaning is unclear, skip
it and say so.**

"225" in a spreadsheet could be a one-rep max, a set of five, or 80% of something. A
wrong guess does not stay in that one cell — an athlete's max is whatever was recorded
most recently, so a bad import quietly becomes their official number and drags down
every weight prescribed for them afterwards. Leaving it out is safe *and visible*: the
coach is told exactly who is missing what, and the system already handles an athlete
with no max on file.

**A typo must not throw away the other 199 rows.** When a name matches nothing, the
file is not rejected. The importer reports the row, offers the closest matches it can
find, and hands back everything it parsed so the coach can correct it on screen.
**Nothing is written until they do.**

**Nothing is created behind the coach's back.** A misspelling turned into a new
athlete would sit in the roster forever, shadowing the real person. So creating
records is either the explicit point of the sheet (a roster) or an explicit choice the
coach makes.

**What is still awkward.** The system currently *guesses* which of the three kinds a
file is, from its column names, and the coach never states their intent. When the
guess fails, the error has to describe all three formats at once because the importer
has no idea what was meant. Letting the coach pick the type up front is a known
outstanding task.

## Group history: the one genuinely new feature

Everything else in the redesign was rearrangement. This was not.

It answers the question a coach actually asks — **"who is falling behind?"** — by
letting history be scoped to a whole group rather than one athlete at a time. It was
built client-side, on data the system already had.

Worth noting for whoever extends it: the ability to filter by group through the URL
was deliberately left unspent. It is available if the feature grows, and adding it
early would have committed the design to a shape nobody had tested yet.
