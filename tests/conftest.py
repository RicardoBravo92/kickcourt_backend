import pytest
from unittest.mock import patch
from django.utils import timezone

from tests.factories import (
    UserFactory,
    AdminUserFactory,
    VendorFactory,
    VendorUserFactory,
)


@pytest.fixture(autouse=True)
def mock_resend():
    """Mock external Resend email service so tests never hit the network."""
    with patch('resend.Emails.send') as mock_send:
        mock_send.return_value = {'id': 'mock-email-id'}
        yield mock_send


@pytest.fixture(autouse=True)
def utc_timezone(settings):
    """Ensure consistent timezone for tests."""
    settings.TIME_ZONE = 'UTC'


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def admin_user(db):
    return AdminUserFactory()


@pytest.fixture
def vendor(db):
    vendor = VendorFactory()
    return vendor


@pytest.fixture
def vendor_user(db, vendor):
    return vendor.user


@pytest.fixture
def api_client(db):
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def client_user(db):
    return UserFactory()


@pytest.fixture
def client_api_client(api_client, client_user):
    api_client.force_authenticate(user=client_user)
    return api_client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def vendor_api_client(api_client, vendor_user):
    api_client.force_authenticate(user=vendor_user)
    return api_client


@pytest.fixture
def court(db, vendor=None):
    from tests.factories import CourtFactory
    return CourtFactory(vendor=vendor)


@pytest.fixture
def court_with_vendor(db, vendor):
    from tests.factories import CourtFactory
    return CourtFactory(vendor=vendor)