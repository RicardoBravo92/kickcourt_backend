import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from fields.models import Field
from bookings.models import Booking

User = get_user_model()

FIELDS_DATA = [
    {"name": "Goal Arena", "field_type": 5, "surface": "SYNTHETIC", "price_per_hour": 25.00, "description": "5v5 synthetic field ideal for quick matches."},
    {"name": "Net Field", "field_type": 5, "surface": "SYNTHETIC", "price_per_hour": 28.00, "description": "Synthetic field with night lighting."},
    {"name": "River Plate Field", "field_type": 7, "surface": "NATURAL", "price_per_hour": 40.00, "description": "7v7 natural grass field."},
    {"name": "Boca Juniors Field", "field_type": 7, "surface": "SYNTHETIC", "price_per_hour": 35.00, "description": "Spacious synthetic field with bleachers."},
    {"name": "Central Stadium", "field_type": 11, "surface": "NATURAL", "price_per_hour": 70.00, "description": "Professional 11v11 field with natural grass."},
    {"name": "Futsal Arena", "field_type": 5, "surface": "INDOOR", "price_per_hour": 32.00, "description": "Indoor court with parquet flooring."},
    {"name": "North Sports Field", "field_type": 7, "surface": "NATURAL", "price_per_hour": 38.00, "description": "Natural grass field in the north side."},
    {"name": "South Soccer", "field_type": 5, "surface": "SYNTHETIC", "price_per_hour": 22.00, "description": "Affordable and accessible synthetic field."},
    {"name": "Club Mayor Field", "field_type": 11, "surface": "SYNTHETIC", "price_per_hour": 80.00, "description": "Professional synthetic field with locker rooms."},
    {"name": "Indoor Pro", "field_type": 5, "surface": "INDOOR", "price_per_hour": 30.00, "description": "Indoor court with excellent lighting."},
]

USERS_DATA = [
    {"username": "admin", "email": "admin@soccer.com", "role": "ADMIN", "password": "Admin1234!", "phone_number": "+5491100000000"},
    {"username": "carlos", "email": "carlos@email.com", "role": "CLIENT", "password": "Client1234!", "phone_number": "+5491111111111"},
    {"username": "maria", "email": "maria@email.com", "role": "CLIENT", "password": "Client1234!", "phone_number": "+5491122222222"},
    {"username": "diego", "email": "diego@email.com", "role": "CLIENT", "password": "Client1234!", "phone_number": "+5491133333333"},
    {"username": "lucia", "email": "lucia@email.com", "role": "CLIENT", "password": "Client1234!", "phone_number": "+5491144444444"},
]

BOOKING_STATUSES = [Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.CANCELLED, Booking.Status.COMPLETED]


class Command(BaseCommand):
    help = "Seed the database with sample users, fields, and bookings"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            Booking.objects.all().hard_delete()
            Field.objects.all().hard_delete()
            User.objects.filter(is_superuser=False).delete()

        self.stdout.write("Seeding users...")
        users = self._seed_users()

        self.stdout.write("Seeding fields...")
        fields = self._seed_fields()

        self.stdout.write("Seeding bookings...")
        self._seed_bookings(users, fields)

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))

    def _seed_users(self):
        users = []
        for data in USERS_DATA:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"],
                    "role": data["role"],
                    "phone_number": data["phone_number"],
                },
            )
            user.set_password(data["password"])
            user.role = data["role"]
            user.save()
            if created:
                self.stdout.write(f"  Created user: {user.username}")
            else:
                self.stdout.write(f"  Updated user: {user.username}")
            users.append(user)
        return users

    def _seed_fields(self):
        fields = []
        for data in FIELDS_DATA:
            field, created = Field.objects.get_or_create(
                name=data["name"],
                defaults=data,
            )
            if created:
                self.stdout.write(f"  Created field: {field.name}")
            else:
                self.stdout.write(f"  Field already exists: {field.name}")
            fields.append(field)
        return fields

    def _seed_bookings(self, users, fields):
        clients = [u for u in users if u.role == "CLIENT"]
        if not clients:
            self.stdout.write(self.style.WARNING("No clients found, skipping bookings."))
            return

        today = date.today()
        hours = [
            (time(9, 0), time(10, 0)),
            (time(10, 0), time(11, 0)),
            (time(11, 0), time(12, 0)),
            (time(14, 0), time(15, 0)),
            (time(15, 0), time(16, 0)),
            (time(16, 0), time(17, 0)),
            (time(17, 0), time(18, 0)),
            (time(18, 0), time(19, 0)),
            (time(19, 0), time(20, 0)),
            (time(20, 0), time(21, 0)),
        ]

        count = 0
        for i in range(15):
            user = random.choice(clients)
            field = random.choice(fields)
            booking_date = today + timedelta(days=random.randint(-10, 20))
            start, end = random.choice(hours)
            status = random.choice(BOOKING_STATUSES)
            duration = (end.hour + end.minute / 60) - (start.hour + start.minute / 60)
            total_price = Decimal(str(field.price_per_hour)) * Decimal(str(duration))

            booking, created = Booking.objects.get_or_create(
                user=user,
                field=field,
                date=booking_date,
                start_time=start,
                defaults={
                    "end_time": end,
                    "total_price": total_price,
                    "status": status,
                },
            )
            if created:
                count += 1
                self.stdout.write(f"  Created booking: {field.name} on {booking_date} ({status})")

        self.stdout.write(f"  Total bookings created: {count}")
