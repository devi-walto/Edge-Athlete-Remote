"""make_admin — make an existing coach login an administrator.

WHY THIS EXISTS: a gym box that was already in use before coach accounts arrived has
coach logins but may have no administrator, and only an administrator can manage
coach logins. Nothing on the website can fix that, by design: if a coach could
promote themselves from a browser, so could anyone who got hold of a coach login.
So the way out is the same as claiming a new installation: a command that only
someone with access to the machine itself can run.

    docker compose exec django python manage.py make_admin <username>

It promotes a login that already exists. It never creates one and never sets a
password. To recover an administrator whose login was deactivated, add --reactivate.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from event_handler.models import CoachProfile


class Command(BaseCommand):
    help = "Make an existing coach login an administrator (run on the machine itself)."

    def add_arguments(self, parser):
        parser.add_argument('username', help="The login to promote. It must already exist.")
        parser.add_argument(
            '--reactivate', action='store_true',
            help="Also switch the login back on if it was deactivated.")

    def handle(self, *args, **options):
        username = options['username']
        user = get_user_model().objects.filter(username=username).first()
        if user is None:
            known = ', '.join(get_user_model().objects.order_by('username')
                              .values_list('username', flat=True)) or '(none)'
            raise CommandError(
                f"There is no login named '{username}'. Nothing was changed. "
                f"Logins on this installation: {known}")
        if not user.is_active and not options['reactivate']:
            raise CommandError(
                f"'{username}' is deactivated, so making it an administrator would "
                "not let anyone sign in. Nothing was changed. Run this again with "
                "--reactivate to switch it back on as well.")

        user.is_staff = True
        user.is_active = True
        user.save(update_fields=['is_staff', 'is_active'])
        # An administrator is a coach too: the Coaches screen lists coach profiles.
        CoachProfile.objects.get_or_create(user=user)
        self.stdout.write(self.style.SUCCESS(
            f"'{username}' is now an administrator. Coaches appears in their account "
            "menu the next time they open or reload the coach workspace."))
