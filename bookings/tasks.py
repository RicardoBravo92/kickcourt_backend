import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_booking_confirmation_email(self, user_email, user_username, field_name, date, start_time, end_time, total_price):
    try:
        subject = f'Booking Confirmation - {field_name}'
        message = f"""
        Hi {user_username},

        Your booking has been confirmed!

        Field: {field_name}
        Date: {date}
        Time: {start_time} - {end_time}
        Total: ${total_price}

        Thank you for your booking!
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        logger.info(f'Booking confirmation sent to {user_email}')
        return f'Sent to {user_email}'
    except Exception as exc:
        logger.error(f'Failed to send email to {user_email}: {exc}')
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_booking_cancelation_email(self, user_email, user_username, field_name, date):
    try:
        subject = f'Booking Cancelled - {field_name}'
        message = f"""
        Hi {user_username},

        Your booking has been cancelled.

        Field: {field_name}
        Date: {date}

        If this was a mistake, please create a new booking.
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_email],
            fail_silently=False,
        )
        logger.info(f'Booking cancelation sent to {user_email}')
        return f'Sent to {user_email}'
    except Exception as exc:
        logger.error(f'Failed to send email to {user_email}: {exc}')
        self.retry(exc=exc, countdown=60)
