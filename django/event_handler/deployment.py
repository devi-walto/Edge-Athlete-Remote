"""
deployment.py — the one place the app asks "am I a gym box or a hosted installation?"

WHY THIS EXISTS: a few things must behave differently on the internet than in a
gym (who may reach a rack screen with no login, for one). If each of those read
the setting for itself, sooner or later two of them would disagree. So nothing
else reads EA_DEPLOYMENT: everything asks is_hosted().

It also holds the small route a screen uses to ask the same question, so the
frontend is told what it is running on and never has to guess from the address.
"""
import os

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from basestation_config.deployment_mode import REMOTE


def deployment():
    """'local' or 'remote'."""
    return settings.EA_DEPLOYMENT


def is_hosted():
    """True on a hosted installation, False on a gym box."""
    return deployment() == REMOTE


@api_view(['GET'])
@permission_classes([AllowAny])
def system_info(request):
    """Which kind of installation this is, and which build.

    Open on purpose: the sign-in screen needs it before anyone has signed in.
    It says nothing else about the installation. The build label comes from
    EA_VERSION, which the release process sets; an unlabelled build says "dev".
    """
    return Response({
        'deployment': deployment(),
        'version': os.environ.get('EA_VERSION', '').strip() or 'dev',
    })
