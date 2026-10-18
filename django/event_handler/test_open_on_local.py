"""Tests for the routes that are open on a gym box and locked on a hosted installation.

WHY THESE EXIST: in a gym the Wi-Fi is the lock, so 21 routes answer with no login
(a rack tablet has nobody to sign in). On the internet there is no Wi-Fi lock. These
tests walk every one of those routes, read straight from the URL configuration, in
BOTH kinds of installation:

  - gym box: exactly as open as before, so a rack tablet in a gym is never asked to
    sign in;
  - hosted: nobody gets in without a login, and each route lets through only the
    roles its rule names.

They also keep the list of open routes short on purpose: a route left fully open has
to be added to the allow-list below by hand, so it cannot happen by accident.
"""
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.permissions import AllowAny
from rest_framework.test import APITestCase

from .models import Athlete, CoachProfile
from .permissions import (ONLINE_ANY_ROLE, ONLINE_COACH, ONLINE_COACH_OR_RACK_OWNER,
                          ONLINE_COACH_OR_SAME_ATHLETE, ONLINE_REFUSE, OpenOnLocal)
from .test_role_checks import ROUTES

User = get_user_model()
PASSWORD = 'Unique-online-2026!safe'

# Fully open in both kinds of installation, on purpose. Add to this only deliberately.
#   health: the container's health check cannot sign in;
#   system_info: the sign-in screen asks which kind of installation this is;
#   coach_setup: claiming a brand-new installation, before any login exists;
#   login_link_lookup, login_link_redeem: an athlete using the link their coach sent,
#     before they have a login (spec 03). The link is the proof.
OPEN_EVERYWHERE = {'health', 'system_info', 'coach_setup',
                   'login_link_lookup', 'login_link_redeem'}
# Signing in and renewing a sign-in have no permission classes at all.
SIGN_IN = {'token_obtain_pair', 'token_refresh'}

OPEN_ON_LOCAL = [r for r in ROUTES if any(isinstance(c, type) and issubclass(c, OpenOnLocal)
                                          for c in r['classes'])]


def online_rule(route):
    return next(c.online_rule for c in route['classes'] if issubclass(c, OpenOnLocal))


def routes_with(rule):
    return [r for r in OPEN_ON_LOCAL if online_rule(r) == rule]


class Walk(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.coach = User.objects.create_user('online_coach', password=PASSWORD)
        CoachProfile.objects.create(user=cls.coach)
        cls.athlete_login = User.objects.create_user('online_athlete', password=PASSWORD)
        cls.athlete = Athlete.objects.create(name='Online Athlete', user=cls.athlete_login)
        cls.other = Athlete.objects.create(name='Someone Else')
        cls.nobody = User.objects.create_user('online_nobody', password=PASSWORD)

    def setUp(self):
        # A stand-in address can make a view fail for its own reasons; only "was the
        # caller turned away at the door" is being tested here.
        self.client.raise_request_exception = False

    def status(self, user, method, url):
        self.client.force_authenticate(user=user)
        return getattr(self.client, method)(url, {}, format='json').status_code

    def for_each(self, routes, check):
        for route in routes:
            for method in route['methods']:
                with self.subTest(route=route['name'], method=method.upper()):
                    check(method, route['url'])


class TheListTests(Walk):
    def test_there_are_exactly_21(self):
        self.assertEqual(len(OPEN_ON_LOCAL), 21, sorted(r['name'] for r in OPEN_ON_LOCAL))

    def test_every_route_has_a_known_online_rule(self):
        known = {ONLINE_COACH, ONLINE_ANY_ROLE, ONLINE_COACH_OR_SAME_ATHLETE,
                 ONLINE_COACH_OR_RACK_OWNER, ONLINE_REFUSE}
        for route in OPEN_ON_LOCAL:
            with self.subTest(route=route['name']):
                self.assertIn(online_rule(route), known)

    def test_nothing_else_is_fully_open(self):
        for route in ROUTES:
            with self.subTest(route=route['name']):
                if AllowAny in route['classes']:
                    self.assertIn(route['name'], OPEN_EVERYWHERE)
                if not route['classes']:
                    self.assertIn(route['name'], SIGN_IN)


@override_settings(EA_DEPLOYMENT='local')
class LocalTests(Walk):
    """Local (a gym box), today's behaviour: nobody is asked to sign in on any of the 21."""

    def for_each_open(self, check):
        # Adding an athlete (POST /api/athletes/) was coach-only on a gym box before
        # this spec too: the view itself asks for a coach. Only its GET is open.
        def skip_coach_write(m, url):
            if url == '/api/athletes/' and m == 'post':
                return
            check(m, url)
        self.for_each(OPEN_ON_LOCAL, skip_coach_write)

    def test_no_login_is_needed(self):
        self.for_each_open(lambda m, url: self.assertNotIn(self.status(None, m, url), (401, 403)))

    def test_an_athlete_login_is_not_turned_away_either(self):
        self.for_each_open(lambda m, url: self.assertNotIn(
            self.status(self.athlete_login, m, url), (401, 403)))


@override_settings(EA_DEPLOYMENT='remote')
class RemoteTests(Walk):
    def test_no_login_gets_nothing(self):
        def check(m, url):
            self.assertIn(self.status(None, m, url), (401, 403))
        self.for_each(OPEN_ON_LOCAL, check)
        # and 401 specifically, wherever the route exists at all online
        self.for_each([r for r in OPEN_ON_LOCAL if online_rule(r) != ONLINE_REFUSE],
                      lambda m, url: self.assertEqual(self.status(None, m, url), 401))

    def test_a_login_attached_to_nothing_gets_nothing(self):
        self.for_each(OPEN_ON_LOCAL, lambda m, url: self.assertEqual(
            self.status(self.nobody, m, url), 403))

    def test_a_coach_gets_through_everywhere_the_route_exists_online(self):
        self.for_each([r for r in OPEN_ON_LOCAL if online_rule(r) != ONLINE_REFUSE],
                      lambda m, url: self.assertNotIn(self.status(self.coach, m, url), (401, 403)))

    def test_the_shared_room_routes_are_refused_to_everyone(self):
        refused = routes_with(ONLINE_REFUSE)
        self.assertEqual({r['name'] for r in refused},
                         {'rack_register', 'rack_racknumber', 'rack_nfc_tap'})
        for user in (None, self.coach, self.athlete_login):
            self.for_each(refused, lambda m, url: self.assertEqual(self.status(user, m, url), 403))

    def test_an_athlete_is_refused_the_coach_routes(self):
        coach_only = routes_with(ONLINE_COACH)
        self.assertEqual({r['name'] for r in coach_only},
                         {'athletes', 'nodes_list', 'node_register', 'room_state'})
        self.for_each(coach_only, lambda m, url: self.assertEqual(
            self.status(self.athlete_login, m, url), 403))

    def test_an_athlete_gets_the_routes_any_role_may_read(self):
        self.for_each(routes_with(ONLINE_ANY_ROLE), lambda m, url: self.assertNotIn(
            self.status(self.athlete_login, m, url), (401, 403)))

    def test_an_athlete_is_refused_rack_routes_until_spec_04_records_owners(self):
        self.for_each(routes_with(ONLINE_COACH_OR_RACK_OWNER), lambda m, url: self.assertEqual(
            self.status(self.athlete_login, m, url), 403))

    def test_an_athlete_may_read_their_own_plan_and_progress_and_nobody_elses(self):
        own, other = self.athlete.pk, self.other.pk
        self.assertNotIn(self.status(self.athlete_login, 'get', f'/api/prescriptions/?athlete={own}'), (401, 403))
        self.assertEqual(self.status(self.athlete_login, 'get', f'/api/prescriptions/?athlete={other}'), 403)
        self.assertEqual(self.status(self.athlete_login, 'get', '/api/prescriptions/'), 403)
        self.assertEqual(self.status(self.athlete_login, 'post', '/api/prescriptions/'), 403)
        progress = '/api/sessions/active/athlete/{}/progress/'
        self.assertNotIn(self.status(self.athlete_login, 'get', progress.format(own)), (401, 403))
        self.assertEqual(self.status(self.athlete_login, 'get', progress.format(other)), 403)

    def test_a_coach_on_a_temporary_password_is_sent_to_change_it(self):
        CoachProfile.objects.filter(user=self.coach).update(must_change_password=True)
        self.client.force_authenticate(User.objects.get(pk=self.coach.pk))
        res = self.client.get('/api/athletes/')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data['code'], 'password_change_required')
