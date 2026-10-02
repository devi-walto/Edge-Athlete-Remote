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

- **Hosting**: k3s, TLS, automatic certificates, deploys from CI, and installations
  stamped out from one template — the real one and a demo ({doc}`hosting`,
  {doc}`databases`)
- **Logins where the network used to be the lock**: a coach/athlete role split, login
  links, the session link with its group check, a rack slot per remote athlete
  ({doc}`access`)
- **Sensors over the internet**: TLS, per-sensor credentials, the broker locked down,
  and settings stored on the sensor per network ({doc}`sensors`)

**The main risk is authentication.** The rack screen has no login by design, because
the gym box's network was the boundary. On the internet, everything the old boundary
did has to be done by logins — and it has to be complete before the first athlete login
exists.

## What goes in now, and what waits

The rule: **anything that shapes the data, a protocol or the hardware is built now.
Anything that only adds on top of those can wait** — because the first kind is
expensive to change once there is data, devices or a printed board depending on it,
and the second kind is not.

| Now — by November 11 | Why now |
|---|---|
| The group check: an athlete gets into a session only if one of their groups is in it | It *is* the access model |
| Login links — first sign-in and recovery | The only way a login is connected to an athlete |
| Installations deployed from one template, with the demo as the second | Proves one database per installation for real — and faculty need the demo |
| Creating an installation from a copy, with the counters moved apart | Trivial before there is data; painful after |
| Sensor settings stored on the device, per network | The firmware is being rewritten for TLS anyway |
| The circuit-board requirements written down | Must be settled before a board is printed |

| Later | Why it can wait |
|---|---|
| The sensor's setup page (captive portal) | Writes the settings format built now |
| Merging a gym box and a hosted installation back together | Nothing to merge until a program runs both |
| An athlete's "my history" page | A screen over data that already exists |
| One sign-in across programs | Needs a second program to matter |

## The schedule

| Dates | Work | Done when |
|---|---|---|
| **Sep 24 – Oct 7** | Port the coach-account hardening. Stand up k3s, TLS and automatic certificates, deploys from CI. The installation template, with the demo as the second installation | **The app is live at a public HTTPS link**, and the demo beside it |
| **Oct 8 – Oct 17** | The coach/athlete role split. Login links, the session link and its group check, a rack slot per remote athlete. Encrypted live updates | A linked athlete opens the session link and lands on their own rack screen; one outside the session's groups is turned away |
| **Oct 18 – Oct 31** | Sensors over the internet: broker TLS and credentials, per-sensor topic limits, per-network settings on the sensor and the USB tool that writes them, authenticated sensor registration. Board requirements written down | A sensor on a home network sends reps to the hosted broker |
| **Nov 1 – Nov 3** | End to end, from a network other than the cluster's | **A remote athlete lifts with a real sensor and the workout is saved on the server** |
| **Nov 4 – Nov 11** | Report, and buffer | Submitted |

The sensor work sits **before** the buffer, not inside it, because it is the only part
with hardware in the loop. The first block grew the most; if it runs long, the demo
installation is the piece that slides into the second.

## Deliberately left out

Everything in the **Later** table above, plus:

- **Firmware updates over the air.**
- **Live two-way sync** — rejected outright, not deferred ({doc}`databases`).

## Still open

- **Whether any measurement is required** — load testing, monitoring, response times.
  If it is, it needs its own slot, and something above moves.
- **The home connection** — the cluster runs at home on the Dell and Mac mini, under
  a Porkbun domain ({doc}`hosting`), but whether the connection accepts incoming
  traffic is still to be checked.
- **When the sensor board is printed** — the setup page does not need to exist first,
  but the board requirements do.
