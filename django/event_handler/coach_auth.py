"""Coach authentication: local first-run enrollment and password changes.

The base station is self-hosted, so there is no public registration. The FIRST
administrator is claimed with a short code that only someone standing at the
machine can obtain (`manage.py setup_code` prints it to the local terminal).
Every later account is created by an administrator (see coach_accounts.py).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import CoachProfile, InstallationSetup
from .services import one_time_secrets
from .deployment import is_hosted
from .roles import ATHLETE, role_of

# How long a locally-issued setup code stays valid. Long enough to walk a
# head coach through booting the box, short enough that a code left on a
# whiteboard overnight is not a standing key.
SETUP_CODE_TTL = timedelta(hours=24)

# No 0/O/1/I/L: the code is read off a terminal and typed on a phone or tablet.
# The code itself is made and checked by the shared one-time secrets helpers.
SETUP_CODE_ALPHABET = one_time_secrets.CODE_ALPHABET


def must_change_password(user) -> bool:
    profile = getattr(user, 'coach_profile', None)
    return bool(profile and profile.must_change_password)


def issue_setup_code(ttl=SETUP_CODE_TTL):
    """Create a fresh one-time code, store only its hash, and return the code.

    Returns (code, expires_at). Any previously issued code stops working, so a
    re-run is also a safe way to revoke a code that leaked.
    """
    code = one_time_secrets.new_code()
    now = timezone.now()
    setup, _ = InstallationSetup.objects.get_or_create(pk=1)
    setup.setup_code_hash = one_time_secrets.seal(code)
    setup.setup_code_created_at = now
    setup.setup_code_expires_at = now + ttl
    setup.save(update_fields=['setup_code_hash', 'setup_code_created_at', 'setup_code_expires_at'])
    return code, setup.setup_code_expires_at


def normalize_setup_code(raw) -> str:
    """Accept the code however someone types it: case, spaces, and dashes drop."""
    return one_time_secrets.normalize_code(raw)


def setup_code_is_valid(raw):
    """True only for the current, unexpired code. False for expired or absent."""
    setup = InstallationSetup.objects.filter(pk=1).first()
    if setup is None or not setup.setup_code_hash:
        return False
    if setup.setup_code_expires_at is None or setup.setup_code_expires_at <= timezone.now():
        return False
    return one_time_secrets.opens(normalize_setup_code(raw), setup.setup_code_hash)


def setup_is_required() -> bool:
    """Enrollment is open only before the marker is set AND before any user exists."""
    if get_user_model().objects.exists():
        return False
    return not InstallationSetup.objects.filter(
        pk=1, completed_at__isnull=False).exists()



# ── Too many wrong attempts (remote only) ─────────────────────────────────────
# On the internet anyone can try passwords, or first-run setup codes, as fast as
# they like. A remote installation turns an address away for a minute after
# FAILED_ATTEMPT_LIMIT wrong attempts. Only WRONG attempts count, so a coach who
# signs in correctly is never slowed down. A local installation (a gym box) does not
# do this: its nginx front door already limits sign-in, and only the gym's Wi-Fi can
# reach it. The count lives in each server process's memory, so with three workers
# the true limit is up to three times this; good enough to stop guessing at speed.
# How long an athlete stays signed in on a device before typing their password
# again (spec 03). Longer than a coach's 7 days (settings.SIMPLE_JWT): an athlete
# signs in on their own phone, and a forgotten password needs the coach to send a
# new link.
ATHLETE_SIGN_IN_LIFETIME = timedelta(days=30)


def refresh_token_for(user):
    """A sign-in for this login: 30 days for an athlete, the usual 7 for a coach."""
    token = RefreshToken.for_user(user)
    if role_of(user) == ATHLETE:
        token.set_exp(lifetime=ATHLETE_SIGN_IN_LIFETIME)
    return token


FAILED_ATTEMPT_LIMIT = 10
FAILED_ATTEMPT_WINDOW_SECONDS = 60
TOO_MANY_ATTEMPTS = 'Too many wrong attempts. Wait a minute, then try again.'


def _client_address(request):
    """Where the request really came from. Behind the cluster's front door every
    request arrives from the front door itself; it adds the browser's address as
    the last entry of X-Forwarded-For."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded and is_hosted():
        return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '')


def _attempts_key(request, scope):
    return f'failed-attempts:{scope}:{_client_address(request)}'


class LimitWrongAttempts:
    """Mixed into a view whose POST can fail because of a wrong secret.

    The view puts its POST logic in `attempt()` (or inherits a `post` from its parent
    class); this class's `post` wraps it with the count.
    """
    attempt_scope = None
    # Which answers count as a wrong attempt. A login link that doesn't work
    # answers 404, so those views add it; otherwise links could be guessed
    # without ever being slowed down.
    counted_statuses = (400, 401)

    def attempt(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not is_hosted():
            return self.attempt(request, *args, **kwargs)
        key = _attempts_key(request, self.attempt_scope)
        if cache.get(key, 0) >= FAILED_ATTEMPT_LIMIT:
            return Response({'detail': TOO_MANY_ATTEMPTS, 'code': 'too_many_attempts'}, status=429)
        try:
            response = self.attempt(request, *args, **kwargs)
        except APIException as refused:
            if refused.status_code in self.counted_statuses:  # a wrong password, code or username
                self._count(key)
            raise
        if response.status_code in self.counted_statuses:
            self._count(key)
        return response

    @staticmethod
    def _count(key):
        if cache.add(key, 1, FAILED_ATTEMPT_WINDOW_SECONDS):
            return
        try:
            cache.incr(key)
        except ValueError:  # expired between add and incr
            cache.add(key, 1, FAILED_ATTEMPT_WINDOW_SECONDS)

class SetupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(trim_whitespace=False, write_only=True, max_length=1024)
    setup_code = serializers.CharField(trim_whitespace=False, write_only=True, max_length=64)

    def validate(self, attrs):
        if not setup_code_is_valid(attrs['setup_code']):
            raise serializers.ValidationError(
                {'setup_code': 'That setup code is not valid or has expired. '
                               'Run `python manage.py setup_code` on the base station.'})
        user = get_user_model()(username=attrs['username'])
        try:
            user.full_clean(exclude=['password', 'last_login', 'date_joined'])
            validate_password(attrs['password'], user)
        except ValidationError as error:
            raise serializers.ValidationError(error.messages)
        return attrs


class SetupView(LimitWrongAttempts, APIView):
    """First-run enrollment. Open only while the installation is unclaimed."""

    attempt_scope = 'setup'

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        required = setup_is_required()
        setup = InstallationSetup.objects.filter(pk=1).first()
        pending = bool(
            setup
            and setup.setup_code_hash
            and setup.setup_code_expires_at
            and setup.setup_code_expires_at > timezone.now()
        )
        response = Response({
            'setup_required': required,
            'setup_code_pending': required and pending,
        })
        response['Cache-Control'] = 'no-store'
        return response

    def attempt(self, request):
        try:
            with transaction.atomic():
                # The migration creates the singleton before requests arrive; the
                # row lock serializes enrollment across gunicorn workers.
                setup = InstallationSetup.objects.select_for_update().get(pk=1)
                if setup.completed_at or get_user_model().objects.exists():
                    return Response(
                        {'detail': 'Setup is complete. Sign in with an existing account.'},
                        status=409)
                form = SetupSerializer(data=request.data)
                form.is_valid(raise_exception=True)
                user = get_user_model().objects.create_superuser(
                    username=form.validated_data['username'],
                    password=form.validated_data['password'])
                CoachProfile.objects.get_or_create(user=user)
                setup.completed_at = timezone.now()
                setup.setup_code_hash = ''
                setup.setup_code_expires_at = None
                setup.save(update_fields=['completed_at', 'setup_code_hash', 'setup_code_expires_at'])
        except IntegrityError:
            # A racing worker won the unique-username insert.
            return Response({'detail': 'That username was just taken. Try another.'}, status=400)
        refresh = RefreshToken.for_user(user)
        response = Response({'access': str(refresh.access_token), 'refresh': str(refresh)}, status=201)
        response['Cache-Control'] = 'no-store'
        return response


def who_signed_in(user):
    """What a screen needs to know about the login: its role, and for an athlete,
    which athlete record it belongs to. Used by sign-in and by "who am I"."""
    role = role_of(user)
    info = {'role': role}
    if role == ATHLETE:
        info['athlete_id'] = user.athlete.pk
        info['athlete_name'] = user.athlete.name
    return info


class CoachTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Sign-in. Adds who signed in, and the first-login password-change requirement.

    A login attached to nothing (no coach profile, no athlete record) is refused
    HERE, with a plain sentence. Without this it would be handed a token that
    every route then refuses, and the person would see a signed-in screen where
    nothing works.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['must_change_password'] = must_change_password(user)
        if role_of(user) == ATHLETE:
            token.set_exp(lifetime=ATHLETE_SIGN_IN_LIFETIME)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        info = who_signed_in(self.user)
        if info['role'] is None:
            raise AuthenticationFailed(
                'This login is not set up as a coach or an athlete. '
                'Ask an administrator to set it up.', code='no_role')
        data['must_change_password'] = must_change_password(self.user)
        data.update(info)
        return data


class CoachTokenObtainPairView(LimitWrongAttempts, TokenObtainPairView):
    """Sign in with a username and password, coach or athlete; wrong tries are slowed down."""
    serializer_class = CoachTokenObtainPairSerializer
    attempt_scope = 'sign_in'


class CheckedTokenRefreshSerializer(TokenRefreshSerializer):
    """Renewing a sign-in, with the same question sign-in asks: is this login
    still switched on, and is it still a coach or an athlete?

    The stock renewal only checks that the renewal token itself is genuine. That
    would keep handing fresh tokens to a deactivated coach or an archived athlete
    for up to a week. Each of those tokens is refused when used, so nothing leaks,
    but the honest answer to "renew me" is no.
    """

    def validate(self, attrs):
        claim = RefreshToken(attrs['refresh']).get(jwt_settings.USER_ID_CLAIM)
        user = get_user_model().objects.filter(**{jwt_settings.USER_ID_FIELD: claim}).first()
        if role_of(user) is None:
            raise AuthenticationFailed('This login can no longer sign in.', code='user_inactive')
        data = super().validate(attrs)
        # Renewing hands out a new renewal token (ROTATE_REFRESH_TOKENS), which
        # would get the usual 7 days; an athlete keeps 30.
        if role_of(user) == ATHLETE and 'refresh' in data:
            renewed = RefreshToken(data['refresh'])
            renewed.set_exp(lifetime=ATHLETE_SIGN_IN_LIFETIME)
            data['refresh'] = str(renewed)
        return data


class CheckedTokenRefreshView(TokenRefreshView):
    """Renew a sign-in, refused for a login that was switched off or lost its role."""
    serializer_class = CheckedTokenRefreshSerializer


class CoachSessionView(APIView):
    """ "Who am I": any signed-in login may ask, whatever its role."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'username': request.user.username,
            'is_staff': request.user.is_staff,
            'must_change_password': must_change_password(request.user),
            **who_signed_in(request.user),
        })


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False, write_only=True, max_length=1024)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True, max_length=1024)

    def validate(self, attrs):
        user = self.context['user']
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'That password is incorrect.'})
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError({'new_password': 'Choose a different password.'})
        try:
            validate_password(attrs['new_password'], user)
        except ValidationError as error:
            raise serializers.ValidationError({'new_password': error.messages})
        return attrs


class PasswordChangeView(APIView):
    """Let a signed-in coach replace their own password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        form = PasswordChangeSerializer(data=request.data, context={'user': request.user})
        form.is_valid(raise_exception=True)
        with transaction.atomic():
            user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
            user.set_password(form.validated_data['new_password'])
            user.save(update_fields=['password'])
            CoachProfile.objects.update_or_create(
                user=user, defaults={'must_change_password': False})
        return Response(status=204)
