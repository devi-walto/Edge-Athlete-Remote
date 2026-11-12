"""athlete_pages.py — the web addresses behind an online athlete's own pages (spec 10).

WHAT KIND OF FILE THIS IS: request handlers (Django "views"). Each answers one web
address; the work itself is in services/athlete_home.py.

WHY: an athlete signed in online needs a Home that says what's next, what's live and
what they did lately, from their own groups only.

  GET /api/athlete/home/              Home's data (Phase 0)
  GET /api/athlete/sessions/          All sessions, 20 at a time, ?before=<cursor> (Phase 3)
  GET /api/athlete/sessions/<id>/     one session as the athlete lived it (Phases 2, 3)

Signed in as an athlete, on a remote server. A coach is refused (403); a local install
answers 404, because a gym has no athlete logins.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from .permissions import IsAthlete, RemoteOnly
from .services.athlete_home import BadCursor, home_for, session_for, sessions_page


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def home(request):
    """Home for the signed-in athlete: what's coming up, what's live, their last five sessions"""
    return Response(home_for(request.user.athlete))


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def athlete_sessions(request):
    """The signed-in athlete's ended sessions, newest first, 20 at a time (?before= for the next page)"""
    try:
        return Response(sessions_page(request.user.athlete, request.query_params.get('before')))
    except BadCursor:
        raise ValidationError({'before': 'Not a page this server handed out.'})


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def athlete_session(request, session_id):
    """One session the signed-in athlete lifted in: their own sets by movement, with totals"""
    found = session_for(request.user.athlete, session_id)
    if found is None:
        raise NotFound()
    return Response(found)
