"""rack_names.py — a rack's automatic number, its name, and how screens print it.

Why this exists (spec 18, Phase 2): a rack used to be a numbered slot a coach gave a
tablet. Now a tablet makes its own rack: it takes the next free number without
asking (numbers still run through every rack table, sensor record, address and live
topic) and a name, "Rack 3" unless someone types another. Two racks may share a name,
so the coach's screens add the number after a shared one, small: "Platform (4)".
Everything that prints a rack asks this file, so the rule lives in one place.
"""
from ..models import VIRTUAL_RACK_BASE, Node, RackRuntime, RackScreen

NAME_MAX = 40


def next_rack_number():
    """The next gym rack number nobody uses: above every rack a tablet, sensor or
    rack state has ever named, below the virtual racks (spec 04)."""
    taken = set()
    for model in (RackScreen, Node, RackRuntime):
        taken.update(model.objects.filter(rack_number__lt=VIRTUAL_RACK_BASE)
                     .exclude(rack_number=None).values_list('rack_number', flat=True))
    return max(taken, default=0) + 1


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
