import logging
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Booking

logger = logging.getLogger(__name__)


def validate_booking_slots(court, date, start_time, end_time, exclude_pk=None):
    if start_time >= end_time:
        raise ValidationError({'end_time': 'End time must be after start time.'})

    if date < timezone.now().date():
        raise ValidationError({'date': 'Cannot book dates in the past.'})

    overlapping = Booking.objects.filter(
        court=court,
        date=date,
        status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
        start_time__lt=end_time,
        end_time__gt=start_time,
    )

    if exclude_pk:
        overlapping = overlapping.exclude(pk=exclude_pk)

    if overlapping.exists():
        raise ValidationError('This court is already booked for the selected time slot.')


def calculate_total_price(court, start_time, end_time):
    from datetime import datetime
    start = datetime.combine(timezone.now().date(), start_time)
    end = datetime.combine(timezone.now().date(), end_time)
    hours = Decimal(str((end - start).total_seconds() / 3600))
    return Decimal(str(court.price_per_hour)) * hours


def calculate_commission(total_price, commission_rate):
    return total_price * commission_rate / Decimal('100')


def create_booking(user, court, date, start_time, end_time):
    validate_booking_slots(court, date, start_time, end_time)
    total_price = calculate_total_price(court, start_time, end_time)
    commission = 0
    if court.vendor and court.vendor.is_approved:
        commission = calculate_commission(total_price, court.vendor.commission_rate)
    booking = Booking(
        user=user,
        court=court,
        date=date,
        start_time=start_time,
        end_time=end_time,
        total_price=total_price,
        commission=commission,
    )
    booking.full_clean()
    booking.save()
    return booking


def send_booking_confirmation(booking):
    from .tasks import send_booking_confirmation_email
    send_booking_confirmation_email.delay(
        user_email=booking.user.email,
        user_username=booking.user.username,
        court_name=booking.court.name,
        date=str(booking.date),
        start_time=str(booking.start_time),
        end_time=str(booking.end_time),
        total_price=str(booking.total_price),
    )


def send_booking_cancelation(booking):
    from .tasks import send_booking_cancelation_email
    send_booking_cancelation_email.delay(
        user_email=booking.user.email,
        user_username=booking.user.username,
        court_name=booking.court.name,
        date=str(booking.date),
    )
