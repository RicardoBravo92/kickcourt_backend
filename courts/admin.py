from django.contrib import admin
from .models import Court, CourtSchedule, CourtBlock


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport_type', 'surface', 'players_per_side', 'price_per_hour', 'is_active', 'vendor', 'deleted_at')
    list_filter = ('sport_type', 'surface', 'is_active')
    readonly_fields = ('deleted_at',)


@admin.register(CourtSchedule)
class CourtScheduleAdmin(admin.ModelAdmin):
    list_display = ('court', 'day_of_week', 'open_time', 'close_time', 'is_active')
    list_filter = ('court', 'day_of_week', 'is_active')


@admin.register(CourtBlock)
class CourtBlockAdmin(admin.ModelAdmin):
    list_display = ('court', 'date', 'start_time', 'end_time', 'reason', 'created_by')
    list_filter = ('court', 'date')
