"""Tests for phantom lifters (simulate_node --phantom): seeded athletes who lift on their own.

WHY THESE EXIST: a phantom does a person's part online, through the same routes an
athlete's phone uses, so the room trains in parallel with one real athlete lifting a
real sensor. Three things must hold: a phantom's sets come out exactly like a real
athlete's (planned reps, saved through set_complete); the hands-on athlete, a real
athlete, or anyone a person can sign in as is never played; and the no-password
logins a phantom needs are gone when it stops.
"""
import threading
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .management.commands.seed_active_session import JORDAN, MANUAL_ATHLETE
from .models import Athlete, CoachProfile, Node, RackRuntime, Rep, Set, TrainingSession
from .phantom_lifter import (PhantomLifter, give_login, is_phantom_login, phantom_athletes,
                             take_logins_back)

User = get_user_model()
NO_WAITING = {"rep_seconds": 0, "rest_seconds": (0, 0), "countdown_seconds": 0,
              "end_seconds": 0, "summary_seconds": 0}


def seed_demo():
    admin = User.objects.create_user('head', password='Unique-demo-2026!safe', is_staff=True)
    CoachProfile.objects.create(user=admin)
    call_command('seed_active_session', stdout=StringIO())
    Node.objects.filter(is_simulated=True).update(is_active=True)   # what the simulator does
    return TrainingSession.objects.get(ended_at__isnull=True)


@override_settings(EA_DEPLOYMENT='remote')
class WhoBecomesAPhantomTests(TestCase):
    def setUp(self):
        seed_demo()

    def test_every_seeded_athlete_but_the_hands_on_one(self):
        self.assertEqual(MANUAL_ATHLETE, JORDAN)
        names = [a.name for a in phantom_athletes(MANUAL_ATHLETE)]
        self.assertEqual(names, ['Alex Rivera', 'Casey Morgan', 'Riley Brooks'])

    def test_never_a_real_athlete(self):
        real = Athlete.objects.create(name='Sam Real')
        Node.objects.create(node_id='ea-real', owner=real, is_simulated=True)
        self.assertNotIn(real, phantom_athletes(MANUAL_ATHLETE))

    def test_never_a_seeded_athlete_someone_can_sign_in_as(self):
        alex = Athlete.objects.get(name='Alex Rivera')
        alex.user = User.objects.create_user('alex', password='Unique-demo-2026!safe')
        alex.save()
        self.assertNotIn(alex, phantom_athletes(MANUAL_ATHLETE))

    def test_its_login_has_no_usable_password_and_is_taken_back(self):
        alex = Athlete.objects.get(name='Alex Rivera')
        login = give_login(alex)
        self.assertTrue(is_phantom_login(login))
        self.assertFalse(login.has_usable_password())
        self.assertFalse(self.client.login(username=login.username, password=''))
        take_logins_back([alex])
        alex.refresh_from_db()
        self.assertIsNone(alex.user)
        self.assertFalse(User.objects.filter(pk=login.pk).exists())

    def test_taking_back_never_removes_a_login_a_coach_made(self):
        casey = Athlete.objects.get(name='Casey Morgan')
        casey.user = User.objects.create_user('casey', password='Unique-demo-2026!safe')
        casey.save()
        take_logins_back([casey])
        casey.refresh_from_db()
        self.assertEqual(casey.user.username, 'casey')


@override_settings(EA_DEPLOYMENT='remote')
class APhantomLiftsTests(TestCase):
    def setUp(self):
        self.session = seed_demo()
        self.riley = Athlete.objects.get(name='Riley Brooks')
        self.sensor = Node.objects.get(owner=self.riley)
        self.sent = []
        self.phantom = PhantomLifter(self.riley, self.sensor.node_id,
                                     lambda node, n, rep: self.sent.append((node, n)),
                                     lambda line: None, NO_WAITING)

    def test_it_joins_and_controls_its_own_rack(self):
        self.phantom.join(self.session.pk)
        runtime = RackRuntime.objects.get(rack_number=self.phantom.rack)
        self.assertEqual(runtime.owner_athlete, self.riley)
        self.sensor.refresh_from_db()
        self.assertEqual(self.sensor.rack_number, self.phantom.rack)

    def test_one_set_is_saved_like_a_real_athletes(self):
        self.phantom.join(self.session.pk)
        self.assertTrue(self.phantom.lift_one_set(self.session.pk, threading.Event()))
        a_set = Set.objects.get(athlete=self.riley)
        self.assertEqual(a_set.exercise.name, 'Back Squat')   # the plan's first movement
        self.assertEqual(a_set.set_number, 1)
        self.assertEqual(a_set.reps_completed, 3)             # the plan's reps
        self.assertIsNotNone(a_set.ended_at)
        self.assertEqual(a_set.node, self.sensor)
        self.assertEqual(Rep.objects.filter(set=a_set).count(), 3)
        self.assertEqual(self.sent, [(self.sensor.node_id, n) for n in (1, 2, 3)])
        self.assertEqual(RackRuntime.objects.get(rack_number=self.phantom.rack).phase, 'idle')

    def test_its_next_set_follows_the_plan(self):
        self.phantom.join(self.session.pk)
        for _ in range(2):
            self.phantom.lift_one_set(self.session.pk, threading.Event())
        numbers = list(Set.objects.filter(athlete=self.riley).order_by('set_number')
                       .values_list('set_number', flat=True))
        self.assertEqual(numbers, [1, 2])

    def test_stopped_mid_set_it_saves_the_reps_so_far_and_leaves_nothing_open(self):
        # Seen in a live run: time ran out mid-set and the set stayed open, the rack
        # "active" on the coach's screen.
        stop = threading.Event()
        self.phantom.publish_rep = lambda node, n, rep: stop.set()      # stop after rep 1
        self.phantom.join(self.session.pk)
        self.assertFalse(self.phantom.lift_one_set(self.session.pk, stop))
        self.phantom.leave()
        a_set = Set.objects.get(athlete=self.riley)
        self.assertIsNotNone(a_set.ended_at)
        self.assertEqual((a_set.reps_completed, a_set.is_false_set), (1, False))
        runtime = RackRuntime.objects.get(rack_number=self.phantom.rack)
        self.assertEqual(runtime.phase, 'idle')
        self.assertIsNone(runtime.lease_expires_at)

    def test_leaving_lets_go_of_the_rack(self):
        self.phantom.join(self.session.pk)
        self.phantom.leave()
        runtime = RackRuntime.objects.get(rack_number=self.phantom.rack)
        self.assertIsNone(runtime.lease_expires_at)

    def test_it_never_touches_the_hands_on_athletes_rack(self):
        jordan = Athlete.objects.get(name=MANUAL_ATHLETE)
        self.phantom.join(self.session.pk)
        self.phantom.lift_one_set(self.session.pk, threading.Event())
        self.assertFalse(Set.objects.filter(athlete=jordan, ended_at__isnull=True).exists())
        self.assertFalse(RackRuntime.objects.filter(owner_athlete=jordan).exists())


@override_settings(EA_DEPLOYMENT='local')
class GymBoxTests(TestCase):
    def test_phantoms_are_refused_on_a_gym_box(self):
        with self.assertRaisesMessage(CommandError, 'online only'):
            call_command('simulate_node', '--phantom', stdout=StringIO())
