"""Tests for the athlete's side of login links: looking a link up, and using it.

WHY THESE EXIST: these two routes are open to anyone on the internet, because the
person opening a link has no login yet. So they must say nothing beyond the one
athlete's name, give the same answer for every kind of bad link, slow down
guessing, keep a link usable when the person only mistyped, and sign the athlete
in for 30 days (a coach keeps 7).
"""
import json
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Athlete, AthleteLoginLink, CoachProfile
from .services import login_links

User = get_user_model()
PASSWORD = 'Unique-redeem-2026!safe'
LOOKUP = '/api/auth/login-link/lookup/'
REDEEM = '/api/auth/login-link/redeem/'
SIGN_IN = '/api/auth/login/'
RENEW = '/api/auth/refresh/'


def days_left(refresh_text):
    exp = RefreshToken(refresh_text)['exp']
    return (exp - timezone.now().timestamp()) / 86400


class LoginLinkRoutesTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.coach = User.objects.create_user('coach', password=PASSWORD)
        CoachProfile.objects.create(user=self.coach)
        self.athlete = Athlete.objects.create(name='Riley Brooks')
        Athlete.objects.create(name='Jordan Lee')   # someone whose name must never show
        self.link = login_links.issue(self.athlete, self.coach)[0]

    def redeem(self, username='riley', password=PASSWORD, link=None):
        return self.client.post(REDEEM, {'link': link or self.link, 'username': username,
                                         'password': password}, format='json')


class LookupTests(LoginLinkRoutesTestCase):
    def test_a_good_link_gives_only_that_athletes_name(self):
        reply = self.client.post(LOOKUP, {'link': self.link}, format='json')
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(reply.data, {'athlete_name': 'Riley Brooks'})
        self.assertEqual(reply['Cache-Control'], 'no-store')

    def test_every_bad_link_gets_the_same_404(self):
        lookup, secret = self.link.split('.', 1)
        expired = Athlete.objects.create(name='Casey Morgan')
        expired_link = login_links.issue(expired, self.coach)[0]
        AthleteLoginLink.objects.filter(athlete=expired).update(
            expires_at=timezone.now() - timedelta(seconds=1))
        bodies = set()
        for bad in [f'{lookup}.wrong', f'nosuchlookup.{secret}', '', 'nonsense', expired_link]:
            reply = self.client.post(LOOKUP, {'link': bad}, format='json')
            self.assertEqual(reply.status_code, 404, bad)
            bodies.add(json.dumps(reply.data, sort_keys=True))
        self.assertEqual(len(bodies), 1)


class RedeemTests(LoginLinkRoutesTestCase):
    def test_using_a_link_makes_the_login_and_signs_in(self):
        reply = self.redeem()

        self.assertEqual(reply.status_code, 201)
        self.assertEqual(reply.data['role'], 'athlete')
        self.assertEqual(reply.data['athlete_name'], 'Riley Brooks')
        self.assertIn('access', reply.data)
        self.athlete.refresh_from_db()
        self.assertEqual(self.athlete.user.username, 'riley')

    def test_the_link_works_only_once(self):
        self.assertEqual(self.redeem().status_code, 201)
        self.assertEqual(self.redeem(username='riley2').status_code, 404)

    def test_a_weak_password_is_refused_and_the_link_still_works(self):
        reply = self.redeem(password='password')
        self.assertEqual(reply.status_code, 400)
        self.assertIn('password', reply.data['fields'])
        self.assertIsNotNone(login_links.find(self.link))
        self.assertEqual(self.redeem().status_code, 201)

    def test_a_taken_username_is_refused_whatever_its_capitals(self):
        reply = self.redeem(username='COACH')
        self.assertEqual(reply.status_code, 400)
        self.assertIn('username', reply.data['fields'])
        self.assertIsNotNone(login_links.find(self.link))

    def test_a_missing_username_or_password_is_refused(self):
        self.assertEqual(self.redeem(username='').status_code, 400)
        self.assertEqual(self.redeem(password='').status_code, 400)
        self.assertIsNotNone(login_links.find(self.link))

    def test_no_reply_names_another_athlete(self):
        replies = [self.client.post(LOOKUP, {'link': self.link}, format='json'),
                   self.redeem(password='password'), self.redeem(),
                   self.client.post(LOOKUP, {'link': self.link}, format='json')]
        for reply in replies:
            self.assertNotIn('Jordan Lee', json.dumps(reply.data, default=str))


class SignInLengthTests(LoginLinkRoutesTestCase):
    def test_an_athlete_stays_signed_in_30_days_from_the_link_sign_in_and_renewal(self):
        self.assertAlmostEqual(days_left(self.redeem().data['refresh']), 30, delta=0.1)

        signed_in = self.client.post(SIGN_IN, {'username': 'riley', 'password': PASSWORD},
                                     format='json')
        self.assertEqual(signed_in.status_code, 200)
        self.assertAlmostEqual(days_left(signed_in.data['refresh']), 30, delta=0.1)

        renewed = self.client.post(RENEW, {'refresh': signed_in.data['refresh']}, format='json')
        self.assertEqual(renewed.status_code, 200)
        self.assertAlmostEqual(days_left(renewed.data['refresh']), 30, delta=0.1)

    def test_a_coach_keeps_7_days(self):
        signed_in = self.client.post(SIGN_IN, {'username': 'coach', 'password': PASSWORD},
                                     format='json')
        self.assertAlmostEqual(days_left(signed_in.data['refresh']), 7, delta=0.1)
        renewed = self.client.post(RENEW, {'refresh': signed_in.data['refresh']}, format='json')
        self.assertAlmostEqual(days_left(renewed.data['refresh']), 7, delta=0.1)


@mock.patch('event_handler.coach_auth.is_hosted', return_value=True)
class GuessingIsSlowedDownTests(LoginLinkRoutesTestCase):
    def test_repeated_bad_lookups_get_429(self, _hosted):
        codes = [self.client.post(LOOKUP, {'link': f'guess{n}.x'}, format='json').status_code
                 for n in range(12)]
        self.assertEqual(codes[:10], [404] * 10)
        self.assertEqual(codes[10:], [429, 429])

    def test_bad_redeems_count_too(self, _hosted):
        for n in range(10):
            self.redeem(link=f'guess{n}.x')
        self.assertEqual(self.redeem().status_code, 429)
