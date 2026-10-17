"""Add the table of login links a coach sends to athletes (spec 03).

WHY: a remote athlete needs a login, and athletes never create themselves. A coach
sends a one-time link; using it makes the athlete's login. This table records each
link: who it's for, a one-way hash of its secret (never the link itself), and
whether it was used, cancelled or ran out.

A new, empty table: nothing that exists today changes when this runs.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event_handler', '0026_athlete_login'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AthleteLoginLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(max_length=128)),
                ('lookup', models.CharField(max_length=16, unique=True)),
                ('created_at', models.DateTimeField()),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('athlete', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='login_links', to='event_handler.athlete')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
