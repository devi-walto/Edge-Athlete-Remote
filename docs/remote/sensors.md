<!--
this page — what changes for a sensor that talks to a server on the internet instead
of a box in the same room.

Remote athletes are assumed to own a sensor. That makes this the largest single piece
of new work in the remote plan, and the only one with hardware in the loop — which is
why it gets its own page and its own weeks.
-->

# Sensors over the internet

**Remote athletes have their own sensor.** Typing reps in by hand is not the remote
flow; the sensor is.

## What forced it

The node firmware (`esp32/edge_athlete_node/`) was written for the gym box's own Wi-Fi,
and it is right for that network:

- **The Wi-Fi name and password and the broker's address** live in `secrets.h`, and
  the node's ID is a constant in the sketch — all fixed when the firmware is built.
- It speaks **plain MQTT on port 1883** — nothing encrypted.
- The broker accepts **anonymous** connections, and anyone may publish to any topic.
- The server's `node_register` route is open to anyone.

On a closed network each of those is reasonable. On the internet, each is a way in:
anyone could read every rep in flight, publish reps as any sensor, or register devices.

## What we chose

| | Gym box (unchanged) | Hosted |
|---|---|---|
| Broker address | the box's IP | a **hostname** — the installation's own address |
| Transport | plain MQTT, 1883 | **MQTT over TLS, 8883** |
| Who may connect | anyone on the box's Wi-Fi | **one username and password per sensor** |
| What a sensor may publish | any topic | **only its own** `edgeathlete/node/<its id>/…` |
| Registering a sensor | open route | **requires a coach or athlete login** |
| A sensor belongs to | a rack | **an athlete** |

**One firmware, two build profiles.** TLS and credentials are a build setting, not a
second sketch. The gym box's profile stays exactly as it is.

**A sensor belongs to an athlete, not a rack**, once it leaves the gym. When the
athlete joins a session, their sensor is pointed at the rack slot the server gave them
({doc}`access`). The reps, sets and topics downstream do not change.

### Two details that would break it in week twelve

**Trust the certificate authority's root, never the certificate itself.** The
server's certificate renews automatically every few months ({doc}`hosting`). A sensor
that pins that certificate — or the intermediate that signed it — stops connecting at
the first renewal, silently, all at once. The firmware carries the long-lived root and
validates the chain against it.

**The sensor needs the correct time before TLS will work at all**, because a
certificate is only valid between two dates. The firmware already sets its clock from
an NTP server; the hosted profile must point it at a public one, not at a gym box that
is not there.

### Deliberately deferred

- **Setting a sensor's Wi-Fi without rebuilding it** (over Bluetooth, or a setup
  hotspot).
- **Updating firmware over the air.**

For the directed study there are one or two remote sensors. **Building the firmware
once per sensor, with that athlete's home Wi-Fi and that sensor's credentials in it, is
acceptable** — a paragraph in the report, not a fleet-management project.

## What we rejected, and why

**MQTT over WebSockets from the sensor**, to share one door with the browsers. More
code and memory on the device, to save one port on the cluster. Browsers need
WebSockets; sensors do not.

**One shared credential for all sensors.** Simpler to build, and one extracted sensor
would then speak for every sensor. Per-sensor credentials mean a lost sensor is revoked
alone.

**Pinning the server's certificate.** Stronger on paper; in practice an outage on
every renewal.

## What it cost

- **Per-sensor firmware builds do not scale.** Past a handful of sensors, Wi-Fi
  set-up without a rebuild stops being optional.
- **A credential lives in each sensor's flash.** Anyone holding the sensor can extract
  it — which is exactly why it is one credential per sensor.
- **TLS costs the sensor memory and a slower connect.** Fine on the ESP32-C6, but worth
  watching as the firmware grows.
