"""common_login.py — the school's common login, from Room Layout (spec 18, Phase 0).

Why this file exists: online, a rack tablet or a TV has nobody to sign in, so the
school has one login every such device shares. These routes are what Room Layout's
Common login card (boards F_CommonLogin_*) asks: what it is and which devices are
signed in with it (any coach), Show (any coach: they're the ones who type it into a
tablet), signing one device out (any coach), and making it or changing its password
(an administrator only, typed straight in, no login link: Devin, 2026-11-12).

A new password signs every device out at once (services/passwords.py and
authentication.py), and the password is also kept sealed so Show can read it back
(services/sealed.py), which no other password here is. Online only: a gym box needs no
login on its racks, so every route here is 404 there.
"""
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import CommonDevice, CommonLogin
from .permissions import IsCoach, IsInstallationAdmin, RemoteOnly
from .services import sealed
from .services.passwords import set_new_password

USERNAME = re.compile(r'^[A-Za-z0-9-]{3,40}$')


def _device(row):
    return {'id': row.pk, 'label': row.label, 'device_id': row.device_id,
            'signed_in_at': row.signed_in_at, 'last_seen_at': row.last_seen_at}


def _check_password(password, user):
    if not isinstance(password, str) or not password:
        return ['Type a password.']
    try:
        validate_password(password, user)
    except ValidationError as error:
        return error.messages
    return None


@api_view(['GET'])
@permission_classes([RemoteOnly, IsCoach])
def common_login(request):
    """The card: set up or not, its username, and the devices signed in with it.
    Never the password: that is only ever in Show's answer."""
    common = CommonLogin.objects.select_related('user').first()
    if common is None:
        return Response({'set_up': False, 'username': None, 'devices': []})
    devices = common.devices.filter(signed_out_at=None).order_by('label', 'signed_in_at')
    return Response({'set_up': True, 'username': common.user.username,
                     'devices': [_device(d) for d in devices]})


@api_view(['POST'])
@permission_classes([RemoteOnly, IsInstallationAdmin])
def common_login_set_up(request):
    """Make the common login: a username and a password, typed by an administrator."""
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password')
    if not USERNAME.match(username):
        return Response({'username': ['3 to 40 letters, numbers and dashes, like gym-screens.']}, status=400)
    User = get_user_model()
    with transaction.atomic():
        if CommonLogin.objects.select_for_update().exists():
            return Response({'code': 'already_set_up',
                             'detail': 'The school already has a common login. Change its password instead.'},
                            status=409)
        if User.objects.filter(username__iexact=username).exists():
            return Response({'username': ['That username is already taken.']}, status=400)
        login = User(username=username)
        problems = _check_password(password, login)
        if problems:
            return Response({'password': problems}, status=400)
        login.set_unusable_password()
        login.save()
        set_new_password(login, password)
        CommonLogin.objects.create(user=login, password_sealed=sealed.seal(password))
    return Response({'set_up': True, 'username': username, 'devices': []}, status=201)


@api_view(['POST'])
@permission_classes([RemoteOnly, IsInstallationAdmin])
def common_login_password(request):
    """A new password, typed by an administrator. Every device is signed out at once."""
    common = CommonLogin.objects.select_related('user').first()
    if common is None:
        return Response({'detail': 'There is no common login yet. Set it up first.'}, status=404)
    password = request.data.get('password')
    problems = _check_password(password, common.user)
    if problems:
        return Response({'password': problems}, status=400)
    with transaction.atomic():
        set_new_password(common.user, password)
        common.password_sealed = sealed.seal(password)
        common.save(update_fields=['password_sealed'])
        common.devices.filter(signed_out_at=None).update(signed_out_at=timezone.now())
    return Response(status=204)


@api_view(['POST'])
@permission_classes([RemoteOnly, IsCoach])
def common_login_show(request):
    """Show: the password, for a coach about to sign a tablet in. A POST, never cached."""
    common = CommonLogin.objects.first()
    if common is None:
        return Response({'detail': 'There is no common login yet.'}, status=404)
    try:
        password = sealed.open_sealed(common.password_sealed)
    except sealed.Unreadable:
        return Response({'code': 'password_unreadable',
                         'detail': "The password can't be shown on this server any more. "
                                   'An administrator can set a new one.'}, status=409)
    response = Response({'password': password})
    response['Cache-Control'] = 'no-store'
    return response


@api_view(['POST'])
@permission_classes([RemoteOnly, IsCoach])
def common_device_sign_out(request, device_pk):
    """Sign one device out (a lost or stuck tablet). The others keep working."""
    device = CommonDevice.objects.filter(pk=device_pk).first()
    if device is None:
        return Response({'detail': 'Device not found.'}, status=404)
    if device.signed_out_at is None:
        device.signed_out_at = timezone.now()
        device.save(update_fields=['signed_out_at'])
    return Response(status=204)
