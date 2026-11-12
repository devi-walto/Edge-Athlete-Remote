"""athlete_pages.py — the web addresses behind an online athlete's own pages (spec 10).

WHAT KIND OF FILE THIS IS: request handlers (Django "views"). Each answers one web
address; the work itself is in services/athlete_home.py.

WHY: an athlete signed in online needs a Home that says what's next, what's live and
what they did lately, from their own groups only.

  GET /api/athlete/home/              Home's data (Phase 0)
  GET /api/athlete/sessions/          All sessions, 20 at a time, ?before=<cursor> (Phase 3)
  GET /api/athlete/sessions/<id>/     one session as the athlete lived it (Phases 2, 3)
  GET /api/athlete/progress/          My Recent Progress, ?from=&to= (Phase 4)
  GET /api/athlete/progress/report/   the same range as a PDF of their own sets, ?unit=kg

Signed in as an athlete, on a remote server. A coach is refused (403); a local install
answers 404, because a gym has no athlete logins.
"""
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from .permissions import IsAthlete, RemoteOnly
from .services.athlete_home import BadCursor, home_for, session_for, sessions_page
from .services.athlete_progress import BadRange, parse_range, progress_for, reports_in_range
from .services.report_pdf import PdfTooLarge, render_athlete_reports_pdf
from .services.reports import athlete_report_detail


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def home(request):
    """Home for the signed-in athlete: what's coming up, what's live, their last five sessions"""
    return Response(home_for(request.user.athlete))


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def athlete_sessions(request):
    """The signed-in athlete's ended sessions, newest first, 20 at a time (?before= for the next page)"""
    try:
        return Response(sessions_page(request.user.athlete, request.query_params.get('before')))
    except BadCursor:
        raise ValidationError({'before': 'Not a page this server handed out.'})


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def athlete_session(request, session_id):
    """One session the signed-in athlete lifted in: their own sets by movement, with totals"""
    found = session_for(request.user.athlete, session_id)
    if found is None:
        raise NotFound()
    return Response(found)


def _range(request):
    try:
        return parse_range(request.query_params.get('from'), request.query_params.get('to'))
    except BadRange as exc:
        raise ValidationError({'range': str(exc)})


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def my_progress(request):
    """My Recent Progress for the signed-in athlete: their own trends over ?from= to ?to= (whole days)"""
    start, to = _range(request)
    return Response(progress_for(request.user.athlete, start, to))


@api_view(['GET'])
@permission_classes([RemoteOnly, IsAthlete])
def my_progress_report(request):
    """The signed-in athlete's own sets from ?from= to ?to= as a PDF, in the daily report's layout"""
    start, to = _range(request)
    athlete = request.user.athlete
    unit = 'kg' if request.query_params.get('unit') == 'kg' else 'lb'
    details = [athlete_report_detail(report, athlete.pk) for report in reports_in_range(athlete, start, to)]
    try:
        pdf = render_athlete_reports_pdf(details, f"{athlete.name} | {start} to {to}", unit)
    except PdfTooLarge:
        return Response({'error': 'That range is too large for one PDF. Try a shorter one.'}, status=413)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="my-report-{start}-to-{to}.pdf"'
    response['Cache-Control'] = 'private, no-store'
    return response
