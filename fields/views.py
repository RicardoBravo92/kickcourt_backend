from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Field
from .serializers import FieldSerializer, FieldListSerializer
from accounts.permissions import IsAdmin


class FieldViewSet(viewsets.ModelViewSet):
    queryset = Field.objects.all()
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
