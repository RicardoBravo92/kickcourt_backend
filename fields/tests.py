from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import Field


class FieldModelTest(TestCase):
    def setUp(self):
        self.field = Field.objects.create(
            name='Cancha 1',
            field_type=Field.FieldType.FIVE_A_SIDE,
            surface=Field.SurfaceType.SYNTHETIC,
            price_per_hour=50.00,
        )

    def test_field_str(self):
        self.assertIn('Cancha 1', str(self.field))

    def test_field_default_values(self):
        self.assertTrue(self.field.is_active)


class FieldViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.field = Field.objects.create(
            name='Cancha Test',
            field_type=7,
            surface='NATURAL',
            price_per_hour=75.00,
        )

    def test_list_fields_public(self):
        response = self.client.get('/api/fields/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_field_requires_auth(self):
        data = {'name': 'New Field', 'price_per_hour': 50.00}
        response = self.client.post('/api/fields/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class FieldQuerySetTest(TestCase):
    def setUp(self):
        Field.objects.create(name='Cancha Norte', price_per_hour=50, is_active=True)
        Field.objects.create(name='Cancha Sur', price_per_hour=50, is_active=False)

    def test_active_queryset(self):
        self.assertEqual(Field.objects.active().count(), 1)

    def test_search_queryset(self):
        self.assertEqual(Field.objects.search('Norte').count(), 1)
