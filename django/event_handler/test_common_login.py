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
# Phase 1: read only, whatever the address (an athlete's day needs a real athlete, and
# the walk's stand-in isn't one, so it is refused there and tested below).
COMMON_READS = {'sessions_active', 'session_status', 'room_state'}
# Phase 1: only for a rack its own device made. The walk's stand-in rack (999999) isn't
# one, so the walk sees them refused too; the tests below use a real one.
COMMON_OWN_RACK = {'rack_state', 'rack_controller_acquire', 'rack_controller_heartbeat',
                   'rack_controller_release', 'rack_checkin', 'rack_checkins',
                   'set_create', 'set_complete'}


@override_settings(EA_DEPLOYMENT='remote')
class TabletTestCase(CommonLoginTestCase):
    """A tablet signed in with the common login, its device owning Rack 3; another
    device owns Rack 4. A running session with two athletes."""

    def setUp(self):
        super().setUp()
        from .models import Exercise, Node, RackScreen, TrainingSession
        make_common()
        self.tokens = self.tablet('tablet-3')
        RackScreen.objects.create(device_id='tablet-3', rack_number=3)
        RackScreen.objects.create(device_id='tablet-4', rack_number=4)
        self.node3 = Node.objects.create(node_id='bar-3', rack_number=3)
        self.node4 = Node.objects.create(node_id='bar-4', rack_number=4)
        self.session = TrainingSession.objects.create(label='Thursday', started_at=timezone.now())
        self.riley = Athlete.objects.create(name='Riley Brooks')
        self.jordan = Athlete.objects.create(name='Jordan Lee')
        self.session.athletes.add(self.riley, self.jordan)
        self.outsider = Athlete.objects.create(name='Not Here Today')
        self.squat, _ = Exercise.objects.get_or_create(name='Back Squat')
        self.client.raise_request_exception = False

    def call(self, method, url, body=None):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens['access']}")
        response = getattr(self.client, method)(url, body or {}, format='json')
        self.client.credentials()
        return response

    def refused(self, response):
        if response.status_code == 401:
            return True
        detail = response.data.get('detail') if isinstance(getattr(response, 'data', None), dict) else None
        return response.status_code == 403 and getattr(detail, 'code', None) == 'permission_denied'


class TheRouteWalkTests(TabletTestCase):
    """The route walk's common column: through only where Phase 1 opens a route to it."""

    def test_every_route_refuses_the_common_login_except_what_phase_1_opens(self):
        for route in ROUTES:
            if route['name'] in OPEN_TO_COMMON:
                continue
            for method in route['methods']:
                with self.subTest(route=route['name'], method=method.upper()):
                    response = self.call(method, route['url'])
                    if route['name'] in COMMON_READS and method == 'get':
                        self.assertFalse(self.refused(response), response.status_code)
                    else:
                        self.assertTrue(self.refused(response), response.status_code)


class WhatATabletReadsTests(TabletTestCase):
    """What the rack screen needs (Devin, 2026-11-12): the names, At this rack, statuses."""

    def test_the_check_in_names_come_from_the_running_session(self):
        response = self.call('get', '/api/sessions/active/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(a['name'] for a in response.data['roster']), ['Jordan Lee', 'Riley Brooks'])

    def test_at_this_rack_for_its_own_rack_only(self):
        from .models import RackCheckIn
        # Checking in needs the rack's controller lease (its own tests cover that); here,
        # only that the door lets the tablet in on its own rack.
        self.assertFalse(self.refused(self.call('post', '/api/racks/3/checkin/', {'athlete': self.riley.pk})))
        RackCheckIn.objects.create(session=self.session, athlete=self.riley, rack_number=3)
        at_rack = self.call('get', '/api/racks/3/checkins/')
        self.assertEqual(at_rack.status_code, 200)
        self.assertEqual([a['name'] for a in at_rack.data['athletes']], ['Riley Brooks'])
        self.assertTrue(self.refused(self.call('get', '/api/racks/4/checkins/')))
        self.assertTrue(self.refused(self.call('post', '/api/racks/4/checkin/', {'athlete': self.riley.pk})))

    def test_resting_lifting_ready_for_everyone_in_the_session(self):
        response = self.call('get', '/api/sessions/active/status/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual({a['athlete_id'] for a in response.data['athletes']}, {self.riley.pk, self.jordan.pk})

    def test_an_athletes_day_only_for_someone_in_the_session(self):
        url = '/api/sessions/active/athlete/{}/progress/'
        self.assertEqual(self.call('get', url.format(self.riley.pk)).status_code, 200)
        self.assertTrue(self.refused(self.call('get', url.format(self.outsider.pk))))

    def test_the_room_display_without_the_coach_details(self):
        self.assertEqual(self.call('get', '/api/room-state/').status_code, 200)
        self.assertIn(self.call('get', '/api/room-state/?details=true').status_code, (401, 403))

    def test_reading_never_writes(self):
        self.assertTrue(self.refused(self.call('post', '/api/sessions/active/')))


class ItsOwnRackTests(TabletTestCase):
    def test_its_racks_state_and_controller(self):
        for method, url in (('get', '/api/racks/3/state/'), ('patch', '/api/racks/3/state/'),
                            ('post', '/api/racks/3/controller/acquire/'),
                            ('post', '/api/racks/3/controller/heartbeat/'),
                            ('post', '/api/racks/3/controller/release/')):
            with self.subTest(method=method, url=url):
                self.assertFalse(self.refused(self.call(method, url)))
                self.assertTrue(self.refused(self.call(method, url.replace('/3/', '/4/'))))

    def test_starting_a_set_names_its_own_rack(self):
        body = {'session': self.session.pk, 'athlete': self.riley.pk, 'exercise': self.squat.pk,
                'set_number': 1, 'rack_number': 3}
        self.assertFalse(self.refused(self.call('post', '/api/sets/', body)))
        self.assertTrue(self.refused(self.call('post', '/api/sets/', {**body, 'rack_number': 4})))
        self.assertTrue(self.refused(self.call('post', '/api/sets/', {k: v for k, v in body.items() if k != 'rack_number'})))

    def test_finishing_a_set_on_its_own_rack_only(self):
        from .models import Set
        mine = Set.objects.create(session=self.session, athlete=self.riley, exercise=self.squat,
                                  set_number=1, node=self.node3)
        theirs = Set.objects.create(session=self.session, athlete=self.jordan, exercise=self.squat,
                                    set_number=1, node=self.node4)
        self.assertFalse(self.refused(self.call('post', f'/api/sets/{mine.pk}/complete/')))
        self.assertTrue(self.refused(self.call('post', f'/api/sets/{theirs.pk}/complete/')))

    def test_a_signed_out_device_loses_its_rack(self):
        CommonDevice.objects.filter(device_id='tablet-3').update(signed_out_at=timezone.now())
        self.assertEqual(self.call('get', '/api/racks/3/checkins/').status_code, 401)
