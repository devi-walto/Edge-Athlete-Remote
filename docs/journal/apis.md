# The APIs

How everything talks to the server. Every route is listed below, grouped by what it
touches — the summary is visible, the detail is one click away.

The few things at the top cut across all of them.

## What the routes act on

Most endpoints below are a verb on one of these. Worth a glance before reading the
tables — half the route names only make sense once you can see what owns what.

```{include} ../_erd.md
:parser: myst
```

Full detail in {doc}`../reference/database`; the reasoning in {doc}`database`.

## The permission rule

**Anything a rack tablet must do is open. Anything that changes the plan or the room
needs a coach login.** 21 routes open and 41 need a coach's login (counted October 7, 2026; the eight sign-in and coach-login routes below are counted separately). Until October 7, nine of those 41, the Room Layout routes, needed an administrator. They now take any coach, because a coach has to be able to help set a room up; the administrator flag guards managing coach logins and nothing else.

**What forced it.** A rack tablet is a kiosk. It boots unattended into full-screen
mode, nobody signs in to it, and there is no keyboard in front of a squat rack. But it
still has to register itself, ask which rack it is, read a plan, and submit a set.

**What we rejected, and why.** Giving each tablet its own credential — provisioning,
storing and rotating a secret on a device that lives in a public room and gets
periodically wiped, for a network that is already private, offline, and has no route
to the internet.

**What it cost — say this out loud.** **Anyone who joins the gym Wi-Fi can read
training data and submit sets.** That is an accepted trade. It is why the Wi-Fi
password matters more than it looks, and why the wall display shows no names
(see {doc}`dashboard`). If this ever runs on a network that is not private, this is
the first decision to revisit — and the hosted service is that network: see
{doc}`../remote/access`.

## A login's role comes from what it is attached to

Until October 2026 this section was titled *"Coach" means "logged in", and nothing
more*. The check was one line: is this request authenticated? That was a recorded,
accepted trade for a gym with two staff logins.

**What forced the change.** Athletes get logins on the hosted service
({doc}`../remote/access`). Under the old check, an athlete's login could edit the
roster, end a session and delete a plan. The check had to be right before the first
athlete login could exist.

**What we chose.** Nothing stores a role. One function, `role_of` in
`django/event_handler/roles.py`, works it out from what the login is attached to:

| Role | How the server knows |
|---|---|
| Administrator | active, has a coach profile, and Django's staff flag is on |
| Coach | active and has a coach profile |
| Athlete | active and attached to an athlete record (`Athlete.user`) |
| None | anything else: **refused everywhere, including at sign-in** |

Every permission class asks that one function. `IsCoach` kept its name on purpose: 43
routes already used it, and its meaning became the one the name always claimed. Sign-in
and "who am I" report the role, so a screen knows who it is talking to before it asks
for anything.

- **Refused by default.** A login attached to nothing, or to both a coach profile and
  an athlete record, gets nothing. That is the safe answer to a half-made account, and
  to any new kind of login nobody has planned for yet.
- **Archiving an athlete switches their login off**, and bringing them back switches it
  on. The rule lives on the athlete record's own save step, not in the archive route, so
  no route can archive an athlete and forget the login. It acts only when
  archived-or-not actually changes.
- **Renewing a sign-in asks the same question.** The stock renewal route only checked
  that the renewal token was genuine, and so kept issuing tokens to a switched-off login
  for up to a week. Each was refused when used; the renewal now refuses too.

**What we rejected, and why.**

- *Django's built-in groups as role labels.* A label and the athlete link could
  disagree, and then one of them is lying.
- *A `role` column on the user table.* It means swapping the user model in a project
  that already has data.
- *Head-coach and assistant powers.* The label on a training group stays a display
  label and is never checked. One coach role; the administrator flag adds exactly one
  thing.

**What it cost.**

- A coach who also lifts cannot use one login for both. They get a separate athlete
  record, like any other athlete.
- 37 older tests created a bare login and called it a coach. Each now gives its user a
  coach profile. No check was loosened to make an old test pass.
- Coach routes are found by a test that reads the URL configuration, so a route added
  later is covered without anyone remembering. The price is that the test sends
  stand-in requests to every coach route, and a view that fails on a stand-in address
  has to be told apart from a view that refused the caller.
- There is still no way to bring an archived athlete back from a screen. The server
  rule exists; the button comes with the archived-athletes work in Analytics.

## Signing in, and coach logins

These eight routes are not in the generated tables further down, because they live in
the project's own `urls.py` (`django/basestation_config/urls.py`) beside sign-in, not
in the app's. They came with the coach-accounts work, written by Braydon and brought
into this repository in October 2026.

| Route | Methods | Access | What it does |
|---|---|---|---|
| `/api/auth/login/` | `POST` | open | Username and password in; tokens out, plus whether a password change is due |
| `/api/auth/refresh/` | `POST` | open | A fresh access token from a refresh token |
| `/api/auth/setup/` | `GET` | open | Whether this installation still needs claiming, and whether a setup code is waiting |
| `/api/auth/setup/` | `POST` | open, **needs the setup code** | Creates the first administrator. Refused for good once anyone exists |
| `/api/auth/me/` | `GET` | 🔒 any login | Who is signed in: username, administrator or not, password change due or not |
| `/api/auth/password/` | `POST` | 🔒 any login | Change your own password |
| `/api/coaches/` | `GET` `POST` | 🔒 administrator | List the coaches; add one with a temporary password, shown once |
| `/api/coaches/{id}/` | `PATCH` | 🔒 administrator | Deactivate, reactivate, make or remove an administrator |
| `/api/coaches/{id}/reset/` | `POST` | 🔒 administrator | A new temporary password for that coach |

`POST` to sign-in, setup and password is limited by the web server to ten attempts a
minute from one address.

**What forced it.** There was one login, `coach` / `coachpass`, typed into the form
for you. On a gym's closed Wi-Fi that was an accepted shortcut. On a server on the
internet it is an open door.

**What we chose.**

- **A new installation is claimed with a one-time code that only the machine prints.**
  Reaching the website is not enough to own it.
- **One coach role, and one administrator flag.** Every coach can do everything in the
  workspace. The flag does exactly one thing: it lets a coach manage coach logins.
- **A temporary password opens the change-password route and nothing else.** While a
  change is due, every coach route answers `403` with `code: password_change_required`.
  It is `403` and never `401` on purpose: the screens treat `401` as "your login is
  gone" and throw it away, which would bounce the coach back to the sign-in form
  forever.
- **The coaches list is the logins that have a coach profile**, not every login. They
  are the same thing today. They stop being the same the day athletes can sign in.
- **What the website cannot do takes the machine.** `setup_code`, `make_admin` and
  Django's own `changepassword` are commands, not routes.

**What we rejected, and why.**

- **A head coach who outranks assistant coaches.** One kind of coach is enough, and a
  hierarchy nobody exercises is wrong the first time someone needs it. "Head coach"
  stays what it was: a label on a training group that no route checks.
- **Letting any coach create logins.** Then a single leaked coach password becomes as
  many logins as the finder likes.
- **Letting the first visitor become the administrator.** That is a race a student
  can win.
- **Email password recovery.** It means collecting email addresses and sending mail
  from a box that is often offline. An administrator resets a coach's password and
  hands them a temporary one.

**What it cost.**

- **A box whose only administrator forgets their password needs someone at the
  machine.** There is no way round that from the website, and there is not meant to be.
- **For a moment, two people know a new coach's password.** It is temporary and it is
  locked to the change-password form, but it does not expire. One-time login codes
  that expire are planned to replace it.
- **Room Layout still needs an administrator.** Assigning tablets to racks and linking
  sensors were locked to the old staff flag before any of this existed. With more than
  one coach that is wrong, and it is being opened to every coach.

## One path through authentication

Every authenticated request from the front end goes through a single helper. Adding a
coach screen? Import that, rather than writing another fetch wrapper.

Scattered token handling is how one screen quietly ends up unauthenticated, or how a
token refresh fixes three screens and misses the fourth. The token lives in browser
storage on purpose, so a page refresh does not sign a coach out mid-session.

## Route order is load-bearing

Some routes are catch-alls — `racks/<device_id>/` matches almost anything in that
position, including the literal word `register`.

**They are registered last on purpose.** The specific routes above them must match
first, or the catch-all swallows them and they all break at once. **Add new routes
above the catch-alls.** This produces a confusing 404 on an endpoint you can see in
the file.

<!-- ROUTES SECTION START — generated by docs/refresh-routes.py -->

<!-- Groups below are ## so this document keeps a single H1. -->

Every route the server has, grouped by what it touches. The summary is visible; the
detail is one click away. Generated from `urls.py` and the permission decorators, so
it matches what is actually wired up.

## System

Health, and the settings an operator changes before a real gym uses the box.

:::::{dropdown} 4 routes

<!-- routes:system:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/health/` | `GET` | open | 200 when the app can serve and the database answers, 503 when it cannot | `health` |
| `/api/system/info/` | `GET` | open | Which kind of installation this is, and which build | `system_info` |
| `/api/system/status/` | `GET` | 🔒 coach | Coach-only | `system_status` |
| `/api/system/wifi-password/` | `POST` | 🔒 coach | Queue a Wi-Fi password change for the host agent to apply | `change_wifi_password` |
<!-- routes:system:end -->

:::::

### Why `/api/health/` is first and open

It answers one question: can this container serve a request and reach the database?

Registered first and deliberately unauthenticated, because **nothing else should have
to be working for it to answer**. It is what the container healthcheck uses, and a
health check that needs a login or a working session is one that lies during exactly
the outage you built it for.

## The room

Rack screens, and the sensors on them.

:::::{dropdown} 22 routes

<!-- routes:the-room:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/racks/register/` | `POST` | local: open · online: refused | A rack tablet announces itself | `rack_register` |
| `/api/racks/racknumber/` | `GET` | local: open · online: refused | A waiting tablet asks "which rack am I?" Returns its rack_number (empty until a coach assigns it) | `rack_racknumber` |
| `/api/racks/unassigned/` | `GET` | 🔒 coach | Coach-only: list every tablet still waiting for a rack (rack_number empty) | `racks_unassigned` |
| `/api/racks/node-assignment/` | `PUT` | 🔒 coach | Select this physical rack's registered node | `rack_node_assignment` |
| `/api/racks/release-all/` | `POST` | 🔒 coach | Coach-only: force-clear EVERY rack in one go — the end-of-session reset | `racks_release_all` |
| `/api/racks/<int:rack_number>/node/` | `DELETE` | 🔒 coach | Coach-only: take whatever sensor is on this rack OFF it | `rack_node_unlink` |
| `/api/ble/scans/` | `POST` | 🔒 coach | — | `ble_scans` |
| `/api/ble/verifications/` | `POST` | 🔒 coach | — | `ble_verifications` |
| `/api/racks/<int:rack_number>/ble-selection/` | `PUT` | 🔒 coach | — | `rack_ble_selection` |
| `/api/racks/<int:rack_number>/sensor-health/` | `GET` | local: open · online: coach, or the rack's own athlete | — | `rack_sensor_health` |
| `/api/racks/<int:rack_number>/state/` | `GET,PATCH` | local: open · online: coach, or the rack's own athlete | Read the authoritative rack mirror or apply one fenced state transition | `rack_state` |
| `/api/racks/<int:rack_number>/controller/acquire/` | `POST` | local: open · online: coach, or the rack's own athlete | Claim or renew ownership after validating the physical rack identity | `rack_controller_acquire` |
| `/api/racks/<int:rack_number>/controller/heartbeat/` | `POST` | local: open · online: coach, or the rack's own athlete | Extend the current lease using server time; heartbeats are not visible events | `rack_controller_heartbeat` |
| `/api/racks/<int:rack_number>/controller/release/` | `POST` | local: open · online: coach, or the rack's own athlete | Release a quiet rack without allowing an open set to lose its owner | `rack_controller_release` |
| `/api/racks/<int:rack_number>/checkin/` | `POST` | local: open · online: coach, or the rack's own athlete | Record that an athlete signed in at this rack (Phase 11 Step 2) | `rack_checkin` |
| `/api/racks/<int:rack_number>/checkins/` | `GET` | local: open · online: coach, or the rack's own athlete | The rack's HOT LIST: athletes this rack currently 'owns' — those whose NEWEST check-in this session is this rack | `rack_checkins` |
| `/api/racks/<int:rack_number>/nfc-tap/` | `POST` | local: open · online: refused | Consume one NFC tap and resolve it to an athlete in the active session | `rack_nfc_tap` |
| `/api/racks/<int:rack_number>/` | `DELETE` | 🔒 coach | Coach-only: FORCE-CLEAR a rack so a fresh screen can take it over | `rack_remove` |
| `/api/nodes/` | `GET` | local: open · online: coach | Open: list every sensor node and its latest status | `nodes_list` |
| `/api/nodes/register/` | `POST` | local: open · online: coach | A sensor announces itself | `node_register` |
| `/api/nodes/<str:node_id>/acquisition-kind/` | `PUT` | 🔒 coach | Provision the transport trusted to supply one registered node's health | `node_acquisition_kind` |
| `/api/racks/<str:device_id>/` | `PATCH` | 🔒 coach | Coach-only: give a waiting tablet its rack number, or release it | `rack_assign` |
<!-- routes:the-room:end -->

:::::

### Known gap: nothing can un-assign a rack

`racks/<device_id>/` only ever *sets* a rack number. **Nothing clears one**, and
`racks/unassigned/` only lists tablets with no number — so a tablet assigned once can
never return to that list. See the deadlock in {doc}`rack-tablet`.

## People

Athletes, the groups they train in, and the staff who run those groups.

:::::{dropdown} 10 routes

<!-- routes:people:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/athletes/` | `GET,POST` | local: open · online: coach | GET: list lifters (open) | `athletes_view` |
| `/api/athletes/<int:athlete_id>/` | `GET,PATCH,DELETE` | 🔒 coach | Coach-only: read or update one lifter | `athlete_detail` |
| `/api/athletes/<int:athlete_id>/login-link/` | `POST,DELETE` | 🔒 coach | POST: make a new link for this athlete | `athlete_login_link` |
| `/api/athletes/<int:athlete_id>/login/` | `DELETE` | 🔒 coach | Remove this athlete's login | `athlete_login` |
| `/api/athletes/<int:athlete_id>/sensors/<str:node_id>/` | `DELETE` | remote only · 🔒 coach | Remove an athlete's sensor (lost, stolen, or passed on) | `athlete_sensor` |
| `/api/training-groups/` | `GET,POST` | 🔒 coach | Coach-only: list or create TrainingGroups | `training_groups_view` |
| `/api/training-groups/<int:group_id>/athletes/` | `GET,POST,DELETE` | 🔒 coach | Coach-only: who is in this TrainingGroup | `training_group_athletes_view` |
| `/api/training-groups/<int:group_id>/coaches/` | `GET,POST,PATCH,DELETE` | 🔒 coach | Coach-only: who runs this TrainingGroup | `training_group_coaches_view` |
| `/api/athletes/<int:athlete_id>/program/` | `GET,PUT,DELETE` | 🔒 coach | What this athlete is training, and which TrainingGroup decides it | `athlete_program_view` |
| `/api/athletes/<int:athlete_id>/program-exercises/<int:exercise_id>/override/` | `GET,PUT,DELETE` | 🔒 coach | Coach-only: an exception for one athlete on one prescribed movement | `athlete_exercise_override_view` |
<!-- routes:people:end -->

:::::

## The movement catalog

The shared vocabulary plans are written in.

:::::{dropdown} 2 routes

<!-- routes:the-movement-catalog:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/exercises/` | `GET` | local: open · online: anyone signed in | Open: list the movement catalog — the official set of exercises the rack and coach pickers choose from, so nobody hand-types a name into drift | `exercises_list` |
| `/api/block-categories/` | `GET,POST` | 🔒 coach | Coach-only: the catalog's label vocabulary — "Off-season", "Football" | `block_categories_view` |
<!-- routes:the-movement-catalog:end -->

:::::

## Templates

Reusable training a coach designs once.

:::::{dropdown} 7 routes

<!-- routes:templates:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/training-blocks/` | `GET,POST` | 🔒 coach | Coach-only: the reusable TEMPLATES a coach designs once and redeploys | `training_blocks_view` |
| `/api/training-blocks/<int:block_id>/` | `GET,PATCH` | 🔒 coach | Coach-only: read or amend one block's own fields | `training_block_detail` |
| `/api/training-blocks/<int:block_id>/workouts/` | `GET,POST` | 🔒 coach | Coach-only: the individual days inside a template, and their movements | `training_block_workouts_view` |
| `/api/training-blocks/<int:block_id>/workout-order/` | `PUT` | 🔒 coach | Coach-only: set the order of the days in a template | `training_block_workout_order` |
| `/api/training-blocks/<int:block_id>/workouts/<int:workout_id>/` | `PATCH,DELETE` | 🔒 coach | Coach-only: rename or remove one day in a template | `training_block_workout_detail` |
| `/api/training-blocks/<int:block_id>/workouts/<int:workout_id>/exercise-order/` | `PUT` | 🔒 coach | Coach-only: set the order of the movements inside one template day | `training_block_exercise_order` |
| `/api/training-blocks/<int:block_id>/workouts/<int:workout_id>/exercises/<int:exercise_id>/` | `PATCH,DELETE` | 🔒 coach | Coach-only: change or remove one prescribed movement in a template day | `training_block_exercise_detail` |
<!-- routes:templates:end -->

:::::

## Programs and the calendar

A template placed in time, and the slots it generates.

:::::{dropdown} 5 routes

<!-- routes:programs-and-the-calendar:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/training-programs/` | `GET,POST` | 🔒 coach | Coach-only: a template DEPLOYED for a TrainingGroup, starting on a date | `training_programs_view` |
| `/api/training-programs/<int:program_id>/promote/` | `POST` | 🔒 coach | Coach-only: turn this program into a new reusable TrainingBlock | `training_program_promote` |
| `/api/scheduled-sessions/` | `GET` | 🔒 coach | Coach-only: the calendar — planned training slots | `scheduled_sessions_view` |
| `/api/scheduled-sessions/<int:slot_id>/` | `GET,PATCH` | 🔒 coach | Coach-only: read a slot, or MOVE it to another date | `scheduled_session_detail` |
| `/api/scheduled-sessions/<int:slot_id>/session/` | `POST` | 🔒 coach | Coach-only: turn a planned slot into a real training session | `scheduled_session_create_session` |
<!-- routes:programs-and-the-calendar:end -->

:::::

## Running a training day

The live session, and the room's current picture.

:::::{dropdown} 9 routes

<!-- routes:running-a-training-day:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/room-state/` | `GET` | local: open · online: coach | The live picture of the room, for the wall display and the coach tablet | `room_state` |
| `/api/sessions/` | `POST` | 🔒 coach | Coach-only: start a training session | `sessions_view` |
| `/api/sessions/active/` | `GET` | local: open · online: anyone signed in | The rack tablet's ONE startup fetch (open, no login) | `sessions_active` |
| `/api/sessions/active/athlete/<int:athlete_id>/progress/` | `GET` | local: open · online: coach, or the athlete asked about | The rack's athlete DAY-VIEW (open, no login) | `athlete_progress` |
| `/api/sessions/active/status/` | `GET` | local: open · online: anyone signed in | Room state for the active session: each athlete's live status + since-when | `session_status` |
| `/api/sessions/<int:session_id>/` | `PATCH` | 🔒 coach | Coach-only: update a session | `session_detail` |
| `/api/sessions/<int:session_id>/join/` | `POST` | remote only · athlete | Join a session online: get your own rack, checked in, with your own sensor on it | `session_join` |
| `/api/sessions/<int:session_id>/participation/` | `GET,POST,DELETE` | 🔒 coach | Coach-only: which TrainingGroups are training in this session, and what they're doing | `session_participation_view` |
| `/api/sessions/<int:session_id>/start/` | `POST` | 🔒 coach | Coach-only: start a session that was created ahead of time | `session_start` |
<!-- routes:running-a-training-day:end -->

:::::

## Performed work

Sets, reps, prescriptions, maxes, and everything derived from them.

:::::{dropdown} 9 routes

<!-- routes:performed-work:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/prescriptions/` | `GET,POST` | local: open · online: coach, or the athlete asked about | GET: an athlete's training plan for today, ?athlete={id} to filter (open) | `prescriptions_view` |
| `/api/reports/` | `GET` | 🔒 coach | Coach-only: browse finished training days, newest first | `reports_view` |
| `/api/reports/<int:report_id>/` | `GET` | 🔒 coach | Coach-only: one finished day in full | `report_detail_view` |
| `/api/reports/<int:report_id>/pdf/` | `GET` | 🔒 coach | Coach-only: the same finished day, as a printable PDF | `report_pdf_view` |
| `/api/reference-maxes/` | `POST` | 🔒 coach | Coach-only: record what athletes can currently lift | `reference_maxes_view` |
| `/api/sets/` | `POST` | local: open · online: coach, or the rack's own athlete | Start a set: create the empty set record when an athlete begins, so the finish endpoint has something to fill in | `set_create` |
| `/api/sets/<int:set_id>/complete/` | `POST` | local: open · online: coach, or the rack's own athlete | Save a finished set | `set_complete` |
| `/api/analytics/session/<int:session_id>/` | `GET` | 🔒 coach | Coach-only: a quick summary of one session — how many sets and reps total, and each athlete's average velocity | `analytics_session` |
| `/api/analytics/athlete/<int:athlete_id>/` | `GET` | 🔒 coach | Coach-only: everything the athlete and history tabs need (P13) | `analytics_athlete` |
<!-- routes:performed-work:end -->

:::::

### `sets/<id>/complete/` is the only way rep data reaches the database

It takes a **whole set at once** — the summary plus every rep — written in a single
transaction. There is no endpoint that accepts an individual rep, and no streaming
path; the server's message subscriber ignores rep topics entirely (see
{doc}`real-time`).

**Why that matters as a rule:** the database can never hold a half-written set. Either
the whole set landed or none of it did. Anything adding a per-rep write path is
fighting the design in {doc}`rack-tablet`, not extending it.

## Spreadsheet import

Two routes for all three kinds of sheet.

:::::{dropdown} 2 routes

<!-- routes:spreadsheet-import:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/imports/preview/` | `POST` | 🔒 coach | Check an uploaded spreadsheet and write NOTHING | `import_preview` |
| `/api/imports/` | `POST` | 🔒 coach | Re-check an uploaded spreadsheet and, if it is clean, save it in one step | `import_commit` |
<!-- routes:spreadsheet-import:end -->

:::::




## Signing in and accounts

Sign-in, first-run setup, coach accounts, and athletes using a login link.

:::::{dropdown} 10 routes

<!-- routes:signing-in-and-accounts:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/auth/setup/` | `GET,POST` | open | First-run enrollment | `SetupView` |
| `/api/auth/me/` | `GET` | signed in | "Who am I": any signed-in login may ask, whatever its role | `CoachSessionView` |
| `/api/auth/password/` | `POST` | signed in | Let a signed-in coach replace their own password | `PasswordChangeView` |
| `/api/auth/login-link/lookup/` | `POST` | open | "Who is this link for?" Only that athlete's name: the page says "Hi <name>" | `LoginLinkLookupView` |
| `/api/auth/login-link/redeem/` | `POST` | open | Use the link: make the athlete's login, and sign them straight in | `LoginLinkRedeemView` |
| `/api/coaches/` | `GET,POST` | 🔒 administrator | List every coach login, or create one with a temporary password (administrators) | `CoachListView` |
| `/api/coaches/<int:user_id>/` | `PATCH` | 🔒 administrator | Change one coach login: switch it off or on, or make it an administrator | `CoachDetailView` |
| `/api/coaches/<int:user_id>/reset/` | `POST` | 🔒 administrator | Give one coach a new temporary password, to change at their next sign-in | `CoachResetPasswordView` |
| `/api/auth/login/` | `POST` | open | Sign in with a username and password, coach or athlete; wrong tries are slowed down | `CoachTokenObtainPairView` |
| `/api/auth/refresh/` | `POST` | open | Renew a sign-in, refused for a login that was switched off or lost its role | `CheckedTokenRefreshView` |
<!-- routes:signing-in-and-accounts:end -->

:::::

## Sensors online

An athlete's own sensor: a one-time code to add it, the sensor claiming itself with it, and removing it (spec 14). Remote only.

:::::{dropdown} 4 routes

<!-- routes:sensors-online:start -->
| Route | Methods | Access | What it does | Handler |
|---|---|---|---|---|
| `/api/athlete/sensor-code/` | `GET,POST` | remote only · athlete | POST: a one-time code to give a new sensor (shown once; works once, for 15 minutes) | `sensor_code` |
| `/api/athlete/sensors/` | `GET` | remote only · athlete | The sensors that belong to the signed-in athlete | `my_sensors` |
| `/api/athlete/sensors/<str:node_id>/` | `DELETE` | remote only · athlete | Remove one of my sensors | `my_sensor` |
| `/api/sensors/claim/` | `POST` | remote only · open | A sensor claims itself with an athlete's code and gets its own login | `SensorClaimView` |
<!-- routes:sensors-online:end -->

:::::
<!-- ROUTES SECTION END -->

