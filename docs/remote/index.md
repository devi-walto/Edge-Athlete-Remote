<!--
this section — Edge Athlete run from anywhere instead of from a gym's own network.

Its own section rather than more journal pages because almost everything in it is
DECIDED BUT NOT BUILT. The journal describes code that exists; this describes code
that is about to. Keeping them apart means nobody reads a plan here as a description
of what the system does today. As each piece lands, its reasoning moves into the
journal page for that part and the page here shrinks to a pointer.
-->

# Remote

The same system, reachable from anywhere. A coach runs a session over a video call,
athletes on their own networks open the rack screen, lift with their own sensor, and
the workout is saved on the server — the same flow as the gym, without the gym's
network.

:::{important}
**Status: decided, not built.** Every page in this section records a decision and
its reasoning. Where something already exists in the code, the page says so and
links to it.
:::

## What changes and what does not

**Nothing about a workout changes.** The rack screen, the set lifecycle, the plan, the
reports, the database — all the same code. The whole difference is **who can reach the
server, and how they prove who they are**:

| | Gym box | Hosted |
|---|---|---|
| Server lives | in the gym | on a cluster on the internet |
| Devices reach it over | the box's own Wi-Fi | the internet |
| The network is the boundary? | **yes** — only the room can connect | **no** — anyone can try |
| So who logs in | coaches only | coaches, and athletes |
| Encryption | not needed on a closed network | required everywhere |

Two decisions in the journal were written for a closed network and say, in their own
words, that they must be revisited if that ever changes: the open routes a rack tablet
uses, and "coach means logged in" (both in {doc}`../journal/apis`). This section is
that revisit.

## The pages

**{doc}`deployments`**
: The ways this can be run, which ones are worth building, and why "a coach exposes
  his own gym box to the internet" is not one of them.

**{doc}`databases`**
: One database per installation — and why that makes moving a program between a gym
  box and the hosted service a copy rather than a migration.

**{doc}`access`**
: Who creates athletes, who gets a login, how a remote athlete reaches their rack
  screen, and what an athlete login can and cannot do.

**{doc}`sensors`**
: What it takes for a sensor to talk to a server on the internet instead of a box
  three metres away.

**{doc}`hosting`**
: The cluster, the certificates, and the two doors into the message broker.

**{doc}`directed-study`**
: What is being built by November 11, in what order, and what was deliberately left
  out.

```{toctree}
:maxdepth: 1
:hidden:

deployments
databases
access
sensors
hosting
directed-study
```
