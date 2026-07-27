from datetime import time, datetime, timedelta

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.cache import cache
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import Field
from .serializers import FieldSerializer, FieldListSerializer
from accounts.permissions import IsAdmin

FIELDS_CACHE_KEY = 'fields_list'
CACHE_TIMEOUT = 60 * 15  # 15 minutes


class FieldViewSet(viewsets.ModelViewSet):
    queryset = Field.objects.active()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['field_type', 'surface', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price_per_hour', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return FieldListSerializer
        return FieldSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'availability']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]

    def list(self, request, *args, **kwargs):
        if request.query_params:
            return super().list(request, *args, **kwargs)

        cached = cache.get(FIELDS_CACHE_KEY)
        if cached:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(FIELDS_CACHE_KEY, response.data, CACHE_TIMEOUT)
        return response

    def perform_create(self, serializer):
        serializer.save()
        cache.delete(FIELDS_CACHE_KEY)

    def perform_update(self, serializer):
        serializer.save()
        cache.delete(FIELDS_CACHE_KEY)

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete(FIELDS_CACHE_KEY)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def restore(self, request, pk=None):
        field = self.get_object()
        field.restore()
        cache.delete(FIELDS_CACHE_KEY)
        return Response({'status': 'restored'})

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def availability(self, request, pk=None):
        field = self.get_object()
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': 'date query param is required (YYYY-MM-DD)'}, status=400)
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        from bookings.models import Booking
        booked = Booking.objects.filter(
            field=field,
            date=target_date,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
        ).values_list('start_time', 'end_time')

        booked_set = set()
        for st, et in booked:
            current = datetime.combine(target_date, st)
            end = datetime.combine(target_date, et)
            while current < end:
                booked_set.add(current.time())
                current += timedelta(hours=1)

        OPEN_HOUR = 8
        CLOSE_HOUR = 23
        slots = []
        for h in range(OPEN_HOUR, CLOSE_HOUR):
            slot_start = time(h, 0)
            slot_end = time(h + 1, 0)
            slots.append({
                'start_time': slot_start.strftime('%H:%M'),
                'end_time': slot_end.strftime('%H:%M'),
                'available': slot_start not in booked_set,
            })

        return Response({
            'field_id': field.id,
            'field_name': field.name,
            'date': date_str,
            'price_per_hour': str(field.price_per_hour),
            'slots': slots,
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def deleted(self, request):
        fields = Field.objects.deleted()
        page = self.paginate_queryset(fields)
        serializer = FieldListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
