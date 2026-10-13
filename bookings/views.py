from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from .models import Booking
from .serializers import BookingSerializer, BookingListSerializer
from .services import send_booking_received, send_booking_confirmation, send_booking_cancelation
from realtime.publishers import publish_availability, publish_booking_event
from accounts.permissions import IsAdmin, IsAdminOrVendor
from vendors.models import Vendor

User = get_user_model()


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'date', 'court']
    search_fields = ['court__name', 'user__username']
    ordering_fields = ['date', 'start_time', 'created_at']
    ordering = ['-date', '-start_time']

    def get_queryset(self):
        # `restore` must be able to reach soft-deleted bookings, so it uses the
        # unfiltered manager instead of the default active-only queryset.
        return self._scoped_queryset(include_deleted=self.action == 'restore')

    def _scoped_queryset(self, include_deleted=False):
        user = self.request.user
        bookings = Booking.objects if include_deleted else Booking.objects.active()
        if user.role == User.Roles.ADMIN:
            return bookings.with_court().with_user()
        if user.role == User.Roles.VENDOR:
            vendor = Vendor.objects.filter(user=user).first()
            if vendor:
                return bookings.for_vendor(vendor).with_court().with_user()
        return bookings.for_user(user).with_court()

    def _check_vendor_ownership(self, booking):
        """Check if the vendor owns the court for this booking."""
        if self.request.user.role == User.Roles.VENDOR:
            vendor = Vendor.objects.filter(user=self.request.user).first()
            if not vendor or booking.court.vendor != vendor:
                raise PermissionDenied('You can only manage bookings for your own courts.')

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        return BookingSerializer
    def perform_create(self, serializer):
        booking = serializer.save(user=self.request.user)
        from .services import calculate_total_price, calculate_commission
        booking.total_price = calculate_total_price(booking.court, booking.start_time, booking.end_time)
        if booking.court.vendor and booking.court.vendor.is_approved:
            booking.commission = calculate_commission(booking.total_price, booking.court.vendor.commission_rate)
        booking.save(update_fields=['total_price', 'commission'])
        send_booking_received(booking)
        publish_availability(booking.court_id, str(booking.date))
        publish_booking_event(booking, 'created')

    def perform_update(self, serializer):
        instance = self.get_object()
        previous_court_id = instance.court_id
        previous_date = str(instance.date)
        from .services import calculate_total_price, calculate_commission
        previous_total = calculate_total_price(instance.court, instance.start_time, instance.end_time)
        booking = serializer.save()
        new_total = calculate_total_price(booking.court, booking.start_time, booking.end_time)
        if new_total != previous_total:
            booking.total_price = new_total
            booking.commission = 0
            if booking.court.vendor and booking.court.vendor.is_approved:
                booking.commission = calculate_commission(new_total, booking.court.vendor.commission_rate)
            booking.save(update_fields=['total_price', 'commission'])
        # Old slot may come free if court/date/time changed.
        if previous_court_id != booking.court_id or previous_date != str(booking.date):
            publish_availability(previous_court_id, previous_date)
        publish_availability(booking.court_id, str(booking.date))
        publish_booking_event(booking, 'updated')

    def create(self, request, *args, **kwargs):
        if request.user.role == User.Roles.VENDOR:
            return Response({'error': 'Vendors cannot create bookings'}, status=status.HTTP_403_FORBIDDEN)
        # Slot-overlap validation runs inside BookingSerializer.validate
        # (see bookings.serializers) inside the transaction started by DRF.
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        bookings = Booking.objects.active().for_user(request.user).with_court().upcoming()
        page = self.paginate_queryset(bookings)
        serializer = BookingListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def pending(self, request):
        bookings = Booking.objects.active().pending().with_court().with_user()
        page = self.paginate_queryset(bookings)
        serializer = BookingListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrVendor])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        self._check_vendor_ownership(booking)
        if booking.status == Booking.Status.CANCELLED:
            return Response({'error': 'Cannot confirm a cancelled booking'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = Booking.Status.CONFIRMED
        booking.save()
        send_booking_confirmation(booking)
        publish_availability(booking.court_id, str(booking.date))
        publish_booking_event(booking, 'confirmed')
        return Response({'status': 'confirmed'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        self._check_vendor_ownership(booking)
        if booking.status == Booking.Status.CANCELLED:
            return Response({'error': 'Booking already cancelled'}, status=status.HTTP_400_BAD_REQUEST)
        if booking.status == Booking.Status.COMPLETED:
            return Response({'error': 'Cannot cancel a completed booking'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = Booking.Status.CANCELLED
        booking.save()
        send_booking_cancelation(booking)
        publish_availability(booking.court_id, str(booking.date))
        publish_booking_event(booking, 'cancelled')
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrVendor])
    def complete(self, request, pk=None):
        booking = self.get_object()
        self._check_vendor_ownership(booking)
        if booking.status == Booking.Status.COMPLETED:
            return Response({'status': 'already_completed'})
        if booking.status == Booking.Status.CANCELLED:
            return Response({'error': 'Cannot complete a cancelled booking'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = Booking.Status.COMPLETED
        booking.save()
        publish_availability(booking.court_id, str(booking.date))
        publish_booking_event(booking, 'completed')
        return Response({'status': 'completed'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrVendor])
    def restore(self, request, pk=None):
        booking = self.get_object()
        self._check_vendor_ownership(booking)
        booking.restore()
        publish_availability(booking.court_id, str(booking.date))
        publish_booking_event(booking, 'restored')
        return Response({'status': 'restored'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def deleted(self, request):
        bookings = Booking.objects.deleted().with_court().with_user()
        page = self.paginate_queryset(bookings)
        serializer = BookingListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
