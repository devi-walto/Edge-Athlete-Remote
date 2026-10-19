"""remote_sessions.py — the web address an athlete's phone calls to join a session.

WHAT KIND OF FILE THIS IS: a request handler (a Django "view"). It answers one web
address, POST /api/sessions/<id>/join/, and passes the work to
services/session_join.py, which holds the rules.

WHY: online, an athlete opens the session link their coach shared, and their phone
calls this. The server checks they belong in the session, makes (or finds) their own
rack, checks them in on it and points their own sensor at it (spec 04, Phase 1).

Athletes only, and only on a remote server: a local install answers 404.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .permissions import IsAthlete, RemoteOnly
from .services.session_join import JoinRefused, join


@api_view(['POST'])
@permission_classes([RemoteOnly, IsAthlete])
def session_join(request, session_id):
    try:
        rack, sensor = join(session_id, request.user.athlete)
    except JoinRefused as refused:
        body = {'code': refused.code, 'detail': refused.detail}
        if refused.session:
            body['session'] = refused.session
        return Response(body, status=refused.status)
    return Response({
        'rack_number': rack.rack_number,
        # id too: the rack screen names its sensor by id when it starts a set.
        'sensor': ({'id': sensor.pk, 'node_id': sensor.node_id, 'last_seen': sensor.last_seen}
                   if sensor else None),
    })
