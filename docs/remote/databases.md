<!--
this page — one database per installation, and how a program moves between a gym box
and the hosted service.

The decision here is small to state and decides a lot: it is why the hosted code can
be the gym box's code, why the fence between programs cannot be forgotten, why the demo
cannot leak real data, and why moving a program from one shape to the other starts
with a copy. Read it before adding anything that has to know about more than one
program.
-->

# One database per installation

An **installation** is one program's copy of the system: its roster, its plans, its
history. A gym box is one installation. On the hosted service, each program is one
installation too — and so is the demo shown to faculty ({doc}`access`).

## What forced it

The hosted service will run more than one installation — at the very least the real
one and the demo. There were two ways to hold that:

1. **One shared database**, with a column on every table saying which program a row
   belongs to, and a filter on every query.
2. **One database per installation**, each looking exactly like a gym box's.

Two further facts pushed towards the second. A program may later want **both** a gym
box and the hosted service, and moving data between them must be safe. And the code
must stay one codebase ({doc}`deployments`).

## What we chose

**One database per installation. The code never knows another installation exists.**

- Every installation — gym box or hosted — has the same schema, created by the same
  migrations.
- On the hosted service, each installation is its own copy of the stack, deployed from
  **one template**: its own database, its own message broker, its own address
  ({doc}`hosting`).
- **The fence between programs is structural.** Program B's rows are not in program
  A's database, so there is no query that can leak them.

### The first move between shapes is a copy

Because both sides have the same schema and each holds exactly one program:

- **Hosted first, adding a gym box later:** the new box is empty. Copy the database
  onto it — row IDs, timestamps and history arrive unchanged.
- **Gym box first, moving online:** the hosted installation is new and empty. Same
  copy, the other direction.

A plain database dump and restore does this. **Both sides must run the same schema
version** — the copy refuses to run across versions rather than guess. Upgrade first,
then copy.

**Only the first move is a copy.** After that, both sides hold real data, and restoring
one over the other would erase whatever the overwritten side recorded since.

### Right after the first copy: move the counters apart

Every table numbers its rows with an auto-incrementing counter. Straight after a copy,
both sides' counters stand at the same number — so the next set recorded on the box and
the next set recorded online would **both be number 501**, and could never be combined.

So the copy has one more step: **the receiving side's counters are moved to a distant
range** (start at a trillion, say). From then on, a new row on one side can never
share a number with a new row on the other. It is part of the copy, not a separate
chore, so it cannot be forgotten.

### After that: add, don't overwrite

A program's sessions normally run on one side at a time, and each side syncs before
running one — a **hand-off**. The case that matters is when that does not happen: the
gym box is offline, a remote session runs online, and a gym session runs on the box
before they have synced.

That still works, because **everything a workout creates is new rows** — the session,
its sets, its reps, its check-ins, its report. Merging back is **adding the other
side's new rows**: both workouts are kept, and because the counters were moved apart,
none of their numbers clash. The athletes they point at already exist on both sides,
with the same numbers, from the first copy.

What can genuinely conflict is a **shared record edited on both sides** — the same
athlete renamed differently, the same plan changed twice. Those get an owner:

| Record | On a merge | Why |
|---|---|---|
| Sessions, sets, reps, check-ins, reports | **added from both sides** | new rows; they never overwrite each other |
| New athletes, groups, plans created on either side | **added** | new rows, and their numbers cannot collide |
| Edits to an existing athlete, group or training group membership | **hosted wins** | the coach manages the roster from anywhere |
| Edits to an existing plan or program | **hosted wins** | the coach plans from anywhere; the box runs what it was last given |
| Athlete logins and login links | **hosted only** | the gym box has no athlete logins ({doc}`access`) |

### What a merge must carry, and what re-derives

Most of the history derives from sets; a few things do not, and a merge that drops
them is silently wrong:

- **Carry:** sets and reps; **manual** maxes (a coach typed them — deriving would
  discard that judgment); end-of-day reports (frozen on purpose, and regenerating one
  later gives a different answer); and **original timestamps** on all of it.
- **Watch:** maxes are add-only, newest wins. Stamped with the time of the merge
  instead of the time of the lift, every athlete's *current* max comes out wrong — and
  every prescribed weight with it, because plans store percentages.

## What we rejected, and why

**One shared database with a program column on every table.** Every query in the
codebase would have to remember the filter, forever, and one forgotten filter leaks
another program's athletes — or real athletes into the faculty demo. And the hosted
code would carry a concept the gym box does not have, which is exactly the drift
{doc}`deployments` rules out.

**Restoring one side over the other after the first copy.** It is the simplest merge,
and it deletes a workout whenever both sides recorded one.

**Switching every table to random IDs (UUIDs).** It also prevents collisions, but it
means rewriting every primary and foreign key in the schema. Moving the counters
apart gets the same guarantee from one step at copy time.

**Live two-way sync.** Unnecessary: new rows are added, and shared records have an
owner.

## What it cost

- **Migrations and backups run once per installation**, not once. Fine at tens of
  installations; it is what the cluster's automation is for.
- **Anything that spans programs needs its own layer.** An athlete who trains with two
  programs has two athlete records in two databases. Linking them is a separate sign-in
  service, not a column — see {doc}`access`.
- **Each hosted installation costs a full stack** in memory, not a few rows. Sharing
  one database server between installations (still one database each) is a tuning
  option for later.
- **"Hosted wins" can discard a roster edit made on an offline box** when the same
  record was also edited online. Rare, and the reason the hand-off — sync before
  switching sides — stays the normal path.

**Status.** Binding **now**, for the directed study: installations are deployed from one
template (the demo is the second one); creating an installation **from a copy** of
another — counters moved apart included — is part of that template; and nothing makes
the hosted schema differ from the gym box's. The merge itself is not built — there is
nothing to merge until a program runs both shapes.
