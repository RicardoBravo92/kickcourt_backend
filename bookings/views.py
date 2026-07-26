from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from .models import Booking
from .serializers import BookingSerializer, BookingListSerializer
from .services import send_booking_confirmation
from accounts.permissions import IsAdmin

User = get_user_model()


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'date', 'field']
    search_fields = ['field__name', 'user__username']
    ordering_fields = ['date', 'start_time', 'created_at']
    ordering = ['-date', '-start_time']

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Roles.ADMIN:
            return Booking.objects.active().with_field().with_user()
        return Booking.objects.active().for_user(user).with_field()

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        return BookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save(user=self.request.user)
        send_booking_confirmation(booking)

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        bookings = Booking.objects.active().for_user(request.user).with_field().upcoming()
        page = self.paginate_queryset(bookings)
        serializer = BookingListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def pending(self, request):
        bookings = Booking.objects.active().pending().with_field().with_user()
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
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def restore(self, request, pk=None):
        booking = self.get_object()
        booking.restore()
        return Response({'status': 'restored'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def deleted(self, request):
        bookings = Booking.objects.deleted().with_field().with_user()
        page = self.paginate_queryset(bookings)
        serializer = BookingListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
