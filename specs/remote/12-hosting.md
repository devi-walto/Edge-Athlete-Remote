# Feature Spec 12: Hosting on k3s, with CD

- Owner: Devin Walton
- Date: 2026-10-14
- Status: In progress — Phase 0 done (branch `feature-hosting`)
- Form items: Definition of Done #1 (k3s, public HTTPS, automatic certificates, CI/CD) and
  #5 (a separate demo installation from the same template). Feeds #7 (end to end) and #8
  (docs on deploying to k3s)
- Depends on: [05 Hosted mode](05-hosted-mode.md). Phases 0–3 need only spec 05's CI phase;
  **Phase 4 (going public) needs all of spec 05.** Runs alongside specs 03 and 04
- Branch: `feature-hosting`
- Design it builds: `docs/remote/hosting.md`, `docs/remote/databases.md`,
  `docs/remote/deployments.md`

## Why

The app runs today as one Docker Compose stack on a box in a gym. The remote version
runs the **same images** on a k3s cluster at home, at a public HTTPS address. A practice
cluster already exists on the Dell (October 8–14): k3s, Traefik, cert-manager with
Let's Encrypt, a DNS updater, a Postgres whose data survives its pod, and Tailscale for
management. What does not exist yet is the real app on it, and a way to rebuild all of
it without the person who built it.

### The rule this spec is judged by

**A fresh Linux machine, one bootstrap command, the repo, and a backup are enough to
bring the whole service back** — the way you would stand it up on a new AWS or Azure
machine when this grows (Devin, 2026-10-14: "this has driven most of my decisions").

So:

- **Only the very first step is a script.** Installing k3s and Tailscale on a bare
  machine is a script you run once. Everything after it is files in the repo that
  describe the end state, applied by a tool. Nothing is done to the Dell by hand that
  is not also in the repo.
- **Secrets are the one thing not in the repo** (it is public). Restoring them is a
  written, rehearsed step of the bootstrap, not something to remember.
- **The proof is a rehearsal on a blank machine**, not a claim (Phase 7).

## User story

As the person running Edge Athlete, I want to tag a version and have it running at a
public HTTPS address a few minutes later, and I want to be able to rebuild the whole
service on a new machine from the repo, so that hosting does not depend on one box or
on my memory.

## Decisions this spec locks in

- **Build on what is already running** (Devin, 2026-10-14). The Dell's plumbing works:
  Traefik, cert-manager, the two certificate issuers, the DNS updater, the hairpin fix,
  Tailscale. It stays as it is. The work is the app's manifests and the image registry,
  and then the app drops in on top. The plumbing is **brought into the repo**, and
  **working on any new machine without hand edits beats matching the Dell exactly**
  (Devin, 2026-10-14): a fixed address becomes a name, `latest` becomes a pinned
  version, one subdomain becomes a list. Every such change is shown and proven before it
  replaces the Dell's version.
- **One node: the Dell**, Ubuntu Server LTS. A Mac mini was planned as a second node and
  cut on 2026-10-14; it was never in the Definition of Done. Nothing assumes one node,
  so adding one later stays possible.
- **The Dockerfiles do not change.** A `k8s/` folder in the repo replaces
  `docker-compose.yml` for the cluster: one subfolder per service. **Kubernetes never
  builds images**; it runs images that already exist in a registry.
- **One template, one variation per installation** (Kustomize: a shared base, one
  overlay per installation). The real installation and the demo differ only in their
  overlay: namespace, address, settings. Chosen over Helm because it is plain Kubernetes
  files, which fits "apply the repo".
- **One server, many schools** (Devin, 2026-10-14). A *server* is one machine running
  the cluster (today, the Dell). Setting one up happens once (`eactl init`). A new
  school is a new **installation on an existing server**; it never gets a server of its
  own. This differs from local on purpose: each gym box is a standalone device, so every
  local install is its own server.
- **One shared Postgres, one database per school** (option B, Devin, 2026-10-14).
  Postgres is the database *server* (one running program); a *database* is one separate,
  named set of tables inside it. The server runs **one** Postgres, in the shared
  namespace `edge-athlete`; each school gets **its own database** in it, with its own
  database login that can open only that database. So a school's app still cannot see
  another school's data, and one Postgres uses far less of the Dell's memory than one per
  school, with one backup job. The cost: if that Postgres is down, every school is.
- **A school is found by a fixed short name, never by its display name** (Devin,
  2026-10-16). Schools nationwide can share a name, so each one gets:

  | | Example | Rules |
  |---|---|---|
  | **Display name** | Demo U | any text; shown to people; can change |
  | **Short name** | `demo-u-k7m2qx` | the name, lowercased and cut to about 20 characters, plus 6 random letters and digits; **never changes**, even if the school renames; tab-completes in `eactl` |
  | Namespace | `ea-demo-u-k7m2qx` | from the short name |
  | Database and its login | `school_demo_u_k7m2qx` | from the short name (`_`, which Postgres prefers) |
  | Address | `demo-u-k7m2qx.<domain>` | from the short name; clicked, never typed |

  People never type a school's address: they follow a login link, or (after the class)
  pick their school on a public landing page that sends them to it (spec 13).
  `eactl find <text>` searches display names.
- **Everything else a school runs is its own**, in its own namespace `ea-<short name>`:
  Django, the two workers, the broker, the screens, one ConfigMap and one Secret
  (mirroring today's `.env`), and a copy of the image pull key.
- **A directory of schools, from day one.** `eactl new` labels each school's namespace
  (`ea/school=<short name>`, `ea/version`, `ea/status=active`) and annotates it with
  what labels can't hold (`ea/display-name`, which may contain spaces, and
  `ea/address`). `eactl list` reads them; `eactl status <short name>` drills into one. The full
  directory (a registry database and a web console) is after the class:
  [spec 13](../later/13-registry-and-console.md).
- **Server settings are asked once and kept out of the repo.** `eactl init` asks for the
  domain, the email for certificate warnings and similar server-wide answers, and saves
  them to `eactl.env` on the laptop, which git ignores. The repo's files use
  placeholders (`${DOMAIN}`, `${ACME_EMAIL}`) that `eactl` fills in when applying. A new
  school's display name is given to `eactl new`; everything else is made from it.
- **Images live in GitHub's container registry** (`ghcr.io`), **private**, even while the
  repo is public. The cluster pulls with a read-only token stored as a Secret.
- **Tests run on pull requests; deploys run on version tags.** A tag like `v0.4.0` (patch
  tags too) builds the images, labels them with that version, and rolls that version out.
  Devin cuts releases by hand when he chooses; every two weeks is the long-term habit.
  Rolling back means deploying the previous tag. A release moves `main` forward to match
  `SprintBranch` (no pull request: that work was already reviewed) and tags it.
- **Runners:** while the repo is public, tests and builds run on GitHub's own machines
  (free, and a stranger's pull request cannot reach the house). A runner on the Dell
  does **deploys only**, fired only by version tags. **After the repo goes private, CI
  may move onto the Dell** to save build minutes.
- **Traefik**, bundled with k3s, is the ingress. **cert-manager is pinned to a version**
  in the repo, not "latest".
- **Managed from Devin's laptop over Tailscale.** The cluster's control port (6443) and
  SSH (22) are never forwarded. Only 80, 443 and later 8883 are.
- **Operator commands are a thin wrapper**, `eactl`, a bash script that **runs on the
  server**: SSH in, then type `eactl` (Devin, 2026-10-14; like the gym box's `ea-*`, and
  the deploy runner on the server can call the same commands). Named apart from the two
  existing `ea.sh` files, which already mean different things on different devices.
  Each command is a few lines over `kubectl` and prints the command before running it.
- **The public docs describe the setup in general terms.** No domain, home address or
  router details in the repo or on the docs site.

## What exists

- **On the Dell (practice, outside the repo):** k3s v1.36.5; `~/k3s-practice/` (nginx
  practice site, Postgres with a 300Mi volume, ClusterIssuers for Let's Encrypt staging
  and production); `~/k3s-addons/` (cert-manager "latest", a `coredns-custom` entry for
  the NAT hairpin, a DDNS CronJob calling the DNS provider's API). A test subdomain is
  live over HTTPS with a trusted certificate. Router forwards 80 and 443 to the Dell.
- **In the repo:** `django/Dockerfile` (start command: `migrate && recover_racks &&
  gunicorn`), `react/Dockerfile` (static build served by nginx), `docker-compose.yml`
  (postgres 15, mosquitto, django, mqtt-listener, monitoring-publisher, react, nginx; a
  `seed` profile), `nginx/nginx.conf` (`/api/auth/` rate-limited, `/api/`, `/admin/`,
  static admin and DRF files → django; `/` → react), `mosquitto/mosquitto.conf`
  (anonymous listeners on 1883 and 9001/WebSockets).
- **After spec 05:** `EA_DEPLOYMENT=local|remote`, `/api/system/info/` (reports the mode
  and an `EA_VERSION` build label), hosted refusals, and a CI workflow on pull requests.

## Lessons from the practice cluster (do not relearn)

- A typo in an annotation fails silently (`cluster-ssuer`). Check with `kubectl get … -o
  yaml` and the controller's logs.
- **Every new public subdomain needs two lines:** one in the `coredns-custom` block (or
  its certificate sticks at "self check", because requests from inside the cluster to the
  public address time out), and one in the DDNS job's list.
- The old storefront's HSTS covers subdomains, so browsers force HTTPS on every
  subdomain.
- k3s `local-path` volume sizes are labels, not limits.
- `kubectl apply -f folder/` applies every YAML file in it; keep anything else out.

## Scope

- Images built on version tags and stored in the registry.
- The app as manifests, one base and an overlay per installation, dropped onto the
  plumbing already on the Dell.
- The Dell's add-ons copied into the repo, and a bootstrap for a bare machine.
- `eactl`.
- Deploys on version tags, rollback, and the release pull request into `main`.
- Going public, once spec 05 is done.
- Backups, and a rehearsed restore.
- The demo installation.
- A full rebuild rehearsal on a blank machine.

## Non-goals

- More than one node. Autoscaling.
- Sensors over the internet and MQTT over TLS on 8883 (the sensors work; this spec only
  leaves room for the port).
- **Browser logins to the broker.** Accepted 2026-10-14: online, the broker's WebSockets
  door is open to read, the same as on a gym box, because the data is test data with
  invented names. Revisit before a real program's athletes use the hosted installation.
- Continuous sync between a gym box and hosted (out of scope on the form).
- A managed cloud. The design keeps the door open; it does not walk through it.

---

## Phase 0 — Images in the registry, on a version tag

- `.github/workflows/release.yml` (new), on GitHub's runners: on a tag `v*.*.*`, build
  the django and react images from the unchanged Dockerfiles, label each with the tag,
  and push them to `ghcr.io`, private. The build stamps `EA_VERSION` with the tag, so
  `/api/system/info/` names the running version.
- A read-only registry token for the cluster, stored as a Secret per installation by a
  written step (not in the repo).
- Images are built for the Dell's processor (amd64). A second processor type is only
  added if the throwaway machine needs it.

**Done when:**

- [x] Pushing a test tag produces both images in the registry with that tag, and they
      are not visible to a logged-out visitor.
- [x] The Dell can pull them with the stored token; a pod without the token cannot.
- [x] A container from the image reports the tag at `/api/system/info/`.

**Result, 2026-10-14.** A test tag (`v0.3.1-test.1`, deleted afterwards) ran
`release.yml` green: both images built, the django image reported its own version, both
stored in `ghcr.io/devi-walto/`. On the Dell, a pod using the pull secret downloaded the
image and printed `v0.3.1-test.1`; a pod without it got `ImagePullBackOff`.

- **The images came out public**: GitHub gives a new package its repository's
  visibility, and the repo is public. Devin set both to private by hand; a logged-out
  pull is now refused (403).
- **Two lines were added to `django/Dockerfile`** (`ARG EA_VERSION=dev`, `ENV
  EA_VERSION=$EA_VERSION`), against "the Dockerfiles do not change". Baking the version
  in at build time cannot drift from the image's tag, which setting it in a manifest
  could. A gym box's own build passes nothing and reports `dev`, as before.
- **The pull key** is a classic token with only `read:packages`, 90 days, stored by
  Devin on the Dell as Secret `ghcr-pull` in the new namespace `edge-athlete` (the token
  never passed through Claude). Renewal is by hand: a new token and the same command
  with `--dry-run=client -o yaml | kubectl apply -f -`. A GitHub App with an
  auto-refreshing key is the after-November option.

**Stop. Devin reviews.**

## Phase 1 — The app on the cluster, private

- `k8s/db/postgres/` (new): **the one shared Postgres**, in the shared namespace
  `edge-athlete`, applied by `eactl apply-db`. One copy, its data on a volume, replaced
  not doubled on update (the practice cluster's `Recreate` strategy). Version 15.18,
  matching a local install's 15. `max_connections` set to 100 (about 10 to 15 schools).
  Its administrator password is the Secret `postgres-admin`, made by a written step.
  The server's layers: cluster add-ons (`apply-cluster`), the database (`apply-db`; the
  backup job joins it in Phase 5), then each school (`eactl new`).
- `k8s/app/base/` (new), what **each school** runs, one file per Compose service; the
  Services keep the Compose names (`mosquitto`, `django`, `react`), so the app's settings
  need no changes:
  - **mosquitto**: Mosquitto 2.0.22, the repo's own `mosquitto.conf` as a ConfigMap
    (generated from the file, so local and remote share one copy); a volume for the
    messages it holds for an offline screen.
  - **postgres alias**: an `ExternalName` Service called `postgres` pointing at the
    shared Postgres, because `settings.py` names its database host `postgres`. No app
    change.
  - **django**: one copy, **with migrations moved from the start command to an init
    container** (a step Kubernetes runs once before the app starts). `recover_racks`
    moves with it. The Dockerfile's own start command is left as it is, so a local
    install is unchanged. Ready = `/api/health/` (it checks the database); alive = the
    port answers (so a database blip doesn't restart every school).
  - **mqtt-listener**, **monitoring-publisher**: the django image with their commands,
    one each, `Recreate`.
  - **react**: the image.
  - An **Ingress** that does what `nginx.conf` does: `/api/`, `/admin/` and the two
    static paths to django, `/` to react, for the school's own host name. (The sign-in
    limit and `no-store` are already in the app when remote: spec 05 Phase 3.)
  - **HTTPS for the school's address** (cert-manager, Let's Encrypt). **Every school is
    public** (Devin, 2026-10-16). A Tailscale-only guard was built and dropped: a school's
    address points at the public IP, so even a Tailscale device's browser arrives from the
    internet and was refused; and a new school is already protected by its one-time
    setup code. Switching a school off is spec 13's **suspend** (app off, data kept).
  - Live updates in the browser connect to port 9001 directly, which isn't reachable
    yet: they arrive in Phase 4 with the `wss` path. Pages, sign-in and data work now.
- **Traefik keeps each visitor's real address** (found and fixed 2026-10-16,
  `k8s/cluster/traefik-keep-visitor-address.yaml`): k3s's ServiceLB rewrote every
  visitor's address, which breaks both the guard and the per-address sign-in limit.
  Traefik now binds ports 80/443 itself and its Service is `ClusterIP`. See
  `docs/remote/hosting.md`, "Keeping each visitor's real address".
- **The first school is made with `eactl new`**, which: creates its namespace with the
  directory labels; creates its database and database login in the shared Postgres;
  writes its ConfigMap (from `.env.example`'s names, pointing at its own database);
  creates its Secret and copies in the pull key; and applies `k8s/app/base` to it.
- **The app uses the plumbing already on the Dell**: Traefik as the ingress, the
  existing `letsencrypt-staging` / `letsencrypt-prod` issuers through the same
  annotation the practice site uses. Nothing in the cluster's add-ons is reinstalled.
- `k8s/cluster/` (new): the Dell's working add-ons, brought into the repo with **only the
  changes a new machine needs**:
  - **cert-manager** (`k8s/cluster/cert-manager/`): the official v1.21.2 file, referenced
    by its address (pinned to the version already running), not copied in. Its own
    folder, applied first: the issuers are a kind cert-manager defines, so on a fresh
    machine they can only be created once it is running.
  - **the two certificate issuers** (`letsencrypt-issuers.yaml`): as they are, with the
    email as `${ACME_EMAIL}`.
  - **the hairpin fix** (`coredns-hairpin.yaml`): instead of Traefik's internal address
    on this Dell (`10.43.x.x`, which a new machine would not have), CoreDNS's `rewrite`
    sends the site's name to Traefik by name. One line per public subdomain.
  - **the DNS updater** (`ddns-updater.yaml`): curl pinned to an exact version; a list
    of subdomains (`${SUBDOMAINS}`) instead of one; creates a subdomain's record if it is
    missing; its namespace included.
  - The DNS provider's keys stay a Secret created by a written step, never a file.
- `eactl` starts here with what Phase 1 needs: `init`, `check`, `apply-cluster`, `apply-db`, `new`,
  `list`. It fills in **only** the named placeholders (`${DOMAIN}`, `${ACME_EMAIL}`,
  `${SUBDOMAINS}`), so the updater script's own `$IP` and `$SUB` survive.
- **`eactl update`** brings one school (`"Demo U"` or its short name) or all of them
  (`--all`) in line with the template, optionally moving them to a release
  (`--version 0.3.2`). It replaces separate `deploy` and `rollback` commands; Phase 3's
  automatic deploy runs `eactl update --all --version <tag>`.

**Done when:**

- [ ] `eactl new <school>` brings every part of the school up healthy, and its database
      login cannot open any other database.
- [ ] `eactl list` shows the school with its address, version and status.
- [ ] *(Browser, over Tailscale)* First-run setup works: `setup_code` run inside the pod
      prints a code, and the code claims the first administrator.
- [ ] *(Browser)* A coach signs in, creates an athlete, and the athlete is still there
      after the school's django pod and the shared postgres pod are deleted.
- [ ] No domain, email or address of Devin's appears in the repo: `eactl.env` is
      ignored by git, and the committed files hold only placeholders.
- [ ] During an update, migrations run once, in the new django copy, before the old one
      stops.
- [ ] `eactl update "Demo U"` rebuilds Demo U with no differences from what's running.
- [ ] The rate limit on sign-in still returns `429`.
- [ ] After `eactl apply-cluster`, its preview shows no difference, and no secret
      value appears anywhere in the repo or its history.

**Demo go-live, 2026-10-16** (ahead of the full phase, for a demo). Demo U
(`demo-u-u3fyig`) was created by hand at `test.<domain>` (the practice site's route was
retired and backed up), with HTTPS, in remote mode, and made public. **`v0.3.1` was tagged
on `feature-hosting`, not on `main`**, for the setup screen's "Welcome to Demo U" and its
"ask support" message; `main` catches up at the next merge. Still to fold into the repo:
`eactl new` doing those steps, the template's HTTPS lines, `apply-db` closing the
maintenance databases to school logins (`REVOKE CONNECT … FROM PUBLIC` on `postgres` and
`template1`, done by hand), invented seed names, and Demo U's own address.

**Stop. Devin reviews.**

## Phase 2 — `eactl`

`scripts/remote/eactl.sh`, a bash script run on the server (SSH in first). Every command
prints the `kubectl` it runs.

| Command | Does |
|---|---|
| `status`, `logs <service>`, `shell` | see what is running, read logs, open a shell in django |
| `setup-code "Name"` | issue the first-administrator code (spec 01), instead of the long `kubectl … setup_code` line |
| `init` | (from Phase 1) once per server: ask the server-wide settings, save `eactl.env` |
| `apply-cluster` | (from Phase 1) fill in the placeholders and apply `k8s/cluster` |
| `apply-db` | (from Phase 1) the shared database |
| `new ["Name"]` | (from Phase 1) make a school on this server, with its database; public over HTTPS |
| `list` | (from Phase 1) the directory: every school, its short name, status, release and address |
| `update "Name" \| --all [--version V]` | (from Phase 1) bring schools up to date, or move them to a release; also the manual deploy and rollback |
| `make-admin <username>` | the recovery command from spec 01 |
| `secrets` | create or update the installation's Secret from a local file that is never committed |
| `backup`, `restore <file>` | Phase 5 |

**Done when:**

- [ ] Each command works on the server, against the real installation.
- [ ] Each prints the underlying `kubectl` command before running it.
- [ ] `restore` and anything else that deletes data asks for the installation name to be
      typed again.

**Stop. Devin reviews.**

## Phase 3 — Deploy on a version tag (CD)

- A **GitHub runner on the Dell, for deploys only.** It runs one job: after Phase 0's
  images exist for a tag, run **`eactl update --all --version <tag>`** (no questions
  asked, since the tag was the decision) and wait for every school to be healthy. The
  demo school updates first; if it fails its health check, the others aren't touched.
- **Its cluster access is limited**: a Kubernetes service account that may update the
  app's namespaces and nothing else (no cluster-wide rights, no secrets outside them).
- **Guarded for a public repo:**
  - only a **tag** starts the deploy job, and only Devin may create `v*` tags (a
    repository rule);
  - GitHub's **"require approval for all outside contributors"** setting is on, so no
    workflow from a stranger's fork runs until Devin approves it;
  - the runner deletes its working files after each job.
- **The release** (Devin, 2026-10-16): **every 3 days, a scheduled GitHub job moves
  `main` forward to match `SprintBranch`** (a fast-forward only: everything on
  `SprintBranch` already passed CI in a pull request). Devin **tags the commits on `main`**
  he wants released. This is the only way `main` moves.
- **A tag must be on `main`.** The release workflow checks it and refuses otherwise.
  (`v0.3.1` was tagged on `feature-hosting` for the Oct 16 demo, before this check
  existed.)
- **Rolling back checks the database first** (Devin, 2026-10-16). Before moving a school
  to an **older** release, `eactl update`:
  1. asks the school's database which migrations it has applied (`django_migrations`);
  2. asks the target release's image which migrations it knows (a throwaway pod that only
     lists its migration files, and never touches a database);
  3. compares them. **No difference:** it says so ("no database changes, safe to
     switch") and carries on. **Applied but unknown to the older release:** it lists
     them and warns that undoing them deletes the data they hold, then offers to **undo
     them first, with the newer release still running** (Django undoes migrations itself,
     `migrate <app> <last one the older release knows>`), **then switch**. Before undoing,
     it saves a **safety copy of that school's database** (`pg_dump`, one file on the
     server, named with the school and the time), and asks `(y/N)`.
  4. If a migration can't be undone (a data step without its undo written), it stops
     before switching, and points at the safety copy.

**Done when:**

- [ ] Tagging a version deploys it; `/api/system/info/` then reports that version.
- [ ] Deploying the previous tag rolls back, and the data is untouched.
- [ ] Rolling back across a migration warns and lists it; choosing to undo saves a
      safety copy first, undoes it with the newer release, then switches. Rolling back
      with no migration in between says it's safe and just switches.
- [ ] `main` moves forward to `SprintBranch` on its 3-day schedule; a tag on any other
      branch is refused.
- [ ] A deploy that fails its health check leaves the previous version serving.
- [ ] The runner's credentials are refused when used to read another namespace's
      Secrets or to change the cluster's add-ons.
- [ ] *(By hand)* The fork-approval setting and the tag rule are on, and recorded in the
      hosting guide.

**Stop. Devin reviews.**

## Phase 4 — Going public

**Starts only when spec 05 is done** (the open routes require a login when hosted,
`DEBUG` is refused, hosts are checked).

- **One wildcard for every school, instead of one setup per school** (to decide here;
  proposed 2026-10-16). Since nobody types a school's address, each could live under one
  wildcard: a DNS record `*.<domain>`, a **wildcard certificate** (Let's Encrypt issues
  those only through the DNS check, via the DNS provider's API that the DNS updater
  already uses, instead of HTTP), and one hairpin rule for the whole domain. Then
  `eactl new` needs no DNS or certificate work at all. The alternative is the old way:
  per school, a DNS record, a line in the DDNS job, a line in `coredns-custom` and a
  certificate.
- The real overlay sets `EA_DEPLOYMENT=remote` and its allowed hosts and trusted origins.
- The Tailscale-only middleware comes off the site.
- **The broker goes online through the site's own address.** Traefik routes a path on
  the HTTPS site to the broker's WebSockets listener, so live updates travel as `wss`
  on 443 like everything else. No new port.
- **The screens connect to it the right way for where they run.** A gym box keeps
  `ws://<host>:9001`; a hosted page uses `wss://<site>/<path>`. Chosen by spec 05's
  `useDeployment()`, so it is one codebase, not two builds.
- **The plain-HTTP workarounds stay for the gym and go unused online.** A gym box serves
  plain HTTP, so the app carries two patches: `polyfills.js` fills in browser features
  that plain HTTP switches off, and the rack screen's kiosk script launches Chromium
  with the gym's address marked as secure. Online, HTTPS makes the browser trust the
  site by itself: the polyfill only fills a gap that is no longer there, and no kiosk
  flag is involved. Neither is removed, because the gym box still needs both.

**Done when:**

- [ ] *(Browser, from a phone on mobile data)* The site loads over HTTPS with a trusted
      certificate.
- [ ] From the internet, every route except sign-in, first-run setup and
      `/api/system/info/` answers `401` without a login (spec 05's walk, against the
      live address).
- [ ] *(Browser, from a phone on mobile data)* Live updates arrive over `wss`: starting
      a set on one phone shows on another without a refresh.
- [ ] *(Browser)* On the public site the offline shell (the service worker) registers,
      with no kiosk flag; on a gym box nothing has changed.
- [ ] Certificates renew: cert-manager reports the renewal time, and a forced renewal on
      staging succeeds.

**Stop. Devin reviews.**

## Phase 5 — Backups, and a restore that has been done

- A CronJob per installation: a nightly database dump, kept for a set number of days,
  **copied off the Dell** (see open decisions for where).
- `eactl backup` and `eactl restore` (Phase 2) use the same format.

**Done when:**

- [ ] A backup appears off the Dell every night.
- [ ] *(By hand)* A restore into a scratch namespace brings back the same athletes, sets
      and reports, with original timestamps.
- [ ] A restore refuses a dump from a different schema version (`docs/remote/databases.md`).

**Stop. Devin reviews.**

## Phase 6 — The demo installation: a dry run of onboarding a new school (Definition of Done #5)

Decided 2026-10-14. The demo is **set up the way a new school's installation would be,
from start to finish, by hand**, so it doubles as the rehearsal of onboarding a real
customer. Devin then hands the faculty reviewer invented login details as if they were
that school's administrator, and demos the whole app from there.

- **The demo is Demo U** (`eactl new --name "Demo U"`, Devin, 2026-10-16), made in
  Phase 1, from the same base as any school: its own namespace, address, Secret, and its
  own database in the shared Postgres. The walkthrough below is rehearsed on it. Never a hand-edited copy of another
  school's files, and never a new server.
- **It starts empty, like a real new school.** First-run setup with a setup code from
  `eactl setup-code`, exactly as spec 01 built it. Devin claims it, creates **an
  administrator login for the faculty reviewer** with an invented username and a real (not
  well-known) password, and hands those over. No `coach` / `coachpass`; spec 01's rule
  against well-known logins holds here too.
- Any data in it is **invented**: entered through the app during the walkthrough, or
  loaded with the seed command. **Never** a copy of the real database.
- The same version tag deploys both installations.
- **Every step the walkthrough needed that the guide did not have is added to the
  guide.** That makes the next school's onboarding a matter of following it.

**Done when:**

- [ ] *(By hand)* The demo was set up from nothing by following the hosting guide, and
      the guide now has every step that was needed.
- [ ] *(Browser)* Signed in with the login details handed to the faculty reviewer, the demo shows
      the administrator's view: Coaches page, adding a coach, the whole workspace.
- [ ] The demo runs at its own address with its own database; nothing in it can read the
      real installation (separate namespaces, separate Secrets, separate databases).
- [ ] Deleting the demo namespace leaves the real installation untouched.
- [ ] One tag updates both.

**Stop. Devin reviews.**

## Phase 7 — From a blank machine: the bootstrap, and the rebuild rehearsal

The rule this spec is judged by, tested end to end. Last on purpose: the app is on the
existing cluster by Phase 1, and this phase proves the same result can be had without
the Dell.

- **The machine itself is prepared by hand, from a written checklist, not a script**
  (Devin, 2026-10-14): Linux installed with the operator's user; Tailscale joined; the
  operator's laptop key added (`ssh-copy-id`) and SSH passwords turned off. Clouds
  (AWS, Azure) ask for the key when the machine is made. Scripts start from a machine
  that already works and is reachable.
- `infra/bootstrap.sh` (new): run once on that prepared machine. Installs the **same
  pinned** k3s version as the Dell. Safe to run twice. On a cloud machine, installs k3s
  with `--disable=servicelb` and uses the cloud's load balancer instead (see Phase 1's
  visitor-address fix). Opens with a plain-language
  comment on why it exists. Written from what was done by hand on the Dell, not invented.
- **A release bundle** (Devin, 2026-10-14): `release.yml` also attaches
  `eactl-<version>.tar.gz` (`scripts/remote/` and `k8s/`, nothing else) to each version
  tag. A new server downloads the bundle for the version it will run, so its playbook
  always matches its images; no git needed. Until then (Phases 1–6), the server holds a
  clone, because the files change constantly.
- **Secrets encrypted on disk from the start** (decided 2026-10-14). Before installing
  k3s, the bootstrap writes `secrets-encryption: true` into `/etc/rancher/k3s/config.yaml`,
  so the new cluster encrypts every Secret it ever stores. By default a Secret is only
  base64-encoded, and anyone with a copy of the cluster's database file could read it.
  This is what managed clouds (AKS, EKS, GKE) do by default. It protects copies of that
  file (a stolen disk, a leaked backup), not someone holding cluster credentials. The
  key lives in `/var/lib/rancher/k3s/server/cred/`: a backup of the cluster's own
  database is useless without it.
- **The Dell gets the same setting by hand**, walked through step by step with Devin:
  add the line, restart k3s, re-encrypt the Secrets already stored
  (`k3s secrets-encrypt reencrypt`), and check one is unreadable in the database file.
- `docs/guides/hosting.md` (new): the machine checklist, bootstrap, the release bundle,
  `eactl init` and `eactl apply-cluster`, the written secret steps, deploy the current
  tag, restore last night's backup.

**Done when:**

- [ ] *(By hand)* On a **throwaway machine** (see open decisions), the guide alone brings
      the real installation back with all its data. The time taken is written in the
      guide.
- [ ] Running `bootstrap.sh` a second time changes nothing and reports so.
- [ ] On the throwaway machine and on the Dell, `k3s secrets-encrypt status` reports
      encryption enabled, and a known Secret's value does not appear in plain text in the
      cluster's database file.
- [ ] Nothing in that run needed a step that is not in the guide.

---

## If there is time: moving a database between a gym box and hosted

Tabled into this spec on 2026-10-06; not in the Definition of Done. The model is in
`docs/remote/databases.md`: the first move is a copy (same schema version, counters
moved apart), after which merges add rows and never overwrite. **Gap to close when it is
built:** athlete logins are hosted only, so a copy from hosted down to a gym box must
strip them (or the box must ignore them), and a gym box must never hold a working
athlete login. Would become `eactl copy-db`.

## Deferred, with a home

- **The registry database and the operator's web console**, an installation's name on
  the sign-in card, and account standing: [spec 13](../later/13-registry-and-console.md),
  after the class. Phase 1's namespace labels are its starting point.
- **Moving CI onto the Dell** once the repo is private; ephemeral runners with Actions
  Runner Controller as a stretch.
- **Ansible** in place of `bootstrap.sh`, for machine configuration.

## Open decisions

| Decision | Recommendation |
|---|---|
| Where Phase 7's throwaway machine runs | A free-tier cloud VM (amd64, like the Dell, and the closest thing to the AWS/Azure goal). A local VM on an Apple-chip Mac would be ARM and need ARM images |
| Where backups are copied to | Off the house entirely (a cloud storage bucket) is the professional answer; the laptop over Tailscale is the cheap one |
| Secrets beyond a local file | A local, never-committed file per installation applied by `eactl secrets` now; Sealed Secrets or SOPS (encrypted secrets in the repo) as a later step |

## Acceptance criteria

- [ ] The app runs on k3s at a public HTTPS address with a certificate that renews
      itself (Definition of Done #1).
- [ ] Tagging a version deploys it; tests gate every merge (CI from spec 05, CD here).
- [ ] A demo installation runs from the same template, isolated from the real one (#5).
- [ ] The whole service has been rebuilt on a blank machine from the repo, the guide and
      a backup.
- [ ] No secret is in the repo, and no stranger's pull request can run anything on the
      Dell.

## Risks

| Risk | What reduces it |
|---|---|
| The real app goes public before its open routes are closed | Phase 4 is gated on spec 05; Phase 1 keeps the site Tailscale-only |
| A fork's pull request runs code on the Dell | Tests and builds run on GitHub's machines; the Dell runner deploys only, on tags only Devin can create; fork approval required |
| The home connection or the Dell goes down before a live demo | Backups off the Dell; the rebuild rehearsal is timed; record the end-to-end demo on video early (Definition of Done #7 allows video) |
| A new subdomain silently fails its certificate | The two-line rule (coredns-custom + DDNS) is in the hosting guide and in Phase 4's and 6's checklists |
| A deploy during a training session ends that school's open sets (`recover_racks` runs in django's start-up step) | Deploy outside training hours; later, a setting that skips it online |
| Time: this spec is large for four weeks | Phases 0–1 put the app on the cluster quickly by reusing the plumbing; 5 and 7 can shrink to a documented restore if time runs out; the database move is optional |

## Docs to update when done

`docs/remote/hosting.md` becomes a description of what was built: Ubuntu Server, Tailscale
for management, Traefik and why, cert-manager over HTTP-01, the DDNS job, the NAT hairpin
and its DNS fix, one namespace per installation, runners, and the rebuild rule.
`docs/guides/hosting.md` (new) is the operator's guide. `docs/journal/scripts.md` gains why
`eactl` is separate from `ea.sh`. `docs/remote/deployments.md`: Compose for a gym box,
manifests for hosted, the same images.
