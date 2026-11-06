<!--
this section — the decisions that only apply to the remote server: the same app,
reached over the internet instead of a gym's own Wi-Fi.

It's a child of Core because it stands on Core: same images, same tables, same
messages, same screens. These pages only cover what had to change once the
network stopped being the lock.
-->

# Remote

The same app, reachable from anywhere. A coach runs a session over a video call, athletes on their own networks open their own rack screen and lift with their own sensor, and the workout is saved on the server: the same flow as the gym, without the gym's network.

**Nothing about a workout changes.** The rack screen, the set lifecycle, the plans, the reports and the database tables are all {doc}`Core <../index>`. The whole difference is who can reach the server, and how they prove who they are:

| | Local install | Remote server |
|---|---|---|
| Server lives | in the gym | k3s on a Dell at my house |
| Devices reach it over | the base station's own Wi-Fi | the internet |
| The network is the lock? | **yes**: only the room can connect | **no**: anyone can try |
| Who logs in | coaches only | coaches and athletes |
| Encryption | not needed on a closed network | required everywhere |

## The pages, in reading order

**{doc}`deployments`**
: The ways this can be run, why "a coach opens his own local install to the internet" isn't one of them, and the one setting (`EA_DEPLOYMENT`) that keeps both installs the same app.

**{doc}`hosting`**
: k3s on the Dell, Traefik in place of nginx, HTTPS that renews itself, and what broke on the way.

**{doc}`databases`**
: One database per school, in one shared Postgres.

**{doc}`releases`**
: How a change gets from a pull request onto every school, demo school first.

**{doc}`access`**
: Login links, session links, and how the server tells a coach from an athlete.

**{doc}`virtual-racks`**
: How a remote athlete gets a rack of their own, and the shared-rack login that's decided but not built.

**{doc}`sensors`**
: An athlete's own sensor, set up from their phone, sending reps safely over the internet.

```{toctree}
:maxdepth: 1
:hidden:

deployments
hosting
databases
releases
access
virtual-racks
sensors
```
