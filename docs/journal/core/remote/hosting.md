<!--
this page — how the app got from a box in one gym to a public HTTPS address,
running on one PC at my house, and what broke on the way.

The tool swaps are called out on purpose (nginx → Traefik, Compose → k3s, and
k3s's built-in load balancer → Traefik on the machine's ports). Each one moved a job
somewhere else, and the next person to change these files needs to know where
it went.
-->

# Hosting

*Oct 2 – Oct 17, 2026 · spec 12 · PRs #3, #4*

## Tool changes at a glance

| Job | Local install | Remote server | Why it changed |
|---|---|---|---|
| Running the containers | Docker Compose | **k3s** (small Kubernetes) | One copy per school from one template; restarts on its own |
| Reverse proxy (sends `/api/` to Django, the rest to React) | nginx | **Traefik**, the one k3s ships with | It's already in the cluster and routes by school address |
| Load balancer (takes the machine's ports 80/443 and hands visits to the proxy) | none; nginx listens on the box's ports | **none; Traefik listens on the Dell's ports itself** | k3s's built-in load balancer (ServiceLB) hid every visitor's address |
| HTTPS certificates | none (closed Wi-Fi) | **cert-manager + Let's Encrypt** | Certificates that renew themselves |
| Live updates in the browser | Mosquitto WebSockets, `ws://` | **the same Mosquitto**, behind TLS at Traefik | No new real-time layer needed |

:::{warning}
**Two jobs nginx did that Traefik doesn't.** On a local install, `nginx/nginx.conf` limits wrong-password tries and tells browsers never to keep a copy of sign-in replies. Online, **Django does both itself** in remote mode (spec 05). If you ever put a different proxy in front, don't move them back into it and assume both installs are covered.

nginx still exists online in one place: inside the React image, handing out the built pages as plain files. It's a file server there, not the proxy.
:::

## The problem

The app ran on one box in one gym: Docker Compose, nginx, plain HTTP, on the box's own Wi-Fi. The network was the security. Only people in the room could connect.

Online, it has to be reachable at a normal web address from anywhere, encrypted end to end, with certificates that renew themselves. Each school needs its own copy, and it all runs on one PC at my house: a Dell OptiPlex.

## Starting point: the local install, as is

**What works:** Compose is the right size for one machine running one school, and it already works. The local install still runs this way.

**Why it doesn't carry online:** nothing in it makes a second school from a template, renews a certificate, or restarts itself across a reboot without help. And I wanted to learn Kubernetes for my DevOps career. So the remote server runs the **same images** on k3s instead.

## Try 1: k3s with its defaults

k3s comes with Traefik as its reverse proxy, and a small built-in load balancer called **ServiceLB** (also known as Klipper). In the cloud, the provider gives a cluster a load balancer that faces the internet. A PC at home has no cloud, so ServiceLB takes the machine's ports 80 and 443 and forwards every visit to Traefik.

So nginx came out as the proxy, and each school got an Ingress, a short routing file that does what `nginx.conf` did (`k8s/app/base/ingress.yaml`). Certificates came from cert-manager asking Let's Encrypt.

**What worked:** a starter app, then the real stack, live on the internet on Oct 16. Kubernetes was super scary for me, even after learning containers. Getting this far was the biggest win of the project.

**What broke, part 1: every visitor looked the same.** As ServiceLB forwards a visit, it writes its own address in place of the visitor's. The sign-in limit locks out an address after 10 wrong passwords in a minute. With every visitor sharing one address, one stranger's guesses would lock *everyone* out.

I measured it instead of assuming. A tiny test app that reports the address it sees was visited from my laptop, and it saw ServiceLB's internal address instead of mine.

The documented fix is ServiceLB's "keep the address" setting (`externalTrafficPolicy: Local`). I tried it first. It removed one rewrite, but ServiceLB rewrites the address again as it hands the visit on. The test app still saw the wrong one.

**What broke, part 2: NAT hairpinning.** The certificates wouldn't finish. I ran `kubectl get pods` to check on the issuer, and it just sat there.

After some research and a conversation with Claude, I found it's a common problem on home routers. From inside the network, a request to my own public address goes out to the router, which is supposed to send it straight back in. Mine wouldn't, so cert-manager's self-check waited forever.

It felt empowering. For the first time I was picturing the network and actually thinking about where my data was going.

## Where I landed

```text
before:  visitor ─▶ Dell ports ─▶ ServiceLB (rewrites address) ─▶ Traefik
after:   visitor ─▶ Dell ports ─────────────────────────────────▶ Traefik   (address intact)
```

- **Traefik holds ports 80 and 443 itself**, so every visit arrives with its real address. That's one file, `k8s/cluster/traefik-keep-visitor-address.yaml`.
- **The cluster answers my public names with Traefik**, so a request to my own address never leaves the cluster. That's `k8s/cluster/coredns-hairpin.yaml`, a rule added to CoreDNS, the cluster's built-in DNS.
- **Two forwarded ports, one entry point.** Everything, every school and every sensor, comes in through Traefik. The router forwards 443 to the Dell, plus 80, which only redirects to HTTPS and lets Let's Encrypt check the domain is mine. The cluster's control port (6443) is never forwarded.
- **One school = one namespace**, stamped from one template, at its own subdomain. The demo school is the second copy, so the template had to prove itself from day one.
- **The home address can change**, so a small job in the cluster updates the domain's records through Porkbun when it moves (`k8s/cluster/ddns-updater.yaml`).

:::{warning}
**Changing Traefik's settings needs care.** k3s installs Traefik from a Helm chart, and these files change that chart's settings. A misspelled setting is silently ignored. One wrong name took the practice site down for about four minutes while I built this. Read the installed chart version's own `values.yaml` before changing anything.
:::

## Live updates in the browser

Screens already get live reps straight from Mosquitto over WebSockets. Online, that connection just needs encryption, and Traefik adds it. **No new real-time server.** I first planned a separate WebSocket server, and dropped it once I saw the browser already had what it needed.

Online, the broker has two WebSocket listeners, each on its own path on 443:

| Listener | Address | Who | May |
|---|---|---|---|
| Screens | `wss://<school>/mqtt` | any browser | listen only |
| Sensors | `wss://<school>/sensors` | each sensor, with its own token ({doc}`sensors`) | send its own reps only |

**The v0.5.0 lesson:** the screens' listen-only rules file was readable by root only, so Mosquitto couldn't read it and stopped. It passed on my Mac because Docker there doesn't enforce file permissions. **Test anything permission-sensitive on real Linux.**

## Things I passed on

- **A rented server.** It skips every home-network question, for a monthly bill. I had the hardware, and running it myself, router and all, was the point.
- **A tunnel service.** No router changes, and it hides my home address. But the sensors were going to use raw MQTT on 8883 then, and most tunnels only expect web traffic. Sensors moved to 443 later, so that reason is gone. I kept port forwarding because it works, and learning the networking was the point. The tunnel stays the fallback if my provider ever blocks the ports.
- **A second node.** A Mac mini was going to join. I cut it on Oct 14: k3s only runs on Linux, so the Mac would need a VM, and an Apple chip would mean building every image twice. Nothing assumes one node.
- **One address with a path per school** (`<domain>/<school>/`). The browser keeps saved data per address, not per path, so schools would share one store, and one school's sign-in would overwrite another's.
- **k3s on the local install too.** One machine, one school. Compose is the right size.

## What it cost

- **Two setups for the same images:** Compose on the local install, manifests on the remote server.
- **One server, so no failover.** k3s restarts a crashed container on its own, but if the Dell or the house's internet is down, the site is down.
- **Only one Traefik per machine.** It holds the ports itself, so an update stops the old one before starting the new one: a few seconds offline.
- **Two Mosquitto settings files** (local and remote) that say the same thing apart from the screens listener. Change one, change both.
- **The screens listener is open to read.** Anyone can listen on the app's topics. Fine while the data is test data; it gets logins before a real program uses it.

How each change gets onto the Dell is its own page: {doc}`releases`.
