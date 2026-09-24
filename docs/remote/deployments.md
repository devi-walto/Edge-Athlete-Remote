<!--
this page — the ways Edge Athlete can be run, and which of them are worth building.

Written as a decision because the tempting option (let a coach open his own box to the
internet) sounds cheaper than it is, and it will be suggested again. The table is the
short answer; the sections below it are the argument.
-->

# Where it runs

## What forced it

Until now there was one answer: a box in the gym, serving its own Wi-Fi, with nothing
reaching it from outside. Running a session over a video call breaks that — the
athletes are not in the room, so they are not on the room's network.

The only things that genuinely differ between the options are **where the server
lives**, **how devices reach it**, and **whether the internet can reach it**.
Everything else is configuration.

## What we chose

| Shape | Server lives | Devices join | Internet | Decision |
|---|---|---|---|---|
| **Gym box** — its own Wi-Fi for devices, optional uplink | in the gym | the box's Wi-Fi | optional, **outbound only** | **Keep.** What exists today |
| **Hosted** | a cluster on the internet | over the internet | yes, by design | **Build.** See {doc}`directed-study` |
| **Coach exposes his gym box** | in the gym | over the internet, **inbound** | inbound | **Rejected** — below |
| **Hybrid** — gym box that also syncs to hosted | both | the box's Wi-Fi, and the internet | outbound only | **Later.** See {doc}`databases` |

### "Gym box on the gym's network" is not a separate shape

It looked like one: turn the box's Wi-Fi off and join the gym's instead. It is a
setting on the gym box, not an architecture, because **the box's own Wi-Fi stays
either way**. Devices join the box's network, so they never need the gym's Wi-Fi
password — no asking the gym's IT, no captive portal, nothing to redo when the gym
changes its password. The gym's network, wired or wireless, is only ever the box's
**uplink**: how the box itself reaches the internet for updates, certificates, or
(later) sync.

So there is one gym box, one hardware build, one way to join a device, everywhere.

### One codebase, one rule

**A hosted installation is a gym box that happens to run in a data centre.** Same
images, same database schema, same message topics, same screens. The hosted service is
not a second application; it is the same one, reached differently. {doc}`databases`
explains the decision that makes this literally true rather than aspirational.

## What we rejected, and why

**Letting a coach open his own gym box to the internet.** It has one real merit — the
data never leaves the coach's hardware — and for a video-call session it loses to
hosting on every other axis:

- **It needs inbound access** to a network nobody on the project controls: port
  forwarding, a changing public address, a firewall configured by a strength coach.
  Every gym becomes a different network to debug from a distance.
- **The security burden lands on the box.** Certificates, logins, patches and backups,
  on a machine in a weight room that nobody watches.
- **Each box is an island.** A fix has to reach every box separately.
- **Doing it properly means an outbound tunnel to a relay** — at which point it is the
  hosted networking, rebuilt with worse properties.

If keeping data on the coach's own hardware ever becomes a hard requirement, the answer
is the **hybrid** shape — the box stays the source of truth and connects *out* — never
opening it *in*.

## What it cost

- **Two ways to run the same code.** The gym box runs under Docker Compose; the hosted
  service runs under k3s ({doc}`hosting`). The images are shared, the orchestration is
  not, and the two must not drift.
- **The gym box stays offline-first.** Nothing added for hosting may make the gym box
  need the internet to run a session.
