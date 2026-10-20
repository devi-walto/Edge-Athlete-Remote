# Specs

Everything that has been **decided but not built**, one file per feature. Read this page
first: it is the index, the order to build in, and the decisions every spec assumes.

> Specs live here, outside `docs/`, so they are never published to the public docs
> site (`docs/publish.sh` copies only `docs/`). When a spec is finished, its lasting
> reasoning moves into `docs/` and the spec is marked Done.

Written 2026-10-06. Owner: Devin Walton. Project: CSC 4903, due **November 11, 2026**.

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
| `main` | **What is deployed.** Nobody commits to it. It is only moved forward to match `SprintBranch` (by hand on Devin's say-so for this class, by a scheduled release workflow later), then tagged; the tag deploys it (spec 12). Until that exists, `main` is moved forward from `SprintBranch` only when Devin says so. |

Feature branch for each spec: `feature-coach_accounts` (01), `feature-roles` (02),
`feature-deployment_switch` (05), `feature-login_links` (03), `feature-session_link`
(04), `feature-athlete_home` (10), `feature-design_rules` (06), `feature-planning`
(07), `feature-session` (08), `feature-analytics` (09), `feature-mine_first` (11).

Spec and mockup edits that are not part of a feature are committed straight to
`SprintBranch`. Release tags and the public docs are cut from `main`.

**Pull requests (decided 2026-10-14, starting with spec 05 Phase 1).** Once CI exists,
work reaches `SprintBranch` only through a pull request: one per spec, with each phase
added to it. Its checks must pass, and Devin merges it. Merging is the approval, because
GitHub does not let anyone approve a pull request opened under their own account. Tests
run on pull requests, not on every push. **`main` takes no pull request**: everything on
`SprintBranch` has already been through one, so a release just moves `main` forward to
match `SprintBranch` and tags it (`vX.Y.Z`, patches included), and the tag rolls it out.
For this class Devin releases by hand when he chooses; later a release workflow does it
on a schedule (every two weeks is the long-term habit). Until spec 05 Phase 1 is built, commits
go straight to `SprintBranch` as before.

### Running the tests

```bash
docker compose build django          # the image BAKES the source: rebuild or you test old code
docker compose run --rm django python manage.py test event_handler
docker compose run --rm django python manage.py makemigrations --check --dry-run
cd react && npx vitest run && npm run build
./docs/build.sh                      # docs, warnings fatal
```

The Django suite had 447 tests on 2026-10-06 and **491 after spec 01** (2026-10-07); the frontend suite has 281.

### House rules (from earlier sessions, still in force)

- Commit messages are short notes-to-self, lower case, no ticket language.
- **No co-author or AI attribution lines on commits.**
- Every code file opens with a plain-language comment saying why it exists.
- Credit Braydon wherever his work is described.

---

## The specs, in build order

| # | Spec | Form item | Depends on | Status |
|---|---|---|---|---|
| 01 | [Secure coach accounts](remote/01-coach-accounts.md) | 2 | — | **Done 2026-10-07**, merged into `SprintBranch` |
| 02 | [Roles: administrator, coach, athlete](remote/02-roles.md) | 3 | 01 | **Done 2026-10-07**, merged into `SprintBranch` |
| 05 | [Hosted mode](remote/05-hosted-mode.md) | 3 | 02 | **Done 2026-10-14**, merged into `SprintBranch`. Includes CI (Phase 1) |
| 12 | [Hosting on k3s, with CD](remote/12-hosting.md) | 1, 5 | 05 | **Phases 0–3 done** (merged): schools on the Dell, deploy on a version tag. Phase 4 (`wss`, then the domain) in progress; Phases 5–7 tabled |
| 03 | [Athlete login links](remote/03-athlete-login-links.md) | 4 | 02, 05 | **Done 2026-10-18** on `feature-login_links` (Phases 0–4, browser-checked). Coach login codes moved to spec 11, Phase 4 |
| 04 | [Session link and virtual racks](remote/04-session-link-and-virtual-racks.md) | 3, 4, 5 | 02, 03, 05 | Built 2026-10-19: Phases 0–3 and 5 (demo data, `eactl seed` / `eactl sim`). Phase 4 (coach's side) moved to the end of the UI redesign; Phase 6 (rehearsal) skipped |
| 10 | [The athlete's home page](remote/10-athlete-pages.md) | 4 | 03, 04, 05 | Written. Phase 4 (opening a past session) is built last, if time |
| 14 | [Sensors online](remote/14-sensors-online.md) | 6, 7 | 03, 04, 12 | Written 2026-10-19. Shared one-time secrets (Phase 0), the broker's sensors door on 443, claim codes, then firmware (needs the sensor) |
| 06 | [Design rules for the coach interface](ui/06-design-rules.md) | 11 | — | Written |
| 07 | [Planning](ui/07-planning.md) | 11 | 06, 01 | Written |
| 08 | [Session](ui/08-session.md) | 11 | 06 | Written |
| 09 | [Analytics](ui/09-analytics.md) | 11 | 06 | Written |
| 11 | [Mine first](ui/11-mine-first.md) | 11, 2 | 02, 06 | Written. A coach's own groups, programs, sessions and athletes come first; coaches on a group can be edited; coaches shown by name. Phase 4 (last of the redesign): coach login codes, moved from spec 03 |

**Build 05 before 03 and 04, and 10 after 04. Spec 12 (hosting) starts after 05 and runs alongside 03 and 04.** It is numbered 05 because it was listed fifth, but 03
and 04 both need its "is this installation hosted?" switch.

**The two tracks can interleave.** Specs 01–05 are the remote access work. Specs 06–09
are the coach interface cleanup. They touch different files for the most part; the
overlaps are called out inside each spec.

### Not specced yet

Nothing in the Definition of Done. The last piece, sensors, became spec 14 on 2026-10-19.

Moved into [spec 12](remote/12-hosting.md) on 2026-10-14: hosting on k3s, the demo
installation, and (as "if there is time") moving a database between a gym box and hosted.

### After the class

Decided or designed, and deliberately left until after November 11. Pick from this list
then. Business plans (pricing, billing) are kept out of this repository.

| Work | Why it waits | Where the design is |
|---|---|---|
| **The registry of schools and the operator's console** | Two schools (real and demo) are manageable with `eactl list`; a console is for many | [spec 13](later/13-registry-and-console.md) |
| An installation's name on the sign-in card (reads "Coach workspace") | Read from the registry | spec 13 |
| Moving a database between a gym box and hosted, both directions | Not in the Definition of Done; "if there is time" in spec 12 | spec 12, `docs/remote/databases.md` |
| Browser logins to the broker | Online it is open to read, accepted while the data is test data; needed before a real program's athletes use it | spec 12, Phase 4 and Non-goals |
| Un-archiving an athlete from a screen | The server rule exists (spec 02); the button belongs with archived athletes in Analytics | spec 09 |
| Opening a past session (athlete) | Built last in spec 10, only if there is time | spec 10, Phase 4 |
| The coach interface redesign | Only if there is time before November 11 | specs 06–09, 11 |
| Moving CI onto the Dell | Only safe once the repo is private | spec 12, Deferred |
| An image pull key that renews itself (a GitHub App) | The 90-day token is renewed by hand meanwhile | spec 12, Phase 0 result |
| A real secrets vault (beyond k3s encrypting Secrets on disk) | One server does not need it yet | spec 12, Phase 7 |
| Ansible in place of `bootstrap.sh` | The script is enough for one machine | spec 12, Deferred |
| A second node | Cut on 2026-10-14; nothing assumes one node | `docs/remote/hosting.md` |

---

## The project's Definition of Done

From the submitted form (`~/Downloads/4903 Student Project- Devin Walton.pdf`),
in priority order:

1. The app runs on k3s at a public HTTPS link, with automatic certificates and CI/CD.
2. Coach accounts secured: setup code, administrator manages coach logins, no
   well-known demo login in production.
3. Coach and athlete roles; athletes join only sessions assigned to their group, each
   on their own rack.
4. Remote athlete access: personal login link, session link from any network,
   encrypted live updates.
5. A separate demo installation from the same template.
6. Remote sensors over MQTT with TLS, one credential each, settings stored on the sensor.
7. End to end, live or on video, from a different network with a real sensor.
8. Developer documentation.
9. Weekly progress reports to Dr. Prather, with commit links.
10. Final presentation: slides, 20 minutes plus 10 of questions.

**Item 11, added 2026-10-06 (goes on the next weekly report):** a unified coach
interface. The front end and back end need to agree, and the local and hosted versions
need to look and behave alike, before a version is published. Specs 06–09.

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
  adds it ("Add to the existing sessions?"). Explained in `docs/journal/database.md`.
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
