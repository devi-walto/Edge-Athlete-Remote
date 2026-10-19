<!--
this page — how the hosted service runs: the cluster, the certificates, and the two
doors into the message broker.

The surprise in here is how little changes. Secure live updates in the browser sounded
like a new real-time layer; it turned out to be encryption in front of the broker the
system already has. That finding is recorded because the bigger plan was written down
first, and someone will find it.
-->

# Hosting

## What forced it

The gym box runs under Docker Compose on one machine, on a private network, over plain
HTTP. The hosted service has to be reachable at a normal web address, encrypted end to
end, and renew its own certificates without anyone visiting it.

## What we chose

### k3s, running the same images

The hosted service runs on **k3s**, a small Kubernetes distribution. Each installation
({doc}`databases`) is one copy of the same stack the gym box runs — web server, Django,
Postgres, the message broker — built from **the same images**, in its own namespace,
**stamped out from one template**. The second installation is the demo shown to
faculty ({doc}`access`), which makes the template prove itself from the first week.

Learning k3s is itself one of the directed study's outcomes ({doc}`directed-study`).

### Where the cluster runs: at home

The cluster runs on one machine at home: **a Dell OptiPlex**, as a single k3s node.

**A second machine was planned and then cut (October 14).** A Mac mini was going to
join later as a second node. It was never part of the Definition of Done, which asks
for the app on k3s at a public HTTPS link, not for a cluster of a given size. It would
also have cost real work: k3s runs only on Linux, so the Mac could only join through a
virtual machine, and an Apple-chip Mac would have meant building every image twice.
Adding a node later is still possible; nothing here depends on there being one.

**Getting traffic from the internet to the Dell:**

| What | How |
|---|---|
| Web traffic (80, 443) and sensors (8883) | The home router forwards those three ports to the Dell. Nothing else is forwarded |
| The home address changing | Home internet addresses change now and then. A small job in the cluster checks the address and updates the domain's records through Porkbun's API when it moves |
| The cluster's own control port (6443) | **Never forwarded.** It is managed from inside the home network only |

**Before any of that works, two things about the home connection have to be true:**

1. **It has its own public address.** Some providers share one public address between
   many homes (called CGNAT), and then nothing outside can reach in. The check: the
   internet address the router reports must match what a site like whatismyip.com
   shows.
2. **The provider does not block ports 80 and 443** on a home plan.

If either fails, the fallback is a tunnel service — see the rejected options below for
why it is the fallback and not the plan.

### Keeping each visitor's real address

Decided and built on October 16.

**What forced it.** The **sign-in limit** depends on knowing **where each visitor is
coming from**: online, the app refuses an address after 10 wrong passwords in a minute
(spec 05, "hosted mode"). A Tailscale-only guard for schools in testing needed it too;
that guard was later dropped (every school is public, protected by its setup code).

k3s ships with a small built-in helper, **ServiceLB**. A cloud provider normally gives a
cluster its front door to the internet; a machine at home has no cloud, so ServiceLB
does the job: it takes the machine's ports 80 and 443 and forwards every visit to
Traefik, the cluster's front door. But as it forwards a visit, it **writes its own
address in place of the visitor's.** Every visitor looked identical, so one stranger's
wrong guesses would have locked everyone out of signing in.

It was measured, not assumed. A small test app that reports the address it sees was
visited from a laptop on Tailscale (an address starting `100.`); it saw the helper's
internal address (one starting `10.42.`) instead.

**What we chose.** Take the helper out of the way. **Traefik answers on the machine's
ports 80 and 443 itself**, so a visit arrives with its address intact:

```text
before:  visitor ─▶ Dell ports ─▶ helper (rewrites address) ─▶ Traefik
after:   visitor ─▶ Dell ports ───────────────────────────────▶ Traefik   (address intact)
```

It is one settings file in the repo (`k8s/cluster/traefik-keep-visitor-address.yaml`),
applied with the rest of the cluster's add-ons, so every new server gets it. Traefik's
own Service becomes inside-only, which ServiceLB ignores; anything inside the cluster
that looks Traefik up by name (the fix that lets the cluster reach its own public
address) is unaffected. Tested after: the same visit arrived with the laptop's own address, and the
practice site, its certificate and the in-cluster check that certificates rely on all
still worked.

**What we rejected.** **ServiceLB's own "keep the address" setting**
(`externalTrafficPolicy: Local`). It is the documented answer, and it was tried first. It
removed one rewrite, but the helper rewrites the address again itself as it hands the
visit on; the test app still saw the helper's address.

**What it cost.**

- **Only one Traefik per machine.** It holds the machine's ports itself, so an update
  stops the old one before starting the new one: a few seconds offline, instead of
  none.
- **Changing it needs care.** k3s installs Traefik from a package, and this changes that
  package's settings; a mistyped setting is silently ignored. A wrong name for one
  setting took the practice site down for about four minutes while this was built.
  Check the package's own settings file for the installed version before changing it.
- **A cloud does this differently.** There, the cloud's load balancer is the front door
  and offers its own way to keep the visitor's address. This file is for a machine with
  no cloud in front of it.

### HTTPS, with certificates that renew themselves

The project uses **a domain Devin owns, registered with Porkbun.** Each installation
gets its own sub-address under it — one for the real installation, one for the demo.

Certificates come from Let's Encrypt and are **renewed automatically by the cluster**
well before they expire — nobody logs in every few months to do it. Let's Encrypt
proves the domain is ours by fetching a file over port 80, which is why port 80 is
forwarded even though the site itself redirects to HTTPS. If port 80 ever cannot be
opened, the same proof can be done through Porkbun's DNS API instead.

### Two doors into one broker

| Door | Port | Used by | Speaks |
|---|---|---|---|
| **Secure WebSockets** (`wss`) | 443, alongside the site | browsers — rack screens, coach screens, wall display | MQTT over WebSockets, over TLS |
| **MQTT over TLS** | 8883 | sensors | plain MQTT, over TLS |

The broker behind both doors is the same Mosquitto the gym box runs. It already has a
WebSockets listener, which the browser uses today over plain `ws://`. **Encrypted
WebSockets is TLS in front of that listener**, handled by the cluster's ingress — not a
new real-time layer.

**The browser only ever listens.** Every screen subscribes; none publishes. So browser
access to the broker is **read-only**, tied to the user's login, and limited to its
installation's topics. The one screen that publishes — the connection-test page — is
a development tool and must not be served by a hosted installation.

**Built (October 2026, `v0.5.0`–`v0.5.1`).** Screens reach the broker at
`wss://<school>/mqtt`: a routing rule on the school's own address, not a page and not an
API route, so no new port. The page picks its address from its own scheme: `https` →
`wss://<school>/mqtt`, plain `http` (a gym box) → `ws://<box>:9001` as before. **The
screens door is listen-only online**: a remote school's broker has its own settings file
that lets anyone read the app's topics on that door and nobody send; django's door is
unchanged and never reachable from outside. A gym box keeps its own settings untouched,
so its test page can still send. Logging in to the broker is still to come; until then
it is read-only and public, which is acceptable while the data is test data.

**The `v0.5.0` lesson.** The listen-only rules file was readable by root only, and the
broker reads it after switching to its own user, so it stopped and took the demo
school's live updates down. The release stopped at the demo school as designed. The
test before it had passed on a Mac, where Docker doesn't enforce file permissions on
shared folders. `v0.5.1` gave the file to the broker's group and named the two doors
(`programs` 1883, `screens` 9001). **Since then, anything whose owner or mode matters is
tested with real Linux permissions**, and a release that fails on a school now undoes
itself (below).

### Deploys come from CI

Because the cluster sits behind a home router, CI cannot reach in to deploy — and the
control port is deliberately never opened for it. Instead, the **rollout step runs on
the Dell itself** (a self-hosted runner): it reaches out to collect the job, so nothing
new is exposed. The gym box keeps installing from its own clone
({doc}`../journal/scripts`).

**How a release works (built October 2026):**

- **Work reaches `main` only through `SprintBranch`.** Every change is a pull request
  into `SprintBranch` with CI green; a job moves `main` forward to it every three days
  (or on a button). **`main` is locked so only that job can move it**: the branch rule
  admits only a deploy key, which the job pushes with. A pull request into `main` can't
  be merged, by anyone.
- **A version releases once its tag is on `main`.** Tag the merge on `SprintBranch`; when
  it reaches `main`, the release builds it. Several versions arriving at once are all
  built, so each can be rolled back to, and only the newest is deployed. A tag not on
  `main` yet waits; nothing is released from a commit that skipped CI.
- **The demo school goes first.** If it fails, no other school is touched, and every part
  that changed is put back to its exact previous setup.
- **A school can be held** at its release; automatic deploys skip it. Moving one school
  back to an older release holds it automatically, after checking which database changes
  the older release doesn't know and offering to undo them behind a safety copy.
- **The deploy login can update schools and nothing else**: no secrets, no shared
  database, no cluster add-ons.
- **The server's own copy of the tools keeps itself current**: an hourly timer on the
  Dell moves it to the newest release, using the Dell's read-only key, so the commands
  typed there match what the schools run. Re-running the setup script is only for a new
  machine.

## What we rejected, and why

**Moving `main` with the workflow's own login.** It can't be singled out by a branch rule,
so locking `main` would lock the job out too, and its pushes never start another
workflow, so a tag reaching `main` couldn't release itself. A write deploy key does
both; it lives only in GitHub's secret store and is used by that one job.

**Running the setup script from the release pipeline.** It runs as root, and the deploy
runner was built to have no root at all; giving it root, or letting it change the copy
root later runs, would let anything that reaches the runner own the machine. The hourly
timer needs no new access.

**Undoing a failed update by re-applying the old release.** It would re-apply the new
template with old images, and the template can be what broke (`v0.5.0`). Each part goes
back to its own previous setup instead.

**One address with a path per school** (`<domain>/<school>/`) instead of a subdomain each.
The browser keeps saved data per address, not per path, so schools would share one
store: one school's sign-in would overwrite another's, and a bug on one school's page
could read every school's tokens. A wildcard certificate and DNS record make subdomains
as little work.

**A separate WebSocket server with a message store behind it**, instead of the broker's
own listener. This was the first plan. Checking the code showed the browser already
speaks MQTT over WebSockets; a second transport would have been two real-time systems
to keep in step, for no gain.

**Running k3s on the gym box too**, so both shapes use the same orchestration. A gym
box is one machine running one installation; Compose is the right size for that, and
it already works. The cost is recorded in {doc}`deployments`.

**Certificates renewed by hand.** Certificate lifetimes are getting shorter, not
longer. Anything that needs a person to renew it will eventually lapse.

**A rented server.** It avoids every home-network question above, for a monthly bill.
Hardware already on hand does the same job, and running the cluster on it — router,
addresses and all — is part of what the directed study is for.

**A tunnel service instead of forwarding ports.** It hides the home address and needs
no router changes, and it handles websites well. It handles the sensors' raw MQTT
connection on port 8883 poorly: most tunnels expect web traffic, or need their own
software on the connecting device, which an ESP32 cannot run. Forwarding three ports
keeps the sensors simple. The tunnel stays the fallback if the home connection cannot
take incoming traffic.

## What it cost

- **Two orchestration setups for the same images** — Compose on the gym box,
  manifests on the cluster.
- **The browser's broker login is new work.** Today the broker trusts everyone on the
  box's Wi-Fi; hosted, it has to check a credential the site issued.
- **One machine, so no failover.** If the Dell is down, the site is down. The cluster
  can still restart a crashed container on its own; it cannot move work to a machine
  that is not there.
- **The site is only as available as the house.** A power cut, a router reboot or an
  outage at the provider takes it down. Fine for a directed study; worth saying out
  loud before a live demo.
- **The home network is now partly public.** Three ports point at the Dell, so the
  Dell needs to be kept updated, and nothing else in the house should depend on it.
- **A write deploy key to look after.** If it is ever exposed, it is deleted under the
  repo's deploy keys and replaced; the setup steps are in `scripts/remote/README.md`.
- **Two broker settings files** (gym and remote) that say the same thing apart from the
  screens door, so a change to one must be made to both.

**Checked, October 5:** the home connection has its own public address (no CGNAT). A
traceroute to the public address reaches it in one hop, so the router holds that
address itself.

**Checked, October 14:** the provider allows incoming traffic on 80 and 443; the sites
are served over HTTPS with certificates that renew themselves.

**Decided, October 17:** the project's own domain (with a wildcard record and
certificate) waits until after the class, and is then the test of rebuilding the whole
setup from scratch.
