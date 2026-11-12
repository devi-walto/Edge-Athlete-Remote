"""Tests for an athlete's Home route (spec 10, Phase 0).

WHY THESE EXIST: Home is the first thing an online athlete sees. It must list only
their own groups' days, say a session is live exactly when the Join button would let
them in, count their recent sets the same way the daily report does, never name
another athlete, refuse everyone but an athlete, and not slow down as the calendar
fills up.
"""
import datetime
import json

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (Athlete, CoachProfile, Exercise, ScheduledSession, SessionParticipation, Set,
                     TrainingGroup, TrainingProgram, TrainingProgramExercise, TrainingProgramWorkout,
                     TrainingSession)
from .services.session_join import JoinRefused, join

User = get_user_model()
URL = '/api/athlete/home/'
TODAY = timezone.localdate()


def athlete(name, username, *groups):
    person = Athlete.objects.create(name=name, user=User.objects.create_user(username, password='x-Unique-2026!'))
    person.training_groups.add(*groups)
    return person


def program(group, workout_name='Day 1 — Lower', movements=('Back Squat', 'Bench Press'), sets=3):
    plan = TrainingProgram.objects.create(training_group=group, name=f'{group.name} plan', start_date=TODAY)
    workout = TrainingProgramWorkout.objects.create(training_program=plan, name=workout_name, position=1)
    for i, name in enumerate(movements):
        TrainingProgramExercise.objects.create(training_program_workout=workout, position=i,
                                               exercise=Exercise.objects.get_or_create(name=name)[0],
                                               sets=sets, reps=5, target_percent=70)
    return plan, workout


def day(plan, workout, offset, session=None):
    return ScheduledSession.objects.create(training_program=plan, training_program_workout=workout,
                                           date=TODAY + datetime.timedelta(days=offset), session=session)


@override_settings(EA_DEPLOYMENT='remote')
class HomeTests(APITestCase):
    def setUp(self):
        self.varsity = TrainingGroup.objects.create(name='Varsity')
        self.receivers = TrainingGroup.objects.create(name='Receivers')
        self.other = TrainingGroup.objects.create(name='JV')
        self.riley = athlete('Riley Brooks', 'riley', self.varsity)
        self.both = athlete('Jordan Lee', 'jordan', self.varsity, self.receivers)
        self.stranger = athlete('Casey Morgan', 'casey', self.other)
        self.v_plan, self.v_workout = program(self.varsity, 'Day 1 — Lower')
        self.r_plan, self.r_workout = program(self.receivers, 'Routes + Speed', ('Sprint',), sets=2)
        self.j_plan, self.j_workout = program(self.other, 'JV Day', ('Deadlift',))

    def home(self, person):
        self.client.force_authenticate(person.user if person else None)
        return self.client.get(URL)

    # ── coming up ──

    def test_one_group_sees_its_future_days_and_nobody_elses(self):
        day(self.v_plan, self.v_workout, 1)
        day(self.v_plan, self.v_workout, -1)          # yesterday: gone
        day(self.j_plan, self.j_workout, 1)           # another group's day
        reply = self.home(self.riley)
        self.assertEqual(reply.status_code, 200, reply.data)
        coming = reply.data['coming_up']
        self.assertEqual(len(coming), 1)
        self.assertEqual(coming[0]['groups'], ['Varsity'])
        self.assertEqual(coming[0]['title'], 'Day 1 — Lower')
        self.assertEqual(coming[0]['movements'], ['Back Squat', 'Bench Press'])
        self.assertIsNone(coming[0]['session_id'])

    def test_two_groups_see_both_and_a_shared_session_is_one_entry(self):
        shared = TrainingSession.objects.create(label='Thursday')
        day(self.v_plan, self.v_workout, 2, shared)
        day(self.r_plan, self.r_workout, 2, shared)
        day(self.r_plan, self.r_workout, 3)
        coming = self.home(self.both).data['coming_up']
        self.assertEqual(len(coming), 2)
        self.assertEqual(coming[0]['groups'], ['Varsity', 'Receivers'])
        self.assertEqual(coming[0]['movements'], ['Back Squat', 'Bench Press', 'Sprint'])
        self.assertEqual(coming[0]['session_id'], shared.pk)
        self.assertEqual(coming[1]['groups'], ['Receivers'])

    def test_an_ended_day_is_left_out_and_a_set_up_day_carries_its_session(self):
        ended = TrainingSession.objects.create(label='Done', started_at=timezone.now(), ended_at=timezone.now())
        set_up = TrainingSession.objects.create(label='Tomorrow')
        day(self.v_plan, self.v_workout, 0, ended)
        day(self.v_plan, self.v_workout, 1, set_up)
        coming = self.home(self.riley).data['coming_up']
        self.assertEqual([c['session_id'] for c in coming], [set_up.pk])

    def test_soonest_first_and_at_most_ten(self):
        for offset in range(14, 0, -1):
            day(self.v_plan, self.v_workout, offset)
        coming = self.home(self.riley).data['coming_up']
        self.assertEqual(len(coming), 10)
        self.assertEqual(coming[0]['date'], (TODAY + datetime.timedelta(days=1)).isoformat())

    # ── live ──

    def live_matches_join(self, person, session):
        live = self.home(person).data['live']
        try:
            join(session.pk, person)
            joinable = True
        except JoinRefused:
            joinable = False
        return live, joinable

    def test_live_is_set_exactly_when_join_would_let_them_in(self):
        running = TrainingSession.objects.create(label='Day 2 — Pull', started_at=timezone.now())
        SessionParticipation.objects.create(session=running, training_program=self.v_plan,
                                            training_program_workout=self.v_workout)
        live, joinable = self.live_matches_join(self.riley, running)
        self.assertTrue(joinable)
        self.assertEqual(live['session_id'], running.pk)
        self.assertEqual(live['title'], 'Day 2 — Pull')
        self.assertEqual(live['groups'], ['Varsity'])
        self.assertEqual(live['movements'], ['Back Squat', 'Bench Press'])

        live, joinable = self.live_matches_join(self.stranger, running)
        self.assertFalse(joinable)
        self.assertIsNone(live)

    def test_a_quick_session_they_were_put_on_is_live(self):
        quick = TrainingSession.objects.create(label='Quick Training Session', started_at=timezone.now())
        quick.athletes.add(self.stranger)
        live, joinable = self.live_matches_join(self.stranger, quick)
        self.assertTrue(joinable)
        self.assertEqual(live['session_id'], quick.pk)
        self.assertEqual(live['groups'], [])

    def test_not_started_or_ended_is_not_live(self):
        not_started = TrainingSession.objects.create(label='Later')
        not_started.athletes.add(self.riley)
        ended = TrainingSession.objects.create(label='Over', started_at=timezone.now(), ended_at=timezone.now())
        ended.athletes.add(self.riley)
        for session in (not_started, ended):
            live, joinable = self.live_matches_join(self.riley, session)
            self.assertFalse(joinable)
            self.assertIsNone(live)

    # ── recent ──

    def ended_session(self, label, days_ago, plan=None, workout=None):
        when = timezone.now() - datetime.timedelta(days=days_ago)
        session = TrainingSession.objects.create(label=label, started_at=when, ended_at=when + datetime.timedelta(hours=1))
        if plan:
            SessionParticipation.objects.create(session=session, training_program=plan, training_program_workout=workout)
        return session

    def lift(self, person, session, count, false_sets=0, adjustments=0):
        squat = Exercise.objects.get(name='Back Squat')
        session.athletes.add(person)          # joining puts them on the roster
        n = 0
        for flags in [{}] * count + [{'is_false_set': True}] * false_sets + [{'is_coach_adjustment': True}] * adjustments:
            n += 1
            Set.objects.create(session=session, athlete=person, exercise=squat, set_number=n,
                               ended_at=session.ended_at, **flags)

    def test_recent_is_the_last_five_they_lifted_in_newest_first(self):
        for i in range(7):
            self.lift(self.riley, self.ended_session(f'Day {i}', 10 - i, self.v_plan, self.v_workout), 2)
        sat_out = self.ended_session('Sat out', 0, self.v_plan, self.v_workout)
        sat_out.athletes.add(self.riley)                          # on it, never lifted
        recent = self.home(self.riley).data['recent']
        self.assertEqual([r['title'] for r in recent], ['Day 6', 'Day 5', 'Day 4', 'Day 3', 'Day 2'])

    def test_recent_counts_match_the_daily_report(self):
        from .services.session_completion import _snapshot as build_report_snapshot
        session = self.ended_session('Counted', 1, self.v_plan, self.v_workout)
        self.lift(self.riley, session, 4, false_sets=1, adjustments=2)
        row = self.home(self.riley).data['recent'][0]
        report = build_report_snapshot(session)
        theirs = next(b for b in report['athletes'] if b['athlete']['id'] == self.riley.pk)
        self.assertEqual(row['sets_done'], len([s for s in theirs['sets'] if not s['is_false_set']]))
        self.assertEqual(row['sets_done'], 4)
        self.assertEqual(row['sets_planned'], 6)        # 2 movements x 3 sets
        self.assertEqual(row['date'], timezone.localdate(session.started_at).isoformat())

    # ── privacy and doors ──

    def test_no_other_athlete_is_named_anywhere(self):
        shared = TrainingSession.objects.create(label='Together', started_at=timezone.now())
        SessionParticipation.objects.create(session=shared, training_program=self.v_plan, training_program_workout=self.v_workout)
        shared.athletes.add(self.stranger, self.both)
        day(self.v_plan, self.v_workout, 1, shared)
        done = self.ended_session('Before', 1, self.v_plan, self.v_workout)
        self.lift(self.riley, done, 1)
        self.lift(self.both, done, 1)
        body = json.dumps(self.home(self.riley).data)
        self.assertIn('Riley Brooks', body)
        for other in Athlete.objects.exclude(pk=self.riley.pk):
            self.assertNotIn(other.name, body)
            self.assertNotIn(other.name.split()[0], body)
        self.assertNotIn('JV', body)

    def test_a_coach_is_refused_and_no_login_is_unauthorised(self):
        coach = User.objects.create_user('coach', password='x-Unique-2026!')
        CoachProfile.objects.get_or_create(user=coach)
        self.client.force_authenticate(coach)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, 401)

    @override_settings(EA_DEPLOYMENT='local')
    def test_a_gym_box_has_no_such_page(self):
        self.assertEqual(self.home(self.riley).status_code, 404)

    def test_a_fixed_number_of_queries_however_many_days(self):
        def count(days):
            ScheduledSession.objects.all().delete()
            for offset in range(1, days + 1):
                day(self.v_plan, self.v_workout, offset)
                day(self.r_plan, self.r_workout, offset)
            self.client.force_authenticate(self.both.user)
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual(self.client.get(URL).status_code, 200)
            return len(queries)
        count(1)                               # the first request does one-off lookups
        self.assertEqual(count(2), count(9))
