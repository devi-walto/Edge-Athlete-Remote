# Feature Spec 14: Sensors online

- Owner: Devin Walton
- Date: 2026-10-19
- Status: Written — not started
- Form items: Definition of Done #6 (sensors: MQTT over TLS, one credential each, publish
  only their own data, settings stored on the sensor) and #7 (end to end from a
  different network with a real sensor)
- Depends on: [04 Session link and virtual racks](04-session-link-and-virtual-racks.md)
  (sensors owned by athletes), [12 Hosting](12-hosting.md) (the `/mqtt` route, the
  school's certificate), [03 Login links](03-athlete-login-links.md) (the one-time secret
  pattern this spec makes shared)
- Background: `docs/remote/sensors.md` (saved networks, trust the root, the BNO085,
  getting every rep through). This spec changes two of its choices; see Decisions.

## Why

A remote athlete lifts at home with their own sensor. The sensor has to reach the
school's server over the internet, safely, and the athlete has to be able to set it up
once and then just switch it on.

**The goal:** an athlete switches their sensor on at home and it just works. Setting it
up takes one sitting, with no one's help. A lost sensor can be switched off without
affecting anything else. Nothing stored on a sensor unlocks anything except that sensor.

For the class, setup is done over USB. The phone setup page that removes the cable is
the last phase, built if there's time.

## User stories

As an athlete, I want to get a code on my athlete page, give it to my sensor with my
home Wi-Fi, and from then on just switch the sensor on and lift.

As a coach, I want an athlete's sensor to belong to them without my linking anything,
and to be able to switch off a lost one.

## Decisions (Devin, 2026-10-19)

1. **Each sensor has its own token, made by the server.** The ID on its label says
   which sensor it claims to be; the token proves it. (Words used in this spec: the
   **account password** is what a person signs in with; the **one-time code** is what
   an athlete types once to claim a sensor; the **sensor token** is the long random
   secret the sensor keeps and sends each time it connects, in MQTT's password field.) Anyone can read an ID, so an
   ID alone would let anyone send reps as that sensor.
2. **The athlete claims their sensor with a one-time code**, not their account password.
   On their athlete page they press **Add my sensor** and get a code like `K7MQ-2XPR`
   that works once, for 15 minutes. The sensor sends the code to the school, and the
   school answers with the sensor's own token and records the athlete as its owner.
   - The sensor never sees the athlete's account password, so a sensor taken apart, or
     a fake setup page, can't give anyone the athlete's account.
   - The setup page (Phase 8) is served by the sensor over its own small Wi-Fi network,
     without the padlock a website has, so it should never ask for an account password.
   - **The coach doesn't link remote sensors.** Claiming does it. The coach can see an
     athlete's sensor and remove a lost one (the screens come with spec 04 Phase 4, in
     the UI redesign). Gym sensors are unchanged: a coach links them to racks.
3. **Sensors use port 443 with WebSockets, like the screens** (replaces 8883 in
   `sensors.md`). No router change, it reaches athletes on networks that block other
   ports, and ESP-MQTT (which the firmware moves to anyway) does WebSockets and QoS 1
   with one setting. Sensors get their **own door** on the broker: the screens' door is
   listen-only, and a sensor's job is sending.
4. **The server tells the broker about sensor logins while it runs**, through the
   broker's built-in dynamic security plugin (`mosquitto_dynamic_security.so`, in the
   image we already use). Django is the broker's administrator on the sensors' door
   only. Checked on 2026-10-19 against Mosquitto 2.0.22 with the remote settings'
   per-door rules: a login made by the server connects; it can send under its own
   `edgeathlete/node/<id>/` and nothing else; a wrong token, no login and a removed
   sensor are refused; the programs door (1883) is unaffected.
5. **One shared piece of code for one-time secrets** (Devin). Three parts of the project
   hand out something that works once and expires: the first-run setup code (spec 01),
   login links (spec 03) and sensor claim codes (this spec), with coach login codes
   (spec 11 Phase 4) next. They share one module instead of three copies.
6. **One firmware for every sensor; behaviour follows the network** (unchanged from
   `sensors.md`). The sensor keeps a list of **servers** (a gym box: plain, port 1883,
   no login; a school: 443, encrypted, its own login) and a list of **Wi-Fi networks**,
   each pointing at one server. On the gym's Wi-Fi it is a gym sensor, at home a remote
   one. No mode button.
7. **USB for the class, the phone page if time** (unchanged). The USB tool and the
   phone page write the same saved settings, so nothing is thrown away.

## What exists

- `coach_auth.py`: `issue_setup_code`, `normalize_setup_code`, `setup_code_is_valid` —
  an 8-character code from an alphabet without look-alike characters, only a hash
  stored, expires, replaced by a newer one. Stored on the one `InstallationSetup` row.
- `services/login_links.py` and `AthleteLoginLink`: `<lookup>.<secret>`, the lookup
  finds the row, only a hash of the secret stored, works once, expires, a newer one
  cancels the older, every failure gives the same answer.
- `LimitWrongAttempts` in `coach_auth.py`: a remote installation turns an address away
  for a minute after 10 wrong attempts.
- `Node.owner` (spec 04): a sensor owned by an athlete attaches to that athlete's rack
  when they join a session.
- The remote broker (`k8s/app/base/mosquitto-remote.conf`): programs door 1883 (inside
  the cluster only), screens door 9001 (`/mqtt`, listen-only). Each door has its own
  rules (`per_listener_settings true`).
- The firmware (`esp32/edge_athlete_node/`): Wi-Fi, broker and node ID compiled in;
  PubSubClient, so QoS 0 only; the MPU-6050.

## Scope

- The shared one-time secrets module; setup codes and login links moved onto it.
- The broker's sensors door and the server's management of sensor logins.
- Claim codes: the athlete's **Add my sensor**, the claim route, removing a sensor.
- The simulator acting as a remote sensor (proves the server side with no hardware).
- The rack screen ignoring a repeated rep.
- Firmware: saved servers and networks, the USB settings tool, ESP-MQTT over WebSockets
  with TLS, the claim, the BNO085.
- The end-to-end run on video.
- If time: the phone setup page.

## Non-goals

- Certificates per sensor (a private key on each sensor, like SSH keys). The check would
  happen at Traefik, where the broker can't see which sensor it was; a token is
  checked by the broker itself.
- Sensors over TLS on a local install. The gym box keeps plain MQTT on its own Wi-Fi.
- The coach's sensor screens (spec 04 Phase 4, in the UI redesign).
- Finding the school from the phone page without typing its address (needs spec 13's
  directory).

---

## Phase 0 — One-time secrets, shared

New `services/one_time_secrets.py`, used by everything that hands out a secret that
works once:

- **Codes, for people to type:** 8 characters from the alphabet without look-alikes
  (`ABCDEFGHJKMNPQRSTUVWXYZ23456789`), shown as `XXXX-XXXX`; typing them ignores case,
  spaces and dashes.
- **Links, for people to click:** a long random secret that fits in a web address.
- **Both:** only a one-way hash is stored (as for passwords), and checking a typed
  secret against it.
- **One-time rows:** an abstract model with the fields `AthleteLoginLink` already has
  (`lookup`, `token_hash`, `created_at`, `expires_at`, `used_at`, `cancelled_at`), and
  the shared rules: make one (a newer one cancels the owner's older unused one), find
  one (the lookup finds the row, the secret proves it; every failure gives the same
  answer), use one (row lock, checked again, marked used), cancel the unused ones.
  - A link's lookup is 12 random characters and its secret 32: `<lookup>.<secret>`.
  - A code's lookup is its first 4 characters and its secret the last 4. Guessing a
    code means guessing both halves within 15 minutes, 10 tries a minute per address.
- **Moved onto it, with no change in behaviour and no database change:**
  - the setup code keeps its one `InstallationSetup` row and uses the code helpers;
  - `AthleteLoginLink` takes its fields and rules from the abstract model.
- Each file opens with what it's for, in plain words.

**Done when:**

- [ ] Every existing setup-code and login-link test passes unchanged.
- [ ] `makemigrations --check` finds nothing to change.
- [ ] Tests of the module itself: a code survives being typed in lower case with spaces
      and a dash; a used, expired, cancelled or wrong secret all give the same answer;
      a newer one cancels the older; two uses at once, one wins; nothing readable is
      stored.
- [ ] No one-time logic is left outside the module (`coach_auth.py` and
      `login_links.py` keep only what is theirs).
- [ ] Full suite passes in both modes.

**Stop. Devin reviews.**

## Phase 1 — The broker's sensors door

- A third door on the remote broker: **`sensors`, port 9002, WebSockets**, loading the
  dynamic security plugin. Nobody gets in without a login; each sensor login may send
  only under `edgeathlete/node/<its id>/` (a role per sensor). Django's administrator
  login is the only other login.
- **Reached at `wss://<school>/sensors`**: one more path in `ingress.yaml`, the same
  certificate.
- **The administrator password** is made by `eactl` and kept in the school's secret,
  never in the repo. The broker's start-up step writes the plugin's file from it the
  first time (`mosquitto_ctrl dynsec init`) onto the broker's own disk, private to the
  broker's user. `eactl update` gives existing schools the new secret value.
- `services/sensor_logins.py`: add, replace and remove a sensor's login, by sending the
  plugin's commands as the administrator. Removing also disconnects the sensor.
- A local install is unchanged: no sensors door, no plugin.

**Done when:**

- [ ] *(Against a real Mosquitto 2.0.22, with the remote settings)* A login made through
      `sensor_logins` connects; it delivers under its own topic and not another's; a
      wrong token and no login are refused; after removal it is disconnected and
      cannot reconnect.
- [ ] The screens' door is still listen-only and the programs door still works.
- [ ] The broker restarting keeps every sensor login.
- [ ] The school's files pass the strict schema check; no password in the repo.
- [ ] A local install's broker settings are unchanged.

**Stop. Devin reviews.**

## Phase 2 — Claiming a sensor

- **`SensorClaimCode`** (on the shared one-time rows; migration 0029): belongs to an
  athlete, 15 minutes, a newer one cancels the older.
- **`POST /api/athlete/sensor-code/`** — athlete, remote only: a new code and when it
  expires.
- **`POST /api/sensors/claim/`** `{code, node_id}` — open on purpose (the sensor has no
  login yet), counted by the wrong-attempt limit, remote only. In one step:
  - the code must work;
  - the sensor record is made or found, and its owner becomes the code's athlete;
  - a new sensor token is made and the broker told; any older token stops working;
  - the reply is `{username, token, path: "/sensors"}`, shown this one time.
  - **A sensor already owned by someone else is refused** ("Ask your coach to remove
    it first"). Otherwise anyone with a code of their own could take over another
    athlete's sensor by typing its ID.
- **Removing a sensor**: `DELETE /api/athletes/<id>/sensor/` (coach) and
  `DELETE /api/athlete/sensor/` (the athlete themselves): its login is removed, it has
  no owner and no rack, and its record and past sets are kept.
- **The athlete's page** gains **Add my sensor**: the code, large, with its expiry and
  what to do with it. Mockup on the Final designs page first. Remote only.

**Done when:**

- [ ] A code claims a sensor: the athlete owns it, the broker knows its login, and the
      token works on the sensors door.
- [ ] A used, expired, cancelled or wrong code all get the same refusal; 10 wrong ones
      in a minute are turned away.
- [ ] Claiming again (a re-setup) replaces the token; the old one stops working.
- [ ] A sensor owned by another athlete is refused and nothing changes.
- [ ] Removing a sensor disconnects it, keeps its sets, and a fresh code can claim it.
- [ ] A coach and a gym box get no code; the claim route is `404` on a gym box.
- [ ] *(Frontend test)* **Add my sensor** shows on remote only.
- [ ] Full suite passes in both modes.

**Stop. Devin reviews.**

## Phase 3 — The simulator as a remote sensor

`simulate_node --claim <code> --server https://<school>` claims the way the firmware
will, then sends over `wss://<school>/sensors` with the login it got. It is the
software stand-in for a real sensor at home.

**Done when:**

- [ ] *(Demo U, from the Mac, over the internet)* A code from the athlete page claims a
      simulated sensor; the athlete joins a session on a phone on mobile data; a set
      records the simulated sensor's reps.
- [ ] The same simulated sensor trying to send as another sensor gets nothing through.
- [ ] Removing it from the athlete stops its reps at once.

**Stop. Devin reviews.**

## Phase 4 — The rack screen ignores a repeated rep

QoS 1 means "at least once", so a rep can arrive twice. The rack screen skips a rep
whose sensor rep number is already stored for the open set (`repBuffer.js`).

**Done when:**

- [ ] *(Frontend test)* The same rep arriving twice is counted once; two different reps
      are both counted; a new set starts counting again.

**Stop. Devin reviews.**

## Phase 5 — Firmware: settings on the sensor, and the claim

Needs the sensor.

- **Saved settings in flash:** servers and Wi-Fi networks (decision 6). Tried in order;
  the first network found is used.
- **The sensor's ID comes from its chip**, so one firmware build serves every sensor.
- **The USB settings tool** (`scripts/sensor/`): add a Wi-Fi network; add a school with
  its address and a claim code. The sensor itself sends the code and keeps the
  token, so the token never leaves the sensor.
- **ESP-MQTT over `wss` at QoS 1** for reps, with an outbox long enough to outlast a
  Wi-Fi drop; pulses and motion stay at QoS 0. A gym server stays plain MQTT on 1883.
- **TLS checked against the stored root certificates** (Let's Encrypt's ISRG Root X1
  and X2), never the server's own certificate. The clock is set from a public time
  server before connecting to a school.
- **The setup button**: a long press clears nothing and opens setup (USB now; the phone
  page later).

**Done when:**

- [ ] One build: a gym network entry talks to a gym box as today; a home entry talks to
      a school over `wss`.
- [ ] A claim code given over USB claims the sensor; switching it off and on reconnects
      with no further setup.
- [ ] Pulling the Wi-Fi mid-set and restoring it within a minute loses no rep.
- [ ] A wrong Wi-Fi password, a wrong address and a used code each show a distinct
      status light and line on the USB console.

**Stop. Devin reviews.**

## Phase 6 — Firmware: the BNO085

Needs the sensor. The motion code reads the BNO085's movement with gravity already
removed and its orientation, in the mode that ignores the compass (`sensors.md`).
Speed is still reset whenever the bar is still. The messages don't change.

**Done when:**

- [ ] A tilted bar no longer changes the measured speed of the same lift.
- [ ] Reps are detected for a squat, a bench and a clean, on a real bar.

**Stop. Devin reviews.**

## Phase 7 — End to end, on video (Definition of Done #7)

A real sensor on a network other than the Dell's, claimed with a code, an athlete
joining from a phone, a set recorded with the sensor's reps, the coach's report showing
it. Recorded.

## Phase 8 — The phone setup page (if time)

The sensor's own small Wi-Fi network and page (`sensors.md`, "The setup flow"): pick
the home network, type its password, test it live; enter the school and a claim code.
Writes the same saved settings as the USB tool. How the page learns the school's
address without typing it is decided here.

---

## Acceptance criteria

- [ ] A sensor reaches its school only with its own token, over an encrypted
      connection, and can send only its own reps.
- [ ] An athlete claims their own sensor with a one-time code; their account password
      never touches the sensor.
- [ ] A lost sensor can be removed without affecting any other.
- [ ] One firmware serves gym and home; settings live on the sensor.
- [ ] One module hands out every one-time secret in the project.
- [ ] A gym box is unchanged.

## Risks

| Risk | What reduces it |
|---|---|
| The broker's disk is lost, and with it every sensor login | Sensors re-claim with a fresh code; Phase 1 decides whether the safety copy also keeps the broker's file |
| Someone types another athlete's sensor ID with their own code | A sensor already owned is refused; a coach removes it first |
| The BNO085 misbehaves on the ESP32-C6 (reported on some ESP32 boards) | It also speaks SPI and UART; Phase 6 is after the server side, so it can't block #6 |
| Hardware time runs short | Phases 0–4 need no sensor, so the server side and #6's security are done first |
| ESP-MQTT is awkward from the Arduino setup | `espMqttClient` is the fallback (`sensors.md`) |
