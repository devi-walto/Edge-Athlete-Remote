# Feature Spec 1: Secure coach accounts

- Owner: Devin Walton
- Date: 2026-10-05
- Status: **Phases 0, 1 and 2 done 2026-10-06 on branch `feature-coach_accounts`. Phase 2: every check passed but one, which is met only in part (an archived athlete's history; see Phase 2 result). Waiting on Devin's review before Phase 3**
- Mockup: `F_SignIn`, `F_FirstRun`, `F_Coaches`, `F_AccountMenu` on the canvas's **Final designs** page ("The same in both: accounts and access"), also in [`specs/ui/mockups/coach-ui-final.html`](../ui/mockups/coach-ui-final.html). Look: [spec 06](../ui/06-design-rules.md) rule 9
- Index and shared decisions: [specs/README.md](../README.md)
- Form item: Definition of Done #2 ("Coach accounts are secured")
- Next spec: 02 — roles (coach, athlete, everyone else refused)

> Specs live in `specs/`, outside `docs/`, so they are never published to the public
> docs site. Decisions that outlive a spec get written into `docs/remote/` in the last
> phase.

## Why this is first

Today anyone who can open the coach page can sign in as `coach` / `coachpass` — the
login form even fills those in for you. On a gym's closed Wi-Fi that was an accepted
shortcut. On the public internet it is an open door, and every later feature (athlete
logins, session links) sits behind it.

Most of the fix already exists: Braydon wrote it on the team repository in September.
This spec brings that work here, fits it into the redesigned coach screens, and closes
three gaps it left.

## User story

As a coach, I want the installation to be claimed with a one-time code and coach
logins to be created by an administrator, so that nobody can walk in with a known
password or make themselves the boss by getting to the website first.

## Decisions this spec locks in

| Decision | Detail |
|---|---|
| **One coach role** | Every coach can see and do everything in the coach workspace. No head/assistant powers. |
| **One administrator flag** | Django's built-in `is_staff`. It controls **only** managing coach logins: create, reset, deactivate, promote. More than one person can have it. |
| **The word is "Administrator"** | Never "head coach" for this flag. "Head coach" stays what it already is: a display label on a training group, which is never checked for access. |
| **Claiming needs control of the machine** | The first administrator is created with a one-time setup code that only a command run on the machine prints. Gym box: whoever is at the box. Hosted: the operator. |
| **The demo login is development-only** | `coach` / `coachpass` refuses to exist unless `DEBUG` is on. Same rule on a gym box and online. |
| **Same code in both versions** | Nothing in this spec behaves differently on a gym box and a hosted installation. |

## Where the code comes from

Three commits on the team repository's `main` (fetched here as `refs/tmp/team-main`):

| Commit | What it is | Plan |
|---|---|---|
| `78260b4` | Setup code, coach profiles, administrator-only account management, archiving an athlete, the screens for all of it | **Bring over.** One conflict, in `Dashboard.jsx` |
| `b59a531` | A compose file for previewing on a laptop at `localhost:8088` | **Skip** — a convenience, not security. See open questions |
| `5a35928` | The demo-login guard (mixed with a rename of that preview file) | **Bring over the guard by hand**, without the preview-file parts |

**The conflict is bigger than it looks.** His screens were written for the old eight-tab
coach page. That page no longer exists here — the redesign replaced it with SESSION /
ANALYTICS / PLANNING — so his "coaches" and "roster" tabs have nowhere to attach.
`coachTabs.js`, which he edits, is no longer used by anything. The backend comes over
cleanly; the screens have to be re-homed. That is Phase 2.

## The three gaps this spec closes

1. **An upgraded box ends up with no administrator.** His migration marks setup as
   "already done" whenever a login exists, but promotes nobody. An existing gym box
   would have coaches and no one able to manage them.
2. **Existing logins have no coach profile.** Only logins created through his new screen
   get one. Spec 02 will use the profile to tell coaches from athletes, so every
   existing login needs one now.
3. **His coach list shows every login.** Harmless today, when every login is a coach.
   Wrong the moment athletes have logins. The list must show coaches only.

## Scope

- One-time setup code to create the first administrator (`manage.py setup_code`)
- Administrator-only API and screen for coach logins: list, create with a temporary
  password, reset, deactivate, promote, demote
- Forced password change on first sign-in with a temporary password
- Guards: the last administrator cannot be removed; nobody can deactivate or demote
  themselves
- A `make_admin` command for upgraded boxes that have logins but no administrator
- A coach profile for every existing login
- The coach list shows coaches only
- The demo login refuses to run outside development; the login form no longer fills in
  credentials
- Archiving an athlete: hidden from pickers, history kept
- The screens placed in the redesigned coach interface

## Non-goals

- **Athlete logins, and tightening "coach" to mean "has a coach profile"** — Spec 02.
  This spec only lays the groundwork (profiles exist, the list is filtered).
- Login links, session links, virtual racks — Specs 03 and 04.
- The "my groups" filter.
- The laptop preview compose file (`b59a531`).
- The parent registry of installations — hosting work.
- His `RosterWorkspace` screen as a tab. The redesign already has a roster in
  PLANNING → Groups; only **archive** is new, and it is added there.

---

## Phase 0 — Bring the code over, change nothing visible

**Goal:** his backend is in the repository and everything that worked still works.
No new screen is wired up yet.

- Work on the branch `feature-coach_accounts`, started from `SprintBranch`.
- Record the baseline first: how many Django tests and frontend tests pass on `SprintBranch`.
- Bring over `78260b4`. For the `Dashboard.jsx` conflict, **keep the redesigned
  version**; his new screen files come in but are not attached to anything yet.
- Bring over the demo guard from `5a35928` by hand (`ensure_demo_coach.py`, its tests,
  the seed service's flag in `docker-compose.yml`). Leave the preview-file parts out.
- Drop his edit to `coachTabs.js` — that file is dead here.

**Done when:**

- [x] Migrations `0023` and `0024` apply cleanly to a **copy of an existing database**
      and to an empty one.
- [x] `makemigrations --check` reports no drift.
- [x] The full Django suite passes: the baseline count, plus his new tests.
- [x] The full frontend suite passes and the production build succeeds.
- [x] In a browser, an existing coach can still sign in and use SESSION, ANALYTICS and
      PLANNING exactly as before. *(One visible difference; see below.)*
- [x] A rack screen still works with no login (the open routes are untouched).

### Phase 0 result — 2026-10-06

| Check | `SprintBranch` (same as `main` that day) | `feature-coach_accounts` |
|---|---|---|
| Django tests | 447 pass | **468 pass** (447 + his 21) |
| Frontend tests | 265 pass | **279 pass** (265 + his 14) |
| Production build | succeeds | succeeds |
| `makemigrations --check` | — | no drift |
| Docs build (warnings fatal) | — | passes |

- **Migrations on a copy of the running database:** `0023` and `0024` applied; 2
  logins, 1 administrator, 4 athletes (all active), 34 sessions, 52 sets and 109 reps
  before and after; setup marked complete. On an empty database: applied, setup left
  open for a setup code.
- **`CoachProfile` rows after migrating: 0.** That is gap 2 above, confirmed; Phase 1's
  migration `0025` fixes it.
- **The branch's server against that copy:** the existing coach signs in (the reply
  now also carries `must_change_password`), a wrong password is refused, eight rack
  routes answer with no login exactly as the running app does, and four coach routes
  refuse without a login and answer with one.
- **The two browser checks**, done by running this branch as a second copy of the app
  on port 8090 against a copy of the database, beside the running app:
  - **Coach:** signed in through the form, then opened all three states and every tab
    (twelve screens). No failed request and no page error. The text on each screen was
    compared with the running app's: **seven identical, five differ in one way** — the
    athlete picker in ANALYTICS now lists athletes **alphabetically**. Before, it was
    in the order the database returned them. That comes from Braydon's change to the
    athlete list and is kept: a fixed order is better than an accidental one.
  - **Rack screen, no login:** sensor shown as live, check-in, Ready, countdown, a set
    with the simulated sensor (4 reps counted), End Set, summary, rest. The set was
    saved with its four reps.

**Where this differs from "bring `78260b4` over as it is", and why:**

1. **`main.jsx` is not wrapped in his first-run screen, and the Room Layout page keeps
   its own login form.** Both attach his screens, which is Phase 2. His wrapper also
   sits in front of every route, rack screens included.
2. **`GET /api/athletes/` stays open.** His commit made it coach-only. The connection
   test and gym tools read it with no login, and this phase promised the open routes
   would not move. Spec 05 closes it for `remote`. His archive filter on that route
   is kept.
3. **His guide is `docs/_COACH_ACCOUNTS.md`, private, with a credit line.** It describes
   screens that are not attached yet, and anything in `docs/` without the underscore is
   published. Its content moves into `docs/remote/` in the last phase.
4. **His frontend tests got an in-memory `localStorage` when none works.** On Node 25
   and later, Node's own `localStorage` hides the test environment's and all 14 failed
   in setup. They pass on either now. No test's meaning changed.
5. **Startup no longer creates the demo login** (his `Dockerfile` change, kept: with the
   guard, creating it at startup would stop a real installation from starting).
   Existing databases keep theirs. **A brand-new database on this branch has no login
   and no screen to claim it until Phase 2**; `manage.py setup_code` plus
   `POST /api/auth/setup/` works by hand, and `docker compose --profile seed` still
   makes the demo login.
6. **`nginx` now limits sign-in, setup and password attempts** to 10 a minute per
   address (his change, kept). It does not touch token refresh or any other route.

**Stop. Devin reviews before Phase 1.**

## Phase 1 — The server rules

**Goal:** the three gaps are closed on the server, with tests.

- **Coach profiles for everyone who exists.** A new migration (`0025`) gives every
  existing login a coach profile, with "must change password" off.
- **The first administrator gets a profile too** when an installation is claimed.
- **The coach list shows coaches only** — logins that have a coach profile.
- **`manage.py make_admin <username>`** makes an existing login an administrator. It
  refuses a username that does not exist, and says so plainly.
- **Signing in tells the screen who you are:** username, administrator or not, and
  whether a password change is due.

**Done when** (each is an automated test unless marked):

- [x] After `0025`, every pre-existing login has exactly one coach profile, and running
      the migration twice changes nothing.
- [x] Claiming an installation creates a login that is an administrator **and** has a
      coach profile.
- [x] A wrong setup code is refused. An expired one is refused. A used one cannot be
      used again. Issuing a new code makes the old one stop working.
- [x] Once an installation is claimed, the setup route refuses to create another
      administrator.
- [x] A login with no coach profile does **not** appear in the coach list.
- [x] A coach who is not an administrator gets `403` from every account-management
      route — list, create, reset, change.
- [x] The last administrator cannot be deactivated or demoted. Nobody can deactivate or
      demote themselves.
- [x] A coach created by an administrator must change their password before any other
      coach route answers them.
- [x] `make_admin` promotes an existing login, and fails clearly on an unknown one.
- [x] `ensure_demo_coach` refuses to run with `DEBUG` off, and runs with it on.
- [x] The full Django suite still passes.

### Phase 1 result — 2026-10-06

**Django suite: 491 pass** (468 after Phase 0, plus 23 new in
`test_coach_account_rules.py`). No migration drift. No frontend file changed.

Run against the Phase 0 code, 8 of the 23 new tests fail, which is the point: they are
the rules that were missing. The other 15 pin rules Braydon's code already kept (the
setup code, claiming, self-demotion), so they cannot quietly stop being true.

| What | How |
|---|---|
| **Profiles for existing logins** | Migration `0025`. On a copy of the running database both logins got one profile each, "must change password" off. Adds only what is missing; going backwards does nothing, on purpose |
| **Coaches only** | `coach_logins()` in `coach_accounts.py`: the list, the detail route and the reset route all start from logins that have a coach profile. A login without one is not listed and answers `404` to reset, promote and deactivate |
| **`make_admin <username>`** | New command. Promotes, never creates, never touches the password. An unknown name fails and lists the logins that do exist |
| **The temporary password is a lock, not a suggestion** | `IsCoach`, `IsActiveStaff` and `IsInstallationAdmin` now refuse with `403` and `code: password_change_required` while a change is due. Signing in, `GET /api/auth/me/` and the change-password route stay reachable. Open routes are unaffected |
| **Who am I** | `GET /api/auth/me/` → `username`, `is_staff`, `must_change_password` (Braydon's, now tested). The sign-in reply carries `must_change_password` |

**Found while doing it:**

- **The forced password change was only in the screen.** In the code as brought over,
  a coach holding a temporary password could call every coach route directly. The
  spec's rule ("before any other coach route answers them") needed the server to
  refuse, so it now does. Phase 2's screens should treat that `403` code as "show the
  change-password form".
- **The "last administrator" rule can only ever be hit by an administrator acting on
  themselves**, because only an administrator may call these routes at all. It is
  still checked separately, and tested directly, so it holds if that ever changes.

**One thing added beyond the spec:** `make_admin --reactivate`. Promoting a
deactivated login would let nobody sign in, so the command refuses it unless asked to
switch the login back on too. Without that, a box whose only administrator was
deactivated in the database would have no way back.

**Stop. Devin reviews before Phase 2.**

## Phase 2 — The screens, built to the Final designs

**Goal:** a coach can do all of it without touching a terminal, after the first claim.

**Whose screens these are.** Braydon's commit came with working screens, but they were
written for the old eight-tab coach page, which the redesign replaced. Since then the
Final designs were agreed (2026-10-06). So this phase **builds the Final design
boards, and takes the working logic out of Braydon's files** — the calls to the
server, the forced password change, the guards, the error messages — rather than
showing his screens as he laid them out. His files have been in the tree, unattached,
since Phase 0. Credit him in each file that carries his logic.

| Screen | Final design | Where it goes | Built from |
|---|---|---|---|
| **First-run setup** — setup code, username, password twice, and "Where the code comes from" beside it | `F_FirstRun` | Shown instead of the app while an installation is unclaimed | The status check and submit logic in his `FirstRunSetup.jsx` |
| **Sign in** — the installation's name, username, password | `F_SignIn` | Replaces today's form. **No credentials filled in.** | The sign-in half of his `CoachAccess.jsx` |
| **Change password** | No board: the same card as sign in, with current password, new password, new password again | Forced after a temporary password; also in the account menu | His `ChangePassword.jsx` |
| **Coaches** — banner, the temporary-password card, the table, **Add coach** | `F_Coaches` | The account menu, **administrators only** | His `CoachManagement.jsx` |
| **Account menu** — signed in as, the Administrator badge, Coaches, Change password, Log out | `F_AccountMenu` | Opens from the top bar, as today | The existing menu, restyled |
| **Archive athlete** | The **Archive** action on a roster row (`F_Local_Roster`) | Today's roster, in PLANNING → Groups. It moves to the Roster tab when spec 07 builds that tab | The archive call in his `RosterWorkspace.jsx` |

**What is not built:** his `RosterWorkspace` as a screen (the design already has a
roster), and his tab entries for the old page. When this phase ends, any of his screen
files that nothing imports are deleted, and so is the dead `coachTabs.js`.

**The look** (spec 06 rule 9, and the boards):

- Sign in and first-run setup are a solid card with a 10px corner on the dark page,
  with the lime "EA" mark, because nobody is signed in. Inputs are `#0b1114` with a
  6px corner. One lime button each.
- The top bar is the bold one, with the signed-in coach's profile image on the lime
  square. The account menu's **Administrator** is the lime pill badge.
- Coaches: the header banner, then the temporary password in its own bordered card
  with **Copy**, then one table on one solid surface. **Add coach** is the screen's one
  lime button. Row actions are quiet text; **Deactivate** is the only red one.
- On a `remote` installation the sign-in page also shows "Athlete? Open the session
  link your coach shared." and **Athlete sign in**. That line is added by spec 03, not
  here; leave room for it.

**Rules:**

- Every label says **Administrator**. "Head coach" appears nowhere for this flag.
- A temporary password is shown **once**, when created or reset, with a line telling
  the administrator to pass it on now because it cannot be shown again.
- The Coaches entry is hidden from non-administrators — and the server refuses them
  anyway (Phase 1), so hiding it is a courtesy, not the lock.
- Archived athletes disappear from pickers and the active roster. Their history stays
  readable in ANALYTICS.
- **An unclaimed installation shows first-run setup to every device, rack screens
  included** (Braydon's behaviour, kept: nothing should run on a box nobody has
  claimed). A rack screen that was already set up can still reopen while the server is
  unreachable, as his wrapper allows.

**Done when:**

- [x] His screen tests are rewritten against the new screens and pass, along with the
      full frontend suite and the production build. No behaviour he tested is dropped
      without a line here saying why.
- [x] *(Browser)* Sign in, first-run setup, Coaches and the account menu match their
      Final design boards.
- [x] *(Browser)* On an empty database the site shows first-run setup and nothing else.
- [x] *(Browser)* The sign-in form is empty when it loads.
- [x] *(Browser)* An administrator sees **Coaches** in the account menu; a regular
      coach does not.
- [x] *(Browser)* Creating a coach shows a temporary password once. Signing in with it
      forces a password change, and the workspace opens only after that.
- [ ] *(Browser)* Archiving an athlete removes them from the session picker and the
      roster; their past sets still open in ANALYTICS. **Met in part; see below.**
- [x] *(Browser)* All three states — SESSION, ANALYTICS, PLANNING — still work as
      before for a regular coach.
- [x] The word "head coach" does not appear on the Coaches screen or in its messages.
- [x] No file under `react/src/coach/` is left that nothing imports.

### Phase 2 result — 2026-10-06

**Frontend: 281 tests pass, production build succeeds. Django: 491 pass** (unchanged).

| Screen | File | Notes |
|---|---|---|
| Sign in | `coach/SignIn.jsx` | Replaces the dashboard's two-column sign-in and the Room Layout page's form (the one that arrived with `coach` / `coachpass` typed in). Always empty |
| First-run setup | `coach/FirstRun.jsx`, `coach/FirstRunGate.jsx` | The gate wraps the whole app in `main.jsx` |
| Change password | `coach/ChangePassword.jsx` | Forced after a temporary password; also at `/coach/account/password` |
| Coaches | `coach/Coaches.jsx` in `coach/AccountPage.jsx` | At `/coach/account/coaches` |
| Account menu | `coach/AccountMenu.jsx` | In the workspace top bar and on the Coaches page |
| Archive athlete | `coach/archiveAthlete.js`, a row action in `coach/GroupsView.jsx` | |
| Shared look | `coach/account.css` | Solid surfaces, from the boards |

Deleted: Braydon's `CoachAccess`, `FirstRunSetup`, `CoachManagement`, `RosterWorkspace`
(and their stylesheets), and the dead `coachTabs.js` with its test.

**Checked in a browser**, on a second copy of the app against a copy of the database
and against an empty one:

- **Empty database:** `/`, `/coach/planning`, `/rack/1`, `/dashboard` and the Coaches
  address all show first-run setup. With no code issued the screen says how to get one.
  A wrong code is refused with a sentence; a too-weak password is refused with the
  reason; the right code creates the administrator, opens the workspace, and the setup
  screen does not come back. `coach` / `coachpass` does not sign in.
- **Existing database:** the sign-in form loads empty; a wrong password gets "The
  username or password was not accepted."; the administrator's menu shows the badge and
  **Coaches**; adding a coach shows the temporary password once and **Done** removes it
  from the page.
- **The new coach:** signing in with the temporary password shows "Choose your own
  password" and nothing else; a coach route called directly with that login answers
  `403 password_change_required`; after changing it the workspace opens. Their menu has
  no badge and no **Coaches**, and typing the Coaches address shows "Only an
  administrator can manage coach logins."
- **Three states as a regular coach:** no failed request, no page error.
- **Archive:** while the athlete is in a running session the server refuses and the
  screen shows its sentence, "End the active training session before removing this
  athlete." With no session running, the athlete leaves the roster and every picker;
  their sets are still stored, and the list including archived athletes still has them.

**The check met only in part: an archived athlete's history.** Their sets are kept, and
every frozen daily report that includes them still opens from ANALYTICS → Reports. But
ANALYTICS → Athlete and History pick an athlete from a list, and an archived athlete is
no longer on it, so their own page cannot be opened. Fixing that means the Analytics
picker offering archived athletes, which is a decision for spec 09 (it changes the
picker for everyone). **Devin to decide:** fix it here, in spec 09, or accept it.

**Found and fixed while building:**

- **A temporary password would have signed the coach straight back out.** The live
  room feed asks for coach detail. With a change due, the server answered "not signed
  in" (`401`), and the workspace reacts to that by discarding the login. The server now
  answers `403 password_change_required` there and on adding an athlete, like every
  other coach route, and a test pins it. (A Phase 1 rule, corrected here.)
- **The workspace's own button styles were overriding the account menu's** (it was
  drawn in the wrong size and weight). The menu's rules are now specific enough to win.
- **Logging out on the Coaches page** now returns to the workspace's address, so the
  next person to sign in lands on the workspace and not on a page about someone else's
  account.

**Where it differs from the boards, and why:**

- **No installation name on the sign-in card.** The board shows one under "Edge
  Athlete". Nothing stores a name for an installation yet (that is the parent registry,
  in the hosting work), so the line reads "Coach workspace".
- **Add coach opens a one-field form** (username) above the table. The board shows only
  the button. Braydon's optional "choose the temporary password yourself" field is
  gone: the server always makes one.
- **Deactivate and Reset password ask first**, in the browser's own confirm box. A
  styled dialog is spec 06's shared-pieces work.
- **The session strip is not on the Coaches page**, matching the board. The bottom
  navbar is, with nothing selected.
- **Of Braydon's 14 screen tests, 13 are carried over** to the new screens, and 4 are
  added. Not carried over: creating and editing an athlete in his separate roster
  page, because that page was not built.

**Stop. Devin reviews before Phase 3.**

## Phase 3 — Rehearse a fresh install and an upgrade

**Goal:** prove both ways a real box meets this change, start to finish, by hand.

**A. Fresh installation** — empty database, `DEBUG` off:

- [ ] The site asks for a setup code. The code comes only from `manage.py setup_code`.
- [ ] Claiming creates the first administrator; the setup screen never appears again.
- [ ] `coach` / `coachpass` does not work, and the demo command refuses to create it.

**B. Upgraded gym box** — a copy of a database that already has coach logins:

- [ ] After migrating, every existing coach can still sign in and use everything.
- [ ] Nobody is an administrator yet, and **Coaches** is not shown to anyone.
- [ ] `manage.py make_admin <username>` on the machine makes one of them an
      administrator; after they sign in again, **Coaches** appears.

**C. The gym still runs:**

- [ ] A rack screen with no login can register, check an athlete in, and save a set.
- [ ] The wall display still shows the room.

**Stop. Devin reviews before Phase 4.**

## Phase 4 — Write it down, then merge

- **Install guide** (`docs/guides/base-station.md`): replace "log in with `coach` /
  `coachpass`" with claiming by setup code; add `make_admin` for upgrades.
- **`docs/journal/apis.md`:** the new routes in the route table (regenerated, not
  hand-edited), and the permission notes updated.
- **`docs/journal/coach-tablet.md`:** coach accounts — what forced it, what was chosen,
  what was rejected (a head/assistant hierarchy; letting any coach manage logins), what
  it cost. Fold in what is still true from his `docs/coach-accounts.md`.
- **`docs/remote/access.md`:** "Setting up the coaches" says Administrator, states the
  one-coach-role decision, and says the operator hands over the setup code on a hosted
  installation.
- Credit Braydon for the original work wherever it is described.

**Done when:**

- [ ] `./docs/build.sh` passes with warnings fatal.
- [ ] Following the install guide on an empty database, word for word, ends at a
      working coach workspace.
- [ ] The route table lists every new route with the right lock.
- [ ] The branch is merged into `SprintBranch` and pushed. (`main` is updated from
      `SprintBranch` by CI/CD, or by Devin until that exists; the docs are published from `main`.)
- [ ] The weekly report's Definition of Done shows item 2 as **Done**.

---

## Acceptance criteria (the whole spec)

- [ ] A new installation can only be claimed with a code printed on the machine.
- [ ] There is no known password that works outside development.
- [ ] Only an administrator can create, reset, deactivate, promote or demote a coach —
      enforced by the server, not just hidden in the screen.
- [ ] An installation can never be left with no administrator through the screen.
- [ ] An upgraded box keeps every existing coach working and has a documented way to
      get its first administrator.
- [ ] Every login that exists has a coach profile, and the coach list shows coaches only.
- [ ] A gym box with no logins at the rack works exactly as before.
- [ ] Nothing here behaves differently between a gym box and a hosted installation.

## Risks

| Risk | What reduces it |
|---|---|
| The redesigned `Dashboard.jsx` and his version disagree about how sign-in state is held | Phase 0 keeps ours and attaches nothing; Phase 2 wires the screens deliberately, one at a time |
| An upgrade locks existing coaches out | Phase 0 tests the migrations on a copy of a real database; Phase 3B rehearses the whole upgrade |
| The demo login is still needed for local development | It still works with `DEBUG` on; the seed service keeps its explicit override |

## Decided (2026-10-05)

1. **The laptop preview compose file (`b59a531`) is skipped.** Bring it over later if wanted.
2. **Archive lives with the roster, not in a separate roster tab of Braydon's.** When
   this spec was written that meant PLANNING → Groups. [Spec 07](../ui/07-planning.md)
   moves the roster to its own **Roster** tab; put Archive wherever the roster is when
   Phase 2 is built.
3. **Merge into `SprintBranch` only after Phase 4**, with each phase reviewed on the branch first.
4. **The state-machine redesign takes precedence over Braydon's screens.** His screens
   are fitted into PLANNING / SESSION / ANALYTICS, never the other way round.

## Notes added 2026-10-06

- The role rules this spec prepares for are in [spec 02](02-roles.md). This spec only
  lays the groundwork (every login has a coach profile; the coach list is filtered).
- On a hosted installation the operator runs `setup_code` when creating the
  installation and passes the code to that program's coach. Same command, same code path.
- Count check: `IsCoach` guards 32 endpoints, `IsActiveStaff` 9, and 21 are open
  (2026-10-06). Earlier notes said 34 and 15.
