# Mosquitto

*Both installs*

**Why I picked it.** MQTT is built for small devices: tiny messages, delivery guarantees (QoS), WebSockets for the browser, and TLS. And we needed a broker for the sensors anyway, so it carries the screens' live updates too.

**What it is.** The message broker — a post office. Programs publish to a named
channel (a *topic*), and anything subscribed to that channel gets a copy. Nobody
addresses anybody directly.

**How we use it.** Every live message in the system. A rep never touches the server:

```
node ──rep──► mosquitto ──► rack screen ──► browser storage
                                              │  (one write per SET, not per rep)
                                              ▼
                                        POST /api/sets/{id}/complete/ ──► django ──► postgres
```

Heartbeats are the exception — those Django *does* listen to:

```
node ──pulse──► mosquitto ──► mqtt-listener ──► postgres (battery, signal, last_seen)
```

And Django announces changes back out, so screens refetch:

```
django ──► monitoring-publisher ──► mosquitto ──► room display + coach's live room
```

**Where it lives.** **Local:** container `edgeathlete-mosquitto`, two listeners on the same broker: **1883** for sensors and Django, **9001** for browsers (the same MQTT over WebSockets). Config in `mosquitto/mosquitto.conf`. **Remote:** `eclipse-mosquitto:2.0.22`, one per school, with three listeners: 1883 for Django and the workers (inside the cluster only), 9001 for screens (`/mqtt`, listen only) and 9002 for sensors (`/sensors`, a token each, through the dynamic security plugin). Config in `k8s/app/base/mosquitto-remote.conf`.

**Worth knowing.** ⚠️ On a local install it allows anonymous connections: anything on the gym's Wi-Fi can publish. That's a known, accepted gap on a closed network. Online, nobody but a sensor with its token can publish anything.

⚠️ The listen-only rules file must be readable by the broker's own user. v0.5.0 took the demo school's live updates down because it was root-only; Docker on a Mac doesn't enforce file permissions, so test it on real Linux.

**More:** {doc}`../core/real-time` for why there is no WebSocket layer in Django ·
{doc}`../../handbook/reference/mqtt-topics` for every topic, its payload, and who hears it
