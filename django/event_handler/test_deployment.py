"""Tests for the setting that says "gym box" or "hosted", and the route that reports it.

WHY THESE EXIST: everything that will differ between a gym and the internet hangs
off this one answer. If a typo could quietly turn a hosted installation into a
"local" one, it would be open to the world; so a wrong value has to stop the app.
And the gym box is the default: an installation that says nothing is a gym box.
"""
import os
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APITestCase

from basestation_config.deployment_mode import parse_deployment

from .deployment import deployment, is_hosted


class ReadingTheSettingTests(SimpleTestCase):
    def test_saying_nothing_means_a_gym_box(self):
        for unset in (None, '', '   '):
            self.assertEqual(parse_deployment(unset), 'local')

    def test_the_two_real_values(self):
        self.assertEqual(parse_deployment('local'), 'local')
        self.assertEqual(parse_deployment('remote'), 'remote')

    def test_capitals_and_stray_spaces_are_forgiven(self):
        self.assertEqual(parse_deployment(' Remote\n'), 'remote')

    def test_anything_else_refuses_to_start_and_says_what_is_allowed(self):
        for wrong in ('cloud', 'hosted', 'true', 'remot', 'local,remote'):
            with self.subTest(wrong), self.assertRaises(ImproperlyConfigured) as caught:
                parse_deployment(wrong)
            self.assertIn('local, remote', str(caught.exception))
            self.assertIn(wrong, str(caught.exception))


class AskingTheAppTests(SimpleTestCase):
    def test_a_gym_box_is_not_hosted(self):
        with override_settings(EA_DEPLOYMENT='local'):
            self.assertEqual(deployment(), 'local')
            self.assertFalse(is_hosted())

    def test_a_remote_installation_is_hosted(self):
        with override_settings(EA_DEPLOYMENT='remote'):
            self.assertTrue(is_hosted())


class SystemInfoRouteTests(APITestCase):
    def test_it_answers_with_no_login_in_both_kinds(self):
        for mode in ('local', 'remote'):
            with self.subTest(mode), override_settings(EA_DEPLOYMENT=mode):
                res = self.client.get('/api/system/info/')
                self.assertEqual(res.status_code, 200)
                self.assertEqual(res.data['deployment'], mode)

    def test_it_says_nothing_else_about_the_installation(self):
        self.assertEqual(set(self.client.get('/api/system/info/').data), {'deployment', 'version', 'name'})

    def test_the_name_comes_from_the_school_setting_and_is_null_without_one(self):
        with mock.patch.dict(os.environ, {'EA_INSTALLATION_NAME': '  Demo U '}):
            self.assertEqual(self.client.get('/api/system/info/').data['name'], 'Demo U')
        with mock.patch.dict(os.environ, {'EA_INSTALLATION_NAME': ''}):
            self.assertIsNone(self.client.get('/api/system/info/').data['name'])

    def test_the_build_label_comes_from_the_release_and_defaults_to_dev(self):
        with mock.patch.dict(os.environ, {'EA_VERSION': 'v0.4.0'}):
            self.assertEqual(self.client.get('/api/system/info/').data['version'], 'v0.4.0')
        with mock.patch.dict(os.environ, {'EA_VERSION': ''}):
            self.assertEqual(self.client.get('/api/system/info/').data['version'], 'dev')
