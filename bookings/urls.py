from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import BookingViewSet
from .dashboard import dashboard_stats, bookings_export_csv

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = router.urls + [
    path('dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('dashboard/export/csv/', bookings_export_csv, name='bookings-export-csv'),
]
