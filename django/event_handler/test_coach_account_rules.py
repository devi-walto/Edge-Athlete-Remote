"""Tests for the server rules added on top of Braydon's coach-accounts work.

WHY THESE EXIST: his work brought the setup code, coach profiles and
administrator-only coach management. It left three gaps (spec 01):

  1. a login that existed before coach accounts had no coach profile;
  2. the coaches list showed every login, which is wrong the day athletes can log in;
  3. a box that already had coaches could end up with no administrator and no way
     to make one.

It also relied on the screen to send a coach with a temporary password to the
change-password form. These tests pin the server-side version of each rule, so none
of them depends on a screen behaving.
"""
import importlib
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from .coach_accounts import _would_remove_last_admin
from .coach_auth import issue_setup_code, setup_code_is_valid
from .models import CoachProfile, InstallationSetup

User = get_user_model()
PASSWORD = 'Unique-coach-2026!safe'
backfill = importlib.import_module(
    'event_handler.migrations.0025_coach_profiles_for_existing_logins').backfill_coach_profiles


class ProfilesForExistingLoginsTests(TestCase):
    """Gap 1: migration 0025."""

    def test_every_login_ends_up_with_exactly_one_profile(self):
        old_a = User.objects.create_user('coach_from_before', password=PASSWORD)
        old_b = User.objects.create_user('another_from_before', password=PASSWORD, is_staff=True)
        has_one = User.objects.create_user('made_on_the_new_screen', password=PASSWORD)
        CoachProfile.objects.create(user=has_one, must_change_password=True)

        self.assertEqual(backfill(User, CoachProfile), 2)

        for user in (old_a, old_b, has_one):
            self.assertEqual(CoachProfile.objects.filter(user=user).count(), 1)
        # People who already chose their own password are not forced to change it...
        self.assertFalse(CoachProfile.objects.get(user=old_a).must_change_password)
        self.assertFalse(CoachProfile.objects.get(user=old_b).must_change_password)
        # ...and a profile that already existed is left exactly as it was.
        self.assertTrue(CoachProfile.objects.get(user=has_one).must_change_password)

    def test_running_it_twice_changes_nothing(self):
        User.objects.create_user('coach_from_before', password=PASSWORD)
        backfill(User, CoachProfile)
        self.assertEqual(backfill(User, CoachProfile), 0)
        self.assertEqual(CoachProfile.objects.count(), 1)

    def test_an_empty_installation_is_fine(self):
        self.assertEqual(backfill(User, CoachProfile), 0)


class ClaimingTests(APITestCase):
    def setUp(self):
        InstallationSetup.objects.update_or_create(pk=1, defaults={'completed_at': None})
        self.code = issue_setup_code()[0]

    def claim(self, code=None, username='first'):
        return self.client.post('/api/auth/setup/', {
            'username': username, 'password': PASSWORD, 'setup_code': code or self.code}, format='json')

    def test_claiming_makes_an_administrator_who_is_also_a_coach(self):
        self.assertEqual(self.claim().status_code, 201)
        user = User.objects.get(username='first')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertEqual(CoachProfile.objects.filter(user=user).count(), 1)
        self.assertFalse(user.coach_profile.must_change_password)

    def test_a_used_code_is_dead(self):
        self.assertEqual(self.claim().status_code, 201)
        self.assertFalse(setup_code_is_valid(self.code))
        again = self.claim(username='second')
        self.assertEqual(again.status_code, 409)
        self.assertFalse(User.objects.filter(username='second').exists())

    def test_a_claimed_installation_refuses_a_second_administrator_even_with_a_new_code(self):
        self.assertEqual(self.claim().status_code, 201)
        fresh = issue_setup_code()[0]
        self.assertEqual(self.claim(code=fresh, username='second').status_code, 409)
        self.assertEqual(User.objects.count(), 1)

    def test_a_wrong_code_creates_nobody(self):
        self.assertEqual(self.claim(code='WRONGCODE').status_code, 400)
        self.assertEqual(User.objects.count(), 0)


class CoachesOnlyTests(APITestCase):
    """Gap 2: the coaches screen is for coaches."""

    def setUp(self):
        self.admin = User.objects.create_user('admin', password=PASSWORD, is_staff=True)
        CoachProfile.objects.create(user=self.admin)
        self.coach = User.objects.create_user('coach', password=PASSWORD)
        CoachProfile.objects.create(user=self.coach)
        # A login with no coach profile: what an athlete's login will be (spec 03).
        self.not_a_coach = User.objects.create_user('athlete_login', password=PASSWORD)
        self.client.force_authenticate(self.admin)

    def test_a_login_without_a_coach_profile_is_not_listed(self):
        listed = [row['username'] for row in self.client.get('/api/coaches/').data]
        self.assertEqual(listed, ['admin', 'coach'])

    def test_it_cannot_be_reset_promoted_or_deactivated_from_the_coaches_screen(self):
        before = User.objects.get(pk=self.not_a_coach.pk).password
        self.assertEqual(self.client.post(f'/api/coaches/{self.not_a_coach.pk}/reset/').status_code, 404)
        self.assertEqual(self.client.patch(
            f'/api/coaches/{self.not_a_coach.pk}/', {'is_staff': True}, format='json').status_code, 404)
        self.assertEqual(self.client.patch(
            f'/api/coaches/{self.not_a_coach.pk}/', {'is_active': False}, format='json').status_code, 404)
        after = User.objects.get(pk=self.not_a_coach.pk)
        self.assertEqual(after.password, before)
        self.assertFalse(after.is_staff)
        self.assertTrue(after.is_active)

    def test_a_regular_coach_is_refused_by_every_account_route(self):
        self.client.force_authenticate(self.coach)
        other = self.admin.pk
        self.assertEqual(self.client.get('/api/coaches/').status_code, 403)
        self.assertEqual(self.client.post('/api/coaches/', {'username': 'x'}, format='json').status_code, 403)
        self.assertEqual(self.client.post(f'/api/coaches/{other}/reset/').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/coaches/{other}/', {'is_staff': False}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/coaches/{self.coach.pk}/', {'is_staff': True}, format='json').status_code, 403)
        self.assertFalse(User.objects.get(pk=self.coach.pk).is_staff)
        self.assertFalse(User.objects.filter(username='x').exists())


class LastAdministratorTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin', password=PASSWORD, is_staff=True)
        CoachProfile.objects.create(user=self.admin)
        self.client.force_authenticate(self.admin)

    def test_nobody_can_deactivate_or_demote_themselves(self):
        for change in ({'is_active': False}, {'is_staff': False}):
            self.assertEqual(self.client.patch(
                f'/api/coaches/{self.admin.pk}/', change, format='json').status_code, 400)
        me = User.objects.get(pk=self.admin.pk)
        self.assertTrue(me.is_active and me.is_staff)

    def test_the_last_administrator_is_recognised(self):
        self.assertTrue(_would_remove_last_admin(self.admin, is_staff=False))
        self.assertTrue(_would_remove_last_admin(self.admin, is_active=False))
        second = User.objects.create_user('second', password=PASSWORD, is_staff=True)
        # The staff flag alone is not an administrator; it has to be a coach login.
        self.assertTrue(_would_remove_last_admin(self.admin, is_staff=False))
        CoachProfile.objects.create(user=second)
        self.assertFalse(_would_remove_last_admin(self.admin, is_staff=False))
        # A deactivated administrator does not count as one that remains.
        second.is_active = False
        second.save()
        self.assertTrue(_would_remove_last_admin(self.admin, is_staff=False))

    def test_one_of_two_administrators_can_be_demoted_and_then_the_other_cannot(self):
        second = User.objects.create_user('second', password=PASSWORD, is_staff=True)
        CoachProfile.objects.create(user=second)
        self.assertEqual(self.client.patch(
            f'/api/coaches/{second.pk}/', {'is_staff': False}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(
            f'/api/coaches/{self.admin.pk}/', {'is_staff': False}, format='json').status_code, 400)


class TemporaryPasswordTests(APITestCase):
    """A temporary password opens the change-password form and nothing else."""

    def setUp(self):
        self.admin = User.objects.create_user('admin', password=PASSWORD, is_staff=True)
        CoachProfile.objects.create(user=self.admin)

    def sign_in(self, username, password):
        self.client.credentials()
        login = self.client.post('/api/auth/login/', {'username': username, 'password': password}, format='json')
        self.assertEqual(login.status_code, 200, login.data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + login.data['access'])
        return login

    def new_coach(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post('/api/coaches/', {'username': 'newcoach'}, format='json')
        self.client.force_authenticate(None)
        return created.data['temporary_password']

    COACH_ROUTES = ('/api/training-groups/', '/api/training-blocks/', '/api/reports/',
                    '/api/scheduled-sessions/', '/api/racks/unassigned/')

    def test_no_coach_route_answers_until_the_password_is_changed(self):
        temp = self.new_coach()
        self.assertTrue(self.sign_in('newcoach', temp).data['must_change_password'])
        for route in self.COACH_ROUTES:
            refused = self.client.get(route)
            self.assertEqual(refused.status_code, 403, route)
            self.assertEqual(refused.data['code'], 'password_change_required', route)
        # Routes that are open to read and coach-only for more must say "change your
        # password", never "you are not signed in": a 401 makes the screens discard the
        # login and show the sign-in form again, which the coach could never get past.
        for refused in (self.client.post('/api/athletes/', {'name': 'Nope'}, format='json'),
                        self.client.get('/api/room-state/?details=true')):
            self.assertEqual(refused.status_code, 403)
            self.assertEqual(refused.data['code'], 'password_change_required')
        # The public room picture is still public.
        self.assertEqual(self.client.get('/api/room-state/').status_code, 200)

        # The way out stays open.
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        changed = self.client.post('/api/auth/password/', {
            'current_password': temp, 'new_password': 'Their-own-choice-2026!'}, format='json')
        self.assertEqual(changed.status_code, 204)

        self.sign_in('newcoach', 'Their-own-choice-2026!')
        for route in self.COACH_ROUTES:
            self.assertEqual(self.client.get(route).status_code, 200, route)

    def test_a_reset_puts_an_administrator_behind_the_same_door(self):
        second = User.objects.create_user('second', password=PASSWORD, is_staff=True)
        CoachProfile.objects.create(user=second)
        self.client.force_authenticate(self.admin)
        temp = self.client.post(f'/api/coaches/{second.pk}/reset/').data['temporary_password']
        self.client.force_authenticate(None)
        self.sign_in('second', temp)
        refused = self.client.get('/api/coaches/')
        self.assertEqual(refused.status_code, 403)
        self.assertEqual(refused.data['code'], 'password_change_required')

    def test_open_routes_do_not_care(self):
        """A rack tablet has no login at all; the rule must not reach it."""
        temp = self.new_coach()
        self.sign_in('newcoach', temp)
        self.assertEqual(self.client.get('/api/exercises/').status_code, 200)
        self.client.credentials()
        self.assertEqual(self.client.get('/api/exercises/').status_code, 200)

    def test_who_am_i(self):
        self.sign_in('admin', PASSWORD)
        self.assertEqual(self.client.get('/api/auth/me/').data, {
            'username': 'admin', 'is_staff': True, 'must_change_password': False,
            'role': 'administrator'})
        temp = self.new_coach()
        self.sign_in('newcoach', temp)
        self.assertEqual(self.client.get('/api/auth/me/').data, {
            'username': 'newcoach', 'is_staff': False, 'must_change_password': True,
            'role': 'coach'})
        self.client.credentials()
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)


class MakeAdminTests(TestCase):
    """Gap 3: an upgraded box with coaches and no administrator."""

    def run_it(self, *args):
        out = StringIO()
        call_command('make_admin', *args, stdout=out)
        return out.getvalue()

    def test_promotes_an_existing_login_and_gives_it_a_profile(self):
        user = User.objects.create_user('longtime_coach', password=PASSWORD)
        self.assertIn('now an administrator', self.run_it('longtime_coach'))
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertEqual(CoachProfile.objects.filter(user=user).count(), 1)
        self.assertTrue(user.check_password(PASSWORD))   # the password is not touched

    def test_an_unknown_username_fails_and_says_so(self):
        User.objects.create_user('longtime_coach', password=PASSWORD)
        with self.assertRaises(CommandError) as raised:
            self.run_it('nobody_by_that_name')
        self.assertIn("no login named 'nobody_by_that_name'", str(raised.exception))
        self.assertIn('longtime_coach', str(raised.exception))   # it names the ones that exist
        self.assertFalse(User.objects.filter(is_staff=True).exists())
        self.assertFalse(User.objects.filter(username='nobody_by_that_name').exists())

    def test_a_deactivated_login_needs_to_be_asked_for_explicitly(self):
        user = User.objects.create_user('left_last_year', password=PASSWORD, is_active=False)
        with self.assertRaises(CommandError):
            self.run_it('left_last_year')
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.run_it('left_last_year', '--reactivate')
        user.refresh_from_db()
        self.assertTrue(user.is_staff and user.is_active)

    def test_running_it_twice_is_harmless(self):
        User.objects.create_user('longtime_coach', password=PASSWORD)
        self.run_it('longtime_coach')
        self.run_it('longtime_coach')
        self.assertEqual(CoachProfile.objects.count(), 1)


class DemoLoginGuardTests(TestCase):
    @override_settings(DEBUG=False)
    def test_refuses_with_debug_off(self):
        with self.assertRaises(CommandError):
            call_command('ensure_demo_coach', stdout=StringIO())
        self.assertFalse(User.objects.filter(username='coach').exists())

    @override_settings(DEBUG=True)
    def test_runs_with_debug_on(self):
        call_command('ensure_demo_coach', stdout=StringIO())
        self.assertTrue(User.objects.get(username='coach').check_password('coachpass'))
