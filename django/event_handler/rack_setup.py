"""rack_setup.py — a tablet makes its own rack, and anyone allowed renames it (spec 18).

Why this file exists: a rack used to be a numbered slot a coach handed a tablet from
Room Layout. Now the tablet does it on "Set up this rack" (board F_Rack_Setup): it
takes the next free number without asking and a name ("Rack 3" unless someone types
another), and the name can be changed later from the tablet or Room Layout. One
device, one rack: a tablet that replaces a dead one makes a new rack, and where each
athlete is still comes from their newest check-in, so nothing is lost.

The same routes serve both versions. In a gym (no login) the tablet says which device
it is in the X-Rack-Device-ID header. Online it is signed in with the school's common
login, and its device comes from that sign-in.
"""
from django.db import IntegrityError, transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .deployment import is_hosted
from .models import RackScreen
from .permissions import (COMMON_DEVICE, COMMON_OWN_RACK, ONLINE_COACH, ONLINE_REFUSE,
                          _common_device, open_on_local)
from .services import rack_names

DEVICE_HEADER = 'X-Rack-Device-ID'


def _device_id(request):
    if is_hosted():
        device = _common_device(request)
        return device.device_id if device else None
    value = request.headers.get(DEVICE_HEADER) or request.query_params.get('device_id')
    return value if isinstance(value, str) and 0 < len(value) <= 255 else None


def _rack(screen):
    return {'rack_number': screen.rack_number, 'name': screen.name,
            'label': rack_names.label_for(screen.rack_number)}


@api_view(['GET', 'POST'])
@permission_classes([open_on_local(ONLINE_REFUSE, common=COMMON_DEVICE)])
def my_rack(request):
    """GET: this device's rack, or none yet with the name it would be given.
    POST { name }: make this device's rack (the next free number, that name, or the
    suggested one). A device that already has a rack gets it back unchanged."""
    device_id = _device_id(request)
    if device_id is None:
        return Response({'code': 'device_required',
                         'detail': f'Say which device this is ({DEVICE_HEADER}).'}, status=400)
    screen = RackScreen.objects.filter(device_id=device_id).exclude(rack_number=None).first()
    if request.method == 'GET':
        if screen is None:
            return Response({'rack': None, 'suggested_name': rack_names.suggested_name()})
        return Response({'rack': _rack(screen), 'suggested_name': None})
    if screen is not None:
        return Response({'rack': _rack(screen)})
    typed = request.data.get('name')
    name = rack_names.clean_name(typed) if typed not in (None, '') else rack_names.suggested_name()
    if name is None:
        return Response({'name': [f'1 to {rack_names.NAME_MAX} characters.']}, status=400)
    # Two tablets setting up at the same moment could pick one number; the second
    # trips the one-screen-per-rack rule and simply takes the next.
    for _ in range(5):
        try:
            with transaction.atomic():
                screen, _created = RackScreen.objects.select_for_update().get_or_create(device_id=device_id)
                screen.rack_number = rack_names.next_rack_number()
                screen.name = name
                screen.save(update_fields=['rack_number', 'name'])
            return Response({'rack': _rack(screen)}, status=201)
        except IntegrityError:
            continue
    return Response({'detail': 'Racks are being set up too fast; try again.'}, status=409)


@api_view(['PATCH'])
@permission_classes([open_on_local(ONLINE_COACH, common=COMMON_OWN_RACK)])
def rack_name(request, rack_number):
    """Rename a rack { name }: a coach from Room Layout, or the rack's own tablet.
    Changes the name everywhere it shows and nothing else."""
    name = rack_names.clean_name(request.data.get('name'))
    if name is None:
        return Response({'name': [f'1 to {rack_names.NAME_MAX} characters.']}, status=400)
    screen = RackScreen.objects.filter(rack_number=rack_number).first()
    if screen is None:
        return Response({'detail': 'No tablet has set this rack up.'}, status=404)
    screen.name = name
    screen.save(update_fields=['name'])
    return Response({'rack': _rack(screen)})
