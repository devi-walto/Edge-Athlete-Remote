"""athlete_logins.py — the web addresses a coach's screen calls to manage athlete logins.

WHAT KIND OF FILE THIS IS: request handlers (Django "views"), not a database
change. Each function here answers one web address under /api/athletes/<id>/:
it receives a request from the coach's screen, does the job, and sends back a
reply. urls.py lists which address goes to which function.

What they do (spec 03, Phase 1):
  POST   /api/athletes/<id>/login-link/   make a login link for this athlete
  DELETE /api/athletes/<id>/login-link/   cancel their unused link
  DELETE /api/athletes/<id>/login/        remove their login (their data stays)

Plus two helpers the roster list uses to show each athlete's login status.

WHY a separate file: the rules for links (once, 3 days, a newer link cancels the
older, only a fingerprint stored) live in services/login_links.py. These
handlers are just the doors to those rules, kept apart from the long views.py.

Coaches only, on both kinds of installation. A local install's roster doesn't
show the button (the screens decide that); the addresses simply go unused there.
"""
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Athlete, AthleteLoginLink
from .permissions import COACH_ROLES, IsCoach
from .roles import role_of
from .services import login_links


@api_view(['POST', 'DELETE'])
@permission_classes([IsCoach])
def athlete_login_link(request, athlete_id):
    """POST: make a new link for this athlete. DELETE: cancel their unused link."""
    athlete = Athlete.objects.filter(pk=athlete_id).first()
    if athlete is None:
        return Response({'detail': 'athlete not found'}, status=404)

    if request.method == 'DELETE':
        login_links.cancel(athlete)
        return Response(status=204)

    # An archived athlete's login is switched off; a link must not bring it back.
    if not athlete.is_active:
        return Response({'detail': 'This athlete is archived. Bring them back first.'}, status=409)
    link, expires_at = login_links.issue(athlete, request.user)
    # This reply is the only time the full link exists anywhere. It goes after a
    # #, which a browser never sends to the server, so the secret stays out of
    # every request log (spec 03, Phase 1).
    return Response({
        'link': request.build_absolute_uri('/login-link') + '#' + link,
        'expires_at': expires_at,
    }, status=201)


@api_view(['DELETE'])
@permission_classes([IsCoach])
def athlete_login(request, athlete_id):
    """Remove this athlete's login. Their sets, reps and reports stay."""
    athlete = Athlete.objects.filter(pk=athlete_id).first()
    if athlete is None:
        return Response({'detail': 'athlete not found'}, status=404)
    login_links.unlink(athlete)
    return Response(status=204)


# ───────────────── the roster's login column ─────────────────

def is_coach(request):
    return role_of(request.user) in COACH_ROLES


def with_login_facts(athletes):
    """Load every athlete's login and waiting link in two database trips, not two per athlete."""
    waiting = AthleteLoginLink.objects.filter(
        used_at__isnull=True, cancelled_at__isnull=True, expires_at__gt=timezone.now(),
    ).order_by('-created_at')
    return athletes.select_related('user').prefetch_related(
        Prefetch('login_links', queryset=waiting, to_attr='waiting_links'))


def login_facts(athlete):
    """What the roster shows about one athlete's login. Never a secret or a fingerprint.

    login_status:
      'link_sent' a link is waiting to be used (also when it will replace a login)
      'linked'    they have a working login
      'none'      neither; an expired link counts as nothing, so the coach sees it ran out
    """
    login = athlete.user if athlete.user_id and athlete.user.is_active else None
    links = getattr(athlete, 'waiting_links', None)
    if links is None:   # loaded without with_login_facts()
        links = list(athlete.login_links.filter(
            used_at__isnull=True, cancelled_at__isnull=True, expires_at__gt=timezone.now()))
    waiting = links[0] if links and athlete.is_active else None
    if waiting:
        status = 'link_sent'
    elif login:
        status = 'linked'
    else:
        status = 'none'
    return {
        'login_status': status,
        'login_username': login.username if login else None,
        'link_expires_at': waiting.expires_at if waiting else None,
    }
