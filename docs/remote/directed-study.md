<!--
this page — what the directed study promises, what is being built to meet it, and in
what order.

Written down now, at the start, because the scope was cut deliberately and the reasons
are much easier to record today than to reconstruct in November. If the plan changes,
change this page and say why; do not let it quietly drift from what is being built.
-->

# The directed study

**Due November 11, 2026.** Planned September 24.

## What it promises

The learning outcomes, as proposed — the requirements document itself is written from
the course's template (CSC 4903) and has not been submitted yet:

1. **Learn k3s.**
2. **Host the app at a link anyone can click.**
3. **Athletes on another network reach the rack screen and run a workout that is saved
   on the server.**

That is: **the same flow as the gym, run from anywhere** instead of needing to be on
the gym box's Wi-Fi. Where something makes more sense for a remote-only session, it
may change — who is lifting is proven with a login rather than a tap, for example —
but the workout itself is the gym's workout.

## What makes it reachable

Most of the backend was built with this in mind:

- **Sets without a sensor are already legal** on the server — the sensor is optional
  when a set is created.
- **Secure live updates are encryption in front of the existing broker**, not a new
  real-time layer ({doc}`hosting`).
- **The database schema stays as it is.** Coach accounts use Django's own
  authentication; the planning features already exist.
- **The coach-account hardening is already written** — on the team repository, by
  Braydon — and is being ported ({doc}`access`).

## What is actually new

- **Hosting**: k3s, TLS, automatic certificates, deploys from CI ({doc}`hosting`)
- **Logins where the network used to be the lock**: a coach/athlete role split, athlete
  invites, the session link, a rack slot per remote athlete ({doc}`access`)
- **Sensors over the internet**: TLS, per-sensor credentials, the broker locked down
  ({doc}`sensors`)

**The main risk is authentication.** The rack screen has no login by design, because
the gym box's network was the boundary. On the internet, everything the old boundary
did has to be done by logins — and it has to be complete before the first athlete login
exists.

## The schedule

| Dates | Work | Done when |
|---|---|---|
| **Sep 24 – Oct 7** | Port the coach-account hardening. Stand up k3s, TLS and automatic certificates, deploys from CI | **The app is live at a public HTTPS link** |
| **Oct 8 – Oct 17** | The coach/athlete role split. Athlete invites, the session link, a rack slot per remote athlete. Encrypted live updates | An invited athlete opens a link and lands on their own rack screen |
| **Oct 18 – Oct 31** | Sensors over the internet: broker TLS and credentials, per-sensor topic limits, the hosted firmware profile, authenticated sensor registration | A sensor on a home network sends reps to the hosted broker |
| **Nov 1 – Nov 3** | End to end, from a network other than the cluster's | **A remote athlete lifts with a real sensor and the workout is saved on the server** |
| **Nov 4 – Nov 11** | Report, and buffer | Submitted |

The sensor work sits **before** the buffer, not inside it, because it is the only part
with hardware in the loop.

## Deliberately left out

- **Sync between a gym box and the hosted service** — designed ({doc}`databases`), not
  built. The study hosts one installation.
- **Linking an athlete's logins across programs** — future ({doc}`access`).
- **Setting a sensor's Wi-Fi without rebuilding it, and firmware updates over the
  air** — sensors are built once per athlete ({doc}`sensors`).
- **An athlete's "my history" page** — only if time remains after November 3.

## Still open

- **Whether any measurement is required** — load testing, monitoring, response times.
  If it is, it needs its own slot, and something above moves.
- **Where the cluster runs** — hardware at home, or a rented server.
- **The domain**, and whether its DNS can be changed freely.
