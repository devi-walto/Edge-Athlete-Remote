# Feature Spec 19: Export my data

- Owner: Devin Walton
- Date: 2026-11-14
- Previously part of spec 20 (data export and sync), split out 2026-11-14 so export can come before sync
- Status: Specced, 1 phase. After the coach redesign (Devin, 2026-11-14). "Full data export in every tier" is on the build-before-selling list (business repo)
- Depends on: nothing new. [23 Sync](23-sync.md) reads the same file

## Why

A school must always be able to take all of its data with it, in every plan. It's the promise that nobody is locked in, and it's how a coach gets a spreadsheet of everything without asking us. **One format:** the file Export makes is the file Sync sends (spec 23), so it's built once.

## The export file

A zip, so a coach can open it:

- `manifest.json`: format version, the schema version (the last migration), the
  installation's name, when it was made, which install made it (its sync id, below), and
  the counts per table.
- **One JSON Lines file per table** (`athletes.jsonl`, `sets.jsonl`, …): every row with its
  original id, foreign keys and timestamps, exactly as stored. This is what Sync reads.
- **One CSV per table people care about** (Devin, 2026-11-14: yes; a coach checking "can I
  really get my data out?" opens the spreadsheet) (athletes, sessions, sets, reps, maxes, programs,
  reports), with names in place of ids where that helps a spreadsheet ("Riley Brooks",
  "Back Squat"). For people; Sync ignores them.
- **What is never in it:** passwords and their hashes, sign-in tokens, sensor logins and
  claim codes, the common login's sealed password, login links, the setup code. Logins are
  each install's own (below).
- **Who may make one:** an administrator, from the coach's settings ("Export my data");
  also `eactl export "School"` for us. Big programs: made in the background and offered as
  a download when ready (*proposed*), not held open in one page request.

What goes in, by kind of table (from `models.py`, 2026-11-14):

| Kind | Tables | In the export | How sync treats them |
|---|---|---|---|
| **Recorded** (a workout makes them; never edited after) | sessions, who took part, sets, reps, check-ins, daily reports, maxes | yes | added; a finished session and everything under it travel together |
| **Shared records** (edited over time) | athletes, groups and their coaches, the movement catalog, tags, categories, templates, programs and their workouts and movements, calendar slots, per-athlete overrides, locations | yes | changed ones are sent; the remote server wins a conflict |
| **Each install's own** | logins, coach profiles, the common login and its devices, password records, one-time codes, the setup record, rack tablets, live rack state, command receipts, live-update events | no | never synced |
| **Sensors** | sensor records (`Node`) | yes (for the record) | *proposed:* not synced: a gym's sensors and an athlete's own are each install's |

## Phase 0 — The export file

the format, every table in its place, the CSVs, what's left out;
   "Export my data" for an administrator, `eactl export`. Round trip: an export imported into
   an empty install gives the same school.

**Done when:**

- [ ] An administrator can download everything the school has recorded, in every plan, with no passwords or secrets in it.
- [ ] An export imported into an empty install gives the same school.

**Stop. Devin reviews.**
