# Feature Spec 23: Syncing a local install with the remote server

- Previously spec 20, "data export and sync" (renumbered 2026-11-14; export split out as spec 19)
- Owner: Devin Walton
- Date: 2026-11-14
- Status: **Written, not scheduled.** Devin answered the open questions 2026-11-14; the
  remaining *proposed* points are smaller and can be settled when phases are cut. Business note: "full data export in every tier" is on the build-before-selling
  list (kept in the business repo).
- Depends on: [04 Hosting](../remote/04-hosting.md) (the remote server, `eactl`),
  [21 Locations](21-locations-and-concurrent-sessions.md) (a local install is one location of its
  school). Builds on the design already written in
  `docs/journal/core/remote/databases.md` ("Moving between a local install and the remote
  server", decided 2026-10-14, not built).

## Why

Two needs, one piece of work:

- **Export:** a school must always be able to take all of its data with it, in every plan.
  It's the promise that nobody is locked in, and it's how a coach gets a spreadsheet of
  everything without asking us.
- **Sync:** a school can run a local install in its gym and the remote server at the same
  time (training in the gym, athletes at home, the coach planning from anywhere). The two
  hold separate databases. **Live two-way sync is rejected** (two copies editing the same
  data puts it at risk; databases.md, spec 04). Instead a coach presses **Sync my data**
  when they want the two to catch up, in either direction.

Several rooms on the remote server are not this spec: one school, one database (spec 21).

## User stories

- As a school administrator, I want to download everything my school has recorded, in a
  form I can open in a spreadsheet, so we're never stuck with one vendor.
- As a coach at a school with a gym install and the remote server, I want one button that
  brings each side up to date with the other, so the gym's workouts show up online and the
  plans I made online show up in the gym.

## Decisions

From databases.md (2026-10-14), carried over:

- **The first sync is a copy.** Both sides have the same tables and each holds one program,
  so the whole of one side goes to the other; ids, timestamps and history arrive unchanged.
  Both sides must be on the same version first.
- **Right after the copy, the receiving side's ids move to a distant range** (each table's
  id counter jumps, to a trillion for example), so new rows on the two sides can never
  share an id. Part of the copy, so it can't be forgotten.
- **After that, add, don't overwrite.** Everything a workout makes is new rows. Syncing adds
  the other side's new rows, so two workouts recorded on two sides are both kept.
- **A shared record edited on both sides: the remote server wins** (the roster and plans
  are managed from anywhere).
- **Original timestamps travel with the data,** or every current max (and every prescribed
  weight, since plans store percentages) comes out wrong. Manual maxes and daily reports
  are carried as they are, never worked out again.

New (Devin, 2026-11-14):

- **One format for both.** The file Export produces is the file Sync sends. Build it once.
- **A sync button in the coach's settings,** both directions, never automatic.
- **Only finished sessions sync.** A session still running (or suspended, spec 21) stays
  behind and goes on the next sync once it has ended, so a sync never needs the whole
  program to be quiet.

## The file

The export file from [11 Export my data](19-data-export.md), exactly; Sync reads its machine-readable files and ignores the CSVs. What each kind of table does in a sync is in the table there ("How sync treats them").

## Sync

- **Who:** an administrator, from the coach's settings, on either side. **A local install is
  paired once with its school's remote server using a code** from the remote server, the way
  a sensor is added (Devin, 2026-11-14), so nobody else can send data into a school.
- **Two ways to carry it, one file** (Devin, 2026-11-14):
  - **Local ↔ remote: by file first.** Download the sync file on one side, upload it on the
    other (a laptop between them). Works on any network, including a school's that blocks
    outside connections. **Direct over the internet** comes after, for a local install that
    can reach the school's address.
  - **Remote ↔ remote: over the internet.** Moving a school from one remote server to
    another (for example onto its own dedicated cloud, the Elite plan) uses the same file
    sent directly between the two servers.
- **What a sync does, each direction:** the finished sessions the other side hasn't seen,
  with everything under them; the shared records changed since the last sync; maxes with
  their original times. Then it records how far it got, so the next sync starts there.
- **What it needs that the database doesn't have yet:**
  - **When each shared record last changed.** Only templates and per-athlete overrides
    record it today (`updated_at`); athletes, groups, programs, the catalog, calendar slots
    and the rest don't. A migration adds `updated_at` to each shared table.
  - **Deletions.** Most things are archived rather than deleted, which syncs as a change.
    What is truly deleted (a movement removed from a workout, a calendar slot) leaves a small
    "deleted" note so the other side removes it too.
  - **This install's sync id and its id range,** and per paired install, how far each
    direction has got (a `SyncPeer` record).
- **Several local installs** (a program with two gyms, each with its own box): each pairs
  with the remote server, never with each other. The remote server is the hub; every sync
  is still between two sides.
- **Logins:** each side keeps its own. Athletes' logins live on the remote server; a local
  install has none (spec 10: gym tablets need no login). **Coaches are matched by
  username** (Devin, 2026-11-14): a coach who exists on only one side is created on the
  other with no usable password, and sets one with the normal reset.
- **Locations (spec 21):** a local install is one location of its school. Its sessions
  arrive online at that location; the remote server's other locations' sessions are sent
  down only if the coach wants the gym to see them (*proposed:* yes, read-only history).

## Answered (Devin, 2026-11-14)

1. Coaches are matched by username; a missing one is created without a usable password.
2. Local ↔ remote: by file first, then direct over the internet. Remote ↔ remote (moving a
   school between servers): over the internet.
3. A local install pairs once with its remote server, using a code.
4. The export includes CSVs for people, as well as the files Sync reads.

## Phases (outline; cut properly when scheduled)

0. **What sync needs in the database:** `updated_at` on shared tables, deletion notes, the
   sync id, id ranges, `SyncPeer`.
1. **The first copy:** a fresh side from a file, the id range moved apart, both on the same
   version (refused otherwise).
2. **Sync by file, both directions:** finished sessions added, changed shared records with
   the remote server winning, maxes with their times; running sessions held back.
3. **Pairing and direct sync;** the button in the coach's settings, with what was sent and
   received; moving a school between remote servers over the internet.
4. **Rehearsal:** a gym install and the remote server each record a workout the same day;
   sync both ways; both workouts are on both sides, maxes and prescribed weights unchanged.

## Acceptance criteria

- [ ] Two workouts recorded on two sides the same day are both on both sides after a sync.
- [ ] A session still running isn't sent; it goes on the next sync after it ends.
- [ ] Every athlete's current max and prescribed weights are the same before and after a
      sync.
- [ ] A roster edit made on both sides comes out as the remote server's.
- [ ] Nothing syncs on its own; there is no live sync.

## Risks

| Risk | What reduces it |
|---|---|
| Two sides give two rows the same id | The id range moves apart as part of the first copy |
| A merge wrecks maxes and weights | Original timestamps travel; maxes are add-only; reports are carried, never recomputed |
| A roster edit made offline in the gym is lost | The remote server wins only a record edited on both sides; syncing before switching sides stays the normal habit |
| An export leaks logins | Logins and every secret are left out, tested |
| A sync file from somewhere else | Pairing; the file names the install that made it and the pair it belongs to |
