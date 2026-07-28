from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'court', 'date', 'start_time', 'end_time', 'status', 'total_price', 'commission')
    list_filter = ('status', 'date')
    search_fields = ('user__username', 'court__name')
