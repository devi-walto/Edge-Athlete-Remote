"""athlete_logins.py — the web addresses for athlete logins: the coach's side and the athlete's.

WHAT KIND OF FILE THIS IS: request handlers (Django "views"), not a database
change. Each one answers one web address: it receives a request from a screen,
does the job, and sends back a reply. The urls.py files list which address goes
to which handler.

The coach's side (spec 03, Phase 1), coaches only:
  POST   /api/athletes/<id>/login-link/   make a login link for this athlete
  DELETE /api/athletes/<id>/login-link/   cancel their unused link
  DELETE /api/athletes/<id>/login/        remove their login (their data stays)
Plus two helpers the roster list uses to show each athlete's login status.

The athlete's side (spec 03, Phase 2), open to anyone, because the person opening
a link has no login yet. The link itself is what proves who they are:
  POST /api/auth/login-link/lookup/   "who is this link for?" (one name, or 404)
  POST /api/auth/login-link/redeem/   use the link: make the login, sign them in
Both slow down repeated wrong attempts (LimitWrongAttempts, on the remote server).

WHY a separate file: the rules for links (once, 3 days, a newer link cancels the
older, only a fingerprint stored) live in services/login_links.py. These
handlers are just the doors to those rules, kept apart from the long views.py.

Coaches only, on both kinds of installation. A local install's roster doesn't
show the button (the screens decide that); the addresses simply go unused there.
"""
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .coach_auth import LimitWrongAttempts, refresh_token_for, who_signed_in
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


# ───────────────── the athlete's side ─────────────────

# One message for every way a link can fail, so the reply never says whether a
# link expired, was used, or never existed.
LINK_DOES_NOT_WORK = "This link doesn't work any more. Ask your coach for a new one."


class LoginLinkAttempt(LimitWrongAttempts, APIView):
    """What both athlete routes share: open to anyone, no sign-in read, never
    kept by a browser, and a link that doesn't work (404) counts as a wrong try."""
    attempt_scope = 'login_link'
    counted_statuses = (400, 401, 404)
    authentication_classes = []
    permission_classes = [AllowAny]

    @staticmethod
    def private(response):
        response['Cache-Control'] = 'no-store'
        return response


class LoginLinkLookupView(LoginLinkAttempt):
    """ "Who is this link for?" Only that athlete's name: the page says "Hi <name>"."""

    def attempt(self, request):
        link = login_links.find(request.data.get('link'))
        if link is None:
            return self.private(Response({'detail': LINK_DOES_NOT_WORK}, status=404))
        return self.private(Response({'athlete_name': link.athlete.name}))


class LoginLinkRedeemView(LoginLinkAttempt):
    """Use the link: make the athlete's login, and sign them straight in."""

    def attempt(self, request):
        username = str(request.data.get('username') or '').strip()
        password = request.data.get('password')
        if not username or not isinstance(password, str) or not password:
            return self.private(Response(
                {'detail': 'Choose a username and a password.'}, status=400))
        try:
            login = login_links.redeem(request.data.get('link'), username, password)
        except login_links.LinkDoesNotWork:
            return self.private(Response({'detail': LINK_DOES_NOT_WORK}, status=404))
        except ValidationError as refused:
            # A taken username or a weak password: say which, keep the link usable.
            problems = (refused.message_dict if hasattr(refused, 'error_dict')
                        else {'password': refused.messages})
            return self.private(Response({'detail': 'Please fix the highlighted fields.',
                                          'fields': problems}, status=400))
        except IntegrityError:
            # Someone else took the name in the same instant.
            return self.private(Response(
                {'detail': 'That username was just taken. Try another.',
                 'fields': {'username': ['That username is already taken.']}}, status=400))
        refresh = refresh_token_for(login)
        return self.private(Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            **who_signed_in(login),
        }, status=201))
