"""passwords.py — the one place any password is set (spec 18, Phase 0).

Why this exists: a new password must sign out every device that signed in with the
old one, for every kind of login (Devin, 2026-10-27). Passwords used to be set in three
places (a coach changing their own, an administrator resetting a coach's, an athlete's
login link), each calling set_password itself; now all of them, and the common login,
call set_new_password(), which also records the moment. authentication.py refuses any
sign-in made before it, when used and when renewed.
"""
from django.utils import timezone

from ..models import PasswordSetAt


def set_new_password(user, raw_password):
    """Set the password, save it, and record when: older sign-ins stop working."""
    user.set_password(raw_password)
    user.save(update_fields=['password'])
    PasswordSetAt.objects.update_or_create(user=user, defaults={'at': timezone.now()})


def signed_in_before_password_set(user, issued_at):
    """Was a sign-in issued at `issued_at` (seconds, from the token) made before the
    login's password was last set? Compared in whole seconds, as the token is: a
    sign-in made in the same second as the change (the changer's own fresh one) stands."""
    record = PasswordSetAt.objects.filter(user=user).only('at').first()
    if record is None or issued_at is None:
        return False
    return int(issued_at) < int(record.at.timestamp())
