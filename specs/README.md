# Specs

Everything that has been **decided but not built**, one file per feature. Read this page
first: it is the index, the roadmap, and the decisions every spec assumes.

> Specs live here, outside `docs/`, so they are never published to the public docs
> site (`docs/publish.sh` copies only `docs/`). When a spec is finished, its lasting
> reasoning moves into `docs/` and the spec is marked Done.

Written 2026-10-06 for the CSC 4903 directed study, which ended with the final
presentation on 2026-11-10 (where each promised item landed: `docs/about/directed-study.md`).
Rewritten 2026-11-11 as the product's roadmap. Owner: Devin Walton.

---

## How every spec is written

- **Phases.** Each spec is cut into phases small enough to review in one sitting.
- **Testable criteria at the end of every phase.** A phase is done when its checklist is
  true, not when the code is written. Each item is an automated test unless it says
  *(Browser)* or *(By hand)*.
- **A stop after every phase.** Devin reviews before the next phase starts. Do not run
  several phases ahead.
- **Work on a feature branch, merge into `SprintBranch` at the end.** See "Branches" below.
- **Screens are built from the Final designs page** (Devin, 2026-10-14). Every screen a
  spec builds follows its `F_*` board on the canvas's Final designs page: layout, wording,
  states, and the solid look. A spec names the boards it builds. A screen a feature needs
  that has no board goes to a proposal page first and is built only after Devin approves
  it; it then moves to Final designs. This applies to specs written later too, so
  features are fitted to the agreed design, not the other way round.
- **Record the baseline first.** Before changing anything, note how many backend and
  frontend tests pass on `SprintBranch`.

### Branches

Devin's convention, set 2026-10-06:

| Branch | What it is |
|---|---|
| `SprintBranch` | **The working trunk for this project.** Every feature branch starts from it and merges back into it. It must always pass the tests. |
| `feature-xyz` | One branch per spec, named `feature-` plus a short name, with underscores between words: `feature-coach_accounts`. Reviewed phase by phase, merged into `SprintBranch` after its last phase. |
| `main` | **What is deployed.** Nobody commits to it. It is only moved forward to match `SprintBranch` by the **Move main forward** workflow on Devin's say-so, then tagged; the tag deploys it (spec 12). |

Merged feature branches are deleted (locally and on GitHub) once their pull request is in;
the pull request page keeps the history and can restore the branch. Two unmerged branches
are kept on GitHub as backups: `feature-rep_counting` (spec 09, one commit) and
`feature-shared_racks` (spec 18, which lives only on that branch until it is picked up).

Spec and mockup edits that are not part of a feature are committed straight to
`SprintBranch`. Release tags and the public docs are cut from `main`.

**Pull requests (decided 2026-10-14, starting with spec 05 Phase 1).** Once CI exists,
work reaches `SprintBranch` only through a pull request: one per spec, with each phase
added to it. Its checks must pass, and Devin merges it. Merging is the approval, because
GitHub does not let anyone approve a pull request opened under their own account. Tests
run on pull requests, not on every push. **`main` takes no pull request**: everything on
`SprintBranch` has already been through one, so a release just moves `main` forward to
match `SprintBranch` and tags it (`vX.Y.Z`, patches included), and the tag rolls it out.
Devin releases by hand when he chooses; a scheduled release every two weeks is the
long-term habit, not switched on yet.

### Running the tests

```bash
docker compose build django          # the image BAKES the source: rebuild or you test old code
docker compose run --rm django python manage.py test event_handler
docker compose run --rm django python manage.py makemigrations --check --dry-run
cd react && npx vitest run && npm run build
./docs/build.sh                      # docs, warnings fatal
```

By v0.8.3 (2026-11-09) CI ran **1,114 tests** on every pull request: the backend suite twice
(as a local install and as the remote server) plus the frontend suite.

### House rules (from earlier sessions, still in force)

- Commit messages are short notes-to-self, lower case, no ticket language.
- **No co-author or AI attribution lines on commits.**
- Every code file opens with a plain-language comment saying why it exists.
- Credit Braydon wherever his work is described.

---

## The specs

| # | Spec | Status |
|---|---|---|
| 01 | [Secure coach accounts](remote/01-coach-accounts.md) | **Done** 2026-10-07 |
| 02 | [Roles: administrator, coach, athlete](remote/02-roles.md) | **Done** 2026-10-07 |
| 05 | [Hosted mode](remote/05-hosted-mode.md) | **Done** 2026-10-14 (includes CI) |
| 12 | [Hosting on k3s, with CD](remote/12-hosting.md) | Phases 0–4 **done**: schools on the Dell, deploy on a version tag, `wss`, the domain. Phases 5–7 tabled |
| 03 | [Athlete login links](remote/03-athlete-login-links.md) | **Done** 2026-10-18 |
| 04 | [Session link and virtual racks](remote/04-session-link-and-virtual-racks.md) | Built (Phases 0–3, 5). Phase 4 (coach's side) belongs to the UI redesign |
| 14 | [Sensors online](remote/14-sensors-online.md) | Phases 0–9 **done**. Phase 10 (Manage sensors, live/standby, Swap) written 2026-11-11 |
| 10 | [The athlete's pages](remote/10-athlete-pages.md) | All phases built 2026-11-11 (Home, session ended, All sessions, a past session, My Recent Progress, Account); review + PR next |
| 06 | [Design rules](ui/06-design-rules.md) | **Done** 2026-11-11: every colour in one token file (guarded in CI, app and sensor setup page), shared pieces in `react/src/ui/`, one-tab rows hidden, developer text out, top bar split |
| 07 | [Planning](ui/07-planning.md) | Written; Add athlete panel and the first/last name split added 2026-11-08 |
| 08 | [Session](ui/08-session.md) | Written |
| 09 | [Analytics](ui/09-analytics.md) | Written |
| 11 | [Mine first](ui/11-mine-first.md) | Written |
| 16 | [The plate loader on the rack screen](ui/16-plate-loader.md) | Built as part of spec 19 (Phases 3–4); its lb/kg choice is shared with the athlete pages |
| 19 | [The rack screen](ui/19-rack-screen.md) | Written 2026-11-11: every rack screen change in one place, both versions (waiting screen, only the planned reps count and each rep's feedback, the plate loader from spec 16, the corner switch, the room display for athletes). Can start any time |
| 13 | [Registry of schools and operator's console](later/13-registry-and-console.md) | Written, later |
| 15 | [Usage history and cloud cost](later/15-usage-and-cost.md) | Written, later (Phase 0, recording, can start any time) |
| 17 | [Locations, and several sessions at once](later/17-concurrent-sessions.md) | Written, later; revised 2026-11-14 (locations, rooms, idle sessions); after spec 18 |
| 20 | [Data export, and syncing a local install with the remote server](later/20-data-export-and-sync.md) | Written 2026-11-14, later |
| 21 | [Make-ups](later/21-make-ups.md) | Draft 2026-11-14, for review |
| 18 | Shared racks online (common login) | Written on `feature-shared_racks` only |

## The roadmap after the class

Five tracks, in the order Devin set on 2026-11-11: housekeeping, then the product.

### 1. Housekeeping (before the repository goes private)

- [x] Spec 07's Add athlete and name-split edits committed.
- [x] Merged branches deleted; the two unmerged ones backed up on GitHub.
- [x] This page rewritten.
- [ ] A last public docs publish (`./docs/publish.sh --push` from a tagged commit).
- [ ] Devin's own "why" for Postgres, nginx, NetworkManager and systemd in the Stack pages.

### 2. Product

The UI redesign and the athlete pages, built from the Final designs page and spec 06's
rules:

- **Coach:** specs 06 → 07 (starting with the name audit) → 08 → 09 → 11, with 16 and spec
  04's Phase 4 alongside; the top bar split (spec 06 rule 12) lands with 06.
- **Athlete:** spec 10, and spec 14 Phase 10 with it.
- **Rack screen (both versions):** spec 19, which gathers every rack screen change (spec 16's
  plate loader, the rep counting moved from spec 09, the waiting screen and corner switch from
  spec 18, the room display for athletes from spec 10). Depends only on spec 06, so it can run
  alongside the athlete or coach work.
- **Still needs a board:** the rack screen's Room display button (spec 19 Phase 6).
- **Later in the track:** spec 18 (shared racks), spec 17 (several sessions at once).
- **Known bugs:** the calendar's Move picker labels the slot's own date "Today"
  (`react/src/schedule.js`, `moveDateChoices`); `eactl seed --reset` fails once
  calendar-staged sessions use the demo plan (`seed_active_session._reset`).

### 3. Going private (2026-11-17) and infrastructure

| Work | Why it waits | Where the design is |
|---|---|---|
| Make the repository private | Public until 2026-11-17, Devin's call | — |
| Moving CI onto the Dell | Only safe once the repository is private | spec 12, Deferred |
| Unhold the kernel; fix the AppArmor problem properly | Held since 2026-11-05 after kernel 7.0.0-42 broke every container | `docs/handbook/guides/remote-server.md` |
| Docs published by the release workflow | Published by hand today | — |
| An image pull key that renews itself (a GitHub App) | The 90-day token is renewed by hand meanwhile | spec 12, Phase 0 result |
| Browser logins to the broker | Needed before a real program's athletes use it | spec 12, Phase 4 and Non-goals |
| A real secrets vault; Ansible in place of `bootstrap.sh` | One server does not need them yet | spec 12 |
| The hosting spec: bootstrap a fresh Linux PC like a cloud machine | Not written yet | — |

### 4. Operations and scale

Spec 13 (registry and console), spec 15 (usage, cost and load baselines), a second node.
**Data export and sync**, [spec 20](later/20-data-export-and-sync.md) (draft 2026-11-14): one export format holding every
table with its original ids and timestamps; "Export my data" in every tier (the
anti-lock-in promise); a manual "Sync my data" button in the coach's settings between a
local install and the remote server, built on the design already in
`docs/journal/core/remote/databases.md` (first a copy, then only finished sessions are
added each way, the remote server wins a shared record edited on both sides). Several
rooms on the remote server are spec 17, not sync: one school, one database.
**Make-up sessions**, [spec 21](later/21-make-ups.md) (draft 2026-11-14): an athlete who missed a session does it
later, and the sets count toward the missed day. Devin's idea: the missed session leaves
each absent athlete a pointer; any one-off session they lift later can be pointed at it,
bringing in that day's plan, and their sets file into the original session as make-ups.
Today the server still accepts a set filed into an ended session and every set has
`is_makeup` (the original design's flow), but no screen does it, and the daily report,
frozen at the end, wouldn't include it. Decided for it (Devin, 2026-11-14): a make-up **rebuilds that
day's report in place** (the same report, rewritten), and **never recalculates anyone's
max**, the make-up athlete's included: maxes are worked out once when a session ends,
newest wins, so recalculating later would put old numbers ahead of newer ones. A make-up
counts toward the missed session's date, with the real lift date shown beside it.

### 5. Kept out of this repository

The sensor's own circuit board, and business plans (pricing, billing).

---

## Decisions every spec assumes

### One codebase, two deployments

A **gym box** (one machine in the gym, its own Wi-Fi, no internet needed) and a
**hosted installation** (on a k3s cluster, reached over the internet) run the same
code, the same database schema and the same message topics. **Every decision must work
in both.** The only intended difference is spec 05's switch: `EA_DEPLOYMENT`, set to
`local` (a gym box, the default) or `remote` (hosted).

One database per installation. The code never knows another installation exists.

### The training model — use these words in the interface

| Term | What it is | Rules |
|---|---|---|
| **Training Block** | A template: an ordered list of days, plus a weekly pattern and a length | **Only ever a template.** No group, no dates. Never "deployed" to a group directly |
| **Training Program** | An instance: your own copy of a block, for **one** group, with a start date | Freely editable; edits never touch the block. Can be **saved as a new Training Block** (promoted). Several programs can share one Training Session |
| **Training Session** | One day of a program on the calendar; later, the day as it was actually run | Created when a program is **scheduled**, not when it is created |
| **Training Group** | Athletes who train together | Filtered, never fenced: every coach sees every group |
| **Roster** | Everyone you coach | The only place athletes are created |

The flow in Planning is **1 Build a Training Block → 2 Create a Training Program →
3 Schedule Training Sessions.** Do not use the word "deploy" for block → group.

A program is **not scheduled** until the coach confirms its start date on the
calendar. Until then its days and date can change freely. Once scheduled, what is *in*
a day can still change, but days cannot be added, removed or reordered.

### People and access

- **One coach role.** Every coach can see and do everything in the coach workspace.
- **One administrator flag** (Django `is_staff`), used only for managing coach logins.
  The interface says **Administrator**, never "head coach" for this flag.
- **Coaches create every athlete.** No public sign-up, in either deployment.
- **The gym stays account-free.** No athlete logs in at a gym rack.
- **Remote athletes** get a login through a personal, single-use **login link** the
  coach sends. The same button handles a forgotten password. A link replaces the login,
  never the training data.
- **The session link** is not a secret. An athlete gets in only if their login is
  linked to an athlete who belongs in that session.
- **A remote athlete's device is their rack.** The server creates a rack for them when
  they join and releases it when the session ends.
- **A sensor belongs to an athlete** once it leaves the gym, and attaches to that
  athlete's rack on its own.
- **No list of athlete names is ever shown to someone who is not signed in.**

### The interface

- The state machine redesign (PLANNING / SESSION / ANALYTICS, the glass navbar) takes
  precedence over Braydon's screens. His screens are fitted into it.
- **Reduce buried buttons.** Anything pressable must look pressable; anything a coach
  needs to see must be visible without drilling.
- The session strip stays on all three states and the header card stays on every tab.
  Both are intentional.
- **Local and hosted are one interface.** Hosted mode adds or hides elements on a
  screen; it never gets its own screen. Features change, form does not. The
  screen-by-screen comparison is rule 8 of spec 06.
- **The look is solid surfaces** (adopted 2026-10-06): every row, card and table on a
  solid panel with a border; tints only on banners; solid block buttons; every End
  button a red outline, in both versions. Spec 06 rule 9.
- Full rules in [spec 06](ui/06-design-rules.md).

---

## The mockups

- **In this repo:** [`ui/mockups/coach-ui-final.html`](ui/mockups/coach-ui-final.html).
  Open it in a browser. Static, sample data only.
- **Live canvas (private to Devin):** https://claude.ai/artifact/Hz3PHLTwRv52aUVe9U4gsG
  — three pages: Remote coach view, Current local UI (real screenshots), Proposed local
  UI, and **Final designs**. **Build only from the Final designs page** (boards named
  `F_*`): local and remote side by side in the adopted solid look; a dashed REMOTE tag
  marks what hosted adds. The other pages are the history of how it got there, and the
  `V3*`/`V4*` boards the specs name show the same screens in the earlier hairline look.
- **Source and screenshots:** `~/Desktop/Coding Projects/Edge Athlete Remote/mockups/`
  and `.../ui-captures/` (outside the repo).

Specs refer to mockup screens by file name, for example `V3b_DesignStep2`. **Where a spec
names an older `V3*`/`V4*` board, build its `F_*` counterpart on Final designs.**

---

## Facts about the code worth knowing before starting

Checked on 2026-10-06 against commit `31f0573`.

- **Permissions today:** `IsCoach` means only "is logged in" and guards 32 endpoints;
  `IsActiveStaff` guards 9; **21 endpoints are open to anyone**
  (`django/event_handler/permissions.py`, `views.py`).
- **Logins:** Django's built-in users, JWT through `rest_framework_simplejwt`. Access
  token 8 hours, refresh token 7 days, rotating.
- **Braydon's coach-account work** is on the team repo's `main`, fetched here as
  `refs/tmp/team-main`: commits `78260b4`, `b59a531`, `5a35928`.
- **Migrations stop at `0025`** (spec 01 added `0023`–`0025`).
- **The rack screen** listens to one sensor, and only while a set is running
  (`react/src/rack/RackScreen.jsx`, around line 540).
- **`instantiate_block()`** creates a program and, as its last line, calls
  `generate_schedule()` (`django/event_handler/services/planning.py`).
- **Several groups already share a session on the server.** A session holds one
  `SessionParticipation` per program; `plan_resolution.py` gives an athlete in two of
  those groups both plans combined, lighter percentage winning on a shared movement.
  The front end has no way to put two programs on one session yet; spec 07 Phase 3
  adds it ("Add to the existing sessions?"). Explained in `docs/handbook/reference/database-tables.md`.
- **A program's days cannot be edited through the API today.** Blocks have routes for
  adding, reordering, editing and deleting days; programs have only "create" and
  "promote". See spec 07.
- **`promote_program_to_block()`** copies days and movements up into a new block. It
  copies no dates and no group. A block has no date field.
- **"Behind"** (an athlete trending down) is worked out in the browser, one request per
  athlete, in `react/src/coach/groupHistory.js`. See spec 09.
- **Design and Workout catalog are one component** (`react/src/WorkoutCatalog.jsx`)
  shown twice with a different `section` value.
- **The local app** runs from the team clone at
  `~/Desktop/Coding Projects/Edge Athlete/Edge-Athlete` (same app code as this repo).
  Demo login `coach` / `coachpass` there until that app is switched to `SprintBranch`; after that it exists only on a seeded development database.
