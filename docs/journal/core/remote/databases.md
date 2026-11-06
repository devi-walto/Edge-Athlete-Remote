<!--
this page — why every school gets its own database, why they all share one
Postgres, and how a program would move between a local install and the remote
server.

Read it before adding anything that has to know about more than one school. The
short version: the app never knows another school exists, and that's on purpose.
-->

# Databases

*Oct 2 – Oct 16, 2026 · spec 12 · PR #3*

## Tool changes at a glance

| Job | Local install | Remote server | Where it lives |
|---|---|---|---|
| The database server | a Postgres container next to the app | **one shared Postgres 15.18** for every school, in the `edge-athlete` namespace | `k8s/db/postgres/` |
| A school's data | the only database there | **its own database** (`school_<short name>`) with **its own login that can open only that one** | made by `eactl new` |
| How the app finds it | the name `postgres` | **the same name**: each school gets an alias called `postgres` that forwards to the shared one | `k8s/app/base/postgres-alias.yaml` |
| Safety copies | — | **`pg_dump` snapshots** on the Dell, root only, last 5 per school, none older than 30 days | `eactl backup`, `eactl restore` |

:::{warning}
**Don't point the app at the shared Postgres by its real name.** `settings.py` asks for `postgres`, on both installs. Online, that's an alias (an ExternalName Service) to `postgres.edge-athlete`. Keep it that way, and the local install and the remote server keep running the same code.
:::

## The problem

The remote server runs more than one school, at the very least the real one and the demo. One school's athletes must never show up in another's, and real athletes must never leak into the demo. It all has to be the same code as the local install. And a program might someday run both a local install and the remote server, so moving data between them has to be safe.

## Try 1: one shared database, with a school column on every table

The usual way to hold many customers: one set of tables, a column saying whose row it is, and a filter on every query.

**Why I passed on it:** every query in the codebase would have to remember that filter, forever. One forgotten filter leaks another school's athletes, or real athletes into the demo. And the remote code would carry an idea the local install doesn't have, which is exactly how two installs drift apart.

## Try 2: a Postgres per school

The first hosting plan gave each school its own Postgres, the same as a local install: a database server per school, each with its own storage.

**What worked:** total separation, and it matched the local install exactly.

**Why I moved on (Oct 14, before it was built):** every Postgres takes its own slice of the Dell's memory, and every one needs its own backup job. With one PC running every school, that adds up fast.

## Try 3: one database per school, in one shared Postgres

Postgres is the database *server*, one running program. A *database* is one separate set of tables inside it. So the server runs one Postgres, and each school gets its own database in it, with its own login that can only open that database.

**Why it fixes both:**

- **From Try 1:** the code never knows another school exists. Every school has the same tables, made by the same migrations. Program B's rows aren't in program A's database, so there's no query that can leak them. The wall between schools is structural, not a filter.
- **From Try 2:** one Postgres to run and back up, instead of one per school eating the Dell's memory.

`eactl new` makes the school's database and login, and writes the school's settings to point at them. `eactl remove` takes a safety copy before deleting anything.

**This is where I landed.**

## Moving between a local install and the remote server

*Decided, not built.* Nothing needs it until a program runs both.

**The first move is a copy.** Both sides have the same tables, and each holds exactly one program, so a plain dump and restore moves it. The new side is empty, and IDs, timestamps and history arrive unchanged. Both sides must be on the same schema version. Upgrade first, then copy.

**Right after the copy, move the ID sequences apart.** Every table's `id` is a Django `BigAutoField`: Postgres hands out the next number from that table's **sequence**. A dump copies the sequences too, so straight after a copy both sides' sequences stand at the same value, and the next set recorded on each side would *both* get `id` 501. The copy runs `setval()` on every table's `id` sequence on the receiving side, moving it to a distant range (a trillion, say), so new rows on the two sides can never share an `id`. It's part of the copy, so it can't be forgotten.

**After that: add, don't overwrite.** Everything a workout makes is new rows: the session, sets, reps, check-ins, report. Merging is adding the other side's new rows, so both workouts are kept. What can actually conflict is a shared record edited on both sides, like the same athlete renamed twice. **The remote server wins those**, because the coach manages the roster and plans from anywhere.

:::{warning}
**A merge has to carry original timestamps.** Maxes are add-only, and the newest one wins. Stamp merged maxes with the time of the merge instead of the time of the lift, and every athlete's current max comes out wrong, and every prescribed weight with it, since plans store percentages. Manual maxes and end-of-day reports get carried as they are, never re-worked out.
:::

## Things I passed on

- **Live two-way sync between a local install and the remote server.** Rejected outright. Two copies editing the same data puts data integrity at risk.
- **Restoring one side over the other after the first copy.** The simplest merge, and it deletes a workout whenever both sides recorded one.
- **Random IDs (UUIDs) on every table.** They'd prevent clashes too, but it means rewriting every key in the schema. Moving the ID sequences apart gets the same guarantee in one step.

## What it cost

- **If the shared Postgres is down, every school is down.** That's the trade for one copy instead of one per school.
- **Migrations run once per school,** not once. Fine at tens of schools; that's what `eactl update --all` is for.
- **Anything that spans schools needs its own layer.** An athlete in two programs has two records in two databases. One sign-in across them is future work.
- **"The remote server wins" can throw away a roster edit** made on an offline local install, if the same record was also edited online. That's why syncing before switching sides stays the normal path.
