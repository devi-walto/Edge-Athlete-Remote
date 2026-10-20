"""A table for sensor claim codes: one-time codes an athlete gives their sensor.

WHY: online, an athlete adds their own sensor without anyone's help (spec 14). Their
athlete page gives them a code; the sensor sends it to the school with its ID and gets
its own sensor token back. Only a hash of each code is kept, like a password; each code
also remembers which sensor used it. A new, empty table: nothing existing changes.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event_handler', '0028_owned_sensors_and_virtual_racks'),
    ]

    operations = [
        migrations.CreateModel(
            name='SensorClaimCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(max_length=128)),
                ('lookup', models.CharField(max_length=16, unique=True)),
                ('created_at', models.DateTimeField()),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('athlete', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sensor_claim_codes', to='event_handler.athlete')),
                ('sensor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='event_handler.node')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
