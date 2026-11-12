"""athlete_progress.py — My Recent Progress: an athlete's own trends over a range they choose
(spec 10, Phase 4).

WHY: an athlete wants to see whether they're getting faster or stronger, from their own
sets only. The coach's Analytics already knows how, but it's coach-only; this answers the
same question for one athlete, about themselves.

For a range of whole days (the school's time zone, both ends included):
  sessions   calendar days they were planned in (any of their programs), and how many
             sessions they lifted in.
  sets       sets done against the sets those days prescribed.
  movements  one row per movement they lifted in the range (two programs, one row):
             heaviest load, fastest rep, today's max (the one their weights come from,
             never recomputed here), and a trend of top sets.

THE TREND STAYS SMALL HOWEVER LONG THE RANGE (Devin, 2026-11-11): at most 14 points. The
step is the smallest on the ladder session -> week -> month -> quarter -> year whose number
of periods the range touches is 14 or fewer. A session point is that session's top set
(its heaviest set, by measured sets first); a longer period's point is the best top set in
it. A period the range only partly covers is marked partial. Periods with no lifting have
no point (nothing to draw).

Counts leave out false sets and coach adjustments, the daily report's own rule, and only
ended sessions count, as in the reports.
"""
from datetime import date, datetime, time, timedelta

from django.db.models import Max
from django.db.models.functions import Coalesce
from django.utils import timezone

from ..models import AthleteReferenceMax, Rep, ScheduledSession, Set, TrainingSession
from .lifting_math import normalize_to_single
from .plan_resolution import movements_for_athlete

MAX_POINTS = 14
LADDER = ('session', 'week', 'month', 'quarter', 'year')


class BadRange(ValueError):
    """From after To, or a date that isn't one."""


def parse_range(raw_from, raw_to, today=None):
    """(from, to) as dates. Missing ends default to the last 30 days, today included."""
    today = today or timezone.localdate()
    try:
        to = date.fromisoformat(raw_to) if raw_to else today
        start = date.fromisoformat(raw_from) if raw_from else to - timedelta(days=29)
    except ValueError as exc:
        raise BadRange('Dates are YYYY-MM-DD.') from exc
    if start > to:
        raise BadRange('From is after To.')
    return start, to


def _bounds(start, to):
    tz = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(start, time.min), tz),
            timezone.make_aware(datetime.combine(to + timedelta(days=1), time.min), tz))


def _sets_in_range(athlete, start, to):
    low, high = _bounds(start, to)
    return (Set.objects
            .filter(athlete=athlete, is_coach_adjustment=False, is_false_set=False,
                    session__ended_at__isnull=False)
            .annotate(when=Coalesce('session__started_at', 'session__ended_at'))
            .filter(when__gte=low, when__lt=high)
            .select_related('exercise', 'session')
            .order_by('when', 'started_at', 'id'))


# ── periods ──

def _period(step, day):
    """The calendar period a day falls in: (first day, last day)."""
    if step == 'week':
        first = day - timedelta(days=day.weekday())          # weeks start Monday
        return first, first + timedelta(days=6)
    if step == 'month':
        first = day.replace(day=1)
        nxt = (first.replace(year=first.year + 1, month=1) if first.month == 12
               else first.replace(month=first.month + 1))
        return first, nxt - timedelta(days=1)
    if step == 'quarter':
        q = (day.month - 1) // 3
        first = date(day.year, 3 * q + 1, 1)
        last_month = 3 * q + 3
        nxt = date(day.year + 1, 1, 1) if last_month == 12 else date(day.year, last_month + 1, 1)
        return first, nxt - timedelta(days=1)
    return date(day.year, 1, 1), date(day.year, 12, 31)       # year


def _periods_touched(step, start, to):
    count, day = 0, start
    while day <= to:
        count += 1
        day = _period(step, day)[1] + timedelta(days=1)
    return count


def choose_step(start, to, sessions_lifted):
    """The smallest step on the ladder that gives MAX_POINTS points or fewer."""
    if sessions_lifted <= MAX_POINTS:
        return 'session'
    for step in LADDER[1:]:
        if _periods_touched(step, start, to) <= MAX_POINTS:
            return step
    return 'year'


def _label(step, first):
    if step in ('session', 'week'):
        return f"{first:%b} {first.day}"
    if step == 'month':
        return f"{first:%b}"
    if step == 'quarter':
        return f"Q{(first.month - 1) // 3 + 1} '{first:%y}"
    return f"{first.year}"


# ── top sets ──

def _better(a, b):
    """The better top set: heavier, then measured, then faster."""
    def key(s):
        return (s.weight_lbs or 0, s.avg_velocity is not None, s.avg_velocity or 0)
    return a if b is None or key(a) >= key(b) else b


def _trend(sets, step, start, to):
    by_session = {}
    for s in sets:
        by_session[s.session_id] = _better(s, by_session.get(s.session_id))
    points = {}
    for s in by_session.values():
        day = timezone.localdate(s.when)
        if step == 'session':
            key, first, last = (day, s.session_id), day, day
        else:
            first, last = _period(step, day)
            key = first
        best = points.get(key)
        points[key] = (first, last, _better(s, best[2] if best else None))
    out = []
    for key in sorted(points, key=lambda k: (k if isinstance(k, date) else k[0], 0 if isinstance(k, date) else k[1])):
        first, last, top = points[key]
        out.append({'date': first.isoformat(), 'label': _label(step, first), 'bucket': step,
                    'partial': step != 'session' and (first < start or last > to),
                    'top_set_avg_velocity': top.avg_velocity, 'load_lbs': top.weight_lbs})
    return out


def _max_today(athlete, exercise_id):
    row = (AthleteReferenceMax.objects.filter(athlete=athlete, exercise_id=exercise_id)
           .order_by('-recorded_at', '-id').first())
    if row is None:
        return None
    return {'weight_lbs': normalize_to_single(row.reference_weight_lbs, row.rep_basis), 'source': row.source}


# ── planned ──

def _planned(athlete, start, to, lifted_sessions):
    """Calendar days planned in the range (two programs sharing a session are one day), and
    the sets those days prescribe. A session lifted that wasn't on the calendar (a quick
    session) adds its own prescription to the sets planned."""
    days = (ScheduledSession.objects
            .filter(training_program__training_group__in=athlete.training_groups.all(),
                    date__gte=start, date__lte=to)
            .select_related('training_program_workout', 'session')
            .prefetch_related('training_program_workout__exercises'))
    seen, sets_planned, day_count = set(), 0, 0
    for day in days:
        key = ('s', day.session_id) if day.session_id else ('d', day.pk)
        if key in seen:
            continue
        seen.add(key)
        day_count += 1
        if day.session_id:
            sets_planned += sum(m['planned_sets'] or 0 for m in movements_for_athlete(athlete, day.session))
        elif day.training_program_workout:
            sets_planned += sum(row.sets or 0 for row in day.training_program_workout.exercises.all())
    for session in lifted_sessions:
        if ('s', session.pk) not in seen:
            sets_planned += sum(m['planned_sets'] or 0 for m in movements_for_athlete(athlete, session))
    return day_count, sets_planned


def progress_for(athlete, start, to):
    sets = list(_sets_in_range(athlete, start, to))
    lifted = {s.session_id: s.session for s in sets}
    days_planned, sets_planned = _planned(athlete, start, to, lifted.values())

    by_exercise, order = {}, []
    for s in sets:
        if s.exercise_id not in by_exercise:
            by_exercise[s.exercise_id] = []
            order.append(s.exercise_id)
        by_exercise[s.exercise_id].append(s)
    fastest = dict(Rep.objects.filter(set__in=[s.pk for s in sets]).values('set__exercise_id')
                   .annotate(best=Max('mean_velocity')).values_list('set__exercise_id', 'best'))

    movements = []
    for exercise_id in sorted(order, key=lambda e: by_exercise[e][0].exercise.name):
        rows = by_exercise[exercise_id]
        step = choose_step(start, to, len({s.session_id for s in rows}))
        trend = _trend(rows, step, start, to)
        speeds = [p['top_set_avg_velocity'] for p in trend if p['top_set_avg_velocity'] is not None]
        loads = [s.weight_lbs for s in rows if s.weight_lbs]
        movements.append({
            'name': rows[0].exercise.name,
            'top_load_lbs': max(loads) if loads else None,
            'trend': trend,
            'change': round(speeds[-1] - speeds[0], 3) if len(speeds) > 1 else None,
            'best_rep_velocity': fastest.get(exercise_id),
            'max': _max_today(athlete, exercise_id),
        })
    return {
        'range': {'from': start.isoformat(), 'to': to.isoformat()},
        'sessions': {'done': len(lifted), 'planned': days_planned},
        'sets': {'done': len(sets), 'planned': sets_planned},
        'movements': movements,
    }


def reports_in_range(athlete, start, to):
    """The daily reports of the ended sessions this athlete lifted in, inside the range,
    oldest first: what Download my report (PDF) is made from."""
    from ..models import DailyReport
    low, high = _bounds(start, to)
    sessions = set(_sets_in_range(athlete, start, to).values_list('session_id', flat=True))
    return list(DailyReport.objects.filter(session_id__in=sessions)
                .annotate(when=Coalesce('session__started_at', 'session__ended_at'))
                .filter(when__gte=low, when__lt=high).order_by('when', 'id'))
