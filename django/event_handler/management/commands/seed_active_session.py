# seed_active_session.py — fill an empty dev database with one realistic, live
# training session so the rack screen has real data to fetch on day one.
#
# It builds exactly what GET /api/sessions/active/ is meant to return: a session
# that hasn't ended, a roster of athletes, a plan they train, a few already-
# finished sets so some athletes read as "has data" (and some don't), and real
# recorded maxes — on purpose leaving one gap and one older-then-newer pair so
# you can see the endpoint pick the current max and expose the "no max yet" case
# the rack screen prompts for.
#
# The plan is built the way a coach builds one: a TrainingBlock (the reusable
# template) is deployed as a TrainingProgram for a TrainingGroup, and that group
# is scheduled into the session. Prescriptions are PERCENTAGES, so the pounds
# each athlete sees come from their own reference max — which is why Riley
# Brooks's missing bench max shows up as a real "no target" case rather than a
# made-up number.
#
# SAFE ON A REAL SCHOOL'S SERVER (spec 04, Phase 5), because it only adds, and
# recognises its own rows:
#   - its athletes and sensors are marked simulated; its group, plan and session
#     have demo-only names;
#   - it refuses if a real athlete already has one of its names;
#   - it never makes a login: with no coach in the school it stops ("claim it
#     first"); the plan belongs to the first administrator;
#   - it never ends a session it didn't make: another session running → it stops.
# On a remote server it is run with `eactl seed "School"`. Each invented athlete gets
# their own simulated sensor; `eactl sim` (simulate_node --seeded) wakes them.
#
# Re-runnable: pass --reset to remove just this command's own earlier rows (by the
# simulated label and the demo names, never by an athlete's name) and rebuild.
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from django.contrib.auth.models import User

from event_handler.models import (Athlete, AthleteReferenceMax, DailyReport, Exercise,
                                  Node, Rep, TrainingSession, SessionParticipation, Set,
                                  TrainingBlock, TrainingBlockExercise, TrainingBlockWorkout,
                                  TrainingGroup, TrainingGroupCoach, TrainingProgram)
from event_handler.services.planning import generate_schedule, instantiate_block
from event_handler.services.virtual_racks import release_session_racks

# Names no real school would use, so the seeder (and --reset) can recognise its own
# group, plan and session without guessing (spec 04, Phase 5). A real school very
# likely has a "Varsity" group.
SESSION_LABEL = "Demo session — Lower + Push"
NODE_ID = "rack_1"          # a gym-style sensor on rack 1, for a local install's demo
GROUP_NAME = "Demo Squad"
BLOCK_NAME = "Demo Strength Block"
# A day INSIDE a block is timeless — it gets scheduled onto whatever date the
# cadence lands on, so naming it after a weekday reads as a contradiction the
# moment the calendar puts "Thursday" on a Friday. The SESSION label above is a
# different thing and can name a real day, because a session IS one.
WORKOUT_NAME = "Day 1 — Lower + Push"

# The demo roster. Invented names on purpose: this data also goes on the public
# demo school (spec 14), and no real person's name belongs there.
ATHLETES = ["Alex Rivera", "Jordan Lee", "Casey Morgan", "Riley Brooks"]

# NFC wristband tags, keyed by athlete name. Only Jordan's is filled in — it is
# the one the demo actually taps, and it is the value the READER reads (which can
# differ from the label printed on the band; the reader is authoritative). A
# fresh seed leaves the others untagged, exactly like a real gym roster. This
# lives in the seeder because nothing else assigns tags, and a fresh database
# without it silently loses wristband sign-in — which is how the demo got burned.
NFC_TAG_BY_ATHLETE = {
    "Jordan Lee": "044DF23A1F1D91",
}

ALEX = "Alex Rivera"
JORDAN = "Jordan Lee"
CASEY = "Casey Morgan"
RILEY = "Riley Brooks"

# The prescription, written once for the whole group. 72% of a 315 squat is 227,
# which rounds to 225 — the same bar the old per-athlete seed put in front of
# Jordan, now arrived at the way the system actually works.
PRESCRIPTION = [
    {"exercise": "Back Squat",  "sets": 5, "reps": 3, "percent": 72.0,
     "zone_min": 0.5, "zone_max": 0.8},
    {"exercise": "Bench Press", "sets": 4, "reps": 5, "percent": 75.0,
     "zone_min": 0.4, "zone_max": 0.7},
]

SQUAT = "Back Squat"
BENCH = "Bench Press"


def sensor_id(name):
    """Each invented athlete's own simulated sensor: "sim-alex-rivera"."""
    return "sim-" + slugify(name)


class Command(BaseCommand):
    help = ("Seed one live demo session: invented athletes (marked simulated), each with "
            "their own simulated sensor, a plan, a few finished sets and maxes. Only adds; "
            "refuses rather than touch real data.")

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Remove this command's own earlier demo rows first, then reseed.")

    @transaction.atomic
    def handle(self, *args, **options):
        # ── checks first: refuse rather than touch anything real ──────────────
        # (All of this runs in one transaction, so a refusal anywhere leaves
        # nothing behind.)
        coach = self._coach()
        clash = list(Athlete.objects.filter(name__in=ATHLETES, is_simulated=False)
                     .values_list("name", flat=True))
        if clash:
            raise CommandError(
                f"A real athlete already has a demo name ({', '.join(clash)}). Nothing was "
                "seeded: demo data never mixes with a real athlete.")
        foreign = (TrainingSession.objects.filter(started_at__isnull=False, ended_at__isnull=True)
                   .exclude(pk__in=self._own_sessions()))
        if foreign.exists():
            raise CommandError(
                f"A session is running ({foreign.first().label!r}). End it first: the seeder "
                "never ends a session it didn't make.")

        if options["reset"]:
            self._reset()

        # ── the rows (only ever added, or reused if they're already ours) ─────
        node, _ = Node.objects.get_or_create(
            node_id=NODE_ID, defaults={"rack_number": 1, "mount_type": Node.MOUNT_BAR,
                                       "is_simulated": True})

        squat, _ = Exercise.objects.get_or_create(name=SQUAT)
        bench, _ = Exercise.objects.get_or_create(name=BENCH)

        # Invented athletes, marked simulated: that label is how the seeder (and
        # --reset) recognises its own rows, never by name alone.
        athletes = {name: Athlete.objects.get_or_create(name=name, is_simulated=True)[0]
                    for name in ATHLETES}
        # Wristband tags must survive re-seeding: get_or_create keeps an existing
        # athlete, so only assign when the row has none. (A coach may have
        # retagged someone by hand; never clobber that.) And never take a tag a
        # real athlete already has.
        for name, tag in NFC_TAG_BY_ATHLETE.items():
            athlete = athletes.get(name)
            if (athlete is not None and not athlete.nfc_tag_id
                    and not Athlete.objects.filter(nfc_tag_id=tag).exists()):
                athlete.nfc_tag_id = tag
                athlete.save(update_fields=["nfc_tag_id"])

        # Each invented athlete owns one simulated sensor (spec 04, Phase 5). When
        # they join a session online it goes on their own rack; `eactl sim` (the
        # simulator with --seeded) makes them send reps. Marked simulated too.
        for athlete in athletes.values():
            Node.objects.get_or_create(
                node_id=sensor_id(athlete.name),
                defaults={"owner": athlete, "is_simulated": True, "mount_type": Node.MOUNT_BAR})

        group, _ = TrainingGroup.objects.get_or_create(name=GROUP_NAME)
        # Staff are a join table now, not a field — a group can have several.
        TrainingGroupCoach.objects.get_or_create(
            training_group=group, coach=coach,
            defaults={"role": TrainingGroupCoach.HEAD})
        for athlete in athletes.values():
            athlete.training_groups.add(group)

        # The template, written once — then deployed for the group. Deploying
        # copies the rows down, which is why editing the template later can't
        # rewrite what this group already trained.
        block, _ = TrainingBlock.objects.get_or_create(name=BLOCK_NAME, coach=coach)
        # Set rather than passed as `defaults`, so a block from an earlier run
        # converges on the cadence this promises; an empty cadence would show a
        # deployed program with an empty calendar and no obvious reason why.
        if not block.cadence_days_of_week or not block.duration_weeks:
            block.cadence_days_of_week = "Mon,Wed,Fri"
            block.duration_weeks = 4
            block.save(update_fields=["cadence_days_of_week", "duration_weeks"])
        block.workouts.filter(position=1).exclude(name=WORKOUT_NAME).update(name=WORKOUT_NAME)
        if not block.workouts.exists():
            workout = TrainingBlockWorkout.objects.create(
                training_block=block, name=WORKOUT_NAME, position=1)
            for position, row in enumerate(PRESCRIPTION, start=1):
                TrainingBlockExercise.objects.create(
                    training_block_workout=workout,
                    exercise=Exercise.objects.get(name=row["exercise"]),
                    position=position, sets=row["sets"], reps=row["reps"],
                    target_percent=row["percent"],
                    velocity_zone_min=row["zone_min"], velocity_zone_max=row["zone_max"])

        # Reuse this group's existing deployment instead of adding another: each
        # program brings its own calendar, so reseeds would stack overlapping slots.
        program = (TrainingProgram.objects
                   .filter(training_group=group, training_block=block)
                   .order_by("id").first())
        if program is None:
            program = instantiate_block(block, group, start_date=timezone.localdate())
        else:
            generate_schedule(program, block)   # idempotent: one slot per day
        program.workouts.filter(position=1).exclude(name=WORKOUT_NAME).update(name=WORKOUT_NAME)

        # Only one day may be open at a time (canon D18). The seeder replaces its
        # OWN earlier demo day; anything else running was refused above.
        own_open = TrainingSession.objects.filter(
            pk__in=self._own_sessions(), ended_at__isnull=True)
        for old in own_open:
            release_session_racks(old)
        closed = own_open.update(ended_at=timezone.now())
        if closed:
            self.stdout.write(f"  ended the earlier demo session ({closed})")

        # The live session, roster = all four athletes.
        session = TrainingSession.objects.create(label=SESSION_LABEL, started_at=timezone.now())
        session.athletes.set(athletes.values())

        # Put the group ON the session, pointed at the day's workout. Without
        # this the session has a roster but nobody has anything to lift.
        SessionParticipation.objects.create(
            session=session, training_program=program,
            training_program_workout=program.workouts.order_by("position").first())

        # Give TWO of the four a finished set already, so has_data is non-trivial
        # (Alex + Jordan read as has_data=true; Casey + Riley as false).
        self._finish_a_set(session, node, athletes[ALEX], squat, 1, 205.0)
        self._finish_a_set(session, node, athletes[JORDAN], squat, 1, 255.0)

        # Recorded reference maxes, shaped to exercise the endpoint:
        #  - Alex gets an OLD squat ref then a NEWER one → endpoint must return 315.
        #  - Riley has NO bench ref → the "set your max" prompt has a gap to fill.
        self._record_max(athletes[ALEX],   squat, 300.0, days_ago=40)
        self._record_max(athletes[ALEX],   squat, 315.0, days_ago=3)
        self._record_max(athletes[ALEX],   bench, 205.0, days_ago=5)
        self._record_max(athletes[JORDAN], squat, 365.0, days_ago=7)
        self._record_max(athletes[JORDAN], bench, 245.0, days_ago=7)
        self._record_max(athletes[CASEY],  squat, 245.0, days_ago=10)
        self._record_max(athletes[CASEY],  bench, 175.0, days_ago=10)
        self._record_max(athletes[RILEY],  squat, 275.0, days_ago=14)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded demo session '{session.label}' (id={session.id}) with "
            f"{len(athletes)} invented athletes in '{GROUP_NAME}', each with their own "
            f"simulated sensor, 2 finished sets, and maxes."))

    # ── what is ours, and who owns the plan ───────────────────────────────────

    def _coach(self):
        """The school's first administrator, or else its first coach. The seeder
        never makes a login: a school with no coach is claimed first (setup code)."""
        coaches = User.objects.filter(coach_profile__isnull=False, is_active=True)
        coach = coaches.filter(is_staff=True).order_by("id").first() or coaches.order_by("id").first()
        if coach is None:
            raise CommandError(
                "This school has no coach yet. Claim it first (setup code), then seed it. "
                "The seeder never makes a login.")
        return coach

    def _own_sessions(self):
        """Demo sessions: the demo label, with the demo group taking part."""
        return (TrainingSession.objects.filter(
                    label=SESSION_LABEL,
                    participations__training_program__training_group__name=GROUP_NAME)
                .values("pk"))

    def _reset(self):
        """Remove this command's own rows, and nothing else.

        Recognised by the simulated label (athletes, sensors) and the demo-only
        group, plan and session names, never by an athlete's name. Order matters:
        a Set and a DailyReport both PROTECT their session, on purpose, so the
        seeder has to say plainly that it is removing its own.
        """
        demo = Athlete.objects.filter(is_simulated=True, name__in=ATHLETES)
        sessions = TrainingSession.objects.filter(pk__in=self._own_sessions())
        for session in sessions:
            release_session_racks(session)
        Set.objects.filter(session__in=sessions).delete()
        DailyReport.objects.filter(session__in=sessions).delete()
        sessions.delete()
        AthleteReferenceMax.objects.filter(athlete__in=demo).delete()
        Node.objects.filter(is_simulated=True).filter(
            Q(owner__in=demo) | Q(node_id=NODE_ID)).delete()
        TrainingProgram.objects.filter(training_group__name=GROUP_NAME).delete()
        TrainingBlock.objects.filter(name=BLOCK_NAME).delete()
        TrainingGroup.objects.filter(name=GROUP_NAME).delete()
        demo.delete()
        self.stdout.write("Reset: removed the earlier demo rows.")

    def _finish_a_set(self, session, node, athlete, exercise, set_number, weight_lbs):
        """Create one already-completed set with a couple of reps, so the athlete
        reads as has_data=true for this session."""
        s = Set.objects.create(
            session=session, athlete=athlete, node=node, exercise=exercise,
            set_number=set_number, weight_lbs=weight_lbs, reps_completed=2,
            avg_velocity=0.68, peak_velocity=0.82, is_false_set=False,
            ended_at=timezone.now())
        for n in (1, 2):
            Rep.objects.create(set=s, rep_number=n, timestamp=timezone.now(),
                               mean_velocity=0.68, peak_velocity=0.82,
                               duration_ms=700, velocity_color="green")
        return s

    def _record_max(self, athlete, exercise, weight_lbs, days_ago,
                    source=AthleteReferenceMax.SOURCE_MANUAL):
        """Append one reference-max row, back-dating recorded_at so 'newest wins'
        is testable (auto_now_add is set on create, so we override it with a
        direct update)."""
        m = AthleteReferenceMax.objects.create(
            athlete=athlete, exercise=exercise, reference_weight_lbs=weight_lbs, source=source)
        AthleteReferenceMax.objects.filter(pk=m.pk).update(
            recorded_at=timezone.now() - timedelta(days=days_ago))
        return m
