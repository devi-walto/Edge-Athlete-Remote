"""Let an athlete record be attached to a login.

WHY: until now the only people who could sign in were coaches. Athletes are about
to get logins of their own, and the server needs a way to tell the two apart. The
answer is this link: a login attached to an athlete record is an athlete login.

The link is empty for every athlete that exists today, so nothing changes for
anyone when this runs. Removing a login later empties the link and leaves the
athlete, their sets and their reps exactly as they were.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('event_handler', '0025_coach_profiles_for_existing_logins'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name='athlete',
            name='user',
            field=models.OneToOneField(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='athlete', to=settings.AUTH_USER_MODEL),
        ),
    ]
