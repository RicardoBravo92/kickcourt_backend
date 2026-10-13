from django.conf import settings
from django.db import models


class Message(models.Model):
    """Chat message tied to a booking (client <-> vendor/admin)."""

    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['booking', 'created_at']),
        ]

    def __str__(self):
        return f'{self.sender} -> booking {self.booking_id}: {self.text[:40]}'