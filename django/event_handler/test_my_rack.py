"""Tests for "my rack" (spec 04, Phase 2): an online athlete's own rack is theirs alone.

WHY THESE EXIST: online, every athlete's phone talks to the same server. If athlete A
could drive athlete B's rack, check B in, or post a set for B, one login could rewrite
someone else's training. And an online athlete who reloads the page must get their
rack back with their set still open: nobody else can be at their rack, so there is
nothing to recover from. When the coach ends the session, the racks must go away
without losing a single set.
"""
import datetime
import uuid

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (Athlete, CoachProfile, Exercise, Node, RackRuntime, Set,
                     TrainingSession)
from .services.session_join import join
from .tests import controller_token

User = get_user_model()
PASSWORD = 'Unique-myrack-2026!safe'


def athlete_with_login(name, username):
    return Athlete.objects.create(name=name, user=User.objects.create_user(username, password=PASSWORD))


@override_settings(EA_DEPLOYMENT='remote')
class MyRackTestCase(APITestCase):
    def setUp(self):
        self.session = TrainingSession.objects.create(label='Remote day', started_at=timezone.now())
        self.a = athlete_with_login('Riley Brooks', 'riley')
        self.b = athlete_with_login('Jordan Lee', 'jordan')
        self.session.athletes.add(self.a, self.b)
        self.a_sensor = Node.objects.create(node_id='sim-riley-brooks', owner=self.a)
        self.a_rack, _ = join(self.session.pk, self.a)
        self.b_rack, _ = join(self.session.pk, self.b)
        self.squat = Exercise.objects.get_or_create(name='Back Squat')[0]

    def as_(self, athlete):
        self.client.force_authenticate(athlete.user)

    def acquire(self, rack, tab='tab-1'):
        token = controller_token()
        reply = self.client.post(f'/api/racks/{rack.rack_number}/controller/acquire/', {
            'device_id': f'phone-{tab}', 'client_instance_id': tab, 'controller_token': token,
        }, format='json')
        headers = None
        if reply.status_code == 200:
            headers = {'X-Rack-Device-ID': f'phone-{tab}', 'X-Client-Instance-ID': tab,
                       'X-Controller-Token': token,
                       'X-Controller-Epoch': str(reply.data['controller_epoch'])}
        return reply, headers

    def start_set(self, rack, athlete, headers):
        rack.refresh_from_db()
        return self.client.post('/api/sets/', {
            'session': self.session.pk, 'athlete': athlete.pk, 'node': self.a_sensor.pk,
            'rack_number': rack.rack_number, 'exercise': self.squat.pk, 'set_number': 1,
            'weight_lbs': 225, 'expected_state_version': rack.state_version,
            'command_id': str(uuid.uuid4()),
        }, format='json', headers=headers)


class OnlyYourOwnRackTests(MyRackTestCase):
    def test_your_own_rack_answers_and_someone_elses_refuses(self):
        self.as_(self.a)
        self.assertEqual(self.client.get(f'/api/racks/{self.a_rack.rack_number}/state/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/racks/{self.b_rack.rack_number}/state/').status_code, 403)
        reply, _ = self.acquire(self.b_rack)
        self.assertEqual(reply.status_code, 403)

    def test_you_cannot_check_in_or_post_a_set_for_someone_else(self):
        self.as_(self.a)
        _, headers = self.acquire(self.a_rack)
        reply = self.client.post(f'/api/racks/{self.a_rack.rack_number}/checkin/', {
            'athlete': self.b.pk, 'command_id': str(uuid.uuid4()),
            'expected_state_version': 0}, format='json', headers=headers)
        self.assertEqual(reply.status_code, 403)
        self.assertEqual(self.start_set(self.a_rack, self.b, headers).status_code, 403)
        self.assertFalse(Set.objects.exists())

    def test_you_cannot_finish_someone_elses_set(self):
        theirs = Set.objects.create(session=self.session, athlete=self.b, exercise=self.squat, set_number=1)
        self.as_(self.a)
        reply = self.client.post(f'/api/sets/{theirs.pk}/complete/', {}, format='json')
        self.assertEqual(reply.status_code, 403)


class AnOwnedRackKeepsItsAthleteTests(MyRackTestCase):
    def test_clearing_or_changing_the_lifter_is_refused(self):
        self.as_(self.a)
        _, headers = self.acquire(self.a_rack)
        for lifter in (None, self.b.pk):
            self.a_rack.refresh_from_db()
            reply = self.client.patch(f'/api/racks/{self.a_rack.rack_number}/state/', {
                'phase': 'idle', 'selected_athlete': lifter,
                'expected_state_version': self.a_rack.state_version,
                'command_id': str(uuid.uuid4())}, format='json', headers=headers)
            self.assertEqual((reply.status_code, reply.data.get('code')), (409, 'owned_rack'), lifter)
        self.a_rack.refresh_from_db()
        self.assertEqual(self.a_rack.selected_athlete, self.a)

    def test_a_coach_cannot_take_control_of_an_athletes_rack(self):
        coach = User.objects.create_user('coach', password=PASSWORD)
        CoachProfile.objects.create(user=coach)
        self.client.force_authenticate(coach)
        reply, _ = self.acquire(self.a_rack)
        self.assertEqual((reply.status_code, reply.data['code']), (403, 'owned_rack'))
        self.a_rack.refresh_from_db()
        self.assertEqual(self.a_rack.selected_athlete, self.a)


class AReloadKeepsYourRackTests(MyRackTestCase):
    def test_reloading_mid_set_gets_the_rack_back_with_the_set_still_open(self):
        self.as_(self.a)
        _, first_tab = self.acquire(self.a_rack, 'tab-1')
        started = self.start_set(self.a_rack, self.a, first_tab)
        self.assertEqual(started.status_code, 201, started.data)

        # The page reloads: a new tab, a new token, no recovery prompt.
        reply, second_tab = self.acquire(self.a_rack, 'tab-2')
        self.assertEqual(reply.status_code, 200, reply.data)
        open_set = Set.objects.get(pk=started.data['id'])
        self.assertIsNone(open_set.ended_at)
        self.assertFalse(open_set.is_false_set)
        # The new tab is the controller now; the old one is fenced out.
        self.assertEqual(self.client.post(f'/api/racks/{self.a_rack.rack_number}/controller/heartbeat/',
                                          headers=second_tab).status_code, 200)
        self.assertEqual(self.client.post(f'/api/racks/{self.a_rack.rack_number}/controller/heartbeat/',
                                          headers=first_tab).status_code, 409)

    def test_no_sensor_still_lets_you_take_your_rack(self):
        self.as_(self.b)                     # Jordan has no sensor
        reply, _ = self.acquire(self.b_rack)
        self.assertEqual(reply.status_code, 200, reply.data)


class EndingTheSessionReleasesTheRacksTests(MyRackTestCase):
    def test_racks_go_sensors_are_freed_and_every_set_is_kept(self):
        self.as_(self.a)
        _, headers = self.acquire(self.a_rack)
        open_set_id = self.start_set(self.a_rack, self.a, headers).data['id']
        done = Set.objects.create(session=self.session, athlete=self.b, exercise=self.squat,
                                  set_number=1, ended_at=timezone.now(), reps_completed=5)

        from .services.session_completion import end_session
        report, created = end_session(self.session.pk)

        self.assertTrue(created)
        self.assertFalse(RackRuntime.objects.filter(session=self.session).exists())
        self.a_sensor.refresh_from_db()
        self.assertIsNone(self.a_sensor.rack_number)
        abandoned = Set.objects.get(pk=open_set_id)
        self.assertIsNotNone(abandoned.ended_at)           # ended and kept
        self.assertTrue(abandoned.is_false_set)
        self.assertTrue(Set.objects.filter(pk=done.pk, reps_completed=5).exists())
        self.assertIsNotNone(report)

    def test_a_physical_rack_is_left_alone(self):
        gym = RackRuntime.objects.create(rack_number=1)
        from .services.session_completion import end_session
        end_session(self.session.pk)
        self.assertTrue(RackRuntime.objects.filter(pk=gym.pk).exists())
