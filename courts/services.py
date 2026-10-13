from django.utils import timezone

from .models import Court, CourtSchedule, CourtBlock


def compute_availability_slots(court, date):
    """Reusable availability computation shared by the REST endpoint and the
    realtime broadcast. Returns a serializable dict."""
    from bookings.models import Booking

    blocks = CourtBlock.objects.filter(court=court, date=date)
    blocked_hours = set()
    for block in blocks:
        hour = block.start_time.hour
        while hour < block.end_time.hour:
            blocked_hours.add(hour)
            hour += 1

    bookings = Booking.objects.filter(
        court=court,
        date=date,
        deleted_at__isnull=True,
        status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
    )
    booked_hours = set()
    for booking in bookings:
        hour = booking.start_time.hour
        while hour < booking.end_time.hour:
            booked_hours.add(hour)
            hour += 1

    day_of_week = date.weekday()
    schedules = CourtSchedule.objects.filter(
        court=court, day_of_week=day_of_week, is_active=True
    )

    available_hours = set()
    if schedules.exists():
        for schedule in schedules:
            hour = schedule.open_time.hour
            while hour < schedule.close_time.hour:
                available_hours.add(hour)
                hour += 1
    else:
        for hour in range(8, 24):
            available_hours.add(hour)

    slots = []
    for hour in range(8, 24):
        status = 'available'
        if hour in booked_hours:
            status = 'booked'
        elif hour in blocked_hours:
            status = 'blocked'
        elif hour not in available_hours:
            status = 'closed'
        slots.append({
            'hour': hour,
            'time': f'{hour:02d}:00',
            'end_time': f'{hour + 1:02d}:00',
            'status': status,
        })

    return {
        'court_id': court.id,
        'court_name': court.name,
        'date': date.isoformat(),
        'slots': slots,
    }


def get_court_or_none(court_id):
    return Court.objects.filter(pk=court_id, is_active=True, deleted_at__isnull=True).first()


def resolve_availability_for_date(court_id, date_str):
    """Get an availability payload for a court on a date, or None."""
    try:
        date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None
    court = get_court_or_none(court_id)
    if court is None:
        return None
    return compute_availability_slots(court, date)