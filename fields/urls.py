from rest_framework.routers import DefaultRouter
from .views import FieldViewSet, FieldScheduleViewSet, FieldBlockViewSet

router = DefaultRouter()
router.register(r'fields', FieldViewSet, basename='field')
router.register(r'field-schedules', FieldScheduleViewSet, basename='field-schedule')
router.register(r'field-blocks', FieldBlockViewSet, basename='field-block')

urlpatterns = router.urls
