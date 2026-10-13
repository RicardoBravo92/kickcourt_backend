from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound, PermissionDenied

from bookings.models import Booking
from realtime.services import is_booking_participant

from .models import Message
from .serializers import MessageSerializer


class BookingMessageListCreateView(generics.ListCreateAPIView):
    """GET chat history / POST a message for a specific booking."""

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_booking(self):
        booking = (
            Booking.objects.select_related('court__vendor', 'user')
            .filter(pk=self.kwargs['booking_id'], deleted_at__isnull=True)
            .first()
        )
        if booking is None:
            raise NotFound('Booking not found.')
        if not is_booking_participant(self.request.user, booking):
            raise PermissionDenied('You cannot access messages for this booking.')
        return booking

    def get_queryset(self):
        booking = self._get_booking()
        return Message.objects.filter(booking=booking)

    def perform_create(self, serializer):
        booking = self._get_booking()
        serializer.save(booking=booking, sender=self.request.user)