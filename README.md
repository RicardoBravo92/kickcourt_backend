# Soccer Booking Backend

REST API for managing soccer field bookings, built with Django REST Framework.

## Features

- JWT Authentication (login, register, refresh token)
- Role-based access (Admin, Client)
- Soccer field catalog (CRUD for admins)
- Booking management with conflict detection
- Filtering, search, and pagination

## Tech Stack

- Python 3.13
- Django 6.0
- Django REST Framework
- SimpleJWT (authentication)
- SQLite (development)

## Setup

```bash
# Clone repository
git clone git@github.com:RicardoBravo92/soccer_booking_backend.git
cd soccer_booking_backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed database (optional)
python manage.py seed

# Start server
python manage.py runserver
```

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/register/` | Register user | No |
| POST | `/api/auth/login/` | Get JWT token | No |
| POST | `/api/auth/refresh/` | Refresh JWT token | No |
| GET | `/api/fields/` | List fields | No |
| POST | `/api/fields/` | Create field | Admin |
| GET | `/api/bookings/` | List bookings | Yes |
| POST | `/api/bookings/` | Create booking | Yes |
| GET | `/api/bookings/my_bookings/` | My bookings | Yes |
| POST | `/api/bookings/{id}/cancel/` | Cancel booking | Yes |

## Seed Data

```bash
python manage.py seed           # Create sample data (skips duplicates)
python manage.py seed --clear   # Clear existing data and re-seed
```

Creates:
- **5 users**: 1 admin (`admin` / `Admin1234!`) + 4 clients (`carlos`, `maria`, `diego`, `lucia` / `Client1234!`)
- **10 fields**: various types (5/7/11-a-side), surfaces (synthetic/natural/indoor), prices ($22-$80/h)
- **15 bookings**: all statuses (PENDING, CONFIRMED, CANCELLED, COMPLETED) across past, present, and future dates

## Project Structure

```
soccer_backend/
├── config/              # Project settings
│   ├── settings/        # Split settings (base/dev/prod)
│   ├── urls.py
│   └── middleware.py
├── accounts/            # User management
│   ├── models.py        # Custom User model
│   ├── views.py         # Register endpoint
│   ├── permissions.py   # IsAdmin, IsClient
│   └── management/commands/seed.py  # Database seeder
├── fields/              # Soccer field catalog
│   ├── models.py        # Field model with QuerySet
│   └── views.py         # Field CRUD
└── bookings/            # Booking management
    ├── models.py        # Booking model with QuerySet
    ├── services.py      # Business logic
    └── views.py         # Booking CRUD + actions
```

## Testing

```bash
python manage.py test
```

## License

MIT
