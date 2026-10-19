"""Tests that is_simulated is a label only: demo data counts like real data.

WHY THESE EXIST: is_simulated used to bar a sensor from racks and hide its sets
from the live room and from max updates. Nothing ever set it, so it did nothing,
until demo data needed it (spec 04, Phase 5): the seeded athletes' stand-in sensors
must drive racks, fill the live room and feed maxes exactly like real ones, while
the label lets the seeder find and wipe its own rows.
"""
from django.test import TestCase
from django.utils import timezone

from .models import Athlete, AthleteReferenceMax, Exercise, Node, Set, TrainingSession
from .services.node_health import node_is_usable
from .services.room_state import room_state_snapshot
from .services.session_completion import _recalculate_reference_maxes


class SimulatedIsALabelOnlyTests(TestCase):
    def setUp(self):
        self.session = TrainingSession.objects.create(label='Demo day', started_at=timezone.now())
        self.athlete = Athlete.objects.create(name='Alex Rivera', is_simulated=True)
        self.session.athletes.add(self.athlete)
        self.node = Node.objects.create(node_id='sim-alex-rivera', is_simulated=True)
        self.squat = Exercise.objects.get_or_create(name='Back Squat')[0]
        Set.objects.create(session=self.session, athlete=self.athlete, node=self.node,
                           exercise=self.squat, set_number=1, weight_lbs=225.0,
                           ended_at=timezone.now(), reps_completed=5, avg_velocity=0.6,
                           is_simulated=True)

    def test_a_simulated_sensor_is_usable(self):
        self.assertTrue(node_is_usable(self.node))

    def test_a_simulated_set_counts_in_the_live_room(self):
        summary = room_state_snapshot(include_details=True)['summary']
        self.assertEqual(summary['athletes_with_sets'], 1)

    def test_a_simulated_set_feeds_the_next_max(self):
        _recalculate_reference_maxes(self.session)
        self.assertTrue(AthleteReferenceMax.objects.filter(
            athlete=self.athlete, exercise=self.squat).exists())

    def test_a_switched_off_sensor_is_still_unusable(self):
        self.node.is_active = False
        self.assertFalse(node_is_usable(self.node))
