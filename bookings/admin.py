from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'field', 'date', 'start_time', 'end_time', 'status', 'total_price')
    list_filter = ('status', 'date')
    search_fields = ('user__username', 'field__name')
