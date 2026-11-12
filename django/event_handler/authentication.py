"""authentication.py — the sign-in check every request goes through.

Why this exists (spec 18, Phase 0): a sign-in is a token the device keeps, good for
hours. Two things must stop one at once, not when it runs out:

  - a new password: every sign-in made before it is refused, for every kind of login
    (services/passwords.py records the moment);
  - a coach signing one common-login device out: that device's sign-in names its
    device record, and a record that's signed out (or belongs to another login) is
    refused, while every other device keeps working.

The same check runs when a device asks to renew its sign-in (coach_auth.py), so a
refused one can't simply be swapped for a fresh one.
"""
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .services.passwords import signed_in_before_password_set

DEVICE_CLAIM = 'common_device'
# How often a device's "last seen" is written: not on every request.
SEEN_EVERY_SECONDS = 60


def check_still_signed_in(user, token):
    """Raise AuthenticationFailed if this sign-in has been cut off; otherwise note
    that a common-login device was seen."""
    if signed_in_before_password_set(user, token.get('iat')):
        raise AuthenticationFailed('The password was changed. Sign in again.', code='password_changed')
    device_id = token.get(DEVICE_CLAIM)
    if device_id is None:
        return
    from .models import CommonDevice   # here: models import modules that import this one
    device = CommonDevice.objects.filter(pk=device_id, common_login__user=user).first()
    if device is None or device.signed_out_at is not None:
        raise AuthenticationFailed('This device was signed out. Sign in again.', code='device_signed_out')
    now = timezone.now()
    if device.last_seen_at is None or (now - device.last_seen_at).total_seconds() >= SEEN_EVERY_SECONDS:
        CommonDevice.objects.filter(pk=device.pk).update(last_seen_at=now)


class CheckedJWTAuthentication(JWTAuthentication):
    """The usual token check, then: is this sign-in still standing?"""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        check_still_signed_in(user, validated_token)
        return user
