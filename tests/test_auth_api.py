import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from tests.factories import UserFactory, AdminUserFactory

User = get_user_model()

REGISTER_URL = '/api/register/'
CHECK_AVAILABILITY_URL = '/api/check-availability/'
FORGOT_URL = '/api/password/forgot/'
RESET_URL = '/api/password/reset/'
LOGIN_URL = '/api/auth/login/'


def valid_register_payload():
    return {
        'username': 'newclient',
        'email': 'newclient@example.com',
        'password': 'StrongPass123!',
        'password_confirm': 'StrongPass123!',
    }


def details(response):
    """Unwrap the custom error envelope: {error, status_code, message, details}."""
    return response.data['details']


class TestRegister:
    def test_register_creates_client_user(self, api_client):
        response = api_client.post(REGISTER_URL, valid_register_payload())
        assert response.status_code == 201
        assert User.objects.get(username='newclient').role == User.Roles.CLIENT
        assert User.objects.filter(email='newclient@example.com').exists()

    def test_register_rejects_duplicate_email_case_insensitive(self, api_client, user):
        payload = valid_register_payload()
        payload['email'] = user.email.upper()
        response = api_client.post(REGISTER_URL, payload)
        assert response.status_code == 400
        assert 'email' in details(response)

    def test_register_rejects_duplicate_username(self, api_client, user):
        payload = valid_register_payload()
        payload['username'] = user.username
        response = api_client.post(REGISTER_URL, payload)
        assert response.status_code == 400

    def test_register_rejects_mismatched_passwords(self, api_client):
        payload = valid_register_payload()
        payload['password_confirm'] = 'DifferentPass123!'
        response = api_client.post(REGISTER_URL, payload)
        assert response.status_code == 400

    def test_register_lowers_email_before_storing(self, api_client):
        payload = valid_register_payload()
        payload['email'] = 'NEWCLIENT@Example.COM'
        response = api_client.post(REGISTER_URL, payload)
        assert response.status_code == 201
        assert User.objects.filter(email='newclient@example.com').exists()


class TestCheckAvailability:
    def test_reports_email_taken_case_insensitive(self, api_client, user):
        response = api_client.post(
            CHECK_AVAILABILITY_URL,
            {'email': user.email.upper()},
        )
        assert response.status_code == 200
        assert response.data['email_available'] is False

    def test_reports_email_free(self, api_client):
        response = api_client.post(
            CHECK_AVAILABILITY_URL,
            {'email': 'free@example.com'},
        )
        assert response.status_code == 200
        assert response.data['email_available'] is True

    def test_reports_username_taken(self, api_client, user):
        response = api_client.post(
            CHECK_AVAILABILITY_URL,
            {'username': user.username},
        )
        assert response.status_code == 200
        assert response.data['username_available'] is False


class TestForgotPassword:
    def test_returns_generic_message_for_unknown_email(self, api_client, mock_resend):
        response = api_client.post(FORGOT_URL, {'email': 'nobody@example.com'})
        assert response.status_code == 200
        assert 'If an account with this email exists' in response.data['detail']
        assert not mock_resend.called

    def test_returns_generic_message_for_existing_email(self, api_client, user, mock_resend):
        response = api_client.post(FORGOT_URL, {'email': user.email})
        assert response.status_code == 200
        assert response.data['detail'] == 'If an account with this email exists, a reset link has been sent.'
        assert mock_resend.called

    def test_email_lookup_is_case_insensitive(self, api_client, user, mock_resend):
        response = api_client.post(FORGOT_URL, {'email': user.email.upper()})
        assert response.status_code == 200
        assert mock_resend.called


class TestResetPassword:
    def _reset_payload(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return {'uid': uid, 'token': token, 'new_password': 'NewStrongPass123!'}

    def test_resets_password_with_valid_link(self, api_client, user):
        user.set_password('OldPass123!')
        user.save()
        response = api_client.post(RESET_URL, self._reset_payload(user))
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password('NewStrongPass123!')

    def test_rejects_invalid_token(self, api_client, user):
        payload = self._reset_payload(user)
        payload['token'] = 'invalid-token'
        response = api_client.post(RESET_URL, payload)
        assert response.status_code == 400

    def test_rejects_invalid_uid(self, api_client):
        payload = self._reset_payload(UserFactory.build())
        payload['uid'] = urlsafe_base64_encode(force_bytes(999999))
        response = api_client.post(RESET_URL, payload)
        assert response.status_code == 400

    def test_rejects_short_password(self, api_client, user):
        payload = self._reset_payload(user)
        payload['new_password'] = 'short'
        response = api_client.post(RESET_URL, payload)
        assert response.status_code == 400

    def test_rejects_missing_fields(self, api_client):
        response = api_client.post(RESET_URL, {})
        assert response.status_code == 400


class TestChangePassword:
    def test_changes_password_with_correct_old(self, client_api_client, client_user):
        response = client_api_client.post('/api/profile/change-password/', {
            'old_password': 'testpass123',
            'new_password': 'NewStrongPass123!',
            'new_password_confirm': 'NewStrongPass123!',
        })
        assert response.status_code == 200
        client_user.refresh_from_db()
        assert client_user.check_password('NewStrongPass123!')

    def test_rejects_wrong_old_password(self, client_api_client):
        response = client_api_client.post('/api/profile/change-password/', {
            'old_password': 'wrong-old-pass',
            'new_password': 'NewStrongPass123!',
            'new_password_confirm': 'NewStrongPass123!',
        })
        assert response.status_code == 400


class TestProfile:
    def test_profile_requires_auth(self, api_client):
        response = api_client.get('/api/profile/')
        assert response.status_code == 401

    def test_profile_returns_current_user(self, client_api_client, client_user):
        response = client_api_client.get('/api/profile/')
        assert response.status_code == 200
        assert response.data['username'] == client_user.username

    def test_profile_patch_updates_phone(self, client_api_client, client_user):
        response = client_api_client.patch('/api/profile/', {'phone_number': '1160000000'})
        assert response.status_code == 200
        client_user.refresh_from_db()
        assert client_user.phone_number == '1160000000'


class TestLogin:
    def test_login_with_email(self, api_client, user):
        response = api_client.post(LOGIN_URL, {
            'username': user.email,
            'password': 'testpass123',
        })
        assert response.status_code == 200
        assert 'access' in response.data
        _, claims_json, _ = response.data['access'].split('.')
        import base64
        padded = claims_json + '=' * (-len(claims_json) % 4)
        claims = __import__('json').loads(base64.urlsafe_b64decode(padded))
        assert claims['role'] == user.role

    def test_login_with_username(self, api_client, user):
        response = api_client.post(LOGIN_URL, {
            'username': user.username,
            'password': 'testpass123',
        })
        assert response.status_code == 200

    def test_login_with_unknown_email(self, api_client):
        response = api_client.post(LOGIN_URL, {
            'username': 'nobody@example.com',
            'password': 'testpass123',
        })
        assert response.status_code == 400