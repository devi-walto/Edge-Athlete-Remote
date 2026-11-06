# Timeline

The order things actually happened in, including the parts that changed course, and who did what.

Where the rest of the Journal explains *why* a decision was made, this explains *when*, and what it displaced. There are two halves: **the local install** (June to August 2026, Phases 1–18 and the merge) and **the remote work** (September 17 to November 11, my directed study).

## Two numbering systems, both real

The project has **two** sets of phase numbers, and mistaking one for the other is the
usual way people get confused reading the older documents.

**Phases 1–18** were the original plan, written up front, before any code existed.
They are the prompts the system was built from.

**The merge (P0–P15)** was a fifteen-phase piece of work that started the moment the
rack screen was finished and frozen. It was not a step between two phases — it
*rebuilt* several of them.

The original phases are kept for provenance. Where the merge rebuilt something, the
old phase text is out of date and says so.

## The shape of it

Six sprints, roughly two and a half weeks each. The team was together through Sprint 4;
Sprints 5 and 6 were the team alone. That handoff point moved once during the project —
originally it sat at the end of Sprint 3, but when four extra phases were inserted after
Phase 4, the firmware work the handoff depended on slid from Phase 9 to Phase 13, and
the gate moved with it.

## The timeline

### Sprint 1 — Foundation

| Phase | Owner | State |
|---|---|---|
| 1 · Repo bootstrap, broker, runbook | Devin | ✅ built |
| 2 · Data models & migrations | Carl | ✅ built, later reshaped by the merge |
| 3 · MQTT pulse pipeline & node simulator | Derrilon | ✅ built |

### Sprint 2 — Real-time backbone, then the planning layer

| Phase | Owner | State |
|---|---|---|
| 4 · Full REST API + batch set-complete | Carl | ✅ built — the set-complete contract is now frozen |
| 5 · Group/block/session hierarchy, catalog, maxes | unassigned | ✅ built, then **rebuilt** by the merge |
| 6 · CSV import pipeline | unassigned | ✅ built, then **rebuilt** by the merge |
| 7 · Session status, roster, makeup flow | unassigned | ✅ built |
| 8 · Wire insights generation | unassigned | ⛔ **still a stub** |

Phases 5–8 were inserted mid-project, after the planning layer turned out to be
necessary earlier than the plan assumed. They went into the spec without an owner,
which is visible in how they were later absorbed and rewritten.

### Sprint 3 — Broadcast and the rack shell

| Phase | Owner | State |
|---|---|---|
| 9 · Django broadcast publisher | Derrilon | ✅ built, later folded into one backbone |
| 10 · Rack screen PWA shell | Braydon | ✅ built — **frozen** |

### Sprint 4 — First vertical slice, and the handoff

| Phase | Owner | State |
|---|---|---|
| 11 · Rack screen end-to-end | Braydon | ✅ built — **frozen** |
| **The merge (P0–P15)** | **Devin** | ✅ complete |
| 12 · Team dashboard kiosk | Devin | ✅ built, reworked by the merge |
| 13 · Real ESP32 firmware v1 | Derrilon | ⚠️ never landed here. **Rebuilt in October** as firmware 2.x (ESP32-C6 + BNO085), see the remote work below |

### Sprints 5–6 — the team alone

| Phase | Owner | State |
|---|---|---|
| 14 · Coach tablet | Braydon | ⚠️ built, **but not as written** — delivered by the merge instead |
| 15 · Fatigue scaffold | Carl | ⛔ not built, deliberately still a stub |
| 16 · Security hardening | whole team | ⚠️ partial: its premise was overturned by the merge. **Finished for the remote server** by remote specs 01–05 and 14 |
| 17 · Firmware hardening & mounts | Derrilon | ⛔ not built |
| 18 · Full integration test & demo prep | whole team | ⛔ not done |

## The merge — the thing that reshaped the project

The merge started the moment Phase 11 froze the rack screen, and it is the single
largest event in the project's history. It put the coach front end onto the real API and
delivered planning, reports, scheduling and analytics along the way.

It matters here because **it reached backwards**. It rebuilt Phases 5 and 6, reworked
12, and delivered 14 — so four numbered phases describe work that was subsequently
redone. That is why the older phase prompts cannot be trusted as a description of what
is running, and why the current shape lives in the journal instead.

All fifteen of its own phases completed, each tagged in git.

## The renaming

Late in the merge, a pass was made over the names — routes, models, and fields — with
one rule: **a name should say what it actually is.**

During the merge, URLs had been deliberately bent to fit the front end that already
existed. That was the right call at the time and the wrong thing to keep: a route named
after a table that no longer exists is a trap for whoever reads it next.

Examples of the shape of it:

- `/api/workout-programs/` became `/api/training-blocks/`, because it serves the
  reusable template and was never a "program"
- `/api/workouts/` became `/api/training-blocks/{id}/workouts/`, because a workout is a
  day *inside* a block and cannot exist without one — moving the block from the request
  body into the URL means it cannot be forgotten
- `/api/workouts/imports/` became `/api/imports/`, because imports handle three kinds of
  sheet and only one of them is workouts

**No behaviour changed.** Same data, same responses, same permissions — only names.

## The remote work: Sep 17 – Nov 11

The same app, reachable from anywhere: my CSC 4903 directed study with Dr. Prather ({doc}`../about/directed-study`). It started from the coach redesign merge on Sep 17 (`a50e3f7`), in its own repo, `Edge-Athlete-Remote`, which kept the full history.

### Five weekly sprints

Each sprint is one weekly report.

| Dates | Sprint | What happened |
|---|---|---|
| Sep 17 – Oct 2 | **Spec & plan** | Designed the remote version, wrote the requirements, chose home hosting. The roles, login links, virtual racks and sensor-ownership decisions were made on Oct 5, before any spec was written |
| Oct 3 – 9 | **Server** | Rebuilt the Dell, learned k3s, secured coach accounts (setup code, one coach role, an administrator flag) |
| Oct 10 – 16 | **Online** | Public HTTPS, automatic tests, roles, many schools. One shared Postgres with a database per school (Oct 14); the Mac mini cut (Oct 14). **Live on Oct 16**, a few days late. The biggest win |
| Oct 17 – 23 | **Join** | Login links, session links from any network, virtual racks, secure sensors. Sensors moved from 8883 to `wss` on 443 (Oct 19) |
| Oct 24 – 30 | **Real sensor** | Live demo, firmware 2.x with the BNO085, the phone setup page. The WT901 dropped: MQTT sensors everywhere (Oct 27). Phantom lifters and the room display online (Oct 30) |

### Releases

| Version | Date | What it brought |
|---|---|---|
| v0.3.0 | Oct 2 | The fork point for the remote version, and the plan for it |
| v0.3.1 | Oct 16 | The setup screen welcomes you to the school by name |
| v0.4.0 | Oct 17 | Hosting on k3s (PR #3) |
| v0.5.0 | Oct 17 | Live updates over `wss`. It crashed the demo school's broker (a root-only rules file); the release stopped at the demo school, as designed |
| v0.5.1 | Oct 17 | The broker fix, named ports, and failed updates that undo themselves |
| v0.6.0 | Oct 19 | Session links, virtual racks and demo data (PR #9) |
| v0.7.0 | Oct 21 | Sensors online: claim codes and a token per sensor, the `/sensors` listener, and the plate loader on the rack screen (PR #10) |
| v0.7.1 | Oct 22 | `eactl get-session-link`, `eactl update` to a named release, `eactl version` (PR #11) |
| v0.7.2 | Oct 22 | eactl keeps itself up to date: the hourly self-update (PR #12) |
| v0.8.0 | Oct 27 | Sensors set up from a phone, and three PRs of fixes (PRs #13–15). **The build was locked here** for the presentation |
| v0.8.1 | Nov 4 | The room display stays signed in online, and phantom lifters (PR #16). A planned exception to the lock |
| v0.8.2 | Nov 4 | Sensor setup v2 after watching a real athlete set one up, taking over a sensor, and release pages (PR #17) |
| *firmware 2.3.4, 2.3.5* | Nov 4–5 | Wi-Fi joins at full transmit power; a filled-in school code waits for Next (PR #18, firmware only, no app release) |

### After the sprints

- **Nov 4:** a load test with phantom athletes. Each school uses about a third of a gigabyte of memory, whether anyone's lifting or not.
- **Nov 5:** an Ubuntu kernel update (7.0.0-42) broke every container after a test reboot: AppArmor started applying the host's rules inside them. Rolled back to the previous kernel and held kernel updates until after Nov 11.
- **Nov 5–6:** these docs, rewritten as a journal and reorganised into Handbook and Journal.

## Where it actually stands

**Built and running, local:** the data layer, the REST API, the real-time backbone, the rack screen, the room display, the coach tools, spreadsheet import, reports, and base station provisioning.

**Built and running, remote:** k3s on the Dell with public HTTPS, a database per school, CI/CD with the demo school first, coach and athlete logins, login links, session links and virtual racks, and sensors set up from a phone, each with its own token.

**Still outstanding:**

- **Phase 8:** insights generation is still a stub returning nothing.
- **Phase 15:** fatigue detection has an interface and a call site, and returns a stub value on purpose.
- **Phase 17:** sensor mounts and firmware hardening (battery, an enclosure).
- **Phase 18:** no full integration test pass.
- **The local install's broker still allows anonymous connections.** Accepted on a closed network; online, only a sensor with its token can publish.
- **Decided, not built:** shared racks online with a common login (spec 18), extra reps past the prescription not counting (spec 09), moving a program between a local install and the remote server (copy, then add-only merges).
- **Leftover code to remove:** the WT901 Bluetooth path, and MQTT messages nothing listens to ({doc}`../handbook/reference/mqtt-topics`).

## Who built what

:::{note}
**Read the commit counts carefully — they do not mean what they look like.** Nearly
every commit on `main` is authored by one account, because one person drove the
commits. The **co-author trailers** are the real collaboration record, and they are
counted separately below.
:::

**160 commits on `main`, from 2026-06-20 to 2026-08-07.**

### By commit authorship

| Author | Commits |
|---|---|
| Devin Walton | 156 |
| Carl Coleman | 2 |
| Braydon | 1 |
| Derrilon Young | 1 |

Counted by email rather than by display name — several people committed under more
than one name. Devin appears as `devi-walto`, `Devin Walton` and `Devin M Walton`;
Carl as `Carl Coleman` and `carbolizer`.

### By co-author credit on `main`

| Contributor | Commits credited |
|---|---|
| Braydon | 56 |
| Derrilon | 20 |
| Carl | 19 |

The unmerged coach admin branch carries more: 64 for Braydon, 49 for Derrilon and 30
for Carl at the time of writing.

### By area

Drawn from the phase owners above rather than from line counts, which measure typing
rather than contribution:

**Devin** — repo and broker bootstrap, the base station provisioning and access point,
the team dashboard, **the entire merge (P0–P15)** and the renaming pass that followed
it, the coach admin state-machine redesign, and this documentation.

**Braydon** — the rack screen, shell through end-to-end, which is the frozen contract
the rest of the system builds against; and the coach tablet.

**Carl** — the data models and migrations that everything else sits on, and the REST API
including the batch set-complete write.

**Derrilon** — the MQTT pulse pipeline and node simulator, and the Django broadcast
publisher — the two halves of the live data path.

### What the numbers do not capture

Phases 5–8 were written without an owner and absorbed during the merge, so a meaningful
amount of the planning layer has no single name against it. The firmware phases were
assigned but never landed here, so the sensor code that exists lives outside this
repository.
