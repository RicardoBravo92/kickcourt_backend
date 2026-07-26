from django.test import TestCase
from django.utils import timezone
from datetime import time, timedelta
from accounts.models import User
from fields.models import Field
from .models import Booking
from .services import validate_booking_slots, create_booking


class BookingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.field = Field.objects.create(
            name='Cancha 1', price_per_hour=50.00
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)

    def test_booking_creation(self):
        booking = Booking.objects.create(
            user=self.user,
            field=self.field,
            date=self.tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            total_price=100.00,
        )
        self.assertEqual(booking.status, Booking.Status.PENDING)

    def test_booking_str(self):
        booking = Booking.objects.create(
            user=self.user,
            field=self.field,
            date=self.tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            total_price=100.00,
        )
        self.assertIn('Cancha 1', str(booking))


class BookingServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.field = Field.objects.create(
            name='Cancha 1', price_per_hour=50.00
        )
        self.tomorrow = timezone.now().date() + timedelta(days=1)

    def test_validate_valid_booking(self):
        validate_booking_slots(self.field, self.tomorrow, time(10, 0), time(12, 0))

    def test_validate_overlapping_booking(self):
        Booking.objects.create(
            user=self.user,
            field=self.field,
            date=self.tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
            total_price=100.00,
        )
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            validate_booking_slots(self.field, self.tomorrow, time(11, 0), time(13, 0))

    def test_create_booking(self):
        booking = create_booking(
            user=self.user,
            field=self.field,
            date=self.tomorrow,
            start_time=time(10, 0),
            end_time=time(12, 0),
        )
        self.assertEqual(booking.total_price, 100.00)


class BookingQuerySetTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.field = Field.objects.create(name='Cancha 1', price_per_hour=50.00)
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)

        Booking.objects.create(
            user=self.user, field=self.field, date=tomorrow,
            start_time=time(10, 0), end_time=time(12, 0),
            total_price=100.00, status='PENDING'
        )
        Booking.objects.create(
            user=self.user, field=self.field, date=today - timedelta(days=1),
            start_time=time(10, 0), end_time=time(12, 0),
            total_price=100.00, status='COMPLETED'
        )

    def test_pending_queryset(self):
        self.assertEqual(Booking.objects.pending().count(), 1)

    def test_upcoming_queryset(self):
        self.assertEqual(Booking.objects.upcoming().count(), 1)

    def test_past_queryset(self):
        self.assertEqual(Booking.objects.past().count(), 1)
