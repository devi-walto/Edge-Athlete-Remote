"""Tests for My Recent Progress and its PDF (spec 10, Phase 4).

WHY THESE EXIST: an athlete's trends must count only their own sets inside the range (false
sets left out) and agree with the daily reports; the chart must stay at 14 bars or fewer
however long the range, on the right step; the max must be the one their weights come
from; and the PDF must hold nobody's sets but theirs.
"""
import datetime

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import (AthleteReferenceMax, CoachProfile, Exercise, Rep, ScheduledSession, SessionParticipation, Set,
                     TrainingGroup, TrainingSession)
from .services.athlete_progress import choose_step
from .services.plan_resolution import current_reference_max
from .services.session_completion import _snapshot, end_session
from .test_athlete_home import User, athlete, program

URL = '/api/athlete/progress/'
PDF = '/api/athlete/progress/report/'
TODAY = timezone.localdate()


@override_settings(EA_DEPLOYMENT='remote')
class ProgressTests(APITestCase):
    def setUp(self):
        self.varsity = TrainingGroup.objects.create(name='Varsity')
        self.receivers = TrainingGroup.objects.create(name='Receivers')
        self.riley = athlete('Riley Brooks', 'riley', self.varsity, self.receivers)
        self.jordan = athlete('Jordan Lee', 'jordan', self.varsity)
        self.v_plan, self.v_workout = program(self.varsity, 'Lower', ('Back Squat', 'Bench Press'), sets=3)
        self.r_plan, self.r_workout = program(self.receivers, 'Speed', ('Back Squat',), sets=2)
        self.squat = Exercise.objects.get(name='Back Squat')
        self.bench = Exercise.objects.get(name='Bench Press')

    def session(self, days_ago, lifts, person=None, plan=None, workout=None, end=True):
        """A session `days_ago` days back; lifts = [(exercise, weight, speed or None, flags)]."""
        when = timezone.make_aware(datetime.datetime.combine(TODAY - datetime.timedelta(days=days_ago), datetime.time(15)))
        s = TrainingSession.objects.create(label=f'Day -{days_ago}', started_at=when)
        SessionParticipation.objects.create(session=s, training_program=plan or self.v_plan,
                                            training_program_workout=workout or self.v_workout)
        person = person or self.riley
        s.athletes.add(person)
        for n, (exercise, weight, speed, *flags) in enumerate(lifts, 1):
            a = Set.objects.create(session=s, athlete=person, exercise=exercise, set_number=n, weight_lbs=weight,
                                   reps_completed=3, avg_velocity=speed, started_at=when + datetime.timedelta(minutes=n),
                                   ended_at=when + datetime.timedelta(minutes=n, seconds=30), **(flags[0] if flags else {}))
            if speed:
                for r in range(1, 4):
                    Rep.objects.create(set=a, rep_number=r, timestamp=when, mean_velocity=speed + .05 * (3 - r),
                                       peak_velocity=1, duration_ms=800, velocity_color='green')
        if end:
            end_session(s.pk, ended_at=when + datetime.timedelta(hours=1))
            s.refresh_from_db()
        return s

    def get(self, params=None, person=None, url=URL):
        self.client.force_authenticate((person or self.riley).user)
        return self.client.get(url, params or {})

    def range(self, days):
        return {'from': (TODAY - datetime.timedelta(days=days - 1)).isoformat(), 'to': TODAY.isoformat()}

    # ── counts ──

    def test_only_their_own_sets_inside_the_range_false_sets_out_matching_the_reports(self):
        inside = self.session(3, [(self.squat, 225, .6), (self.squat, 235, .55), (self.squat, 245, .5, {'is_false_set': True}),
                                  (self.bench, 165, None)])
        self.session(40, [(self.squat, 315, .4)])                                     # outside 30 days
        self.session(2, [(self.squat, 405, .3)], person=self.jordan)                  # someone else
        self.session(1, [(self.squat, 500, .2)], end=False)                           # still running
        data = self.get(self.range(30)).data
        self.assertEqual(data['sets']['done'], 3)
        theirs = next(a for a in _snapshot(inside)['athletes'] if a['athlete']['id'] == self.riley.pk)
        self.assertEqual(data['sets']['done'], len([s for s in theirs['sets'] if not s['is_false_set']]))
        squat = next(m for m in data['movements'] if m['name'] == 'Back Squat')
        self.assertEqual(squat['top_load_lbs'], 235)                                  # the false 245 and others' 405 left out
        self.assertAlmostEqual(squat['best_rep_velocity'], .7)                        # fastest rep of a counted set
        self.assertEqual(data['sessions']['done'], 1)

    def test_planned_counts_their_calendar_days_and_the_sets_they_prescribe(self):
        for offset in (1, 3, 5):
            ScheduledSession.objects.create(training_program=self.v_plan, training_program_workout=self.v_workout,
                                            date=TODAY - datetime.timedelta(days=offset))
        lifted = self.session(3, [(self.squat, 225, .6)])
        ScheduledSession.objects.filter(date=TODAY - datetime.timedelta(days=3)).update(session=lifted)
        data = self.get(self.range(30)).data
        self.assertEqual(data['sessions'], {'done': 1, 'planned': 3})
        self.assertEqual(data['sets']['planned'], 3 * 6)                              # 2 movements x 3 sets, 3 days

    def test_two_programs_one_row_per_movement(self):
        self.session(4, [(self.squat, 225, .6)])
        self.session(2, [(self.squat, 185, .7)], plan=self.r_plan, workout=self.r_workout)
        rows = [m['name'] for m in self.get(self.range(30)).data['movements']]
        self.assertEqual(rows.count('Back Squat'), 1)
        squat = next(m for m in self.get(self.range(30)).data['movements'] if m['name'] == 'Back Squat')
        self.assertEqual(len(squat['trend']), 2)

    # ── the trend ──

    def test_30_days_is_one_point_per_session_each_its_top_set(self):
        self.session(8, [(self.squat, 225, .62), (self.squat, 245, .51)])
        self.session(4, [(self.squat, 235, .58)])
        trend = self.get(self.range(30)).data['movements'][0]['trend']
        self.assertEqual([(p['bucket'], p['load_lbs'], p['top_set_avg_velocity']) for p in trend],
                         [('session', 245, .51), ('session', 235, .58)])
        self.assertFalse(any(p['partial'] for p in trend))
        squat = self.get(self.range(30)).data['movements'][0]
        self.assertAlmostEqual(squat['change'], .07)                                  # last minus first

    def test_never_more_than_14_points_on_the_smallest_step_that_fits(self):
        for d in range(0, 90, 3):                                                     # 30 sessions in 90 days
            self.session(d, [(self.squat, 200 + d, .5 + d / 1000)])
        trend = self.get(self.range(90)).data['movements'][0]['trend']
        self.assertLessEqual(len(trend), 14)
        self.assertEqual({p['bucket'] for p in trend}, {'week'})
        self.assertTrue(trend[0]['partial'] or trend[-1]['partial'])                  # the range cuts a week
        # a week's point is the best top set in it: the heaviest
        first_week = [200 + d for d in range(0, 90, 3)
                      if TODAY - datetime.timedelta(days=d) >= datetime.date.fromisoformat(trend[-1]['date'])]
        self.assertEqual(trend[-1]['load_lbs'], max(first_week))

    def test_the_ladder(self):
        day = datetime.date
        self.assertEqual(choose_step(day(2026, 10, 1), day(2026, 10, 30), 12), 'session')
        self.assertEqual(choose_step(day(2026, 8, 3), day(2026, 10, 31), 30), 'week')      # 13 weeks
        self.assertEqual(choose_step(day(2025, 11, 1), day(2026, 10, 31), 100), 'month')   # 12 months
        self.assertEqual(choose_step(day(2025, 3, 1), day(2026, 10, 31), 200), 'quarter')  # 20 months
        self.assertEqual(choose_step(day(2022, 11, 1), day(2026, 10, 31), 400), 'year')    # 4 years

    def test_a_20_month_range_gives_8_quarter_points(self):
        start, end = datetime.date(2025, 3, 1), datetime.date(2026, 10, 31)
        day = start
        while day <= end:                                                             # one session every 2 weeks
            self.session((TODAY - day).days, [(self.squat, 225, .6)])
            day += datetime.timedelta(days=14)
        trend = self.get({'from': start.isoformat(), 'to': end.isoformat()}).data['movements'][0]['trend']
        self.assertEqual(len(trend), 8)
        self.assertEqual({p['bucket'] for p in trend}, {'quarter'})
        self.assertEqual(trend[0]['label'], "Q1 '25")
        self.assertTrue(trend[0]['partial'])                                          # Q1 starts Jan, range starts Mar
        self.assertTrue(trend[-1]['partial'])                                         # Q4 runs to Dec, the range stops Oct 31
        self.assertFalse(any(p['partial'] for p in trend[1:-1]))

    # ── the max ──

    def test_max_is_todays_reference_max_whatever_the_range(self):
        self.session(4, [(self.squat, 225, .6)])                                      # ending writes an estimated max
        AthleteReferenceMax.objects.create(athlete=self.riley, exercise=self.squat, reference_weight_lbs=300,
                                           rep_basis=1, source='manual')
        squat = self.get(self.range(30)).data['movements'][0]
        self.assertEqual(squat['max'], {'weight_lbs': current_reference_max(self.riley.pk, self.squat.pk), 'source': 'manual'})
        self.assertEqual(squat['max']['weight_lbs'], 300)
        older = self.get({'from': (TODAY - datetime.timedelta(days=10)).isoformat(),
                          'to': (TODAY - datetime.timedelta(days=3)).isoformat()}).data['movements'][0]
        self.assertEqual(older['max']['weight_lbs'], 300)                             # today's, not the range's

    def test_no_max_is_null(self):
        self.session(4, [(self.bench, None, None)])                                   # typed in, no load: nothing estimated
        bench = self.get(self.range(30)).data['movements'][0]
        self.assertIsNone(bench['max'])

    # ── the range ──

    def test_from_after_to_and_bad_dates_are_refused(self):
        self.assertEqual(self.get({'from': '2026-11-10', 'to': '2026-11-01'}).status_code, 400)
        self.assertEqual(self.get({'from': 'yesterday', 'to': '2026-11-01'}).status_code, 400)

    def test_no_range_means_the_last_30_days(self):
        self.assertEqual(self.get().data['range'], self.range(30))

    # ── the PDF ──

    def test_the_pdf_holds_only_their_sets(self):
        shared = self.session(3, [(self.squat, 225, .6)], end=False)
        Set.objects.create(session=shared, athlete=self.jordan, exercise=self.squat, set_number=9, weight_lbs=405,
                           reps_completed=1, avg_velocity=.2)
        shared.athletes.add(self.jordan)
        end_session(shared.pk)
        reply = self.get(self.range(30), url=PDF)
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(reply['Content-Type'], 'application/pdf')
        body = reply.content.decode('latin-1')
        self.assertIn('Riley Brooks', body)
        self.assertIn('225', body)
        self.assertNotIn('Jordan', body)
        self.assertNotIn('405', body)

    def test_the_pdf_in_kilograms(self):
        self.session(3, [(self.squat, 225, .6)])
        body = self.get({**self.range(30), 'unit': 'kg'}, url=PDF).content.decode('latin-1')
        self.assertIn('102 kg', body)                                                 # 225 lb = 102.06 kg -> 102
        self.assertNotIn('225 lbs', body)

    # ── doors ──

    def test_doors(self):
        coach = User.objects.create_user('coach2', password='x-Unique-2026!')
        CoachProfile.objects.get_or_create(user=coach)
        for url in (URL, PDF):
            self.client.force_authenticate(coach)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.client.force_authenticate(None)
            self.assertEqual(self.client.get(url).status_code, 401)

    @override_settings(EA_DEPLOYMENT='local')
    def test_a_gym_box_has_no_such_page(self):
        for url in (URL, PDF):
            self.assertEqual(self.get(url=url).status_code, 404)
