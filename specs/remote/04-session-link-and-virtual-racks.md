# Feature Spec 4: The session link and virtual racks

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started. No decisions open (who may join: decided 2026-10-14;
  where a browser lands online: decided 2026-10-17)
- Form items: Definition of Done #3 and #4
- Depends on: [02 Roles](02-roles.md), [05 Hosted mode](05-hosted-mode.md), [03 Login links](03-athlete-login-links.md)
- Mockup: coach side `F_Remote_Session` on the canvas's Final designs page. Athlete side:
  the `B_*` boards (lifting) and `A_Waiting`, `A_NotOnSession`, `A_Ended` on the
  "Remote athlete view (proposed)" page, each beside a screenshot of today's rack screen

## Why

This is the feature the project exists for: an athlete on another network opens a link,
lands on their own rack screen, lifts, and the workout is saved on the server — the
same flow as the gym.

In the gym a rack is a tablet a coach set up, with a sensor a coach linked. A coach
running fifty athletes over a video call cannot set up fifty racks. So when a signed-in
athlete joins, **the server makes their rack for them**, and their sensor attaches by
itself.

## User stories

As a coach, I want to share one link in the call and watch athletes appear in the live
room, without setting anything up per athlete.

As an athlete, I want to open that link and be on my own rack screen, with my sensor
already connected.

## Decisions this spec locks in

- **The session link is not a secret.** It names a session. Who gets in is decided by
  the login, so it is safe in a group chat.
- **Their device is their rack.** No "which rack are you at?" question.
- **One athlete, one rack, per session.** Two athletes can never share one; the same
  athlete rejoining gets the same one back.
- **Racks appear on join and are released when the session ends.** Nothing piles up.
- **A sensor belongs to an athlete**, linked once. On join it attaches to that
  athlete's rack. An athlete cannot use a sensor that is not theirs.
- **Siblings on one bar each get their own rack and their own sensor.** Both sensors
  feel every rep, but a rack only listens while its own set is running
  (`react/src/rack/RackScreen.jsx`, the effect that subscribes "ONLY while a set is
  active"). No new code is needed for this; it gets a test.
- **Hosted only.** On a gym box none of this is reachable.
- **The athlete uses the same rack screen as the gym, not a second one** (Devin,
  2026-10-06). It was built to be portable and is already a phone-width column. A rack
  that has an owner simply skips choosing an athlete. See Phase 3.
- **A rack with an owner always has that athlete selected.** This is a fact the server
  keeps (`RackRuntime.owner_athlete`), not a guess such as "only one person checked in
  recently". That guess was considered and rejected: in the gym the first athlete to
  check in would trip it, it depends on a timer, and it would still let a remote
  athlete reach a list of names.
- **Online, nobody lands on "Set up this device"** (Devin, 2026-10-17). The
  local/remote switch decides what `/` shows: a coach or an athlete, by login. A local
  install keeps the picker exactly as it is. A coach can still open the display view
  online from a button during a live session; athletes cannot. See 3f.

### Decided 2026-10-14 — who may join

The agreed rule is **"the athlete must be in a training group assigned to the
session."** In the data, that is: one of the athlete's `training_groups` is the group
of a `TrainingProgram` that has a `SessionParticipation` on this session.

Spec 08 adds the **Quick Training Session**, where a coach picks athletes one by one
and may pick no workout at all. Such a session has a roster (`TrainingSession.athletes`)
but can have no program, and so no group.

**Decided by Devin: an athlete may join if they are on the session's roster, or in a
group taking part in it.** The roster is filled when a planned day is set up and when a
quick session is created, so this is the same rule for planned days and it does not
lock everyone out of a quick one.

## What exists today

- `RackScreen` (`device_id`, `rack_number`), `RackRuntime` (one row per `rack_number`:
  the controller lease, phase, selected athlete and exercise, current set),
  `RackCheckIn` (`session`, `athlete`, `rack_number`; newest wins), `Node`
  (`node_id`, `rack_number`, `last_seen`, …). `django/event_handler/models.py`.
- A rack's controller is one browser tab, identified by a token kept in
  `sessionStorage` (`react/src/rack/controllerIdentity.js`); the lease lasts 20 seconds.
  A tab that reloads loses the token — the reason the recovery flow exists
  (`rack_controller_acquire`, `recover`).
- `PUT /api/racks/node-assignment/` links a sensor to a rack, addressed by the screen's
  device id, and already refuses a sensor on another rack or with an open set.
- Room state (`room_state`) lists racks for the coach's live room.
- Sets are legal without a sensor (`set_create`).

## Scope

- Sensor ownership: `Node.owner`.
- `POST /api/sessions/{id}/join/`: the membership check, the rack, the sensor.
- Releasing virtual racks when a session ends.
- The rack screen on a rack that has an owner (Phase 3), plus two changes to the rack
  screen in both versions: rep bars in, the WT901 card out.
- What `/` shows on a remote installation (3f).
- The ownership half of spec 05's rules for rack endpoints.
- The coach's live room: virtual racks, sensor status, **Not joined yet**, **Copy
  session link**.
- Assigning a sensor to an athlete from the roster.
- Demo data (Phase 5): the seeder safe online, seeded athletes with their own simulated
  sensors, `eactl seed` and `eactl sim`.

## Non-goals

- Setting up a sensor's Wi-Fi, TLS to the broker, per-sensor credentials (sensors work).
- The athlete's "my history" page.
- A shared-device mode for two athletes on one phone.

---

## Phase 0 — Data

Migration `0028`:

- `Node.owner` — nullable FK to `Athlete`, `SET_NULL`. A gym sensor has no owner.
- `RackRuntime.owner_athlete` — nullable FK to `Athlete`, `SET_NULL`. Set only on a
  virtual rack. **This is the field spec 05's "the athlete whose rack it is" reads.**
- `RackRuntime.session` — nullable FK to `TrainingSession`, `SET_NULL`, so release can
  find a session's virtual racks.

Rack numbers: physical racks keep small numbers. **Virtual racks are numbered from
10 000 up**, so the two can never collide on an installation that runs both. One
constant, `VIRTUAL_RACK_BASE`.

**Done when:**

- [ ] The migration applies to empty and existing databases; no drift.
- [ ] Every existing rack and sensor has no owner and behaves as before.
- [ ] The full suite passes in both deployment modes.

**Stop. Devin reviews.**

## Phase 1 — Joining

`POST /api/sessions/{id}/join/` — athlete only, hosted only. In one transaction:

1. The session must be **started and not ended**. A session that is only set up
   returns `409 not_started` ("Your coach hasn't started this session yet").
2. The membership rule (decided above). Failing it returns
   `403 not_in_session`.
3. Find this athlete's virtual rack for this session; if there is none, take the next
   free number from `VIRTUAL_RACK_BASE` and create the `RackRuntime` with
   `owner_athlete` and `session`. Take a row lock so two joins cannot pick one number.
4. Check the athlete in on that rack **through the same service the check-in route
   uses**, so the rack's state already names them as the selected athlete when their
   screen opens.
5. If the athlete owns an active sensor, point it at the rack.
6. Return `{rack_number, sensor: {node_id, last_seen} | null}`.

Calling it again returns the same rack. Nothing else in the response.

**Done when:**

- [ ] An athlete on the roster (or in a participating group) gets a rack ≥ 10 000.
- [ ] An athlete outside the session gets `403`; a coach gets `403` (coaches do not
      take racks); no login gets `401`; a gym box returns `404`.
- [ ] Joining twice returns the same rack number and creates no second row.
- [ ] **Fifty athletes joining at once get fifty different racks** (a concurrency test).
- [ ] An athlete in two participating groups gets one rack.
- [ ] A session that is set up but not started, and one that has ended, both refuse.
- [ ] The athlete's sensor ends up on their rack; an athlete with no sensor gets
      `sensor: null` and can still lift.
- [ ] A sensor owned by athlete A is never attached to athlete B's rack.

**Stop. Devin reviews.**

## Phase 2 — "My rack" is enforced, and released

- Fill in spec 05's ownership stubs: on a hosted installation an athlete may call the
  rack endpoints **only for a rack whose `owner_athlete` is them**, may check in only
  themselves, and may create or complete a set only for themselves on that rack.
- **The controller lease follows the login when hosted.** An athlete who reloads the
  page must get their rack back without the recovery prompt, because nobody else can
  hold it. On a virtual rack, `rack_controller_acquire` treats "same owner athlete" as
  "same holder". The gym-box lease is unchanged.
- **An owned rack cannot lose its athlete.** Clearing the selected athlete, or
  checking a different athlete in, on a rack with an `owner_athlete` is refused
  (`409 owned_rack`), whoever asks.
- Ending a session releases its virtual racks: detach sensors, end any open set the way
  `_end_open_sets_on_rack` already does, delete the `RackRuntime` rows. Hook it into the
  existing end-of-session path.

**Done when:**

- [ ] Athlete A calling any rack endpoint for athlete B's rack gets `403`.
- [ ] Athlete A cannot check athlete B in, or post a set for athlete B.
- [ ] On an owned rack, an update that clears the selected athlete, and a check-in
      for anyone but the owner, both return `409` and change nothing.
- [ ] An athlete who reloads mid-set regains control of their rack and their set is
      still open and unharmed.
- [ ] After the session ends: no virtual `RackRuntime` rows remain, the sensors have no
      rack, an open set was ended and kept, and the report includes the remote sets.
- [ ] A physical rack's lease, recovery and release behave exactly as before
      (the existing tests pass unchanged).

**Stop. Devin reviews.**

## Phase 3 — The same rack screen, on a rack that has an owner

Mockups `B_Ready`, `B_Countdown`, `B_Active`, `B_Summary`, `B_Rest`, drawn from the
rack screen's own styles and set beside screenshots of it as it is today.

**How the screen already works** (checked in `react/src/rack/RackScreen.jsx`): the
lifting athlete is not chosen on the screen. Tapping a name sends a check-in, the
server records the athlete on the rack, and the screen draws whatever the rack's state
says. The list of names shows in exactly two cases: nobody is selected while idle, or
the rack is resting. So a rack whose state already names an athlete opens straight on
the Ready view. **There is no second flow and no second component.**

**3a. Getting there.** Route `/session/<id>` (the session link, and the home screen's
Join button): if not signed in, go to `/athlete` and come back. Call `join`, then
render the existing `RackLive` → `RackScreen` for the returned rack number, skipping
`RackNodeSetup` (there is no device or sensor to set up). Before that:

- `409 not_started` → "Your coach hasn't started this session yet", with the day's
  plan, retried every few seconds (`A_Waiting`);
- `403 not_in_session` → "You're not on this session. Ask your coach." (`A_NotOnSession`);
- the session ending while the athlete is on the screen → what they did today (`A_Ended`).

**3b. One new fact on the rack's state.** `GET racks/{n}/state/` and the controller
snapshot gain `owner_athlete: {id, name} | null`. It is added, nothing is renamed or
removed. **Before building, check this against the merge canon's frozen rack contract
(§6.3)**: that freeze covers the plan the rack reads, but confirm an added field on
rack state is allowed, and update `docs/reference/message-contract.md`.

**3c. What an owner changes on the screen.** One value, `owned = snapshot.owner_athlete != null`,
read in `RackScreen.jsx` and passed to `Idle.jsx`:

| When the rack has an owner | Where |
|---|---|
| The header shows the athlete's name where it says "Rack 7" | `RackScreen.jsx`, top bar |
| "Lifting · name · Not here?" is not drawn (the name is in the header; the button would clear an athlete who cannot be cleared) | `Idle.jsx` |
| The "or, next lifter" divider and list are not drawn on the rest screen | `RestPhase` |
| The check-in list and the card-reader polling never run (`showCheckInList` is false) | `RackScreen.jsx` |

Everything else is untouched: the session title, the phase badge, the day view, the
number pad for changing the load, the countdown, End Set and False Set, the summary,
the rest timer, the durable rep buffer, and **the footer (`phase`, `node`, `buffered`),
which stays word for word** because it is how you see that reps are being kept on the
device.

**3d. Changes to the rack screen in BOTH versions** (gym and remote; Devin, 2026-10-06):

- **The "WT901 movement" card is removed.** Local and remote both read reps from the
  MQTT sensor only, so the diagnostic has no job. This removes the card from
  `ActivePhase` and its two props; the separate WT901 rack agent under
  `scripts/hardware/` is not touched by this spec.
- **A "Velocity by rep" card takes its place**: one bar per rep in the running set,
  the value above it, coloured by the same green/yellow/red zone as the big number.
  The same card appears on the set summary, between Avg/Peak and Start Rest Timer.
  The screen already receives every rep; it keeps their velocities in a list for the
  current set. After a reload mid-set, bars show for the reps the snapshot can restore
  and for every rep after; if the snapshot cannot restore them, that is acceptable and
  the count and averages are still right.
- **A dot beside `node:` in the footer**, mint when the sensor's heartbeat is fresh and
  amber when it is not. This replaces the "Sensor checking" line that lived in the
  removed card. With no sensor the footer reads `node: —` as it does today, and
  lifting is still allowed.

**3e. End Set with no reps measured: confirm before saving** (both versions; Devin,
2026-10-06, as an edge-case precaution). Mockup `B_ConfirmSet`.

Today, pressing End Set when no reps arrived saves a real, completed set with 0 reps
and says nothing (`finishSet` in `RackScreen.jsx`). That happens with no sensor, and
with a sensor that was on but missed the set.

- **When:** End Set is pressed, it is not a False Set, and the rep buffer is empty. The
  trigger is "nothing was measured", never "this rack has no sensor".
- **What appears:** a full-screen form in the rack screen's own style, like the number
  pad for changing the load: "No reps were measured · Set 2 complete?", the movement,
  and two numbers, **reps** and **load**, filled in from the plan's target reps and
  the load on the bar. Tapping a number opens the existing number pad.
- **Complete** sends the same `complete` call with `reps_completed` as typed, an empty
  `reps` list and no velocities, and saves the typed load on the set. The server
  already accepts this; nothing checks that the count matches the list.
- **Go back** closes the form. The set is still open and still listening, so reps that
  arrive late are not lost.
- **One set at a time.** The form is for the set that was just ended, not a way to log
  several sets at once: every set is its own row and its own rest.
- **A typed set is never a personal record.** `_personal_records` skips a set that has
  no rep rows.
- **Wherever velocity is shown for a typed set** (the summary, the coach's room,
  History, the daily report) it reads "not measured", never 0.00. The summary shows
  the reps and "— m/s", as it already does for a missing value.

**3f. Where a browser lands, remote only** (Devin, 2026-10-17). Today `/` shows "Set up
this device" (Rack Tablet, Base Station Display, Coach Admin) to any browser with no
saved role (`Picker` and `Home` in `react/src/App.jsx`). That is right for a gym, where
someone sets up each tablet once. Online, a person is a coach or an athlete, known from
their login.

- **The switch decides; the gym code is left alone.** `Home` asks `useDeployment()`.
  When it says `local`, `Home` and `Picker` run exactly as today, picker included.
  When it says `remote`:
  - an athlete whose login is still valid goes to `/athlete`, their overview page
    (spec 10; until it exists, spec 03 Phase 4's placeholder);
  - everyone else goes to `/coach`, where the coach sign-in already links to the
    athlete one ("Athlete? …", spec 03 Phase 4).
- **A session link goes straight to the session.** `/session/<id>` with a valid login
  skips sign-in and the overview and joins at once (3a). Sign-in appears only when the
  login is missing or has expired, and it returns to the session afterwards.
- **Where an athlete can go online:** their overview and their session. Never the
  coach screens, the display view (dashboard), or the room's state (coach only, spec 05).
- **The display view, coaches only, by choice.** During a live session the coach's
  screen shows a button that opens the existing display view (`/dashboard`) for that
  session, for a TV or a second device signed in as that coach. It is not shown when no
  session is live. Normally nobody needs it; the default is the coach screens.
  - **Decided 2026-10-17: no display for athletes.** The display reads the room's state
    (`useLiveRoomState` → `room_state`), which stays coach only. Opening it to athletes
    would be a server change for a nice-to-have that may not be wanted.
- **A saved `device_role` is ignored online**, so an old setting in the browser cannot
  land someone on a rack screen.
- **While the switch has not answered yet** (the first moment of the page), `/` shows
  nothing rather than flashing the picker.
- **Only `/` and that button change.** What `/rack/setup` and `/dashboard` may do
  online is already decided by the server (spec 05).

**Done when:**

- [ ] *(Frontend test)* Rendered with an owner: no check-in list, no "Not here?", no
      next-lifter list, no card-reader request, and the header shows the athlete's name.
- [ ] *(Frontend test)* Rendered with no owner: the screen is the same as before this
      spec apart from 3d. The existing rack tests pass with only the WT901 assertions removed.
- [ ] *(Frontend test)* The footer shows `phase`, `node` and `buffered` in both cases.
- [ ] *(Frontend test)* Five reps arriving draw five bars in zone colours; the summary
      shows the same five.
- [ ] *(Frontend test)* No "WT901" text is rendered in either mode.
- [ ] *(Frontend test)* End Set with an empty buffer shows the form, prefilled with the
      target reps and the load; with one or more buffered reps it does not appear.
- [ ] *(Frontend test)* Go back leaves the set open and sends nothing; Complete sends
      exactly one `complete` call with the typed count and an empty rep list.
- [ ] A set completed with a count and no rep rows saves, counts toward "sets done",
      is flagged as neither a velocity nor a weight record, and appears in the report
      as not measured.
- [ ] False Set never shows the form.
- [ ] `RackScreen.jsx` is one component; there is no `MyRackScreen` or copy of it.
- [ ] *(Browser)* Opening the session link signed out → sign in → Ready view for that
      athlete, in one flow, with no list of names at any point.
- [ ] *(Browser)* With the simulator standing in for the athlete's sensor, a set runs
      and saves, the bars fill in, and the coach's live room shows the reps.
- [ ] *(Browser)* Pulling the network mid-set raises `buffered`, and it drains when the
      connection returns.
- [ ] *(Browser)* The gym rack screen (`/rack/...`) still offers the check-in list and
      rotates lifters.
- [ ] *(Frontend test)* Local, no saved role: `/` shows the picker, as today.
- [ ] *(Frontend test)* Remote: `/` never shows the picker, even with a saved
      `device_role`; a signed-in athlete goes to `/athlete`, anyone else to `/coach`.
- [ ] *(Browser)* Remote, athlete still signed in: the session link opens the rack
      screen with no sign-in step.
- [ ] *(Frontend test)* The display button shows for a coach only, and only while a
      session is live; an athlete's screens never show it.

**Stop. Devin reviews.**

## Phase 4 — The coach's side

Only when hosted:

- **Copy session link** on the session strip (`SessionWidget.jsx`). The link is
  `https://<this installation>/session/<id>`.
- The live room lists virtual racks by **athlete name**, with a sensor dot.
- **Not joined yet**: athletes who may join and have not, each showing *Has a login* or
  a **Send login link** shortcut (spec 03).
- On the roster: a **Sensor** column — the owned sensor's id and when it was last seen,
  or **Add sensor ID** (type the id from the sensor's label). `PUT
  /api/athletes/{id}/sensor/` `{node_id}`, coach only; a sensor has one owner at a time
  and reassigning it is allowed.

**Done when:**

- [ ] The room-state response includes virtual racks with their athlete and sensor
      status, for coaches only.
- [ ] "Not joined yet" is exactly the athletes who may join minus those who have.
- [ ] Assigning a sensor that another athlete owns moves it, and says so.
- [ ] *(Frontend test)* None of this renders on a gym box.
- [ ] *(Browser)* The copied link opens the right session for a signed-in athlete.

**Stop. Devin reviews.**

## Phase 5 — Demo data: seeded athletes with their own simulated sensors

Folded in from a separate seeder spec (Devin, 2026-10-17), so it is built once, after
sensors can belong to athletes. It is what the rehearsal (Phase 6) runs on, and what
fills the demo school for demos and screenshots.

**What exists.** The seeder (`seed_active_session`) builds one live session with a
roster, a plan, a few finished sets and recorded maxes; a local install runs it with
`docker compose run --rm seed`. The simulator (`simulate_node`) pretends to be a sensor:
it registers, sends a heartbeat every 5 seconds, and sends reps only while its rack has
a set running. Neither can be run on a remote school today.

**Why the seeder can't simply be run online as it is:**

1. It can make a well-known login: on a database with no users it creates `coach` /
   `coach`, which spec 01 forbids.
2. It ends every open session (only one may be open), which on a real school would end
   a real workout.
3. `--reset` deletes by name, and the names aren't unique to the demo: a real school
   very likely has a group called "Varsity", and could have an athlete called Jordan Lee.

**Decisions (Devin, 2026-10-17):**

- **Invented names, in both local and remote** (done: Alex Rivera, Jordan Lee, Casey
  Morgan, Riley Brooks; the local wristband tag moved to Jordan Lee).
- **The seeder only adds, and recognizes its own rows** instead of guessing by name:
  - its athletes are marked `is_simulated` (nothing in the app treats a simulated
    athlete differently, so they show and lift like anyone else);
  - its group and plan have names no real school would use ("Demo Squad", "Demo Strength
    Block");
  - its sensors are marked `is_simulated` too, and owned by a seeded athlete;
  - `--reset` deletes only those rows;
  - if a real (not simulated) athlete already has one of the seeded names, it refuses.
- **It never makes a login.** With no coach in the school it stops: "Claim this school
  first (setup code), then seed it." The plan belongs to the first administrator.
- **It never ends a session it didn't make.** Another session open → it stops: "A
  session is running. End it first." Its own earlier seeded session may be replaced.
- **One owned simulated sensor per seeded athlete** (`sim-alex-rivera`, …; the id is
  for people to read, the seeder finds them by the label), made by the seeder with
  `Node.owner` set (Phase 0). Like any owned sensor, it only ever attaches
  to its owner's rack. (The gym-style `rack_1` sensor stays for a local install.)
- **`is_simulated` is a label only** (Devin, 2026-10-17; done on this branch). It
  used to bar a simulated sensor from racks and hide simulated sets from the live room
  and from max updates, a "simulation mode" from before the redesign that nothing ever
  switched on. Now a simulated sensor is linked, used and counted exactly like a real
  one, and sets it records are still labelled simulated; the label only lets the seeder
  find and wipe its own rows. No change on a local install in practice: nothing there
  is marked simulated. (The whole-day "Simulation active" label on the coach's session
  strip is untouched; nothing turns it on either.)
- **No flag for demo schools.** Seeding only adds fake rows that a coach can archive in
  the app, and `eactl sim` only wakes sensors owned by seeded athletes, so a school that
  was never seeded has nothing to wake. `eactl seed` still asks you to type the
  school's short name.
- **The local `seed` step runs `ensure_demo_coach` first, then the seeder**, because the
  seeder no longer makes a login. One line in `docker-compose.yml`; the local result is
  the same as before.
- **The simulator responds; people drive** (option A). The sensors send reps while
  their athlete's set runs; a person opens the session link as that athlete and starts
  the set. Fake athletes that lift by themselves (signing in, starting and ending sets)
  are left for after the class.

**Commands (`eactl`, remote):**

- `eactl seed "School Name" [--reset]`: asks for the short name, then runs the seeder
  inside the school's django (only the seeder, never `ensure_demo_coach`).
- `eactl sim "School Name" [--hours 2] [--stop]`: wakes the seeded athletes' sensors.
  It runs the simulator as a one-off Kubernetes Job in the school, using the school's
  own django image, for all of those sensors at once.
  - **It stops itself after 2 hours, twice over:** the simulator gets a `--stop-after`
    setting and exits cleanly, and the Job has a hard limit (`activeDeadlineSeconds`)
    in case the simulator hangs. `--stop` ends it early.
  - **On stopping, its sensors are unregistered: unlinked from any rack and marked
    inactive.** Not deleted: each finished set remembers the sensor that measured it.
    The next `eactl sim` makes them active again.
  - A second `eactl sim` while one is running says so and starts nothing.
- Tab completion, `eactl help` and `scripts/remote/README.md` list both.

**Done when:**

- [ ] No real person's name is left in the seeder or its comments. *(done)*
- [ ] On a database with no users, the seeder writes nothing and creates no login.
- [ ] With a non-seeded session open, the seeder writes nothing and that session is
      still open; with only its own seeded session open, a re-run replaces it.
- [ ] `--reset` on a school that also has a real "Varsity" group and a real athlete
      leaves both untouched.
- [ ] With a real athlete named like a seeded one, the seeder refuses and writes nothing.
- [ ] Each seeded athlete owns exactly one sensor, marked `is_simulated`.
- [ ] *(done)* A simulated sensor can be linked to a rack and is usable; its sets count
      in the live room and feed max updates (`test_simulated_label.py`).
- [ ] The simulator runs several sensors at once; each sends reps only while its own
      athlete's set runs, on that athlete's rack.
- [ ] With `--stop-after`, the simulator exits by itself and its sensors are unlinked
      and inactive (a test with a short time); deleting the Job early does the same.
- [ ] A fresh local box: `docker compose run --rm seed` still ends with the demo coach
      and the seeded session.
- [ ] Full suite passes in both modes.

**Stop. Devin reviews.**

## Phase 6 — Rehearsal

By hand, hosted mode, two browsers, on the demo school after `eactl seed` and with
`eactl sim` running:

- [ ] A coach starts a session; two athletes in the group open the link and each land
      on their own rack; an athlete outside the group is turned away.
- [ ] Two seeded athletes join from two browsers, and each one's simulated sensor feeds
      only their own rack.
- [ ] Two simulators stand in for two sensors **on the same bar** (both publish every
      rep). Each athlete's set records only while it is running; neither rack records
      the other's set. *(This is the siblings case.)*
- [ ] One athlete closes the tab mid-set and reopens the link: same rack, same open
      set, no reps lost.
- [ ] The coach ends the session: both racks vanish from the room; the report shows
      both athletes' sets.
- [ ] The same build, switched to `local`, runs a normal gym session with a rack
      tablet and no logins.

---

## Acceptance criteria

- [ ] A coach sets up nothing per athlete during a remote session.
- [ ] An athlete gets into a session only if they belong in it.
- [ ] No two athletes ever share a rack; an athlete cannot touch another's rack or sensor.
- [ ] A reload or a dropped connection never strands a remote athlete.
- [ ] Remote sets land in the same tables and the same report as gym sets.
- [ ] A gym box is unchanged.

## Risks

| Risk | What reduces it |
|---|---|
| Two joins race for one rack number | A row lock in Phase 1, and the fifty-at-once test |
| A remote athlete is stranded as a read-only observer after a reload — the bug that already happened in the gym | Phase 2 ties the lease to the login on virtual racks; Phase 6 rehearses it |
| Virtual racks leak when a session is never ended | Release also runs when a stale session is ended late; rows carry `session`, so a cleanup command can find orphans |
| The rack screen is forked and the two copies drift | Phase 3 uses the one `RackScreen.jsx`, switched by a fact in the rack's state; a test renders it with and without an owner |
| Adding `owner_athlete` to rack state breaks the frozen rack contract | It is additive; Phase 3b checks the canon first and stops if it is not allowed |
| Demo data reaching a real school | The seeder only adds, recognizes its own rows, refuses on a name clash, never makes a login or ends another session; `eactl seed` asks for the short name |
| A simulator left running | It stops itself after 2 hours, and Kubernetes ends the Job at the same limit if it doesn't |

## Docs to update when done

`docs/remote/access.md` section 3, `docs/remote/sensors.md` (a sensor belongs to an
athlete), `docs/journal/rack-tablet.md` (my-rack mode), `docs/reference/message-contract.md`
if room state gains fields, the route table.
