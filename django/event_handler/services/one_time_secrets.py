"""One-time secrets: the one place the app makes, stores and checks a secret that works once.

WHY THIS FILE EXISTS: several parts of the project hand someone a secret that works
once and then expires:
  - the first-run setup code, read off the base station to claim it (spec 01);
  - login links, which a coach sends an athlete (spec 03);
  - sensor claim codes, which an athlete gives their sensor (spec 14);
  - and next, coach login codes (spec 11).
Each one used to make, hash and check its secret its own way. They now share this file,
so the rules are written once and a fix reaches all of them.

Two kinds of secret, for two ways of passing one on:
  - a CODE is for a person to read and type: 8 characters with no look-alikes
    (no 0/O, 1/I/L), shown as XXXX-XXXX. Typing ignores case, spaces and dashes.
  - a LINK is for a person to click: a long random secret that fits in a web address.

The same rules for both:
  - only a one-way hash is stored (the way Django stores passwords), so a copy of the
    database can't be used to claim anything;
  - a row works once, until it expires, and a newer one cancels the owner's older one;
  - every way a secret can fail (wrong, used, expired, cancelled, never existed) gives
    the same answer, so nobody can learn which.

A row is found by its LOOKUP, a public part of the secret, and proven by the rest:
  - a link is `<lookup>.<secret>`: 12 characters to find the row, 32 to prove it;
  - a code's first 4 characters find the row and its last 4 prove it. Guessing one
    means guessing both halves before it expires, against the wrong-attempt limit.
The rows themselves are models built on `OneTimeSecret` (models.py).
"""
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

# No 0/O, 1/I/L: a code is read off a screen and typed on a phone, tablet or sensor page.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
CODE_LOOKUP_LENGTH = 4

CODE = "code"
LINK = "link"


# ── Making and checking a secret ──────────────────────────────────────────────

def new_code() -> str:
    """8 random characters from CODE_ALPHABET, e.g. "K7MQ2XPR"."""
    return ''.join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(raw) -> str:
    """A code however someone typed it: capitals, and anything not in the alphabet dropped."""
    return ''.join(ch for ch in str(raw or '').upper() if ch in CODE_ALPHABET)


def format_code(code) -> str:
    """How a code is shown to people: "K7MQ-2XPR"."""
    code = normalize_code(code)
    return f"{code[:CODE_LOOKUP_LENGTH]}-{code[CODE_LOOKUP_LENGTH:]}"


def new_link_secret() -> str:
    """A long random secret that is safe in a web address (32 characters)."""
    return secrets.token_urlsafe(24)


def seal(secret) -> str:
    """The one-way hash to store instead of the secret."""
    return make_password(secret)


def opens(secret, sealed) -> bool:
    """True if this secret is the one that was sealed. False for anything empty."""
    if not secret or not sealed:
        return False
    return check_password(secret, sealed)


# ── One-time rows (models built on OneTimeSecret) ─────────────────────────────

def issue(model, style, lifetime, owner, **fields):
    """Make a new one-time row for this owner. Returns (text to hand over, row).

    `owner` is how the model names whose it is, e.g. {"athlete": athlete}. The owner's
    older unused rows stop working. The text is returned this one time and stored
    nowhere: a link `<lookup>.<secret>`, or a code shown as XXXX-XXXX.
    """
    now = timezone.now()
    with transaction.atomic():
        cancel_unused(model, owner, now)
        lookup, secret, text = _new_secret(model, style)
        row = model.objects.create(
            lookup=lookup, token_hash=seal(secret), created_at=now,
            expires_at=now + lifetime, **owner, **fields)
    return text, row


def find(model, style, text):
    """The row if this secret still works, otherwise None, whatever the reason."""
    lookup, secret = _split(style, text)
    if not lookup or not secret:
        return None
    row = model.objects.filter(lookup=lookup).first()
    if row is None:
        # Check against a stand-in hash anyway, so an unknown lookup takes as long
        # to refuse as a known one: the time taken mustn't say which lookups exist.
        opens(secret, _stand_in_hash())
        return None
    if not opens(secret, row.token_hash) or not row.still_works():
        return None
    return row


def lock_if_still_works(model, row):
    """Lock the row and check it again; None if it stopped working meanwhile.

    For use inside a transaction, right before using a row up: two people using one
    secret at the same moment must not both get what it gives.
    """
    locked = model.objects.select_for_update().get(pk=row.pk)
    return locked if locked.still_works() else None


def mark_used(row):
    row.used_at = timezone.now()
    row.save(update_fields=['used_at'])


def cancel_unused(model, owner, now=None):
    """The owner's unused rows stop working. Used ones are kept as a record."""
    model.objects.filter(used_at__isnull=True, cancelled_at__isnull=True, **owner).update(
        cancelled_at=now or timezone.now())


# ── helpers ───────────────────────────────────────────────────────────────────

def _new_secret(model, style):
    """(lookup, secret, text to hand over), with a lookup no row has used yet."""
    while True:
        if style == CODE:
            code = new_code()
            lookup, secret, text = (code[:CODE_LOOKUP_LENGTH], code[CODE_LOOKUP_LENGTH:],
                                    format_code(code))
        else:
            lookup, secret = secrets.token_urlsafe(9), new_link_secret()   # 12 + 32 characters
            text = f"{lookup}.{secret}"
        if not model.objects.filter(lookup=lookup).exists():
            return lookup, secret, text


def _split(style, text):
    if style == CODE:
        code = normalize_code(text)
        if len(code) != CODE_LENGTH:
            return None, None
        return code[:CODE_LOOKUP_LENGTH], code[CODE_LOOKUP_LENGTH:]
    lookup, _, secret = str(text or '').partition('.')
    return lookup, secret


_STAND_IN = []


def _stand_in_hash():
    if not _STAND_IN:
        _STAND_IN.append(make_password(secrets.token_urlsafe(24)))
    return _STAND_IN[0]
