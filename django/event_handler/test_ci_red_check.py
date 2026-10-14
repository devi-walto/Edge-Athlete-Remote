"""A test that fails on purpose. Never merge this.

Why this file exists: it proves a red check blocks a pull request from merging
(spec 05 Phase 1). Its pull request is closed and the branch deleted afterwards.
"""
from django.test import SimpleTestCase


class RedCheckTests(SimpleTestCase):
    def test_fails_on_purpose(self):
        self.assertEqual(1, 2, "this test fails on purpose to prove CI blocks merging")
