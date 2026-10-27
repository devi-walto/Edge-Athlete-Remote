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
standing at a rack, or a TV showing the room, has no login, and online every rack
route and the room view need one. So the remote version only fits teams training
apart, and the screens a gym already knows can't be used online.

## User story

As a coach at a school on the remote version, I want a tablet at each shared rack and
the room on a TV, working like they do in a gym, without each athlete signing in on
their own phone.

## Decisions (Devin, 2026-10-26 and 2026-10-27)

- **A common login**, a new kind of login beside administrator, coach and athlete. Like
  the others, it is not stored as a role: the login's role comes from what it is
  attached to (`roles.py`). **One per school, shared by every tablet and TV** (a
  username and password the staff know). Each device signed in with it gets its own
  record, so a coach can see them and the racks they made.
- **It can be a rack or the room display.** After signing in, the device shows the
  role picker, offering **Rack Tablet** and **Base Station Display** (not Coach Admin).
  The device remembers its pick, as a gym tablet does today. There is no rack setup
  screen online: the login says it's a gym device, and the picker says which kind.
- **The rack screen is the gym's rack screen**: check-in list, next lifter, the same
  flow. Not the athlete's own-rack view. **The display is the gym's room display.**
- **A rack makes itself and is named at the rack.** A coach no longer links a tablet to
  a numbered slot. A tablet that replaces a dead one just makes a new rack: where an
  athlete is comes from their newest check-in, and the "at this rack" lists update on
  their own, so nothing is lost.
  - **It names itself** with the next free name ("Rack 3"), without asking. It can be
    renamed from the tablet or from the coach's Room Layout (Devin, 2026-10-27).
  - Behind the scenes the rack keeps an automatic number, because rack numbers run
    through the rack tables, the sensor records, the room view, `/rack/<n>` and the
    live-update topics.
  - **Two racks may share a name.** When they do, the coach's screens show each one's
    number after it, small and in brackets ("Platform A (12)"), so they can be told
    apart. A rack whose name is its own shows no number.
- **School sensors.** A sensor can be claimed for the school instead of for an athlete
  (same one-time code as spec 14). School sensors are offered on rack tablets as a list,
  by the name a coach gives them (also written on a sticker on the sensor).
- **Pairing confirms itself with one rep.** The tablet picks a sensor from the list, a
  **60-second countdown** appears ("Do one rep with the bar"), with a **Cancel** button to stop
  it any time (Devin, 2026-10-27: 60 s, not 20, because it can be cancelled), and the link is saved
  only when that sensor reports a rep before it ends. No rep, no link: if it can't count
  a rep, it isn't worth linking. There is no "link anyway".
- **Sensors already on a working rack are not offered.**
- **Everything can be set up from the coach's Room Layout as well as at the rack**
  (Devin, 2026-10-27), so a coach can set up a whole room from one screen instead of
  walking to each tablet. Only signing a tablet in has to happen on the tablet. From
  Room Layout a coach can rename a rack or a sensor, link a sensor to a rack, and clear
  or remove a rack. **Linking from Room Layout still needs someone at the bar**: the same
  60-second countdown shows on the coach's screen and on that rack's tablet, and the link
  is saved on a rep from that sensor. That walk is necessary friction.
- **A rack is cleared or removed, never "released"** (Devin, 2026-10-27). With no slots,
  today's force-release splits in two. **Clear**: the tablet is still there but stuck;
  the rack keeps its name, tablet and sensor, and is ready for the next lifter.
  **Remove**: the tablet is gone; the rack leaves the list and its sensor is freed to
  link elsewhere. Both end a set in progress as a false set (its reps were on the
  tablet), and the confirm says so. Athletes' sets and check-ins are kept either way.
  **Clear all racks** stays for the end of a session.
- **No separate "Identify" button** (Devin, 2026-10-27). The one time a coach needs to
  spot a tablet across the room is while pairing it, so the tablet's pairing countdown
  shows its rack's name big, outlined in lime. Every other time, the rack's name is in
  the tablet's header.
- **A dead tablet's sensor can be taken only when nothing is in progress on it**: its
  tablet has been silent longer than the controller lease (20 seconds) **and its rack
  has no set open**. Another rack tablet sees it in the list as "Rack 3, tablet offline"
  and takes it with the usual one-rep pairing. While a set is open the sensor stays
  put until the tablet comes back and finishes the set with the reps it kept, or a coach
  force-clears the rack, as today. (Why: see "Reps kept on the tablet" below.)
- **The risk of a shared password is accepted.** Anyone who knows it can read the
  roster and the room, take an idle sensor, and check athletes in and log sets for them
  while a session is running, from anywhere. If it is misused, a coach resets the common
  login the same way as any other account (a fresh login link to set a new password);
  every device is then signed out and signs in again with the new one. The sign-in's
  wrong-password limit applies to it as to any login.
- **Local works the same way later**, after the class: same naming and pairing in a
  gym, minus the login, which a gym doesn't need. The local flow works today and is what
  a gym demo uses.

## Reps kept on the tablet

How buffering works today, and why a dead tablet's sensor waits for an open set:

- During a set, each rep the sensor sends reaches the tablet over live updates and is
  written to the tablet's own storage first (`db/repBuffer.js`). At the end of the set
  the tablet sends them all in one go, and clears its copy **only after the server has
  them**. A failed send keeps them to retry.
- **The server has none of a set's reps until that send.** If a rack is taken over
  while its set is open, the set is ended as a false set with no reps
  (`end_open_sets_on_rack`), and the reps stay stranded on the old tablet.
- **A tablet that drops off the network and comes back is fine today**: its tab still
  holds its controller token, so it takes its rack back with the set still open and
  finishes it. Nothing in this spec changes that, as long as nobody takes the sensor
  meanwhile, which the rule above guarantees.
- Reps the sensor sends while the tablet can't hear them are lost either way: the
  sensor doesn't keep them. That's unchanged.

## What happens to the rack routes

The rack keeps its number (automatic now), so **every route addressed by rack number
stays as it is**; only who may use it online changes.

| Route | Online, with this spec | Local |
|---|---|---|
| `/rack/<n>` (the rack screen) | Same, `n` the rack's automatic number | Same |
| `/rack/setup` (wait for a coach to assign a number) | Not used: picking Rack Tablet makes and names the rack, then goes to `/rack/<n>` | Same for now. After the class it becomes "name this rack, pair a sensor" instead of waiting |
| `/api/racks/<n>/…` (state, the controller lease, check-in, check-ins, sensor health) and `set_create` / `set_complete` | Same routes, now also allowed for the common login on its own device's racks (Phase 1) | Unchanged |
| `/api/racks/register/`, `/api/racks/racknumber/`, `/api/racks/<n>/nfc-tap/` | Still refused | Unchanged |
| `/api/racks/unassigned/`, `PATCH /api/racks/<device_id>/` (give a tablet its number), `/api/racks/node-assignment/` (link a sensor) | Not used for shared racks: the tablet names its rack and pairs its own sensor | Unchanged for now; no longer needed once local moves over after the class |
| `DELETE /api/racks/<n>/` (force-clear), `DELETE /api/racks/<n>/node/` (take a sensor off), `/api/racks/release-all/` | Same, coaches only | Unchanged |
| Virtual racks (an online athlete's own rack, spec 04) | Unchanged | — |

**New routes:** make a rack and rename it (Phase 2); list the school's sensors, link one
to a rack, take an idle one from a dead tablet's rack (Phase 3); a coach's list of
devices and signing one out (Phase 0).

## What exists today

- **Roles** (`roles.py`): a login attached to a coach profile is an administrator or a
  coach, one attached to an athlete record is an athlete, anything else is refused.
- **The role picker** (`App.jsx`, `Picker`): Rack Tablet, Base Station Display, Coach
  Admin; the pick is kept in the browser (`device_role`).
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
- **Sign-in**: an 8-hour access token and a 7-day refresh, rotated, so a device in
  regular use stays signed in; one left unused for a week signs in again. A refresh is
  refused for a login that has been switched off or lost its role
  (`CheckedTokenRefreshView`), **not** for one whose password changed.

## Non-goals

- Changing the gym (local) flow. After the class.
- The server checking a pairing rep for itself. The tablet's word is trusted, as it
  already is for which sensor it picked.
- NFC check-in online. The check-in list does the job.
- Several sessions at once (spec 17).

---

## Phase 0 — The common login

- The model the common login is attached to (one per school), and one record per device
  signed in with it.
- `role_of()` answers **common** for it. A login attached to it and to anything else is
  refused, like the existing two-attachment case.
- Any coach sets it up and resets it the way they do an athlete's login: a login link
  to set the password (spec 03). A coach can also sign out one device.
- **A new password signs out every device signed in with the old one, for every kind of
  login** (Devin, 2026-10-27), not just the common one. Passwords are set in three places
  today (a coach's own change in `coach_auth.py`, a coach's reset in `coach_accounts.py`,
  a login link in `services/login_links.py`), and they all go through **one shared
  function** that sets the password and records when. A renewal of a sign-in made
  before that moment is refused (`CheckedTokenRefreshView`). The device that made the
  change is handed a fresh sign-in, so the person changing it stays signed in.
- Every coach route refuses the common login.

**Done when:**

- [ ] The common login's role is common; a half-made or switched-off one gets nothing.
- [ ] After a password change, no device signed in before it can renew, for a coach,
      an athlete and the common login alike; the device that changed it stays signed in.
- [ ] After signing out one device, the others still can renew.
- [ ] *(Unit test)* The route walk gains a common column: every route that isn't opened
      to it in Phase 1 refuses it.
- [ ] Full suite passes in both modes.

## Phase 1 — What the common login may do online

- The rack routes allow it **for racks its own device made**, and no other rack.
- `athletes_view` (the check-in list's roster), `prescriptions_view` and
  `athlete_progress` allow it, the last two only for athletes checked in at its rack.
- `room_state` (the room display) allows it.
- Registering a rack, asking its number and the NFC tap stay refused: online a rack is
  made by picking Rack Tablet (Phase 2).

**Done when:**

- [ ] *(Unit test)* The route walk: each route lets the common login through exactly as
      listed, and refuses it on another device's rack.
- [ ] Local is unchanged: the walk's local pass still finds every route open.
- [ ] Full suite passes in both modes.

## Phase 2 — Racks that make and name themselves

- A device signed in with the common login that picks Rack Tablet, with no rack yet,
  makes one: the next free number, and the name given at the rack. The name can be
  changed from the tablet.
- A rack whose tablet has gone silent, and that has no sensor and nobody checked in,
  drops out of the room view and the coach's list.
- The rack's name appears wherever its number does today (rack screen, room view, the
  daily report's rack list). On the coach's screens, a name two racks share is followed
  by each rack's number in small brackets.

**Done when:**

- [ ] A new tablet's first pick makes a rack with the name given; a second tablet makes
      a second rack.
- [ ] Renaming changes the name everywhere and nothing else.
- [ ] Two racks with one name both show their number in brackets on the coach's
      screens; a rack with a name of its own shows none.
- [ ] A dead tablet's empty rack leaves the room view; its athletes' check-ins and sets
      are untouched.
- [ ] Full suite passes in both modes.

## Phase 3 — School sensors and pairing

- A coach makes a claim code for the school (no athlete) and names the sensor.
  `SensorClaimCode.athlete` becomes optional; a school sensor has no owner.
- The list a rack tablet sees: the school's sensors, by name, with battery and last
  seen; not those on a rack whose tablet is live; a dead tablet's shown as free to take
  only when its rack has no open set.
- Linking a sensor to the tablet's rack, and taking an idle one from a dead tablet's
  rack. Taking one whose rack has a set open is refused.
- **Pairing on the rack screen:** pick a sensor, a 60-second countdown, with Cancel, appears ("Do one
  rep with the bar"), the screen listens to that sensor's reps, and the link is saved on
  the first rep. When the countdown ends with no rep: "No rep from Bar 3. Is it switched
  on and on this bar?", and nothing is linked.
- The simulator answers a pairing: a simulated sensor sends one rep when a rack is
  pairing it, so demos and browser checks work without hardware.

**Done when:**

- [ ] A school code claims a sensor with no owner; an athlete's code still claims it
      for that athlete.
- [ ] The list leaves out sensors on live racks and marks a dead tablet's as free only
      when its rack has no open set.
- [ ] Taking an idle sensor from a dead tablet's rack moves it; one with a set open, or
      on a live tablet's rack, is refused and nothing changes.
- [ ] A tablet that was offline mid-set comes back, takes its rack back and sends its
      kept reps; the set is saved with all of them.
- [ ] *(Unit test)* Pairing saves the link on a rep from the chosen sensor; a rep from
      another sensor does nothing; no rep within 60 seconds saves nothing; Cancel stops it and saves nothing.
- [ ] *(Browser)* Pairing a simulated sensor on a rack tablet, start to finish.
- [ ] Full suite passes in both modes.

## Phase 4 — The screens

**Approved 2026-10-27, on the Final designs page** (row "the coach's Room Layout for
shared racks"): `F_RoomLayout_Local` and `F_RoomLayout_Remote` (the one screen that
differs: remote adds the common login strip and a Sign out tablet button on each rack
card), and, the same in both, `F_LinkSensor_Pick`, `F_LinkSensor_Countdown`,
`F_Rack_Pairing`, `F_ClearRack`, `F_RemoveRack`. Room Layout's rack screens show six at a
time (swipe, or arrows on a laptop, for more); the school sensors list shows six rows and
scrolls. Still without a board: the common sign-in on a device, the two-choice
role picker, and the rack tablet's own sensor list. They go on a proposal page first
and are built after Devin approves them (rule in `specs/README.md`). The rack screen and
the room display themselves are the existing ones.

**Done when:**

- [ ] Each screen matches its approved board.
- [ ] *(Browser)* A fresh tablet: sign in, pick Rack Tablet, name the rack, pair a
      sensor, check an athlete in, finish a set.
- [ ] *(Browser)* A fresh TV: sign in, pick Base Station Display, see the room live.
- [ ] *(Browser)* A coach signs one device out; the others keep working.

## Phase 5 — Rehearsal and docs

- *(By hand)* Two tablets on a remote school, one sensor each: take one tablet offline
  mid-set and bring it back (the set keeps its reps); then kill it between sets and take
  its sensor from the other tablet.
- What the common login is, and how pairing works, in `docs/remote/access.md` and the
  journal.
- Merge into `SprintBranch` through the spec's pull request.
