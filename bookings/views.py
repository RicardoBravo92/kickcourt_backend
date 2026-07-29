from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from .models import Booking
from .serializers import BookingSerializer, BookingListSerializer
from .services import send_booking_confirmation, send_booking_cancelation
from accounts.permissions import IsAdmin, IsAdminOrVendor

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
        user = self.request.user
        if user.role == User.Roles.ADMIN:
            return Booking.objects.active().with_court().with_user()
        if user.role == User.Roles.VENDOR:
            from vendors.models import Vendor
            vendor = Vendor.objects.filter(user=user).first()
            if vendor:
                return Booking.objects.active().for_vendor(vendor).with_court().with_user()
        return Booking.objects.active().for_user(user).with_court()

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
        send_booking_confirmation(booking)

    def create(self, request, *args, **kwargs):
        if request.user.role == User.Roles.VENDOR:
            return Response({'error': 'Vendors cannot create bookings'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

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

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if booking.status == Booking.Status.CANCELLED:
            return Response({'error': 'Booking already cancelled'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = Booking.Status.CANCELLED
        booking.save()
        send_booking_cancelation(booking)
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrVendor])
    def complete(self, request, pk=None):
        booking = self.get_object()
        if booking.status == Booking.Status.COMPLETED:
            return Response({'status': 'already_completed'})
        if booking.status == Booking.Status.CANCELLED:
            return Response({'error': 'Cannot complete a cancelled booking'}, status=status.HTTP_400_BAD_REQUEST)
        booking.status = Booking.Status.COMPLETED
        booking.save()
        return Response({'status': 'completed'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrVendor])
    def restore(self, request, pk=None):
        booking = self.get_object()
        booking.restore()
        return Response({'status': 'restored'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def deleted(self, request):
        bookings = Booking.objects.deleted().with_court().with_user()
        page = self.paginate_queryset(bookings)
        serializer = BookingListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
