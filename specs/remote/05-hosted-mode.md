# Feature Spec 5: Hosted mode

- Owner: Devin Walton
- Date: 2026-10-06
- Status: In progress — Phase 0 done (branch `feature-deployment_switch`). Phase 1 (CI) added 2026-10-14; the old Phases 1–3 are now 2–4
- Form item: Definition of Done #3
- Depends on: [02 Roles](02-roles.md)
- **Build this before 03 and 04**, which both need its switch

## Why

On a gym box the network is the lock: only devices on the box's own Wi-Fi can connect,
so 21 endpoints are open to anyone and a rack tablet needs no login. `docs/journal/apis.md`
records that trade and says it must be revisited "if this ever runs on a network that
is not private". A hosted installation is that network.

The gym box must keep working exactly as it does. So the same endpoints need two
behaviours, chosen by one setting, with both tested.

## User story

As the person running a hosted installation, I want everything a stranger could reach
to require a login, without changing how a rack tablet works in a gym.

## Decisions this spec locks in

- **One setting decides.** `EA_DEPLOYMENT`, read from the environment: `local` (the
  default) or `remote`. Nothing else in the code asks "am I on the internet?".
- **The two values are `local` and `remote`** (Devin, 2026-10-06). In these specs and the
  docs, "gym box" means an installation running as `local`, and "hosted" means one
  running as `remote`. The words describe where it runs; the setting is what the code reads.
- **Not two copies of the routes.** Each open endpoint gets a permission class that
  asks the setting. Same view, same URL.
- **The default is the gym box.** A missing or misspelled value must not open a hosted
  installation by accident — so an unknown value **refuses to start**, and the hosted
  manifests set it explicitly.
- **One codebase, always** (Devin, 2026-10-14). Every difference between a gym box and a
  hosted installation (HTTP or HTTPS, `ws` or `wss`, which routes are open, which browser
  workarounds apply) is chosen at run time from this setting or from how the page was
  served. Never a second build, a fork of a file, or a hosted-only copy of a screen. The
  specs that add a hosted behaviour (12 for HTTPS and `wss`, 03 and 04 for athletes) key
  it off this switch.
- **The frontend is told, it does not guess.** One small endpoint reports the mode, and
  remote-only controls key off it.

## The 21 open endpoints, and what each becomes when hosted

| Endpoint (view name) | Gym box | Hosted |
|---|---|---|
| `rack_register`, `rack_racknumber` | open | **refused** — hosted racks are created by joining a session (spec 04) |
| `rack_state`, `rack_sensor_health` | open | coach, or the athlete whose rack it is |
| `rack_controller_acquire`, `_heartbeat`, `_release` | open | coach, or the athlete whose rack it is |
| `rack_checkin`, `rack_checkins` | open | coach, or the athlete whose rack it is; an athlete can only check **themselves** in |
| `rack_nfc_tap` | open | **refused** — no shared rack to tap at |
| `set_create`, `set_complete` | open | coach, or an athlete creating/completing **their own** set on **their own** rack |
| `athlete_progress` | open | coach, or that athlete |
| `prescriptions_view` | open | coach, or an athlete (their own only) |
| `exercises_list` | open | any signed-in role |
| `sessions_active`, `session_status` | open | any signed-in role |
| `athletes_view` (`GET` lists every athlete; `POST` creates one) | open | **coach only** — it is a list of names, many of them minors |
| `nodes_list`, `node_register` | open | coach only (per-sensor credentials are the sensors work) |
| `room_state` | open | coach only |

"The athlete whose rack it is" is answered by spec 04, which records which athlete a
hosted rack was created for. Until spec 04 lands, **an athlete is refused** on those
rows and only a coach passes; that is safe and lets this spec ship first.

## Scope

- The setting, its validation, and a startup failure on an unknown value.
- A permission class, `OpenOnLocal`, plus the per-endpoint hosted rule from the table.
- `GET /api/system/info/` reporting the mode (open; it reveals nothing else).
- Hosted-only refusals: the connection-test page, the demo login (already refused
  outside development by spec 01), the NFC tap route.
- Hosts, CORS and CSRF trusted origins read from the environment for hosted.
- Rate limits on sign-in for hosted.

## Non-goals

- TLS, certificates, the cluster (hosting work).
- Broker logins for browsers and sensors (sensors work).
- Which athlete owns which rack (spec 04).

---

## Phase 0 — The setting

- `settings.py` reads `EA_DEPLOYMENT`; allowed values `local`, `remote`; default
  `local`. Any other value raises at startup with a message naming the allowed values.
- `deployment.py` (new) with `is_hosted()` — the one place that reads the setting.
- `GET /api/system/info/` → `{"deployment": "local" | "remote", "version": "..."}`.
- `.env.example` documents the variable.

**Done when:**

- [x] With the variable unset, the app starts as `local` and every existing test passes.
- [x] `EA_DEPLOYMENT=remote` starts; `EA_DEPLOYMENT=cloud` fails to start with a clear error.
- [x] `/api/system/info/` returns the mode in both, with no login.

**Result, 2026-10-07.** Suite 536 → 545. Started for real three ways: unset → `local`,
`remote` → `remote`, `cloud` → refuses with a message naming the two allowed values.
The value is parsed in `basestation_config/deployment_mode.py` (so `settings.py` can use
it while Django starts) and read by the app only through `event_handler/deployment.py`.
`version` comes from an `EA_VERSION` environment variable and says `dev` when unset;
nothing sets it yet, which is the release and hosting work.

**Stop. Devin reviews.**

## Phase 1 — Tests on every pull request (CI)

Added 2026-10-14. CI lives here because Phase 2 needs the suite run in both modes on
every change, and because this spec's own pull request is the project's **first manual
approval**: from here on, work reaches `SprintBranch` only through a pull request whose
checks pass and which Devin merges (see "Branches" in `specs/README.md`). Deploys on
version tags are the other half of CI/CD and live in [spec 12](12-hosting.md).

- `.github/workflows/ci.yml` (new), opening with a plain-language comment on why it
  exists. Runs **on pull requests into `SprintBranch` and `main`**, not on every push
  (Devin, 2026-10-14), and can be started by hand.
- **On GitHub's own runners** while the repo is public: free, and a stranger's pull
  request never reaches a machine in the house (spec 12 explains the runners).
- Jobs:
  - **backend**, twice — once with `EA_DEPLOYMENT=local`, once with `remote`: build the
    django image from its Dockerfile (which also proves the image builds), start a
    throwaway Postgres and Mosquitto beside it on their own network with the names the
    app expects (`postgres`, `mosquitto`), run the suite and the migration drift check
    inside the image. The same way the suite is run by hand today.
  - **frontend**: the frontend suite and the production build, on the Node version the
    react Dockerfile uses; and the react image builds.
  - **docs**: the docs build, warnings fatal.
- The settings each leg runs with are files in the repo (`ci/local.env`,
  `ci/remote.env`), with throwaway values only. When Phase 3 makes `remote` refuse
  `DEBUG` and empty hosts, the remote file already sets them correctly.
- **The rules on GitHub, after the first green run** (a check can only be required once
  it has run once). Devin turns them on by hand, guided; they are account settings:
  - `SprintBranch` and `main`: changes only through a pull request; the backend (both
    legs), frontend and docs checks must pass; no force pushes; no deleting.
  - **Merging is the approval.** GitHub does not let anyone approve their own pull
    request, and every pull request here is opened under Devin's account, so "one
    approval required" would block every merge. Only Devin can merge.

**Done when:**

- [ ] Opening this spec's pull request runs all four checks, and each passes.
- [ ] A throwaway pull request with a deliberately failing test shows red and **cannot
      be merged**. Closed afterwards, never merged.
- [ ] The two backend legs show up as separate checks, named for their mode.
- [ ] A push to a branch with no pull request starts nothing.
- [ ] *(By hand)* The branch rules are on for `SprintBranch` and `main`, and a direct
      push to either is refused.
- [ ] The time one full run takes is written down (it matters once the repo is private
      and minutes are counted).

**Stop. Devin reviews.**

## Phase 2 — The 21 endpoints

- `OpenOnLocal(remote=<rule>)`: on a gym box, allow. Hosted, apply the rule from the
  table (`coach`, `any_role`, `coach_or_owner`, `refuse`).
- Replace `AllowAny` on all 21 views. No view logic changes.
- Ownership checks for `coach_or_owner` are stubs that refuse athletes until spec 04.

**Done when:**

- [ ] **A test walks every route that uses `OpenOnLocal`, in both modes.** Gym box: no
      login is needed (today's behaviour, byte for byte). Hosted: no login gets `401`
      on every one.
- [ ] A test fails if any view still uses `AllowAny` other than sign-in, the setup
      routes from spec 01, and `/api/system/info/`. New open routes have to be added to
      that short allow-list on purpose.
- [ ] Hosted: a coach passes every row marked coach; an athlete gets `403` on
      `athletes_view`, `nodes_list`, `node_register`, `room_state`.
- [ ] Hosted: `rack_register`, `rack_racknumber` and `rack_nfc_tap` return `403` for everyone.
- [ ] The full suite passes in **both** modes (Phase 1's CI runs it twice on every pull request).

**Stop. Devin reviews.**

## Phase 3 — Hosted hardening

- `ALLOWED_HOSTS`, CORS origins and CSRF trusted origins come from the environment when
  hosted, and startup fails if they are empty.
- `DEBUG` on with `remote` refuses to start.
- Behind the cluster's HTTPS front door, Django learns the request was secure from the
  proxy's header (`SECURE_PROXY_SSL_HEADER`), and its session and CSRF cookies are
  marked secure, **when hosted only**. A gym box stays on plain HTTP with nothing
  changed.
- Sign-in is rate-limited when hosted (DRF throttling; a small number per minute per address).
- The frontend's connection-test page (`/connection-test`) renders a "not available"
  notice when the mode is hosted. It is the one screen that publishes to the broker.

**Done when:**

- [ ] `remote` with `DEBUG=True`, or with empty hosts, fails to start.
- [ ] Hosted: a request marked secure by the proxy is treated as HTTPS, and cookies carry
      the secure flag. Gym box: no change (the existing suite proves it).
- [ ] Repeated wrong sign-ins get `429` when hosted, and are unlimited on a gym box.
- [ ] *(Frontend test)* The connection-test page shows the notice in hosted mode.

**Stop. Devin reviews.**

## Phase 4 — The frontend learns the mode

- A small hook, `useDeployment()`, fetches `/api/system/info/` once and caches it.
- Nothing visible changes yet. Specs 03, 04 and 07 use the hook to show remote-only
  controls: login-link status, sensor ownership, the session link.

**Done when:**

- [ ] *(Frontend test)* The hook returns the mode and does not refetch on every render.
- [ ] *(Browser)* The gym-box app looks and works exactly as before.

---

## Acceptance criteria

- [ ] A gym box behaves exactly as it did, with no login at the rack.
- [ ] Hosted, nothing answers without a login except sign-in, first-run setup and
      `/api/system/info/`.
- [ ] Hosted, no endpoint returns a list of athlete names to anyone but a coach.
- [ ] A mis-set or missing configuration cannot produce an open hosted installation.
- [ ] Both modes are tested on every change.

## Risks

| Risk | What reduces it |
|---|---|
| A new endpoint is added open and nobody notices it is open when hosted | The allow-list test in Phase 2 |
| The gym box regresses because tests only ran in one mode | CI runs the suite in both modes |
| A rack tablet in the gym is suddenly asked to log in | Phase 2's gym-box walk asserts no login is needed on all 21 |

## Docs to update when done

`docs/journal/apis.md` — *The permission rule* (the "15 routes open" count there is
already stale; it is 21). `docs/remote/access.md` — "the open routes behave differently
in the two shapes" becomes a description of `EA_DEPLOYMENT`. Regenerate the route table
with `docs/refresh-routes.py`.
