# Feature Spec 18: Shared racks online

- Owner: Devin Walton
- Date: 2026-10-27
- Status: **Picked up 2026-11-12 on `feature-rack_setup`, before spec 19's Phase 1**
  (Devin: it changes how racks are made, and spec 19 would need rewriting after it).
  Gained Phase 5, the local install moving to the same flow. Phase 0 of spec 19 (the
  no-session rack, `F_Rack_NoSession`, approved here) is already built on this branch.
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
  record, so a coach can see them and the racks they made. **An administrator makes it
  and changes its password directly, typing both; no login link** (Devin, 2026-11-12): a
  link lets an athlete choose a password their coach never sees, but this one is a staff
  password someone has to type into every tablet anyway.
- **The flow on a tablet (Devin, 2026-10-27), kept as simple as the rack screen is:**
  1. **The normal sign-in screen, unchanged** (the athlete's, `F_Ath_R2`). Only where it
     lands afterwards differs.
  2. **Set up this rack:** the rack's name, filled in with the next free one ("Rack 3")
     and editable, and the school's sensors to pick from; picking one starts the
     60-second check. "No sensor for now" skips it (the rack then shows Needs a sensor
     in Room Layout). This step is also where the tablet waits while a coach sets it
     up from Room Layout: it simply stays here, and when either side starts the check
     the same countdown (`F_Rack_Pairing`) appears; no separate waiting screen. This is
     not the old `/rack/setup` (waiting for a coach to assign a slot number), which
     isn't used online. Shown only when the device has no rack yet;
     signing in again on a set-up tablet goes straight to step 3.
  3. **The idle rack screen**, exactly as a rack works on remote.
- **No role picker.** The idle rack screen gains one small button in its bottom-right
  corner, above the footer (which stays word for word), showing the room display's mark
  (the rising bars): it switches the tablet to the room display. On the room display the
  same corner shows the rack's mark (the barbell) to switch back. **Either way it asks
  first** (Devin, 2026-10-27): "Switch Rack 3 to the room display?" / "Switch back to
  Rack 3?", with Cancel and Switch, so a stray tap can't take a rack away. The tablet
  remembers which it was showing. A tablet used only as a TV just stays on the display.
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
  while a session is running, from anywhere. If it is misused, an administrator types a
  new password; every device is then signed out and signs in again with the new one. The sign-in's
  wrong-password limit applies to it as to any login.
- **Local works the same way later**, after the class: same naming and pairing in a
  gym, minus the login, which a gym doesn't need. The local flow works today and is what
  a gym demo uses.

### Added 2026-11-12

- **The local install moves to the same flow** (Devin, 2026-11-12), in this spec, not
  later: a rack claims its own number and name, and pairs its own sensor; nobody assigns
  a tablet to a slot. Phase 5.
- **No rack slots for particular workouts** (proposed, Devin to confirm). The numbered
  slot was partly meant for racks set up for certain work. That fact belongs to the
  equipment, not to the tablet: the sensor on the bar, platform or mat is what the rack
  can measure, and it already carries it (`Node.mount_type`, and the merge canon's
  `Node.allowed_exercises`, D9, a filter that fails open and never blocks a set). Since a
  rack's sensor is paired to it, a rack still "is" the jump rack because its sensor is the
  jump mat, wherever the tablet came from. Later, a movement says which kind of sensor it
  needs, and the rack screen asks for it (or hides that movement) when its sensor can't
  measure it. Nothing in this spec needs it; no slot design is kept for it.

**How a sensor sets itself up** (read from the firmware, `esp32/edge_athlete_node`,
2026-11-12), which this spec builds on:

- **Its ID is its own:** `ea-` plus the end of its Wi-Fi chip's address (`ea-3f9c1a`).
  Nobody gives it one, and it never changes.
- **Setup on a phone:** hold the button 3 s; the sensor opens its own Wi-Fi
  (`EdgeAthlete-…`) and page. Pick a network and its password; then **remote**: the
  school code, and a sensor code (spec 14's claim), which gets it its own login; or
  **local**: no code at all, the base station is whatever gave this Wi-Fi its addresses.
  Up to 4 networks are kept; it restarts and connects.
- **Then it talks over MQTT:** a pulse every 5 s on `edgeathlete/node/<id>/pulse`, and each
  rep on `…/rep`. Remote, it may send only under its own ID.
- **The gap on a local install:** the firmware never tells the base station it exists,
  and the server ignores a pulse from a sensor it has no row for ("node is not
  registered", `process_pulse.py`). `POST /api/nodes/register/` exists for it, but nothing
  calls it (only the simulator makes its own row). Today a real sensor on a local install
  is invisible until a row is made by hand. Phase 5 closes this on the server, so no
  sensor needs reflashing.

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
| `/rack/setup` (wait for a coach to assign a number) | Not used: signing in leads to "Set up this rack", which makes and names the rack, then goes to `/rack/<n>` | Becomes "Set up this rack" too (Phase 5), with no sign-in before it |
| `/api/racks/<n>/…` (state, the controller lease, check-in, check-ins, sensor health) and `set_create` / `set_complete` | Same routes, now also allowed for the common login on its own device's racks (Phase 1) | Unchanged |
| `/api/racks/register/`, `/api/racks/racknumber/`, `/api/racks/<n>/nfc-tap/` | Still refused | Unchanged |
| `/api/racks/unassigned/`, `PATCH /api/racks/<device_id>/` (give a tablet its number), `/api/racks/node-assignment/` (link a sensor) | Not used for shared racks: the tablet names its rack and pairs its own sensor | Retired in Phase 5, once nothing calls them |
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

- Rack slots kept for particular workouts (see "Added 2026-11-12": that belongs to the
  sensor, later).
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
- **An administrator sets it up and changes its password directly** (Devin, 2026-11-12):
  a username and a password typed in, no login link. The same rules as any password here
  (length, not a common one).
- **Where it lives: a card two racks tall on the left of Rack screens' first page**
  (Devin, 2026-11-12), so the first page shows it and four racks; the pages after show six
  racks. It shows the username, the password hidden behind **Show**, and the tablets and
  TVs signed in with it, in a list that scrolls inside the card, each with **Sign out**.
  Every coach sees all of that (a coach is the one who signs a tablet in). Administrators
  also get **Change password**, or **Set up the common login** when there is none: each
  opens a **dialog over the page** (like Clear a rack), not a form in the card. A plain
  coach with none set up reads "ask an administrator". This replaces the strip
  `F_RoomLayout_Remote` drew above the racks; the TV's row from that strip is in the card's
  list. Boards on the canvas's Proposed page: `F_CommonLogin_CoachView`,
  `F_CommonLogin_Admin`, `F_CommonLogin_Change`, `F_CommonLogin_Setup` (proposed
  2026-11-12, v4); once approved they go to Final designs and `F_RoomLayout_Remote` is
  redrawn with the card.
- **Show needs the password kept readable** (a normal password is stored scrambled one
  way, and can't be shown again). This one is also kept encrypted with the server's key,
  read only by a coach's request to show it, never in any list, and replaced on every
  change. Acceptable for this login alone: it is a staff password meant to be shared (the
  risk is accepted below), and anyone who could read the server's key could already do
  far more.
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
- [ ] An administrator makes the common login and changes its password; a plain coach
      gets 403 for both but can show the password and sign out one device; an athlete or
      the common login itself can't show it; there is never a second one.
- [ ] The password is never in a list or any other answer than Show's, and Show gives the
      new one right after a change.
- [ ] *(Unit test)* The route walk gains a common column: every route that isn't opened
      to it in Phase 1 refuses it.
- [ ] Full suite passes in both modes.

## Phase 1 — What the common login may do online

- The rack routes allow it **for racks its own device made**, and no other rack.
- `athletes_view` (the check-in list's roster), `prescriptions_view` and
  `athlete_progress` allow it, the last two only for athletes checked in at its rack.
- `room_state` (the room display) allows it.
- Registering a rack, asking its number and the NFC tap stay refused: online a rack is
  made by signing in with the common login (Phase 2).

**Done when:**

- [ ] *(Unit test)* The route walk: each route lets the common login through exactly as
      listed, and refuses it on another device's rack.
- [ ] Local is unchanged: the walk's local pass still finds every route open.
- [ ] Full suite passes in both modes.

## Phase 2 — Racks that make and name themselves

- A device signed in with the common login, with no rack yet, makes one when it
  finishes "Set up this rack": the next free number, and the name shown there (the
  suggested one unless changed). The name can be changed later from the tablet or Room
  Layout.
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
scrolls.

**Also approved 2026-10-27, on Final designs:** `F_Rack_Setup` ("Set up this rack", in
the Room Layout row, just before `F_Rack_Pairing`); the corner switch, added to
`F_Rack_L1` with its confirm `F_Rack_SwitchToDisplay` beside it; and `F_Display` with its
confirm `F_Display_SwitchToRack` at the end of the gym rack row (the room display in its
current landscape layout, in the solid colours; only the corner button is new). The
sign-in screen needs no new board. The rack screen itself is unchanged; online its
check-in prompt drops the NFC line.

**Also approved 2026-10-27, on Final designs, for local and remote:** `F_Rack_NoSession`,
the first board in the gym rack row (BOTH 0). A rack with no session running shows "No
session yet" in the header and, in place of the empty check-in list, "Rack 3 is ready ·
Waiting for today's session" with "A coach starts it from the coach app. This screen
updates on its own, then shows who can check in." and a small chip saying the sensor is
live. The NFC prompt is hidden in this state only, since nobody can check in yet; the
corner switch stays. It needs nothing from the common login, so it can ship on its own
before the rest of this spec (the tablet already picks up a new session on its own,
PR #14).

**Done when:**

- [ ] Each screen matches its approved board.
- [ ] *(Browser)* A fresh tablet: sign in, keep or change the suggested name, pair a
      sensor, check an athlete in, finish a set.
- [ ] *(Browser)* With no session running, a rack shows the waiting message (local and
      remote); when a coach starts one, the check-in list replaces it within 5 seconds
      with no reload.
- [ ] *(Browser)* The corner button asks first, then flips the tablet to the room display
      and back; Cancel changes nothing; a reload keeps whichever it was showing.
- [ ] *(Browser)* While a tablet is on "Set up this rack", a coach starting the check
      from Room Layout brings up the countdown on that tablet.
- [ ] *(Browser)* A coach signs one device out; the others keep working.

## Phase 4b — Demo data on the common login

So a demo or a rehearsal has a shared rack without hardware (Devin, 2026-10-27). Today's
seeder and simulator (spec 04 Phase 5: `seed_active_session` / `eactl seed`,
`simulate_node --seeded` / `eactl sim`) make online athletes with their own sensors;
they gain a shared rack.

- **The seeder** also makes, on a remote server: one rack, made the way a tablet makes
  it (the next free number, named "Demo rack"), and one **school sensor** (no owner,
  simulated, named "Demo bar") linked to it. Like everything it makes, both are
  labelled demo, so they're easy to find and wipe, and it refuses if a real rack or
  sensor already has those names.
- **The common login is not made by the seeder.** Spec 04 Phase 5's rule stands: the
  seeder never makes a login, because a demo password on a real school's server is an
  open door. If the school has no common login yet, the seeder says so and points to
  the coach's setup link. (Proposed; Devin to confirm.)
- **The simulator** drives the demo bar like any simulated sensor: reps during a set,
  and the one rep that answers a pairing (Phase 3).

**Done when:**

- [ ] After `eactl seed`, Room Layout shows "Demo rack" with "Demo bar" on it, and the
      school sensors list shows Demo bar.
- [ ] A tablet signed in with the common login that picks Demo rack lifts a full set
      with `eactl sim` running, and the set is saved with its reps.
- [ ] Seeding twice changes nothing; wiping the demo data removes both.
- [ ] The seeder still makes no login of any kind (test).

## Phase 5 — The local install moves over (added 2026-11-12)

The same racks, sensors and screens as Phases 2 to 4, on a gym's base station, minus the
login a gym doesn't need. Boards: the same as Phase 4 (`F_Rack_Setup`, `F_Rack_Pairing`,
`F_RoomLayout_Local`, `F_LinkSensor_Pick`, `F_LinkSensor_Countdown`, `F_ClearRack`,
`F_RemoveRack`, the corner switch).

- **A sensor shows up by itself.** On a local install, the first pulse from a sensor the
  base station doesn't know makes its row: no owner, no rack, named by its ID until a coach
  names it (Room Layout, and the sticker). Remote is unchanged (a sensor there exists only
  by claiming). As safe as the register route it replaces: on a gym's own Wi-Fi anyone
  could already make that row. No firmware change.
- **A tablet sets up its own rack.** A new device goes to **Set up this rack** (no sign-in):
  the next free name, editable, and the gym's sensors to pick from, not those on a rack
  whose tablet is live. Picking one starts the 60-second one-rep check (Phase 3); "No
  sensor for now" skips it. Then the rack screen. Today's `/rack/setup` (waiting for a
  coach to give it a number) and the sensor step that follows it (`RackNodeSetup.jsx`,
  "The base station could not confirm this rack setup") are replaced by it.
- **The first screen on a fresh device** (proposed, Devin to confirm): straight to Set up
  this rack, with a small "This is the coach's computer" link to the coach app. The room
  display is reached from a rack's corner switch, so today's three-way picker (Rack Tablet,
  Base Station Display, Coach Admin) goes. A device already set up keeps its job.
- **Room Layout, local** (`F_RoomLayout_Local`): rename racks and sensors, link a sensor
  with the countdown on both screens, Clear and Remove. Typing a node ID, giving a tablet a
  slot number and Release go, with the routes behind them.
- **The corner switch** (rack ↔ room display, asking first) on local tablets: what spec 19
  Phase 5 planned, built here once for both versions.
- **A gym that's already set up keeps working after the update.** Each existing tablet
  keeps its rack number and gets the name "Rack N"; each sensor linked to a rack stays
  linked; nobody re-pairs anything.
- NFC check-in stays on local.

**Done when:**

- [ ] *(Backend test)* On a local install a pulse from an unknown sensor makes its row (no
      owner, no rack) and later pulses update it; on remote it is still ignored.
- [ ] *(Backend test)* The migration: existing tablets keep their numbers, named "Rack N";
      sensor links are kept.
- [ ] *(Backend test)* The retired slot routes are gone; the route walk still finds every
      remaining local route open.
- [ ] *(Frontend test)* A fresh device lands on Set up this rack; a set-up one goes
      straight to its rack screen.
- [ ] *(Browser)* A fresh local install with the simulator: open a tablet, Set up this rack,
      pair the simulated sensor with one rep, check an athlete in, finish a set; then
      rename the rack from Room Layout and see the new name on the tablet.
- [ ] *(Real sensor)* A sensor set up for local on the base station's Wi-Fi appears in
      the list by itself and pairs with one rep.
- [ ] Full suite passes in both modes.

**Stop. Devin reviews.**

## Phase 6 — Rehearsal and docs

- *(By hand)* Two tablets on a remote school, one sensor each: take one tablet offline
  mid-set and bring it back (the set keeps its reps); then kill it between sets and take
  its sensor from the other tablet.
- *(By hand)* The same on a local install, two tablets and two real sensors.
- What the common login is, and how pairing works, in `docs/remote/access.md` and the
  journal; the local setup in the rack-screen journal page.
- Merge into `SprintBranch` through the spec's pull request.
