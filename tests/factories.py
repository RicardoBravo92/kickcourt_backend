import factory
from datetime import time, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import User
from courts.models import Court, CourtBlock
from vendors.models import Vendor
from bookings.models import Booking


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = 'testpass123'
    role = User.Roles.CLIENT
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop('password', None)
        user = super()._create(model_class, *args, **kwargs)
        if password:
            user.set_password(password)
            user.save()
        return user


class AdminUserFactory(UserFactory):
    role = User.Roles.ADMIN
    is_staff = True
    is_superuser = True


class VendorUserFactory(UserFactory):
    role = User.Roles.VENDOR


class VendorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vendor

    user = factory.SubFactory(VendorUserFactory)
    business_name = factory.Sequence(lambda n: f"Vendor {n}")
    phone = '1155550000'
    address = 'Av. Siempre Viva 123'
    institution_number = '20-12345678-9'
    is_approved = True
    commission_rate = Decimal('10.00')


class CourtFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Court

    name = factory.Sequence(lambda n: f"Court {n}")
    sport_type = 'FOOTBALL'
    surface = 'SYNTHETIC'
    players_per_side = 5
    price_per_hour = Decimal('50.00')
    is_active = True
    vendor = None


class CourtBlockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CourtBlock

    court = factory.SubFactory(CourtFactory)
    date = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=1))
    start_time = time(10, 0)
    end_time = time(12, 0)
    reason = 'Maintenance'


class BookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Booking

    user = factory.SubFactory(UserFactory)
    court = factory.SubFactory(CourtFactory)
    date = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=1))
    start_time = time(10, 0)
    end_time = time(12, 0)
    total_price = Decimal('100.00')
    commission = Decimal('10.00')
    status = Booking.Status.PENDING


def future_date(days=1):
    return timezone.localdate() + timedelta(days=days)