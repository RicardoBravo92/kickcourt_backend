import pytest
from django.utils import timezone
from datetime import time, timedelta

from courts.models import Court, CourtBlock
from tests.factories import BookingFactory, CourtFactory, CourtBlockFactory

COURTS_URL = '/api/courts/'


def valid_court_payload():
    return {
        'name': 'Cancha Central',
        'sport_type': 'FOOTBALL',
        'surface': 'SYNTHETIC',
        'price_per_hour': '40.00',
    }


class TestCreateCourt:
    def test_vendor_can_create_court(self, vendor_api_client, vendor):
        response = vendor_api_client.post(COURTS_URL, valid_court_payload())
        assert response.status_code == 201
        assert Court.objects.get(pk=response.data['id']).vendor_id == vendor.id

    def test_admin_can_assign_vendor_at_create(self, admin_api_client, vendor):
        payload = valid_court_payload()
        payload['vendor'] = vendor.id
        response = admin_api_client.post(COURTS_URL, payload)
        assert response.status_code == 201
        assert Court.objects.get(pk=response.data['id']).vendor_id == vendor.id

    def test_client_cannot_create_court(self, client_api_client):
        response = client_api_client.post(COURTS_URL, valid_court_payload())
        assert response.status_code == 403

    def test_anonymous_can_list_and_retrieve(self, api_client, court):
        assert api_client.get(COURTS_URL).status_code == 200
        assert api_client.get(f'{COURTS_URL}{court.id}/').status_code == 200

    def test_anonymous_cannot_create(self, api_client):
        response = api_client.post(COURTS_URL, valid_court_payload())
        assert response.status_code == 401


class TestUpdateCourtOwnership:
    def test_vendor_can_update_own_court(self, vendor_api_client, vendor):
        court = CourtFactory(vendor=vendor)
        response = vendor_api_client.patch(f'{COURTS_URL}{court.id}/', {'name': 'Renamed'})
        assert response.status_code == 200
        assert response.data['name'] == 'Renamed'

    def test_vendor_cannot_update_other_vendor_court(self, vendor_api_client):
        other = CourtFactory()
        response = vendor_api_client.patch(f'{COURTS_URL}{other.id}/', {'name': 'Hijack'})
        assert response.status_code == 404

    def test_update_keeps_original_vendor(self, vendor_api_client, vendor):
        court = CourtFactory(vendor=vendor)
        response = vendor_api_client.patch(f'{COURTS_URL}{court.id}/', {'name': 'Still Mine'})
        assert response.status_code == 200
        assert Court.objects.get(pk=court.id).vendor_id == vendor.id

    def test_vendor_cannot_delete_other_vendor_court(self, vendor_api_client):
        other = CourtFactory()
        response = vendor_api_client.delete(f'{COURTS_URL}{other.id}/')
        assert response.status_code == 404

    def test_vendor_soft_deletes_own_court(self, vendor_api_client, vendor):
        court = CourtFactory(vendor=vendor)
        response = vendor_api_client.delete(f'{COURTS_URL}{court.id}/')
        assert response.status_code == 204
        court.refresh_from_db()
        assert court.deleted_at is not None
        assert not Court.objects.active().filter(pk=court.id).exists()

    def test_my_courts_filter(self, vendor_api_client, vendor):
        CourtFactory(vendor=vendor)
        CourtFactory()
        response = vendor_api_client.get(f'{COURTS_URL}?my_courts=true')
        assert response.status_code == 200
        assert response.data['count'] == 1


class TestAvailability:
    def test_returns_blocked_hours(self, api_client, court):
        tomorrow = timezone.localdate() + timedelta(days=1)
        CourtBlockFactory(court=court, date=tomorrow, start_time=time(10, 0), end_time=time(12, 0))

        response = api_client.get(f'{COURTS_URL}{court.id}/availability/?date={tomorrow}')
        assert response.status_code == 200
        slots = {slot['hour']: slot['status'] for slot in response.data['slots']}
        assert slots[10] == 'blocked'
        assert slots[11] == 'blocked'
        assert slots[9] == 'available'

    def test_soft_deleted_booking_does_not_block(self, api_client, user, court):
        tomorrow = timezone.localdate() + timedelta(days=1)
        booking = BookingFactory(
            user=user, court=court, date=tomorrow,
            start_time=time(10, 0), end_time=time(12, 0),
        )
        booking.delete()

        response = api_client.get(f'{COURTS_URL}{court.id}/availability/?date={tomorrow}')
        assert response.status_code == 200
        slots = {slot['hour']: slot['status'] for slot in response.data['slots']}
        assert slots[10] == 'available'
        assert slots[11] == 'available'

    def test_requires_date_param(self, api_client, court):
        response = api_client.get(f'{COURTS_URL}{court.id}/availability/')
        assert response.status_code == 400

    def test_invalid_date_format(self, api_client, court):
        response = api_client.get(f'{COURTS_URL}{court.id}/availability/?date=not-a-date')
        assert response.status_code == 400