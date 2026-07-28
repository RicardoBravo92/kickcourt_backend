from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def active(self):
        return self.filter(deleted_at__isnull=True)


class FieldQuerySet(SoftDeleteQuerySet):
    def active(self):
        return super().active().filter(is_active=True)

    def by_type(self, field_type):
        return self.filter(field_type=field_type)

    def by_surface(self, surface):
        return self.filter(surface=surface)

    def search(self, query):
        return self.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query)
        )


class Field(models.Model):
    class FieldType(models.IntegerChoices):
        FIVE_A_SIDE = 5, '5 vs 5'
        SEVEN_A_SIDE = 7, '7 vs 7'
        ELEVEN_A_SIDE = 11, '11 vs 11'

    class SurfaceType(models.TextChoices):
        SYNTHETIC = 'SYNTHETIC', 'Synthetic Grass'
        NATURAL = 'NATURAL', 'Natural Grass'
        INDOOR = 'INDOOR', 'Indoor / Parquet'

    name = models.CharField(max_length=100)
    field_type = models.IntegerField(choices=FieldType.choices, default=FieldType.FIVE_A_SIDE)
    surface = models.CharField(max_length=20, choices=SurfaceType.choices, default=SurfaceType.SYNTHETIC)
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='fields/', blank=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = FieldQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['field_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['deleted_at']),
        ]

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])

    def __str__(self):
        return f"{self.name} ({self.get_field_type_display()}) - ${self.price_per_hour}/h"


class FieldSchedule(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'

    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('field', 'day_of_week')
        ordering = ['field', 'day_of_week']

    def __str__(self):
        return f"{self.field.name} - {self.get_day_of_week_display()}: {self.open_time}-{self.close_time}"


class FieldBlock(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='blocks')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='field_blocks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.field.name} - {self.date} {self.start_time}-{self.end_time}"
