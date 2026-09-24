<!--
this page — one database per installation, and how a program moves between a gym box
and the hosted service.

The decision here is small to state and decides a lot: it is why the hosted code can
be the gym box's code, why the fence between programs cannot be forgotten, and why
moving a program from one shape to the other is a copy. Read it before adding anything
that has to know about more than one program.
-->

# One database per installation

An **installation** is one program's copy of the system: its roster, its plans, its
history. A gym box is one installation. On the hosted service, each program is one
installation too.

## What forced it

The hosted service may run more than one program. There were two ways to hold that:

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
- On the hosted service, each installation is its own copy of the stack: its own
  database, its own message broker, its own address ({doc}`hosting`).
- **The fence between programs is structural.** Program B's rows are not in program
  A's database, so there is no query that can leak them.

### Moving a program between shapes is a copy

Because both sides have the same schema and each holds exactly one program:

- **Hosted first, adding a gym box later:** the new box is empty. Copy the database
  onto it — row IDs, timestamps and history arrive unchanged.
- **Gym box first, moving online:** the hosted installation is new and empty. Same
  copy, the other direction.

A plain database dump and restore does this. **The one precondition is that both sides
run the same schema version** — the copy must refuse to run across versions rather
than guess. Upgrade first, then copy.

### After the first copy: a hand-off, not a merge

A program's sessions never run in the gym and online **at the same time**. So ongoing
sync is a hand-off: **whichever side ran the last session holds the current truth, and
the other side syncs before it runs one.**

The one case that hand-off does not cover is an edit made **between** sessions while
the gym box is offline — a coach changes Thursday's plan from home on Tuesday. That is
settled by giving each kind of record one home:

| Record | Home in a hybrid program | Why |
|---|---|---|
| Sessions, sets, reps, check-ins | **wherever they were recorded** | only one side ran that session |
| Plans and programs | **hosted** | a coach plans from anywhere; the gym box runs what it was last given |
| Athlete logins | **hosted** | the gym box has no athlete logins ({doc}`access`) |

The two sides then only ever change **different kinds** of record, so there is nothing
to reconcile — only newer copies to pass along.

### What a sync must carry, and what re-derives

Most of the history derives from sets; a few things do not, and a sync that drops them
is silently wrong:

- **Carry:** sets and reps; **manual** maxes (a coach typed them — deriving would
  discard that judgment); end-of-day reports (frozen on purpose, and regenerating one
  later gives a different answer); and **original timestamps** on all of it.
- **Watch:** maxes are add-only, newest wins. Replayed out of order, or stamped with the
  time of the sync, every athlete's *current* max comes out wrong — and every
  prescribed weight with it, because plans store percentages.

A whole-database copy gets all of this right for free. It only matters once sync is
incremental.

## What we rejected, and why

**One shared database with a program column on every table.** Every query in the
codebase would have to remember the filter, forever, and one forgotten filter leaks
another program's athletes. Row IDs would collide the first time a gym box's data moved
online — the box's athlete 17 and the hosted athlete 17 are different people — so every
move would need a renumbering import. And the hosted code would carry a concept the gym
box does not have, which is exactly the drift {doc}`deployments` rules out.

**Live two-way sync.** Unnecessary, because sessions never overlap and each record has
one home.

## What it cost

- **Migrations and backups run once per installation**, not once. Fine at tens of
  installations; it is what the cluster's automation is for.
- **Anything that spans programs needs its own layer.** An athlete who trains with two
  programs has two athlete records in two databases. Linking them is a separate sign-in
  service, not a column — see {doc}`access`.
- **Each hosted installation costs a full stack** in memory, not a few rows. Sharing
  one database server between installations (still one database each) is a tuning
  option for later.

**Status.** For the directed study there is exactly one hosted installation, so none of
the sync is built. What is binding **now**: no hosted-only tables, no program column,
and nothing that makes the hosted schema differ from the gym box's.
