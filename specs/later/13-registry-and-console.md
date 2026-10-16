# Feature Spec 13: The registry of schools, and the operator's console

- Owner: Devin Walton
- Date: 2026-10-14
- Status: **After the class.** Written so the design is not lost; not scheduled, and not
  part of the Definition of Done
- Depends on: [12 Hosting](../remote/12-hosting.md) (its namespace labels and `eactl`)

## Why

A server runs many schools: one shared Postgres with a database per school, and the
rest of each school's app in its own namespace (spec 12). During the class, the
directory of schools is the labels on those namespaces, read by `eactl list`. That is
enough for two schools (the real one and the demo). It stops being enough once there
are schools to look after: an operator wants one place that lists every school with what
matters about it, and lets them drill into one to work on it.

## User story

As someone running Edge Athlete for many schools, I want one login that shows me every
school, its address, version, health and standing, and lets me open one school to work on
its installation, so that I never have to remember which school lives where.

## The design

### A registry database, beside the schools

Databases do not nest. The registry is **one more database in the same shared
Postgres**, `ea_registry`. It does not contain the schools; it describes them, one row
each:

| Field | Example |
|---|---|
| school | Lincoln HS |
| address | `lincoln.<domain>` |
| database, namespace | `school_lincoln`, `ea-lincoln` |
| status | active · suspended · archived |
| version | `v0.4.0` |
| contact, created, notes | … |

```text
Postgres (one server)
├── ea_registry        ← the directory: one row per school
├── school_lincoln     ← Lincoln's own data
└── school_demo        ← the demo's own data
```

This is the usual "catalog" pattern for one-database-per-customer apps.

### Drilling down means switching to a school, not reaching into it

Postgres cannot query across databases without add-ons, on purpose. The console reads a
school's row, then works on that school through its own database and namespace: its
health, logs, version, backup, restore, its administrator recovery. **No school's athletes
ever appear in the registry.**

### Two kinds of login, never mixed

- **A school's logins** (its administrator, coaches, athletes) sign in at that school's
  address and see only that school. Unchanged.
- **Operator logins** (EA staff) sign in to the console and see every school. They are
  stored in the registry, not in any school's database, and they are not school
  administrators.

### What the console does

| Action | What happens |
|---|---|
| List schools | the registry, with live health and version |
| Open a school | its detail page: health, version, logs, backups |
| Add a school | what `eactl new` does, from the console, and a registry row |
| Change a school's status | suspended: the school's app is scaled to zero and its address shows a notice; its data is untouched. Active again: scaled back up |
| Upgrade a school | set its version, through the same deploy path as CD |
| Back up, restore | the same as `eactl backup` / `restore` |
| First administrator | issue a setup code for a new school (spec 01), or recover an administrator |

### What carries over from the class

- Spec 12's namespace labels (`ea/installation`, address, version, `ea/status`) are the
  registry's first rows: a one-time import.
- `eactl` keeps working; the console calls the same steps.
- The installation's name on the sign-in card (reads "Coach workspace" today) is read from
  the registry by each school's app.

### A school picker, not central logins (Devin, 2026-10-16)

People don't type a school's address. They open **one public landing page**, find their
school, and are sent to it; they sign in **there**, on the school's own address, exactly
as today.

```text
landing page ─ search or scroll "Demo U" ─▶ remembered in this browser ─▶ demo-u-k7m2qx.<domain>
                                                                          └─ that school's own sign-in
```

- **Logins stay in each school's own database.** The landing page never sees a
  password, holds no accounts and has no database of its own. Nothing about sign-in,
  login links (specs 01, 03) or local installs changes.
- **The directory is public**: display name, city, state and address of every school,
  from this registry (or, before it exists, the namespace annotations `eactl list`
  reads). It holds no user data. Search and a scrollable list are both fine.
- **The choice is remembered in the browser** (IndexedDB or localStorage on the landing
  page), so the next visit goes straight to the school.
- **No install option on the landing page.** It has no web app manifest and offers
  nothing to install. The app is installed from the school's own address, after the
  first visit, so each installed app belongs to one school.
- **It's a new screen:** a mockup on the Final designs page first. Remote only.

## Phases (outline; to be cut properly when scheduled)

0. `ea_registry` and its import from the namespace labels; `eactl list` reads it.
1. The console, read-only: list and detail pages, operator sign-in.
2. Actions: add, suspend and reactivate, upgrade.
3. The installation's name on each school's sign-in card.
4. The school picker landing page.

## Non-goals

- Any one school's data in the registry.
- **Card or bank details, ever.** If schools are ever charged, a payment provider holds
  the payment details; nothing about it is designed in this repository.
- Moving schools between servers (a later spec, if there is ever a second server).

## Open questions for when it is scheduled

- Whether the console is part of the same Django codebase (a separate settings mode) or
  its own small app.
- Where operator logins live, and whether they use the same one-time login codes as
  coaches (spec 03 Phase 5).
