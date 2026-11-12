"""athlete_pages.py — the web addresses behind an online athlete's own pages (spec 10).

WHAT KIND OF FILE THIS IS: request handlers (Django "views"). Each answers one web
address; the work itself is in services/athlete_home.py.

WHY: an athlete signed in online needs a Home that says what's next, what's live and
what they did lately, from their own groups only.

  GET /api/athlete/home/   Home's data (Phase 0)

Signed in as an athlete, on a remote server. A coach is refused (403); a local install
answers 404, because a gym has no athlete logins.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .permissions import IsAthlete, RemoteOnly
from .services.athlete_home import home_for


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def home(request):
    """Home for the signed-in athlete: what's coming up, what's live, their last five sessions"""
    return Response(home_for(request.user.athlete))
