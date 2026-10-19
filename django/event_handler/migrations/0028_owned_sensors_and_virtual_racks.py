"""Let a sensor belong to an athlete, and a rack belong to an athlete for one session.

WHY: online, an athlete trains on their own phone with their own sensor (spec 04).
The server makes them a rack when they join a session (a "virtual rack") and points
their own sensor at it. These three empty columns hold who owns what:
  - Node.owner: the athlete a sensor belongs to;
  - RackRuntime.owner_athlete: whose virtual rack it is;
  - RackRuntime.session: which session it was made for, to release it afterwards.

Every existing sensor and rack gets nothing in them, so nothing changes for a gym.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event_handler', '0027_athlete_login_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_nodes', to='event_handler.athlete'),
        ),
        migrations.AddField(
            model_name='rackruntime',
            name='owner_athlete',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_racks', to='event_handler.athlete'),
        ),
        migrations.AddField(
            model_name='rackruntime',
            name='session',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='virtual_racks', to='event_handler.trainingsession'),
        ),
    ]
