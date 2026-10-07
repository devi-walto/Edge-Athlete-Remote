"""Tests for roles.py: working out who a login is from what it is attached to.

WHY THESE EXIST: every permission check is about to ask role_of(). If it ever
answers "coach" for an athlete, an athlete can run the gym; if it ever answers
None for a real coach, that coach is locked out. These pin every kind of login,
including the broken ones, and that removing a login never removes an athlete's
history.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone

from .models import Athlete, CoachProfile, Exercise, Rep, Set, TrainingSession
from .roles import role_of

User = get_user_model()


def make_login(username, *, coach=False, athlete=False, **flags):
    user = User.objects.create_user(username, password='Unique-roles-2026!safe', **flags)
    if coach:
        CoachProfile.objects.create(user=user)
    if athlete:
        Athlete.objects.create(name=f'{username} (athlete)', user=user)
    return user


class RoleOfTests(TestCase):
    def test_a_coach_profile_with_the_staff_flag_is_an_administrator(self):
        self.assertEqual(role_of(make_login('head', coach=True, is_staff=True)), 'administrator')

    def test_a_coach_profile_is_a_coach(self):
        self.assertEqual(role_of(make_login('assistant', coach=True)), 'coach')

    def test_an_athlete_record_is_an_athlete(self):
        self.assertEqual(role_of(make_login('lifter', athlete=True)), 'athlete')

    def test_the_staff_flag_does_not_make_an_athlete_an_administrator(self):
        self.assertEqual(role_of(make_login('lifter', athlete=True, is_staff=True)), 'athlete')

    def test_a_login_attached_to_nothing_is_refused(self):
        self.assertIsNone(role_of(make_login('half_made')))

    def test_the_staff_flag_alone_is_refused(self):
        self.assertIsNone(role_of(make_login('staff_only', is_staff=True)))

    def test_a_login_attached_to_both_is_refused_and_logged(self):
        both = make_login('both', coach=True, athlete=True)
        with self.assertLogs('event_handler.roles', level='WARNING') as logs:
            self.assertIsNone(role_of(both))
        self.assertIn('both a coach profile and an athlete record', logs.output[0])

    def test_a_switched_off_login_of_any_kind_is_refused(self):
        for name, kind in (('off_admin', dict(coach=True, is_staff=True)),
                           ('off_coach', dict(coach=True)),
                           ('off_athlete', dict(athlete=True))):
            with self.subTest(name):
                self.assertIsNone(role_of(make_login(name, is_active=False, **kind)))

    def test_nobody_signed_in_is_refused(self):
        self.assertIsNone(role_of(AnonymousUser()))
        self.assertIsNone(role_of(None))

    def test_the_answer_follows_the_database_not_a_stale_copy(self):
        user = make_login('promoted', coach=True)
        self.assertEqual(role_of(user), 'coach')
        User.objects.filter(pk=user.pk).update(is_staff=True)
        self.assertEqual(role_of(User.objects.get(pk=user.pk)), 'administrator')


class RemovingALoginKeepsTheAthleteTests(TestCase):
    def test_the_athlete_and_their_history_survive(self):
        user = make_login('leaving', athlete=True)
        athlete = Athlete.objects.get(user=user)
        lifted = Set.objects.create(
            session=TrainingSession.objects.create(), athlete=athlete,
            exercise=Exercise.objects.get_or_create(name='Back Squat')[0], set_number=1)
        Rep.objects.create(set=lifted, rep_number=1, timestamp=timezone.now(),
                           mean_velocity=0.6, peak_velocity=0.8, duration_ms=900,
                           velocity_color='green')

        user.delete()

        athlete.refresh_from_db()
        self.assertIsNone(athlete.user)
        self.assertEqual(Set.objects.filter(athlete=athlete).count(), 1)
        self.assertEqual(Rep.objects.filter(set__athlete=athlete).count(), 1)
