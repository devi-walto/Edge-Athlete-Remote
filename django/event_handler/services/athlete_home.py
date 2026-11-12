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
