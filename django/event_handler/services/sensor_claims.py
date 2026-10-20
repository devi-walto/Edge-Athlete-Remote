"""Sensor claims: how an athlete adds their own sensor, and how a sensor is removed.

WHY: online, an athlete sets up their sensor at home without anyone's help (spec 14).
  1. On their athlete page they press "Add my sensor" and get a one-time code, like
     K7MQ-2XPR. It works once, for 15 minutes; only a hash of it is stored.
  2. They give the sensor the code (over USB now, the sensor's own setup page later).
  3. The sensor sends the code and its ID to the school. If the code works, the
     sensor now belongs to that athlete, and gets its own sensor token: a long random
     secret it keeps and uses every time it connects. The broker is told at once that
     this sensor, with this token, may send only its own messages.

The athlete's account password never touches the sensor; the code can only add a
sensor, once. A sensor that already belongs to someone else is refused, so nobody can
take over another athlete's sensor by typing its ID: their coach removes it first.

Removing a sensor takes its login away on the broker (it is disconnected at once),
gives it no owner and no rack, and keeps its record and every set it measured.

The rules for one-time codes live in one_time_secrets.py, and the broker side in
sensor_logins.py; this file joins them up.
"""
from datetime import timedelta

from django.db import transaction

from ..models import Node, SensorClaimCode
from . import one_time_secrets, sensor_logins

CODE_LIFETIME = timedelta(minutes=15)
# Where the sensor connects with its token, on the school's own address.
SENSORS_PATH = "/sensors"


class ClaimRefused(Exception):
    """Why a claim didn't go through. `code` is for the sensor; `detail` for people."""

    def __init__(self, code, detail, status):
        super().__init__(detail)
        self.code, self.detail, self.status = code, detail, status


def _code_does_not_work():
    # The one answer for every way a code can fail.
    return ClaimRefused(
        'code_does_not_work',
        "That code doesn't work. Get a new one on your athlete page (Add my sensor).", 400)


def issue_code(athlete):
    """A new claim code for this athlete. Returns (code shown as XXXX-XXXX, expires_at).
    Any unused code they had stops working."""
    text, row = one_time_secrets.issue(SensorClaimCode, one_time_secrets.CODE, CODE_LIFETIME,
                                       owner={'athlete': athlete})
    return text, row.expires_at


def latest_code(athlete):
    """How the athlete's newest code is doing, for their page while it waits:
    {"status": waiting | used | expired | none, "expires_at", "sensor": its ID or None}.
    The code itself isn't here: only its hash is stored."""
    code = (SensorClaimCode.objects.filter(athlete=athlete).select_related('sensor')
            .order_by('-created_at', '-pk').first())
    if code is None:
        return {"status": "none", "expires_at": None, "sensor": None}
    if code.used_at:
        status = "used"
    elif code.still_works():
        status = "waiting"
    else:
        status = "expired"   # ran out, or a newer one cancelled it
    return {"status": status, "expires_at": code.expires_at,
            "sensor": code.sensor.node_id if code.sensor else None}


def claim(code_text, sensor_id):
    """A sensor claims itself with an athlete's code. Returns its login:
    {"username": its ID, "token": its new sensor token, "path": "/sensors"}.

    All or nothing: if the broker can't be told, nothing is saved and the code still
    works. Raises ClaimRefused. A code that doesn't work, for any reason, gets the same
    answer, and is checked first, so only someone holding a working code learns
    whether a sensor ID is taken.
    """
    found = one_time_secrets.find(SensorClaimCode, one_time_secrets.CODE, code_text)
    if found is None:
        raise _code_does_not_work()
    if not sensor_logins.SENSOR_ID.match(str(sensor_id or '')):
        raise ClaimRefused('bad_sensor_id', "That isn't a usable sensor ID.", 400)

    token = one_time_secrets.new_token()
    with transaction.atomic():
        code = one_time_secrets.lock_if_still_works(SensorClaimCode, found)
        if code is None:
            raise _code_does_not_work()
        sensor, _ = Node.objects.select_for_update().get_or_create(node_id=sensor_id)
        if sensor.owner_id not in (None, code.athlete_id):
            raise ClaimRefused(
                'owned_by_someone_else',
                "This sensor belongs to another athlete. Ask your coach to remove it "
                "from them first.", 409)
        sensor.owner_id = code.athlete_id
        sensor.is_active = True   # claimed means ready to use (spec 04 attaches active ones)
        sensor.save(update_fields=['owner', 'is_active'])
        code.sensor = sensor
        code.save(update_fields=['sensor'])
        one_time_secrets.mark_used(code)
        # Last, so a broker that can't be reached undoes everything above.
        try:
            sensor_logins.add(sensor_id, token)
        except sensor_logins.SensorDoorError as exc:
            raise ClaimRefused('sensors_door_unavailable',
                               "The school can't take sensors right now. Try again in a "
                               "few minutes.", 503) from exc
    return {"username": sensor_id, "token": token, "path": SENSORS_PATH}


def remove(sensor):
    """Take this sensor away from its athlete: its login on the broker goes (it is
    disconnected at once), and it has no owner and no rack. Its record and its sets
    stay. Raises sensor_logins.SensorDoorError if the broker can't be told, and then
    changes nothing."""
    with transaction.atomic():
        sensor = Node.objects.select_for_update().get(pk=sensor.pk)
        sensor.owner = None
        sensor.rack_number = None
        sensor.save(update_fields=['owner', 'rack_number'])
        sensor_logins.remove(sensor.node_id)
