"""Checking an athlete in at a rack: the one step both ways in share.

WHY: an athlete gets to a rack in two ways. In a gym, they tap their name (or their
wristband) on the rack's screen (the check-in route). Online, joining a session puts
them on their own rack (spec 04). Both must do exactly the same thing, or the rack
screen, the live room and the report would see the two differently. So the step
lives here, once.

What it does: records the check-in (append-only; the newest check-in is the
athlete's current rack), makes the athlete the rack's selected lifter, moves the
rack's state on by one revision, and tells the live room something changed.

The caller holds the rack's row lock and has already decided the athlete may be
there; this only records it.
"""
from ..models import MonitoringEvent, RackCheckIn


def record_check_in(runtime, session, athlete):
    RackCheckIn.objects.create(session=session, athlete=athlete, rack_number=runtime.rack_number)
    runtime.selected_athlete = athlete
    runtime.state_version += 1
    runtime.save(update_fields=["selected_athlete", "state_version", "updated_at"])
    MonitoringEvent.objects.create(reason="athlete_checked_in", is_simulated=session.is_simulated)
