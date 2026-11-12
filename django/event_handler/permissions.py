"""
permissions.py — the "bouncer" for actions that are not open to everyone.

Some actions (creating athletes, assigning racks, ending sessions) should only
work for a coach. This file is that check. It does not decide who a login is;
roles.py does that, from what the login is attached to. Each class here just
says which roles it lets through. Endpoints that are open to any screen simply
don't use this bouncer.
"""
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import BasePermission

from .roles import ADMINISTRATOR, ATHLETE, COACH, COMMON, role_of

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
    an ordinary coach, and it guards managing logins: coach logins, and making the
    school's common login or changing its password (spec 18).
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


class RemoteOnly(BasePermission):
    """A route that exists only on a remote server. On a local install it answers 404,
    as if it weren't there, before any question of who is asking: a gym has no online
    athletes, so there is nothing to refuse or explain."""

    def has_permission(self, request, view):
        from .deployment import is_hosted
        if not is_hosted():
            raise NotFound()
        return True


class IsCoachOrAthlete(BasePermission):
    """Let through a coach or an athlete; refuse a login attached to nothing, and the
    common login (spec 18), which only gets the routes Phase 1 opens to it by name."""

    def has_permission(self, request, view):
        role = _role(request)
        if role not in (ADMINISTRATOR, COACH, ATHLETE):
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

# What the school's common login (a rack tablet or TV online, spec 18) may do on such a
# route, on top of the rule above. None (the default): refused.
COMMON_OWN_RACK = 'own_rack'   # only for a rack its own device made
COMMON_READ = 'read'           # read only (GET); the route itself decides what's in it
COMMON_DEVICE = 'device'       # any request from a signed-in common-login device (its own rack setup)


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
    """Is this athlete using their OWN rack, for themselves? (spec 04, Phase 2)

    Online, an athlete may use the rack routes only for the rack made for them when
    they joined a session (`RackRuntime.owner_athlete`), may check in only
    themselves, and may start or finish a set only for themselves. Anything else is
    refused; a coach is let through earlier and never reaches this.
    """
    from .models import RackRuntime, Set   # here, not at the top: models import this file's neighbours

    athlete = getattr(request.user, 'athlete', None)
    if athlete is None:
        return False
    kwargs = getattr(request, 'parser_context', {}).get('kwargs', {}) or {}
    data = request.data if isinstance(request.data, dict) else {}

    def is_me(value):
        return value is None or str(value) == str(athlete.pk)

    def owns(rack_number):
        return RackRuntime.objects.filter(rack_number=rack_number, owner_athlete=athlete).exists()

    if 'rack_number' in kwargs:
        # Their own rack, and only ever checking in themselves on it.
        return owns(kwargs['rack_number']) and is_me(data.get('athlete'))
    if 'set_id' in kwargs:
        # Finishing a set: only one of their own.
        return Set.objects.filter(pk=kwargs['set_id'], athlete=athlete).exists()
    # Starting a set: for themselves, and on their own rack if it names one.
    if data.get('athlete') is None or not is_me(data.get('athlete')):
        return False
    rack_number = data.get('rack_number')
    return rack_number is None or owns(rack_number)


def _common_device(request):
    """The common-login device this request comes from, from its sign-in (spec 18).
    authentication.py has already refused a signed-out one."""
    from .authentication import DEVICE_CLAIM
    from .models import CommonDevice
    token = getattr(request, 'auth', None)
    device_pk = token.get(DEVICE_CLAIM) if token is not None and hasattr(token, 'get') else None
    if device_pk is None:
        return None
    return CommonDevice.objects.filter(pk=device_pk, signed_out_at=None,
                                       common_login__user=request.user).first()


def _common_owns_the_rack(request, view):
    """Is this common-login device using a rack it made itself? (spec 18, Phase 1)

    A device's racks are the rack screens with its device id (Phase 2 makes them). The
    rack comes from the address, or for starting a set from the body (`rack_number`,
    which the rack screen always sends), or for finishing one from the set's sensor,
    else the athlete's newest check-in.
    """
    from .models import RackCheckIn, RackScreen, Set
    device = _common_device(request)
    if device is None:
        return False
    racks = set(RackScreen.objects.filter(device_id=device.device_id)
                .exclude(rack_number=None).values_list('rack_number', flat=True))
    if not racks:
        return False
    kwargs = getattr(request, 'parser_context', {}).get('kwargs', {}) or {}
    if 'rack_number' in kwargs:
        return int(kwargs['rack_number']) in racks
    if 'set_id' in kwargs:
        found = Set.objects.filter(pk=kwargs['set_id']).select_related('node').first()
        if found is None:
            return False
        if found.node is not None and found.node.rack_number is not None:
            return found.node.rack_number in racks
        newest = (RackCheckIn.objects.filter(athlete_id=found.athlete_id)
                  .order_by('-checked_in_at').values_list('rack_number', flat=True).first())
        return newest in racks
    data = request.data if isinstance(request.data, dict) else {}
    try:
        return int(data.get('rack_number')) in racks
    except (TypeError, ValueError):
        return False


def _common_reads(request, view):
    """Read only. An athlete's day only for someone in the running session."""
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        return False
    kwargs = getattr(request, 'parser_context', {}).get('kwargs', {}) or {}
    if 'athlete_id' in kwargs:
        from .services.active_session import active_session
        session = active_session()
        return session is not None and session.athletes.filter(pk=kwargs['athlete_id']).exists()
    return True


class OpenOnLocal(BasePermission):
    """Open on a gym box. On a hosted installation, apply `online_rule`.

    Use `open_on_local(rule)` to get one for a route; the rule is part of the class
    so a test can read every route's rule straight from the URL configuration.
    """
    online_rule = None
    common_rule = None

    def has_permission(self, request, view):
        from .deployment import is_hosted  # read at request time, so tests can switch it
        if not is_hosted():
            return True
        role = _role(request)
        # The common login's own rule comes first: a route refused to everyone else
        # online (a tablet making its own rack) may still be open to it (spec 18).
        if role == COMMON and self.common_rule == COMMON_DEVICE:
            return _common_device(request) is not None
        if self.online_rule == ONLINE_REFUSE:
            raise PermissionDenied('This is not available on a hosted installation.')
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
        if role == COMMON:
            if self.common_rule == COMMON_OWN_RACK:
                return _common_owns_the_rack(request, view)
            if self.common_rule == COMMON_READ:
                return _common_reads(request, view)
        return False


def open_on_local(online_rule, common=None):
    """A permission class for one route: open on a gym box, `online_rule` when hosted,
    and `common` (COMMON_OWN_RACK, COMMON_READ, COMMON_DEVICE, or None: refused) for the
    common login."""
    allowed = (ONLINE_COACH, ONLINE_ANY_ROLE, ONLINE_COACH_OR_SAME_ATHLETE,
               ONLINE_COACH_OR_RACK_OWNER, ONLINE_REFUSE)
    if online_rule not in allowed:
        raise ValueError(f'unknown online rule {online_rule!r}')
    if common not in (None, COMMON_OWN_RACK, COMMON_READ, COMMON_DEVICE):
        raise ValueError(f'unknown common-login rule {common!r}')
    name = f'OpenOnLocal_{online_rule}' + (f'_common_{common}' if common else '')
    return type(name, (OpenOnLocal,), {'online_rule': online_rule, 'common_rule': common})
