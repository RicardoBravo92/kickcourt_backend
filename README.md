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

## Testing

```bash
python manage.py test
```

## License

MIT
