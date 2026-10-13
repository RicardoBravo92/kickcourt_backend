from django.contrib import admin

from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'sender', 'text', 'created_at', 'read_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'sender__username')