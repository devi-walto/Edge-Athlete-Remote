# Feature Spec 15: Usage history, a cloud cost estimate, and when to scale

- Owner: Devin Walton
- Date: 2026-10-20
- Status: **After the class, except Phase 0.** Phase 0 (recording) can start any time:
  history can't be collected later, so the sooner it runs, the more there is to work
  with. Not part of the Definition of Done (the form leaves out measurement and load
  testing).
- Depends on: [12 Hosting](../remote/12-hosting.md) (the Dell, the shared Postgres, the
  namespace per school). Phase 5 builds on [13 Registry and console](13-registry-and-console.md).

## Why

Every school runs on one server today, the Dell. Two questions will come up as schools
are added, and both need numbers rather than guesses:

1. **What would this cost to run in the cloud?** For example on AWS: which server size,
   how much storage, how much traffic, per month.
2. **When does one server stop being enough?** Which month the busiest hour would have
   outgrown the Dell, or the next cloud server size, and how much each new school or
   athlete brings that day forward.

Both come from the same thing: a record, month by month, of what the server and each
school actually used.

## User story

As the person running the server, I want a monthly report of what the server used, what
it would have cost on AWS, and when it would need to grow, so that I can plan before it
slows down rather than after.

## Decisions (Devin, 2026-10-20)

- **Its own spec**, not part of spec 13. Spec 13's console shows the results later
  (Phase 5).
- **Record now, analyse later.** Only the recording (Phase 0) is worth doing before
  November 11.
- **AWS first** for the estimate. Other clouds can use the same numbers later.

## What to record, and why each

| Measure | Why it matters | AWS charge it maps to |
|---|---|---|
| CPU and memory, server and per school, **every 5 minutes** | Training happens in bursts (after school), so the **busiest hour** decides the server size, not the average | EC2 instance size |
| Disk: each school's database, the broker's disk, the backups | Grows with every set and rep | EBS (GB per month), S3 for backups |
| Traffic out to the internet, per school | Pages, live updates, reports | Data transfer out |
| Connections at the busiest moment: screens and sensors on the broker | When one broker or server stops being enough, regardless of CPU | (decides scaling, not price) |
| Per school, per day: active athletes, sessions, sets, reps, coaches | Turns server numbers into **cost per athlete**, so growth can be forecast from schools and athletes, not just from a line through past months | — |

**Peaks, not averages.** For each day, keep the busy-hour figure (the 95th percentile of
that day's samples, so one odd spike doesn't decide it) as well as the average.

**Counts only.** No names, nothing about any one athlete: how many, never who.

## Phases

### Phase 0 — Record (can start now)

- **A small database, `ea_usage`, in the shared Postgres**, beside the schools' (the way
  spec 13 adds `ea_registry`). Two tables:
  - `sample`: time, school (or "server"), CPU, memory. One row per part per 5 minutes.
  - `daily`: date, school, the day's busy-hour and average CPU and memory, database
    size, broker disk, and the counts (active athletes, sessions, sets, reps, coaches).
- **A collector**, run by Kubernetes on a schedule (a CronJob in `edge-athlete`):
  - every 5 minutes: CPU and memory from metrics-server (part of k3s already, so
    nothing new to install), per school and for the whole server;
  - once a night: database sizes, disk use, the day's counts from each school, and the
    roll-up of the day's samples into `daily`.
- **Read-only, and only what it needs.** The collector reads the cluster's figures
  (no changes allowed) and the counts through a login that may only count rows in each
  school's database, never read them. It writes to `ea_usage` and nowhere else.
- **Old samples are thinned:** keep the 5-minute samples for 90 days; `daily` rows are
  kept for good (a few hundred bytes a day per school).
- **`eactl usage "School" [--days 30]`**: the daily rows for one school, or `--server`
  for the whole server.

**Done when:**

- [ ] Samples appear every 5 minutes and a `daily` row per school each night, for every
      school, including one added after the collector started.
- [ ] The collector's login can't change anything in the cluster, or read any row in a
      school's database (only count them); checked by trying.
- [ ] A school's counts match what its own database says for that day.
- [ ] The collector costs the server almost nothing (under 1% CPU on average).
- [ ] A restart of Postgres or the Dell loses at most the samples taken while it was down.
- [ ] `eactl usage` shows the last 30 days for a school and for the server.

**Stop. Devin reviews.**

### Phase 1 — Traffic and connections

- Traefik's built-in counters switched on: bytes in and out per school address.
- The broker's own counters: connections at the busiest moment, per door (screens,
  sensors).
- Both rolled into `daily`.

**Done when:**

- [ ] A day's traffic per school is within 10% of what the router or Traefik logs show.
- [ ] Opening ten screens raises that day's peak connections by ten.

### Phase 2 — The monthly report

- One page per month (`eactl usage --month 2026-11`): for the server and each school,
  busy-hour CPU and memory, storage, traffic, peak connections, and the counts.
- **Cost per unit**, worked out from the months so far: per active athlete, per set, per
  school: storage per month, traffic per month, CPU and memory in the busiest hour.

**Done when:**

- [ ] The report for a month matches the `daily` rows it comes from.
- [ ] The cost per unit is shown with how many months it rests on (one month is a guess).

### Phase 3 — The AWS estimate

- The month's needs plus headroom (30% by default, a setting): pick the smallest EC2
  instance that fits the busy hour, then add EBS for storage, S3 for backups, and
  traffic out.
- Prices from AWS's own Price List API, for one chosen region, fetched when the report
  runs, so they are never stale; the date and region are printed with the estimate.
- Shown beside what the Dell costs (electricity, from a setting).
- **The estimates and anything about pricing or the business stay out of this
  repository** (the README's rule). The code that makes them is fine here.

**Done when:**

- [ ] For a past month, the estimate names an instance, storage and transfer, with a
      total, the region and the price date.
- [ ] Changing the headroom changes the instance picked when it should.

### Phase 4 — When it would have scaled, and when it will

- **Looking back:** for each past month, which server size the busy hour needed; the
  first month it would have outgrown the Dell, or each cloud size.
- **Looking forward, two ways, shown side by side:**
  - the trend of the past months, carried on;
  - from growth: "N new schools a month, about M athletes each" (settings) times the
    cost per unit from Phase 2.
- Each forecast names the limit it crosses first (memory, CPU, disk, connections) and
  the month, with a range rather than one date.

**Done when:**

- [ ] With made-up history that crosses a limit in a known month, both ways find it.
- [ ] Doubling the growth settings brings the date forward, and the report says which
      limit moved it.

### Phase 5 — In the console

The report and forecast as pages in spec 13's operator console: charts per month, per
school, and the forecast line.

---

## Acceptance criteria

- [ ] Every school's use is recorded from the day it starts, with no names.
- [ ] A month's use turns into an AWS estimate with prices that aren't stale.
- [ ] The report says when the server would have needed to grow, and when it will.
- [ ] Recording costs the server almost nothing and can't change or read a school's data.

## Non-goals

- Load testing or made-up traffic to find limits (the form leaves it out; real use only).
- Charging schools, or pricing plans.
- Growing the server by itself (autoscaling). This spec says when; a person decides.
- Estimates for clouds other than AWS (the same numbers can feed them later).

## Open questions

- The Dell's own figures: CPU cores, memory, disk size, and its electricity use, for
  the comparison. *(Devin to fill in.)*
- The AWS region to price in.
- Whether `daily` rows move into spec 13's `ea_registry` when that exists, or stay in
  their own database.

## Risks

| Risk | What reduces it |
|---|---|
| Too few months to forecast from | Every forecast shows how many months it rests on and a range; the growth-based one works from the first month |
| One unusual day (a demo, a tournament) skews a month | Busy hour is the 95th percentile, and the report lists the days that stood out |
| The collector becomes a way into school data | It may only count rows, and only write to `ea_usage`; Phase 0 checks both by trying |
| Cost numbers leak business plans into the public repo | Estimates are printed, not committed; only the code is in the repo |
