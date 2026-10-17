"""Tests for services/login_links.py: the one-time links that give athletes their logins.

WHY THESE EXIST: a login link is as good as a password for that athlete. These pin
that it behaves like one (works once, runs out, a newer one cancels it, never stored
in readable form), that every failure looks the same from outside, and that using
one replaces the athlete's login without touching a single set or rep.
"""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Athlete, AthleteLoginLink, CoachProfile, Exercise, Rep, Set, TrainingSession
from .roles import role_of
from .services import login_links
from .services.login_links import LinkDoesNotWork

User = get_user_model()
PASSWORD = 'Unique-links-2026!safe'


class LoginLinkTestCase(TestCase):
    def setUp(self):
        self.coach = User.objects.create_user('coach', password=PASSWORD)
        CoachProfile.objects.create(user=self.coach)
        self.athlete = Athlete.objects.create(name='Riley Brooks')


class IssueTests(LoginLinkTestCase):
    def test_issuing_twice_leaves_exactly_one_usable_link(self):
        first = login_links.issue(self.athlete, self.coach)
        second = login_links.issue(self.athlete, self.coach)

        self.assertIsNone(login_links.find(first))
        self.assertIsNotNone(login_links.find(second))
        usable = [l for l in AthleteLoginLink.objects.all() if login_links._still_works(l)]
        self.assertEqual(len(usable), 1)

    def test_the_plain_link_is_stored_nowhere(self):
        link = login_links.issue(self.athlete, self.coach)
        secret = link.split('.', 1)[1]

        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM event_handler_athleteloginlink')
            stored = ' '.join(str(value) for row in cursor.fetchall() for value in row)
        self.assertNotIn(secret, stored)
        self.assertNotIn(link, stored)

    def test_a_link_runs_out_after_three_days(self):
        login_links.issue(self.athlete, self.coach)
        row = AthleteLoginLink.objects.get()
        self.assertEqual(row.expires_at - row.created_at, timedelta(days=3))


class FindTests(LoginLinkTestCase):
    """Every failure is None, so a caller can't tell one reason from another."""

    def setUp(self):
        super().setUp()
        self.link = login_links.issue(self.athlete, self.coach)
        self.row = AthleteLoginLink.objects.get()

    def test_a_good_link_is_found(self):
        self.assertEqual(login_links.find(self.link), self.row)

    def test_a_wrong_secret(self):
        self.assertIsNone(login_links.find(f'{self.row.lookup}.not-the-secret'))

    def test_an_expired_link(self):
        AthleteLoginLink.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertIsNone(login_links.find(self.link))

    def test_a_used_link(self):
        AthleteLoginLink.objects.update(used_at=timezone.now())
        self.assertIsNone(login_links.find(self.link))

    def test_a_cancelled_link(self):
        AthleteLoginLink.objects.update(cancelled_at=timezone.now())
        self.assertIsNone(login_links.find(self.link))

    def test_an_unknown_lookup(self):
        self.assertIsNone(login_links.find('nosuchlookup.' + self.link.split('.', 1)[1]))

    def test_nonsense(self):
        for text in ['', None, 'no-dot', '.', 'only.', '.only']:
            self.assertIsNone(login_links.find(text))

    def test_an_archived_athletes_link(self):
        self.athlete.is_active = False
        self.athlete.save()
        self.assertIsNone(login_links.find(self.link))


class RedeemTests(LoginLinkTestCase):
    def test_a_first_login_is_an_athlete_login_with_no_coach_profile(self):
        login = login_links.redeem(login_links.issue(self.athlete, self.coach), 'riley', PASSWORD)

        self.athlete.refresh_from_db()
        self.assertEqual(self.athlete.user, login)
        self.assertEqual(role_of(login), 'athlete')
        self.assertFalse(CoachProfile.objects.filter(user=login).exists())
        self.assertTrue(login.check_password(PASSWORD))

    def test_a_link_works_only_once(self):
        link = login_links.issue(self.athlete, self.coach)
        login_links.redeem(link, 'riley', PASSWORD)
        with self.assertRaises(LinkDoesNotWork):
            login_links.redeem(link, 'riley2', PASSWORD)

    def test_a_new_link_replaces_the_login_and_keeps_every_set_and_rep(self):
        old = login_links.redeem(login_links.issue(self.athlete, self.coach), 'riley', PASSWORD)
        lifted = Set.objects.create(
            session=TrainingSession.objects.create(), athlete=self.athlete,
            exercise=Exercise.objects.get_or_create(name='Back Squat')[0], set_number=1)
        Rep.objects.create(set=lifted, rep_number=1, timestamp=timezone.now(),
                           mean_velocity=0.6, peak_velocity=0.8, duration_ms=900,
                           velocity_color='green')
        sets_before = list(Set.objects.filter(athlete=self.athlete).values())
        reps_before = list(Rep.objects.filter(set__athlete=self.athlete).values())
        old_token = str(RefreshToken.for_user(old).access_token)
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f'Bearer {old_token}')
        self.assertEqual(api.get('/api/auth/me/').status_code, 200)

        # Forgot the password: the coach sends a new link, and the athlete keeps
        # the same username.
        new = login_links.redeem(login_links.issue(self.athlete, self.coach), 'riley', PASSWORD)

        old.refresh_from_db()
        self.athlete.refresh_from_db()
        self.assertFalse(old.is_active)
        self.assertEqual(self.athlete.user, new)
        self.assertEqual(new.username, 'riley')
        self.assertEqual(api.get('/api/auth/me/').status_code, 401)   # signed out everywhere
        self.assertEqual(list(Set.objects.filter(athlete=self.athlete).values()), sets_before)
        self.assertEqual(list(Rep.objects.filter(set__athlete=self.athlete).values()), reps_before)

    def test_a_weak_password_changes_nothing(self):
        old = login_links.redeem(login_links.issue(self.athlete, self.coach), 'riley', PASSWORD)
        link = login_links.issue(self.athlete, self.coach)

        with self.assertRaises(ValidationError):
            login_links.redeem(link, 'riley-new', 'password')

        self._assert_nothing_changed(old, link)

    def test_a_taken_username_changes_nothing(self):
        old = login_links.redeem(login_links.issue(self.athlete, self.coach), 'riley', PASSWORD)
        link = login_links.issue(self.athlete, self.coach)

        with self.assertRaises(ValidationError):
            login_links.redeem(link, 'coach', PASSWORD)

        self._assert_nothing_changed(old, link)

    def test_a_failure_after_the_old_login_is_switched_off_changes_nothing(self):
        # The very last step fails: everything before it must be undone too.
        old = login_links.redeem(login_links.issue(self.athlete, self.coach), 'riley', PASSWORD)
        link = login_links.issue(self.athlete, self.coach)

        with mock.patch.object(AthleteLoginLink, 'save', side_effect=RuntimeError('disk full')):
            with self.assertRaises(RuntimeError):
                login_links.redeem(link, 'riley-new', PASSWORD)

        self._assert_nothing_changed(old, link)

    def _assert_nothing_changed(self, old, link):
        old.refresh_from_db()
        self.athlete.refresh_from_db()
        self.assertTrue(old.is_active)
        self.assertEqual(old.username, 'riley')
        self.assertEqual(self.athlete.user, old)
        self.assertIsNotNone(login_links.find(link))   # still unused, still works


class UnlinkTests(LoginLinkTestCase):
    def test_unlink_switches_the_login_off_and_cancels_the_link(self):
        login = login_links.redeem(login_links.issue(self.athlete, self.coach), 'riley', PASSWORD)
        pending = login_links.issue(self.athlete, self.coach)

        login_links.unlink(self.athlete)

        login.refresh_from_db()
        self.athlete.refresh_from_db()
        self.assertFalse(login.is_active)
        self.assertIsNone(self.athlete.user)
        self.assertIsNone(login_links.find(pending))
        self.assertTrue(Athlete.objects.filter(pk=self.athlete.pk).exists())

    def test_unlink_with_no_login_is_harmless(self):
        login_links.unlink(self.athlete)
        self.athlete.refresh_from_db()
        self.assertIsNone(self.athlete.user)
