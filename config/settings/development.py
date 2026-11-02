from .base import *
from django.core.management.utils import get_random_secret_key

if not SECRET_KEY:
    SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', get_random_secret_key())

DEBUG = True
# Allow localhost without env var in development
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# No Redis in local dev: an in-memory broker keeps `.delay()` from trying to
# reach localhost:6379 (which raised RuntimeError and produced 500s on booking
# creation). Emails are simply queued and never delivered in development.
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'
CELERY_TASK_ALWAYS_EAGER = False

# Security headers for development
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
