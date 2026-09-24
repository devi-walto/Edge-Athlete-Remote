<!--
this page — what changes for a sensor that talks to a server on the internet instead
of a box in the same room, and what the sensor's setup flow demands of the circuit
board.

Remote athletes are assumed to own a sensor. That makes this the largest single piece
of new work in the remote plan, and the only one with hardware in the loop. The setup
flow itself comes last, but it decides what goes on the board — so the board
requirements are recorded here now, before anything is printed.
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

And a sensor whose settings are fixed at build time needs **a firmware build per
athlete**, because every athlete's home Wi-Fi is different.

## What we chose

### The connection

| | Gym box (unchanged) | Hosted |
|---|---|---|
| Broker address | the box's IP | a **hostname** — the installation's own address |
| Transport | plain MQTT, 1883 | **MQTT over TLS, 8883** |
| Who may connect | anyone on the box's Wi-Fi | **one username and password per sensor** |
| What a sensor may publish | any topic | **only its own** `edgeathlete/node/<its id>/…` |
| Registering a sensor | open route | **requires a coach or athlete login** |
| A sensor belongs to | a rack | **an athlete** |

**A sensor belongs to an athlete, not a rack**, once it leaves the gym. When the
athlete joins a session, their sensor is pointed at the rack slot the server gave them
({doc}`access`). The reps, sets and topics downstream do not change.

### Settings live on the sensor, per network — built now

**One firmware for every sensor.** Nothing about a particular athlete, network or
server is compiled in. The sensor stores a short list of **saved networks** in its
flash, and each entry carries everything needed to use that network:

| Per saved network | Example: gym | Example: home |
|---|---|---|
| Wi-Fi name and password | the gym box's network | the athlete's home Wi-Fi |
| Server | the gym box | the installation's hostname |
| Encryption | off | TLS, validated against the stored root |
| Sensor's credential | none | its own username and password |

A saved network is not just a password — **it is a password paired with the server it
leads to.** In the gym, the base station's network is simply another saved entry.

For the directed study, entries are written **over USB** by a small command-line tool.
The setup page below writes the **same stored format** later, so nothing built now is
thrown away.

### Two details that would break it in week twelve

**Trust the certificate authority's root, never the certificate itself.** The
server's certificate renews automatically every few months ({doc}`hosting`). A sensor
that pins that certificate — or the intermediate that signed it — stops connecting at
the first renewal, silently, all at once. The firmware carries the long-lived root and
validates the chain against it.

**The sensor needs the correct time before TLS will work at all**, because a
certificate is only valid between two dates. The firmware already sets its clock from
an NTP server; hosted entries must point it at a public one, not at a gym box that is
not there.

### The setup flow — last, but decided

The chosen approach is a **setup page served by the sensor itself** — a captive portal.
No app to install, and it works the same on every phone.

- The sensor opens its own Wi-Fi network, answers every DNS lookup with its own
  address, and serves one small page. **The phone's portal check pops that page open
  automatically.**
- The sensor runs its access point and joins other networks **at the same time**, so
  the page can list nearby networks, try the chosen one live, and report success or a
  wrong password on the spot.
- **The same page takes the athlete's pairing code**, so one screen sets up Wi-Fi and
  links the sensor to the athlete.

Plan around:

- **An iPhone's portal window is short-lived** and closes when the phone leaves the
  sensor's network. The page is one small file of plain JavaScript.
- **The sensor's network changes channel** when the sensor joins the home network,
  dropping the phone briefly. The page reconnects and asks for status again.
- **The ESP32-C6 is 2.4 GHz only.** A 5 GHz-only home network cannot be joined; the
  page should say so rather than fail silently.
- **The setup network has a password**, printed on the sensor's label. Never open.
- **There is always a way back into setup** — a long press, or reopening the portal on
  its own when every saved network keeps failing.

School Wi-Fi, with its sign-in pages and certificates, is deliberately not a case:
athletes on campus lift in the school's weight room, on the base station's network.

### What this demands of the circuit board

These are **hardware** requirements. The firmware can change after a board is printed;
these cannot.

| Requirement | Why |
|---|---|
| **A setup button** on a free GPIO | long press to re-enter setup |
| **A status indicator** — at least one LED, ideally multi-colour | shows setup mode / connecting / connected / failed without a screen |
| **Space for a label** | the sensor's setup-network password, and its ID |
| **Antenna placement and clearance** for 2.4 GHz | the only band the C6 has; a poorly placed antenna is a range problem no firmware fixes |

## What we rejected, and why

**Setting up Wi-Fi over Bluetooth from a web page.** Web Bluetooth does not work on
iPhones, in any browser. A setup flow that excludes iPhones is not a setup flow.

**A native phone app for setup.** It works everywhere, at the cost of building,
publishing and maintaining an app to do one job the captive portal does from a web page.

**Building firmware per sensor.** It was the first plan for the directed study. It
means a rebuild for every athlete and every change of Wi-Fi — and settings stored on
the device cost about the same to build now as compiled-in ones.

**MQTT over WebSockets from the sensor**, to share one door with the browsers. More
code and memory on the device, to save one port on the cluster. Browsers need
WebSockets; sensors do not.

**One shared credential for all sensors.** Simpler to build, and one extracted sensor
would then speak for every sensor. Per-sensor credentials mean a lost sensor is revoked
alone.

**Pinning the server's certificate.** Stronger on paper; in practice an outage on
every renewal.

## What it cost

- **A credential lives in each sensor's flash.** Anyone holding the sensor can extract
  it — which is exactly why it is one credential per sensor.
- **TLS costs the sensor memory and a slower connect.** Fine on the ESP32-C6, but worth
  watching as the firmware grows.
- **Until the setup page exists, settings are written over USB.** Fine for a handful of
  sensors; the page is what makes it something an athlete can do alone.
- **The board has to be designed for a flow that is not built yet.** Hence the table
  above — it is the part of this plan that cannot be revised later.
