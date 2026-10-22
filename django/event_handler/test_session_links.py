"""Tests for session_links, what `eactl link "School"` prints (spec 04).

WHY THESE EXIST: during a demo the running session's link couldn't be found anywhere.
This prints it, ready to send: the running session first, or, with none running, the
sessions set up ahead. It must never print a link for a session that has ended.
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import TrainingSession


def links(address="demo-u-k7m2qx.example.test"):
    out = StringIO()
    call_command("session_links", "--address", address, stdout=out)
    return out.getvalue()


class SessionLinksTests(TestCase):
    def test_the_running_session_link(self):
        running = TrainingSession.objects.create(label="Day 1", started_at=timezone.now())
        out = links()
        self.assertIn("Running now:", out)
        self.assertIn(f"https://demo-u-k7m2qx.example.test/session/{running.pk}", out)

    def test_none_running_lists_the_set_up_ones(self):
        set_up = TrainingSession.objects.create(label="Thursday")
        out = links()
        self.assertIn("No session is running.", out)
        self.assertIn(f"/session/{set_up.pk}    Thursday", out)

    def test_an_ended_session_is_never_listed(self):
        ended = TrainingSession.objects.create(label="Old", started_at=timezone.now(),
                                               ended_at=timezone.now())
        self.assertNotIn(f"/session/{ended.pk}", links())

    def test_an_address_keeps_its_own_scheme(self):
        TrainingSession.objects.create(label="Day 1", started_at=timezone.now())
        self.assertIn("http://localhost/session/", links("http://localhost/"))
