from django.db import models


class FieldQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

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

    objects = FieldQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['field_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_field_type_display()}) - ${self.price_per_hour}/h"
