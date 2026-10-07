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
