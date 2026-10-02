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

The cluster runs on two machines at home: **a Dell OptiPlex and a Mac mini.**

**It starts on the Dell alone.** k3s runs only on Linux. The Dell runs it directly;
the Mac mini can only join through a Linux virtual machine. So the first goal is
everything working on one machine. The Mac mini joins later as a second node, which
is a learning step in its own right and blocks nothing before it.

**If the Mac mini has an Apple chip, the images must be built twice** — once for the
Dell's Intel-style processor, once for the Mac's ARM one. Another reason the Dell goes
first.

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

### Deploys come from CI

A push builds the images, tags them, and rolls them out to the cluster. The gym box
keeps installing from its own clone ({doc}`../journal/scripts`).

Because the cluster sits behind a home router, CI cannot reach in to deploy — and the
control port is deliberately never opened for it. Instead, the **rollout step runs on
the Dell itself** (a self-hosted runner): it reaches out to collect the job, so nothing
new is exposed.

## What we rejected, and why

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
- **If the cluster mixes processor types** — an Apple-chip Mac mini beside the Dell —
  every image must be built for both. Starting on the Dell alone defers this.
- **The site is only as available as the house.** A power cut, a router reboot or an
  outage at the provider takes it down. Fine for a directed study; worth saying out
  loud before a live demo.
- **The home network is now partly public.** Three ports point at the Dell, so the
  Dell needs to be kept updated, and nothing else in the house should depend on it.

**Still to check before week 2:**

- Does the home connection have its own public address (no CGNAT)?
- Does the provider allow incoming traffic on ports 80 and 443?
- Does the Mac mini have an Apple chip or an Intel one?
- Have the domain's old DNS records been cleared out, so only the project's remain?
