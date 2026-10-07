"""
deployment_mode.py — reading the one setting that says what kind of installation this is.

WHY THIS EXISTS: the same code runs in two places. In a gym it sits on its own
private Wi-Fi, where the network is the lock and a rack tablet needs no login.
On the internet there is no such lock. One environment variable, EA_DEPLOYMENT,
says which of the two this installation is:

    local   a gym box (the default)
    remote  a hosted installation, reached over the internet

This file only turns the raw text into one of those two words. It is kept apart
from settings.py so it can be tested on its own, and it imports nothing from
Django so settings.py can use it while Django is still starting.

A misspelled value REFUSES TO START. Quietly falling back to "local" would open
a hosted installation to the internet because of a typo.
"""
from django.core.exceptions import ImproperlyConfigured

LOCAL = 'local'
REMOTE = 'remote'
ALLOWED = (LOCAL, REMOTE)


def parse_deployment(raw):
    """Return 'local' or 'remote'. Unset or blank means 'local'."""
    value = (raw or '').strip().lower()
    if not value:
        return LOCAL
    if value not in ALLOWED:
        raise ImproperlyConfigured(
            f"EA_DEPLOYMENT is set to {raw!r}, which is not a kind of installation. "
            f"Use one of: {', '.join(ALLOWED)}. Leave it unset for a gym box (local).")
    return value
