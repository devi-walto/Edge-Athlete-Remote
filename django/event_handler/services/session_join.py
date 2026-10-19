"""Joining a session online: an athlete gets their own rack, with their own sensor on it.

WHY: in a gym a rack is a tablet a coach set up, with a sensor a coach linked. A coach
running fifty athletes over a video call can't set up fifty racks. So when a signed-in
athlete joins, the server makes their rack for them (a "virtual rack", numbered from
VIRTUAL_RACK_BASE up) and points their own sensor at it (spec 04, Phase 1).

join(session_id, athlete), all in one transaction:
  1. the session must have started and not ended;
  2. the athlete must belong in it: on its roster, or in a group taking part in it
     (Devin, 2026-10-14);
  3. their rack for this session, found or made. Joining again gives the same one;
  4. they're checked in on it, through the same step the gym's check-in uses, so the
     rack already names them when their screen opens;
  5. if they own an active sensor, it is pointed at their rack.

Joins for one session wait their turn (a row lock on the session), so two athletes
joining at the same moment can never be given the same rack number. Only one
session is open at a time, so that is enough.
"""
from django.db import transaction
from django.db.models import F, Max

from ..models import VIRTUAL_RACK_BASE, Node, RackRuntime, TrainingSession
from .rack_checkin import record_check_in


class JoinRefused(Exception):
    """Why an athlete can't join: a code for the screen, and the HTTP status."""

    def __init__(self, code, status, detail, session=None):
        super().__init__(detail)
        self.code, self.status, self.detail = code, status, detail
        # The session's name, for a session the athlete belongs in that hasn't
        # started or has ended: the waiting and ended pages show it.
        self.session = session


def may_join(session, athlete):
    """On the session's roster, or in a group whose program takes part in it."""
    if session.athletes.filter(pk=athlete.pk).exists():
        return True
    return session.participations.filter(
        training_program__training_group__athletes=athlete).exists()


def join(session_id, athlete):
    """Returns (rack, sensor or None). Raises JoinRefused."""
    with transaction.atomic():
        session = TrainingSession.objects.select_for_update().filter(pk=session_id).first()
        if session is None:
            raise JoinRefused('not_found', 404, 'That session does not exist.')
        if not athlete.is_active or not may_join(session, athlete):
            raise JoinRefused('not_in_session', 403, "You're not on this session. Ask your coach.")
        named = {'id': session.pk, 'label': session.label}
        if session.started_at is None:
            raise JoinRefused('not_started', 409, "Your coach hasn't started this session yet.", named)
        if session.ended_at is not None:
            raise JoinRefused('ended', 409, 'This session has ended.', named)

        # On the roster from now on, so the live room and the report include them
        # (a group member may not have been on it when the day was set up).
        session.athletes.add(athlete)

        rack = (RackRuntime.objects.select_for_update()
                .filter(session=session, owner_athlete=athlete).first())
        if rack is None:
            highest = (RackRuntime.objects.filter(rack_number__gte=VIRTUAL_RACK_BASE)
                       .aggregate(n=Max('rack_number'))['n'])
            rack = RackRuntime.objects.create(
                rack_number=VIRTUAL_RACK_BASE if highest is None else highest + 1,
                owner_athlete=athlete, session=session)
        if rack.selected_athlete_id != athlete.pk:
            record_check_in(rack, session, athlete)

        sensor = (Node.objects.select_for_update()
                  .filter(owner=athlete, is_active=True)
                  # the one heard from most recently; a never-seen one last
                  .order_by(F('last_seen').desc(nulls_last=True), '-pk').first())
        if sensor is not None and sensor.rack_number != rack.rack_number:
            sensor.rack_number = rack.rack_number
            sensor.save(update_fields=['rack_number'])
    return rack, sensor
