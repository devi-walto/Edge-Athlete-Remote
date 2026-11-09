"""Tests for demo data (spec 04, Phase 5): a seeder safe to run on a real school's
server, and a simulator that wakes the demo athletes' own sensors and tidies up.

WHY THESE EXIST: the seeder now runs online, on a server where real schools keep real
data. It must only ever add, recognise its own rows by label rather than by name, never
make a login, never end a session it didn't make, and refuse rather than mix demo data
into a real athlete. The simulator must stop itself and leave no "live" sensor behind.
"""
import os
import threading
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from .management.commands.seed_active_session import (ATHLETES, BLOCK_NAME, GROUP_NAME,
                                                       GUEST_ATHLETES, LOGIN_ATHLETES,
                                                       MANUAL_ATHLETE, demo_login, NFC_TAG_BY_ATHLETE,
                                                       NODE_ID, SESSION_LABEL, sensor_id)
from .models import (Athlete, AthleteReferenceMax, CoachProfile, Node, RackRuntime, Set,
                     TrainingBlock, TrainingGroup, TrainingSession)
from .services.room_state import room_state_snapshot
from .services.session_join import join

User = get_user_model()
PASSWORD = 'Unique-demo-2026!safe'


def make_admin():
    admin = User.objects.create_user('head', password=PASSWORD, is_staff=True)
    CoachProfile.objects.create(user=admin)
    return admin


def seed(*args):
    call_command('seed_active_session', *args, stdout=StringIO())


class SeederRefusesTests(TestCase):
    def test_no_coach_yet_writes_nothing_and_makes_no_login(self):
        with self.assertRaisesMessage(CommandError, 'Claim it first'):
            seed()
        self.assertFalse(User.objects.exists())
        self.assertFalse(Athlete.objects.exists())
        self.assertFalse(TrainingSession.objects.exists())

    def test_another_session_running_is_left_alone(self):
        make_admin()
        real = TrainingSession.objects.create(label='Real practice', started_at=timezone.now())
        with self.assertRaisesMessage(CommandError, 'End it first'):
            seed()
        real.refresh_from_db()
        self.assertIsNone(real.ended_at)
        self.assertFalse(Athlete.objects.exists())

    def test_a_real_athlete_with_a_demo_name_is_never_mixed_in(self):
        make_admin()
        Athlete.objects.create(name='Jordan Lee')
        with self.assertRaisesMessage(CommandError, 'Jordan Lee'):
            seed()
        self.assertEqual(Athlete.objects.count(), 1)
        self.assertFalse(TrainingSession.objects.exists())


class SeederAddsTests(TestCase):
    def setUp(self):
        self.admin = make_admin()

    def test_it_builds_the_demo_school(self):
        seed()
        demo = Athlete.objects.filter(name__in=ATHLETES)
        self.assertEqual(demo.count(), 4)
        self.assertTrue(all(a.is_simulated for a in demo))
        for athlete in demo:
            sensors = Node.objects.filter(owner=athlete)
            if athlete.name == MANUAL_ATHLETE:          # the hands-on athlete: none
                self.assertFalse(sensors.exists())
                continue
            self.assertEqual([n.node_id for n in sensors], [sensor_id(athlete.name)])
            self.assertTrue(sensors.get().is_simulated)
        session = TrainingSession.objects.get(label=SESSION_LABEL)
        self.assertIsNone(session.ended_at)
        self.assertEqual(TrainingBlock.objects.get(name=BLOCK_NAME).coach, self.admin)
        self.assertEqual(User.objects.count(), 1)          # no login was made

    def test_the_hands_on_athlete_loses_a_simulated_sensor_but_keeps_a_real_one(self):
        jordan = Athlete.objects.create(name=MANUAL_ATHLETE, is_simulated=True)
        Node.objects.create(node_id=sensor_id(MANUAL_ATHLETE), owner=jordan, is_simulated=True)
        Node.objects.create(node_id='ea-169a84', owner=jordan)                # a real sensor
        seed()
        self.assertEqual(list(Node.objects.filter(owner=jordan).values_list('node_id', flat=True)),
                         ['ea-169a84'])

    def test_an_existing_sim_sensor_of_the_athlete_is_adopted(self):
        riley = Athlete.objects.create(name='Riley Brooks', is_simulated=True)
        Node.objects.create(node_id='sim-riley-brooks', owner=riley)          # no label yet
        seed()
        self.assertTrue(Node.objects.get(node_id='sim-riley-brooks').is_simulated)

    def test_a_sim_named_sensor_someone_else_owns_is_left_alone(self):
        real = Athlete.objects.create(name='Sam Real')
        Node.objects.create(node_id='sim-riley-brooks', owner=real)
        seed()
        sensor = Node.objects.get(node_id='sim-riley-brooks')
        self.assertEqual((sensor.owner, sensor.is_simulated), (real, False))

    def test_seeding_again_replaces_only_its_own_session(self):
        seed()
        first = TrainingSession.objects.get(label=SESSION_LABEL, ended_at__isnull=True)
        seed()
        first.refresh_from_db()
        self.assertIsNotNone(first.ended_at)
        self.assertEqual(TrainingSession.objects.filter(ended_at__isnull=True).count(), 1)
        self.assertEqual(Athlete.objects.filter(name__in=ATHLETES).count(), 4)

    def test_reset_leaves_a_real_varsity_group_and_real_athletes_alone(self):
        varsity = TrainingGroup.objects.create(name='Varsity')
        real = Athlete.objects.create(name='Sam Real')
        real.training_groups.add(varsity)
        seed()
        TrainingSession.objects.filter(label=SESSION_LABEL).update(ended_at=timezone.now())
        seed('--reset')
        self.assertTrue(TrainingGroup.objects.filter(pk=varsity.pk).exists())
        self.assertTrue(Athlete.objects.filter(pk=real.pk).exists())
        self.assertEqual(TrainingGroup.objects.filter(name=GROUP_NAME).count(), 1)
        self.assertEqual(Athlete.objects.filter(name__in=ATHLETES).count(), 4)

    def test_reset_releases_the_demo_racks(self):
        seed()
        session = TrainingSession.objects.get(label=SESSION_LABEL, ended_at__isnull=True)
        riley = Athlete.objects.get(name='Riley Brooks')
        rack, sensor = join(session.pk, riley)
        seed('--reset')
        self.assertFalse(RackRuntime.objects.filter(pk=rack.pk).exists())


class GymOnlyPiecesTests(TestCase):
    """A gym box's demo has a sensor fixed to rack 1 and a wristband tag; a remote
    school gets neither (nothing drives rack_1 online, and nobody taps a wristband at
    home). Seen on Demo U: rack_1 sat in the live room as "pulse overdue"."""

    def setUp(self):
        make_admin()

    @override_settings(EA_DEPLOYMENT='local')
    def test_a_gym_box_gets_the_rack_sensor_and_the_tag(self):
        seed()
        self.assertEqual(Node.objects.get(node_id=NODE_ID).rack_number, 1)
        for name, tag in NFC_TAG_BY_ATHLETE.items():
            self.assertEqual(Athlete.objects.get(name=name).nfc_tag_id, tag)

    @override_settings(EA_DEPLOYMENT='remote')
    def test_a_remote_school_gets_neither(self):
        seed()
        self.assertFalse(Node.objects.filter(node_id=NODE_ID).exists())
        self.assertFalse(Athlete.objects.filter(nfc_tag_id__isnull=False).exists())

    @override_settings(EA_DEPLOYMENT='remote')
    def test_online_the_finished_sets_name_each_athletes_own_sensor(self):
        seed()
        for a_set in Set.objects.all():
            if a_set.athlete.name == MANUAL_ATHLETE:   # has no simulated sensor
                self.assertIsNone(a_set.node)
            else:
                self.assertEqual(a_set.node.owner, a_set.athlete)

    @override_settings(EA_DEPLOYMENT='remote')
    def test_an_earlier_seeds_rack_sensor_is_removed_online(self):
        Node.objects.create(node_id=NODE_ID, rack_number=1, is_simulated=True)
        seed()
        self.assertFalse(Node.objects.filter(node_id=NODE_ID).exists())

    @override_settings(EA_DEPLOYMENT='remote')
    def test_a_real_sensor_called_rack_1_is_left_alone(self):
        Node.objects.create(node_id=NODE_ID, rack_number=1)   # not simulated: someone's real one
        seed()
        self.assertEqual(Node.objects.get(node_id=NODE_ID).rack_number, 1)


@override_settings(EA_DEPLOYMENT='remote')
class GuestSeatTests(TestCase):
    """Guest seats (Devin, 2026-11-08, `seed --guest-logins`): athletes kept free for
    visitors during a live demo. Each has a rack waiting from the moment the session is
    seeded, joining lands on it, and the demo logins are made only when asked for."""

    def setUp(self):
        make_admin()
        seed('--guest-logins')
        self.session = TrainingSession.objects.get(label=SESSION_LABEL, ended_at__isnull=True)

    def test_each_guest_has_a_sensor_on_a_rack_of_their_own_before_joining(self):
        racks = RackRuntime.objects.filter(session=self.session)
        self.assertEqual(sorted(r.owner_athlete.name for r in racks), sorted(GUEST_ATHLETES))
        for rack in racks:
            sensor = Node.objects.get(owner=rack.owner_athlete)
            self.assertEqual((sensor.node_id, sensor.is_simulated, sensor.rack_number),
                             (sensor_id(rack.owner_athlete.name), True, rack.rack_number))

    def test_the_live_room_shows_the_empty_seats(self):
        shown = {r['rack_number'] for r in room_state_snapshot(include_details=True)['racks']}
        for rack in RackRuntime.objects.filter(session=self.session):
            self.assertIn(rack.rack_number, shown)

    def test_joining_lands_on_the_waiting_rack(self):
        taylor = Athlete.objects.get(name=GUEST_ATHLETES[0])
        waiting = RackRuntime.objects.get(session=self.session, owner_athlete=taylor)
        rack, sensor = join(self.session.pk, taylor)
        self.assertEqual(rack.pk, waiting.pk)
        self.assertEqual(sensor.rack_number, waiting.rack_number)

    def test_guests_are_on_the_session_with_maxes(self):
        for name in GUEST_ATHLETES:
            guest = Athlete.objects.get(name=name)
            self.assertTrue(self.session.athletes.filter(pk=guest.pk).exists())
            self.assertTrue(guest.training_groups.filter(name=GROUP_NAME).exists())
            self.assertEqual(AthleteReferenceMax.objects.filter(athlete=guest).count(), 2)

    def test_the_guests_and_jordan_get_the_convention_logins(self):
        for name in LOGIN_ATHLETES:
            username, password = demo_login(name)
            login = Athlete.objects.get(name=name).user
            self.assertEqual(login.username, username)
            self.assertTrue(login.check_password(password))
        self.assertEqual(demo_login('Jordan Lee'), ('jordan', 'jordanpass123'))

    def test_the_phantoms_get_no_login_and_the_guests_are_never_phantoms(self):
        from .phantom_lifter import phantom_athletes
        Node.objects.filter(is_simulated=True).update(is_active=True)   # what the simulator does
        names = {a.name for a in phantom_athletes(MANUAL_ATHLETE)}
        self.assertEqual(names, {'Alex Rivera', 'Casey Morgan', 'Riley Brooks'})
        for name in names:
            self.assertIsNone(Athlete.objects.get(name=name).user)

    def test_seeding_again_moves_the_seats_and_keeps_the_logins(self):
        seed('--guest-logins')
        new = TrainingSession.objects.get(label=SESSION_LABEL, ended_at__isnull=True)
        self.assertEqual(RackRuntime.objects.filter(session=self.session).count(), 0)
        self.assertEqual(RackRuntime.objects.filter(session=new).count(), len(GUEST_ATHLETES))
        for name in GUEST_ATHLETES:     # maxes are not stacked by a re-seed
            self.assertEqual(AthleteReferenceMax.objects.filter(athlete__name=name).count(), 2)
        self.assertEqual(User.objects.count(), 1 + len(LOGIN_ATHLETES))

    def test_reset_removes_the_demo_logins_and_rebuilds_them_once(self):
        seed('--reset', '--guest-logins')
        self.assertEqual(Athlete.objects.filter(name__in=GUEST_ATHLETES).count(), len(GUEST_ATHLETES))
        self.assertEqual(RackRuntime.objects.filter(owner_athlete__name__in=GUEST_ATHLETES).count(),
                         len(GUEST_ATHLETES))
        self.assertEqual(User.objects.count(), 1 + len(LOGIN_ATHLETES))

    def test_a_real_athlete_with_a_guest_name_is_never_mixed_in(self):
        TrainingSession.objects.filter(label=SESSION_LABEL).update(ended_at=timezone.now())
        Athlete.objects.filter(name='Sam Ortiz').update(is_simulated=False)
        with self.assertRaisesMessage(CommandError, 'Sam Ortiz'):
            seed('--guest-logins')


@override_settings(EA_DEPLOYMENT='remote')
class GuestLoginRulesTests(TestCase):
    def setUp(self):
        make_admin()

    def test_without_the_flag_no_guests_and_no_logins(self):
        seed()
        self.assertFalse(Athlete.objects.filter(name__in=GUEST_ATHLETES).exists())
        self.assertFalse(RackRuntime.objects.exists())
        self.assertEqual(User.objects.count(), 1)

    def test_jordan_keeps_a_login_he_already_has(self):
        jordan = Athlete.objects.create(name=MANUAL_ATHLETE, is_simulated=True)
        jordan.user = User.objects.create_user('jlee', password=PASSWORD)
        jordan.save()
        seed('--guest-logins')
        jordan.refresh_from_db()
        self.assertEqual(jordan.user.username, 'jlee')
        self.assertFalse(User.objects.filter(username='jordan').exists())
        seed('--reset', '--guest-logins')       # a login a person chose survives a reset
        self.assertTrue(User.objects.filter(username='jlee').exists())

    def test_a_username_someone_else_holds_is_never_taken(self):
        other = User.objects.create_user('Taylor', password=PASSWORD)
        seed('--guest-logins')
        self.assertIsNone(Athlete.objects.get(name='Taylor Grant').user)
        self.assertTrue(User.objects.get(pk=other.pk).check_password(PASSWORD))


@override_settings(EA_DEPLOYMENT='local')
class NoGuestSeatsOnAGymBoxTests(TestCase):
    def test_a_gym_box_refuses_the_flag_and_writes_nothing(self):
        make_admin()
        with self.assertRaisesMessage(CommandError, 'remote server'):
            seed('--guest-logins')
        self.assertFalse(Athlete.objects.exists())


class DemoCoachTests(TestCase):
    def test_the_local_demo_coach_is_a_coach(self):
        call_command('ensure_demo_coach', '--i-know-this-is-a-demo-box', stdout=StringIO())
        coach = User.objects.get(username='coach')
        self.assertTrue(CoachProfile.objects.filter(user=coach).exists())
        seed()   # the local seed step's order: the demo coach first, then the seeder
        self.assertTrue(TrainingSession.objects.filter(label=SESSION_LABEL).exists())


@override_settings(EA_DEPLOYMENT='remote')
class SimulatorTests(TransactionTestCase):
    """Runs the real simulator against the test broker for a moment."""

    def setUp(self):
        make_admin()
        seed()
        session = TrainingSession.objects.get(label=SESSION_LABEL, ended_at__isnull=True)
        self.riley = Athlete.objects.get(name='Riley Brooks')
        self.rack, _ = join(session.pk, self.riley)
        self.sensor = Node.objects.get(owner=self.riley)
        self.assertEqual(self.sensor.rack_number, self.rack.rack_number)

    def run_sim(self, *args):
        call_command('simulate_node', '--seeded', *args, stdout=StringIO())

    def assert_unregistered(self):
        for node in Node.objects.filter(owner__is_simulated=True):
            self.assertIsNone(node.rack_number, node.node_id)
            self.assertFalse(node.is_active, node.node_id)

    def test_it_stops_itself_and_unregisters_its_sensors(self):
        self.run_sim('--stop-after', '0.02')          # about a second
        self.assert_unregistered()
        self.assertTrue(Node.objects.filter(pk=self.sensor.pk).exists())   # kept, not deleted

    def test_being_stopped_from_outside_does_the_same(self):
        # What Kubernetes does when `eactl sim --stop` deletes the Job.
        threading.Timer(1.0, lambda: os.kill(os.getpid(), 15)).start()
        self.run_sim()
        self.assert_unregistered()

    def test_a_new_run_puts_the_guest_sensors_back_on_their_seats(self):
        seed('--guest-logins')
        self.run_sim('--stop-after', '0.02')          # a run ending takes them off
        guest = Athlete.objects.get(name=GUEST_ATHLETES[0])
        seat = RackRuntime.objects.get(owner_athlete=guest)
        seen = []

        def watch():
            from django.db import connection
            try:
                seen.append(Node.objects.get(owner=guest).rack_number)
            finally:
                connection.close()
        threading.Timer(0.5, watch).start()
        self.run_sim('--stop-after', '0.02')
        self.assertEqual(seen, [seat.rack_number])

    def test_it_wakes_switched_off_sensors(self):
        Node.objects.filter(pk=self.sensor.pk).update(is_active=False)
        woke = []

        def watch():
            from django.db import connection
            try:
                woke.append(Node.objects.get(pk=self.sensor.pk).is_active)
            finally:
                connection.close()
        threading.Timer(0.5, watch).start()
        self.run_sim('--stop-after', '0.02')
        self.assertEqual(woke, [True])
