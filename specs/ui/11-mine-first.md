# Feature Spec 11: Mine first — a coach sees their own work first

- Owner: Devin Walton
- Date: 2026-10-06
- Status: Written — not started
- Form item: #11 (unified coach interface)
- Depends on: [02 Roles](../remote/02-roles.md) (a coach is a login with a coach profile),
  [06 Design rules](06-design-rules.md). Touches the screens of [07 Planning](07-planning.md)
  and [09 Analytics](09-analytics.md); build it after them or alongside
- Mockup: **approved 2026-10-07**, on the canvas's Final designs page ("The same in both:
  Planning"): `F_Groups` (the Mine | Everyone switch, coaches by name, the pencil),
  `F_CoachesEditor` (the pencil pressed), `F_NewCoachEveryone` (a coach on no group).
  Also in [`mockups/coach-ui-final.html`](mockups/coach-ui-final.html)

## Why

Every coach sees every group, program, session and athlete. That is deliberate and it
stays: one coach role, nothing fenced. But in a department with several coaches it
means each of them scrolls past everyone else's work to reach their own, and nothing on
screen says who is in charge of a group or a session.

Most of what is needed is already stored and unused:

- A training group records its coaches, each as **head** or **assistant**
  (`TrainingGroupCoach`). Whoever creates a group becomes its head. A route to add and
  remove coaches exists (`training-groups/{id}/coaches/`). **No screen calls it**, so
  every group has exactly one coach and it cannot be changed.
- Training blocks already have a "show mine" lens (`GET /api/training-blocks/?coach=me`).
  The code calls it "a lens, not a fence". **No screen calls that either.**
- The login table already has first-name and last-name columns. **Nothing fills them**,
  so every screen that names a coach shows a username.

## User story

As a coach, I want the groups, programs, sessions and athletes I am responsible for to
come first, and to see who is in charge of anything I am looking at, so that I can find
my own work at a glance and still reach everyone else's in one press.

## Decisions this spec locks in

Decided with Devin on 2026-10-06.

- **A lens, never a fence.** Nothing here refuses anybody anything. "Everyone" is always
  one press away, a link to something that is not yours opens normally, and the server
  never answers `403` because of whose it is.
- **Lists default to Mine.** If a coach is on no group yet, the list opens on Everyone
  instead, so a new coach never lands on an empty screen. The choice is remembered on
  that device.
- **A coach's things are derived, not stored.** Nothing new is written to the database
  for it. The chain is:

  | Thing | It is "mine" when |
  |---|---|
  | Training group | I am on it, as head or assistant |
  | Training program | it belongs to one of my groups |
  | Calendar day | it belongs to one of those programs |
  | Training session | one of those programs is on it |
  | Quick Training Session (no program) | an athlete on it is in one of my groups |
  | Athlete | they are in one of my groups |
  | Training block | I created it (already built) |

- **A session's coaches come from its programs' groups.** No "started by" field. For a
  Quick Training Session they come from the groups its athletes are in; if that gives
  several coaches, all are shown.
- **Coaches are attached to the group, not the program.** The group is where head and
  assistant already live. A program belongs to one group and inherits its coaches, so
  a new program for the same group needs nothing assigned.
- **A group has at most one head and any number of assistants.** Making someone head
  moves the previous head to assistant (the route already does this). A group may have
  no coaches at all; then it is nobody's and shows only under Everyone.
- **A coach who leaves is deactivated, never deleted, and their groups are tidied up
  when that happens** (Devin, 2026-10-06):
  - deactivating an **assistant** takes them off their groups automatically;
  - deactivating a **head coach** is refused, with a message naming the groups and
    saying to hand them over first.

  The database's own refusal to delete a login that is on a group is left as it is. It
  only matters if a login is deleted by hand, which the app never does.
- **Any coach may edit a group's coaches.** It is a label, not a permission, so it
  follows the one-coach-role rule.
- **People are shown by name.** First and last name, falling back to the username when
  no name has been entered.

### A side effect to know about

Because a session's coaches are derived, they are the group's coaches **now**. Change a
group's coaches next month and last month's sessions show the new names. The saved
daily report is the exception: it is frozen when the day ends, so the coach names are
written into it at that moment and stay true to the day.

## What exists today

Checked against the code on 2026-10-06.

- `TrainingGroupCoach(training_group, coach, role)`, one row per coach per group;
  deleting a login that is on a group is refused.
- `GET|POST|DELETE training-groups/{id}/coaches/`: lists, adds or changes, removes.
  **It accepts any login id** (`User.objects.filter(id=…)`), which is wrong once
  athletes have logins.
- `TrainingGroupSerializer` returns `coaches` and `head_coach`; `coach_name` is the
  **username**.
- `TrainingBlock.coach` and the `?coach=me` / `?coach=<id>` lens on
  `GET /api/training-blocks/`.
- `GET /api/coaches/` is administrators only (spec 01). There is no list of coaches a
  regular coach can read.
- `TrainingSession` has no coach field. `SessionParticipation` ties a session to a
  program; a program has one `training_group`.
- `react/src/coach/GroupsView.jsx` shows a group's coaches in one line (`coachLine`).

## Scope

- Coach names: collected, editable, and shown wherever a coach is named.
- A small list of coaches that any coach can read, for the picker.
- The "mine" lens on groups, programs, calendar days, sessions and athletes.
- Each of those naming its coaches.
- An editor for a group's coaches.
- A Mine | Everyone switch on the lists.

## Non-goals

- Any restriction on what a coach may see or do.
- Coaches on a program or a session directly.
- Notifying a coach about their groups.
- Profile pictures. The avatar stays the generic one.

---

## Phase 0 — Names, and who can be picked

Backend, plus three small forms.

- `display_name(user)`: "First Last" when either is set, else the username. One
  function, used by every serializer that names a coach. `coach_name` in
  `TrainingGroupCoachSerializer`, `head_coach`, the block's creator and the Coaches
  page all go through it.
- `GET /api/auth/me/` gains `first_name`, `last_name`, `name`.
  `PATCH /api/auth/me/` `{first_name, last_name}` lets a coach set their own.
- **Where a name is asked for:** first-run setup (the first administrator), and where a
  coach's login is made (spec 01's Add coach today; the login-code page once spec 03
  Phase 5 lands). The account menu gains **Your name**.
- `GET /api/coaches/directory/` — any coach. Active coach logins only, as
  `[{id, name}]`, sorted by name. No usernames beyond the fallback, no status, no flags.
- **Guard on the group-coaches route:** the `coach` it is given must be an active login
  with a coach profile. Anything else is `400`, never silently accepted.

- **Deactivating a coach** (`PATCH /api/coaches/{id}/` with `is_active: false`, spec
  01): if they are head of any group, refuse with `409` and the group names ("Maria
  Reyes is head coach of Varsity Football and Receivers. Hand those groups to another
  coach first."). Otherwise remove their assistant rows in the same transaction.
  Reactivating does not put them back on anything.

**Done when:**

- [ ] Deactivating an assistant removes them from every group they assisted, and
      nothing else about those groups changes.
- [ ] Deactivating a head coach is refused, names every group they head, and changes
      nothing; once those groups have another head, it succeeds.
- [ ] Reactivating a coach leaves them on no group.
- [ ] A login with a name is shown by it everywhere a coach is named; one without is
      shown by username.
- [ ] A coach can change their own name and nobody else's.
- [ ] `directory` answers a regular coach, lists only active coaches, and reveals
      nothing but an id and a name. No login, and an athlete login, are refused.
- [ ] Adding an athlete's login, a deactivated coach, or an unknown id to a group is
      refused with `400` and changes nothing.
- [ ] *(Browser)* First-run setup and Add coach ask for a name; the account menu shows
      it and lets it be edited.

**Stop. Devin reviews.**

## Phase 1 — The lens, on the server

Backend. One module, `services/coach_scope.py`, opening with a plain-language comment
on why "mine" is worked out and never stored.

- `groups_of(coach)` → the groups they are on.
- `coaches_of_session(session)` → the coaches of the groups of the session's programs;
  for a session with no program, of the groups its athletes are in. Head first, then
  assistants, each coach once.
- **The lens uses the convention blocks already have:** `?coach=me` (and `?coach=<id>`)
  on `GET training-groups/`, the training-programs list, `scheduled-sessions/`, the
  sessions list and `athletes/`. Without it every route answers exactly as today.
- Every item on those lists carries `mine` (true or false for the caller) and
  `coaches: [{id, name, role}]`, so a screen can sort mine-first and name the people in
  charge without another request.
- **Fixed number of queries per list**, however long it is.
- When a day ends, the daily report's frozen snapshot records the session's coach
  names as they were.

**Done when:**

- [ ] For a coach on group A and not B: `?coach=me` returns A's group, programs,
      calendar days, sessions and athletes, and none of B's; without it, both.
- [ ] A head and an assistant of the same group get the same "mine".
- [ ] An athlete in A and B is "mine" to a coach of either.
- [ ] A shared session (programs from A and B) is "mine" to coaches of both, and lists
      both sets of coaches, each person once, head first.
- [ ] A Quick Training Session with no program is "mine" to a coach of any group one of
      its athletes is in; with athletes in no group it is nobody's.
- [ ] A group with no coaches is in nobody's "mine" and in everybody's unfiltered list.
- [ ] `?coach=me` never produces `403` or `404` for something that exists; opening any
      item directly works for every coach.
- [ ] A finished session's report keeps the coach names it was frozen with after the
      group's coaches change.
- [ ] Each list makes the same number of queries with 5 items and with 500.
- [ ] Every response is byte-for-byte unchanged when `?coach` is not sent, apart from
      the two added fields.

**Stop. Devin reviews.**

## Phase 2 — Editing a group's coaches

Frontend. A small pencil beside the coaches line on a group (Devin: "a small button or
pencil next to where we display the coaches"). It opens an editor in place:

- the group's coaches as rows: name, **Head** or **Assistant**, and quiet actions
  **Make head** and **Remove**;
- **Add a coach**: a picker of the coaches from `directory` who are not on the group
  yet, added as an assistant;
- **Make head** on an assistant moves the current head to assistant, in one step, and
  says so in the row before it is pressed ("replaces Maria Reyes as head");
- removing the last coach is allowed and asks first: "Nobody will be in charge of
  Varsity Football. It will still appear under Everyone."

This is how a group is handed from its creator to someone else: add the new coach,
make them head, remove the old one.

The same names show, read-only, on the group's programs and on a session.

**Done when:**

- [ ] *(Frontend test)* Add, remove and make-head each call the existing route and the
      row updates from the server's answer.
- [ ] *(Frontend test)* The picker never offers someone already on the group.
- [ ] *(Browser)* Hand a group from its creator to another coach in three presses; the
      new coach now finds it under Mine and the old one under Everyone.
- [ ] *(Browser)* A group ends up with one head and two assistants, all shown by name.
- [ ] *(Browser)* A regular coach, not only an administrator, can do all of it.

**Stop. Devin reviews.**

## Phase 3 — Mine | Everyone on the lists

Frontend. One switch, the same two-option control as the calendar's List | Month
(spec 06 rule 9), with **Mine** and **Everyone**.

| Screen | With Mine chosen |
|---|---|
| Planning › Groups | my groups |
| Planning › Roster | athletes in my groups; the group filter chips show my groups first |
| Planning › Design | programs of my groups; training blocks I created |
| Planning › Calendar | calendar days of my groups' programs, in both List and Month |
| Analytics pickers | my athletes and groups listed first, the rest under a divider |
| Session | not filtered: the room is the room. It names the session's coaches |

- **Default Mine.** If the coach is on no group, the switch starts on Everyone and a
  line says why: "You are not on any training group yet, so this shows everyone's."
- The choice is one setting for the whole workspace on that device, not one per tab.
- Under Mine, an empty list says so and offers the way out: "None of your groups has a
  program yet. **Show everyone's**".
- Each row names its coaches in one quiet line, head first.

**Done when:**

- [ ] *(Frontend test)* Each listed screen requests `?coach=me` under Mine and no
      `coach` parameter under Everyone.
- [ ] *(Frontend test)* A coach on no group starts on Everyone with the explaining line.
- [ ] *(Frontend test)* The choice survives a reload and applies to every tab.
- [ ] *(Browser)* Two coaches on different groups each open Planning and see their own
      group first; one press on Everyone shows both.
- [ ] *(Browser)* A link to another coach's group, program or athlete opens normally
      while Mine is chosen.
- [ ] *(Browser)* SESSION shows every rack whatever the switch says.

**Stop. Devin reviews.**

---

## Acceptance criteria

- [ ] A coach's own groups, programs, sessions and athletes come first by default.
- [ ] Everything else is one press away, and nothing is ever refused because of whose
      it is.
- [ ] Anywhere a group, program or session is shown, so is who is in charge, by name.
- [ ] A group can be handed to another coach without touching the database by hand.
- [ ] Nothing new is stored to work out what is "mine".

## Risks

| Risk | What reduces it |
|---|---|
| The lens gets mistaken for a permission and something starts refusing | Phase 1 tests that it never produces `403`/`404`; the rule is the first decision in this spec |
| A new coach opens every screen empty and thinks the app is broken | Start on Everyone when they are on no group, and say why |
| Deriving coaches for a long list is slow | Fixed query count, tested at 5 and 500 items |
| Old sessions appear to have been run by whoever coaches the group today | The frozen daily report keeps the names of the day; live screens say "coaches of this group" |
| An athlete's login gets added as a group's coach | Phase 0 guard on the route, and the picker only lists coaches |

## Docs to update when done

`docs/journal/database.md` (why "mine" is derived and coaches hang off the group),
`docs/journal/coach-tablet.md` (lens, not fence), and the route table.
