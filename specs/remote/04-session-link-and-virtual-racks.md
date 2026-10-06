# Feature Spec 4: The session link and virtual racks

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started. **One decision open** (who may join; see below)
- Form items: Definition of Done #3 and #4
- Depends on: [02 Roles](02-roles.md), [05 Hosted mode](05-hosted-mode.md), [03 Login links](03-athlete-login-links.md)
- Mockup: `Main` (live remote room) on the Remote page of the canvas

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

### Open decision — who may join?

The agreed rule is **"the athlete must be in a training group assigned to the
session."** In the data, that is: one of the athlete's `training_groups` is the group
of a `TrainingProgram` that has a `SessionParticipation` on this session.

Spec 08 adds the **Quick Training Session**, where a coach picks athletes one by one
and may pick no workout at all. Such a session has a roster (`TrainingSession.athletes`)
but can have no program, and so no group.

**Recommendation: an athlete may join if they are on the session's roster, or in a
group taking part in it.** The roster is filled when a planned day is set up and when a
quick session is created, so this is the same rule for planned days and it does not
lock everyone out of a quick one. **Confirm before Phase 1.**

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
- The rack screen in "my rack" mode.
- The ownership half of spec 05's rules for rack endpoints.
- The coach's live room: virtual racks, sensor status, **Not joined yet**, **Copy
  session link**.
- Assigning a sensor to an athlete from the roster.

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
2. The membership rule (the open decision above). Failing it returns
   `403 not_in_session`.
3. Find this athlete's virtual rack for this session; if there is none, take the next
   free number from `VIRTUAL_RACK_BASE` and create the `RackRuntime` with
   `owner_athlete` and `session`. Take a row lock so two joins cannot pick one number.
4. Write a `RackCheckIn` for the athlete on that rack.
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
- Ending a session releases its virtual racks: detach sensors, end any open set the way
  `_end_open_sets_on_rack` already does, delete the `RackRuntime` rows. Hook it into the
  existing end-of-session path.

**Done when:**

- [ ] Athlete A calling any rack endpoint for athlete B's rack gets `403`.
- [ ] Athlete A cannot check athlete B in, or post a set for athlete B.
- [ ] An athlete who reloads mid-set regains control of their rack and their set is
      still open and unharmed.
- [ ] After the session ends: no virtual `RackRuntime` rows remain, the sensors have no
      rack, an open set was ended and kept, and the report includes the remote sets.
- [ ] A physical rack's lease, recovery and release behave exactly as before
      (the existing tests pass unchanged).

**Stop. Devin reviews.**

## Phase 3 — The rack screen in "my rack" mode

Route `/session/<id>` (the session link): if not signed in, go to `/athlete` and come
back. Then call `join` and render the existing rack screen with:

- no device setup, no "which rack" step, no sensor picker, no athlete picker — the
  athlete is fixed;
- the athlete's own plan for this session (the existing prescriptions and progress
  calls, now answering for the signed-in athlete);
- a **sensor line**: "Sensor connected" / "Sensor not connected — check it is on", from
  the sensor's heartbeat. Lifting is allowed either way;
- `403 not_in_session` → "You're not on this session. Ask your coach."; `409` → "Your
  coach hasn't started this session yet", retried every few seconds.

Reuse `RackScreen.jsx` and its durable rep buffer; do not fork it. The differences are
props.

**Done when:**

- [ ] *(Frontend test)* In my-rack mode the athlete picker, rack setup and sensor
      picker are not rendered.
- [ ] *(Browser)* Opening the session link signed out → sign in → rack screen, in one flow.
- [ ] *(Browser)* With the simulator standing in for the athlete's sensor, a set runs
      and saves, and the coach's live room shows the reps.
- [ ] *(Browser)* The gym rack screen (`/rack/...`) is unchanged.

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

## Phase 5 — Rehearsal

By hand, hosted mode, two browsers:

- [ ] A coach starts a session; two athletes in the group open the link and each land
      on their own rack; an athlete outside the group is turned away.
- [ ] Two simulators stand in for two sensors **on the same bar** (both publish every
      rep). Each athlete's set records only while it is running; neither rack records
      the other's set. *(This is the siblings case.)*
- [ ] One athlete closes the tab mid-set and reopens the link: same rack, same open
      set, no reps lost.
- [ ] The coach ends the session: both racks vanish from the room; the report shows
      both athletes' sets.
- [ ] The same build, switched to `gymbox`, runs a normal gym session with a rack
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
| A remote athlete is stranded as a read-only observer after a reload — the bug that already happened in the gym | Phase 2 ties the lease to the login on virtual racks; Phase 5 rehearses it |
| Virtual racks leak when a session is never ended | Release also runs when a stale session is ended late; rows carry `session`, so a cleanup command can find orphans |
| The rack screen is forked and the two copies drift | Phase 3 reuses `RackScreen.jsx` with props; a test renders both modes |

## Docs to update when done

`docs/remote/access.md` section 3, `docs/remote/sensors.md` (a sensor belongs to an
athlete), `docs/journal/rack-tablet.md` (my-rack mode), `docs/reference/message-contract.md`
if room state gains fields, the route table.
