import pytest
from datetime import time, timedelta

from django.utils import timezone

from bookings.models import Booking
from tests.factories import (
    BookingFactory,
    CourtFactory,
    CourtBlockFactory,
    UserFactory,
)

BOOKINGS_URL = '/api/bookings/'


def future_booking_payload(court, days=1):
    date = timezone.localdate() + timedelta(days=days)
    return {
        'court': court.id,
        'date': str(date),
        'start_time': '10:00',
        'end_time': '12:00',
    }


class TestCreateBooking:
    def test_client_can_create_booking(self, client_api_client, court, client_user):
        response = client_api_client.post(BOOKINGS_URL, future_booking_payload(court))
        assert response.status_code == 201
        assert response.data['status'] == Booking.Status.PENDING
        assert response.data['user'] == client_user.username
        assert str(response.data['total_price']) == '100.00'

    def test_commission_computed_for_approved_vendor(self, client_api_client, court_with_vendor):
        response = client_api_client.post(BOOKINGS_URL, future_booking_payload(court_with_vendor))
        assert response.status_code == 201
        assert str(response.data['commission']) == '10.00'

    def test_vendor_cannot_create_booking(self, vendor_api_client, court):
        response = vendor_api_client.post(BOOKINGS_URL, future_booking_payload(court))
        assert response.status_code == 403

    def test_anonymous_cannot_create_booking(self, api_client, court):
        response = api_client.post(BOOKINGS_URL, future_booking_payload(court))
        assert response.status_code == 401

    def test_overlapping_booking_is_rejected(self, client_api_client, court):
        client_api_client.post(BOOKINGS_URL, future_booking_payload(court))
        payload = future_booking_payload(court)
        payload['start_time'] = '11:00'
        payload['end_time'] = '13:00'
        response = client_api_client.post(BOOKINGS_URL, payload)
        assert response.status_code == 400

    def test_blocked_time_slot_is_rejected(self, client_api_client, court):
        CourtBlockFactory(court=court, date=timezone.localdate() + timedelta(days=1),
                          start_time=time(9, 0), end_time=time(11, 0))
        response = client_api_client.post(BOOKINGS_URL, future_booking_payload(court))
        assert response.status_code == 400

    def test_past_date_is_rejected(self, client_api_client, court):
        payload = future_booking_payload(court, days=-1)
        response = client_api_client.post(BOOKINGS_URL, payload)
        assert response.status_code == 400


class TestUpdateBookingStatus:
    def test_status_is_read_only(self, client_api_client, court):
        response = client_api_client.post(BOOKINGS_URL, future_booking_payload(court))
        booking_id = response.data['id']

        response = client_api_client.patch(
            f'{BOOKINGS_URL}{booking_id}/',
            {'status': Booking.Status.CONFIRMED},
        )
        assert response.status_code == 200
        assert response.data['status'] == Booking.Status.PENDING

        booking = Booking.objects.get(pk=booking_id)
        assert booking.status == Booking.Status.PENDING

    def test_total_price_recalculated_on_update(self, client_api_client, court):
        response = client_api_client.post(BOOKINGS_URL, future_booking_payload(court))
        booking_id = response.data['id']

        response = client_api_client.patch(
            f'{BOOKINGS_URL}{booking_id}/',
            {'end_time': '14:00'},
        )
        assert response.status_code == 200
        assert str(response.data['total_price']) == '200.00'


class TestBookingActions:
    @pytest.fixture
    def vendor_tomorrow(self):
        return timezone.localdate() + timedelta(days=1)

    @pytest.fixture
    def pending_booking(self, user, court):
        return BookingFactory(user=user, court=court, status=Booking.Status.PENDING)

    def test_cancel_pending_booking(self, client_api_client, client_user, court):
        booking = BookingFactory(user=client_user, court=court)
        response = client_api_client.post(f'{BOOKINGS_URL}{booking.id}/cancel/')
        assert response.status_code == 200
        booking.refresh_from_db()
        assert booking.status == Booking.Status.CANCELLED

    def test_cannot_cancel_completed_booking(self, client_api_client, client_user, court):
        booking = BookingFactory(user=client_user, court=court, status=Booking.Status.COMPLETED)
        response = client_api_client.post(f'{BOOKINGS_URL}{booking.id}/cancel/')
        assert response.status_code == 400
        booking.refresh_from_db()
        assert booking.status == Booking.Status.COMPLETED

    def test_client_cannot_confirm_booking(self, client_api_client, pending_booking):
        response = client_api_client.post(f'{BOOKINGS_URL}{pending_booking.id}/confirm/')
        assert response.status_code == 403

    def test_admin_can_confirm_booking(self, admin_api_client, pending_booking):
        response = admin_api_client.post(f'{BOOKINGS_URL}{pending_booking.id}/confirm/')
        assert response.status_code == 200
        pending_booking.refresh_from_db()
        assert pending_booking.status == Booking.Status.CONFIRMED

    def test_vendor_can_confirm_own_court_booking(self, vendor_api_client, vendor):
        court = CourtFactory(vendor=vendor)
        player = UserFactory()
        booking = BookingFactory(user=player, court=court)
        response = vendor_api_client.post(f'{BOOKINGS_URL}{booking.id}/confirm/')
        assert response.status_code == 200

    def test_cannot_confirm_cancelled_booking(self, admin_api_client, user, court):
        booking = BookingFactory(user=user, court=court, status=Booking.Status.CANCELLED)
        response = admin_api_client.post(f'{BOOKINGS_URL}{booking.id}/confirm/')
        assert response.status_code == 400


class TestBookingScoping:
    def test_client_sees_only_own_bookings(self, client_api_client, client_user):
        court = CourtFactory()
        BookingFactory(user=client_user, court=court)
        BookingFactory(user=UserFactory(), court=court)

        response = client_api_client.get(BOOKINGS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_vendor_sees_only_own_court_bookings(self, vendor_api_client, vendor):
        own_court = CourtFactory(vendor=vendor)
        other_court = CourtFactory()
        BookingFactory(user=UserFactory(), court=own_court)
        BookingFactory(user=UserFactory(), court=other_court)

        response = vendor_api_client.get(BOOKINGS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_admin_sees_all_bookings(self, admin_api_client, court):
        BookingFactory(user=UserFactory(), court=court)
        BookingFactory(user=UserFactory(), court=court)

        response = admin_api_client.get(BOOKINGS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 2

    def test_my_bookings_only_upcoming(self, client_api_client, client_user, court):
        BookingFactory(user=client_user, court=court, date=timezone.localdate() + timedelta(days=1))
        BookingFactory(user=client_user, court=court, date=timezone.localdate() - timedelta(days=1))

        response = client_api_client.get(f'{BOOKINGS_URL}my_bookings/')
        assert response.status_code == 200
        assert response.data['count'] == 1


class TestDashboardExport:
    def test_admin_can_export_csv(self, admin_api_client):
        response = admin_api_client.get('/api/dashboard/export/csv/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        assert b'User,Email,Court' in response.content

    def test_csv_contains_bookings(self, admin_api_client, user, court):
        BookingFactory(user=user, court=court)
        response = admin_api_client.get('/api/dashboard/export/csv/')
        assert response.status_code == 200
        assert court.name.encode() in response.content

    def test_non_admin_cannot_export_csv(self, client_api_client):
        response = client_api_client.get('/api/dashboard/export/csv/')
        assert response.status_code == 403

    def test_vendor_cannot_export_csv(self, vendor_api_client):
        response = vendor_api_client.get('/api/dashboard/export/csv/')
        assert response.status_code == 403

    def test_admin_stats_available(self, admin_api_client):
        response = admin_api_client.get('/api/dashboard/stats/')
        assert response.status_code == 200
        assert 'total_bookings' in response.data