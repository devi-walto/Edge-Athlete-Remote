"""
permissions.py — the "bouncer" for actions that are not open to everyone.

Some actions (creating athletes, assigning racks, ending sessions) should only
work for a coach. This file is that check. It does not decide who a login is;
roles.py does that, from what the login is attached to. Each class here just
says which roles it lets through. Endpoints that are open to any screen simply
don't use this bouncer.
"""
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .roles import ADMINISTRATOR, ATHLETE, COACH, role_of

COACH_ROLES = (ADMINISTRATOR, COACH)


def password_change_due(user) -> bool:
    """True while this login is still on a temporary password.

    An administrator hands a new coach a temporary password (or resets one). Until
    the coach replaces it, that password is known to two people, so the login is
    not yet theirs alone.
    """
    profile = getattr(user, 'coach_profile', None)
    return bool(profile and profile.must_change_password)


def refuse_while_password_change_due(user):
    """Stop a signed-in coach at the door until they have set their own password.

    The screens already send them to the change-password form, but a screen is a
    courtesy, not a lock: without this, the temporary password would work against
    every coach route for anyone who skipped the form. Signing in, "who am I" and
    the change-password route itself do not use these permission classes, so the
    way out stays open.
    """
    if password_change_due(user):
        raise PermissionDenied({
            'code': 'password_change_required',
            'detail': 'Change your temporary password before using the coach workspace.',
        })


def _role(request):
    return role_of(getattr(request, 'user', None))


class IsCoach(BasePermission):
    """Let through a coach or an administrator who is past their temporary password.

    "Coach" used to mean "signed in", because coaches were the only people who
    could sign in. Now it means what the name says: the login is attached to a
    coach profile. An athlete's login, or one attached to nothing, is refused.
    """

    def has_permission(self, request, view):
        if _role(request) not in COACH_ROLES:
            return False
        refuse_while_password_change_due(request.user)
        return True


class IsInstallationAdmin(BasePermission):
    """Let through an administrator only.

    The administrator flag is the sole difference between an administrator and
    an ordinary coach, and it guards exactly one thing: managing coach logins.
    ("Head coach" is only a label on a training group and is never checked.)
    """

    def has_permission(self, request, view):
        if _role(request) != ADMINISTRATOR:
            return False
        refuse_while_password_change_due(request.user)
        return True


class IsAthlete(BasePermission):
    """Let through an athlete's own login only."""

    def has_permission(self, request, view):
        return _role(request) == ATHLETE


class IsCoachOrAthlete(BasePermission):
    """Let through anyone with a role; refuse a login attached to nothing."""

    def has_permission(self, request, view):
        role = _role(request)
        if role is None:
            return False
        if role in COACH_ROLES:
            refuse_while_password_change_due(request.user)
        return True


# ─────────────── routes that are open in a gym but not on the internet ───────────────
#
# On a gym box the network is the lock: only devices on the box's own Wi-Fi can
# connect, so a rack tablet needs no login. A hosted installation has no such lock.
# These routes stay exactly as open as before on a gym box, and on a hosted
# installation each one applies the rule named for it below (spec 05, Phase 2).

# What a hosted installation lets through on such a route.
ONLINE_COACH = 'coach'                          # a coach or an administrator
ONLINE_ANY_ROLE = 'any_role'                    # anyone with a role, athletes included
ONLINE_COACH_OR_SAME_ATHLETE = 'coach_or_same_athlete'  # an athlete may read their OWN
ONLINE_COACH_OR_RACK_OWNER = 'coach_or_rack_owner'      # an athlete may use their OWN rack
ONLINE_REFUSE = 'refuse'                        # nobody: there is no shared room online


def _asks_about_own_athlete(request, view):
    """True when an athlete is READING something about themselves: the athlete in
    the address (`athlete_id`) or in `?athlete=` is their own record."""
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        return False
    kwargs = getattr(request, 'parser_context', {}).get('kwargs', {}) or {}
    asked = kwargs.get('athlete_id', request.query_params.get('athlete'))
    athlete = getattr(request.user, 'athlete', None)
    return athlete is not None and asked is not None and str(asked) == str(athlete.pk)


def _owns_the_rack(request, view):
    """Is this athlete the one a hosted rack was made for?

    Always False until spec 04 records which athlete a hosted rack belongs to
    (`RackRuntime.owner_athlete`). Refusing is the safe answer meanwhile: only a
    coach gets through on these routes when hosted.
    """
    return False


class OpenOnLocal(BasePermission):
    """Open on a gym box. On a hosted installation, apply `online_rule`.

    Use `open_on_local(rule)` to get one for a route; the rule is part of the class
    so a test can read every route's rule straight from the URL configuration.
    """
    online_rule = None

    def has_permission(self, request, view):
        from .deployment import is_hosted  # read at request time, so tests can switch it
        if not is_hosted():
            return True
        if self.online_rule == ONLINE_REFUSE:
            raise PermissionDenied('This is not available on a hosted installation.')
        role = _role(request)
        if role in COACH_ROLES:
            refuse_while_password_change_due(request.user)
            return True
        if role == ATHLETE:
            if self.online_rule == ONLINE_ANY_ROLE:
                return True
            if self.online_rule == ONLINE_COACH_OR_SAME_ATHLETE:
                return _asks_about_own_athlete(request, view)
            if self.online_rule == ONLINE_COACH_OR_RACK_OWNER:
                return _owns_the_rack(request, view)
        return False


def open_on_local(online_rule):
    """A permission class for one route: open on a gym box, `online_rule` when hosted."""
    allowed = (ONLINE_COACH, ONLINE_ANY_ROLE, ONLINE_COACH_OR_SAME_ATHLETE,
               ONLINE_COACH_OR_RACK_OWNER, ONLINE_REFUSE)
    if online_rule not in allowed:
        raise ValueError(f'unknown online rule {online_rule!r}')
    return type(f'OpenOnLocal_{online_rule}', (OpenOnLocal,), {'online_rule': online_rule})
