"""
roles.py — the one place that answers "who is this login?"

WHY THIS EXISTS: for a long time "coach" simply meant "signed in", because coaches
were the only people who could sign in. Athletes are about to get logins too, and
an athlete's login must never be able to edit the roster or end a session.

Nothing stores a role. A login's role comes from what it is attached to:

  - attached to a coach profile, with the staff flag on  -> "administrator"
  - attached to a coach profile                          -> "coach"
  - attached to an athlete record                        -> "athlete"
  - attached to nothing, or switched off, or not signed in -> None (refused)

Every check in the app asks role_of(). That way a half-made account, or a new
kind of login nobody planned for, gets nothing until somebody decides otherwise.
"""
import logging

from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

ADMINISTRATOR = 'administrator'
COACH = 'coach'
ATHLETE = 'athlete'


def _attached(user, name):
    """The coach profile or athlete record attached to this login, or None."""
    try:
        return getattr(user, name)
    except ObjectDoesNotExist:
        return None


def role_of(user):
    """Return 'administrator', 'coach', 'athlete', or None.

    None means "refuse". A login attached to BOTH a coach profile and an athlete
    record is a data mistake, not a person with two jobs: we cannot tell which
    it was meant to be, so it gets None and a warning in the log.
    """
    if user is None or not user.is_authenticated or not user.is_active:
        return None

    is_coach = _attached(user, 'coach_profile') is not None
    is_athlete = _attached(user, 'athlete') is not None

    if is_coach and is_athlete:
        logger.warning(
            'login %s is attached to both a coach profile and an athlete record; '
            'refusing it until one of the two is removed', user.pk)
        return None
    if is_coach:
        return ADMINISTRATOR if user.is_staff else COACH
    if is_athlete:
        return ATHLETE
    return None
