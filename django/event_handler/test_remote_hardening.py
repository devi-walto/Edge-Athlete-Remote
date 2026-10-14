"""Tests for the safety checks only a REMOTE installation needs (spec 05, Phase 3).

WHY THESE EXIST: on the internet, a line left out of the configuration can turn on
debug pages for strangers or let anyone try passwords as fast as they like. A remote
installation must refuse to start without the settings that prevent that, must know
that a request was HTTPS even though the cluster's front door handed it on as plain
HTTP, and must slow down whoever keeps getting a password wrong. A local installation
(a gym box) is on its own Wi-Fi over plain HTTP, and none of this may change it.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from basestation_config.deployment_mode import remote_settings

from .coach_auth import FAILED_ATTEMPT_LIMIT, issue_setup_code
from .models import CoachProfile

User = get_user_model()
PASSWORD = 'Unique-remote-2026!safe'


class RemoteStartupRulesTests(SimpleTestCase):
    def test_debug_on_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            remote_settings(debug=True, allowed_hosts_raw='team.example.com', csrf_origins_raw='')
        self.assertIn('DEBUG', str(caught.exception))

    def test_no_web_address_refuses_to_start(self):
        for empty in (None, '', ' , '):
            with self.subTest(empty), self.assertRaises(ImproperlyConfigured) as caught:
                remote_settings(debug=False, allowed_hosts_raw=empty, csrf_origins_raw='')
            self.assertIn('ALLOWED_HOSTS', str(caught.exception))

    def test_trusted_origins_default_to_https_on_each_address(self):
        hosts, origins = remote_settings(debug=False, csrf_origins_raw='',
                                         allowed_hosts_raw='team.example.com, demo.example.com')
        self.assertEqual(hosts, ['team.example.com', 'demo.example.com'])
        self.assertEqual(origins, ['https://team.example.com', 'https://demo.example.com'])

    def test_trusted_origins_can_be_named_on_purpose(self):
        _, origins = remote_settings(debug=False, allowed_hosts_raw='team.example.com',
                                     csrf_origins_raw='https://other.example.com')
        self.assertEqual(origins, ['https://other.example.com'])


class SettingsMatchTheModeTests(SimpleTestCase):
    """CI runs the suite once as local and once as remote, so this checks the real
    settings module both ways."""

    def test_https_settings_are_on_only_when_remote(self):
        remote = settings.EA_DEPLOYMENT == 'remote'
        self.assertEqual(getattr(settings, 'SECURE_PROXY_SSL_HEADER', None) is not None, remote)
        self.assertEqual(settings.SESSION_COOKIE_SECURE, remote)
        self.assertEqual(settings.CSRF_COOKIE_SECURE, remote)
        if remote:
            self.assertFalse(settings.DEBUG)

    @override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
    def test_a_request_the_front_door_marks_https_is_treated_as_https(self):
        request = RequestFactory().get('/', HTTP_X_FORWARDED_PROTO='https')
        self.assertTrue(request.is_secure())
        self.assertFalse(RequestFactory().get('/').is_secure())


class WrongAttemptLimitTests(APITestCase):
    def setUp(self):
        cache.clear()
        # the counts live in the cache; leave none behind for the next test class
        self.addCleanup(cache.clear)
        self.coach = User.objects.create_user('limit_coach', password=PASSWORD)
        CoachProfile.objects.create(user=self.coach)

    def sign_in(self, password, address='203.0.113.7'):
        return self.client.post('/api/auth/login/', {'username': 'limit_coach', 'password': password},
                                format='json', HTTP_X_FORWARDED_FOR=address)

    @override_settings(EA_DEPLOYMENT='remote')
    def test_remote_turns_an_address_away_after_too_many_wrong_passwords(self):
        for _ in range(FAILED_ATTEMPT_LIMIT):
            self.assertEqual(self.sign_in('wrong').status_code, 401)
        blocked = self.sign_in('wrong')
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.data['code'], 'too_many_attempts')
        # even the right password waits out the minute
        self.assertEqual(self.sign_in(PASSWORD).status_code, 429)

    @override_settings(EA_DEPLOYMENT='remote')
    def test_correct_sign_ins_never_count(self):
        for _ in range(FAILED_ATTEMPT_LIMIT + 5):
            self.assertEqual(self.sign_in(PASSWORD).status_code, 200)

    @override_settings(EA_DEPLOYMENT='remote')
    def test_each_address_is_counted_on_its_own(self):
        for _ in range(FAILED_ATTEMPT_LIMIT):
            self.sign_in('wrong', address='203.0.113.7')
        self.assertEqual(self.sign_in('wrong', address='203.0.113.7').status_code, 429)
        self.assertEqual(self.sign_in(PASSWORD, address='198.51.100.9').status_code, 200)

    @override_settings(EA_DEPLOYMENT='local')
    def test_local_has_no_limit_here(self):
        for _ in range(FAILED_ATTEMPT_LIMIT + 5):
            self.assertEqual(self.sign_in('wrong').status_code, 401)

    @override_settings(EA_DEPLOYMENT='remote')
    def test_wrong_setup_codes_are_limited_too(self):
        User.objects.all().delete()
        issue_setup_code()
        body = {'setup_code': 'WRONGWRONG', 'username': 'first', 'password': PASSWORD,
                'password_confirm': PASSWORD}
        for _ in range(FAILED_ATTEMPT_LIMIT):
            self.assertEqual(self.client.post('/api/auth/setup/', body, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/auth/setup/', body, format='json').status_code, 429)
