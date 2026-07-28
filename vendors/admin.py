from django.contrib import admin
from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'is_approved', 'commission_rate', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('business_name', 'user__username')
