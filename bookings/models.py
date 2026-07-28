from django.db import models
from django.utils import timezone
from accounts.models import User


class BookingQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(status=Booking.Status.PENDING)

    def confirmed(self):
        return self.filter(status=Booking.Status.CONFIRMED)

    def for_user(self, user):
        return self.filter(user=user)

    def for_court(self, court):
        return self.filter(court=court)

    def for_vendor(self, vendor):
        return self.filter(court__vendor=vendor)

    def upcoming(self):
        return self.filter(date__gte=timezone.now().date())

    def past(self):
        return self.filter(date__lt=timezone.now().date())

    def with_court(self):
        return self.select_related('court')

    def with_user(self):
        return self.select_related('user')


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    court = models.ForeignKey('courts.Court', on_delete=models.CASCADE, related_name='bookings')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['status']),
            models.Index(fields=['user', 'date']),
            models.Index(fields=['court', 'date']),
            models.Index(fields=['deleted_at']),
        ]

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    def __str__(self):
        return f"Booking {self.court.name} - {self.date} ({self.start_time} - {self.end_time})"
