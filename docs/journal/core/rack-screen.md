<!--
this page — the tablet at each rack: where reps are kept safe, the set lifecycle,
and how a sensor gets to a rack.

The rack screen is the one place where losing data can't be undone, so the
durability decision comes first. The kiosk decisions (HTTPS, trusted origin,
browser profiles, manifests) only exist because the local install is served over
plain HTTP; they're on the Local only > Kiosk screens page.
-->

# Rack screen

The tablet at each rack. The only screen an athlete actually touches, and the one part of the system where losing data can't be undone.

:::{admonition} Who built this
:class: note
**Bluetooth sensor acquisition** (the host agent, sensor selection at the rack, and the NFC groundwork): **Braydon**. The design record behind it is `docs/_ADR_RACK_BLE_LIVE_WORKFLOW.md`.

**Everything else on this page** (the set lifecycle, on-device rep buffering, the install and offline work): **Devin**.
:::

## Tool changes at a glance

| Job | First | Now | Where it lives |
|---|---|---|---|
| Keeping reps safe mid-set | — | **the browser's own database (IndexedDB)**, cleared only after the server confirms | `react/src/db/repBuffer.js` |
| How a sensor reaches the rack | Wi-Fi (MQTT), then Bluetooth too (WT901, through a program on the base station) | **MQTT sensors everywhere**, local and remote (since Oct 27) | {doc}`remote/sensors` |
| Linking a sensor to a rack | a coach, on the coach's screens | **local:** a coach, in Room Layout or on the rack card · **remote:** the athlete's own sensor, attached on join | {doc}`remote/virtual-racks` |
| Who's lifting online | — | **the rack's owner**, on a virtual rack | {doc}`remote/virtual-racks` |
| The athlete's plan | read once at check-in | **re-read after every set** | `RackScreen.jsx` |
| Releasing a tablet | nothing could | **"no rack" means release** (Aug 12) | Room Layout |

## The problem

Reps arrive one at a time over a wireless connection, in a room full of metal, and they're only useful as a complete set. Something has to hold a partial set safely while it's being built. And the screen has to know which sensor is on its bar.

## Where reps are kept safe

**Try 1: in the server's memory.** **Why I passed on it:** a browser tab surviving a Wi-Fi drop is a far better bet than a server process surviving a restart while holding unfinished sets for every rack. One loses a rack; the other loses the room.

**Try 2: on the sensor**, a full set stored in its flash and sent directly. **Why I passed on it:** the sensor has no idea whose set it is. The session, athlete and exercise only exist on the rack screen, so the sensor would need a whole new channel just to learn who it's recording. And the browser gives durable storage for free; doing it in firmware means a hand-written flash queue with acknowledgement, replay and flash-wear handling, to save a network hop that isn't a bottleneck.

**Where I landed: the rack screen is where reps are kept safe, not the server.** Every rep is written to the browser's own database **the instant it arrives**, before the screen updates and before the server hears anything. When the set ends, the whole set goes to the server in **one request**. The local copy is cleared only after the server confirms.

Think of it as writing each rep in a notebook as it happens, so even if the phone line drops before you call it in, you still have every rep.

*Since firmware 2.0 the sensor does keep reps for a moment:* ESP-MQTT holds a rep that ended while it was offline and sends it when it reconnects. That's a few reps waiting for a connection, not a set, so Try 2's reasons still stand.

**What it cost:** if a tablet crashes or loses power mid-set, **that rack's current set is lost.** It's accepted, not solved, and ruled out of scope rather than left as an open bug. The loss stays at one rack instead of the room.

## The set lifecycle

Worth knowing before changing anything nearby:

1. **Check in.** Tapping a name (or a wristband) is the check-in. It's append-only and newest wins: the most recent check-in decides which rack an athlete is at. Online, joining a session does the same check-in, through the same function ({doc}`remote/virtual-racks`).
2. **Idle.** The athlete's workout for the day loads, with a suggested movement and a target weight worked out from their max, or a blank one they can fill in.
3. **Active.** The screen listens to its sensor **only while a set is running.** Reps at any other time are ignored, so a bumped bar between sets doesn't become data.
4. **Complete.** Exactly one submission per set, guarded so a double-tap can't make two. The plan is re-read afterwards, so a coach's edit mid-session reaches the rack by the next set, and a finished movement moves on to the next one by itself.
5. **Rest.** The check-in list comes back, so the next lifter can take the rack.

**Next (decided Oct 27, not built):** reps past the prescription won't count. The screen will say "Reps past 5 won't count," and the server will decide which reps count, not the firmware: *the sensor just reports what happened.* A set with bad reps is what False Set is for.

## Reps in progress aren't results

Live reps have to show up instantly, and a bar somebody bumped between sets moves exactly like lifting.

So there are two different things with two different standards. Reps arriving *during* a set are **live activity**: shown right away, kept only as a recoverable snapshot, never counted as anything. Records, rankings and history are written only when a set is **completed**, from the saved set.

**Nothing becomes a number anyone is judged on until a person ends the set.**

The cost is two copies of the same reps, and a real chance of mixing them up when reading the code. The alternative was a knocked barbell setting a personal record, which is the kind of bug that ruins trust in the whole system.

## How a sensor gets to a rack

**Try 1: Wi-Fi sensors through the broker.** The original sensors reported over Wi-Fi, through Mosquitto. A coach linked each one to a rack.

**Try 2: add Bluetooth (the WT901), per sensor.** Each sensor recorded its own transport (`Node.acquisition_kind`: `mqtt` or `wt901_ble`), so rack 1 could be Bluetooth while rack 2 was Wi-Fi, in the same session. Three decisions came with it:

- **A program on the base station owned the radio, not the browser.** Browser Bluetooth needs a secure context (the local install is plain HTTP), a person's tap to pair every time (a rack screen boots unattended), and doesn't exist on iPhone or iPad. The cost: that program was a single point of failure for every Bluetooth rack at once.
- **Raw motion data never left the base station.** The server saw confirmed reps, never the stream.
- **Sensors were chosen at the rack, by a coach, before anyone signed in.** Bluetooth sensors show up as anonymous nearby radios; you have to stand at rack 3, watch one move, and confirm *that's* the one. Choosing used scan-scoped handles, so a Bluetooth address never reached the browser or the database.

**Why I moved on (Oct 27):** one kind of sensor everywhere, local and remote, simplifies the hardware story. The new sensor (ESP32-C6 + BNO085) speaks MQTT over Wi-Fi in the gym and over the internet from home ({doc}`remote/sensors`).

**Where I landed: MQTT sensors everywhere.** On a local install, a coach links a sensor to a rack in **Room Layout**, or from the **rack card in Session** while looking at it. Online, an athlete's own sensor attaches to their virtual rack when they join.

:::{warning}
**The Bluetooth code is still in the repo, unused:** `rack/rackAgent.js`, `rack/RackNodeSetup.jsx`, `/api/racks/{n}/sensor-health/`, the `/api/ble/…` routes, `services/ble_agent.py`, `scripts/hardware/wt901_rack_agent.py`, and `Node.acquisition_kind`. Don't build on it. It's leftover, to be removed.

One lesson from it is worth keeping: when sensor selection moved to the rack, the coach-side linking route was removed, and work written against it compiled and merged cleanly, then failed when someone pressed the button. A removed route fails at runtime, not at merge.
:::

## A sensor announces itself (local)

**The problem:** nothing could put a Wi-Fi sensor into the system. A message from a sensor the database had never heard of was rejected, so a second simulated rack published into nothing while its log looked healthy. With real hardware, eight sensors on eight racks had no way in short of typing database rows by hand.

**Where I landed:** the pattern the system already used. A rack tablet has always *announced itself* ("I exist, here's my ID") and waited for a coach to give it a rack. Now sensors do too (`POST /api/nodes/register/`), and the simulator does it on startup.

**Why leaving it open is safe:** announcing gets a sensor a row and nothing else: no rack, no data path. The step that matters is linking, and that's a coach action. **The one rule that would be a hole if it broke:** announcing must never change a sensor that already exists, or anything on the gym's Wi-Fi could take over a linked sensor's rack. There's a test whose only job is that.

**Online it's different:** registering is coach-only, and a sensor claims itself with an athlete's one-time code instead ({doc}`remote/sensors`).

## A tablet can be released, not only assigned

*Fixed Aug 12.* For most of the project, nothing ever cleared a tablet's rack number, and the coach's list of waiting tablets only showed ones with *no* number. So a tablet sent back to setup kept its old rack, never reappeared in the list, and couldn't be reassigned: still working, still on the network, unreachable from the coach's side.

**The workaround that made it worse:** clearing the tablet's browser data seemed to fix it, and became folklore. It works because it erases the tablet's identity, so it comes back as a device the server has never seen. You weren't repairing the tablet; you were replacing it, and abandoning the old record every time.

**Where I landed:** assignment accepts an explicit "no rack" to mean *release this tablet*, and Room Layout has a button for it. The tablet gets `enter_setup` over MQTT and reappears in the waiting list within seconds.

**The half that's easy to miss:** a tablet only left its waiting screen when the rack it was told about *differed* from the one it knew. So a tablet freed from rack 3 and put straight back on rack 3 would have waited forever, which is exactly what someone fixing a mislabelled room tries first. Being released now also makes it forget its old rack.

**What it cost:** a meaningful null. "No rack number in the request" and "rack number deliberately empty" now have to be told apart.

## The freeze, and why it ended

For most of the project, `react/src/rack/`, `react/src/db/repBuffer.js` and `react/src/device.js` were **frozen**: ship as-is, build alongside them. Several people were building against this behaviour at once while it was also the demo, and small "improvements" to a shared contract break things in ways that are hard to trace.

**It was lifted on Aug 10**, because two known bugs sat inside it and couldn't be fixed there: the screen's periodic refresh is off during an active set, and an athlete's plan was read once at check-in and never again. The second is fixed (the plan is re-read after every set). The first matters much less now that reps arrive at QoS 1 and the broker holds them for a screen that blinks off ({doc}`real-time`).

**The lesson isn't "never freeze code."** A freeze needs an expiry condition stated when it starts, or it outlives its reason and nobody feels entitled to end it.

## Things I passed on

- **Keeping a partial set in the server's memory, or on the sensor.** The rack screen keeps it.
- **A second rack screen for remote athletes.** Same screen ({doc}`remote/virtual-racks`).
- **Bluetooth in the browser.** No secure context locally, no one to tap pair, no iPhone.
- **Two kinds of sensor.** MQTT everywhere since Oct 27.

## What it cost

- **A tablet that dies mid-set loses that set.**
- **Two copies of the same reps** (live and saved), easy to mix up in the code.
- **Leftover Bluetooth code** that looks live and isn't.

The kiosk decisions (why the local install isn't HTTPS, the trusted origin, kiosk vs incognito, a browser profile per role, three app manifests) are on {doc}`local/kiosk-screens`.
