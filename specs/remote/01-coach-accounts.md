# Feature Spec 1: Secure coach accounts

- Owner: Devin Walton
- Date: 2026-10-05
- Status: **Approved 2026-10-05, not started.** Waiting on Devin's go to begin Phase 0
- Mockup: `FirstRun`, `SignIn`, `Coaches`, `AccountMenu` on the Remote page of the canvas (first-draft styling; follow [spec 06](../ui/06-design-rules.md) for the look)
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

- Work on a branch, `remote/coach-accounts`. `main` stays releasable.
- Record the baseline first: how many Django tests and frontend tests pass on `main`.
- Bring over `78260b4`. For the `Dashboard.jsx` conflict, **keep the redesigned
  version**; his new screen files come in but are not attached to anything yet.
- Bring over the demo guard from `5a35928` by hand (`ensure_demo_coach.py`, its tests,
  the seed service's flag in `docker-compose.yml`). Leave the preview-file parts out.
- Drop his edit to `coachTabs.js` — that file is dead here.

**Done when:**

- [ ] Migrations `0023` and `0024` apply cleanly to a **copy of an existing database**
      and to an empty one.
- [ ] `makemigrations --check` reports no drift.
- [ ] The full Django suite passes: the baseline count, plus his new tests.
- [ ] The full frontend suite passes and the production build succeeds.
- [ ] In a browser, an existing coach can still sign in and use SESSION, ANALYTICS and
      PLANNING exactly as before.
- [ ] A rack screen still works with no login (the open routes are untouched).

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

- [ ] After `0025`, every pre-existing login has exactly one coach profile, and running
      the migration twice changes nothing.
- [ ] Claiming an installation creates a login that is an administrator **and** has a
      coach profile.
- [ ] A wrong setup code is refused. An expired one is refused. A used one cannot be
      used again. Issuing a new code makes the old one stop working.
- [ ] Once an installation is claimed, the setup route refuses to create another
      administrator.
- [ ] A login with no coach profile does **not** appear in the coach list.
- [ ] A coach who is not an administrator gets `403` from every account-management
      route — list, create, reset, change.
- [ ] The last administrator cannot be deactivated or demoted. Nobody can deactivate or
      demote themselves.
- [ ] A coach created by an administrator must change their password before any other
      coach route answers them.
- [ ] `make_admin` promotes an existing login, and fails clearly on an unknown one.
- [ ] `ensure_demo_coach` refuses to run with `DEBUG` off, and runs with it on.
- [ ] The full Django suite still passes.

**Stop. Devin reviews before Phase 2.**

## Phase 2 — The screens, in the redesigned interface

**Goal:** a coach can do all of it without touching a terminal, after the first claim.

| Screen | Where it goes |
|---|---|
| **First-run setup** — enter the setup code, choose a username and password | Shown instead of the app while an installation is unclaimed |
| **Sign in** | Replaces the current form. **No credentials filled in** |
| **Change password** | Forced after a temporary password; also in the account menu |
| **Coaches** — list, add, reset, deactivate, make or remove administrator | The account menu (the logo), **administrators only** |
| **Archive athlete** | The existing roster in PLANNING → Groups |

- Every label says **Administrator**. "Head coach" appears nowhere for this flag.
- A temporary password is shown **once**, when created or reset, with a line telling
  the administrator to pass it on now because it cannot be shown again.
- The Coaches entry is hidden from non-administrators — and the server refuses them
  anyway (Phase 1), so hiding it is a courtesy, not the lock.
- Archived athletes disappear from pickers and the active roster. Their history stays
  readable in ANALYTICS.

**Done when:**

- [ ] His screen tests are adapted to the new placement and pass, along with the full
      frontend suite and the production build.
- [ ] *(Browser)* On an empty database the site shows first-run setup and nothing else.
- [ ] *(Browser)* The sign-in form is empty when it loads.
- [ ] *(Browser)* An administrator sees **Coaches** in the account menu; a regular
      coach does not.
- [ ] *(Browser)* Creating a coach shows a temporary password once. Signing in with it
      forces a password change, and the workspace opens only after that.
- [ ] *(Browser)* Archiving an athlete removes them from the session picker and the
      roster; their past sets still open in ANALYTICS.
- [ ] *(Browser)* All three states — SESSION, ANALYTICS, PLANNING — still work as
      before for a regular coach.
- [ ] The word "head coach" does not appear on the Coaches screen or in its messages.

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
- [ ] The branch is merged to `main`, pushed, and the docs are published.
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
3. **Merge to `main` only after Phase 4**, with each phase reviewed on the branch first.
4. **The state-machine redesign takes precedence over Braydon's screens.** His screens
   are fitted into PLANNING / SESSION / ANALYTICS, never the other way round.

## Notes added 2026-10-06

- The role rules this spec prepares for are in [spec 02](02-roles.md). This spec only
  lays the groundwork (every login has a coach profile; the coach list is filtered).
- On a hosted installation the operator runs `setup_code` when creating the
  installation and passes the code to that program's coach. Same command, same code path.
- Count check: `IsCoach` guards 32 endpoints, `IsActiveStaff` 9, and 21 are open
  (2026-10-06). Earlier notes said 34 and 15.
