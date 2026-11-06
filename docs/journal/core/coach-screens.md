<!--
this page — everything a coach touches: signing in, wiring the room together,
planning, running a session and reading what happened.

The coach UI went from eight flat tabs, to eight grouped tabs, to three states.
Each step is kept here so nobody walks back into the one before it. The
spreadsheet importer's "skip it and say so" rule is the one to read before
touching imports.
-->

# Coach screens

Everything a coach touches: signing in, wiring the room together, planning training, running a session, and reading what happened.

:::{admonition} Who built this
:class: note
**The room-layout controls** (assigning screens and sensors to rack slots, releasing a screen, unlinking a sensor, releasing every screen at once): **Carl and Devin**. They sit on the rack-assignment API Carl built in Phase 4, extended with the release and unlink routes.

**Force-clearing a wedged rack** (the escape hatch for an open set nobody can finish): **Braydon**.

**Coach accounts, server side and first screens:** **Braydon**, rebuilt by Devin to fit the three-state workspace.

**Everything else on this page** (sign-in, planning, the spreadsheet import, reports, the scheduling workspace, the three-state redesign): **Devin**, delivered through the merge (P0–P15) rather than as the Phase 14 originally written.
:::

## Tool changes at a glance

| Job | First | Now | Where it lives |
|---|---|---|---|
| The console's shape | eight flat tabs, then the same eight grouped | **three states: Planning, Session, Analytics** (merged Sep 17, `a50e3f7`) | `Dashboard.jsx`, `coach/coachState.js` |
| Which state you're in | component state | **the URL**: `/coach/planning`, `/coach/session`, `/coach/analytics` | `coach/coachState.js` |
| Coach API calls | a fetch wrapper per screen | **one helper** | `coach/api.js` |
| Signing in | two forms, one with the demo login typed in | **one empty form**, with a link to the athlete sign-in | `coach/SignIn.jsx` |
| A coach's own account | two more tabs | **the menu in the top-left corner** | `coach/AccountMenu.jsx` |
| Athlete logins (online) | — | **Send login link** on the roster, with a warning dialog | `coach/GroupsView.jsx`, `coach/LoginLinkDialog.jsx` |

**Where the code lives:** the console itself is in `react/src/` proper: `Dashboard.jsx` (the shell, the three states and the live room), `WorkoutCatalog.jsx`, `ScheduleWorkspace.jsx`, `ReportsWorkspace.jsx`. `react/src/coach/` started as just sign-in and rack setup, and now also holds the account pages, groups, the session widget, the state navbar, quick notes and login links.

## The problem

A coach uses completely different parts of the app depending on **when** it is: planning next week, running today's session, or reading what happened afterwards. All of it has to live in one workspace, on a tablet, often in the middle of a session with a room full of athletes.

## Try 1: eight flat tabs

Room, workouts, schedule, reports, athlete, history, programs, notes, side by side.

**Why I moved on:** they weren't peers. Room-level views sat next to per-athlete ones, and a per-athlete view means nothing until a coach picks an athlete. A flat row gave everything equal weight and made the common path slow.

## Try 2: the same eight, grouped

Two groups, **Room** and **Athlete**, with a divider. Per-athlete tabs were dimmed until an athlete was picked ("Select an athlete to open their view").

**What worked:** it was the low-risk increment under a deadline. It answered "per-athlete views are mixed in with room-level ones" without touching routes or data, while the bigger redesign was still unproven on a branch.

**Why I moved on:** it was still one row of everything. The grouping was a hint, not a structure. It's gone now, along with the file that held it (`coachTabs.js`).

## Where I landed: three states

Grouped by **when**, not by feature:

| State | The coach is… | Its tabs |
|---|---|---|
| **Planning** | setting up training ahead of time | Design, Groups, Workout catalog, Calendar |
| **Session** | running the room right now | Room |
| **Analytics** | reading what happened | Athlete, History, Notes, Reports |

- **The state lives in the URL**, so a reload keeps its place, Back works, and a view can be linked.
- **The rule that held the redesign together: no backend routes change.** It was re-shelving things that already worked, not a rewrite. Only group history (below) was allowed to break that.
- **One surface changing mode, not three pages.** The navbar stays put and animates between states. Rebuilding each state as its own page would have thrown away the live room and refetched everything, turning a mode change into a page load.

:::{admonition} A real bug this caused
:class: note
The first version reset the whole coach app on every state change, because React was told to treat each state as a brand-new component. It looked cosmetic (the sliding indicator jumped instead of animating), but underneath, the room, the athlete list and the movement catalog were refetched every time. The fix was to compare instead of replace. The reasoning is a comment in `App.jsx`, because the "obvious" version is the broken one.
:::

**How the merge was settled.** The branch forked on Aug 5 and the trunk kept moving, so `App.jsx` and `Dashboard.jsx` conflicted. The rule: **the redesign wins on shape, the trunk wins on behaviour the redesign never touched**, decided per hunk by asking which side actually *changed* a thing since the fork, not which was newer. So the states, the navbar, the session widget, groups, quick notes and the empty-room panels' removal came from the redesign; live velocity on the session hero and coach-side sensor linking came from the trunk.

## Rack assignment is a screen, not configuration

A sensor and a tablet are separate identities. The only thing making both "Rack 3" is a coach saying so, for each one. So pairing happens on a setup screen, not in a config file or by guessing.

**That's why a rack showing no data is usually an assignment problem, not a hardware one.** That one sentence saves more debugging than anything else on this page.

There are two places to do it, on purpose: **Room Layout** for setting the room up, and the **rack card in Session** for fixing a rack while you're looking at it. Both call the same route, `PUT /api/racks/node-assignment/` ({doc}`../../handbook/reference/message-contract`), so the same server rules apply.

## One sign-in path for every coach request

Coach actions are the privileged ones: creating athletes, changing plans, assigning racks. Scattering token handling across screens is how one ends up quietly unauthenticated. **Every signed-in coach request goes through `coach/api.js`.** Adding a coach screen? Import from there; don't write another fetch wrapper.

The token is kept in browser storage on purpose, so a refresh doesn't sign a coach out mid-session. During a live demo in front of a room, that matters more than it sounds.

## A coach's own account lives in the corner

Coach accounts arrived in October. The first screens were written as two more tabs in the old row of eight, and that row no longer existed. And a coach's login isn't training: it isn't planning, a session or analytics.

- **The top-left corner is the account menu.** It says who's signed in and whether they're an administrator, and holds Coaches (administrators only), Change password and Log out.
- **Coaches and Change password are their own small pages** (`/coach/account/…`) inside the same top bar and navbar, so one press takes you back.
- **One sign-in form, and it starts empty.** It replaced two, one of which came with the demo username and password already typed in.
- **Until an installation is claimed, every device sees first-run setup**, rack tablets included. A tablet that has seen a claimed installation remembers that, so it can reopen its screen while the server is unreachable. That memory decides what's drawn and grants nothing.
- **A temporary password opens one screen.** "Choose your own password" replaces the whole workspace until it's done, and the server enforces the same thing.
- **Athletes are archived, never deleted.** The athlete leaves the roster and every picker, and their tag is freed; everything they lifted is kept. The server refuses while they're in a running session.
- **Online, the roster has Send login link,** with a dialog that says the link is personal and the session link is the one that's safe to share ({doc}`remote/access`).

## Spreadsheet upload

**The problem:** coaches already keep everything in spreadsheets. Making them retype a season into a new app is how a new app gets abandoned.

**Where I landed:** take the file they already have. Three kinds are supported: a **roster** (people), a **max sheet** (what each person can lift) and a **plan** (the workouts as percentages).

**The rule for the whole importer: when a number's meaning is unclear, skip it and say so.** "225" could be a one-rep max, a set of five, or 80% of something. A wrong guess doesn't stay in one cell: an athlete's max is whatever was recorded most recently, so a bad import quietly becomes their official number and drags down every weight prescribed after it. Leaving it out is safe *and* visible: the coach is told exactly who's missing what.

- **A typo doesn't throw away the other 199 rows.** A name that matches nothing is reported with the closest matches, and everything parsed comes back so the coach can fix it on screen. **Nothing is written until they do.**
- **Nothing is created behind the coach's back.** A misspelling turned into a new athlete would shadow the real person forever. Creating records is either the point of the sheet (a roster) or an explicit choice.

**Still awkward:** the importer *guesses* which kind a file is from its column names (`detect_sheet_type`). When the guess fails, the error has to describe all three formats. Letting the coach pick the type up front is still to do.

## Group history: the one new feature in the redesign

Everything else was rearrangement. This answers the question a coach actually asks, **"who's falling behind?"**, by scoping history to a whole group instead of one athlete. It's built in the browser, on data the server already had.

Filtering by group through the URL was deliberately left unbuilt. It's there if the feature grows; adding it early would have locked in a shape nobody had tested.

## Things I passed on

- **Eight flat tabs, and eight grouped ones.** Tries 1 and 2.
- **Each state as its own page.** It would refetch everything on every switch.
- **Laying out the first account screens as they were.** They belonged to a page that's gone. Their logic was kept (the calls, the guards, the error messages); their layout wasn't.
- **A separate roster page for archiving.** The workspace already had a roster.
- **Hiding Coaches as the only protection.** A regular coach doesn't see the entry, and the server refuses them anyway. The hidden button is a courtesy.
- **Guessing what a spreadsheet number means.**

## What it cost

- **An archived athlete's page can't be opened in Analytics.** Their sets are kept and still appear in every saved report, but the athlete picker doesn't list them.
- **The coach sign-in card doesn't name the school.** It says "Coach workspace". The athlete sign-in and first-run screens do show it.
- **Deactivate and Reset password ask in the browser's plain confirm box.** A styled dialog is still to come.
- **The importer guesses the sheet type.**
