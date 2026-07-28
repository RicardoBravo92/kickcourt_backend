from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import CourtSchedule, CourtBlock
from .serializers import CourtScheduleSerializer, CourtBlockSerializer
from accounts.permissions import IsAdmin


class CourtScheduleViewSet(viewsets.ModelViewSet):
    queryset = CourtSchedule.objects.all()
    serializer_class = CourtScheduleSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['court', 'day_of_week']

    def get_queryset(self):
        qs = CourtSchedule.objects.all()
        court_id = self.request.query_params.get('court')
        if court_id:
            qs = qs.filter(court_id=court_id)
        return qs


class CourtBlockViewSet(viewsets.ModelViewSet):
    queryset = CourtBlock.objects.all()
    serializer_class = CourtBlockSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['court', 'date']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
