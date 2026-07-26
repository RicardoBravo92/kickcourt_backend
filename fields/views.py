from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.cache import cache
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
        if self.action in ['list', 'retrieve']:
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

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def deleted(self, request):
        fields = Field.objects.deleted()
        page = self.paginate_queryset(fields)
        serializer = FieldListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
