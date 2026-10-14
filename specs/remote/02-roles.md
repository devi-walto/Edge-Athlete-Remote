# Feature Spec 2: Roles — administrator, coach, athlete

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Done 2026-10-07, merged into `SprintBranch`
- Form item: Definition of Done #3
- Depends on: [01 Secure coach accounts](01-coach-accounts.md)
- Next: [05 Hosted mode](05-hosted-mode.md), then 03 and 04

## Why

Today "coach" means "logged in" and nothing more. The check is one line in
`django/event_handler/permissions.py` and it guards 32 endpoints. That was a recorded,
accepted trade for a gym with two staff logins.

It stops being acceptable the moment an athlete has a login: that login would be able
to edit the roster, end sessions and delete plans. **This spec has to be finished
before the first athlete login can exist.** Spec 03 creates those logins; it must not
start until this one is merged.

### Decided 2026-10-06 — every coach may use Room Layout

Found in spec 01's Phase 3 rehearsal. Eight routes need the administrator flag today:
assigning a tablet to a rack, removing a rack, releasing all racks, linking or replacing
a rack's sensor, changing how a sensor is read, and the sensor scan and verify routes
(`IsActiveStaff` in `views.py`). That predates coach accounts and went unnoticed because
every login was the staff demo login.

**Devin's decision: regular coaches need to be able to help set a room up, so these
eight routes take any coach.** That keeps the agreed rule true: the administrator flag
controls only managing coach logins (`/api/coaches/…`), and nothing else.

Build it in this spec, with the role checks:

- The eight routes move from `IsActiveStaff` to the coach check. `IsActiveStaff` is
  then unused and is deleted; `IsInstallationAdmin` stays, for coach logins only.
- The Room Layout page's "Authorize sensor setup" step accepts any coach.

**Done when** (add to the phase that changes the permission classes):

- [x] A coach who is not an administrator can assign a tablet to a rack, link a
      sensor, replace a sensor, and release a rack.
- [x] No login, and an athlete login, are refused on all eight.
- [x] A coach who is not an administrator still gets `403` from every `/api/coaches/…` route.
- [x] `IsActiveStaff` appears nowhere in the code.
- [ ] *(Browser)* A regular coach completes Room Layout for one rack from start to finish.

**Result, 2026-10-07.** Built in Phase 1. Nine routes moved, not eight: linking a sensor and
unlinking one are two routes. The browser check is still open: finishing Room Layout
needs a sensor in range, so it is for Devin to do once on the gym box.

## User story

As a coach, I want athlete logins to be able to do only athlete things, so that giving
an athlete access to their own rack can never give them my controls.

## Decisions this spec locks in

**A login's role is decided by what it is attached to.** Nothing is stored as a "role".

| Role | How the server knows | Can do |
|---|---|---|
| **Administrator** | Active, has a coach profile, and Django's `is_staff` is on | Everything a coach can, plus manage coach logins |
| **Coach** | Active and has a coach profile (`CoachProfile`, from spec 01) | The whole coach workspace |
| **Athlete** | Active and attached to an athlete record (`Athlete.user`, new) | Their own rack in a session they belong to; reading their program's published results |
| **None of these** | — | **Refused everywhere** |

- **One coach role.** No head/assistant powers. The head/assistant label on a training
  group (`TrainingGroupCoach.role`) stays a display label and is never checked.
- **A login is a coach or an athlete, never both.** A coach who also lifts gets a
  separate athlete record with no login, the same as any gym athlete.
- **Refused by default.** A login with neither a coach profile nor an athlete record
  gets nothing. That is the safe answer to a half-created account.
- **Rejected:** Django's built-in groups as role labels (a label and the athlete link
  could disagree); a `role` column on the user table (means swapping the user model in a
  project that already has data).

## What exists today

- `permissions.py`: `IsCoach` (authenticated), `IsActiveStaff` (authenticated, active,
  staff). After spec 01: also `IsInstallationAdmin`, the same test as `IsActiveStaff`.
- `settings.py`: `DEFAULT_PERMISSION_CLASSES = IsAuthenticated`. JWT access token 8
  hours, refresh 7 days.
- `models.py`: `Athlete` has no link to a login. After spec 01 it has `is_active`.
- After spec 01, the sign-in response and `GET` on the coach-session route already
  return `username`, `is_staff` and `must_change_password`.

## Scope

- `Athlete.user`: an optional one-to-one link to a login.
- Permission classes that test for a real role.
- Every coach-only endpoint refuses an athlete.
- The sign-in response says which role signed in.
- Archiving an athlete turns their login off.
- The coach app refuses to load for an athlete login, and says why.

## Non-goals

- Creating athlete logins (spec 03).
- The 21 open endpoints (spec 05).
- What an athlete may read or do on a rack (specs 04 and 05).
- The athlete's own screens.

---

## Phase 0 — The link and the role helper

- Migration `0026`: add `Athlete.user`, a nullable one-to-one to the user model.
  `on_delete=SET_NULL`: deleting a login must never delete an athlete's history.
- `django/event_handler/roles.py` (new), with one function, `role_of(user)`, returning
  `"administrator"`, `"coach"`, `"athlete"` or `None`. Every permission class and every
  view that needs to know asks this one function.
- A login with both a coach profile and an athlete link is a data error: `role_of`
  returns `None` for it and logs a warning.

**Done when:**

- [x] `0026` applies to an empty database and to a copy of an existing one, and
      `makemigrations --check` reports no drift.
- [x] `role_of` returns the right answer for: an administrator; a coach; an athlete; a
      login with neither; a login with both; an inactive login of each kind (all
      `None`); an anonymous request (`None`).
- [x] Deleting a login leaves its athlete record, sets and reps untouched.
- [x] The full Django suite still passes.

**Result, 2026-10-07.** Built on `feature-roles`. Suite 491 → 502. `0026` was applied
to an empty throwaway database and to an existing one; no drift.

**Stop. Devin reviews.**

## Phase 1 — The checks

Rewrite `permissions.py` on top of `role_of`:

| Class | Lets through |
|---|---|
| `IsCoach` | administrator, coach |
| `IsInstallationAdmin` | administrator |
| `IsAthlete` | athlete |
| `IsCoachOrAthlete` | any of the three |

`IsCoach` keeps its name on purpose: 32 endpoints already use it, and its meaning
becomes the one the name always claimed.

**Done when:**

- [x] **One test walks every route that uses `IsCoach`** — discovered from the URL
      configuration, not typed out — and asserts, for each allowed method: a coach is
      not refused for permission; an athlete gets `403`; a login with no role gets
      `403`; no login gets `401`. A new coach route added later is covered without
      anyone remembering to add a test.
- [x] The same walk for the administrator-only routes: a coach gets `403`.
- [x] Every existing test that signs in as a plain user still passes — which means the
      test fixtures give that user a coach profile. Fix the fixtures, not the checks.
- [x] The full Django suite passes.

**Result, 2026-10-07.** Suite 502 → 520. The walk reads 73 routes out of the URL
configuration: 43 coach routes (65 route-and-method pairs) and 3 administrator routes.
It also fails if any route is guarded by "signed in" alone, apart from "who am I" and
changing your own password. `IsActiveStaff` is deleted, not kept as an alias (the Room
Layout decision above). 37 older test users were given a coach profile; no check was
loosened. Two open-to-read routes check for a coach inside the view (`athletes`,
`room-state?details=true`); they now answer `403` to a signed-in non-coach and have their
own tests. The last-administrator rule now counts coach logins only.

**Stop. Devin reviews.**

## Phase 2 — Signing in, and archiving

- The sign-in response and the session route add `role`, and for an athlete
  `athlete_id` and `athlete_name`.
- A login with no role is refused **at sign-in** with a plain message, not handed a
  token that then fails everywhere.
- Archiving an athlete (`is_active = False`, from spec 01) also sets their login's
  `is_active` to false; unarchiving turns it back on. Inactive logins are already
  refused by the JWT layer on every request, so access ends at once.

**Done when:**

- [x] Sign-in returns the right `role` for all three; `athlete_id` only for an athlete.
- [x] A login with no role cannot sign in.
- [x] After an athlete is archived, a request made with a token issued **before** the
      archive gets `401`.
- [x] Unarchiving restores sign-in. The athlete's history is unchanged throughout.

**Result, 2026-10-07.** Suite 520 → 536, using real sign-in tokens.

- The login link lives in `Athlete.save()`, not in the archive route, so no code path can
  archive an athlete and forget the login. It acts only when archived-or-not changes:
  editing an athlete never switches a login back on.
- **There is no un-archive route or screen yet.** The server rule is built and tested at
  the model; the button belongs with the archived-athletes work in spec 09.
- **Found and fixed: renewing a sign-in ignored a switched-off login.** The stock renewal
  route kept issuing tokens to a deactivated coach or archived athlete for up to a week.
  Each token was refused on use, so nothing leaked. `/api/auth/refresh/` now asks
  `role_of` first. This also closes it for deactivated coaches (spec 01).
- **For Phase 3:** the sign-in screen replaces every `401` with "The username or password
  was not accepted", so the plain no-role sentence is sent but not yet shown.

**Stop. Devin reviews.**

## Phase 3 — The coach app

- After sign-in, if `role` is `athlete`, the coach app shows a short screen — "This is
  the coach workspace. Use the session link your coach sent you." — with a sign-out
  button, and loads nothing else.
- The Coaches entry in the account menu keys off `role === "administrator"`.
- The sign-in screen shows the server's sentence when a login is refused for having no
  role (`code: no_role`), not the wrong-password message.

**Done when:**

- [x] *(Frontend test)* An athlete sign-in on `/coach` renders the notice and makes no
      coach API requests.
- [x] *(Browser)* A coach and an administrator see exactly what they saw before.
- [x] The frontend suite passes and the production build succeeds.

**Result, 2026-10-07.** Frontend 281 → 288; Django still 536; production build succeeds.

- The role is stored beside the token at sign-in, so the workspace knows it is an
  athlete before it asks the server anything. With an athlete signed in the only
  requests are sign-in and "who am I".
- The notice is one page, `NotACoach.jsx`, used by the workspace, the account pages and
  Room Layout. The sensor-setup sign-in on a rack tablet refuses an athlete outright.
- *(Browser, on a throwaway copy)* An athlete sees the notice; a login attached to
  nothing sees the server's sentence; a coach sees the workspace and Room Layout and no
  Coaches entry; an administrator sees Coaches, which lists the two coaches and neither
  of the other logins.
- Docs updated: `docs/journal/apis.md`, `docs/remote/access.md`, `docs/reference/spec.md`.

---

## Acceptance criteria

- [x] An athlete login is refused by every coach-only and administrator-only endpoint.
- [x] A login attached to nothing is refused everywhere, including at sign-in.
- [x] Archiving an athlete ends their access immediately and keeps their history.
- [x] No coach or administrator loses anything they could do before.
- [x] Nothing behaves differently between a gym box and a hosted installation.

## Risks

| Risk | What reduces it |
|---|---|
| A coach route is missed and stays open to athletes | The Phase 1 test discovers routes from the URL configuration rather than a list |
| Existing coaches are locked out because they have no coach profile | Spec 01's migration `0025` gives every existing login one; Phase 1 fails loudly if a fixture user lacks it |
| Someone adds a third kind of login later and it silently becomes a coach | Refused-by-default: a new kind gets nothing until a class lets it through |

## Docs to update when done

`docs/journal/apis.md` — the section titled *"Coach" means "logged in", and nothing
more* is no longer true; rewrite it with what forced the change and what was rejected.
`docs/remote/access.md` — section 5 (two kinds of login) becomes a description of the
code rather than a plan.
