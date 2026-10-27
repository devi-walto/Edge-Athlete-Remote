# Feature Spec 18: Shared racks online

- Owner: Devin Walton
- Date: 2026-10-27
- Status: **Written, not started. When to build it is not decided:** in the class only
  if the sensor firmware (spec 14, Phase 5) is finished first, otherwise after
  November 11. Not part of the Definition of Done.
- Depends on: [02 Roles](02-roles.md) (a login's role comes from what it is attached
  to), [05 Hosted mode](05-hosted-mode.md) (the online rule on every rack route),
  [04 Session link and virtual racks](04-session-link-and-virtual-racks.md) (racks that
  make themselves), [14 Sensors online](14-sensors-online.md) (sensors claim themselves
  with a one-time code)

## Why

Online, every athlete lifts on their own phone with their own sensor (spec 04). A
school whose athletes lift together on shared racks can't do that today: a tablet
standing at a rack has no login, and online every rack route needs one. So the remote
version only fits teams training apart, and the rack screen a gym already knows can't
be used online.

## User story

As a coach at a school on the remote version, I want a tablet at each shared rack,
working like the gym rack screen, without each athlete signing in on their own phone.

## Decisions (Devin, 2026-10-26 and 2026-10-27)

- **A new kind of login for rack tablets**, beside administrator, coach and athlete.
  Like the others, it is not stored as a role: the login's role comes from what it is
  attached to (`roles.py`). A login attached to a rack account is a **rack**.
- **No setup mode online.** A gym tablet has a setup screen because it has no login,
  so the device itself has to remember whether it is a rack, a coach tablet or the wall.
  Online the login says it: a tablet signed in as a rack is a rack.
- **The rack screen is the gym's rack screen**: check-in list, next lifter, the same
  flow. Not the athlete's own-rack view.
- **A rack makes itself and names itself.** A coach no longer links a tablet to a
  numbered slot. A tablet that replaces a dead one just makes a new rack: where an
  athlete is comes from their newest check-in, and the "at this rack" lists update on
  their own, so nothing is lost.
- **School sensors.** A sensor can be claimed for the school instead of for an athlete
  (same one-time code as spec 14). School sensors are offered on rack tablets as a list,
  by the name a coach gives them (also written on a sticker on the sensor).
- **Pairing confirms itself with one rep.** The tablet picks a sensor from the list, a
  countdown appears ("Do one rep with the bar"), and the link is saved only when that
  sensor reports a rep before the countdown ends. No rep, no link: if it can't count a
  rep, it isn't worth linking. There is no "link anyway".
- **Sensors already on a working rack are not offered.**

## Proposed, waiting for Devin

Recommendations, not decisions. Each is settled before the phase that needs it.

1. **One shared rack login per school, with a record for each tablet** (recommended),
   or one login per rack. Shared is simpler for coaches; the record per tablet means a
   lost tablet can be signed out on its own without signing out every rack.
2. **A name on top of an automatic number** (recommended), rather than replacing rack
   numbers. Rack numbers run through the rack tables, the sensor records, the room
   view, `/rack/<n>` and the live-update topics. Keeping a number behind the scenes,
   picked the way virtual racks get theirs, gives racks names without rewriting that.
   Whether two racks may share a name is open.
3. **A dead tablet's sensor becomes free to take.** Once its rack's tablet has been
   silent longer than the controller lease (20 seconds), another rack tablet sees the
   sensor in its list as "Platform A, tablet offline 3 min" and can take it after a
   confirm and the usual one-rep pairing. A set left open on it is **ended with the reps
   it had and kept**, as when a session's virtual racks are released. A live tablet's
   sensor can't be taken. A coach can still force-clear a rack, as today.
4. **How a tablet signs in and stays signed in.** A sign-in lasts 8 hours and renews for
   7 days, so a tablet left alone over a break would be signed out. Suggested: a coach
   makes a **rack link** (the login-link machinery of spec 03) and opens it on the
   tablet; the tablet's record keeps it signed in until a coach signs it out.
5. **The countdown's length.** Suggested 30 seconds.
6. **The wall display.** It isn't a rack. Either a small read-only login of its own, or
   a rack login may also read the room view. Room view online is coaches only today.
7. **Local works the same way later.** Same flow in a gym (the tablet names its rack
   and pairs a sensor with one rep), minus the login, which a gym doesn't need. After the
   class: the local flow works today and is what a gym demo uses.

## What exists today

- **Roles** (`roles.py`): a login attached to a coach profile is an administrator or a
  coach, one attached to an athlete record is an athlete, anything else is refused.
- **Every route has an online rule** (`permissions.py`, `open_on_local`). The rack routes
  (`rack_state`, `rack_checkin`, `rack_checkins`, the controller lease routes,
  `set_create`, `set_complete`, `rack_sensor_health`) allow a coach or the rack's own
  athlete online; `prescriptions_view` and `athlete_progress` a coach or that same
  athlete; `athletes_view`, `room_state` and `nodes_list` coaches only. Registering a
  rack, asking its number and the NFC tap are refused online (`ONLINE_REFUSE`).
  `test_open_on_local.py` walks all of them for every role.
- **Racks**: `RackScreen` (a tablet, `device_id` made in the browser), `RackRuntime` (the
  live state, keyed by `rack_number`), a 20-second controller lease (`CONTROLLER_LEASE`),
  and `recovery_required` when a rack is taken over with a set open. Virtual racks are
  numbered from `VIRTUAL_RACK_BASE` (10 000) up; gym racks keep small numbers.
- **A set doesn't record its rack** (dropped in the merge, canon D11). Where an athlete
  is comes from their newest `RackCheckIn`; the daily report lists the racks each athlete
  used.
- **Sensors**: `Node.owner` is the athlete for an athlete's own sensor, empty for a gym
  sensor, which a coach links to a rack by `Node.rack_number`. Unlinking is refused
  while a set is open on the sensor. `SensorClaimCode.athlete` is required today.
- **Reps reach the screen directly**: a sensor sends each rep on
  `edgeathlete/node/<its id>/rep` (online it may send only under its own id), browsers
  may read every `edgeathlete/` topic, and the rack screen already listens to one
  sensor's reps (`react/src/mqtt/client.js`). The simulator (`simulate_node`) sends reps
  only during a set.
- **Sign-in**: an 8-hour access token and a 7-day refresh, rotated; a refresh is refused
  for a login that has been switched off (`CheckedTokenRefreshView`).

## Non-goals

- Changing the gym (local) flow. Proposed item 7, after the class.
- The server checking a pairing rep for itself. The tablet's word is trusted, as it
  already is for which sensor it picked.
- NFC check-in online. The check-in list does the job.
- Several sessions at once (spec 17).

---

## Phase 0 — The rack login

Settles proposed items 1 and 4 first.

- The model a rack login is attached to, with one record per tablet signed in to it.
- `role_of()` answers **rack** for it. A login attached to a rack account and anything
  else is refused, like the existing two-attachment case.
- Signing a tablet in, and a coach signing one tablet out (its renewals refused from
  then on).
- Every coach route refuses a rack login.

**Done when:**

- [ ] A rack login's role is rack; a half-made or switched-off one gets nothing.
- [ ] A signed-out tablet can't renew its sign-in; the school's other tablets can.
- [ ] *(Unit test)* The route walk gains a rack column: every route that isn't opened
      to racks in Phase 1 refuses a rack login.
- [ ] Full suite passes in both modes.

## Phase 1 — What a rack login may do online

- The rack routes allow a rack login **for racks it made**, and no other rack.
- `athletes_view` (the check-in list's roster), `prescriptions_view` and
  `athlete_progress` allow a rack login, the last two only for athletes checked in at
  its rack.
- Registering a rack, asking its number and the NFC tap stay refused: online a rack is
  made by signing in (Phase 2).
- The wall display, if proposed item 6 is settled by then.

**Done when:**

- [ ] *(Unit test)* The route walk: each route lets a rack login through exactly as
      listed, and refuses it on another tablet's rack.
- [ ] Local is unchanged: the walk's local pass still finds every route open.
- [ ] Full suite passes in both modes.

## Phase 2 — Racks that make and name themselves

Settles proposed item 2 first.

- A signed-in rack tablet with no rack makes one: the next free number, and a name the
  tablet gives it. The name can be changed from the tablet.
- A rack whose tablet has gone silent, and that has no sensor and nobody checked in,
  drops out of the room view and the coach's list.
- The rack's name appears wherever its number does today (rack screen, room view, the
  daily report's rack list).

**Done when:**

- [ ] A new tablet's first sign-in makes a rack with the name given; a second tablet
      makes a second rack.
- [ ] Renaming changes the name everywhere and nothing else.
- [ ] A dead tablet's empty rack leaves the room view; its athletes' check-ins and sets
      are untouched.
- [ ] Full suite passes in both modes.

## Phase 3 — School sensors and pairing

Settles proposed items 3 and 5 first.

- A coach makes a claim code for the school (no athlete) and names the sensor.
  `SensorClaimCode.athlete` becomes optional; a school sensor has no owner.
- The list a rack tablet sees: the school's sensors, by name, with battery and last
  seen; not those on a rack whose tablet is live; a dead tablet's shown as free to take
  (item 3).
- Linking a sensor to the tablet's rack, and taking one from a dead tablet's rack: its
  open set is ended with the reps it had and kept, then the sensor moves.
- **Pairing on the rack screen:** pick a sensor, a countdown appears ("Do one rep with
  the bar"), the screen listens to that sensor's reps, and the link is saved on the first
  rep. When the countdown ends with no rep: "No rep from Bar 3. Is it switched on and
  on this bar?", and nothing is linked.
- The simulator answers a pairing: a simulated sensor sends one rep when a rack is
  pairing it, so demos and browser checks work without hardware.

**Done when:**

- [ ] A school code claims a sensor with no owner; an athlete's code still claims it
      for that athlete.
- [ ] The list leaves out sensors on live racks and marks a dead tablet's as free.
- [ ] Taking a dead tablet's sensor ends its open set, keeps it with its reps, and
      moves the sensor; a live tablet's sensor is refused.
- [ ] *(Unit test)* Pairing saves the link on a rep from the chosen sensor; a rep from
      another sensor does nothing; no rep before the countdown ends saves nothing.
- [ ] *(Browser)* Pairing a simulated sensor on a rack tablet, start to finish.
- [ ] Full suite passes in both modes.

## Phase 4 — The screens

No Final design boards exist yet for: signing a tablet in as a rack, naming the rack,
the sensor list, the pairing countdown, and signing a tablet out (coach side). They go
on a proposal page first and are built after Devin approves them (rule in
`specs/README.md`). The rack screen itself is the existing one.

**Done when:**

- [ ] Each screen matches its approved board.
- [ ] *(Browser)* A fresh tablet: sign in, name the rack, pair a sensor, check an
      athlete in, finish a set.
- [ ] *(Browser)* A coach signs one tablet out; the others keep working.

## Phase 5 — Rehearsal and docs

- *(By hand)* Two tablets on a remote school, one sensor each; unplug one mid-set and
  take its sensor from the other.
- What a rack login is, and how pairing works, in `docs/remote/access.md` and the
  journal.
- Merge into `SprintBranch` through the spec's pull request.
