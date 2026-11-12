"""sealed.py — keep a secret the app must be able to read back, encrypted.

Why this exists: a normal password is stored scrambled one way, so nobody (not even
this app) can ever read it again. Two passwords here are different on purpose: the
school's common login, which every coach may look at with Show so they can sign a
rack tablet in (spec 18, Phase 0), and later the rack Wi-Fi's (Phase 5). Those are kept
encrypted instead, with a key made from the server's own secret key, so they read back
on this server and are useless anywhere else.

If the server's secret key changes, what was sealed can't be opened any more: open()
raises Unreadable, and the screen asks an administrator to set a new password.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

# A fixed label, so this key is never the same as any other made from SECRET_KEY.
_LABEL = b'edge-athlete:sealed:v1:'


class Unreadable(Exception):
    """Sealed with a different key (the server's secret key changed), or damaged."""


def _box():
    digest = hashlib.sha256(_LABEL + settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def seal(text):
    return _box().encrypt(text.encode()).decode()


def open_sealed(sealed):
    try:
        return _box().decrypt(sealed.encode()).decode()
    except (InvalidToken, ValueError) as error:
        raise Unreadable() from error
