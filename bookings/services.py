import logging
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Booking

logger = logging.getLogger(__name__)


def validate_booking_slots(field, date, start_time, end_time, exclude_pk=None):
    if start_time >= end_time:
        raise ValidationError({'end_time': 'End time must be after start time.'})

    if date < timezone.now().date():
        raise ValidationError({'date': 'Cannot book dates in the past.'})

    overlapping = Booking.objects.filter(
        field=field,
        date=date,
        status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
        start_time__lt=end_time,
        end_time__gt=start_time,
    )

    if exclude_pk:
        overlapping = overlapping.exclude(pk=exclude_pk)

    if overlapping.exists():
        raise ValidationError('This field is already booked for the selected time slot.')


def calculate_total_price(field, start_time, end_time):
    from datetime import datetime
    start = datetime.combine(timezone.now().date(), start_time)
    end = datetime.combine(timezone.now().date(), end_time)
    hours = (end - start).total_seconds() / 3600
    return field.price_per_hour * hours


def create_booking(user, field, date, start_time, end_time):
    validate_booking_slots(field, date, start_time, end_time)
    total_price = calculate_total_price(field, start_time, end_time)
    booking = Booking(
        user=user,
        field=field,
        date=date,
        start_time=start_time,
        end_time=end_time,
        total_price=total_price,
    )
    booking.full_clean()
    booking.save()
    return booking


def send_booking_confirmation(booking):
    try:
        subject = f'Booking Confirmation - {booking.field.name}'
        message = f"""
        Hi {booking.user.username},

        Your booking has been confirmed!

        Field: {booking.field.name}
        Date: {booking.date}
        Time: {booking.start_time} - {booking.end_time}
        Total: ${booking.total_price}

        Thank you for your booking!
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [booking.user.email],
            fail_silently=True,
        )
        logger.info(f'Booking confirmation sent to {booking.user.email}')
    except Exception as e:
        logger.error(f'Failed to send booking confirmation: {e}')
