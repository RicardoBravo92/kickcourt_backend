from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourtViewSet
from .views_extra import CourtScheduleViewSet, CourtBlockViewSet

router = DefaultRouter()
router.register(r'courts', CourtViewSet, basename='court')
router.register(r'court-schedules', CourtScheduleViewSet, basename='court-schedule')
router.register(r'court-blocks', CourtBlockViewSet, basename='court-block')

urlpatterns = [
    path('', include(router.urls)),
]
