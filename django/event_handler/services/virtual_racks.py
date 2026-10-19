"""Virtual racks: the online athlete's own rack, and cleaning up after a session.

WHY: an online athlete's rack is made for them when they join a session (see
session_join.py). It exists only for that session, so when the coach ends the session
its racks go away: nothing piles up, and each athlete's sensor is free again for the
next session (spec 04, Phase 2).

Also home to ending a rack's unfinished sets, the step both releasing a virtual rack
and a gym rack's recovery/release use (it lived in views.py; moved here unchanged so
the end-of-session code can use it too).
"""
from django.utils import timezone

from ..models import Node, RackRuntime, Set


def end_open_sets_on_rack(rack_number):
    """End every unfinished set on this rack as a FALSE set.

    PROTECT on Set.session means we never delete; ending is the only legal way to
    close work, and false is the honest label for work that was started and
    abandoned. A set is "on this rack" when its node is assigned here — that's
    the physical truth, and the sensor is what ties a set to a rack.

    The CALLER owns the transaction.
    """
    open_sets = Set.objects.select_for_update().filter(
        ended_at=None,
        node__rack_number=rack_number,
    )
    ended = 0
    for s in open_sets:
        s.ended_at = timezone.now()
        s.is_false_set = True
        s.reps_completed = 0
        s.avg_velocity = None
        s.peak_velocity = None
        s.save(update_fields=[
            "ended_at", "is_false_set", "reps_completed",
            "avg_velocity", "peak_velocity",
        ])
        ended += 1
    return ended


def release_session_racks(session):
    """When a session ends: end each virtual rack's open set (kept, as a false set),
    take each athlete's sensor off their rack, and remove the racks.

    Their sets, reps and check-ins stay: the report and every athlete's history read
    those, never the rack rows. The CALLER owns the transaction. Returns how many
    racks were released.
    """
    racks = list(RackRuntime.objects.select_for_update().filter(session=session))
    for rack in racks:
        end_open_sets_on_rack(rack.rack_number)
        Node.objects.filter(rack_number=rack.rack_number).update(rack_number=None)
    RackRuntime.objects.filter(pk__in=[rack.pk for rack in racks]).delete()
    return len(racks)
