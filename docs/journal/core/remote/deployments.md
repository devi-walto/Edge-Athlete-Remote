<!--
this page — the ways Edge Athlete can be run, which ones are worth building,
and the one setting that keeps them the same app.

The tempting option (a coach opens his own gym's local install to the internet)
sounds cheaper than it is, and it will be suggested again. Try 2 is the answer.
-->

# Deployments

*Oct 2 – Oct 16, 2026 · specs 05, 12*

## Tool changes at a glance

| Job | How | Where it lives |
|---|---|---|
| Which kind of install this is | **one environment variable, `EA_DEPLOYMENT`**: `local` (the default) or `remote` | `basestation_config/deployment_mode.py` |
| Asking it in code | **`is_hosted()`**, and nothing else reads the variable | `event_handler/deployment.py` |
| Asking it from a screen | **`GET /api/system/info/`**: `deployment`, `version`, school name. Open, so the sign-in screen can ask | `event_handler/deployment.py` |
| Testing both | **CI runs the whole backend suite twice**, once as `local`, once as `remote` | `.github/workflows/ci.yml` |

:::{warning}
**Never read `EA_DEPLOYMENT` yourself. Call `is_hosted()`.** If each feature read the setting its own way, two of them would eventually disagree. And a misspelled value **refuses to start** on purpose: quietly falling back to `local` would open a remote server to the internet with gym rules because of a typo.
:::

## The problem

Until now there was one answer: a local install in the gym, serving its own Wi-Fi, with nothing reaching it from outside. A session over a video call breaks that. The athletes aren't in the room, so they aren't on the room's network.

The only things that really differ between the options are where the server lives, how devices reach it, and whether the internet can reach it. Everything else is configuration.

## Try 1: put the local install on the gym's network

Turn the base station's own Wi-Fi off and join the gym's instead, so it's reachable from more places.

**Why I moved on:** it isn't a new shape, it's a setting, and the base station's own Wi-Fi stays either way. Devices join the base station's network, so they never need the gym's Wi-Fi password: no asking the school's IT, no captive portal, nothing to redo when the gym changes its password. The gym's network, wired or wireless, is only ever the base station's **uplink**, how it reaches the internet for updates. And it still doesn't reach an athlete at home.

## Try 2: let a coach open his local install to the internet

It has one real merit: the data never leaves the coach's hardware. For a video-call session it loses everywhere else:

- **It needs inbound access** to a network nobody on the project controls: port forwarding, a changing public address, a firewall set up by a strength coach. Every gym becomes a different network to debug from a distance.
- **The security lands on the base station:** certificates, logins, patches and backups, on a machine in a weight room nobody watches.
- **Every base station is an island.** A fix has to reach each one separately.
- **Doing it properly means an outbound tunnel to a relay,** and at that point it's the remote server's networking rebuilt worse.

## Try 3: a remote server, same app

**This is where I landed.** A remote server is a local install that happens to run on k3s instead of Compose: same images, same database tables, same message topics, same screens ({doc}`hosting`). It isn't a second app. It's the same one, reached differently, and `EA_DEPLOYMENT` is the only switch.

The things that do behave differently online all go through `is_hosted()`:

- rack routes need a signed-in athlete instead of being open ({doc}`access`);
- the sign-in limit counts wrong tries in Django instead of nginx;
- a remote server refuses to start with `DEBUG` on or with no allowed hosts, and trusts form posts only from `https://` plus those hosts (`remote_settings()` in `deployment_mode.py`).

| Shape | Server lives | Devices join | Internet | Status |
|---|---|---|---|---|
| **Local install** | in the gym | the base station's Wi-Fi | optional, **outbound only** | Built. The default |
| **Remote server** | k3s on the Dell | over the internet | yes, by design | Built |
| **Both**, a local install that hands off to the remote server | both | the base station's Wi-Fi, and the internet | outbound only | Later. A copy, then add-only merges ({doc}`databases`), never live sync |

If keeping data on a school's own hardware ever becomes a hard requirement, the answer is **both**: the local install stays the source of truth and connects *out*. Never open it *in*.

## Things I passed on

- **A coach opening his own local install to the internet.** Try 2.
- **A second app for remote.** Two apps drift. One codebase, one switch.
- **k3s on the local install too.** One machine running one school. Compose is the right size.

## What it cost

- **Two ways to run the same images:** Compose on the local install, k3s on the remote server. The images are shared, the orchestration isn't, and the two can't be allowed to drift.
- **Every backend test runs twice in CI.** Slower pull requests, but a change that only works on one install can't merge.
- **The local install stays offline-first.** Nothing added for the remote server may make a local install need the internet to run a session.
