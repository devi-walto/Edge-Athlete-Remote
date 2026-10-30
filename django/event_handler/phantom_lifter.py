# phantom_lifter.py — a seeded demo athlete who lifts on their own, for a live demo.
#
# WHY: online, a demo used to need a real person per athlete: someone signs in, joins
# the session and presses through every set, or the simulated sensors sit silent. A
# phantom lifter does that person's part, so a room full of invented athletes trains
# in parallel while one real athlete lifts with a real sensor beside them.
#
# IT GOES THROUGH THE FRONT DOOR. A phantom calls the same routes, in the same order,
# that an athlete's phone does: join the session (which gives them their own rack),
# take control of that rack, count down, start a set, report each rep, finish the
# set, rest. So the coach's live room and the room display show a phantom exactly as
# they would show a person, and nothing in the rack rules is loosened for it.
#
# THE ONE THING IT NEEDS: A LOGIN THAT NOBODY CAN USE. Online, an athlete's own rack
# answers to that athlete's login and nobody else's (spec 04), so a phantom needs one.
# The simulator gives each phantom a login with no usable password for as long as it
# runs, and removes it when it stops. Nobody can sign in with it; it exists so the
# server sees "the rack's owner".
#
# WHO NEVER BECOMES ONE: the hands-on demo athlete (the seeder's MANUAL_ATHLETE), any
# athlete who isn't simulated, and any simulated athlete someone CAN sign in as (a
# coach who sent one a login link is using them by hand).
#
# Online only: on a gym box a rack is a tablet a coach set up, and simulating the
# tablets themselves is the shared-racks work (spec 18).
import base64
import random
import secrets
import time
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import close_old_connections
from django.utils.text import slugify

PHANTOM_LOGIN_PREFIX = "phantom-"


def phantom_username(athlete):
    return PHANTOM_LOGIN_PREFIX + slugify(athlete.name)


def is_phantom_login(user):
    """A login made by the simulator: our prefix and no usable password."""
    return bool(user and user.username.startswith(PHANTOM_LOGIN_PREFIX) and not user.has_usable_password())


def phantom_athletes(manual_name):
    """The seeded athletes a phantom may play: simulated, owning an active simulated
    sensor, not the hands-on one, and not one somebody can actually sign in as."""
    from .models import Athlete

    chosen = []
    for athlete in (Athlete.objects.filter(is_simulated=True, is_active=True)
                    .exclude(name=manual_name).select_related("user").order_by("name")):
        if athlete.user_id and not is_phantom_login(athlete.user):
            continue
        if not athlete.owned_nodes.filter(is_simulated=True).exists():
            continue
        chosen.append(athlete)
    return chosen


def give_login(athlete):
    """Attach a login nobody can use (made once, reused if a run was cut short)."""
    user = athlete.user if athlete.user_id else None
    if user is None:
        user, _ = User.objects.get_or_create(username=phantom_username(athlete))
        user.set_unusable_password()
        user.is_active = True
        user.save()
        athlete.user = user
        athlete.save(update_fields=["user"])
    return user


def take_logins_back(athletes):
    """Remove the phantoms' logins. Their athletes, sets and sensors stay."""
    from .models import Athlete

    for athlete in Athlete.objects.filter(pk__in=[a.pk for a in athletes]).select_related("user"):
        user = athlete.user if athlete.user_id else None
        if is_phantom_login(user):
            athlete.user = None
            athlete.save(update_fields=["user"])
            user.delete()


def _site_host():
    for host in settings.ALLOWED_HOSTS:
        host = host.strip().lstrip(".")
        if host and host != "*":
            return host
    return "localhost"


def _controller_token():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")


class Refused(Exception):
    pass


class PhantomLifter:
    """One phantom, driven step by step from its own thread."""

    def __init__(self, athlete, node_id, publish_rep, log, pace):
        from rest_framework.test import APIClient

        self.athlete, self.node_id, self.publish_rep, self.log, self.pace = athlete, node_id, publish_rep, log, pace
        self.client = APIClient(HTTP_HOST=_site_host())
        self.client.force_authenticate(give_login(athlete))
        self.rack = None
        self.open_set = None      # {"id": ..., "reps": [...]} while a set is under way
        self.headers = {}
        self.last_heartbeat = 0.0

    # ── talking to the server, exactly as the phone does ──────────────────────

    def _call(self, method, path, body=None, controlled=False):
        # Each call is a real request through Django's handler, so its start and end
        # signals already tidy the thread's database connection, as for a phone.
        extra = self.headers if controlled else {}
        for _ in range(4):
            response = getattr(self.client, method)(f"/api{path}", body, format="json", **extra)
            # Too many rack commands this second: wait as long as the server asks.
            if response.status_code != 429:
                break
            time.sleep(float((getattr(response, "data", None) or {}).get("retry_after_seconds", 1)))
        if response.status_code >= 400:
            data = getattr(response, "data", None)
            code = data.get("code") if isinstance(data, dict) else None
            raise Refused(f"{method.upper()} {path} -> {response.status_code} {code or data}")
        return response.data

    def _version(self):
        return self._call("get", f"/racks/{self.rack}/state/")["state_version"]

    def _command(self, **fields):
        return {**fields, "command_id": str(uuid.uuid4()), "expected_state_version": self._version()}

    def _state(self, **fields):
        return self._call("patch", f"/racks/{self.rack}/state/", self._command(**fields), controlled=True)

    def heartbeat(self):
        if self.rack is not None and time.monotonic() - self.last_heartbeat >= 5:
            self._call("post", f"/racks/{self.rack}/controller/heartbeat/", {}, controlled=True)
            self.last_heartbeat = time.monotonic()

    def _wait(self, seconds, stop):
        """Wait, keeping the rack's lease alive like an open screen does."""
        end = time.monotonic() + seconds
        while not stop.is_set() and time.monotonic() < end:
            self.heartbeat()
            stop.wait(min(1.0, max(0.0, end - time.monotonic())))
        return not stop.is_set()

    # ── the athlete's part ─────────────────────────────────────────────────────

    def join(self, session_id):
        self.rack = self._call("post", f"/sessions/{session_id}/join/", {})["rack_number"]
        device = f"phantom-{self.athlete.pk}"
        identity = {"device_id": device, "client_instance_id": str(uuid.uuid4()),
                    "controller_token": _controller_token()}
        reply = self._call("post", f"/racks/{self.rack}/controller/acquire/", identity)
        self.headers = {
            "HTTP_X_RACK_DEVICE_ID": identity["device_id"],
            "HTTP_X_CLIENT_INSTANCE_ID": identity["client_instance_id"],
            "HTTP_X_CONTROLLER_TOKEN": identity["controller_token"],
            "HTTP_X_CONTROLLER_EPOCH": str(reply["controller_epoch"]),
        }
        self.last_heartbeat = time.monotonic()
        self.log(f"[{self.athlete.name}] joined, rack {self.rack}")

    def next_movement(self):
        progress = self._call("get", f"/sessions/active/athlete/{self.athlete.pk}/progress/")
        movements = progress.get("movements") or []
        if not movements:
            return None
        current = progress.get("current_exercise_id")
        # Plan done: start over at the first movement, so the room keeps moving.
        return next((m for m in movements if m["exercise_id"] == current), movements[0])

    def lift_one_set(self, session_id, stop):
        """Countdown, set, reps, finish, rest. False once asked to stop."""
        movement = self.next_movement()
        if movement is None:
            self.log(f"[{self.athlete.name}] has nothing planned; waiting")
            return self._wait(10, stop)

        self._state(phase="countdown", selected_athlete=self.athlete.pk,
                    selected_exercise=movement["exercise_id"], rep_count=0,
                    latest_mean_velocity=None, latest_peak_velocity=None, latest_color=None)
        if not self._wait(self.pace.get("countdown_seconds", 3), stop):
            return False

        node = self._node_pk()
        load = movement.get("last_weight_lbs") or movement.get("target_weight_lbs")
        created = self._call("post", "/sets/", self._command(
            session=session_id, athlete=self.athlete.pk, exercise=movement["exercise_id"],
            set_number=movement["next_set_number"], weight_lbs=load,
            is_makeup=False, rack_number=self.rack, node=node), controlled=True)

        reps = []
        self.open_set = {"id": created["id"], "reps": reps}
        planned = movement.get("target_reps") or 5
        top = movement.get("velocity_zone_max") or 0.8
        floor = movement.get("velocity_zone_min") or 0.4
        start = random.uniform(top - 0.08, top + 0.04)   # fresh: near the top of the zone
        for number in range(1, planned + 1):
            if not self._wait(self.pace["rep_seconds"] * random.uniform(0.85, 1.15), stop):
                return False
            mean = max(0.15, round(start - (number - 1) * random.uniform(0.02, 0.05), 3))  # tiring
            peak = round(mean + random.uniform(0.1, 0.25), 3)
            rep = {"mean_velocity": mean, "peak_velocity": peak,
                   "duration_ms": random.randint(650, 1100), "timestamp": _now_iso()}
            self.publish_rep(self.node_id, number, rep)     # the sensor's own message
            color = "green" if mean >= floor else "yellow"
            reps.append({"rep_number": number, **rep, "velocity_color": color})
            self._state(phase="active", rep_count=number, latest_mean_velocity=mean,
                        latest_peak_velocity=peak, latest_color=color)

        if not self._wait(self.pace.get("end_seconds", 1.5), stop):
            return False
        self._finish_open_set()
        self.log(f"[{self.athlete.name}] {movement['name']} set {movement['next_set_number']}: "
                 f"{len(reps)} reps")

        if not self._wait(self.pace.get("summary_seconds", 4), stop):   # a look at the summary
            return False
        self._state(phase="rest")
        if not self._wait(random.uniform(*self.pace["rest_seconds"]), stop):
            return False
        self._state(phase="idle")
        return True

    def _finish_open_set(self):
        """Save the set under way, the one batch the phone sends at End Set. With no
        reps yet (stopped between countdown and the first rep) it's a false set."""
        if self.open_set is None:
            return
        reps = self.open_set["reps"]
        if reps:
            body = dict(reps_completed=len(reps),
                        avg_velocity=round(sum(r["mean_velocity"] for r in reps) / len(reps), 3),
                        peak_velocity=max(r["peak_velocity"] for r in reps),
                        is_false_set=False, reps=reps)
        else:
            body = dict(reps_completed=0, avg_velocity=None, peak_velocity=None,
                        is_false_set=True, reps=[])
        self._call("post", f"/sets/{self.open_set['id']}/complete/", self._command(**body),
                   controlled=True)
        self.open_set = None

    def _node_pk(self):
        from .models import Node

        return Node.objects.filter(node_id=self.node_id).values_list("pk", flat=True).first()

    def leave(self):
        """Stopped: finish a set under way with the reps so far, back to idle, and let
        go of the rack, so nothing is left open or stuck "active" on the coach's screen."""
        if self.rack is None:
            return
        for step in (self._finish_open_set,
                     lambda: self._state(phase="idle"),
                     lambda: self._call("post", f"/racks/{self.rack}/controller/release/",
                                        self._command(), controlled=True)):
            try:
                step()
            except Exception:   # noqa: BLE001 - best effort on the way out
                pass


def _now_iso():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def run_phantom(athlete, node_id, publish_rep, log, stop, pace, start_delay):
    """A phantom's whole life: wait its turn, join, lift until told to stop."""
    from .services.active_session import active_session

    if stop.wait(start_delay):
        return
    phantom = None
    try:
        close_old_connections()
        session = active_session()
        if session is None:
            log(f"[{athlete.name}] no session is running; not joining")
            return
        phantom = PhantomLifter(athlete, node_id, publish_rep, log, pace)
        phantom.join(session.id)
        while not stop.is_set():
            if not phantom.lift_one_set(session.id, stop):
                break
    except Refused as refused:
        log(f"[{athlete.name}] stopped: {refused}")
    finally:
        if phantom is not None:
            phantom.leave()
