import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def _layer():
    return get_channel_layer()


def publish_availability(court_id, date):
    """Broadcast the current availability of a court to the ``court_<id>`` room."""
    from courts.services import resolve_availability_for_date

    layer = _layer()
    if layer is None:
        return
    payload = resolve_availability_for_date(court_id, date)
    if payload is None:
        logger.warning('Availability broadcast skipped: no court %s on %s', court_id, date)
        return
    try:
        async_to_sync(layer.group_send)(
            f'court_{court_id}',
            {'type': 'court.availability', 'data': payload},
        )
    except Exception:  # noqa: BLE001 - WS must never break a booking request
        logger.exception('Failed to publish availability for court %s', court_id)


def publish_booking_event(booking, event):
    """Broadcast a booking event to the affected user, vendor and admins."""
    layer = _layer()
    if layer is None:
        return

    data = {
        'event': event,
        'booking_id': booking.id,
        'court_id': booking.court_id,
        'court_name': getattr(booking.court, 'name', ''),
        'date': str(booking.date),
        'start_time': str(booking.start_time),
        'end_time': str(booking.end_time),
        'status': booking.status,
        'user_id': booking.user_id,
    }
    try:
        data['user_username'] = booking.user.username
    except Exception:  # noqa: BLE001
        data['user_username'] = ''

    groups = {f'user_{booking.user_id}', 'admins'}
    vendor = getattr(booking.court, 'vendor', None)
    if vendor is not None:
        groups.add(f'vendor_{vendor.user_id}')

    for group in groups:
        try:
            async_to_sync(layer.group_send)(
                group,
                {'type': 'booking.event', 'data': data},
            )
        except Exception:  # noqa: BLE001
            logger.exception('Failed to publish booking event to %s', group)


def publish_chat_message(booking_id, message_data):
    layer = _layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(
            f'booking_{booking_id}',
            {'type': 'chat.message', 'data': message_data},
        )
    except Exception:  # noqa: BLE001
        logger.exception('Failed to publish chat message for booking %s', booking_id)