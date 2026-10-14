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


def remote_settings(*, debug, allowed_hosts_raw, csrf_origins_raw):
    """The settings a REMOTE installation must have, or a reason it cannot start.

    On the internet, three mistakes are dangerous and easy to make by leaving a
    line out of the configuration:

    - debug mode on: Django's debug pages show settings and code to anyone;
    - no named web address: Django would answer for any address pointed at it;
    - no list of sites allowed to send forms: needed once the site is HTTPS.

    Returns (allowed_hosts, csrf_trusted_origins). Raises ImproperlyConfigured with
    a plain message when something is missing. The trusted origins default to
    https:// plus each allowed host, which is right when the site is served on its
    own address; set CSRF_TRUSTED_ORIGINS to override.
    """
    if debug:
        raise ImproperlyConfigured(
            "EA_DEPLOYMENT is remote but DEBUG is on. Debug pages show the app's "
            "settings and code to anyone on the internet. Set DEBUG=False.")
    hosts = [h.strip() for h in (allowed_hosts_raw or '').split(',') if h.strip()]
    if not hosts:
        raise ImproperlyConfigured(
            "EA_DEPLOYMENT is remote but ALLOWED_HOSTS is empty. Set it to the "
            "installation's web address, e.g. ALLOWED_HOSTS=team.example.com")
    origins = [o.strip() for o in (csrf_origins_raw or '').split(',') if o.strip()]
    if not origins:
        origins = [f'https://{h}' for h in hosts if h not in ('*',) and not h.startswith('.')]
    return hosts, origins
