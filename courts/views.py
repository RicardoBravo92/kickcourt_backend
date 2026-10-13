from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Court, CourtSchedule, CourtBlock
from .serializers import CourtSerializer, CourtListSerializer, CourtScheduleSerializer, CourtBlockSerializer
from accounts.permissions import IsAdmin, IsAdminOrVendor

User = get_user_model()


class CourtViewSet(viewsets.ModelViewSet):
    queryset = Court.objects.active()
    serializer_class = CourtSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sport_type', 'surface', 'is_active', 'vendor']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price_per_hour', 'sport_type']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'availability'):
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrVendor()]

    def get_queryset(self):
        qs = Court.objects.active()
        user = self.request.user
        if self.action in ('update', 'partial_update', 'destroy'):
            if user.role == User.Roles.ADMIN:
                return qs
            if user.role == User.Roles.VENDOR and hasattr(user, 'vendor_profile') and user.vendor_profile:
                return qs.filter(vendor=user.vendor_profile)
            return qs.none()
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
        if user.role == User.Roles.ADMIN:
            serializer.save(vendor=serializer.validated_data.get('vendor'))
            return
        vendor = getattr(user, 'vendor_profile', None)
        serializer.save(vendor=vendor)

    def perform_update(self, serializer):
        serializer.save(vendor=self.get_object().vendor)

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        from .services import compute_availability_slots

        court = self.get_object()
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': 'date parameter required (YYYY-MM-DD)'}, status=400)
        try:
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)

        return Response(compute_availability_slots(court, date))
