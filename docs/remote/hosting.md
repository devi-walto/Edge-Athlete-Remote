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
Postgres, the message broker — built from **the same images**, in its own namespace.

Learning k3s is itself one of the directed study's outcomes ({doc}`directed-study`).

### HTTPS, with certificates that renew themselves

Each installation gets its own address under one domain. Certificates come from
Let's Encrypt and are **renewed automatically by the cluster** well before they expire —
nobody logs in every few months to do it.

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

## What it cost

- **Two orchestration setups for the same images** — Compose on the gym box,
  manifests on the cluster.
- **The browser's broker login is new work.** Today the broker trusts everyone on the
  box's Wi-Fi; hosted, it has to check a credential the site issued.
- **If the cluster mixes processor types** (an ARM board and an x86 machine), every
  image must be built for both. Avoidable by keeping the cluster to one type.

**Still open:** where the cluster runs — hardware at home, or a rented server — and
which domain it lives under. Both change the work, not the design.
