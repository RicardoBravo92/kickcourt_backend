from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import CourtSchedule, CourtBlock
from .serializers import CourtScheduleSerializer, CourtBlockSerializer
from accounts.permissions import IsAdmin
from realtime.publishers import publish_availability


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
        block = serializer.save(created_by=self.request.user)
        publish_availability(block.court_id, str(block.date))

    def perform_update(self, serializer):
        instance = self.get_object()
        block = serializer.save()
        if (
            instance.court_id != block.court_id
            or instance.date != block.date
            or instance.start_time != block.start_time
            or instance.end_time != block.end_time
        ):
            publish_availability(instance.court_id, str(instance.date))
        publish_availability(block.court_id, str(block.date))

    def perform_destroy(self, instance):
        instance.delete()
        publish_availability(instance.court_id, str(instance.date))
