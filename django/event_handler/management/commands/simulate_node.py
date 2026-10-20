# simulate_node.py - fake rack sensor for development and live demos.
#
# The real nodes don't exist yet. This stands in for one: it publishes the same
# pulse and rep messages on the same topics, so everything downstream — the
# tablet, Django's subscriber, the wall display — can be built and demoed
# against it without any hardware in the room.
#
# IT ALSO KNOWS WHEN TO SHUT UP. A real sensor bolted to a rack nobody is using
# should not be filling the broker with reps, and in a demo a rack that chatters
# while nobody stands at it makes the whole room look like noise. So the rep
# stream is GATED on whether the linked rack is actually busy — see the gate
# section below for what "busy" means and why it is a DB read rather than an
# HTTP call.
#
# The heartbeat is NOT gated, deliberately. Pulses are how Django knows the node
# is alive; going quiet on those would make an idle rack look like a dead one.
#
# TWO WAYS TO RUN IT.
#   --node-id rack_1   one sensor, as before (a local install's demo).
#   --seeded           every seeded demo athlete's OWN sensor at once (spec 04,
#                      Phase 5): what `eactl sim` runs on a remote school. Each one
#                      follows its athlete's rack, so it wakes when its athlete joins
#                      a session online and starts a set. With --stop-after it stops
#                      itself; however it stops (time up, Ctrl+C, or Kubernetes
#                      ending the job), its sensors are unlinked and marked inactive.

import json
import os
import signal
import threading
import time

import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, connection

from ...sensor_messages import build_pulse_payload, build_rep_payload

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

PULSE_INTERVAL_SECONDS = 5.0
# How often the gate re-reads the database. Short enough that a demo feels
# instant when a coach starts a set, long enough that an idle simulator is not
# hammering Postgres all afternoon.
GATE_POLL_SECONDS = 2.0

# The gate's three settings, from strictest to loosest.
MODE_LIFTING = "lifting"
MODE_CHECKIN = "checkin"
MODE_ALWAYS = "always"


# ── the gate ────────────────────────────────────────────────────────────────
#
# WHY A DATABASE READ AND NOT A REST CALL. This is a Django management command,
# so it is already inside the ORM — GET /api/sessions/active/status/ would be
# the same rows via an HTTP hop, plus a base URL to configure and a service to
# be up. Reading directly means the simulator has no opinion about where the web
# server lives, and it cannot be broken by nginx.
#
# It reuses active_session() rather than writing its own "which day is live"
# query, because that helper exists precisely so nothing disagrees about it —
# four hand-written copies of that rule is what caused canon D18.


def rack_for_node(node_id):
    """The rack this node is linked to, or None if it isn't linked to one yet.

    Re-read on every poll rather than resolved once at startup, so a coach who
    links the sensor to a rack mid-demo sees it wake up on its own instead of
    having to restart the simulator.
    """
    from ...models import Node

    node = Node.objects.filter(node_id=node_id).values("rack_number").first()
    return node["rack_number"] if node else None


def rack_activity(rack_number, mode):
    """Is this rack busy right now? -> (active, token, why)

    `token` identifies WHAT is happening, so the caller can tell one set from
    the next: when it changes, a new set started and rep numbering restarts at
    1. `why` is a short human phrase for the log — a simulator that goes quiet
    without saying why is indistinguishable from one that has crashed.
    """
    from ...models import RackCheckIn, Set
    from ...services.active_session import active_session

    if mode == MODE_ALWAYS:
        return True, "always", "gate off"

    if rack_number is None:
        return False, None, "node is not linked to a rack"

    session = active_session()
    if session is None:
        return False, None, "no training day is running"

    # Athletes this rack currently owns. Check-ins are add-only and newest-wins
    # (the same shape as reference maxes), so an athlete's current rack is simply
    # their newest row — which is why this walks newest-first and keeps the first
    # one seen per athlete rather than filtering on rack_number in SQL. Filtering
    # directly would match an athlete who checked in here earlier and has since
    # moved to another rack.
    here = set()
    seen = set()
    for row in (RackCheckIn.objects
                .filter(session=session)
                .order_by("athlete_id", "-checked_in_at")
                .values_list("athlete_id", "rack_number")):
        athlete_id, rack = row
        if athlete_id in seen:
            continue
        seen.add(athlete_id)
        if rack == rack_number:
            here.add(athlete_id)

    if not here:
        return False, None, f"nobody is checked in at rack {rack_number}"

    if mode == MODE_CHECKIN:
        token = "checkin:" + ",".join(str(a) for a in sorted(here))
        return True, token, f"{len(here)} checked in at rack {rack_number}"

    # MODE_LIFTING — the strict one. A set with no end time is a set in progress;
    # that is the same test GET /api/sessions/active/status/ uses to call an
    # athlete "lifting", so the simulator and the room screens agree.
    open_set = (Set.objects
                .filter(session=session, athlete_id__in=here, ended_at__isnull=True)
                .order_by("-started_at", "-id")
                .values("id", "athlete_id")
                .first())
    if open_set is None:
        return False, None, f"checked in at rack {rack_number}, but no set is open"

    return True, f"set:{open_set['id']}", f"set {open_set['id']} is open"


class Command(BaseCommand):
    help = ("Simulate a rack sensor node, publishing fake pulse + rep traffic over MQTT. "
            "Reps pause while the linked rack is idle; pulses never stop.")

    def add_arguments(self, parser):
        which = parser.add_mutually_exclusive_group(required=True)
        which.add_argument("--node-id", type=str,
                           help="Node ID to simulate, e.g. rack_1")
        which.add_argument("--seeded", action="store_true",
                           help="Simulate every seeded demo athlete's own sensor at once "
                                "(spec 04, Phase 5; what `eactl sim` runs). On stopping, "
                                "they are unlinked from their racks and marked inactive.")
        parser.add_argument("--stop-after", type=float, default=None, metavar="MINUTES",
                            help="Stop by itself after this many minutes (default: run until "
                                 "stopped). `eactl sim` uses 120.")
        parser.add_argument("--rack", type=int, default=None,
                            help="Rack number to watch (--node-id only). Default: whatever "
                                 "rack this node is linked to in the database.")
        parser.add_argument("--interval", type=float, default=3.0,
                            help="Seconds between reps (default: 3.0)")
        parser.add_argument("--reps-per-set", type=int, default=5,
                            help="Reps before a rest, in 'always' mode only (default: 5). "
                                 "In the gated modes the tablet decides where a set ends.")
        parser.add_argument("--active-when", choices=[MODE_LIFTING, MODE_CHECKIN, MODE_ALWAYS],
                            default=MODE_LIFTING,
                            help="When to publish reps. 'lifting' (default): only while a set "
                                 "is open at the rack. 'checkin': whenever anyone is checked in "
                                 "there. 'always': never pause — the old behaviour.")

    def handle(self, *args, **options):
        from ...models import Node

        fixed_rack = options["rack"]
        mode = options["active_when"]
        seeded = options["seeded"]

        if seeded:
            # The seeded demo athletes' own sensors: marked simulated, owned by a
            # simulated athlete. Woken (made active) for the length of this run.
            nodes = Node.objects.filter(is_simulated=True, owner__is_simulated=True)
            node_ids = list(nodes.values_list("node_id", flat=True))
            if not node_ids:
                raise CommandError("No seeded demo sensors here. Seed the school first.")
            nodes.update(is_active=True)
            self.stdout.write(f"Woke {len(node_ids)} demo sensor(s): {', '.join(node_ids)}")
            fixed_rack = None   # each follows its own athlete's rack
        else:
            node_id = options["node_id"]
            # Register before publishing, the way real firmware should.
            #
            # Pulses from an unknown node are REJECTED ("node is not registered"), so
            # without this a second simulated rack published forever into nothing: the
            # container ran, the log looked healthy, and no node ever appeared for a
            # coach to link.
            #
            # Not marked simulated here. is_simulated is now a label only (it no
            # longer bars a sensor from racks or hides its sets; spec 04, Phase 5),
            # and the seeder is what marks its own sensors. This command just drives
            # whichever sensor it is given.
            node, created = Node.objects.get_or_create(node_id=node_id)
            self.stdout.write(
                f"{'Registered' if created else 'Found'} node {node_id} "
                f"(rack: {node.rack_number if node.rack_number is not None else 'unassigned'})"
            )
            if node.rack_number is None:
                self.stdout.write(
                    "  ^ link it to a rack in the coach admin page before it publishes reps"
                )
            node_ids = [node_id]

        self.stdout.write(f"Starting simulate_node for {', '.join(node_ids)} "
                          f"(gate: {mode}, rack: {fixed_rack or 'from database'})")

        client = mqtt.Client()
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()

        # One stop signal for every thread. Set by the time limit, Ctrl+C, or
        # SIGTERM, which is what Kubernetes sends when `eactl sim --stop` deletes
        # the Job, or when the Job's own hard time limit runs out.
        stop_event = threading.Event()
        previous_sigterm = signal.signal(signal.SIGTERM, lambda *_: stop_event.set())

        threads = []
        for node_id in node_ids:
            for target in (self._pulse_loop, self._rep_loop):
                thread = threading.Thread(
                    target=target, daemon=True,
                    args=(client, node_id, stop_event, fixed_rack, mode, options))
                thread.start()
                threads.append(thread)

        deadline = options["stop_after"] * 60 if options["stop_after"] else None
        try:
            if stop_event.wait(deadline):
                self.stdout.write("Asked to stop.")
            else:
                self.stdout.write(f"Time's up ({options['stop_after']:g} min).")
        except KeyboardInterrupt:
            self.stdout.write("\nStopping simulate_node...")
        finally:
            stop_event.set()
            for thread in threads:
                thread.join(timeout=5)
            client.loop_stop()
            client.disconnect()
            signal.signal(signal.SIGTERM, previous_sigterm)
            if seeded:
                # Unregister: off their racks and inactive, so nothing shows a
                # "live" sensor once the demo is over. Not deleted: each finished
                # set remembers the sensor that measured it.
                close_old_connections()
                Node.objects.filter(node_id__in=node_ids).update(rack_number=None, is_active=False)
                self.stdout.write(f"Unregistered {len(node_ids)} demo sensor(s).")

    def _pulse_loop(self, client, node_id, stop_event, fixed_rack, mode, options):
        """Heartbeats, never gated: an idle node is still a healthy node."""
        topic = f"edgeathlete/node/{node_id}/pulse"
        try:
            while not stop_event.is_set():
                close_old_connections()
                client.publish(topic, json.dumps(build_pulse_payload(node_id)), qos=1)
                stop_event.wait(PULSE_INTERVAL_SECONDS)
        finally:
            connection.close()   # each thread has its own; let it go with the thread

    def _rep_loop(self, client, node_id, stop_event, fixed_rack, mode, options):
        """Reps, only while this node's rack is busy (see the gate above)."""
        try:
            self._reps(client, node_id, stop_event, fixed_rack, mode, options)
        finally:
            connection.close()   # each thread has its own; let it go with the thread

    def _reps(self, client, node_id, stop_event, fixed_rack, mode, options):
        topic = f"edgeathlete/node/{node_id}/rep"
        interval, reps_per_set = options["interval"], options["reps_per_set"]
        rep_number = 0
        last_token = None
        last_why = None
        while not stop_event.is_set():
            # Long-running: the database connection can be dropped underneath us
            # (idle timeout, a restart) and Django keeps handing back the dead one
            # until it is told to let go.
            close_old_connections()

            rack = fixed_rack if fixed_rack is not None else rack_for_node(node_id)
            active, token, why = rack_activity(rack, mode)

            # Say something only when the answer CHANGES.
            if why != last_why:
                state = "ACTIVE" if active else "idle"
                self.stdout.write(f"[{node_id}] {state} — {why}")
                last_why = why

            if not active:
                rep_number = 0
                last_token = None
                stop_event.wait(GATE_POLL_SECONDS)
                continue

            # A new set means rep numbering starts over.
            if token != last_token:
                rep_number = 0
                last_token = token

            rep_number += 1
            payload = build_rep_payload(node_id, rep_number)
            client.publish(topic, json.dumps(payload), qos=1)
            self.stdout.write(f"[{node_id}] rep {rep_number} -> {payload['mean_velocity']} m/s")

            # 'always' has no tablet telling it where a set ends, so it keeps the
            # original count-and-rest rhythm.
            if mode == MODE_ALWAYS and rep_number >= reps_per_set:
                rep_number = 0
                self.stdout.write(f"[{node_id}] set complete, resting")
                stop_event.wait(interval * 2)
            else:
                stop_event.wait(interval)
