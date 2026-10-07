"""Tests for what sign-in says about who signed in, and for archiving an athlete.

WHY THESE EXIST: the screens decide what to show from the role that sign-in
reports, so it has to be right for all three roles. A login attached to nothing
must be stopped at the door with a plain sentence, not handed a key that opens
nothing. And archiving an athlete has to end their access at once, including
for a phone that signed in before the archive, without touching their history.

These use real sign-in tokens on purpose: the point is what the real door does.
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Athlete, CoachProfile, Exercise, Rep, Set, TrainingSession

User = get_user_model()
PASSWORD = 'Unique-roles-2026!safe'
LOGIN = '/api/auth/login/'
ME = '/api/auth/me/'


class SignInBase(APITestCase):
    def make(self, username, *, coach=False, athlete_name=None, **flags):
        user = User.objects.create_user(username, password=PASSWORD, **flags)
        if coach:
            CoachProfile.objects.create(user=user)
        if athlete_name:
            Athlete.objects.create(name=athlete_name, user=user)
        return user

    def sign_in(self, username):
        return self.client.post(LOGIN, {'username': username, 'password': PASSWORD}, format='json')

    def use(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


class SignInSaysWhoSignedInTests(SignInBase):
    def test_an_administrator(self):
        self.make('head', coach=True, is_staff=True)
        data = self.sign_in('head').data
        self.assertEqual(data['role'], 'administrator')
        self.assertNotIn('athlete_id', data)

    def test_a_coach(self):
        self.make('assistant', coach=True)
        data = self.sign_in('assistant').data
        self.assertEqual(data['role'], 'coach')
        self.assertNotIn('athlete_id', data)
        self.assertNotIn('athlete_name', data)

    def test_an_athlete_also_gets_their_athlete_record(self):
        user = self.make('lifter', athlete_name='Jordan Lee')
        data = self.sign_in('lifter').data
        self.assertEqual(data['role'], 'athlete')
        self.assertEqual(data['athlete_id'], user.athlete.pk)
        self.assertEqual(data['athlete_name'], 'Jordan Lee')
        self.assertFalse(data['must_change_password'])

    def test_who_am_i_gives_the_same_answer(self):
        user = self.make('lifter', athlete_name='Jordan Lee')
        self.make('assistant', coach=True)
        self.use(self.sign_in('lifter').data['access'])
        me = self.client.get(ME).data
        self.assertEqual((me['role'], me['athlete_id'], me['athlete_name']),
                         ('athlete', user.athlete.pk, 'Jordan Lee'))
        self.use(self.sign_in('assistant').data['access'])
        me = self.client.get(ME).data
        self.assertEqual(me['role'], 'coach')
        self.assertNotIn('athlete_id', me)


class ALoginAttachedToNothingTests(SignInBase):
    def test_it_cannot_sign_in_and_is_told_why(self):
        self.make('half_made')
        res = self.sign_in('half_made')
        self.assertEqual(res.status_code, 401)
        self.assertNotIn('access', res.data)
        self.assertIn('not set up as a coach or an athlete', str(res.data['detail']))

    def test_the_staff_flag_alone_does_not_get_in(self):
        self.make('staff_only', is_staff=True)
        self.assertEqual(self.sign_in('staff_only').status_code, 401)

    def test_a_login_attached_to_both_does_not_get_in(self):
        self.make('both', coach=True, athlete_name='Both Ways')
        with self.assertLogs('event_handler.roles', level='WARNING'):
            self.assertEqual(self.sign_in('both').status_code, 401)

    def test_a_wrong_password_still_reads_as_a_wrong_password(self):
        self.make('assistant', coach=True)
        res = self.client.post(LOGIN, {'username': 'assistant', 'password': 'nope'}, format='json')
        self.assertEqual(res.status_code, 401)
        self.assertNotIn('not set up', str(res.data['detail']))


class ArchivingAnAthleteTests(SignInBase):
    def setUp(self):
        self.coach = self.make('assistant', coach=True)
        self.login = self.make('lifter', athlete_name='Jordan Lee')
        self.athlete = self.login.athlete
        lifted = Set.objects.create(
            session=TrainingSession.objects.create(label='Past', ended_at=timezone.now()),
            athlete=self.athlete, exercise=Exercise.objects.get_or_create(name='Back Squat')[0],
            set_number=1)
        Rep.objects.create(set=lifted, rep_number=1, timestamp=timezone.now(), mean_velocity=0.6,
                           peak_velocity=0.8, duration_ms=900, velocity_color='green')

    def archive_as_the_coach(self):
        self.client.credentials()
        self.client.force_authenticate(self.coach)
        self.assertEqual(self.client.delete(f'/api/athletes/{self.athlete.pk}/').status_code, 204)
        self.client.force_authenticate(None)

    def history(self):
        return (Set.objects.filter(athlete=self.athlete).count(),
                Rep.objects.filter(set__athlete=self.athlete).count())

    def test_a_token_from_before_the_archive_stops_working_at_once(self):
        tokens = self.sign_in('lifter').data
        self.use(tokens['access'])
        self.assertEqual(self.client.get(ME).status_code, 200)

        self.archive_as_the_coach()

        self.use(tokens['access'])
        self.assertEqual(self.client.get(ME).status_code, 401)
        self.client.credentials()
        renewed = self.client.post('/api/auth/refresh/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(renewed.status_code, 401)
        self.assertEqual(self.sign_in('lifter').status_code, 401)

    def test_bringing_them_back_restores_sign_in_and_history_is_untouched(self):
        before = self.history()
        self.archive_as_the_coach()
        self.assertEqual(self.sign_in('lifter').status_code, 401)
        self.assertEqual(self.history(), before)

        athlete = Athlete.objects.get(pk=self.athlete.pk)
        athlete.is_active = True
        athlete.save()

        self.assertEqual(self.sign_in('lifter').data['role'], 'athlete')
        self.assertEqual(self.history(), before)

    def test_editing_an_athlete_never_switches_a_login_back_on(self):
        """Only archiving and un-archiving touch the login. If a login was switched
        off some other way, renaming the athlete must not quietly re-open it."""
        User.objects.filter(pk=self.login.pk).update(is_active=False)
        athlete = Athlete.objects.get(pk=self.athlete.pk)
        athlete.notes = 'left knee'
        athlete.save()
        athlete.name = 'Jordan A. Lee'
        athlete.save(update_fields=['name'])
        self.assertFalse(User.objects.get(pk=self.login.pk).is_active)

    def test_archiving_an_athlete_with_no_login_still_works(self):
        plain = Athlete.objects.create(name='No Login')
        self.client.force_authenticate(self.coach)
        self.assertEqual(self.client.delete(f'/api/athletes/{plain.pk}/').status_code, 204)
        plain.refresh_from_db()
        self.assertFalse(plain.is_active)


class RenewingASignInTests(SignInBase):
    def renew(self, refresh):
        self.client.credentials()
        return self.client.post('/api/auth/refresh/', {'refresh': refresh}, format='json')

    def test_a_working_login_can_renew(self):
        self.make('assistant', coach=True)
        res = self.renew(self.sign_in('assistant').data['refresh'])
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)

    def test_a_deactivated_coach_cannot_renew(self):
        coach = self.make('assistant', coach=True)
        refresh = self.sign_in('assistant').data['refresh']
        User.objects.filter(pk=coach.pk).update(is_active=False)
        self.assertEqual(self.renew(refresh).status_code, 401)

    def test_a_login_that_lost_its_role_cannot_renew(self):
        coach = self.make('assistant', coach=True)
        refresh = self.sign_in('assistant').data['refresh']
        CoachProfile.objects.filter(user=coach).delete()
        self.assertEqual(self.renew(refresh).status_code, 401)

    def test_a_made_up_token_is_still_just_refused(self):
        self.assertEqual(self.renew('not-a-token').status_code, 401)
