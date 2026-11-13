"""rack_names.py — a rack's automatic number, its name, and how screens print it.

Why this exists (spec 18, Phase 2): a rack used to be a numbered slot a coach gave a
tablet. Now a tablet makes its own rack: it takes the next free number without
asking (numbers still run through every rack table, sensor record, address and live
topic) and a name, "Rack 3" unless someone types another. Two racks may share a name,
so the coach's screens add the number after a shared one, small: "Platform (4)".
Everything that prints a rack asks this file, so the rule lives in one place.

It also keeps the racks tidy (Devin, 2026-11-13). A rack whose tablet hasn't been heard
from in 30 days, with no sensor and no set open, is cleaned up, and its number is free
for the next tablet (the lowest free number is taken, so 1, _, 3 gives the next one 2).
A number is free only when nothing still points at it, including a check-in during the
running session, so nobody can show up "at" a rack they never used. The 10-minute rule
that hides a dead tablet's empty rack from the room (room_state.py) asks the same two
questions this file answers: when was the tablet last heard, and is the number in use.
"""
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from ..models import (VIRTUAL_RACK_BASE, CommonDevice, Node, RackCheckIn, RackRuntime,
                      RackScreen, Set)
from .active_session import active_session

# A tablet silent this long, on a rack with no sensor and no set open: the rack goes.
CLEAN_UP_AFTER = timedelta(days=30)
# How often the clean-up may run (it runs when the room or a tablet's rack is read).
CLEAN_UP_EVERY_SECONDS = 60 * 60

NAME_MAX = 40


def numbers_in_use():
    """Every gym rack number something still points at: a tablet's rack, a sensor, a
    rack's live state, or a check-in during the running session."""
    taken = set()
    for model in (RackScreen, Node, RackRuntime):
        taken.update(model.objects.filter(rack_number__lt=VIRTUAL_RACK_BASE)
                     .exclude(rack_number=None).values_list('rack_number', flat=True))
    session = active_session()
    if session is not None:
        taken.update(RackCheckIn.objects.filter(session=session).values_list('rack_number', flat=True))
    return taken


def next_rack_number():
    """The lowest gym rack number nothing points at (below the virtual racks, spec 04)."""
    taken = numbers_in_use()
    number = 1
    while number in taken:
        number += 1
    return number


def last_heard(numbers):
    """{rack number: when its tablet was last heard}. A tablet renews its hold on its
    rack every 5 seconds (the controller lease), so the lease's end is the last word
    from it; a tablet that never took its rack counts from when it set the rack up."""
    heard = dict(RackScreen.objects.filter(rack_number__in=list(numbers))
                 .values_list('rack_number', 'last_seen'))
    for number, until in (RackRuntime.objects.filter(rack_number__in=list(numbers))
                          .exclude(lease_expires_at=None).values_list('rack_number', 'lease_expires_at')):
        heard[number] = until
    return heard


def quiet_racks(longer_than, now=None):
    """Gym racks with a tablet, no sensor, and no word from the tablet for `longer_than`."""
    now = now or timezone.now()
    tablets = set(RackScreen.objects.filter(rack_number__lt=VIRTUAL_RACK_BASE)
                  .exclude(rack_number=None).values_list('rack_number', flat=True))
    tablets -= set(Node.objects.filter(rack_number__in=tablets).values_list('rack_number', flat=True))
    heard = last_heard(tablets)
    return {n for n in tablets if heard.get(n) is None or heard[n] < now - longer_than}


def clean_up(now=None):
    """Remove racks quiet for CLEAN_UP_AFTER with no set open or anyone checked in this
    session, with their live state, and common-login sign-ins that ended that long ago.
    History is untouched: reports keep the names they were frozen with, sets and
    check-ins keep their numbers. Returns the numbers freed."""
    now = now or timezone.now()
    gone = quiet_racks(CLEAN_UP_AFTER, now)
    if not gone:
        removed = set()
    else:
        open_sets = set(RackRuntime.objects.filter(rack_number__in=gone, current_set__ended_at=None)
                        .exclude(current_set=None).values_list('rack_number', flat=True))
        session = active_session()
        here_today = set(RackCheckIn.objects.filter(session=session, rack_number__in=gone)
                         .values_list('rack_number', flat=True)) if session else set()
        removed = gone - open_sets - here_today
        with transaction.atomic():
            RackRuntime.objects.filter(rack_number__in=removed).delete()
            RackScreen.objects.filter(rack_number__in=removed).delete()
    CommonDevice.objects.filter(signed_out_at__lt=now - CLEAN_UP_AFTER).delete()
    return removed


def tidy_up():
    """clean_up(), at most once an hour (it runs on reads, which come often)."""
    if cache.add('rack_names:clean_up', True, timeout=CLEAN_UP_EVERY_SECONDS):
        clean_up()


def suggested_name():
    """'Rack N' for the smallest N no rack is called yet."""
    names = {n.lower() for n in RackScreen.objects.exclude(name='').values_list('name', flat=True)}
    n = 1
    while f'rack {n}' in names:
        n += 1
    return f'Rack {n}'


def clean_name(value):
    """A name as typed, trimmed; None if it can't be one."""
    if not isinstance(value, str):
        return None
    name = ' '.join(value.split())
    return name if 0 < len(name) <= NAME_MAX else None


def names_by_rack(numbers=None):
    """{rack number: name} for racks that have a tablet with a name."""
    screens = RackScreen.objects.exclude(rack_number=None).exclude(name='')
    if numbers is not None:
        screens = screens.filter(rack_number__in=list(numbers))
    return dict(screens.values_list('rack_number', 'name'))


def labels_by_rack(numbers):
    """{rack number: what a coach's screen prints}: its name, the number in brackets
    when another rack shares the name, 'Rack N' for a rack with no name yet."""
    numbers = list(numbers)
    names = names_by_rack()
    counts = {}
    for name in names.values():
        counts[name.lower()] = counts.get(name.lower(), 0) + 1
    labels = {}
    for number in numbers:
        name = names.get(number)
        if not name:
            labels[number] = f'Rack {number}'
        elif counts[name.lower()] > 1:
            labels[number] = f'{name} ({number})'
        else:
            labels[number] = name
    return labels


def label_for(number):
    return labels_by_rack([number])[number] if number is not None else None
