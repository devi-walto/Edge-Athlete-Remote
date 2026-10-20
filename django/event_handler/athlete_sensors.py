"""athlete_sensors.py — the web addresses for adding and removing an athlete's own sensor.

WHAT KIND OF FILE THIS IS: request handlers (Django "views"), not a database change.
Each one answers one web address: it receives a request, does the job, and sends back
a reply. The urls.py files list which address goes to which handler.

WHY: online, an athlete adds their own sensor without anyone's help (spec 14). The
rules (a one-time code, the sensor's own token, a sensor already owned is refused)
live in services/sensor_claims.py; these handlers are just the doors to them.

The athlete's side, signed in as the athlete:
  POST   /api/athlete/sensor-code/           a one-time code for "Add my sensor"
  GET    /api/athlete/sensors/               my sensors
  DELETE /api/athlete/sensors/<sensor id>/   remove one of my sensors
The sensor's side, open to anyone, because a sensor has no login yet: the code is
what proves it may join. Slowed down after repeated wrong codes:
  POST   /api/sensors/claim/                 {code, node_id} -> its login
The coach's side:
  DELETE /api/athletes/<id>/sensors/<sensor id>/   remove an athlete's lost sensor

Remote only. A local install answers 404: gym sensors are linked to racks by a coach,
on the gym's own Wi-Fi, as before.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .coach_auth import LimitWrongAttempts
from .models import Athlete, Node
from .permissions import IsAthlete, IsCoach, RemoteOnly
from .services import sensor_claims, sensor_logins


def _sensor_row(sensor):
    return {'node_id': sensor.node_id, 'last_seen': sensor.last_seen,
            'is_active': sensor.is_active}


def _remove(sensor):
    try:
        sensor_claims.remove(sensor)
    except sensor_logins.SensorDoorError:
        return Response({'code': 'sensors_door_unavailable',
                         'detail': "The school can't remove sensors right now. Try again "
                                   "in a few minutes."}, status=503)
    return Response(status=204)


# ───────────────── the athlete's side ─────────────────

@api_view(['POST'])
@permission_classes([RemoteOnly, IsAthlete])
def sensor_code(request):
    """A one-time code to give a new sensor. Shown once; works once, for 15 minutes."""
    code, expires_at = sensor_claims.issue_code(request.user.athlete)
    response = Response({'code': code, 'expires_at': expires_at}, status=201)
    response['Cache-Control'] = 'no-store'
    return response


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def my_sensors(request):
    sensors = Node.objects.filter(owner=request.user.athlete).order_by('node_id')
    return Response({'sensors': [_sensor_row(s) for s in sensors]})


@api_view(['DELETE'])
@permission_classes([RemoteOnly, IsAthlete])
def my_sensor(request, node_id):
    sensor = Node.objects.filter(owner=request.user.athlete, node_id=node_id).first()
    if sensor is None:
        return Response({'detail': 'sensor not found'}, status=404)
    return _remove(sensor)


# ───────────────── the sensor's side ─────────────────

class SensorClaimView(LimitWrongAttempts, APIView):
    """A sensor claims itself with an athlete's code and gets its own login.

    Open to anyone (a sensor has no login yet), no sign-in read, never kept by a
    browser. A code that doesn't work (400) counts as a wrong try."""
    attempt_scope = 'sensor_claim'
    authentication_classes = []
    permission_classes = [RemoteOnly]

    def attempt(self, request):
        try:
            login = sensor_claims.claim(request.data.get('code'), request.data.get('node_id'))
        except sensor_claims.ClaimRefused as refused:
            response = Response({'code': refused.code, 'detail': refused.detail},
                                status=refused.status)
        else:
            # The token is in this reply and nowhere else; the sensor keeps it.
            response = Response(login, status=201)
        response['Cache-Control'] = 'no-store'
        return response


# ───────────────── the coach's side ─────────────────

@api_view(['DELETE'])
@permission_classes([RemoteOnly, IsCoach])
def athlete_sensor(request, athlete_id, node_id):
    """Remove an athlete's sensor (lost, stolen, or passed on). Its sets stay."""
    athlete = Athlete.objects.filter(pk=athlete_id).first()
    sensor = athlete and Node.objects.filter(owner=athlete, node_id=node_id).first()
    if not sensor:
        return Response({'detail': 'sensor not found'}, status=404)
    return _remove(sensor)
