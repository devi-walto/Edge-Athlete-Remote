"""Tests for joining a session online (spec 04, Phase 1).

WHY THESE EXIST: joining is how an online athlete gets a rack at all. It must let in
exactly the athletes who belong (on the roster, or in a group taking part), give each
one their own rack that nobody else can be given, give the same rack back on a
rejoin, and put only their OWN sensor on it. Fifty athletes joining in the same
second must still get fifty different racks.
"""
import datetime
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .models import (VIRTUAL_RACK_BASE, Athlete, CoachProfile, Node, RackCheckIn, RackRuntime,
                     SessionParticipation, TrainingGroup, TrainingProgram, TrainingSession)

User = get_user_model()
PASSWORD = 'Unique-join-2026!safe'


def athlete_with_login(name, username):
    login = User.objects.create_user(username, password=PASSWORD)
    return Athlete.objects.create(name=name, user=login)


def started_session(label='Remote day'):
    return TrainingSession.objects.create(label=label, started_at=timezone.now())


def take_part(session, group):
    program = TrainingProgram.objects.create(training_group=group, name=f'{group.name} plan',
                                             start_date=datetime.date.today())
    SessionParticipation.objects.create(session=session, training_program=program)


@override_settings(EA_DEPLOYMENT='remote')
class JoinTests(APITestCase):
    def setUp(self):
        self.session = started_session()
        self.group = TrainingGroup.objects.create(name='Varsity')
        take_part(self.session, self.group)
        self.in_group = athlete_with_login('Riley Brooks', 'riley')
        self.in_group.training_groups.add(self.group)
        self.on_roster = athlete_with_login('Jordan Lee', 'jordan')
        self.session.athletes.add(self.on_roster)
        self.outsider = athlete_with_login('Casey Morgan', 'casey')

    def join_as(self, athlete, session=None):
        self.client.force_authenticate(athlete.user if athlete else None)
        return self.client.post(f'/api/sessions/{(session or self.session).pk}/join/')

    def test_an_athlete_in_a_taking_part_group_gets_a_virtual_rack(self):
        reply = self.join_as(self.in_group)
        self.assertEqual(reply.status_code, 200, reply.data)
        self.assertGreaterEqual(reply.data['rack_number'], VIRTUAL_RACK_BASE)
        rack = RackRuntime.objects.get(rack_number=reply.data['rack_number'])
        self.assertEqual(rack.owner_athlete, self.in_group)
        self.assertEqual(rack.session, self.session)
        self.assertEqual(rack.selected_athlete, self.in_group)   # checked in, ready on open
        self.assertTrue(self.session.athletes.filter(pk=self.in_group.pk).exists())
        self.assertIsNone(reply.data['sensor'])

    def test_an_athlete_on_the_roster_gets_a_rack(self):
        self.assertEqual(self.join_as(self.on_roster).status_code, 200)

    def test_joining_twice_gives_the_same_rack_and_no_second_row_or_check_in(self):
        first = self.join_as(self.in_group).data['rack_number']
        second = self.join_as(self.in_group).data['rack_number']
        self.assertEqual(first, second)
        self.assertEqual(RackRuntime.objects.filter(owner_athlete=self.in_group).count(), 1)
        self.assertEqual(RackCheckIn.objects.filter(athlete=self.in_group).count(), 1)

    def test_two_athletes_get_different_racks(self):
        a = self.join_as(self.in_group).data['rack_number']
        b = self.join_as(self.on_roster).data['rack_number']
        self.assertNotEqual(a, b)

    def test_in_two_taking_part_groups_still_one_rack(self):
        other = TrainingGroup.objects.create(name='Speed')
        take_part(self.session, other)
        self.in_group.training_groups.add(other)
        self.join_as(self.in_group)
        self.assertEqual(RackRuntime.objects.filter(owner_athlete=self.in_group).count(), 1)

    def test_who_is_turned_away(self):
        reply = self.join_as(self.outsider)
        self.assertEqual((reply.status_code, reply.data['code']), (403, 'not_in_session'))
        coach = User.objects.create_user('coach', password=PASSWORD)
        CoachProfile.objects.create(user=coach)
        self.client.force_authenticate(coach)
        self.assertEqual(self.client.post(f'/api/sessions/{self.session.pk}/join/').status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(f'/api/sessions/{self.session.pk}/join/').status_code, 401)
        self.assertFalse(RackRuntime.objects.exists())

    def test_an_archived_athlete_is_turned_away(self):
        self.in_group.is_active = False
        self.in_group.save()
        self.in_group.user.is_active = True   # even with a login that still works
        self.in_group.user.save()
        self.assertEqual(self.join_as(self.in_group).status_code, 403)

    def test_a_session_not_started_or_ended_refuses(self):
        waiting = TrainingSession.objects.create(label='Later')
        waiting.athletes.add(self.on_roster)
        reply = self.join_as(self.on_roster, waiting)
        self.assertEqual((reply.status_code, reply.data['code']), (409, 'not_started'))

        self.session.ended_at = timezone.now()
        self.session.save()
        reply = self.join_as(self.on_roster)
        self.assertEqual((reply.status_code, reply.data['code']), (409, 'ended'))
        self.assertFalse(RackRuntime.objects.exists())

    def test_an_unknown_session_is_404(self):
        self.client.force_authenticate(self.on_roster.user)
        self.assertEqual(self.client.post('/api/sessions/999999/join/').status_code, 404)

    def test_their_own_sensor_goes_on_their_rack(self):
        mine = Node.objects.create(node_id='sim-riley-brooks', owner=self.in_group)
        reply = self.join_as(self.in_group)
        mine.refresh_from_db()
        self.assertEqual(mine.rack_number, reply.data['rack_number'])
        self.assertEqual(reply.data['sensor']['node_id'], 'sim-riley-brooks')

    def test_someone_elses_sensor_never_goes_on_their_rack(self):
        jordans = Node.objects.create(node_id='sim-jordan-lee', owner=self.on_roster)
        gym = Node.objects.create(node_id='rack-1-sensor', rack_number=1)
        reply = self.join_as(self.in_group)
        jordans.refresh_from_db()
        gym.refresh_from_db()
        self.assertIsNone(reply.data['sensor'])
        self.assertIsNone(jordans.rack_number)
        self.assertEqual(gym.rack_number, 1)

    def test_a_switched_off_sensor_is_not_used(self):
        Node.objects.create(node_id='sim-riley-old', owner=self.in_group, is_active=False)
        self.assertIsNone(self.join_as(self.in_group).data['sensor'])

    def test_the_most_recently_seen_sensor_is_used(self):
        Node.objects.create(node_id='sim-riley-never', owner=self.in_group)
        Node.objects.create(node_id='sim-riley-recent', owner=self.in_group, last_seen=timezone.now())
        self.assertEqual(self.join_as(self.in_group).data['sensor']['node_id'], 'sim-riley-recent')


@override_settings(EA_DEPLOYMENT='local')
class LocalInstallTests(APITestCase):
    def test_a_local_install_has_no_join(self):
        session = started_session()
        athlete = athlete_with_login('Riley Brooks', 'riley')
        session.athletes.add(athlete)
        self.client.force_authenticate(athlete.user)
        self.assertEqual(self.client.post(f'/api/sessions/{session.pk}/join/').status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(f'/api/sessions/{session.pk}/join/').status_code, 404)


@override_settings(EA_DEPLOYMENT='remote')
class FiftyAtOnceTests(TransactionTestCase):
    reset_sequences = True

    def test_fifty_athletes_joining_at_once_get_fifty_different_racks(self):
        session = started_session()
        athletes = [athlete_with_login(f'Lifter {n}', f'lifter{n}') for n in range(50)]
        session.athletes.add(*athletes)

        def join(athlete):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(athlete.user)
                reply = client.post(f'/api/sessions/{session.pk}/join/')
                return reply.status_code, reply.data.get('rack_number')
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(join, athletes))

        self.assertEqual({status for status, _ in results}, {200})
        numbers = [number for _, number in results]
        self.assertEqual(len(set(numbers)), 50)
        self.assertEqual(sorted(numbers), list(range(VIRTUAL_RACK_BASE, VIRTUAL_RACK_BASE + 50)))
        self.assertEqual(RackRuntime.objects.count(), 50)
