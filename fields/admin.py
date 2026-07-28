from django.contrib import admin
from .models import Field, FieldSchedule, FieldBlock


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'field_type', 'surface', 'price_per_hour', 'is_active', 'deleted_at')
    list_filter = ('field_type', 'surface', 'is_active')
    readonly_fields = ('deleted_at',)


@admin.register(FieldSchedule)
class FieldScheduleAdmin(admin.ModelAdmin):
    list_display = ('field', 'day_of_week', 'open_time', 'close_time', 'is_active')
    list_filter = ('field', 'day_of_week', 'is_active')


@admin.register(FieldBlock)
class FieldBlockAdmin(admin.ModelAdmin):
    list_display = ('field', 'date', 'start_time', 'end_time', 'reason', 'created_by')
    list_filter = ('field', 'date')
