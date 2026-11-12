"""athlete_home.py — what an athlete's Home page shows: what's next, what's live, what
they did lately (spec 10, Phase 0).

WHY: after signing in, an online athlete had nowhere to land except a page telling them
to go find the session link their coach sent. Home answers the three questions an
athlete opens the app with, from their own groups only:

  coming_up  the calendar days of every Training Program whose group they're in, from
             today on, whose session hasn't ended. Soonest first, at most ten. Two
             programs that share one session on the same date are one entry.
  live       the session that's running right now AND that they may join, decided by
             the same may_join() the Join button uses, so the two can never disagree.
  recent     their last five ended sessions they actually lifted in, newest first, with
             sets done (false sets and coach adjustments left out, the same count the
             daily report keeps) against the sets their plan prescribed that day.

Nothing here names another athlete, or a group the athlete isn't in. Loads aren't sent:
the rack screen works those out.
"""
from django.db.models import Count, Max, Q
from django.utils import timezone

from ..models import ScheduledSession, Set, TrainingSession
from .plan_resolution import movements_for_athlete
from .session_join import may_join

COMING_UP_LIMIT = 10
RECENT_LIMIT = 5


def _first_name(name):
    return (name or '').split(' ')[0]


def _coming_up(athlete, group_ids, today):
    days = (ScheduledSession.objects
            .filter(training_program__training_group_id__in=group_ids, date__gte=today)
            .exclude(session__ended_at__isnull=False)
            .select_related('training_program__training_group', 'training_program_workout', 'session')
            .prefetch_related('training_program_workout__exercises__exercise')
            .order_by('date', 'id'))
    entries, by_key = [], {}
    for day in days:
        # Two programs on one date that share a session are one day for this athlete.
        key = (day.date, day.session_id) if day.session_id else (day.date, 'day', day.pk)
        group = day.training_program.training_group.name
        workout = day.training_program_workout
        names = [row.exercise.name for row in workout.exercises.all()] if workout else []
        entry = by_key.get(key)
        if entry is None:
            if len(entries) == COMING_UP_LIMIT:
                continue
            entry = {'date': day.date.isoformat(),
                     'title': workout.name if workout else day.training_program.name,
                     'groups': [], 'movements': [], 'session_id': day.session_id}
            by_key[key] = entry
            entries.append(entry)
        if group not in entry['groups']:
            entry['groups'].append(group)
        entry['movements'] += [n for n in names if n not in entry['movements']]
    return entries


def _live(athlete, group_names):
    if not athlete.is_active:
        return None
    running = TrainingSession.objects.filter(started_at__isnull=False, ended_at__isnull=True).order_by('-started_at', '-pk')
    for session in running:
        if not may_join(session, athlete):
            continue
        taking_part = [p.training_program.training_group.name
                       for p in session.participations.select_related('training_program__training_group')]
        return {'session_id': session.pk, 'title': session.label,
                'groups': [g for g in dict.fromkeys(taking_part) if g in group_names],
                'movements': [m['name'] for m in movements_for_athlete(athlete, session)],
                'started_at': session.started_at.isoformat()}
    return None


def _recent(athlete):
    lifted = (Set.objects
              .filter(athlete=athlete, is_coach_adjustment=False, session__ended_at__isnull=False)
              .values('session')
              .annotate(done=Count('id', filter=Q(is_false_set=False)), ended=Max('session__ended_at'))
              .order_by('-ended', '-session')[:RECENT_LIMIT])
    rows = list(lifted)
    sessions = TrainingSession.objects.in_bulk([r['session'] for r in rows])
    recent = []
    for row in rows:
        session = sessions[row['session']]
        planned = sum(m['planned_sets'] or 0 for m in movements_for_athlete(athlete, session))
        when = session.started_at or session.ended_at
        recent.append({'session_id': session.pk,
                       'date': timezone.localdate(when).isoformat(),
                       'title': session.label,
                       'sets_done': row['done'], 'sets_planned': planned})
    return recent


def home_for(athlete):
    """Everything Home shows, for this athlete only."""
    groups = list(athlete.training_groups.order_by('name').values_list('id', 'name'))
    group_ids = [g for g, _ in groups]
    group_names = {n for _, n in groups}
    return {
        'athlete': {'name': athlete.name, 'first_name': _first_name(athlete.name),
                    'groups': [n for _, n in groups]},
        'live': _live(athlete, group_names),
        'coming_up': _coming_up(athlete, group_ids, timezone.localdate()),
        'recent': _recent(athlete),
    }


def session_for(athlete, session_id):
    """One session, as this athlete lived it: their own sets grouped by movement in the order
    they lifted, with totals (spec 10, Phases 2 and 3). None when they didn't lift in it, the
    same answer as a session that doesn't exist, so it can't be used to find sessions.

    Sets done leave out false sets and coach adjustments, the daily report's own count. Each
    movement also carries the sets its plan asked for, and a movement planned but not lifted
    is listed with no sets, so "2 of 3" and "0 of 3" both show.
    """
    session = TrainingSession.objects.filter(pk=session_id).first()
    if session is None:
        return None
    sets = list(Set.objects.filter(session=session, athlete=athlete, is_coach_adjustment=False,
                                   is_false_set=False)
                .select_related('exercise').prefetch_related('reps').order_by('started_at', 'id'))
    if not sets:
        return None
    plan = movements_for_athlete(athlete, session)
    planned = {m['exercise_id']: m['planned_sets'] or 0 for m in plan}

    by_exercise, order = {}, []
    for a_set in sets:
        if a_set.exercise_id not in by_exercise:
            by_exercise[a_set.exercise_id] = {'name': a_set.exercise.name,
                                              'sets_planned': planned.get(a_set.exercise_id, 0), 'sets': []}
            order.append(a_set.exercise_id)
        by_exercise[a_set.exercise_id]['sets'].append({
            'set_number': a_set.set_number, 'weight_lbs': a_set.weight_lbs,
            'reps': a_set.reps_completed or 0, 'avg_velocity': a_set.avg_velocity,
            'reps_detail': [r.mean_velocity for r in sorted(a_set.reps.all(), key=lambda r: r.rep_number)],
        })
    for movement in plan:
        if movement['exercise_id'] not in by_exercise:
            by_exercise[movement['exercise_id']] = {'name': movement['name'],
                                                    'sets_planned': movement['planned_sets'] or 0, 'sets': []}
            order.append(movement['exercise_id'])

    speeds = [s.avg_velocity for s in sets if s.avg_velocity is not None]
    group_names = set(athlete.training_groups.values_list('name', flat=True))
    taking_part = [p.training_program.training_group.name
                   for p in session.participations.select_related('training_program__training_group')]
    when = session.started_at or session.ended_at
    return {
        'session_id': session.pk,
        'date': timezone.localdate(when).isoformat() if when else None,
        'title': session.label,
        'groups': [g for g in dict.fromkeys(taking_part) if g in group_names],
        'totals': {'sets_done': len(sets), 'sets_planned': sum(planned.values()),
                   'reps': sum(s.reps_completed or 0 for s in sets),
                   'avg_velocity': (sum(speeds) / len(speeds)) if speeds else None},
        'movements': [by_exercise[e] for e in order],
    }
