"""Tests for athlete_logins.py: the coach's routes for athlete login links.

WHY THESE EXIST: these routes hand out the only copy of a login link, so they must
answer coaches and nobody else, build a link that works on whichever school it was
made on, and never let a secret or its fingerprint leak into the roster.
"""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Athlete, AthleteLoginLink, CoachProfile
from .services import login_links

User = get_user_model()
PASSWORD = 'Unique-logins-2026!safe'


class AthleteLoginRoutesTestCase(APITestCase):
    def setUp(self):
        self.coach = User.objects.create_user('coach', password=PASSWORD)
        CoachProfile.objects.create(user=self.coach)
        self.athlete = Athlete.objects.create(name='Riley Brooks')
        self.link_url = f'/api/athletes/{self.athlete.pk}/login-link/'
        self.login_url = f'/api/athletes/{self.athlete.pk}/login/'

    def as_coach(self):
        self.client.force_authenticate(self.coach)

    def send_link(self, **headers):
        self.as_coach()
        return self.client.post(self.link_url, **headers)


class WhoMayUseThemTests(AthleteLoginRoutesTestCase):
    def routes(self):
        return [('post', self.link_url), ('delete', self.link_url), ('delete', self.login_url)]

    def test_no_login_gets_401(self):
        for method, url in self.routes():
            self.assertEqual(getattr(self.client, method)(url).status_code, 401, (method, url))

    def test_an_athlete_gets_403(self):
        lifter = Athlete.objects.create(name='Jordan Lee')
        lifter.user = login_links.redeem(login_links.issue(lifter, self.coach)[0], 'jordan', PASSWORD)
        self.client.force_authenticate(lifter.user)
        for method, url in self.routes():
            self.assertEqual(getattr(self.client, method)(url).status_code, 403, (method, url))

    def test_an_unknown_athlete_is_404(self):
        self.as_coach()
        self.assertEqual(self.client.post('/api/athletes/999999/login-link/').status_code, 404)


class SendLinkTests(AthleteLoginRoutesTestCase):
    def test_the_reply_carries_a_working_link_after_a_hash(self):
        reply = self.send_link()

        self.assertEqual(reply.status_code, 201)
        address, _, link = reply.data['link'].partition('#')
        self.assertTrue(address.endswith('/login-link'))
        self.assertIsNotNone(login_links.find(link))
        self.assertEqual(reply.data['expires_at'], AthleteLoginLink.objects.get().expires_at)

    @override_settings(ALLOWED_HOSTS=['demo.example.com'],
                       SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
    def test_behind_the_remote_servers_front_door_the_link_is_https_on_the_schools_address(self):
        reply = self.send_link(HTTP_HOST='demo.example.com', HTTP_X_FORWARDED_PROTO='https')
        self.assertTrue(reply.data['link'].startswith('https://demo.example.com/login-link#'))

    def test_an_archived_athlete_is_refused(self):
        self.athlete.is_active = False
        self.athlete.save()
        self.assertEqual(self.send_link().status_code, 409)
        self.assertFalse(AthleteLoginLink.objects.exists())

    def test_cancel_stops_the_link(self):
        link = self.send_link().data['link'].partition('#')[2]
        self.assertEqual(self.client.delete(self.link_url).status_code, 204)
        self.assertIsNone(login_links.find(link))

    def test_remove_login_switches_it_off(self):
        link = self.send_link().data['link'].partition('#')[2]
        login = login_links.redeem(link, 'riley', PASSWORD)

        self.assertEqual(self.client.delete(self.login_url).status_code, 204)

        login.refresh_from_db()
        self.athlete.refresh_from_db()
        self.assertFalse(login.is_active)
        self.assertIsNone(self.athlete.user)


class RosterLoginColumnTests(AthleteLoginRoutesTestCase):
    def roster_row(self):
        self.as_coach()
        rows = self.client.get('/api/athletes/').data
        return next(r for r in rows if r['id'] == self.athlete.pk)

    def test_none_then_link_sent_then_linked(self):
        self.assertEqual(self.roster_row()['login_status'], 'none')

        link = self.send_link().data['link'].partition('#')[2]
        row = self.roster_row()
        self.assertEqual(row['login_status'], 'link_sent')
        self.assertIsNotNone(row['link_expires_at'])

        login_links.redeem(link, 'riley', PASSWORD)
        row = self.roster_row()
        self.assertEqual(row['login_status'], 'linked')
        self.assertEqual(row['login_username'], 'riley')
        self.assertIsNone(row['link_expires_at'])

    def test_a_link_that_ran_out_shows_as_none(self):
        self.send_link()
        AthleteLoginLink.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.roster_row()['login_status'], 'none')

    def test_a_new_link_for_a_linked_athlete_shows_link_sent_and_keeps_the_username(self):
        login_links.redeem(self.send_link().data['link'].partition('#')[2], 'riley', PASSWORD)
        self.send_link()
        row = self.roster_row()
        self.assertEqual(row['login_status'], 'link_sent')
        self.assertEqual(row['login_username'], 'riley')

    def test_the_roster_never_carries_a_secret_or_a_fingerprint(self):
        link = self.send_link().data['link'].partition('#')[2]
        secret = link.split('.', 1)[1]
        self.as_coach()
        body = json.dumps(self.client.get('/api/athletes/').data, default=str)
        self.assertNotIn(secret, body)
        self.assertNotIn(AthleteLoginLink.objects.get().token_hash, body)
        self.assertNotIn('pbkdf2', body)

    def test_the_roster_asks_the_database_the_same_number_of_times_for_1_or_21_athletes(self):
        self.as_coach()
        self.client.get('/api/athletes/')   # warm up anything loaded only once
        with_one = self._queries_for_roster()
        for n in range(20):
            lifter = Athlete.objects.create(name=f'Lifter {n}')
            login_links.issue(lifter, self.coach)
        self.assertEqual(self._queries_for_roster(), with_one)

    def _queries_for_roster(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as captured:
            self.client.get('/api/athletes/')
        return len(captured)
