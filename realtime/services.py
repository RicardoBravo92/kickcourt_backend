from realtime.models import Message
from realtime.serializers import MessageSerializer


def create_chat_message(user, booking, text):
    message = Message.objects.create(booking=booking, sender=user, text=text)
    return MessageSerializer(message).data


def is_booking_participant(user, booking):
    """Admin, the booking owner, or the vendor that owns the court."""
    if user.role == 'ADMIN':
        return True
    if booking.user_id == user.id:
        return True
    if user.role == 'VENDOR':
        vendor = getattr(user, 'vendor_profile', None)
        return bool(vendor) and booking.court.vendor_id == vendor.id
    return False