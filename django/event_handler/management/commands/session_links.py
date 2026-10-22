# session_links.py — print the session link for the running session, ready to send.
#
# Why this exists: online, athletes join a session through its link,
# https://<school>/session/<number>. The number isn't shown anywhere yet (the coach's
# "Copy session link" button comes with the UI redesign, spec 04 Phase 4), and during a
# demo there was no quick way to find it. `eactl get-session-link "School"` runs this inside the
# school; it only reads.
#
# It prints the running session's link first. With none running, it says so and lists
# the sessions a coach has set up but not started yet, so a link can be sent ahead of
# time (an athlete who opens it early waits on "not started yet" until the coach starts).

from django.core.management.base import BaseCommand, CommandError

from event_handler.services.active_session import open_sessions, scheduled_but_not_started

SET_UP_SHOWN = 5   # the soonest few; a school can have many set up for the weeks ahead


class Command(BaseCommand):
    help = "Print the link athletes use to join the running session (and any set up ahead)."

    def add_arguments(self, parser):
        parser.add_argument("--address", required=True,
                            help="the school's own address, e.g. demo-u-k7m2qx.<domain> "
                                 "(eactl passes it)")

    def handle(self, *args, **options):
        address = options["address"].strip().rstrip("/")
        if not address:
            raise CommandError("--address is empty")
        if "://" not in address:
            address = f"https://{address}"

        def line(session):
            return f"  {address}/session/{session.pk}    {session.label or '(no name)'}"

        running = list(open_sessions())
        if running:
            self.stdout.write("Running now:")
            for session in running:
                self.stdout.write(line(session))
        else:
            self.stdout.write("No session is running.")

        set_up = list(scheduled_but_not_started()[:SET_UP_SHOWN])
        if set_up:
            self.stdout.write("Set up, not started yet (athletes who open these wait until "
                              "the coach starts):")
            for session in set_up:
                self.stdout.write(line(session))
