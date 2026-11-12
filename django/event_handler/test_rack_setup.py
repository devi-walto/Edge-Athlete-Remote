"""Tests for racks that make and name themselves (spec 18, Phase 2).

WHY THESE EXIST: a tablet no longer waits for a coach to give it a numbered slot. It
takes the next free number and a name on "Set up this rack", in a gym with no login
and online with the common login. These pin that each new tablet gets its own rack,
that a name can be changed by the right people and shows everywhere a rack is
printed, that a shared name gets its number added, and that a dead tablet's empty
rack leaves the room without anything being deleted.
"""
import importlib
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (Athlete, CoachProfile, Node, RackCheckIn, RackRuntime, RackScreen,
                     TrainingSession)
from .services.rack_names import labels_by_rack
from .services.room_state import room_state_snapshot
from .test_common_login import TABLET_PASSWORD, make_common

User = get_user_model()
PASSWORD = 'Unique-racks-2026!safe'


def rack_labels():
    return {r['rack_number']: r['label'] for r in room_state_snapshot(include_details=False)['racks']}


@override_settings(EA_DEPLOYMENT='local')
class InAGymTests(APITestCase):
    def mine(self, device, method='get', body=None):
        return getattr(self.client, method)('/api/racks/mine/', body or {}, format='json',
                                            HTTP_X_RACK_DEVICE_ID=device)

    def test_a_tablet_must_say_which_device_it_is(self):
        self.assertEqual(self.client.get('/api/racks/mine/').status_code, 400)

    def test_each_new_tablet_makes_the_next_rack_with_the_next_name(self):
        self.assertEqual(self.mine('tab-a').data, {'rack': None, 'suggested_name': 'Rack 1'})
        first = self.mine('tab-a', 'post')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data['rack'], {'rack_number': 1, 'name': 'Rack 1', 'label': 'Rack 1'})
        second = self.mine('tab-b', 'post', {'name': '  Platform  '})
        self.assertEqual(second.data['rack'], {'rack_number': 2, 'name': 'Platform', 'label': 'Platform'})
        self.assertEqual(self.mine('tab-c').data['suggested_name'], 'Rack 2')

    def test_a_tablet_with_a_rack_gets_the_same_one_back(self):
        made = self.mine('tab-a', 'post').data['rack']
        again = self.mine('tab-a', 'post', {'name': 'Something else'})
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.data['rack'], made)
        self.assertEqual(self.mine('tab-a').data['rack'], made)

    def test_numbers_skip_anything_already_used(self):
        Node.objects.create(node_id='old-bar', rack_number=7)
        self.assertEqual(self.mine('tab-a', 'post').data['rack']['rack_number'], 8)

    def test_a_name_must_be_a_name(self):
        self.assertEqual(self.mine('tab-a', 'post', {'name': 'x' * 41}).status_code, 400)
        self.assertEqual(self.mine('tab-a', 'post', {'name': '   '}).status_code, 400)


@override_settings(EA_DEPLOYMENT='local')
class NamesShowEverywhereTests(APITestCase):
    def setUp(self):
        RackScreen.objects.create(device_id='tab-3', rack_number=3, name='Platform')
        RackScreen.objects.create(device_id='tab-4', rack_number=4, name='Platform')
        RackScreen.objects.create(device_id='tab-5', rack_number=5, name='Squat rack')
        for number in (3, 4, 5):
            Node.objects.create(node_id=f'bar-{number}', rack_number=number)

    def test_a_shared_name_gets_its_number_a_name_of_its_own_does_not(self):
        self.assertEqual(rack_labels(), {3: 'Platform (3)', 4: 'Platform (4)', 5: 'Squat rack'})

    def test_renaming_changes_the_name_everywhere_and_nothing_else(self):
        runtime = RackRuntime.objects.create(rack_number=4)
        response = self.client.patch('/api/racks/4/name/', {'name': 'Bench'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(rack_labels(), {3: 'Platform', 4: 'Bench', 5: 'Squat rack'})
        self.assertEqual(self.client.get('/api/racks/4/state/').data['rack_label'], 'Bench')
        screen = RackScreen.objects.get(rack_number=4)
        self.assertEqual((screen.device_id, screen.rack_number), ('tab-4', 4))
        self.assertEqual(RackRuntime.objects.get(pk=runtime.pk).rack_number, 4)

    def test_a_rack_with_no_name_reads_rack_and_its_number(self):
        self.assertEqual(labels_by_rack([9]), {9: 'Rack 9'})


@override_settings(EA_DEPLOYMENT='local')
class ADeadTabletsEmptyRackTests(TestCase):
    """Silent tablet + no sensor + nobody checked in: the rack leaves the room."""

    def setUp(self):
        RackScreen.objects.create(device_id='dead', rack_number=6, name='Old tablet')

    def test_it_leaves_the_room_and_nothing_is_deleted(self):
        RackRuntime.objects.create(rack_number=6, lease_expires_at=timezone.now() - timedelta(hours=1))
        self.assertNotIn(6, rack_labels())
        self.assertTrue(RackScreen.objects.filter(rack_number=6).exists())

    def test_it_stays_while_its_tablet_is_alive(self):
        RackRuntime.objects.create(rack_number=6, lease_expires_at=timezone.now() + timedelta(seconds=20))
        self.assertIn(6, rack_labels())

    def test_it_stays_with_a_sensor_or_someone_checked_in(self):
        Node.objects.create(node_id='bar-6', rack_number=6)
        self.assertIn(6, rack_labels())
        Node.objects.all().delete()
        session = TrainingSession.objects.create(label='Thursday', started_at=timezone.now())
        athlete = Athlete.objects.create(name='Riley Brooks')
        session.athletes.add(athlete)
        RackCheckIn.objects.create(session=session, athlete=athlete, rack_number=6)
        self.assertIn(6, rack_labels())


@override_settings(EA_DEPLOYMENT='remote')
class OnlineTests(APITestCase):
    def setUp(self):
        self.coach = User.objects.create_user('racks_coach', password=PASSWORD)
        CoachProfile.objects.create(user=self.coach)
        self.athlete = User.objects.create_user('racks_athlete', password=PASSWORD)
        Athlete.objects.create(name='Racks Athlete', user=self.athlete)
        make_common()
        signed_in = self.client.post('/api/auth/login/', {'username': 'gym-screens', 'password': TABLET_PASSWORD,
                                                          'device_id': 'tablet-x'}, format='json')
        self.access = signed_in.data['access']

    def as_tablet(self, method, url, body=None):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')
        response = getattr(self.client, method)(url, body or {}, format='json')
        self.client.credentials()
        return response

    def test_a_tablet_on_the_common_login_makes_its_own_rack(self):
        made = self.as_tablet('post', '/api/racks/mine/', {'name': 'Platform'})
        self.assertEqual(made.status_code, 201)
        self.assertEqual(RackScreen.objects.get(device_id='tablet-x').name, 'Platform')
        self.assertEqual(self.as_tablet('get', '/api/racks/mine/').data['rack']['name'], 'Platform')

    def test_it_renames_its_own_rack_but_no_other(self):
        number = self.as_tablet('post', '/api/racks/mine/').data['rack']['rack_number']
        RackScreen.objects.create(device_id='someone-else', rack_number=number + 1, name='Theirs')
        self.assertEqual(self.as_tablet('patch', f'/api/racks/{number}/name/', {'name': 'Mine'}).status_code, 200)
        self.assertEqual(self.as_tablet('patch', f'/api/racks/{number + 1}/name/', {'name': 'Taken'}).status_code, 403)

    def test_a_coach_renames_any_rack_from_room_layout_an_athlete_none(self):
        RackScreen.objects.create(device_id='tab-2', rack_number=2, name='Rack 2')
        self.client.force_authenticate(user=self.coach)
        self.assertEqual(self.client.patch('/api/racks/2/name/', {'name': 'Bench'}, format='json').status_code, 200)
        self.client.force_authenticate(user=self.athlete)
        self.assertEqual(self.client.patch('/api/racks/2/name/', {'name': 'Mine now'}, format='json').status_code, 403)

    def test_nobody_but_a_tablet_sets_a_rack_up_online(self):
        for user in (self.coach, self.athlete):
            self.client.force_authenticate(user=user)
            self.assertEqual(self.client.post('/api/racks/mine/', {}, format='json').status_code, 403)


class TheMigrationTests(TestCase):
    def test_existing_tablets_are_called_rack_and_their_number(self):
        from django.apps import apps
        migration = importlib.import_module('event_handler.migrations.0031_rack_names')
        RackScreen.objects.create(device_id='old', rack_number=2)
        RackScreen.objects.create(device_id='waiting')
        migration.name_existing_racks(apps, None)
        self.assertEqual(RackScreen.objects.get(device_id='old').name, 'Rack 2')
        self.assertEqual(RackScreen.objects.get(device_id='waiting').name, '')
