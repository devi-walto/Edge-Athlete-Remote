"""Tests that an online athlete only sees themselves in the room (spec 04).

WHY THESE EXIST: the active-session routes list everyone in the session, because a
gym's rack tablet shows the whole roster to check people in. Online, those same
routes are open to any signed-in athlete, so without this every athlete could read
every other athlete's name, plan, maxes and status. A coach, and a gym tablet with
nobody signed in, must still see everyone.
"""
import json

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Athlete, CoachProfile, TrainingSession

User = get_user_model()
PASSWORD = 'Unique-privacy-2026!safe'
ROUTES = ['/api/sessions/active/', '/api/sessions/active/status/']


class RoomPrivacyTestCase(APITestCase):
    def setUp(self):
        self.session = TrainingSession.objects.create(label='Remote day', started_at=timezone.now())
        self.riley = Athlete.objects.create(
            name='Riley Brooks', user=User.objects.create_user('riley', password=PASSWORD))
        self.jordan = Athlete.objects.create(name='Jordan Lee')
        self.session.athletes.add(self.riley, self.jordan)

    def body(self, url):
        reply = self.client.get(url)
        self.assertEqual(reply.status_code, 200, (url, reply.data))
        return json.dumps(reply.data, default=str)


@override_settings(EA_DEPLOYMENT='remote')
class OnlineAthleteTests(RoomPrivacyTestCase):
    def test_an_athlete_sees_only_themselves(self):
        self.client.force_authenticate(self.riley.user)
        for url in ROUTES:
            body = self.body(url)
            self.assertIn('Riley Brooks', body, url)
            self.assertNotIn('Jordan Lee', body, url)
        roster = self.client.get('/api/sessions/active/').data['roster']
        self.assertEqual([entry['athlete_id'] for entry in roster], [self.riley.pk])

    def test_a_coach_still_sees_everyone(self):
        coach = User.objects.create_user('coach', password=PASSWORD)
        CoachProfile.objects.create(user=coach)
        self.client.force_authenticate(coach)
        for url in ROUTES:
            body = self.body(url)
            self.assertIn('Riley Brooks', body, url)
            self.assertIn('Jordan Lee', body, url)


@override_settings(EA_DEPLOYMENT='local')
class GymTabletTests(RoomPrivacyTestCase):
    def test_a_gym_tablet_still_sees_the_whole_roster(self):
        for url in ROUTES:
            body = self.body(url)
            self.assertIn('Riley Brooks', body, url)
            self.assertIn('Jordan Lee', body, url)
