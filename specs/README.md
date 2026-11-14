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
| `main` | **What is deployed.** Nobody commits to it. It is only moved forward to match `SprintBranch` by the **Move main forward** workflow on Devin's say-so, then tagged; the tag deploys it (spec 04). |

Merged feature branches are deleted (locally and on GitHub) once their pull request is in;
the pull request page keeps the history and can restore the branch. Two unmerged branches
are kept on GitHub as backups: `feature-rep_counting` (spec 16, one commit) and
`feature-shared_racks` (spec 10's first text; picked up on `feature-rack_setup` 2026-11-12).

Spec and mockup edits that are not part of a feature are committed straight to
`SprintBranch`. Release tags and the public docs are cut from `main`.

**Pull requests (decided 2026-10-14, starting with spec 03 Phase 1).** Once CI exists,
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

## The specs, in build order

Renumbered on 2026-11-14 so the numbers are the order they're built in. Each spec's file
starts with a "Previously spec #" line; old numbers in commits, code comments and the docs
journal are looked up in the table under this one. Status words: **Complete**, **In
progress** (phases built of phases), **Specced** (phases written, not started), **Not
specced**.

| # | Spec | What it delivers, and why it's here | Status |
|---|---|---|---|
| 01 | [Secure coach accounts](remote/01-coach-accounts.md) | Coach logins, first-run setup, password rules | Complete (2026-10-07) |
| 02 | [Roles](remote/02-roles.md) | Administrator, coach, athlete: a login's role comes from what it's attached to | Complete (2026-10-07) |
| 03 | [Hosted mode](remote/03-hosted-mode.md) | One codebase, local or remote, every route with its online rule; CI tests both | Complete (2026-10-14) |
| 04 | [Hosting on k3s, with CD](remote/04-hosting.md) | Schools on the Dell, deploys on a version tag, `wss`, the domain | Complete (Phases 0–4); the rest became spec 18 |
| 05 | [Athlete login links](remote/05-athlete-login-links.md) | A coach sends a link; the athlete picks a password | Complete (2026-10-18) |
| 06 | [Session link and virtual racks](remote/06-session-link-and-virtual-racks.md) | An online athlete joins a session on their phone, their own rack | Complete (Phases 0–3, 5); the coach's side moved into spec 15 |
| 07 | [Sensors online](remote/07-sensors-online.md) | An athlete's own sensor: claim code, setup page, firmware, MQTT online | Complete (Phases 0–9); Manage sensors became spec 12 |
| 08 | [Design rules](ui/08-design-rules.md) | Colour tokens, shared pieces in `react/src/ui/`, the top bar, one shared piece per element | Complete (2026-11-11) |
| 09 | [The athlete's pages](remote/09-athlete-pages.md) | Home, session ended, all sessions, a past session, My Recent Progress, Account | Complete (2026-11-12, PR 22) |
| **10** | [Rack setup and shared racks](remote/10-shared-racks-online.md) | **Now.** A school's common login for tablets and TVs online; racks that name themselves; one-rep pairing; the shared dialog; the local install moves to the same flow. Changes how racks are made, so it comes before the rack screen | **In progress: 3 of 9 phases built** (0, 1, 2), awaiting review, on `feature-rack_setup` |
| 11 | [The rack screen](ui/11-rack-screen.md) (+ [11b plate loader](ui/11b-plate-loader.md)) | Only the planned reps count, each rep's feedback, the plate loader, the room display for athletes. Resumes once spec 10 has changed how racks are made | **In progress: 1 of 6 phases built** (Phase 0), paused for spec 10 |
| 12 | [Manage sensors](remote/12-manage-sensors.md) | Several sensors per athlete, one live, Swap. Small, and builds on spec 10's sensor pairing | Specced, 1 phase |
| 13 | School usage card and monthly report | What a school sees about its own use, including the "60% of the roster logging weekly" guarantee. Before the coach redesign so the redesign has a place for it | **Not specced** |
| 14 | [Planning](ui/14-planning.md) | Coach redesign 1: groups, roster, calendar, Add athlete, the name audit | Specced, 8 phases |
| 15 | [Session](ui/15-session.md) | Coach redesign 2: running a session, one card per rack, the coach's side for online athletes | Specced, 6 phases |
| 16 | [Analytics](ui/16-analytics.md) | Coach redesign 3: history with reports, Behind, a finished session's link leads to analytics | Specced, 6 phases |
| 17 | [Mine first](ui/17-mine-first.md) | Coach redesign 4: a coach's own groups and sessions first | Specced, 5 phases |
| 18 | [Backups and rebuild](later/18-backups-and-rebuild.md) | Safety copies off the server with a tested restore, a demo-school dry run, rebuilding from a blank machine. After the redesign (Devin, 2026-11-14) | Specced, 3 phases |
| 19 | [Export my data](later/19-data-export.md) | Everything a school recorded, in every plan; the format sync reuses | Specced, 1 phase |
| 20 | [Registry and console](later/20-registry-and-console.md) | The operator's list of schools, and what each plan includes ("Locations included"). Needed before locations | Specced, 5 phases |
| 21 | [Locations and several sessions](later/21-locations-and-concurrent-sessions.md) | Several rooms, one session per location at once, idle sessions suspended, a device's location | Specced, 6 phases |
| 22 | [Make-ups](later/22-make-ups.md) | A coach's make-up session; missed days filled in; fixes `is_makeup`. Needs locations (idle sessions end on their own) and the rack screen | Specced, 6 phases |
| 23 | [Sync](later/23-sync.md) | "Sync my data" between a local install and the remote server; moving a school between servers. Needs locations and export | Specced, 5 phases |
| 24 | [Usage history and cloud cost](later/24-usage-and-cost.md) | Our own server cost per school, load baselines (its Phase 0, recording, can start any time) | Specced, 6 phases |

### Old numbers

| Was | Now | | Was | Now |
|---|---|---|---|---|
| 01 | 01 | | 12, Phases 0–4 | 04 |
| 02 | 02 | | 12, Phases 5–7 | 18 |
| 03 | 05 | | 13 | 20 |
| 04 | 06 (its Phase 4 → 15) | | 14, Phases 0–9 | 07 |
| 05 | 03 | | 14, Phase 10 | 12 |
| 06 | 08 | | 15 | 24 |
| 07 | 14 | | 16 | 11b |
| 08 | 15 | | 17 | 21 |
| 09 | 16 | | 18 | 10 |
| 10 | 09 | | 19 | 11 |
| 11 | 17 | | 20 | 19 (export) and 23 (sync) |
| | | | 21 | 22 |

## The roadmap after the class

Five tracks, in the order Devin set on 2026-11-11: housekeeping, then the product.

### 1. Housekeeping (before the repository goes private)

- [x] Spec 14's Add athlete and name-split edits committed.
- [x] Merged branches deleted; the two unmerged ones backed up on GitHub.
- [x] This page rewritten.
- [ ] A last public docs publish (`./docs/publish.sh --push` from a tagged commit).
- [ ] Devin's own "why" for Postgres, nginx, NetworkManager and systemd in the Stack pages.

### 2. Product

In the order of the table above (specs 09 to 17, then 18 onward). Still needs a board: the
rack screen's Room display button (spec 11 Phase 6). **Known bugs:** the calendar's Move
picker labels the slot's own date "Today" (`react/src/schedule.js`, `moveDateChoices`);
`eactl seed --reset` fails once calendar-staged sessions use the demo plan
(`seed_active_session._reset`); the rack screen marks an athlete's later sets as make-ups
(fixed by spec 22, Phase 0).

### 3. Going private (2026-11-17) and infrastructure

| Work | Why it waits | Where the design is |
|---|---|---|
| Make the repository private | Public until 2026-11-17, Devin's call | — |
| Moving CI onto the Dell | Only safe once the repository is private | spec 04, Deferred |
| Unhold the kernel; fix the AppArmor problem properly | Held since 2026-11-05 after kernel 7.0.0-42 broke every container | `docs/handbook/guides/remote-server.md` |
| Docs published by the release workflow | Published by hand today | — |
| An image pull key that renews itself (a GitHub App) | The 90-day token is renewed by hand meanwhile | spec 04, Phase 0 result |
| Browser logins to the broker | Needed before a real program's athletes use it | spec 04, Phase 4 and Non-goals |
| A real secrets vault; Ansible in place of `bootstrap.sh` | One server does not need them yet | spec 04 |
| The hosting spec: bootstrap a fresh Linux PC like a cloud machine | Not written yet | — |

### 4. Operations and scale

Specs 10 to 24 in the table, and a second node.

### 5. Kept out of this repository

The sensor's own circuit board, and business plans (pricing, billing).

---

## Decisions every spec assumes

### One codebase, two deployments

A **gym box** (one machine in the gym, its own Wi-Fi, no internet needed) and a
**hosted installation** (on a k3s cluster, reached over the internet) run the same
code, the same database schema and the same message topics. **Every decision must work
in both.** The only intended difference is spec 03's switch: `EA_DEPLOYMENT`, set to
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
  screen-by-screen comparison is rule 8 of spec 08.
- **The look is solid surfaces** (adopted 2026-10-06): every row, card and table on a
  solid panel with a border; tints only on banners; solid block buttons; every End
  button a red outline, in both versions. Spec 08 rule 9.
- Full rules in [spec 08](ui/08-design-rules.md).

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
  The front end has no way to put two programs on one session yet; spec 14 Phase 3
  adds it ("Add to the existing sessions?"). Explained in `docs/handbook/reference/database-tables.md`.
- **A program's days cannot be edited through the API today.** Blocks have routes for
  adding, reordering, editing and deleting days; programs have only "create" and
  "promote". See spec 14.
- **`promote_program_to_block()`** copies days and movements up into a new block. It
  copies no dates and no group. A block has no date field.
- **"Behind"** (an athlete trending down) is worked out in the browser, one request per
  athlete, in `react/src/coach/groupHistory.js`. See spec 16.
- **Design and Workout catalog are one component** (`react/src/WorkoutCatalog.jsx`)
  shown twice with a different `section` value.
- **The local app** runs from the team clone at
  `~/Desktop/Coding Projects/Edge Athlete/Edge-Athlete` (same app code as this repo).
  Demo login `coach` / `coachpass` there until that app is switched to `SprintBranch`; after that it exists only on a seeded development database.
