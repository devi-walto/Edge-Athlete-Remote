"""
permissions.py — the "bouncer" for coach-only actions.

Some actions (creating athletes, assigning racks, ending sessions) should only
work for a logged-in coach. This file is that check: is the person making the
request a logged-in coach? Yes -> let them through. No -> block it. Endpoints
that are open to any screen simply don't use this bouncer.
"""
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


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


class IsCoach(BasePermission):
    """Allow the request only if it carries a valid coach login (a JWT token,
    which the login endpoint hands out) that is past its temporary password."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        refuse_while_password_change_due(request.user)
        return True


class IsActiveStaff(BasePermission):
    """Require the active staff account used for security-sensitive setup."""

    def has_permission(self, request, view):
        if not (request.user
                and request.user.is_authenticated
                and request.user.is_active
                and request.user.is_staff):
            return False
        refuse_while_password_change_due(request.user)
        return True


class IsInstallationAdmin(BasePermission):
    """An administrator: an active staff account that may manage coach logins.

    Staff status is the sole difference between an administrator and an ordinary
    coach, so this is the check that keeps account creation, password resets, and
    deactivation out of a regular coach's hands. ("Administrator" is this flag.
    "Head coach" is only a label on a training group and is never checked.)
    """

    def has_permission(self, request, view):
        if not (request.user
                and request.user.is_authenticated
                and request.user.is_active
                and request.user.is_staff):
            return False
        refuse_while_password_change_due(request.user)
        return True
