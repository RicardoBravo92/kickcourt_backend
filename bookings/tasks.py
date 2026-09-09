import logging
import resend
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def _send_resend_email(user_email, subject, html):
    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": user_email,
        "subject": subject,
        "html": html,
    })


@shared_task(bind=True, max_retries=3)
def send_booking_received_email(self, user_email, user_username, court_name, date, start_time, end_time, total_price):
    try:
        subject = f'Booking Request Received - {court_name}'
        html = f"""
            <h2>Booking Request Received</h2>
            <p>Hi {user_username},</p>
            <p>Your booking request has been received and is pending confirmation.</p>
            <ul>
                <li>Court: {court_name}</li>
                <li>Date: {date}</li>
                <li>Time: {start_time} - {end_time}</li>
                <li>Total: ${total_price}</li>
            </ul>
            <p>We will notify you once it is confirmed.</p>
        """
        _send_resend_email(user_email, subject, html)
        logger.info(f'Booking received email sent to {user_email}')
        return f'Sent to {user_email}'
    except Exception as exc:
        logger.error(f'Failed to send email to {user_email}: {exc}')
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_booking_confirmation_email(self, user_email, user_username, court_name, date, start_time, end_time, total_price):
    try:
        subject = f'Booking Confirmed - {court_name}'
        html = f"""
            <h2>Booking Confirmed</h2>
            <p>Hi {user_username},</p>
            <p>Your booking has been confirmed!</p>
            <ul>
                <li>Court: {court_name}</li>
                <li>Date: {date}</li>
                <li>Time: {start_time} - {end_time}</li>
                <li>Total: ${total_price}</li>
            </ul>
            <p>Thank you for your booking!</p>
        """
        _send_resend_email(user_email, subject, html)
        logger.info(f'Booking confirmation sent to {user_email}')
        return f'Sent to {user_email}'
    except Exception as exc:
        logger.error(f'Failed to send email to {user_email}: {exc}')
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_booking_cancelation_email(self, user_email, user_username, court_name, date):
    try:
        subject = f'Booking Cancelled - {court_name}'
        html = f"""
            <h2>Booking Cancelled</h2>
            <p>Hi {user_username},</p>
            <p>Your booking has been cancelled.</p>
            <ul>
                <li>Court: {court_name}</li>
                <li>Date: {date}</li>
            </ul>
            <p>If this was a mistake, please create a new booking.</p>
        """
        _send_resend_email(user_email, subject, html)
        logger.info(f'Booking cancelation sent to {user_email}')
        return f'Sent to {user_email}'
    except Exception as exc:
        logger.error(f'Failed to send email to {user_email}: {exc}')
        self.retry(exc=exc, countdown=60)