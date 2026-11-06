<!--
this page — why every live update in the app goes through one MQTT broker, why
the server never hears a single rep, and how the screens find out the room changed.

These decisions are the same on the local install and the remote server; only how
a message reaches the broker differs (see the MQTT topics page). Read this before
proposing a change to how sensors or screens talk, because reps and heartbeats go
to different places for different reasons.
-->

# Real-time

Everything that updates a screen without someone pressing refresh. For every topic, what starts it and who hears it, see {doc}`../../handbook/reference/mqtt-topics`. This page is about *why* it's built this way.

## Tool changes at a glance

| Job | First | Now | Why it changed |
|---|---|---|---|
| Live updates | Django Channels, considered | **MQTT through one Mosquitto broker** | We already needed a broker for the sensors |
| Browser connection | plain `ws://` on 9001 | local: still `ws://` on 9001 · remote: **`wss://<school>/mqtt` through Traefik** | A secure page refuses an insecure socket |
| MQTT in the browser | a new random client name every reconnect, QoS 0 | **mqtt.js with a stable client name, `clean: false`, QoS 1** | The broker can now hold messages for a screen that blinked off |
| MQTT on the sensor | PubSubClient, QoS 0 only | **ESP-MQTT, reps at QoS 1** | See {doc}`remote/sensors` |
| Telling screens the room changed | Django broadcasting the data | **a `MonitoringEvent` row, sent by `monitoring-publisher`, retained** | A missed message can't leave a screen wrong, and nothing private goes on the broker |
| Broker memory | none: everything lost on restart | **`persistence true`**, kept 1 day per client | Queued messages survive a broker restart |

## The problem

Screens have to update live: a rep lands on the rack screen the moment it ends, the room display moves when a set finishes, and nobody presses refresh. Several racks lift at once, on a base station that also runs the web server and the database. And a lost rep is a lost rep: it's someone's training.

## Try 1: Django Channels

The obvious answer in a Django project: an add-on that gives Django real WebSockets.

**Why I passed on it:** it would have been the biggest piece of new infrastructure in the project: a different server model, a channel layer to run, and a second way for messages to move. We already needed a broker for the sensors, and Django already has an MQTT client. Publishing to the broker we had got live updates for free.

## Try 2: each sensor runs its own small web server

**Why I passed on it:** it creates a **device-discovery problem.** Every time a sensor moves to a different rack, something has to find its new IP address. Subscribing to a topic solves that: reassigning a sensor is just "listen to a different string." No IP lookup, no connection to tear down.

## Where I landed: one broker, MQTT everywhere

One **Mosquitto** broker, and everything talks to it. Sensors publish, browsers subscribe, Django publishes and listens to a narrow slice. Browsers can't speak plain MQTT, so they use the same MQTT wrapped in WebSockets.

| | Local install | Remote server |
|---|---|---|
| Sensors and Django | port 1883 | sensors: `wss://<school>/sensors` (port 9002 behind Traefik), each with its own token. Django: 1883, inside the cluster only |
| Browsers | port 9001, `ws://` | `wss://<school>/mqtt` (port 9001 behind Traefik), listen only |

**Topics live under `edgeathlete/`, keyed by the sensor, not the rack:** `edgeathlete/node/{node_id}/rep`. Two early documents disagreed (`edgeathlete/*` vs `rack/{n}/*`), and two naming schemes is how a subscriber silently listens to nothing. A rack number is an assignment a coach can change; a sensor ID is the hardware. Keying the topic to hardware means moving a sensor is a subscription change on the screen, not re-addressing the sensor.

**What it cost:** the broker is now something the front end depends on, not just a back-end detail. And on the local install the browser's connection is still plain `ws://`, so the local install **can't be served over HTTPS** without breaking it. Online, Traefik puts TLS in front of the same listener. See {doc}`rack-screen` and {doc}`local/base-station` for what that costs locally.

## The server never hears a single rep

**The problem:** one message per rep, several racks at once, several reps a minute each. Every one could have been a database write.

**What I passed on:** writing every rep. The base station also runs the broker, the web server and the screens on modest hardware. Per-rep writes across many racks is real load, and the useful unit of training data is the set, not the rep.

**Where I landed:** Django subscribes to **`edgeathlete/node/+/pulse` only**, the heartbeats. Reps go from the sensor to the rack screen and stop there. The rack screen saves each one in the browser first, then sends the whole set at once when it ends: **one database write per set.** That's {ref}`POST /api/sets/{id}/complete/ <mc-set-complete>`, the only place reps are written.

**What it cost:** the server doesn't have a live rep count, so the room can't tick up from server data alone. The rack screen reports its rep count and latest speed through the rack-state route as it goes, and the room shows that.

:::{admonition} If you're changing how sensors talk
:class: important
**Reps and heartbeats go to different places for different reasons.** Reps go to the rack screen; heartbeats go to the server. A proposal that moves "sensor data" without separating the two will either break sensor-health monitoring or quietly leave a second radio running.
:::

## Telling the screens the room changed

**The problem:** the room display and the coach's live room have to move when anything happens: a check-in, a set starting or ending, a rack changing state.

**Try 1: Django broadcasts the data itself.** After a set, it publishes the athlete, the speeds, the rep count (`leaderboard_update`, `rack/{n}/state`).

**Why I moved on:**

- **Fire-and-forget.** A screen that blinked off for a second missed it, and stayed wrong until someone refreshed.
- **It puts athletes' data on the broker.** Online, the screens' listener is open to read, so anything on it is effectively public.

**Where I landed:** tell the screens only that **something changed**, and let them ask the server for the truth.

1. Every change writes a `MonitoringEvent` row **in the same database transaction** as the change itself. If the change rolls back, so does the event. If the event can't be written, the change doesn't happen.
2. The `monitoring-publisher` worker sends each row, in order, as `room_state_changed` on `edgeathlete/dashboard/state`: a reason and a revision number, no athlete data. It's **retained**, and the row is only marked sent once the broker confirms.
3. The screens skip any revision they've already seen and fetch {ref}`GET /api/room-state/ <mc-room-state>`.

A screen that misses a message just catches up on the next one, or on the retained one when it reconnects. The server is the only place the room's picture is put together.

**What it cost:** every update is a message plus a fetch, not just a message. And the old data broadcasts are still sent, but nothing listens to them any more ({doc}`../../handbook/reference/mqtt-topics`). They're leftovers to remove.

## Getting every message through

The first version lost messages easily: browser subscriptions at QoS 0, a **new random client name on every reconnect** (so the broker owed a screen nothing after a blip), no broker persistence (so nothing survived a restart), and sensor firmware that could only publish at QoS 0.

All four are fixed:

- **The browser** connects with a stable name (`<device id>-<tab id>`) and `clean: false`, and subscribes at QoS 1. The broker queues messages for a screen that drops for a moment.
- **The broker** has `persistence true`, and keeps a disconnected client's queue for 1 day.
- **The sensor** moved from PubSubClient to ESP-MQTT and sends reps at QoS 1, kept until the broker confirms ({doc}`remote/sensors`). QoS 1 means *at least* once, so the rack screen drops a rep it has already stored.
- **Django** publishes at QoS 1.

**Still QoS 0 on purpose:** pulses and live speed (`motion`). A lost one is replaced a moment later.

## Things I passed on

- **Django Channels.** Try 1.
- **A web server on each sensor.** Try 2.
- **Writing every rep to the database.** One write per set.
- **Putting athlete data in live broadcasts.** The screens fetch it instead.

## What it cost

- **The broker is a front-end dependency.** If it's down, nothing updates live, though every finished set is still saved.
- **No HTTPS on the local install** while the browser connects over plain `ws://`.
- **A room update is a message and a fetch.** Cheap, but twice the round trips.
