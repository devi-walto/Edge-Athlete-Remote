"""Login links: how a remote athlete gets a login, the first time and after forgetting it.

WHY: athletes never create themselves. A coach makes the athlete record, then sends
that athlete a personal link; whoever opens it picks a username and password, and
that login is attached to the athlete. Forgot the password? The coach sends a new
link. Same button, same path (spec 03).

A link is treated like a password:
  - it works once, and expires after LINK_LIFETIME;
  - a newer link cancels any older unused one;
  - using it signs the athlete's old login out everywhere;
  - only a one-way hash of its secret is stored.

A link looks like `<lookup>.<secret>`. The lookup finds the row; the secret proves
the holder received the link. Every way a link can fail gives the same answer
(None), so nobody can learn whether a link expired, was used, or never existed.
Making, finding and using up the link follow the shared rules in
one_time_secrets.py; this file adds what is a login link's own: the login.

The data never changes hands here: sets, reps, maxes and reports belong to the
athlete record, and a link only replaces the login attached to it.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import Athlete, AthleteLoginLink
from . import one_time_secrets

LINK_LIFETIME = timedelta(days=3)


def issue(athlete, coach):
    """Make a new link for this athlete. Returns (link, expires_at).

    The full link is returned this one time and stored nowhere. Any unused link
    the athlete already had stops working.
    """
    text, link = one_time_secrets.issue(
        AthleteLoginLink, one_time_secrets.LINK, LINK_LIFETIME,
        owner={'athlete': athlete}, created_by=coach)
    return text, link.expires_at


def cancel(athlete):
    """Cancel the athlete's unused link, if any. Their login, if they have one, stays."""
    _cancel_unused(athlete, timezone.now())


def find(link_text):
    """The link row if this link still works, otherwise None, whatever the reason."""
    return one_time_secrets.find(AthleteLoginLink, one_time_secrets.LINK, link_text)


def redeem(link_text, username, password):
    """Use a link: give its athlete a new login with this username and password.

    All or nothing. If anything fails (the link stopped working, the username is
    taken, the password is too weak), the old login keeps working and the link
    stays unused. Returns the new login. Raises ValidationError for a bad
    username or password, LinkDoesNotWork for a link that doesn't work.
    """
    User = get_user_model()
    with transaction.atomic():
        found = find(link_text)
        if found is None:
            raise LinkDoesNotWork()
        # Lock the row, then check again: two people using one link at the same
        # moment must not both get a login.
        link = one_time_secrets.lock_if_still_works(AthleteLoginLink, found)
        if link is None:
            raise LinkDoesNotWork()
        athlete = Athlete.objects.select_for_update().get(pk=link.athlete_id)

        _retire_login(athlete)

        # Usernames ignore capital letters, as coach logins already do: "Riley"
        # and "riley" are one name. (Checked after the old login is renamed out
        # of the way, so an athlete can pick their own old name again.)
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError({'username': ['That username is already taken.']})
        new_login = User(username=username)
        validate_password(password, user=new_login)
        new_login.set_password(password)
        new_login.full_clean(exclude=['password'])   # a taken or invalid username stops here
        new_login.save()

        athlete.user = new_login
        athlete.save(update_fields=['user'])
        one_time_secrets.mark_used(link)
    return new_login


def unlink(athlete):
    """Take the athlete's login away and cancel any unused link. Their data stays."""
    with transaction.atomic():
        athlete = Athlete.objects.select_for_update().get(pk=athlete.pk)
        _retire_login(athlete)
        _cancel_unused(athlete, timezone.now())


class LinkDoesNotWork(Exception):
    """The link is unknown, wrong, expired, used or cancelled; deliberately not saying which."""


# ───────────────────────────── helpers ─────────────────────────────

def _still_works(link):
    return link.still_works()   # the rule lives on the model (AthleteLoginLink)


def _cancel_unused(athlete, now):
    one_time_secrets.cancel_unused(AthleteLoginLink, {'athlete': athlete}, now)


def _retire_login(athlete):
    """Switch the athlete's current login off and detach it.

    Switched off is what signs it out everywhere: the sign-in layer refuses an
    inactive login on its next request, so no list of revoked tokens is needed.
    It is renamed too, so the athlete can pick the same username again.
    The login row is kept, not deleted, as a record.
    """
    old = athlete.user
    if old is None:
        return
    old.is_active = False
    old.username = f"{old.username}~replaced-{old.pk}"[:150]
    old.save(update_fields=['is_active', 'username'])
    athlete.user = None
    athlete.save(update_fields=['user'])

