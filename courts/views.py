from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Court, CourtSchedule, CourtBlock
from .serializers import CourtSerializer, CourtListSerializer, CourtScheduleSerializer, CourtBlockSerializer
from accounts.permissions import IsAdmin, IsAdminOrVendor


class CourtViewSet(viewsets.ModelViewSet):
    queryset = Court.objects.active()
    serializer_class = CourtSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sport_type', 'surface', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price_per_hour', 'sport_type']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        if self.action == 'availability':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminOrVendor()]

    def get_queryset(self):
        qs = Court.objects.active()
        user = self.request.user
        if self.request.query_params.get('my_courts') == 'true' and user.is_authenticated and hasattr(user, 'vendor_profile') and user.vendor_profile:
            qs = qs.filter(vendor=user.vendor_profile)
        sport = self.request.query_params.get('sport_type')
        if sport:
            qs = qs.by_sport(sport)
        surface = self.request.query_params.get('surface')
        if surface:
            qs = qs.by_surface(surface)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.search(search)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return CourtListSerializer
        return CourtSerializer

    def perform_create(self, serializer):
        user = self.request.user
        vendor = None
        if hasattr(user, 'vendor_profile'):
            vendor = user.vendor_profile
        serializer.save(vendor=vendor)

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        from bookings.models import Booking
        court = self.get_object()
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': 'date parameter required (YYYY-MM-DD)'}, status=400)
        try:
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)

        blocks = CourtBlock.objects.filter(court=court, date=date)
        blocked_hours = set()
        for block in blocks:
            hour = block.start_time.hour
            while hour < block.end_time.hour:
                blocked_hours.add(hour)
                hour += 1

        bookings = Booking.objects.filter(
            court=court, date=date,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]
        )
        booked_hours = set()
        for booking in bookings:
            hour = booking.start_time.hour
            while hour < booking.end_time.hour:
                booked_hours.add(hour)
                hour += 1

        day_of_week = date.weekday()
        schedules = CourtSchedule.objects.filter(court=court, day_of_week=day_of_week, is_active=True)

        available_hours = set()
        if schedules.exists():
            for schedule in schedules:
                hour = schedule.open_time.hour
                while hour < schedule.close_time.hour:
                    available_hours.add(hour)
                    hour += 1
        else:
            for hour in range(8, 24):
                available_hours.add(hour)

        slots = []
        for hour in range(8, 24):
            status = 'available'
            if hour in booked_hours:
                status = 'booked'
            elif hour in blocked_hours:
                status = 'blocked'
            elif hour not in available_hours:
                status = 'closed'
            slots.append({
                'hour': hour,
                'time': f'{hour:02d}:00',
                'end_time': f'{hour + 1:02d}:00',
                'status': status,
            })

        return Response({
            'court_id': court.id,
            'court_name': court.name,
            'date': date_str,
            'slots': slots,
        })
