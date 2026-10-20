"""Tests for adding and removing an athlete's own sensor (spec 14, Phase 2).

WHY THESE EXIST: claiming is how a sensor at home gets in at all. A code must work
once, for its own athlete only; every failure must look the same and be slowed down;
a sensor someone else owns must never change hands; and if the broker can't be told,
nothing may be half-done. Removing must shut the sensor out and keep its sets.

Most tests stand in for the broker (sensor_logins is replaced by a recorder). The last
class uses the real broker's sensors door when CI's remote run provides one.
"""
import datetime
from unittest import mock, skipUnless

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .coach_auth import FAILED_ATTEMPT_LIMIT
from .models import (Athlete, CoachProfile, Exercise, Node, SensorClaimCode, Set,
                     TrainingSession)
from .services import sensor_logins

User = get_user_model()
PASSWORD = 'Unique-sensor-2026!safe'


def athlete_with_login(name, username):
    return Athlete.objects.create(name=name, user=User.objects.create_user(username, password=PASSWORD))


@override_settings(EA_DEPLOYMENT='remote')
class ClaimTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.riley = athlete_with_login('Riley Brooks', 'riley')
        self.jordan = athlete_with_login('Jordan Lee', 'jordan')
        self.broker = mock.patch.multiple(sensor_logins, add=mock.DEFAULT, remove=mock.DEFAULT)
        self.door = self.broker.start()
        self.addCleanup(self.broker.stop)

    def code_for(self, athlete):
        self.client.force_authenticate(athlete.user)
        reply = self.client.post('/api/athlete/sensor-code/')
        self.client.force_authenticate(None)
        self.assertEqual(reply.status_code, 201, reply.data)
        return reply.data['code']

    def claim(self, code, node_id='ea-3f9c'):
        return self.client.post('/api/sensors/claim/', {'code': code, 'node_id': node_id},
                                format='json')


class CodeTests(ClaimTestCase):
    def test_an_athlete_gets_a_code_for_15_minutes(self):
        self.client.force_authenticate(self.riley.user)
        reply = self.client.post('/api/athlete/sensor-code/')
        self.assertEqual(reply.status_code, 201)
        self.assertRegex(reply.data['code'], r'^[A-Z2-9]{4}-[A-Z2-9]{4}$')
        left = reply.data['expires_at'] - timezone.now()
        self.assertTrue(datetime.timedelta(minutes=14) < left <= datetime.timedelta(minutes=15))
        self.assertEqual(reply['Cache-Control'], 'no-store')

    def test_only_an_athlete_gets_one(self):
        coach = User.objects.create_user('coach', password=PASSWORD)
        CoachProfile.objects.create(user=coach)
        self.client.force_authenticate(coach)
        self.assertEqual(self.client.post('/api/athlete/sensor-code/').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/athlete/sensor-code/').status_code, 401)


class ClaimTests(ClaimTestCase):
    def test_a_code_claims_a_sensor(self):
        reply = self.claim(self.code_for(self.riley))
        self.assertEqual(reply.status_code, 201, reply.data)
        self.assertEqual((reply.data['username'], reply.data['path']), ('ea-3f9c', '/sensors'))
        self.assertGreaterEqual(len(reply.data['token']), 40)
        sensor = Node.objects.get(node_id='ea-3f9c')
        self.assertEqual(sensor.owner, self.riley)
        self.assertTrue(sensor.is_active)
        self.door['add'].assert_called_once_with('ea-3f9c', reply.data['token'])
        self.assertEqual(reply['Cache-Control'], 'no-store')

    def test_every_code_that_doesnt_work_gets_the_same_answer(self):
        used = self.code_for(self.riley)
        self.claim(used)
        expired = self.code_for(self.jordan)
        SensorClaimCode.objects.filter(athlete=self.jordan).update(
            expires_at=timezone.now() - datetime.timedelta(seconds=1))
        cancelled = self.code_for(Athlete.objects.create(name='Casey Morgan',
                                  user=User.objects.create_user('casey', password=PASSWORD)))
        self.code_for(Athlete.objects.get(name='Casey Morgan'))        # cancels the first
        answers = set()
        for code in (used, expired, cancelled, 'ZZZZ-ZZZZ', '', None):
            reply = self.claim(code, 'ea-other')
            answers.add((reply.status_code, reply.data['code'], reply.data['detail']))
        self.assertEqual(len(answers), 1, answers)
        self.assertEqual(answers.pop()[:2], (400, 'code_does_not_work'))
        self.assertFalse(Node.objects.filter(node_id='ea-other').exists())

    def test_wrong_codes_are_slowed_down(self):
        for _ in range(FAILED_ATTEMPT_LIMIT):
            self.claim('ZZZZ-ZZZZ')
        self.assertEqual(self.claim(self.code_for(self.riley)).status_code, 429)

    def test_claiming_again_replaces_the_token(self):
        first = self.claim(self.code_for(self.riley)).data['token']
        second = self.claim(self.code_for(self.riley)).data['token']
        self.assertNotEqual(first, second)
        self.assertEqual(self.door['add'].call_args_list[-1].args, ('ea-3f9c', second))

    def test_a_sensor_someone_else_owns_is_refused(self):
        Node.objects.create(node_id='ea-3f9c', owner=self.jordan)
        code = self.code_for(self.riley)
        reply = self.claim(code)
        self.assertEqual((reply.status_code, reply.data['code']), (409, 'owned_by_someone_else'))
        self.assertEqual(Node.objects.get(node_id='ea-3f9c').owner, self.jordan)
        self.door['add'].assert_not_called()
        self.assertEqual(self.claim(code, 'ea-mine').status_code, 201)   # the code still works

    def test_if_the_broker_cant_be_told_nothing_changes(self):
        self.door['add'].side_effect = sensor_logins.SensorDoorError('down')
        code = self.code_for(self.riley)
        reply = self.claim(code)
        self.assertEqual((reply.status_code, reply.data['code']), (503, 'sensors_door_unavailable'))
        self.assertFalse(Node.objects.filter(node_id='ea-3f9c').exists())
        self.door['add'].side_effect = None
        self.assertEqual(self.claim(code).status_code, 201)              # the code still works

    def test_an_unusable_sensor_id_is_refused(self):
        code = self.code_for(self.riley)
        for bad in ('a/b', 'x+', '', 'x' * 65):
            self.assertEqual(self.claim(code, bad).data['code'], 'bad_sensor_id')
        self.assertEqual(self.claim(code).status_code, 201)

    def test_an_archived_athletes_code_stops_working(self):
        code = self.code_for(self.riley)
        self.riley.is_active = False
        self.riley.save()
        self.assertEqual(self.claim(code).data['code'], 'code_does_not_work')


class RemoveTests(ClaimTestCase):
    def setUp(self):
        super().setUp()
        self.claim(self.code_for(self.riley))
        self.sensor = Node.objects.get(node_id='ea-3f9c')
        self.sensor.rack_number = 10000
        self.sensor.save()
        session = TrainingSession.objects.create(label='Remote day', started_at=timezone.now())
        exercise = Exercise.objects.create(name='Back squat')
        self.set = Set.objects.create(session=session, athlete=self.riley, node=self.sensor,
                                      exercise=exercise, set_number=1)

    def test_an_athlete_removes_their_sensor_and_its_sets_stay(self):
        self.client.force_authenticate(self.riley.user)
        self.assertEqual(self.client.get('/api/athlete/sensors/').data['sensors'][0]['node_id'],
                         'ea-3f9c')
        self.assertEqual(self.client.delete('/api/athlete/sensors/ea-3f9c/').status_code, 204)
        self.sensor.refresh_from_db()
        self.assertEqual((self.sensor.owner, self.sensor.rack_number), (None, None))
        self.door['remove'].assert_called_once_with('ea-3f9c')
        self.set.refresh_from_db()
        self.assertEqual(self.set.node, self.sensor)
        self.assertEqual(self.client.get('/api/athlete/sensors/').data['sensors'], [])

    def test_a_removed_sensor_can_be_claimed_with_a_fresh_code(self):
        self.client.force_authenticate(self.riley.user)
        self.client.delete('/api/athlete/sensors/ea-3f9c/')
        self.assertEqual(self.claim(self.code_for(self.jordan)).status_code, 201)
        self.assertEqual(Node.objects.get(node_id='ea-3f9c').owner, self.jordan)

    def test_an_athlete_cannot_remove_someone_elses(self):
        self.client.force_authenticate(self.jordan.user)
        self.assertEqual(self.client.delete('/api/athlete/sensors/ea-3f9c/').status_code, 404)
        self.door['remove'].assert_not_called()

    def test_a_coach_removes_an_athletes_lost_sensor(self):
        coach = User.objects.create_user('coach', password=PASSWORD)
        CoachProfile.objects.create(user=coach)
        self.client.force_authenticate(coach)
        url = f'/api/athletes/{self.riley.pk}/sensors/ea-3f9c/'
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertIsNone(Node.objects.get(node_id='ea-3f9c').owner)
        self.client.force_authenticate(self.jordan.user)
        self.assertEqual(self.client.delete(url).status_code, 403)

    def test_if_the_broker_cant_be_told_the_sensor_is_kept(self):
        self.door['remove'].side_effect = sensor_logins.SensorDoorError('down')
        self.client.force_authenticate(self.riley.user)
        self.assertEqual(self.client.delete('/api/athlete/sensors/ea-3f9c/').status_code, 503)
        self.assertEqual(Node.objects.get(node_id='ea-3f9c').owner, self.riley)


@override_settings(EA_DEPLOYMENT='local')
class LocalInstallTests(APITestCase):
    def test_a_local_install_has_none_of_it(self):
        athlete = athlete_with_login('Riley Brooks', 'riley')
        self.client.force_authenticate(athlete.user)
        self.assertEqual(self.client.post('/api/athlete/sensor-code/').status_code, 404)
        self.assertEqual(self.client.get('/api/athlete/sensors/').status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/sensors/claim/', {'code': 'ABCD-EFGH',
                                          'node_id': 'ea-1'}).status_code, 404)


@skipUnless(settings.MQTT_SENSORS_ADMIN_PASSWORD, "needs a broker with the sensors door (CI's remote run)")
@override_settings(EA_DEPLOYMENT='remote')
class RealBrokerTests(APITestCase):
    def test_the_token_works_on_the_sensors_door_until_removed(self):
        from .test_sensor_logins import sensor
        cache.clear()
        riley = athlete_with_login('Riley Brooks', 'riley')
        self.client.force_authenticate(riley.user)
        code = self.client.post('/api/athlete/sensor-code/').data['code']
        self.client.force_authenticate(None)
        login = self.client.post('/api/sensors/claim/', {'code': code, 'node_id': 'ci-claim-check'},
                                 format='json').data
        try:
            client, rc, _ = sensor(login['username'], login['token'])
            self.assertEqual(rc, 0)
            client.disconnect()
            client.loop_stop()
            self.client.force_authenticate(riley.user)
            self.assertEqual(self.client.delete('/api/athlete/sensors/ci-claim-check/').status_code, 204)
            client, rc, _ = sensor(login['username'], login['token'])
            self.assertNotEqual(rc, 0)
            client.loop_stop()
        finally:
            sensor_logins.remove('ci-claim-check')
