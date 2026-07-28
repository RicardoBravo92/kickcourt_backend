import random
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from courts.models import Court, CourtSchedule, CourtBlock, SportType, SurfaceType
from bookings.models import Booking
from vendors.models import Vendor

User = get_user_model()

COURTS_DATA = [
    {"name": "Goal Arena", "sport_type": SportType.FOOTBALL, "surface": SurfaceType.SYNTHETIC, "players_per_side": 5, "price_per_hour": 25.00, "description": "Synthetic football court for 5v5 action."},
    {"name": "Padel Elite", "sport_type": SportType.PADEL, "surface": SurfaceType.SYNTHETIC, "players_per_side": 2, "price_per_hour": 20.00, "description": "Professional padel court."},
    {"name": "River Plate Field", "sport_type": SportType.FOOTBALL, "surface": SurfaceType.NATURAL, "players_per_side": 7, "price_per_hour": 40.00, "description": "Natural grass 7v7 football field."},
    {"name": "Tennis Club Central", "sport_type": SportType.TENNIS, "surface": SurfaceType.CLAY, "players_per_side": 1, "price_per_hour": 35.00, "description": "Clay tennis court with lights."},
    {"name": "Central Stadium", "sport_type": SportType.FOOTBALL, "surface": SurfaceType.NATURAL, "players_per_side": 11, "price_per_hour": 70.00, "description": "Professional 11v11 football field."},
    {"name": "Futsal Arena", "sport_type": SportType.FOOTBALL, "surface": SurfaceType.INDOOR, "players_per_side": 5, "price_per_hour": 32.00, "description": "Indoor futsal court."},
    {"name": "Padel Indoor Pro", "sport_type": SportType.PADEL, "surface": SurfaceType.INDOOR, "players_per_side": 2, "price_per_hour": 28.00, "description": "Indoor padel with premium glass walls."},
    {"name": "Basket Arena", "sport_type": SportType.BASKETBALL, "surface": SurfaceType.WOOD, "players_per_side": 5, "price_per_hour": 45.00, "description": "Full-size indoor basketball court."},
    {"name": "Beach Volley Club", "sport_type": SportType.VOLLEYBALL, "surface": SurfaceType.SAND, "players_per_side": 6, "price_per_hour": 30.00, "description": "Olympic-size beach volleyball court."},
    {"name": "Hockey Park", "sport_type": SportType.HOCKEY, "surface": SurfaceType.SYNTHETIC, "players_per_side": 5, "price_per_hour": 38.00, "description": "Synthetic hockey court for fast games."},
    {"name": "Tennis Hard Court", "sport_type": SportType.TENNIS, "surface": SurfaceType.HARD, "players_per_side": 2, "price_per_hour": 25.00, "description": "Hard tennis court, well maintained."},
    {"name": "South Soccer", "sport_type": SportType.FOOTBALL, "surface": SurfaceType.SYNTHETIC, "players_per_side": 5, "price_per_hour": 22.00, "description": "Affordable synthetic football court."},
    {"name": "Basket Outdoor", "sport_type": SportType.BASKETBALL, "surface": SurfaceType.HARD, "players_per_side": 5, "price_per_hour": 18.00, "description": "Outdoor basketball court with hoops."},
    {"name": "Volley Indoor", "sport_type": SportType.VOLLEYBALL, "surface": SurfaceType.INDOOR, "players_per_side": 6, "price_per_hour": 35.00, "description": "Indoor volleyball court."},
    {"name": "Hockey Grass", "sport_type": SportType.HOCKEY, "surface": SurfaceType.GRASS, "players_per_side": 11, "price_per_hour": 50.00, "description": "Natural grass hockey field."},
]

USERS_DATA = [
    {"username": "admin", "email": "admin@soccer.com", "role": "ADMIN", "password": "Admin1234!", "phone_number": "+5491100000000"},
    {"username": "carlos", "email": "carlos@email.com", "role": "CLIENT", "password": "Client1234!", "phone_number": "+5491111111111"},
    {"username": "maria", "email": "maria@email.com", "role": "CLIENT", "password": "Client1234!", "phone_number": "+5491122222222"},
    {"username": "diego", "email": "diego@email.com", "role": "CLIENT", "password": "Client1234!", "phone_number": "+5491133333333"},
    {"username": "lucia", "email": "lucia@email.com", "role": "CLIENT", "password": "Client1234!", "phone_number": "+5491144444444"},
    {"username": "vendor1", "email": "vendor1@email.com", "role": "VENDOR", "password": "Vendor1234!", "phone_number": "+5491155555555"},
    {"username": "vendor2", "email": "vendor2@email.com", "role": "VENDOR", "password": "Vendor1234!", "phone_number": "+5491166666666"},
]

BOOKING_STATUSES = [Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.CANCELLED, Booking.Status.COMPLETED]


class Command(BaseCommand):
    help = "Seed the database with sample users, courts, vendors, and bookings"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            Booking.objects.all().hard_delete()
            Court.objects.all().hard_delete()
            Vendor.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        self.stdout.write("Seeding users...")
        users = self._seed_users()

        self.stdout.write("Seeding vendors...")
        vendors = self._seed_vendors(users)

        self.stdout.write("Seeding courts...")
        courts = self._seed_courts(vendors)

        self.stdout.write("Seeding court schedules...")
        self._seed_schedules(courts)

        self.stdout.write("Seeding bookings...")
        self._seed_bookings(users, courts)

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

    def _seed_vendors(self, users):
        vendors = []
        vendor_users = [u for u in users if u.role == "VENDOR"]
        vendor_configs = [
            {"business_name": "Pro Sports Management", "commission_rate": 8.00},
            {"business_name": "Elite Courts Group", "commission_rate": 12.00},
        ]
        for i, v_user in enumerate(vendor_users):
            config = vendor_configs[i] if i < len(vendor_configs) else {"business_name": f"{v_user.username} Sports", "commission_rate": 10.00}
            vendor, created = Vendor.objects.get_or_create(
                user=v_user,
                defaults={
                    "business_name": config["business_name"],
                    "is_approved": True,
                    "commission_rate": config["commission_rate"],
                },
            )
            if created:
                self.stdout.write(f"  Created vendor: {vendor.business_name}")
            vendors.append(vendor)
        return vendors

    def _seed_courts(self, vendors):
        courts = []
        for i, data in enumerate(COURTS_DATA):
            vendor = vendors[i % len(vendors)] if vendors else None
            court, created = Court.objects.get_or_create(
                name=data["name"],
                defaults={**data, "vendor": vendor},
            )
            if not created:
                court.sport_type = data["sport_type"]
                court.surface = data["surface"]
                court.players_per_side = data["players_per_side"]
                court.price_per_hour = Decimal(str(data["price_per_hour"]))
                court.description = data["description"]
                court.vendor = vendor
                court.save()
            if created:
                self.stdout.write(f"  Created court: {court.name} ({court.get_sport_type_display()})")
            courts.append(court)
        return courts

    def _seed_schedules(self, courts):
        count = 0
        for court in courts:
            for day in range(7):
                schedule, created = CourtSchedule.objects.get_or_create(
                    court=court,
                    day_of_week=day,
                    defaults={
                        "open_time": time(8, 0),
                        "close_time": time(23, 0),
                    },
                )
                if created:
                    count += 1
        self.stdout.write(f"  Created {count} schedules")

    def _seed_bookings(self, users, courts):
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
        for i in range(30):
            user = random.choice(clients)
            court = random.choice(courts)
            booking_date = today + timedelta(days=random.randint(-10, 20))
            start, end = random.choice(hours)
            status = random.choice(BOOKING_STATUSES)
            duration = (end.hour + end.minute / 60) - (start.hour + start.minute / 60)
            total_price = Decimal(str(court.price_per_hour)) * Decimal(str(duration))
            commission = Decimal('0')
            if court.vendor and court.vendor.is_approved:
                commission = total_price * court.vendor.commission_rate / Decimal('100')

            booking, created = Booking.objects.get_or_create(
                user=user,
                court=court,
                date=booking_date,
                start_time=start,
                defaults={
                    "end_time": end,
                    "total_price": total_price,
                    "commission": commission,
                    "status": status,
                },
            )
            if created:
                count += 1
                self.stdout.write(f"  Created booking: {court.name} on {booking_date} ({status})")

        self.stdout.write(f"  Total bookings created: {count}")
