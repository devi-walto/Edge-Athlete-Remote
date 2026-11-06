<!--
this page — the CSC 4903 directed study the remote work was built for: what I
promised, where each piece ended up, and what changed from the plan and why.

Written at the start (Sep 24) and finished at the end (Nov 6). The plan is kept
next to what happened on purpose: the changes are the useful part.
-->

# Directed study (CSC 4903)

*Dr. Prather · Sep 17 – Nov 11, 2026*

## What I set out to do

The same flow as the gym, run from anywhere. A coach runs a session over a video call, athletes on their own networks open their own rack screen and lift with their own sensor, and the workout is saved on the server. Three learning outcomes:

1. **Learn k3s.**
2. **Host the app at a link anyone can click.**
3. **Athletes on another network reach the rack screen and run a workout that's saved on the server.**

The rule I planned by: **anything that shapes the data, a protocol or the hardware is built now; anything that only adds on top of those can wait.** The first kind gets expensive to change once there's data or devices depending on it. Or, the way I put it in my presentation: I wanted to get the foundation right first. Everything else can be built on top of it later.

## Where each item ended up

The Definition of Done from the project form, in priority order:

| # | Item | Status | Where |
|---|---|---|---|
| 1 | k3s, public HTTPS, certificates that renew themselves, CI/CD | **Done**, live Oct 16 | {doc}`../journal/core/remote/hosting`, {doc}`../journal/core/remote/releases` |
| 2 | Coach accounts hardened: a setup code, an administrator manages logins, no well-known demo login online | **Done** | {doc}`../journal/core/remote/access` |
| 3 | Coach and athlete roles; athletes join only sessions their group is in, on their own rack | **Done** | {doc}`../journal/core/remote/access`, {doc}`../journal/core/remote/virtual-racks` |
| 4 | Login links (also for recovery), a session link that works from any network, live updates over `wss` | **Done** | {doc}`../journal/core/remote/access` |
| 5 | A separate demo school, made from the same template | **Done** | {doc}`../journal/core/remote/databases` |
| 6 | Sensors: MQTT over TLS, a credential per sensor, each publishes only its own data, settings stored on the sensor | **Done** | {doc}`../journal/core/remote/sensors` |
| 7 | End to end, live or on video, from a different network with a real sensor | **Done**, shown live Oct 27 | {doc}`../journal/core/remote/sensors` |
| 8 | Developer docs: deploying on k3s, and the key decisions | **Done** | {doc}`../handbook/guides/remote-server`, the {doc}`Journal <../journal/index>` |
| 9 | Weekly progress reports to Dr. Prather, with links to commits | **Done** | the final report, Nov 6 |
| 10 | The final presentation | **Scheduled** | before Nov 11 |

## The plan vs what happened

| Planned | Work | Actually |
|---|---|---|
| Sep 24 – Oct 7 | Coach-account hardening; k3s, TLS, certificates, CI deploys; the school template with the demo as the second school | Live at a public HTTPS link on **Oct 16**, about a week late. I was learning Kubernetes and getting a starter app running first |
| Oct 8 – Oct 17 | Roles, login links, the session link and its group check, a rack per remote athlete, encrypted live updates | Live updates over `wss` Oct 17 (v0.5); session links and virtual racks Oct 19 (v0.6) |
| Oct 18 – Oct 31 | Sensors over the internet: TLS and credentials, per-sensor topic limits, settings stored on the sensor | Sensors online Oct 21 (v0.7); the real sensor and the phone setup page Oct 27 (v0.8.0) |
| Nov 1 – Nov 3 | End to end from another network | **Done early**, at the Oct 27 demo |
| Nov 4 – Nov 11 | Report, and buffer | Sensor setup v2 after watching a real athlete set one up; these docs; the presentation |

The first block grew the most, like I expected. The sensor work sat **before** the buffer on purpose, since it was the only part with hardware in the loop, and that's the part that ended up finishing early.

## What changed from the plan, and why

- **The sensor's phone setup page moved from "later" to "now"** (Oct 27). The plan was a USB tool for the class and a setup page after. After the demo, a laptop and a cable clearly wasn't something an athlete would do alone, so I dropped the USB tool ({doc}`../journal/core/remote/sensors`).
- **Sensors use `wss` on 443, not MQTT on 8883** (Oct 19). Moving the firmware to ESP-MQTT made WebSockets one setting, and 443 needs no extra router port and gets through hotel and guest Wi-Fi.
- **One shared Postgres with a database per school, not a Postgres per school** (Oct 14), before it was built ({doc}`../journal/core/remote/databases`).
- **The second server was cut** (Oct 14). It was never in the Definition of Done, and k3s only runs on Linux.
- **One kind of sensor everywhere** (Oct 27). The Bluetooth sensor was dropped; the same MQTT sensor works in the gym and from home.
- **Copying a school between a local install and the remote server slid to later.** It was planned "now" because it's trivial before there's data. It's decided, and nothing needs it until a program runs both.

## Deliberately left out

- **Live two-way sync** between a local install and the remote server. Rejected outright, not deferred: two copies editing the same data puts data integrity at risk.
- **A second server, autoscaling, load testing.** One home server is enough for now; nothing assumes a second. (I ran a load test anyway on Nov 4: each school uses about a third of a gigabyte of memory, busy or idle.)
- **Firmware updates over the air,** and a certificate per sensor.
- **An athlete history page with charts,** and **one sign-in across programs.** A history page is a screen over data that already exists; one sign-in only matters with a second program.

## What was open at the start, and the answers

- **Was any measurement required?** No. Load testing wasn't on the form.
- **Would my provider block ports 80 and 443?** No. The connection has its own public address (checked Oct 5), and both ports came through once something was serving on them (Oct 14).
