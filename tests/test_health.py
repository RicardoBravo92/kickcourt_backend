import pytest


@pytest.mark.django_db
def test_health_returns_ok(client):
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'ok'}


@pytest.mark.django_db
def test_health_with_trailing_slash_returns_ok(client):
    response = client.get('/health/')

    assert response.status_code == 200


@pytest.mark.django_db
def test_health_rejects_non_get(client):
    response = client.post('/health')

    assert response.status_code == 405
