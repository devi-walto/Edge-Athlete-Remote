"""Tests for the school's common login (spec 18, Phase 0).

WHY THESE EXIST: online, every rack tablet and TV shares one login. These pin who may
make it and see it, that a new password signs out every device that used the old one
(for every kind of login, not just this one), that signing one device out leaves the
others alone, and that the common login gets nothing a coach or an athlete gets: it is
refused on every route until Phase 1 opens a few to it by name.
"""
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from datetime import timedelta

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .coach_auth import CoachTokenObtainPairSerializer

from .models import Athlete, CoachProfile, CommonDevice, CommonLogin
from .roles import COMMON, role_of
from .services import sealed
from .services.passwords import set_new_password
from .test_open_on_local import OPEN_EVERYWHERE
from .test_role_checks import ROUTES

User = get_user_model()
PASSWORD = 'Unique-common-2026!safe'
TABLET_PASSWORD = 'Gym-screens-2026!only'


def signed_in_earlier(user, device=None, seconds=30):
    """Tokens as a device that signed in `seconds` ago would hold them. Tokens count
    whole seconds, so "signed in before the change" is made by an earlier issue time."""
    earlier = timezone.now() - timedelta(seconds=seconds)
    refresh = CoachTokenObtainPairSerializer.get_token(user)
    refresh.set_iat(at_time=earlier)
    if device is not None:
        refresh['common_device'] = device.pk
    access = refresh.access_token
    access.set_iat(at_time=earlier)
    return {'refresh': str(refresh), 'access': str(access)}


def make_common(username='gym-screens', password=TABLET_PASSWORD):
    user = User.objects.create_user(username, password=password)
    CommonLogin.objects.create(user=user, password_sealed=sealed.seal(password))
    return user


@override_settings(EA_DEPLOYMENT='remote')
class CommonLoginTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user('cl_admin', password=PASSWORD, is_staff=True)
        self.coach = User.objects.create_user('cl_coach', password=PASSWORD)
        for user in (self.admin, self.coach):
            CoachProfile.objects.create(user=user)
        self.athlete_login = User.objects.create_user('cl_athlete', password=PASSWORD)
        Athlete.objects.create(name='Common Athlete', user=self.athlete_login)

    def sign_in(self, username, password, **extra):
        return self.client.post('/api/auth/login/', {'username': username, 'password': password, **extra},
                                format='json')

    def tablet(self, device_id='tablet-1', password=TABLET_PASSWORD):
        response = self.sign_in('gym-screens', password, device_id=device_id)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def get_as(self, access, url='/api/auth/me/'):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.get(url)
        self.client.credentials()
        return response

    def renew(self, refresh):
        return self.client.post('/api/auth/refresh/', {'refresh': refresh}, format='json')

    def as_user(self, user):
        self.client.force_authenticate(user=user)


class TheRoleTests(CommonLoginTestCase):
    def test_its_role_is_common(self):
        self.assertEqual(role_of(make_common()), COMMON)

    def test_switched_off_or_attached_twice_gets_nothing(self):
        common = make_common()
        common.is_active = False
        common.save()
        self.assertIsNone(role_of(common))
        twice = User.objects.create_user('twice-tablets', password=PASSWORD)
        CommonLogin.objects.filter(user=common).update(user=twice)   # the one common login...
        CoachProfile.objects.create(user=twice)                     # ...and a coach as well
        self.assertIsNone(role_of(User.objects.get(pk=twice.pk)))

    def test_there_is_never_a_second_one(self):
        make_common()
        self.as_user(self.admin)
        response = self.client.post('/api/common-login/set-up/',
                                    {'username': 'more-screens', 'password': TABLET_PASSWORD}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(CommonLogin.objects.count(), 1)


class SigningInTests(CommonLoginTestCase):
    def test_a_tablet_signs_in_and_its_tokens_name_its_device(self):
        make_common()
        tokens = self.tablet()
        self.assertEqual(tokens['role'], COMMON)
        device = CommonDevice.objects.get()
        self.assertEqual(device.device_id, 'tablet-1')
        self.assertEqual(RefreshToken(tokens['refresh'])['common_device'], device.pk)
        self.assertEqual(self.get_as(tokens['access']).status_code, 200)

    def test_it_must_say_which_device_it_is(self):
        make_common()
        self.assertEqual(self.sign_in('gym-screens', TABLET_PASSWORD).status_code, 400)

    def test_signing_in_again_closes_the_old_sign_in(self):
        make_common()
        first = self.tablet()
        self.tablet()
        self.assertEqual(self.get_as(first['access']).status_code, 401)
        self.assertEqual(CommonDevice.objects.filter(signed_out_at=None).count(), 1)

    @override_settings(EA_DEPLOYMENT='local')
    def test_a_gym_box_has_no_use_for_it(self):
        make_common()
        response = self.sign_in('gym-screens', TABLET_PASSWORD, device_id='tablet-1')
        self.assertEqual(response.status_code, 401)


class NewPasswordSignsOutTests(CommonLoginTestCase):
    """A new password signs out every device signed in with the old one, every kind of login."""

    def test_the_common_login_every_tablet_out_when_an_admin_changes_it(self):
        common = make_common()
        self.tablet('tablet-a'), self.tablet('tablet-b')
        a, b = (signed_in_earlier(common, device) for device in CommonDevice.objects.all())
        self.as_user(self.admin)
        response = self.client.post('/api/common-login/password/', {'password': 'Brand-new-screens-77!'},
                                    format='json')
        self.assertEqual(response.status_code, 204)
        self.client.force_authenticate(user=None)
        for tokens in (a, b):
            self.assertEqual(self.get_as(tokens['access']).status_code, 401)
            self.assertEqual(self.renew(tokens['refresh']).status_code, 401)
        self.assertFalse(CommonDevice.objects.filter(signed_out_at=None).exists())
        self.assertEqual(self.sign_in('gym-screens', 'Brand-new-screens-77!', device_id='tablet-a').status_code, 200)

    def test_a_coach_changing_their_own_stays_signed_in_on_this_device_only(self):
        old = signed_in_earlier(self.coach)
        other_device = signed_in_earlier(self.coach)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {old['access']}")
        response = self.client.post('/api/auth/password/', {'current_password': PASSWORD,
                                                             'new_password': 'Another-unique-2026!'}, format='json')
        self.client.credentials()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_as(other_device['access']).status_code, 401)
        self.assertEqual(self.renew(other_device['refresh']).status_code, 401)
        self.assertEqual(self.get_as(response.data['access']).status_code, 200)
        self.assertEqual(self.renew(response.data['refresh']).status_code, 200)

    def test_an_athlete_and_a_reset_coach_alike(self):
        athlete = signed_in_earlier(self.athlete_login)
        coach = signed_in_earlier(self.coach)
        set_new_password(self.athlete_login, 'Athlete-fresh-2026!')
        self.as_user(self.admin)
        self.assertEqual(self.client.post(f'/api/coaches/{self.coach.pk}/reset/').status_code, 200)
        self.client.force_authenticate(user=None)
        for name, tokens in (('cl_athlete', athlete), ('cl_coach', coach)):
            self.assertEqual(self.get_as(tokens['access']).status_code, 401, name)
            self.assertEqual(self.renew(tokens['refresh']).status_code, 401, name)

    def test_the_common_login_cannot_change_its_own(self):
        make_common()
        tokens = self.tablet()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.post('/api/auth/password/', {'current_password': TABLET_PASSWORD,
                                                             'new_password': 'Tablet-took-over-1!'}, format='json')
        self.assertEqual(response.status_code, 403)


class SigningOneDeviceOutTests(CommonLoginTestCase):
    def test_the_others_keep_working(self):
        make_common()
        a, b = self.tablet('tablet-a'), self.tablet('tablet-b')
        device_a = CommonDevice.objects.get(device_id='tablet-a')
        self.as_user(self.coach)
        self.assertEqual(self.client.post(f'/api/common-login/devices/{device_a.pk}/sign-out/').status_code, 204)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.get_as(a['access']).status_code, 401)
        self.assertEqual(self.renew(a['refresh']).status_code, 401)
        self.assertEqual(self.get_as(b['access']).status_code, 200)
        self.assertEqual(self.renew(b['refresh']).status_code, 200)


class WhoMayDoWhatTests(CommonLoginTestCase):
    def test_an_admin_makes_it_and_changes_it_a_coach_cannot(self):
        self.as_user(self.coach)
        body = {'username': 'gym-screens', 'password': TABLET_PASSWORD}
        self.assertEqual(self.client.post('/api/common-login/set-up/', body, format='json').status_code, 403)
        self.as_user(self.admin)
        response = self.client.post('/api/common-login/set-up/', body, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(role_of(User.objects.get(username='gym-screens')), COMMON)
        self.as_user(self.coach)
        self.assertEqual(self.client.post('/api/common-login/password/', {'password': 'Coach-tries-2026!'},
                                          format='json').status_code, 403)

    def test_a_weak_password_or_odd_username_is_refused(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.post('/api/common-login/set-up/', {'username': 'gym screens!', 'password': TABLET_PASSWORD},
                                          format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/common-login/set-up/', {'username': 'gym-screens', 'password': 'password'},
                                          format='json').status_code, 400)
        self.assertFalse(CommonLogin.objects.exists())

    def test_any_coach_sees_it_and_its_devices_and_can_show_it(self):
        make_common()
        self.tablet('tablet-a')
        self.as_user(self.coach)
        card = self.client.get('/api/common-login/').data
        self.assertEqual(card['username'], 'gym-screens')
        self.assertEqual([d['device_id'] for d in card['devices']], ['tablet-a'])
        self.assertNotIn(TABLET_PASSWORD, str(card))           # never in the card
        shown = self.client.post('/api/common-login/show/')
        self.assertEqual(shown.data, {'password': TABLET_PASSWORD})
        self.assertEqual(shown['Cache-Control'], 'no-store')

    def test_show_gives_the_new_one_right_after_a_change(self):
        make_common()
        self.as_user(self.admin)
        self.client.post('/api/common-login/password/', {'password': 'Brand-new-screens-77!'}, format='json')
        self.as_user(self.coach)
        self.assertEqual(self.client.post('/api/common-login/show/').data['password'], 'Brand-new-screens-77!')

    def test_an_athlete_or_the_common_login_itself_cannot_show_it(self):
        common = make_common()
        for user in (self.athlete_login, common):
            self.as_user(user)
            self.assertEqual(self.client.post('/api/common-login/show/').status_code, 403)
            self.assertEqual(self.client.get('/api/common-login/').status_code, 403)

    @override_settings(EA_DEPLOYMENT='local')
    def test_a_gym_box_has_none_of_these_routes(self):
        self.as_user(self.admin)
        self.assertEqual(self.client.get('/api/common-login/').status_code, 404)


# Open to anyone by nature (signing in, a sensor claiming itself with its one-time code),
# and "who am I", which every signed-in login may ask.
OPEN_TO_COMMON = OPEN_EVERYWHERE | {'token_obtain_pair', 'token_refresh', 'sensor_claim', 'coach_session'}


@override_settings(EA_DEPLOYMENT='remote')
class TheRouteWalkTests(APITestCase):
    """The route walk's common column: until Phase 1 opens a few routes to it by name,
    the common login is turned away at the door of every route."""

    def test_every_route_refuses_the_common_login(self):
        common = make_common()
        self.client.raise_request_exception = False
        self.client.force_authenticate(user=common)
        for route in ROUTES:
            if route['name'] in OPEN_TO_COMMON:
                continue
            for method in route['methods']:
                with self.subTest(route=route['name'], method=method.upper()):
                    response = getattr(self.client, method)(route['url'], {}, format='json')
                    self.assertIn(response.status_code, (401, 403), response.status_code)
