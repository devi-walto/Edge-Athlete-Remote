"""Give every login that already exists a coach profile.

WHY: the coach-accounts work added the CoachProfile table, but only logins created
through the new Coaches screen got a row in it. Every login that existed before
(on any gym box already in use) had none. That was invisible while "a login" and
"a coach" meant the same thing. It stops being invisible in the next piece of work,
where having a coach profile is what tells a coach apart from an athlete: a coach
with no profile would be treated as a stranger and locked out of their own gym.

So: one profile per existing login, with the forced password change OFF, because
these people already chose their own passwords.

Safe to run twice; it only ever adds the profiles that are missing. Going
backwards does nothing, on purpose: removing profiles would lock coaches out.
"""
from django.conf import settings
from django.db import migrations


def backfill_coach_profiles(user_model, profile_model):
    """Create the missing profiles. Returns how many were created."""
    have = set(profile_model.objects.values_list('user_id', flat=True))
    missing = [profile_model(user_id=pk, must_change_password=False)
               for pk in user_model.objects.values_list('pk', flat=True) if pk not in have]
    profile_model.objects.bulk_create(missing)
    return len(missing)


def forwards(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    backfill_coach_profiles(apps.get_model(app_label, model_name),
                            apps.get_model('event_handler', 'CoachProfile'))


class Migration(migrations.Migration):
    dependencies = [
        ('event_handler', '0024_setup_code_and_coach_profiles'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
