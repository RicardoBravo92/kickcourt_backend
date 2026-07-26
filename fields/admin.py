from django.contrib import admin
from .models import Field


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'field_type', 'surface', 'price_per_hour', 'is_active', 'deleted_at')
    list_filter = ('field_type', 'surface', 'is_active')
    readonly_fields = ('deleted_at',)
