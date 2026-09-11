import pytest
from datetime import time, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from bookings.models import Booking
from bookings.services import (
    create_booking,
    validate_booking_slots,
    calculate_total_price,
    calculate_commission,
)
from courts.models import Court
from tests.factories import (
    UserFactory,
    CourtFactory,
    CourtBlockFactory,
    BookingFactory,
)


class TestPricing:
    def test_total_price_is_hours_times_rate(self, court):
        assert calculate_total_price(court, time(10, 0), time(12, 0)) == Decimal('100.00')

    def test_commission_percentage(self, court):
        assert calculate_commission(Decimal('100'), Decimal('10')) == Decimal('10')

    def test_half_hour_pricing(self, court):
        court.price_per_hour = Decimal('50.00')
        assert calculate_total_price(court, time(10, 0), time(10, 30)) == Decimal('25.00')


class TestSlotValidation:
    def test_rejects_start_equal_end(self, court):
        with pytest.raises(ValidationError):
            validate_booking_slots(court, timezone.localdate() + timedelta(days=1), time(10, 0), time(10, 0))

    def test_rejects_start_after_end(self, court):
        with pytest.raises(ValidationError):
            validate_booking_slots(court, timezone.localdate() + timedelta(days=1), time(12, 0), time(10, 0))

    def test_rejects_past_date(self, court):
        with pytest.raises(ValidationError) as excinfo:
            validate_booking_slots(court, timezone.localdate() - timedelta(days=1), time(10, 0), time(12, 0))
        assert 'date' in excinfo.value.error_dict

    def test_rejects_blocked_slot(self, court):
        tomorrow = timezone.localdate() + timedelta(days=1)
        CourtBlockFactory(court=court, date=tomorrow, start_time=time(10, 0), end_time=time(12, 0))
        with pytest.raises(ValidationError):
            validate_booking_slots(court, tomorrow, time(10, 0), time(12, 0))

    def test_allows_slot_adjacent_to_block(self, court):
        tomorrow = timezone.localdate() + timedelta(days=1)
        CourtBlockFactory(court=court, date=tomorrow, start_time=time(10, 0), end_time=time(12, 0))
        validate_booking_slots(court, tomorrow, time(12, 0), time(14, 0))

    def test_rejects_overlapping_booking(self, court):
        tomorrow = timezone.localdate() + timedelta(days=1)
        BookingFactory(court=court, date=tomorrow, start_time=time(10, 0), end_time=time(12, 0))
        with pytest.raises(ValidationError):
            validate_booking_slots(court, tomorrow, time(11, 0), time(13, 0))

    def test_exclude_pk_allows_same_booking(self, court):
        tomorrow = timezone.localdate() + timedelta(days=1)
        booking = BookingFactory(court=court, date=tomorrow, start_time=time(10, 0), end_time=time(12, 0))
        validate_booking_slots(court, tomorrow, time(10, 0), time(12, 0), exclude_pk=booking.pk)


class TestCreateBookingService:
    def test_sets_vendor_and_price(self, user, court):
        booking = create_booking(user, court, timezone.localdate() + timedelta(days=1), time(10, 0), time(12, 0))
        assert booking.total_price == Decimal('100.00')
        assert booking.status == Booking.Status.PENDING

    def test_commission_when_vendor_approved(self, user, vendor):
        court = CourtFactory(vendor=vendor)
        booking = create_booking(user, court, timezone.localdate() + timedelta(days=1), time(10, 0), time(12, 0))
        assert booking.commission == Decimal('10.00')

    def test_no_commission_when_vendor_unapproved(self, user, vendor):
        vendor.is_approved = False
        vendor.save()
        court = CourtFactory(vendor=vendor)
        booking = create_booking(user, court, timezone.localdate() + timedelta(days=1), time(10, 0), time(12, 0))
        assert booking.commission == Decimal('0')


@pytest.mark.django_db
class TestModelBehaviors:
    def test_booking_soft_delete(self):
        booking = BookingFactory()
        booking.delete()
        booking.refresh_from_db()
        assert booking.deleted_at is not None
        assert not Booking.objects.active().filter(pk=booking.pk).exists()

    def test_booking_restore(self):
        booking = BookingFactory()
        booking.delete()
        booking.restore()
        booking.refresh_from_db()
        assert booking.deleted_at is None

    def test_court_soft_delete(self):
        court = CourtFactory()
        court.delete()
        court.refresh_from_db()
        assert court.deleted_at is not None
        assert not Court.objects.active().filter(pk=court.pk).exists()

    def test_pending_and_confirmed_querysets(self):
        BookingFactory(status=Booking.Status.PENDING)
        BookingFactory(status=Booking.Status.CONFIRMED)
        BookingFactory(status=Booking.Status.CANCELLED)
        assert Booking.objects.pending().count() == 1
        assert Booking.objects.confirmed().count() == 1

    def test_upcoming_excludes_past(self):
        BookingFactory(date=timezone.localdate() + timedelta(days=1))
        BookingFactory(date=timezone.localdate() - timedelta(days=1))
        assert Booking.objects.upcoming().count() == 1
        assert Booking.objects.past().count() == 1