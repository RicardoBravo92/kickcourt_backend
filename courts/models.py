from django.db import models
from django.utils import timezone


class SportType(models.TextChoices):
    FOOTBALL = 'FOOTBALL', 'Football'
    PADEL = 'PADEL', 'Padel'
    TENNIS = 'TENNIS', 'Tennis'
    BASKETBALL = 'BASKETBALL', 'Basketball'
    VOLLEYBALL = 'VOLLEYBALL', 'Volleyball'
    HOCKEY = 'HOCKEY', 'Hockey'


class SurfaceType(models.TextChoices):
    SYNTHETIC = 'SYNTHETIC', 'Synthetic'
    NATURAL = 'NATURAL', 'Natural Grass'
    INDOOR = 'INDOOR', 'Indoor'
    CLAY = 'CLAY', 'Clay'
    GRASS = 'GRASS', 'Grass'
    HARD = 'HARD', 'Hard Court'
    WOOD = 'WOOD', 'Wood'
    SAND = 'SAND', 'Sand'


SPORT_SURFACES = {
    SportType.FOOTBALL: [SurfaceType.SYNTHETIC, SurfaceType.NATURAL, SurfaceType.INDOOR],
    SportType.PADEL: [SurfaceType.SYNTHETIC, SurfaceType.INDOOR],
    SportType.TENNIS: [SurfaceType.CLAY, SurfaceType.GRASS, SurfaceType.HARD, SurfaceType.INDOOR],
    SportType.BASKETBALL: [SurfaceType.HARD, SurfaceType.WOOD, SurfaceType.INDOOR],
    SportType.VOLLEYBALL: [SurfaceType.SAND, SurfaceType.HARD, SurfaceType.INDOOR],
    SportType.HOCKEY: [SurfaceType.SYNTHETIC, SurfaceType.GRASS, SurfaceType.INDOOR],
}

SPORT_PLAYERS = {
    SportType.FOOTBALL: [5, 7, 11],
    SportType.PADEL: [2, 4],
    SportType.TENNIS: [1, 2],
    SportType.BASKETBALL: [5],
    SportType.VOLLEYBALL: [6],
    SportType.HOCKEY: [5, 6, 11],
}


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def active(self):
        return self.filter(deleted_at__isnull=True)


class CourtQuerySet(SoftDeleteQuerySet):
    def active(self):
        return super().active().filter(is_active=True)

    def by_sport(self, sport_type):
        return self.filter(sport_type=sport_type)

    def by_surface(self, surface):
        return self.filter(surface=surface)

    def search(self, query):
        return self.filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query)
        )


class Court(models.Model):
    name = models.CharField(max_length=100)
    sport_type = models.CharField(max_length=20, choices=SportType.choices, default=SportType.FOOTBALL)
    surface = models.CharField(max_length=20, choices=SurfaceType.choices, default=SurfaceType.SYNTHETIC)
    players_per_side = models.IntegerField(default=5)
    price_per_hour = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='courts/', blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='courts', null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = CourtQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['sport_type']),
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
        return f"{self.name} ({self.get_sport_type_display()}) - ${self.price_per_hour}/h"


class CourtSchedule(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'

    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('court', 'day_of_week')
        ordering = ['court', 'day_of_week']

    def __str__(self):
        return f"{self.court.name} - {self.get_day_of_week_display()}: {self.open_time}-{self.close_time}"


class CourtBlock(models.Model):
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='blocks')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='court_blocks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.court.name} - {self.date} {self.start_time}-{self.end_time}"
