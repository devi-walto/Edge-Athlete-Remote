# Feature Spec 18: Backups, a demo dry run, and rebuilding from a blank machine

- Owner: Devin Walton
- Date: 2026-10-14 (split out 2026-11-14)
- Previously spec 12, Phases 5–7 (split out when the specs were put in build order, 2026-11-14)
- Status: Specced, 3 phases. After the coach redesign (Devin, 2026-11-14)
- Depends on: [06 Hosting on k3s](../remote/04-hosting.md) (Phases 0–4, done)

The rest of the hosting spec: safety copies off the server with a restore that has actually been done, a dry run of onboarding a new school on the demo installation, and the whole setup rebuilt from a blank machine with one bootstrap command (the "fresh Linux PC, like a cloud machine" requirement). Its decisions and background are in spec 04.

## Phase 0 — Backups, and a restore that has been done

- A CronJob per installation: a nightly database dump, **copied off the Dell**, so a dead
  disk, a stolen machine or a house problem doesn't take the backups with it.
  - **Where (recommended, 2026-10-16):** a cloud storage bucket (e.g. Backblaze B2 or AWS
    S3; well under $1 a month at this size). The laptop over Tailscale is the free
    fallback, but only while it's on, and it's in the same house.
  - **Kept: 7 daily, 4 weekly, 6 monthly**, in **one folder per school**.
  - **Encrypted before leaving the Dell**: they hold athletes' data. The key is kept like
    any other secret, never in the repo.
- `eactl backup` and `eactl restore` (Phase 2) use the same format.

**Done when:**

- [ ] A backup appears off the Dell every night.
- [ ] *(By hand)* A restore into a scratch namespace brings back the same athletes, sets
      and reports, with original timestamps.
- [ ] A restore refuses a dump from a different schema version (`docs/journal/core/remote/databases.md`).

**Stop. Devin reviews.**

## Phase 1 — The demo installation: a dry run of onboarding a new school (Definition of Done #5)

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

## Phase 2 — From a blank machine: the bootstrap, and the rebuild rehearsal

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
