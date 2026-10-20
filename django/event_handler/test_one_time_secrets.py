"""Tests for the shared one-time secrets (spec 14, Phase 0).

WHY THESE EXIST: setup codes, login links and (next) sensor claim codes all depend on
these rules being right: a secret works once, until it expires; a newer one cancels
the older; every failure looks the same; nothing readable is stored. They are tested
here once, against a real table (AthleteLoginLink), with both kinds of secret.
"""
import inspect
import threading
import time
from datetime import timedelta
from unittest import mock

from django.db import close_old_connections, connections, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from . import coach_auth
from .models import Athlete, AthleteLoginLink
from .services import login_links, one_time_secrets as ots

LIFETIME = timedelta(minutes=15)


def issue(athlete, style=ots.CODE):
    return ots.issue(AthleteLoginLink, style, LIFETIME, owner={'athlete': athlete})


class CodeTests(TestCase):
    def test_a_code_is_8_characters_with_no_look_alikes(self):
        for _ in range(50):
            code = ots.new_code()
            self.assertEqual(len(code), 8)
            self.assertFalse(set(code) & set('0O1IL'))

    def test_a_code_is_shown_in_two_halves(self):
        self.assertEqual(ots.format_code('k7mq2xpr'), 'K7MQ-2XPR')

    def test_typing_ignores_case_spaces_and_dashes(self):
        self.assertEqual(ots.normalize_code(' k7mq - 2xpr '), 'K7MQ2XPR')


class OneTimeRowTests(TestCase):
    def setUp(self):
        self.athlete = Athlete.objects.create(name='Riley Brooks')

    def test_a_code_is_found_however_it_is_typed(self):
        text, row = issue(self.athlete)
        typed = f"  {text.lower().replace('-', ' - ')} "
        self.assertEqual(ots.find(AthleteLoginLink, ots.CODE, typed), row)

    def test_a_link_is_found(self):
        text, row = issue(self.athlete, ots.LINK)
        self.assertEqual(ots.find(AthleteLoginLink, ots.LINK, text), row)

    def test_every_failure_gives_the_same_answer(self):
        used_text, used = issue(Athlete.objects.create(name='A'))
        ots.mark_used(used)
        expired_text, expired = issue(Athlete.objects.create(name='B'))
        AthleteLoginLink.objects.filter(pk=expired.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1))
        cancelled_text, _ = issue(Athlete.objects.create(name='C'))
        issue(Athlete.objects.get(name='C'))                     # cancels the first
        good_text, _ = issue(self.athlete)
        wrong_text = good_text[:5] + ('A' if good_text[5] != 'A' else 'B') + good_text[6:]
        for text in (used_text, expired_text, cancelled_text, wrong_text, 'ZZZZ-ZZZZ', '', None):
            self.assertIsNone(ots.find(AthleteLoginLink, ots.CODE, text), text)

    def test_a_newer_one_cancels_the_older(self):
        first, _ = issue(self.athlete)
        second, _ = issue(self.athlete)
        self.assertIsNone(ots.find(AthleteLoginLink, ots.CODE, first))
        self.assertIsNotNone(ots.find(AthleteLoginLink, ots.CODE, second))

    def test_someone_elses_newer_code_cancels_nothing_of_mine(self):
        mine, _ = issue(self.athlete)
        issue(Athlete.objects.create(name='Jordan Lee'))
        self.assertIsNotNone(ots.find(AthleteLoginLink, ots.CODE, mine))

    def test_nothing_readable_is_stored(self):
        for style in (ots.CODE, ots.LINK):
            text, row = issue(self.athlete, style)
            row.refresh_from_db()
            secret = (ots.normalize_code(text)[4:] if style == ots.CODE
                      else text.partition('.')[2])
            stored = ' '.join(str(getattr(row, f.attname)) for f in row._meta.fields)
            self.assertNotIn(secret, stored)
            self.assertTrue(row.token_hash.startswith('pbkdf2_') or '$' in row.token_hash)

    def test_an_unknown_lookup_takes_as_long_to_refuse(self):
        issue(self.athlete)
        with mock.patch.object(ots, 'opens', wraps=ots.opens) as opens:
            self.assertIsNone(ots.find(AthleteLoginLink, ots.CODE, 'ZZZZ-ZZZZ'))
        self.assertEqual(opens.call_count, 1)   # a hash was still checked

    def test_an_archived_athletes_link_stops_working(self):
        text, _ = issue(self.athlete, ots.LINK)
        self.athlete.is_active = False
        self.athlete.save()
        self.assertIsNone(ots.find(AthleteLoginLink, ots.LINK, text))


class TwoAtOnceTests(TransactionTestCase):
    def test_two_uses_at_the_same_moment_only_one_wins(self):
        _, row = issue(Athlete.objects.create(name='Riley Brooks'))
        wins, ready = [], threading.Barrier(2)

        def use():
            close_old_connections()
            try:
                ready.wait()
                with transaction.atomic():
                    locked = ots.lock_if_still_works(AthleteLoginLink, row)
                    if locked is not None:
                        time.sleep(0.2)       # hold the lock while the other one waits
                        ots.mark_used(locked)
                        wins.append(True)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=use) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(wins, [True])


class OneHomeTests(TestCase):
    """The making and checking of secrets lives only in one_time_secrets.py."""

    def test_no_copy_left_in_the_setup_code_or_login_links(self):
        for module in (coach_auth, login_links):
            source = inspect.getsource(module)
            for copy in ('import secrets', 'django.contrib.auth.hashers', 'secrets.choice',
                         'token_urlsafe'):
                self.assertNotIn(copy, source, f'{copy} in {module.__name__}')
