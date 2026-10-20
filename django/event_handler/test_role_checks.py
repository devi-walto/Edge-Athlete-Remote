"""Tests that walk EVERY route and check who is let through.

WHY THESE EXIST: "coach" used to mean "signed in". The day athletes can sign in,
any coach route that was missed is a route an athlete can use to edit the roster
or end a session. A hand-typed list of routes would go stale the first time
someone adds one, so these tests read the routes out of the app itself: a new
coach route is covered the moment it is added, without anyone remembering.

They also pin the rule that nothing is guarded by "signed in" alone any more,
apart from the two routes every signed-in person needs.
"""
import re

from django.contrib.auth import get_user_model
from django.urls import URLPattern, URLResolver, get_resolver
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APITestCase

from . import permissions
from .models import Athlete, CoachProfile, Node, RackScreen
from .deployment import is_hosted
from .permissions import IsCoach, IsInstallationAdmin, RemoteOnly

User = get_user_model()
PASSWORD = 'Unique-roles-2026!safe'
WRITE_OR_READ = ('get', 'post', 'put', 'patch', 'delete')
# Routes every signed-in person needs whatever their role: "who am I", and
# changing your own password. Anything else guarded by "signed in" alone is a bug.
SIGNED_IN_ONLY = {'coach_session', 'coach_password_change'}
# Signing in and renewing a sign-in: open by nature, they are how you get a login.
SIGN_IN = {'token_obtain_pair', 'token_refresh'}


def _filled(route):
    """Turn 'racks/<int:rack_number>/' into a real address with stand-in values."""
    def stand_in(match):
        kind = match.group(1) or 'str'
        return {'int': '999999', 'uuid': '00000000-0000-0000-0000-000000000000'}.get(kind, 'x')
    return re.sub(r'<(?:(\w+):)?\w+>', stand_in, route)


def _walk(patterns, prefix=''):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _walk(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            view = getattr(entry.callback, 'cls', None) or getattr(entry.callback, 'view_class', None)
            if view is None or not hasattr(view, 'permission_classes'):
                continue  # not one of ours (Django's own admin pages)
            methods = [m for m in WRITE_OR_READ
                       if m in view.http_method_names and hasattr(view, m)]
            yield {'name': entry.name, 'url': '/' + _filled(prefix + str(entry.pattern)),
                   'classes': list(view.permission_classes), 'methods': methods}


ROUTES = list(_walk(get_resolver().url_patterns))


def routes_guarded_by(permission_class):
    return [r for r in ROUTES if permission_class in r['classes']]


class RouteWalk(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('walk_admin', password=PASSWORD, is_staff=True)
        cls.coach = User.objects.create_user('walk_coach', password=PASSWORD)
        for user in (cls.admin, cls.coach):
            CoachProfile.objects.create(user=user)
        cls.athlete = User.objects.create_user('walk_athlete', password=PASSWORD)
        Athlete.objects.create(name='Walk Athlete', user=cls.athlete)
        cls.nobody = User.objects.create_user('walk_attached_to_nothing', password=PASSWORD)

    def setUp(self):
        # A stand-in address can make a view fail for its own reasons. That is not
        # what is being tested; only "was the caller refused for who they are".
        self.client.raise_request_exception = False

    def ask(self, user, method, url):
        self.client.force_authenticate(user=user)
        return getattr(self.client, method)(url, {}, format='json')

    def status(self, user, method, url):
        return self.ask(user, method, url).status_code

    def refused_for_who_they_are(self, user, method, url):
        """True if the caller was turned away at the door. A view may answer 403
        for its own reasons (the Wi-Fi route does, for a wrong password); that is
        the view running, which means the door let the caller in."""
        res = self.ask(user, method, url)
        if res.status_code == 401:
            return True
        detail = res.data.get('detail') if isinstance(getattr(res, 'data', None), dict) else None
        return res.status_code == 403 and getattr(detail, 'code', None) == 'permission_denied'

    def for_each(self, permission_class, check):
        for route in routes_guarded_by(permission_class):
            for method in route['methods']:
                with self.subTest(route=route['name'], method=method.upper()):
                    if RemoteOnly in route['classes'] and not is_hosted():
                        # An online-only route doesn't exist on a local install: 404
                        # for everyone, before any question of who is asking.
                        self.assertEqual(self.status(self.coach, method, route['url']), 404)
                    else:
                        check(method, route['url'])


class CoachRoutesTests(RouteWalk):
    def test_the_walk_actually_found_the_coach_routes(self):
        self.assertGreaterEqual(len(routes_guarded_by(IsCoach)), 40)

    def test_nobody_signed_in_gets_401(self):
        self.for_each(IsCoach, lambda m, url: self.assertEqual(self.status(None, m, url), 401))

    def test_an_athlete_gets_403(self):
        self.for_each(IsCoach, lambda m, url: self.assertEqual(self.status(self.athlete, m, url), 403))

    def test_a_login_attached_to_nothing_gets_403(self):
        self.for_each(IsCoach, lambda m, url: self.assertEqual(self.status(self.nobody, m, url), 403))

    def test_a_coach_is_not_refused(self):
        self.for_each(IsCoach, lambda m, url: self.assertFalse(
            self.refused_for_who_they_are(self.coach, m, url)))

    def test_an_administrator_is_not_refused(self):
        self.for_each(IsCoach, lambda m, url: self.assertFalse(
            self.refused_for_who_they_are(self.admin, m, url)))


class AdministratorRoutesTests(RouteWalk):
    def test_the_walk_found_them_and_they_are_all_coach_logins(self):
        found = routes_guarded_by(IsInstallationAdmin)
        self.assertGreaterEqual(len(found), 3)
        for route in found:
            self.assertTrue(route['url'].startswith('/api/coaches/'), route['url'])

    def test_a_coach_gets_403(self):
        self.for_each(IsInstallationAdmin,
                      lambda m, url: self.assertEqual(self.status(self.coach, m, url), 403))

    def test_an_athlete_and_a_login_attached_to_nothing_get_403(self):
        def check(m, url):
            self.assertEqual(self.status(self.athlete, m, url), 403)
            self.assertEqual(self.status(self.nobody, m, url), 403)
        self.for_each(IsInstallationAdmin, check)

    def test_nobody_signed_in_gets_401(self):
        self.for_each(IsInstallationAdmin,
                      lambda m, url: self.assertEqual(self.status(None, m, url), 401))

    def test_an_administrator_is_not_refused(self):
        self.for_each(IsInstallationAdmin, lambda m, url: self.assertFalse(
            self.refused_for_who_they_are(self.admin, m, url)))


class NothingIsGuardedBySignedInAloneTests(APITestCase):
    def test_every_route_names_who_it_lets_through(self):
        for route in ROUTES:
            with self.subTest(route=route['name']):
                if not route['classes']:
                    self.assertIn(route['name'], SIGN_IN)
                if IsAuthenticated in route['classes']:
                    self.assertIn(route['name'], SIGNED_IN_ONLY)

    def test_the_old_staff_check_is_gone(self):
        self.assertFalse(hasattr(permissions, 'IsActiveStaff'))


class OpenToReadCoachToWriteTests(RouteWalk):
    """Two routes anyone may read but only a coach may use fully. They check inside
    the view, not with a permission class, so the walk above does not reach them."""

    def test_an_athlete_cannot_add_an_athlete(self):
        self.assertEqual(self.status(self.athlete, 'post', '/api/athletes/'), 403)
        self.assertEqual(self.status(self.nobody, 'post', '/api/athletes/'), 403)
        self.assertEqual(self.status(None, 'post', '/api/athletes/'), 401)

    def test_a_coach_can_still_add_an_athlete(self):
        self.client.force_authenticate(user=self.coach)
        res = self.client.post('/api/athletes/', {'name': 'New Lifter'}, format='json')
        self.assertEqual(res.status_code, 201)


class RoomLayoutIsForEveryCoachTests(RouteWalk):
    """Decided 2026-10-06: a regular coach can set a room up. These used to need
    the administrator flag."""
    ROOM_LAYOUT = {'rack_assign', 'rack_remove', 'racks_release_all', 'rack_node_assignment',
                   'ble_scans', 'ble_verifications', 'rack_ble_selection', 'node_acquisition_kind'}

    def test_every_room_layout_route_takes_the_coach_check(self):
        by_name = {r['name']: r for r in ROUTES}
        for name in self.ROOM_LAYOUT:
            with self.subTest(route=name):
                self.assertIn(name, by_name)
                self.assertEqual(by_name[name]['classes'], [IsCoach])

    def test_a_regular_coach_can_release_every_rack(self):
        self.assertEqual(self.status(self.coach, 'post', '/api/racks/release-all/'), 200)

    def test_a_regular_coach_sets_one_rack_up_from_start_to_finish(self):
        screen = RackScreen.objects.create(device_id='walk-tablet')
        first = Node.objects.create(node_id='walk-sensor-1', last_seen=timezone.now(),
                                    acquisition_kind=Node.ACQUISITION_MQTT)
        second = Node.objects.create(node_id='walk-sensor-2', last_seen=timezone.now(),
                                     acquisition_kind=Node.ACQUISITION_MQTT)
        self.client.force_authenticate(user=self.coach)

        # 1. put the tablet on rack 3
        res = self.client.patch('/api/racks/walk-tablet/', {'rack_number': 3}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        # 2. link a sensor, 3. replace it with another
        for node in (first, second):
            res = self.client.put('/api/racks/node-assignment/',
                                  {'device_id': 'walk-tablet', 'node_id': node.node_id}, format='json')
            self.assertEqual(res.status_code, 200, res.data)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertIsNone(first.rack_number)
        self.assertEqual(second.rack_number, 3)
        # 4. take the rack back out of the room
        res = self.client.delete('/api/racks/3/')
        self.assertEqual(res.status_code, 200, res.data)
        screen.refresh_from_db()
        self.assertIsNone(screen.rack_number)
