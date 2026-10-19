"""Tests for spec 04, Phase 0: sensors that belong to an athlete, and virtual racks.

WHY THESE EXIST: the rest of spec 04 trusts these facts. A virtual rack must be told
apart from a gym rack by its number alone, and an athlete leaving (archived or
deleted) must never take a sensor, a rack or anyone's history with them.
"""
from django.test import TestCase
from django.utils import timezone

from .models import VIRTUAL_RACK_BASE, Athlete, Node, RackRuntime, TrainingSession


class VirtualRackDataTests(TestCase):
    def setUp(self):
        self.athlete = Athlete.objects.create(name='Riley Brooks')
        self.session = TrainingSession.objects.create(label='Remote day', started_at=timezone.now())

    def test_gym_racks_and_virtual_racks_are_told_apart_by_number(self):
        self.assertFalse(RackRuntime.objects.create(rack_number=1).is_virtual)
        self.assertFalse(RackRuntime.objects.create(rack_number=VIRTUAL_RACK_BASE - 1).is_virtual)
        self.assertTrue(RackRuntime.objects.create(rack_number=VIRTUAL_RACK_BASE).is_virtual)

    def test_a_new_sensor_and_rack_have_no_owner(self):
        self.assertIsNone(Node.objects.create(node_id='gym-sensor').owner)
        rack = RackRuntime.objects.create(rack_number=3)
        self.assertIsNone(rack.owner_athlete)
        self.assertIsNone(rack.session)

    def test_removing_the_athlete_keeps_their_sensor_and_rack(self):
        sensor = Node.objects.create(node_id='sim-riley-brooks', owner=self.athlete)
        rack = RackRuntime.objects.create(rack_number=VIRTUAL_RACK_BASE,
                                          owner_athlete=self.athlete, session=self.session)

        self.athlete.delete()

        sensor.refresh_from_db()
        rack.refresh_from_db()
        self.assertIsNone(sensor.owner)
        self.assertIsNone(rack.owner_athlete)
        self.assertEqual(rack.session, self.session)

    def test_an_athlete_finds_their_sensors_and_a_session_its_racks(self):
        Node.objects.create(node_id='sim-riley-brooks', owner=self.athlete)
        RackRuntime.objects.create(rack_number=VIRTUAL_RACK_BASE, owner_athlete=self.athlete,
                                   session=self.session)
        self.assertEqual([n.node_id for n in self.athlete.owned_nodes.all()], ['sim-riley-brooks'])
        self.assertEqual([r.rack_number for r in self.session.virtual_racks.all()], [VIRTUAL_RACK_BASE])
